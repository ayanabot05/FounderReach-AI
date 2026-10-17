"""Bind M4 review choices to the existing signed DecisionRun lifecycle."""
import json

from founderreach.acquisition import DecisionRun, Experiment
from founderreach.m4.candidates import DecisionContext
from founderreach.m4.contracts import DecisionResult
from founderreach.m4.decision import AcquisitionDecisionEngine


def review_packet(decision: DecisionResult) -> dict:
    """An unapproved local review artifact; it has no release capability."""
    if not decision.primary:
        raise ValueError("No eligible primary action")
    candidate = decision.primary.candidate
    return {"mode": "LOCAL_REVIEW_ONLY", "business_id": candidate.business_id,
            "profile_version": candidate.profile_version, "candidate_id": candidate.candidate_id,
            "action_id": candidate.action_id, "channel": candidate.channel,
            "proposed_action": candidate.proposed_action,
            "evidence": [x.model_dump(mode="json") for x in candidate.supporting_evidence],
            "uncertainties": decision.uncertainties,
            "required_approvals": decision.required_approvals,
            "approved": False}


def prepare_existing_gate_run(decision: DecisionResult, context: DecisionContext, *, baseline_artifact: str,
                              exact_human_copy: str, destination: str) -> DecisionRun:
    """Prepare an exact version using M1's gate; no signature or packet release here."""
    if not decision.primary or not decision.primary.eligibility.local_action_eligible:
        raise PermissionError("No eligible M4 action")
    candidate = decision.primary.candidate
    current = AcquisitionDecisionEngine().decide(context)
    if (not current.primary or current.primary.candidate.action_id != candidate.action_id
            or current.primary.candidate.candidate_id != candidate.candidate_id):
        raise PermissionError("M4 recommendation is no longer the current eligible action")
    if candidate.fixture_only:
        raise PermissionError("Fixture decisions cannot enter the manual release gate")
    if destination != candidate.target_url or not exact_human_copy.strip():
        raise ValueError("Exact copy and the selected candidate destination are required")
    if candidate.estimated_cash_cost_inr != 0:
        raise PermissionError("Only known ₹0 actions may enter the signed gate")
    experiment = Experiment(channel=candidate.channel, action=candidate.proposed_action,
        audience_evidence=tuple(x.source_url for x in candidate.supporting_evidence if x.source_url),
        channel_evidence=candidate.confidence_basis, reach="Unknown",
        evidence_strength=candidate.confidence_basis, founder_effort=candidate.founder_effort,
        planned_cost_inr=0, measurability=candidate.suggested_outcome_metric or "Unknown",
        prerequisites=tuple(decision.required_approvals), reason=decision.why_primary or "",
        rank=1)
    run = DecisionRun([experiment], 1,
        {"m4_candidate_id": candidate.candidate_id, "m4_action_id": candidate.action_id,
         "business_id": candidate.business_id, "profile_version": candidate.profile_version,
         "evidence": [x.model_dump(mode="json") for x in candidate.supporting_evidence]},
        {"authorized_new_spend_inr": 0})
    run.freeze_baseline(baseline_artifact)
    binding = {"purpose": "founderreach.m4.exact-action.v1",
               "business_id": candidate.business_id, "profile_version": candidate.profile_version,
               "candidate_id": candidate.candidate_id, "action_id": candidate.action_id,
               "proposed_action": candidate.proposed_action, "exact_human_copy": exact_human_copy}
    run.prepare_action(json.dumps(binding, sort_keys=True, ensure_ascii=False), destination, 0)
    return run
