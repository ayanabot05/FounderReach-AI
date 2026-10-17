"""Isolated local research store; no production or legacy opportunity writes."""
import sqlite3
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

from founderreach.models import CustomerOpportunity
from founderreach.identity import opportunity_id
from founderreach.evidence import EvidenceObservation
from founderreach.privacy import require_minimized_text


class ResearchStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS research_evidence (
                business_id TEXT NOT NULL, source_id TEXT NOT NULL,
                opportunity_id TEXT NOT NULL UNIQUE, original_url TEXT NOT NULL,
                profile_version INTEGER NOT NULL, payload_json TEXT NOT NULL,
                PRIMARY KEY (business_id, source_id))""")
            conn.execute("CREATE INDEX IF NOT EXISTS research_by_business_url ON research_evidence(business_id, original_url)")
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS research_unique_business_url ON research_evidence(business_id, original_url)")
            conn.execute("""CREATE TABLE IF NOT EXISTS evidence_observations (
                business_id TEXT NOT NULL, observation_id TEXT NOT NULL, source_id TEXT NOT NULL,
                payload_json TEXT NOT NULL, PRIMARY KEY (business_id, observation_id))""")
            conn.execute("""CREATE TABLE IF NOT EXISTS review_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT, business_id TEXT NOT NULL,
                observation_id TEXT NOT NULL, reviewer TEXT NOT NULL, decision TEXT NOT NULL,
                reason TEXT NOT NULL, created_at TEXT NOT NULL)""")
            conn.execute("""CREATE TABLE IF NOT EXISTS query_runs (
                run_id INTEGER PRIMARY KEY AUTOINCREMENT, business_id TEXT NOT NULL,
                source_key TEXT NOT NULL, payload_json TEXT NOT NULL, created_at TEXT NOT NULL)""")

    def _connect(self):
        return sqlite3.connect(self.path)

    def save(self, opportunity: CustomerOpportunity):
        require_minimized_text(opportunity.evidence_excerpt, opportunity.direct_problem_evidence,
                               opportunity.customer_problem, opportunity.why_relevant,
                               opportunity.suggested_response,
                               opportunity.verification.evidence_excerpt if opportunity.verification else None,
                               opportunity.verification.verification_notes if opportunity.verification else None,
                               opportunity.feedback_notes, *opportunity.rejection_reasons)
        opportunity = opportunity.model_copy(update={"author": None})
        if not opportunity.business_id or not opportunity.source_id:
            raise ValueError("Stable business and source IDs are required")
        if opportunity.id != opportunity_id(opportunity.business_id, opportunity.source_id):
            raise ValueError("Opportunity ID does not match business and source identity")
        with self._connect() as conn:
            old = conn.execute("SELECT original_url FROM research_evidence WHERE business_id=? AND source_id=?",
                               (opportunity.business_id, opportunity.source_id)).fetchone()
            if old and old[0] != opportunity.original_url:
                raise ValueError("Source identity cannot silently change URL")
            alias = conn.execute("SELECT source_id FROM research_evidence WHERE business_id=? AND original_url=?",
                                 (opportunity.business_id, opportunity.original_url)).fetchone()
            if alias and alias[0] != opportunity.source_id:
                raise ValueError("One business URL has conflicting source identities")
            conn.execute("""INSERT INTO research_evidence VALUES (?,?,?,?,?,?)
                ON CONFLICT(business_id, source_id) DO UPDATE SET
                profile_version=excluded.profile_version, payload_json=excluded.payload_json""",
                (opportunity.business_id, opportunity.source_id, opportunity.id,
                 opportunity.original_url, opportunity.profile_version, opportunity.model_dump_json()))

    def list_business(self, business: str) -> list[CustomerOpportunity]:
        with self._connect() as conn:
            rows = conn.execute("SELECT payload_json FROM research_evidence WHERE business_id=? ORDER BY source_id",
                                (business,)).fetchall()
        return [CustomerOpportunity.model_validate_json(row[0]) for row in rows]

    def save_observation(self, observation: EvidenceObservation) -> None:
        require_minimized_text(observation.excerpt, observation.claim)
        with self._connect() as conn:
            old = conn.execute("SELECT payload_json FROM evidence_observations WHERE business_id=? AND observation_id=?",
                               (observation.business_id, observation.observation_id)).fetchone()
            if old:
                prior = EvidenceObservation.model_validate_json(old[0])
                if prior.source_id != observation.source_id or prior.provenance != observation.provenance or prior.source_url != observation.source_url:
                    raise ValueError("Observation source and provenance cannot change")
                if prior.review_state != observation.review_state:
                    raise ValueError("Review state changes require an audit event")
            conn.execute("""INSERT INTO evidence_observations VALUES (?,?,?,?)
                ON CONFLICT(business_id, observation_id) DO UPDATE SET payload_json=excluded.payload_json""",
                (observation.business_id, observation.observation_id, observation.source_id,
                 observation.model_dump_json()))

    def list_observations(self, business: str) -> list[EvidenceObservation]:
        from founderreach.identity import business_id
        business_id(business)
        with self._connect() as conn:
            rows = conn.execute("SELECT payload_json FROM evidence_observations WHERE business_id=? ORDER BY observation_id",
                                (business,)).fetchall()
        return [EvidenceObservation.model_validate_json(row[0]) for row in rows]

    def get_observation(self, business: str, observation: str) -> EvidenceObservation | None:
        from founderreach.identity import business_id
        business_id(business)
        with self._connect() as conn:
            row = conn.execute("SELECT payload_json FROM evidence_observations WHERE business_id=? AND observation_id=?",
                               (business, observation)).fetchone()
        return EvidenceObservation.model_validate_json(row[0]) if row else None

    def record_review(self, business: str, observation: str, reviewer: str,
                      decision: str, reason: str) -> EvidenceObservation:
        require_minimized_text(reason)
        if decision not in ("confirmed", "rejected") or not reviewer.strip() or not reason.strip():
            raise ValueError("Review requires decision, reviewer and reason")
        with self._connect() as conn:
            row = conn.execute("SELECT payload_json FROM evidence_observations WHERE business_id=? AND observation_id=?",
                               (business, observation)).fetchone()
            if not row:
                raise LookupError("Business observation not found")
            old = EvidenceObservation.model_validate_json(row[0])
            if old.review_state != "pending":
                raise ValueError("Only pending evidence may be reviewed")
            updated = old.model_copy(update={"review_state": decision})
            conn.execute("UPDATE evidence_observations SET payload_json=? WHERE business_id=? AND observation_id=?",
                         (updated.model_dump_json(), business, observation))
            conn.execute("INSERT INTO review_events (business_id,observation_id,reviewer,decision,reason,created_at) VALUES (?,?,?,?,?,?)",
                         (business, observation, reviewer, decision, reason, datetime.now(timezone.utc).isoformat()))
        return updated

    def list_reviews(self, business: str, observation: str) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute("SELECT reviewer,decision,reason,created_at FROM review_events WHERE business_id=? AND observation_id=? ORDER BY event_id",
                                (business, observation)).fetchall()
        return [dict(zip(("reviewer", "decision", "reason", "created_at"), row)) for row in rows]

    def log_query_run(self, business: str, source_key: str, payload: dict) -> None:
        from founderreach.identity import business_id
        business_id(business)
        with self._connect() as conn:
            conn.execute("INSERT INTO query_runs (business_id,source_key,payload_json,created_at) VALUES (?,?,?,?)",
                         (business, source_key, json.dumps(payload, default=str), datetime.now(timezone.utc).isoformat()))

    def list_query_runs(self, business: str) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute("SELECT payload_json FROM query_runs WHERE business_id=? ORDER BY run_id", (business,)).fetchall()
        return [json.loads(row[0]) for row in rows]

    def prune_retention(self, registry, now: datetime | None = None) -> int:
        """Apply reviewed source retention limits in this local store on use."""
        now = now or datetime.now(timezone.utc)
        removed = 0
        with self._connect() as conn:
            rows = conn.execute("SELECT business_id,observation_id,payload_json FROM evidence_observations").fetchall()
            for business, identity, payload in rows:
                observation = EvidenceObservation.model_validate_json(payload)
                policy = registry.get(observation.source_key)
                if policy and observation.observed_at < now - timedelta(days=policy.retention_days):
                    conn.execute("DELETE FROM review_events WHERE business_id=? AND observation_id=?", (business, identity))
                    conn.execute("DELETE FROM evidence_observations WHERE business_id=? AND observation_id=?", (business, identity))
                    removed += 1
            runs = conn.execute("SELECT run_id,source_key,created_at FROM query_runs").fetchall()
            for run_id, source_key, created_at in runs:
                policy = registry.get(source_key)
                if policy and datetime.fromisoformat(created_at) < now - timedelta(days=policy.retention_days):
                    conn.execute("DELETE FROM query_runs WHERE run_id=?", (run_id,))
            opportunities = conn.execute("SELECT business_id,source_id,payload_json FROM research_evidence").fetchall()
            for business, source, payload in opportunities:
                opportunity = CustomerOpportunity.model_validate_json(payload)
                source_key = "hackernews" if opportunity.platform == "Hacker News" else opportunity.platform.lower().replace(" ", "_")
                policy = registry.get(source_key)
                if policy and opportunity.created_at < now - timedelta(days=policy.retention_days):
                    conn.execute("DELETE FROM research_evidence WHERE business_id=? AND source_id=?", (business, source))
        return removed
