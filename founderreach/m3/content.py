"""Shared M3 handoff to future acquisition ranking; never publishes or drafts."""
from __future__ import annotations

from hashlib import sha256
from pydantic import BaseModel, Field

from founderreach.evidence import EvidenceObservation
from founderreach.models import ProductProfile
from founderreach.m3.site import SEOFinding, SiteAudit
from founderreach.m3.aeo import AEOReport
from founderreach.m3.geo import GEOReport


class SupportingClaim(BaseModel):
    observation_id: str
    claim: str
    citation_url: str | None
    evidence_label: str


class ContentOpportunity(BaseModel):
    opportunity_id: str
    business_id: str
    profile_version: int
    intent_key: str
    source_observation_ids: list[str]
    existing_page: str | None
    proposed_page_topic: str | None
    target_audience: str
    search_or_answer_intent: str
    supporting_claims: list[SupportingClaim]
    related_seo_codes: list[str]
    related_aeo_codes: list[str]
    related_geo_codes: list[str]
    permission_state: str
    freshness_state: str
    confidence: float = Field(ge=0, le=1)
    estimated_effort: str
    review_status: str = "pending_human_review"
    proposed_acquisition_action: str
    suggested_outcome_metric: str
    execution_mode: str = "LOCAL_REVIEW_ONLY"


class ContentAnalysis(BaseModel):
    business_id: str
    site: SiteAudit
    aeo: AEOReport
    geo: GEOReport
    opportunities: list[ContentOpportunity] = Field(default_factory=list)
    status: str
    evidence_coverage: float = Field(ge=0, le=1)
    unsupported_claim_rate: float = Field(ge=0, le=1)
    limitations: list[str] = Field(default_factory=list)


class ContentOpportunityEngine:
    def build(self, profile: ProductProfile, observations: list[EvidenceObservation],
              site: SiteAudit, aeo: AEOReport, geo: GEOReport, *,
              discovery_status: str = "not_run") -> ContentAnalysis:
        if not profile.confirmed or any(x.business_id != profile.identifier for x in observations) or any(
                x.business_id != profile.identifier for x in (site, aeo, geo)):
            raise PermissionError("M3 inputs must share one confirmed business")
        by_id = {x.observation_id: x for x in observations}
        opportunities: list[ContentOpportunity] = []
        used_topics: set[str] = set()
        used_pages: set[str] = set()
        supported_claims = 0
        all_claims = 0
        for cluster in sorted(aeo.clusters, key=lambda x: -x.priority):
            if cluster.intent_key in used_topics:
                continue
            matching = cluster.matching_page
            evidence = [by_id[x] for x in cluster.observation_ids if x in by_id]
            verified = [x for x in evidence if x.current_verification_state() == "verified"
                        and x.may_support("owned_content_planning")]
            alternatives = [x for x in evidence if x.provenance == "founder_attested"
                            and x.verification_state == "attested" and x.review_state != "rejected"]
            selected = verified or alternatives
            if not selected:
                continue
            action = ("research_only" if not verified else
                      "improve_owned_page" if matching else "create_owned_page")
            claims = [SupportingClaim(observation_id=x.observation_id, claim=x.claim,
                citation_url=str(x.source_url) if x.source_url else None,
                evidence_label="source_verified" if x in verified else "founder_attested_unverified")
                for x in selected]
            all_claims += len(claims)
            supported_claims += len(verified)
            if matching and matching in used_pages:
                existing = next(item for item in opportunities if item.existing_page == matching)
                for claim in claims:
                    if claim.observation_id not in existing.source_observation_ids:
                        existing.source_observation_ids.append(claim.observation_id)
                        existing.supporting_claims.append(claim)
                existing.related_aeo_codes = sorted(set(existing.related_aeo_codes) |
                    {x.code for x in aeo.findings if set(x.observation_ids) & set(cluster.observation_ids)})
                used_topics.add(cluster.intent_key)
                continue
            if not matching and verified:
                site.findings.append(SEOFinding(code="content_gap", affected_url=site.approved_origin,
                    observed_evidence=cluster.representative_question[:500],
                    problem="No matching owned page was observed for this evidence-backed question",
                    severity="medium", suggested_correction="Review one focused page for this question",
                    confidence=0.7, limitations="Bounded inventory may omit an existing page; no ranking inference",
                    estimated_effort="medium", verification_method="Compare question with approved page inventory"))
            related_seo = sorted({x.code for x in site.findings if x.affected_url == matching or
                                  (not matching and x.code == "content_gap" and
                                   x.observed_evidence == cluster.representative_question[:500])})
            related_aeo = sorted({x.code for x in aeo.findings if set(x.observation_ids) & set(cluster.observation_ids)})
            related_geo = sorted({x.code for x in geo.readiness_findings if x.affected_url in (matching, site.approved_origin, None)})
            identity = sha256(f"content:v1:{profile.identifier}:{profile.version}:{cluster.intent_key}".encode()).hexdigest()[:24]
            opportunities.append(ContentOpportunity(opportunity_id=identity, business_id=profile.identifier,
                profile_version=profile.version, intent_key=cluster.intent_key,
                source_observation_ids=[x.observation_id for x in selected], existing_page=matching,
                proposed_page_topic=None if matching else cluster.representative_question,
                target_audience=profile.target_audiences[0] if profile.target_audiences else "founder_review_required",
                search_or_answer_intent=cluster.representative_question, supporting_claims=claims,
                related_seo_codes=related_seo, related_aeo_codes=related_aeo,
                related_geo_codes=related_geo,
                permission_state="allowed_for_planning" if verified else "unknown_attested",
                freshness_state="timely" if any(x.freshness_state == "timely" for x in selected) else "evergreen"
                    if all(x.freshness_state == "evergreen" for x in selected) else "unknown",
                confidence=min(cluster.priority, 0.4) if not verified else cluster.priority,
                estimated_effort="medium" if action == "create_owned_page" else "small",
                proposed_acquisition_action=action,
                suggested_outcome_metric="Qualified owned-page visits and founder-reviewed answer coverage"))
            used_topics.add(cluster.intent_key)
            if matching:
                used_pages.add(matching)
        useful = [x for x in observations if x.kind in ("customer_question", "customer_need", "complaint")
                  and x.relevance_state != "rejected"]
        used_ids = {id for item in opportunities for id in item.source_observation_ids}
        status = "source_unavailable" if discovery_status in ("unavailable", "permission_blocked") else "ready" if opportunities else "insufficient_evidence"
        limitations = ["Read-only bounded site inventory does not establish indexing, ranking or AI citation status"]
        if discovery_status in ("unavailable", "partial", "permission_blocked"):
            limitations.append("Source discovery was incomplete; no-demand inference is prohibited")
        return ContentAnalysis(business_id=profile.identifier, site=site, aeo=aeo, geo=geo,
            opportunities=opportunities, status=status,
            evidence_coverage=len(used_ids) / len(useful) if useful else 0,
            unsupported_claim_rate=(all_claims - supported_claims) / all_claims if all_claims else 0,
            limitations=limitations)


def evaluate_labeled_codes(actual: list[str], expected: list[str]) -> dict[str, float]:
    """Simple fixed-fixture classification quality; never an acquisition success metric."""
    predicted, gold = set(actual), set(expected)
    tp = len(predicted & gold)
    precision = tp / len(predicted) if predicted else (1.0 if not gold else 0.0)
    recall = tp / len(gold) if gold else 1.0
    return {"precision": precision, "recall": recall,
            "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0}
