"""Generate only channels supported by supplied business-scoped records."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from founderreach.evidence import EvidenceObservation
from founderreach.models import ProductProfile
from founderreach.m3.content import ContentAnalysis
from founderreach.m3.site import origin
from founderreach.placements import PlacementOpportunity
from founderreach.m4.contracts import AcquisitionCandidate, EvidenceRef, digest, make_candidate


class OwnedChannelCapability(BaseModel):
    business_id: str
    channel: str = "owned_social"
    account_url: str
    owner_confirmed: bool
    planning_permission: bool
    checked_at: datetime
    expires_at: datetime
    verification_method: str
    measurement_ready: bool = False

    def current(self, now: datetime | None = None) -> bool:
        current = now or datetime.now(timezone.utc)
        return bool(self.owner_confirmed and self.planning_permission and self.checked_at.tzinfo
                    and self.expires_at.tzinfo and self.checked_at <= current < self.expires_at)


@dataclass
class DecisionContext:
    profile: ProductProfile
    observations: list[EvidenceObservation]
    content: ContentAnalysis | None = None
    placements: list[PlacementOpportunity] = field(default_factory=list)
    owned_channels: list[OwnedChannelCapability] = field(default_factory=list)
    discovery_status: str = "not_run"
    site_evidence_mode: str = "unknown"

    def validate(self):
        if not self.profile.confirmed:
            raise PermissionError("Confirmed profile required")
        business = self.profile.identifier
        if any(item.business_id != business for item in self.observations + self.placements + self.owned_channels):
            raise PermissionError("Cross-business M4 input")
        if self.content and (self.content.business_id != business or self.content.site.business_id != business
                             or self.content.site.approved_origin != origin(str(self.profile.website))
                             or self.content.aeo.business_id != business or self.content.geo.business_id != business
                             or any(x.business_id != business or x.profile_version != self.profile.version
                                    for x in self.content.opportunities)):
            raise PermissionError("M3 analysis does not match current business profile")


def observation_ref(item: EvidenceObservation) -> EvidenceRef:
    return EvidenceRef(kind="m2_observation", identifier=item.observation_id,
        provenance=item.provenance, verification_state=item.current_verification_state(),
        policy_version=item.source_policy_version,
        source_url=str(item.source_url) if item.source_url else None,
        fingerprint=digest(item.model_dump(mode="json")))


def site_ref(finding, *, engine: str = "seo") -> EvidenceRef:
    return EvidenceRef(kind="m3_site_finding", identifier=f"{engine}:{finding.code}|{finding.affected_url or ''}",
        provenance="owned_site_audit", verification_state="observed",
        source_url=finding.affected_url, fingerprint=digest(finding.model_dump(mode="json")))


def content_ref(opportunity) -> EvidenceRef:
    return EvidenceRef(kind="m3_content_opportunity", identifier=opportunity.opportunity_id,
        provenance="m3_evidence_linked_content", verification_state="review_pending",
        source_url=opportunity.existing_page,
        fingerprint=digest(opportunity.model_dump(mode="json")))


class CandidateFactory:
    def build(self, context: DecisionContext) -> list[AcquisitionCandidate]:
        context.validate()
        profile = context.profile
        by_id = {item.observation_id: item for item in context.observations}
        audience = profile.target_audiences[0] if profile.target_audiences else "founder_review_required"
        candidates: list[AcquisitionCandidate] = []
        verified_demand = [item for item in context.observations if
                           item.kind in ("customer_question", "customer_need", "complaint")
                           and item.relevance_state == "matched" and
                           item.current_verification_state() == "verified" and item.may_support("research")]

        def add(channel, action_type, scope, action, evidence, *, url=None, effort="medium",
                risk="low", metric=None, measured=False, uncertainty=None, permission="planning_allowed",
                cost=0.0):
            if not evidence:
                return
            refs = list(dict((f"{ref.kind}:{ref.identifier}", ref) for ref in evidence).values())
            observations = [by_id[ref.identifier] for ref in refs if ref.kind == "m2_observation"
                            and ref.identifier in by_id]
            timeliness = "timely" if any(x.freshness_state == "timely" for x in observations) else \
                         "evergreen" if observations and all(x.freshness_state == "evergreen" for x in observations) else "unknown"
            candidates.append(make_candidate(business_id=profile.identifier, profile_version=profile.version,
                channel=channel, action_type=action_type, action_scope=scope,
                target_customer_segment=audience, proposed_action=action, target_url=url,
                supporting_evidence=refs, relevance="matched" if observations else "uncertain",
                timeliness=timeliness, permission_state=permission,
                confidence_basis="independently verified demand" if observations else "observed owned-site finding",
                uncertainty=uncertainty or [], founder_effort=effort, estimated_cash_cost_inr=cost,
                risk=risk, reversibility="easy" if scope == "internal_research" else "moderate",
                suggested_outcome_metric=metric, measurement_ready=measured,
                fixture_only=context.site_evidence_mode == "fixture"))

        if context.content:
            analysis = context.content
            for opportunity in analysis.opportunities:
                support = [by_id[id] for id in opportunity.source_observation_ids if id in by_id]
                verified = [item for item in support if item in verified_demand and
                            item.may_support("owned_content_planning")]
                if not verified or opportunity.proposed_acquisition_action == "research_only":
                    continue
                refs = [observation_ref(item) for item in verified] + [content_ref(opportunity)]
                relevant_site = [finding for finding in analysis.site.findings if
                                 finding.affected_url in (opportunity.existing_page, analysis.site.approved_origin)
                                 and finding.code in opportunity.related_seo_codes]
                refs += [site_ref(finding) for finding in relevant_site]
                url = opportunity.existing_page or analysis.site.approved_origin
                add("owned_website", "prepare_content_plan", "local_prepare",
                    f"Prepare one evidence-linked plan for: {opportunity.search_or_answer_intent}", refs,
                    url=url, effort=opportunity.estimated_effort,
                    metric=opportunity.suggested_outcome_metric, measured=False,
                    uncertainty=["Publication and organic reach remain unverified"])
                for finding in relevant_site:
                    if finding.code in ("canonical", "noindex", "robots_blocked"):
                        add("technical_seo", "prepare_technical_fix", "local_prepare",
                            f"Review and prepare correction for {finding.code} at {finding.affected_url}",
                            [observation_ref(item) for item in verified] + [content_ref(opportunity), site_ref(finding)],
                            url=finding.affected_url, effort="small", risk="medium",
                            metric="Founder-verified technical correction", measured=True,
                            uncertainty=["Search indexing outcome is unknown"])
            for finding in analysis.aeo.findings:
                if finding.code != "missing_direct_answer" or not finding.affected_url:
                    continue
                support = [by_id[id] for id in finding.observation_ids if id in by_id]
                verified = [item for item in support if item in verified_demand and item.may_support("owned_content_planning")]
                if verified:
                    add("owned_answer", "prepare_answer_improvement", "local_prepare",
                        f"Prepare a concise supported answer on {finding.affected_url}",
                        [observation_ref(item) for item in verified] + [site_ref(finding, engine="aeo")],
                        url=finding.affected_url, effort="small", metric="Founder-reviewed direct-answer coverage",
                        measured=True, uncertainty=["Answer visibility is unmeasured"])
            for finding in analysis.geo.readiness_findings:
                if finding.code not in ("brand_name_mismatch", "schema_brand_mismatch", "contact_inconsistency"):
                    continue
                support = verified_demand[:1]
                if support:
                    add("owned_identity", "prepare_entity_correction", "local_prepare",
                        f"Review confirmed identity and prepare correction for {finding.code}",
                        [observation_ref(support[0]), site_ref(finding, engine="geo")],
                        url=finding.affected_url or analysis.site.approved_origin,
                        effort="small", risk="medium", metric="Founder-confirmed identity consistency",
                        measured=True, uncertainty=["AI visibility remains unknown"])

        for capability in context.owned_channels:
            if not capability.current() or "owned_channel" not in profile.allowed_acquisition_channels:
                continue
            for item in verified_demand[:1]:
                if not item.may_support("owned_content_planning"):
                    continue
                ref = EvidenceRef(kind="owned_channel_access", identifier=capability.account_url,
                    provenance="founder_confirmed_account", verification_state="current",
                    source_url=capability.account_url, fingerprint=digest(capability.model_dump(mode="json")))
                add("owned_social", "prepare_social_outline", "local_prepare",
                    f"Prepare a founder-reviewed outline answering observed question: {item.claim}",
                    [observation_ref(item), ref], url=capability.account_url,
                    effort="small", risk="medium", metric="Tagged qualified visits after separate publication approval",
                    measured=capability.measurement_ready,
                    uncertainty=["Audience reach is unknown; publication requires separate signed approval"])

        for item in verified_demand:
            if item.source_key != "hackernews":
                continue
            add("community_research", "review_customer_question", "internal_research",
                f"Review the observed question and current community rules; record learning internally: {item.claim}",
                [observation_ref(item)], url=str(item.source_url), effort="small", risk="medium",
                metric="Founder-reviewed research insight", measured=False, permission="research_allowed",
                uncertainty=["No community reply permission or outreach authorization"])

        for placement in context.placements:
            item = by_id.get(placement.supporting_observation_id)
            if not item or item.current_verification_state() != "verified" or placement.stage != "research_only":
                continue
            ref = EvidenceRef(kind="placement", identifier=placement.supporting_observation_id,
                provenance="observed_placement", verification_state="research_only",
                source_url=str(placement.target_url), fingerprint=digest(placement.model_dump(mode="json")))
            add(placement.kind, "verify_placement_terms", "internal_research",
                f"Review published terms, audience and permission for observed {placement.kind}: {placement.target_name}",
                [observation_ref(item), ref], url=str(placement.target_url), effort="medium",
                metric="Placement permission and audience verified by founder", measured=False,
                permission="research_allowed", uncertainty=["Contact permission and placement cost unknown"])
        return candidates
