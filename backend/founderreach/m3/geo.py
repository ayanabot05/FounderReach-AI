"""Entity readiness and actual, manually captured AI citation observations."""
from __future__ import annotations

from datetime import datetime, timezone
import sqlite3
from pathlib import Path
import re
from urllib.parse import urlsplit
from pydantic import BaseModel, Field, HttpUrl, model_validator

from founderreach.evidence import EvidenceObservation
from founderreach.models import ProductProfile
from founderreach.m3.site import SiteAudit, tokens
from founderreach.m3.aeo import similarity


class FixedQuestionSet(BaseModel):
    business_id: str
    version: int = Field(ge=1)
    questions: list[str] = Field(min_length=1, max_length=30)

    @model_validator(mode="after")
    def distinct_questions(self):
        if len({q.strip().lower() for q in self.questions}) != len(self.questions):
            raise ValueError("Fixed questions must be distinct")
        if any(not q.strip() for q in self.questions):
            raise ValueError("Blank fixed question")
        return self


class AICitationObservation(BaseModel):
    business_id: str
    question_set_version: int
    question: str
    provider: str
    answer_excerpt: str = Field(min_length=1)
    citation_url: HttpUrl
    captured_at: datetime
    capture_method: str = "manual_observation"
    status: str = "observed"

    @model_validator(mode="after")
    def actual_capture(self):
        if self.status != "observed" or self.capture_method != "manual_observation":
            raise ValueError("Only actual manually captured citations may be stored as observed")
        if self.captured_at.tzinfo is None or self.captured_at > datetime.now(timezone.utc):
            raise ValueError("Citation capture time must be timezone-aware and not future")
        if not self.provider.strip() or not self.question.strip():
            raise ValueError("Citation needs provider and fixed question")
        return self


class GEOFinding(BaseModel):
    code: str
    affected_url: str | None
    observed_evidence: str
    problem: str
    suggested_correction: str
    confidence: float = Field(ge=0, le=1)
    limitations: str
    observation_ids: list[str] = Field(default_factory=list)


class EntityObservation(BaseModel):
    entity_type: str
    name: str
    source_url: str | None
    provenance: str
    observed_evidence: str


class GEOReport(BaseModel):
    business_id: str
    entities: list[EntityObservation] = Field(default_factory=list)
    readiness_findings: list[GEOFinding] = Field(default_factory=list)
    third_party_observation_ids: list[str] = Field(default_factory=list)
    citation_observations: list[AICitationObservation] = Field(default_factory=list)
    ai_visibility: str = "unknown"
    fixed_question_set_version: int | None = None
    historical_comparison: dict = Field(default_factory=dict)


