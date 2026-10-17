"""Local acquisition decision workflow. No network calls or publishing adapter.

Discussion labels are used only as problem research, never as outreach leads.
Production persistence is deliberately absent until live database security is checked.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Optional

from founderreach.ai.cost_tracker import cost_tracker
from founderreach.engine import AYANA_PROFILE
from founderreach.models import DiscussionItem
from founderreach.validation.intent import intent_classifier
from founderreach.validation.scorer import opportunity_scorer
from founderreach.approval_gate import Approval, PreflightAttestation, verify_approval, verify_preflight


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


@dataclass(frozen=True)
class Experiment:
    channel: str
    action: str
    audience_evidence: tuple[str, ...]
    channel_evidence: str
    reach: str
    evidence_strength: str
    founder_effort: str
    planned_cost_inr: int
    measurability: str
    prerequisites: tuple[str, ...]
    reason: str
    rank: int


@dataclass(frozen=True)
class ActionVersion:
    experiment_rank: int
    exact_copy: str
    destination: str
    channel: str
    maximum_cost_inr: int
    version: str


@dataclass
class Outcome:
    day: int
    attributable_visits: Optional[int] = None
    cta_clicks: Optional[int] = None
    qualified_inquiries: Optional[int] = None
    founder_minutes: Optional[int] = None
    actual_cost_inr: Optional[float] = None

    def __post_init__(self):
        if not 0 <= self.day <= 28:
            raise ValueError("Outcome day must be 0–28")
        for key, value in asdict(self).items():
            if value is not None and value < 0:
                raise ValueError(f"{key} cannot be negative")
        if self.cta_clicks is not None and self.attributable_visits is not None and self.cta_clicks > self.attributable_visits:
            raise ValueError("CTA sessions cannot exceed attributable visit sessions")


@dataclass
class DecisionRun:
    experiments: list[Experiment]
    recommendation: int
    evidence_audit: dict
    budget_snapshot: dict
    baseline_artifact: Optional[str] = None
    action: Optional[ActionVersion] = None
    approval: Optional[Approval] = None
    preflight: Optional[PreflightAttestation] = None
    packet_released_version: Optional[str] = None
    audit: list[dict] = field(default_factory=list)
    outcomes: list[Outcome] = field(default_factory=list)

    def _event(self, name: str, **details):
        self.audit.append({"at": _now(), "event": name, **details})

    def freeze_baseline(self, completed_artifact: str):
        path = Path(completed_artifact)
        if not path.is_file() or path.name == "AYANA_MANUAL_BASELINE_V1.md":
            raise ValueError("Completed manual baseline JSON required")
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, UnicodeError) as exc:
            raise ValueError("Completed manual baseline JSON required") from exc
        required = ("founder_id", "start_time", "stop_time", "active_minutes", "sources",
                    "selected_action", "draft_outline", "cta", "measurement_plan",
                    "seen_prior_recommendation")
        if any(key not in record or record[key] in (None, "", []) for key in required):
            raise ValueError("Baseline missing required timing, evidence, or action fields")
        if not isinstance(record["active_minutes"], (int, float)) or record["active_minutes"] <= 0:
            raise ValueError("Active founder minutes must be positive")
        self.baseline_artifact = str(path.resolve())
        self._event("manual_baseline_recorded", artifact_sha256=hashlib.sha256(path.read_bytes()).hexdigest())

    def prepare_action(self, exact_copy: str, destination: str, maximum_cost_inr: int = 0):
        if not self.baseline_artifact:
            raise PermissionError("Complete manual baseline before reviewing assisted action")
        selected = self.experiments[self.recommendation - 1]
        if not exact_copy.strip() or not destination.startswith("https://"):
            raise ValueError("Exact copy and HTTPS destination required")
        if maximum_cost_inr < 0 or maximum_cost_inr > 1000:
            raise ValueError("Cost exceeds hard ceiling")
        if maximum_cost_inr > 0:
            raise PermissionError("No paid activation approved")
        payload = {"experiment_rank": selected.rank, "exact_copy": exact_copy,
                   "destination": destination, "channel": selected.channel,
                   "maximum_cost_inr": maximum_cost_inr}
        self.action = ActionVersion(**payload, version=_digest(payload))
        self.approval = None
        self.preflight = None
        self.packet_released_version = None
        self._event("action_version_prepared", version=self.action.version)
        return self.action

    def record_ceo_approval(self, approval: Approval):
        if not self.action:
            raise PermissionError("Prepare exact action before CEO approval")
        identity = verify_approval(self.action, approval)
        self.approval = approval
        self._event("ceo_approval_recorded", version=approval.version, key_fingerprint=identity)

    def record_preflight(self, attestation: PreflightAttestation):
        if not self.action:
            raise PermissionError("Prepare exact action before preflight")
        identity = verify_preflight(self.action, attestation)
        self.preflight = attestation
        self._event("independent_preflight_recorded", version=attestation.version, key_fingerprint=identity)

    def manual_execution_packet(self) -> dict:
        """Returns instructions for a human; never performs an external action."""
        if not self.action or not self.approval or not self.preflight:
            raise PermissionError("Signed CEO approval and independent preflight are required")
        verify_approval(self.action, self.approval)
        verify_preflight(self.action, self.preflight)
        self.packet_released_version = self.action.version
        self._event("manual_execution_packet_released", version=self.action.version)
        return {"mode": "MANUAL_ONLY", "action": asdict(self.action),
                "approval": {"version": self.approval.version, "approved_at": self.approval.approved_at},
                "preflight": {"version": self.preflight.version, "observed_at": self.preflight.observed_at}}

    def record_outcome(self, outcome: Outcome):
        if not self.action or not self.approval or self.approval.version != self.action.version or self.packet_released_version != self.action.version:
            raise PermissionError("Approved and gate-cleared action required before outcome recording")
        if any(o.day == outcome.day for o in self.outcomes):
            raise ValueError("One outcome snapshot per day")
        self.outcomes.append(outcome)
        self._event("outcome_recorded", day=outcome.day)

    def export_local(self, path: str):
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def build_ayana_decision(labels_path: str) -> DecisionRun:
    """Rank three owned/opt-in experiments using existing labeled research.

    No connector is called: Reddit remains disabled and live source verification is
    unavailable. The scorer is diagnostic for problem fit, never outreach authority.
    """
    labels = json.loads(Path(labels_path).read_text(encoding="utf-8"))
    positive = []
    rejected = []
    for row in labels:
        has_intent, _, _ = intent_classifier.extract_direct_evidence(row["text"], AYANA_PROFILE)
        discussion = DiscussionItem(id=row["id"], platform=row["source"], original_url=row["url"], text=row["text"])
        score = opportunity_scorer.score(discussion, AYANA_PROFILE)
        result = {"id": row["id"], "url": row["url"], "human_label": row["label"],
                  "direct_problem_detected": has_intent, "problem_fit_score": score.problem_fit,
                  "source_live_verified_now": False, "outreach_eligible": False}
        (positive if has_intent and row["label"] == "POTENTIAL_CUSTOMER_INTENT" else rejected).append(result)
    if not positive:
        raise ValueError("No independently labeled direct AYANA problem evidence")
    evidence_urls = tuple(p["url"] for p in positive)
    experiments = [
        Experiment("AYANA-owned website", "Check whether an existing parent check-in guide is deployed; if not, prepare its existing copy and CTA for founder review and manual publication.",
                   evidence_urls, "AYANA source contains three guide pages; 12 Oct owner audit said they were not deployed then. Current deployment unverified.",
                   "Low–medium, uncertain", "Direct problem evidence; search demand and current reach unverified", "Medium", 0,
                   "Potentially high after guide visits, CTA, and signup attribution are checked",
                   ("Current deployed guide status", "Guide page and CTA events", "Visit-to-signup or inquiry attribution", "CEO approval"),
                   "Owned channel, existing asset, and clearest documented customer problem; readiness remains conditional.", 1),
        Experiment("Founder-owned LinkedIn", "Prepare one practical NRI parent-care post with a distinct tagged link; founder may publish manually only after approval.",
                   evidence_urls, "No AYANA LinkedIn ownership, follower geography, or prior reach verified.",
                   "Unknown", "Direct problem evidence; channel audience unverified", "Low–medium", 0,
                   "Tagged visits possible; signup attribution currently absent",
                   ("Account ownership and relevant audience", "Tagged-link measurement", "CEO approval"),
                   "Lower preparation effort, but no evidence the current audience contains qualified caregivers.", 2),
        Experiment("Opted-in diaspora partner", "Prepare a parent-care checklist for an existing partner who has invited contributions; partner controls any publication.",
                   evidence_urls, "No opted-in partner or newsletter placement verified.",
                   "Zero until partner opts in; potentially medium later", "Direct problem evidence; channel access unverified", "High", 0,
                   "Tagged visits and partner distribution count possible if partner cooperates",
                   ("Documented invitation", "Partner audience and distribution", "Tagged-link measurement", "CEO approval"),
                   "Potential audience fit, but access and effort are currently unproven.", 3),
    ]
    run = DecisionRun(experiments, 1,
                      {"type": "historical_independent_labels_not_live_source_verification",
                       "positive_problem_examples": positive, "rejected_examples": rejected,
                       "reddit_discovery_enabled": False},
                      cost_tracker.get_spending_summary())
    run._event("decision_generated", recommendation=1, production_write=False, external_action=False)
    return run
