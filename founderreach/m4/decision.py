"""Fail-closed eligibility followed by channel-neutral, ordinal ranking."""
from __future__ import annotations

from founderreach.evidence import EvidenceObservation
from founderreach.m4.candidates import (CandidateFactory, DecisionContext, observation_ref,
                                        site_ref, content_ref)
from founderreach.m4.contracts import (AcquisitionCandidate, DecisionResult, Eligibility,
                                        RankedCandidate, action_identity, candidate_identity, digest)
from founderreach.source_registry import SourceRegistry


class AcquisitionDecisionEngine:
    ACTIONS = {
        "owned_website": ("prepare_content_plan", "local_prepare", {"m3_content_opportunity"}),
        "technical_seo": ("prepare_technical_fix", "local_prepare", {"m3_content_opportunity", "m3_site_finding"}),
        "owned_answer": ("prepare_answer_improvement", "local_prepare", {"m3_site_finding"}),
        "owned_identity": ("prepare_entity_correction", "local_prepare", {"m3_site_finding"}),
        "owned_social": ("prepare_social_outline", "local_prepare", {"owned_channel_access"}),
        "community_research": ("review_customer_question", "internal_research", {"m2_observation"}),
        "media": ("verify_placement_terms", "internal_research", {"placement"}),
        "newsletter": ("verify_placement_terms", "internal_research", {"placement"}),
        "directory": ("verify_placement_terms", "internal_research", {"placement"}),
        "partnership": ("verify_placement_terms", "internal_research", {"placement"}),
    }
    def __init__(self, registry: SourceRegistry | None = None):
        self.registry = registry or SourceRegistry()
        self.factory = CandidateFactory()

    def eligibility(self, context: DecisionContext, candidate: AcquisitionCandidate) -> Eligibility:
        context.validate()
        reasons: list[str] = []
        research = False
        expected = self.ACTIONS.get(candidate.channel)
        ref_kinds = {ref.kind for ref in candidate.supporting_evidence}
        if not expected or candidate.action_type != expected[0] or candidate.action_scope != expected[1] or not expected[2] <= ref_kinds:
            reasons.append("Unsupported channel action or missing channel-specific evidence")
        if candidate.business_id != context.profile.identifier or candidate.profile_version != context.profile.version:
            return Eligibility(research_eligible=False, local_action_eligible=False,
                               reasons=["Business or profile version does not match"])
        if candidate.candidate_id != candidate_identity(candidate) or candidate.action_id != action_identity(candidate):
            return Eligibility(research_eligible=False, local_action_eligible=False,
                               reasons=["Candidate or exact action version changed"])
        if candidate.action_id not in {item.action_id for item in self.factory.build(context)}:
            reasons.append("Action is not generated from the current business evidence")
        if candidate.fixture_only != (context.site_evidence_mode == "fixture") and context.content:
            reasons.append("Site evidence mode does not match candidate")
        if context.content and context.site_evidence_mode not in ("fixture", "approved_live"):
            reasons.append("Site evidence mode is unknown")
        by_id = {item.observation_id: item for item in context.observations}
        observation_ids: set[str] = set()
        for ref in candidate.supporting_evidence:
            if ref.kind == "m2_observation":
                item = by_id.get(ref.identifier)
                if not item or item.business_id != candidate.business_id:
                    reasons.append("Missing business-scoped M2 observation")
                    continue
                observation_ids.add(item.observation_id)
                if ref.model_dump() != observation_ref(item).model_dump():
                    reasons.append("M2 evidence changed since candidate preparation")
                policy = self.registry.get(item.source_key)
                if item.provenance == "public_api" and (not policy or policy.version != item.source_policy_version
                        or policy.decision("research") != "allowed"):
                    reasons.append("Current source policy is unknown, expired or changed")
                    continue
                if item.provenance == "public_api" and candidate.action_scope == "local_prepare" and (
                        not policy or policy.decision("owned_content_planning") != "allowed"):
                    reasons.append("Current source policy forbids owned-content planning")
                if item.current_verification_state() != "verified" or item.relevance_state != "matched":
                    reasons.append("Demand evidence is stale, unverified or irrelevant")
                    continue
                if not item.may_support("research"):
                    reasons.append("Research permission is not current")
                    continue
                research = True
                if candidate.action_scope == "local_prepare" and not item.may_support("owned_content_planning"):
                    reasons.append("Owned-content planning permission is absent")
            elif ref.kind == "m3_site_finding":
                if not context.content or context.site_evidence_mode not in ("fixture", "approved_live"):
                    reasons.append("Trusted site audit is absent")
                    continue
                all_findings = ([site_ref(x) for x in context.content.site.findings] +
                                [site_ref(x, engine="aeo") for x in context.content.aeo.findings] +
                                [site_ref(x, engine="geo") for x in context.content.geo.readiness_findings])
                if not any(x.model_dump() == ref.model_dump() for x in all_findings):
                    reasons.append("Site finding changed or is not in the audited inventory")
            elif ref.kind == "m3_content_opportunity":
                if not context.content or not any(content_ref(x).model_dump() == ref.model_dump()
                                                  for x in context.content.opportunities):
                    reasons.append("M3 content opportunity changed or is absent")
            elif ref.kind == "placement":
                matches = [x for x in context.placements if x.supporting_observation_id == ref.identifier]
                if not matches or not any(digest(x.model_dump(mode="json")) == ref.fingerprint
                                          and str(x.target_url) == ref.source_url and x.stage == "research_only"
                                          for x in matches):
                    reasons.append("Placement evidence changed or is not research-only")
                if candidate.action_scope != "internal_research":
                    reasons.append("Placement contact is not authorized")
            elif ref.kind == "owned_channel_access":
                matches = [x for x in context.owned_channels if x.account_url == ref.identifier]
                if not any(x.current() and digest(x.model_dump(mode="json")) == ref.fingerprint for x in matches):
                    reasons.append("Owned-channel access is not current or verified")
            else:
                reasons.append("Unsupported evidence type")
        if not observation_ids:
            reasons.append("No traceable M2 observation")
        if candidate.estimated_cash_cost_inr is None:
            reasons.append("Cash cost is unknown; ₹0 cannot be assumed")
        elif candidate.estimated_cash_cost_inr > 0:
            reasons.append("New cash spend exceeds the ₹0 ceiling")
        if candidate.permission_state in ("unknown", "blocked", "expired"):
            reasons.append("Candidate permission is not current")
        if candidate.action_scope == "local_prepare" and candidate.permission_state != "planning_allowed":
            reasons.append("Local preparation requires planning permission")
        if candidate.action_scope == "internal_research" and candidate.permission_state != "research_allowed":
            reasons.append("Internal research requires research permission")
        if candidate.founder_effort == "unknown" or candidate.risk == "unknown":
            reasons.append("Effort or risk is unknown")
        if context.content and candidate.action_scope == "local_prepare":
            conflicts = [x for x in context.content.aeo.findings if x.code in
                         ("contradictory_answer", "unsupported_answer_claim") and
                         observation_ids.intersection(x.observation_ids)]
            if conflicts:
                reasons.append("Contradictory or unsupported answer claim requires human resolution")
        if not research:
            reasons.append("No current verified research evidence")
        return Eligibility(research_eligible=research,
                           local_action_eligible=research and not reasons,
                           external_release_eligible=False, reasons=list(dict.fromkeys(reasons)))

    @staticmethod
    def rubric(candidate: AcquisitionCandidate, context: DecisionContext) -> dict[str, int]:
        source_ids = {x.identifier for x in candidate.supporting_evidence if x.kind == "m2_observation"}
        site_partial = bool(context.content and context.content.site.state == "partial")
        return {
            "customer_fit": 2 if candidate.relevance == "matched" else 1,
            "evidence_strength": 2 if len(source_ids) >= 2 else 1,
            "timeliness": {"timely": 2, "evergreen": 1, "unknown": 0}[candidate.timeliness],
            "feasibility": 1 if candidate.action_scope == "internal_research" or site_partial else 2,
            "founder_effort": {"small": 2, "medium": 1, "large": 0, "unknown": 0}[candidate.founder_effort],
            "cash_cost": 2 if candidate.estimated_cash_cost_inr == 0 else 0,
            "risk": {"low": 2, "medium": 1, "high": 0, "unknown": 0}[candidate.risk],
            "measurement": 2 if candidate.measurement_ready else 1 if candidate.suggested_outcome_metric else 0,
        }

    def decide(self, context: DecisionContext,
               candidates: list[AcquisitionCandidate] | None = None) -> DecisionResult:
        context.validate()
        candidates = candidates if candidates is not None else self.factory.build(context)
        ranked: list[RankedCandidate] = []
        rejected: list[dict] = []
        seen_actions: set[tuple[str, str, str | None]] = set()
        for candidate in candidates:
            eligibility = self.eligibility(context, candidate)
            key = (candidate.channel, candidate.action_type, candidate.target_url)
            if key in seen_actions:
                rejected.append({"candidate_id": candidate.candidate_id, "reasons": ["Duplicate channel action and target consolidated"]})
                continue
            if not eligibility.local_action_eligible:
                rejected.append({"candidate_id": candidate.candidate_id, "reasons": eligibility.reasons,
                                 "research_eligible": eligibility.research_eligible})
                continue
            seen_actions.add(key)
            rubric = self.rubric(candidate, context)
            total = sum(rubric.values())
            ranked.append(RankedCandidate(candidate=candidate, eligibility=eligibility,
                rubric=rubric, total_points=total,
                explanation="; ".join(f"{name}={value}/2" for name, value in rubric.items())))
        ranked.sort(key=lambda x: (-x.total_points, x.candidate.candidate_id))
        status = ("recommended" if ranked else
                  "source_unavailable" if context.discovery_status in ("unavailable", "permission_blocked")
                  else "no_eligible_action")
        primary = ranked[0] if ranked else None
        alternatives = ranked[1:4]
        uncertainties = list(dict.fromkeys((primary.candidate.uncertainty if primary else []) +
            (["Discovery was partial or unavailable; absence of demand cannot be inferred"] if
              context.discovery_status in ("partial", "unavailable", "permission_blocked") else [])))
        return DecisionResult(business_id=context.profile.identifier, profile_version=context.profile.version,
            status=status, discovery_status=context.discovery_status, primary=primary,
            alternatives=alternatives, rejected=rejected,
            why_primary=(f"Highest eligible ordinal rubric total ({primary.total_points}/16); "
                         f"{primary.explanation}. No conversion or revenue forecast." if primary else None),
            why_alternatives_lower=[f"{x.candidate.channel}: {x.total_points}/16 versus "
                                    f"{primary.total_points}/16; {x.explanation}" for x in alternatives],
            uncertainties=uncertainties,
            required_approvals=["Founder review of evidence and exact action",
                "Signed CEO approval and independent preflight before any manual release"] if primary else [],
            suggested_success_metrics=[primary.candidate.suggested_outcome_metric] if primary and
                primary.candidate.suggested_outcome_metric else [])