class GEOObservationStore:
    """Isolated local history for fixed questions and actual manual captures."""
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS geo_question_sets (
                business_id TEXT NOT NULL, version INTEGER NOT NULL, payload_json TEXT NOT NULL,
                PRIMARY KEY (business_id, version))""")
            conn.execute("""CREATE TABLE IF NOT EXISTS geo_citations (
                id INTEGER PRIMARY KEY AUTOINCREMENT, business_id TEXT NOT NULL,
                question_set_version INTEGER NOT NULL, payload_json TEXT NOT NULL)""")

    def save_question_set(self, question_set: FixedQuestionSet) -> None:
        with sqlite3.connect(self.path) as conn:
            old = conn.execute("SELECT payload_json FROM geo_question_sets WHERE business_id=? AND version=?",
                               (question_set.business_id, question_set.version)).fetchone()
            if old and old[0] != question_set.model_dump_json():
                raise ValueError("Published question-set version is immutable")
            conn.execute("INSERT OR IGNORE INTO geo_question_sets VALUES (?,?,?)",
                         (question_set.business_id, question_set.version, question_set.model_dump_json()))

    def latest_question_set(self, business: str) -> FixedQuestionSet | None:
        with sqlite3.connect(self.path) as conn:
            row = conn.execute("SELECT payload_json FROM geo_question_sets WHERE business_id=? ORDER BY version DESC LIMIT 1",
                               (business,)).fetchone()
        return FixedQuestionSet.model_validate_json(row[0]) if row else None

    def add_citation(self, citation: AICitationObservation) -> None:
        with sqlite3.connect(self.path) as conn:
            row = conn.execute("SELECT payload_json FROM geo_question_sets WHERE business_id=? AND version=?",
                               (citation.business_id, citation.question_set_version)).fetchone()
            if not row:
                raise LookupError("Fixed question set is required")
            fixed = FixedQuestionSet.model_validate_json(row[0])
            if citation.question not in fixed.questions:
                raise ValueError("Citation question is outside the fixed set")
            conn.execute("INSERT INTO geo_citations (business_id,question_set_version,payload_json) VALUES (?,?,?)",
                         (citation.business_id, citation.question_set_version, citation.model_dump_json()))

    def list_citations(self, business: str, version: int) -> list[AICitationObservation]:
        with sqlite3.connect(self.path) as conn:
            rows = conn.execute("SELECT payload_json FROM geo_citations WHERE business_id=? AND question_set_version=? ORDER BY id",
                                (business, version)).fetchall()
        return [AICitationObservation.model_validate_json(row[0]) for row in rows]


def compare_citation_history(observations: list[AICitationObservation]) -> dict:
    if len(observations) < 2:
        return {}
    ordered = sorted(observations, key=lambda x: x.captured_at)
    return {"first_observed_at": ordered[0].captured_at.isoformat(),
            "last_observed_at": ordered[-1].captured_at.isoformat(),
            "actual_observation_count": len(ordered),
            "distinct_citation_urls": len({str(x.citation_url) for x in ordered})}


class GEOEngine:
    def analyze(self, profile: ProductProfile, site: SiteAudit,
                observations: list[EvidenceObservation], *,
                question_set: FixedQuestionSet | None = None,
                citations: list[AICitationObservation] | None = None) -> GEOReport:
        if not profile.confirmed or site.business_id != profile.identifier:
            raise PermissionError("GEO requires one confirmed business and its site audit")
        if any(x.business_id != profile.identifier for x in observations):
            raise PermissionError("Cross-business evidence is not allowed")
        if question_set and question_set.business_id != profile.identifier:
            raise PermissionError("Cross-business question set is not allowed")
        citations = citations or []
        if citations and not question_set:
            raise ValueError("Observed citations require a fixed question set")
        if any(x.business_id != profile.identifier or x.question_set_version != question_set.version
               or x.question not in question_set.questions for x in citations):
            raise PermissionError("Citation does not belong to this business question set")
        report = GEOReport(business_id=profile.identifier,
                           fixed_question_set_version=question_set.version if question_set else None,
                           citation_observations=citations,
                           ai_visibility="observed_citations" if citations else "unknown",
                           historical_comparison=compare_citation_history(citations))
        report.entities.append(EntityObservation(entity_type="organization", name=profile.name,
            source_url=str(profile.website), provenance="founder_confirmed_profile",
            observed_evidence=profile.name))
        name = profile.name.lower()
        home = next((page for page in site.pages if page.url.rstrip("/") == site.approved_origin), None)
        if not home:
            report.readiness_findings.append(self._finding("missing_home_identity", site.approved_origin,
                "Homepage absent from audited inventory", "Organization identity cannot be checked",
                "Audit the approved homepage", 0.9))
        brand_variants = set()
        contact_values = set()
        organization_schema = False
        website_schema = False
        for page in site.pages:
            page_name = page.title.split("|")[-1].split("—")[-1].strip()
            if page_name:
                brand_variants.add(page_name.lower())
            if name not in page.title.lower() and page.url.rstrip("/") == site.approved_origin:
                report.readiness_findings.append(self._finding("brand_name_mismatch", page.url, page.title,
                    "Homepage title omits the confirmed brand name", "Align the visible identity with the confirmed profile", 0.85))
            for paragraph in page.paragraphs:
                contact_values.update(re.findall(r"[\w.+-]+@[\w.-]+\.[a-z]{2,}", paragraph.lower()))
            for entry in page.jsonld:
                values = entry.get("@graph") if isinstance(entry.get("@graph"), list) else [entry]
                for value in values:
                    if not isinstance(value, dict):
                        continue
                    kind = value.get("@type", "")
                    kinds = kind if isinstance(kind, list) else [kind]
                    if "Organization" in kinds:
                        organization_schema = True
                        schema_name = str(value.get("name") or "")
                        if schema_name:
                            report.entities.append(EntityObservation(entity_type="organization", name=schema_name,
                                source_url=page.url, provenance="owned_site_schema",
                                observed_evidence=str(value)[:300]))
                        if schema_name and schema_name.lower() != name:
                            report.readiness_findings.append(self._finding("schema_brand_mismatch", page.url,
                                schema_name, "Organization schema name differs from confirmed brand",
                                "Correct the Organization name after founder review", 0.95))
                    if "WebSite" in kinds:
                        website_schema = True
                        site_url = str(value.get("url") or "")
                        if site_url and urlsplit(site_url).hostname != urlsplit(site.approved_origin).hostname:
                            report.readiness_findings.append(self._finding("website_schema_mismatch", page.url,
                                site_url, "WebSite schema points to a different host",
                                "Set the confirmed canonical website URL", 0.95))
                    if "Product" in kinds:
                        product_name = str(value.get("name") or "")
                        if product_name:
                            report.entities.append(EntityObservation(entity_type="product", name=product_name,
                                source_url=page.url, provenance="owned_site_schema",
                                observed_evidence=str(value)[:300]))
            if name in page.title.lower() and not any(e.entity_type == "product" and e.source_url == page.url
                                                       for e in report.entities):
                report.entities.append(EntityObservation(entity_type="product", name=profile.name,
                    source_url=page.url, provenance="owned_site_title_inference",
                    observed_evidence=page.title))
        if len(brand_variants) > 1:
            report.readiness_findings.append(self._finding("brand_inconsistency", site.approved_origin,
                ", ".join(sorted(brand_variants)), "Page title brand labels differ across the inventory",
                "Choose the founder-confirmed brand name consistently", 0.65))
        if not any("about" in page.url.lower() or "about" in page.title.lower() for page in site.pages):
            report.readiness_findings.append(self._finding("missing_about", site.approved_origin,
                "No About page in approved inventory", "Organization background is not visible in inventory",
                "Review whether a factual About page is needed", 0.7))
        if not contact_values and not any("contact" in page.url.lower() for page in site.pages):
            report.readiness_findings.append(self._finding("missing_contact", site.approved_origin,
                "No contact identity in audited pages", "Contact details were not observed",
                "Review a factual contact page or contact detail", 0.7))
        if len(contact_values) > 1:
            report.readiness_findings.append(self._finding("contact_inconsistency", site.approved_origin,
                ", ".join(sorted(contact_values)), "Multiple contact identities appear in audited pages",
                "Confirm the authoritative contact details with the founder", 0.7))
        if not organization_schema:
            report.readiness_findings.append(self._finding("missing_organization_schema", site.approved_origin,
                "Organization JSON-LD not found", "Organization markup was not observed",
                "Assess accurate Organization markup", 0.9))
        if not website_schema:
            report.readiness_findings.append(self._finding("missing_website_schema", site.approved_origin,
                "WebSite JSON-LD not found", "Website markup was not observed",
                "Assess accurate WebSite markup", 0.9))
        for observation in observations:
            if (observation.kind == "third_party_mention" and observation.current_verification_state() == "verified"
                    and observation.provenance in ("public_api", "independent_review")
                    and observation.source_url and observation.may_support("research")
                    and name in (observation.excerpt + " " + observation.claim).lower()
                    and urlsplit(str(observation.source_url)).hostname != urlsplit(site.approved_origin).hostname):
                report.third_party_observation_ids.append(observation.observation_id)
        if not report.third_party_observation_ids:
            report.readiness_findings.append(self._finding("missing_third_party_evidence", None,
                "No independently verified external brand mention supplied", "Third-party corroboration is unknown",
                "Collect legitimate mentions under an approved source policy", 0.9))
        for page in site.pages:
            for paragraph in page.paragraphs:
                if re.search(r"\b(?:guaranteed|always|\d+%|24/7)\b", paragraph.lower()) and not any(
                        observation.kind == "third_party_mention" and observation.source_url
                        and observation.current_verification_state() == "verified"
                        and observation.may_support("research")
                        and similarity(paragraph, observation.claim) >= 0.75 for observation in observations):
                    report.readiness_findings.append(self._finding("uncited_factual_claim", page.url,
                        paragraph[:200], "Strong factual claim lacks supplied independent evidence",
                        "Add a traceable citation or revise the claim", 0.7))
        return report

    @staticmethod
    def _finding(code, url, evidence, problem, correction, confidence):
        return GEOFinding(code=code, affected_url=url, observed_evidence=evidence, problem=problem,
                          suggested_correction=correction, confidence=confidence,
                          limitations="GEO readiness does not prove AI recommendation or citation")
