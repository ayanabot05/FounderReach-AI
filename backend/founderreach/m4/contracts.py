"""Channel-neutral candidate and decision contracts with stable exact-action identity."""
from __future__ import annotations

from hashlib import sha256
import json
import math
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from founderreach.identity import business_id


def digest(value: dict) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                             default=str).encode()).hexdigest()[:24]


class EvidenceRef(BaseModel):
    kind: Literal["m2_observation", "m3_site_finding", "m3_content_opportunity", "placement", "owned_channel_access"]
    identifier: str
    provenance: str
    verification_state: str
    policy_version: int | None = None
    source_url: str | None = None
    fingerprint: str | None = None


class AcquisitionCandidate(BaseModel):
    business_id: str
    profile_version: int = Field(ge=1)
    candidate_id: str
    action_id: str
    channel: str
    action_type: str
    action_scope: Literal["internal_research", "local_prepare"]
    target_customer_segment: str
    proposed_action: str
    target_url: str | None = None
    supporting_evidence: list[EvidenceRef] = Field(min_length=1)
    relevance: Literal["matched", "uncertain"]
    timeliness: Literal["timely", "evergreen", "unknown"]
    permission_state: Literal["research_allowed", "planning_allowed", "unknown", "blocked", "expired"]
    confidence_basis: str
    uncertainty: list[str] = Field(default_factory=list)
    founder_effort: Literal["small", "medium", "large", "unknown"]
    estimated_cash_cost_inr: float | None = Field(default=None, ge=0)
    risk: Literal["low", "medium", "high", "unknown"]
    reversibility: Literal["easy", "moderate", "difficult", "unknown"]
    suggested_outcome_metric: str | None = None
    measurement_ready: bool = False
    review_state: Literal["pending_human_review"] = "pending_human_review"
    approval_state: Literal["unapproved"] = "unapproved"
    fixture_only: bool = False

    @model_validator(mode="after")
    def valid_identity(self):
        business_id(self.business_id)
        if self.estimated_cash_cost_inr is not None and not math.isfinite(self.estimated_cash_cost_inr):
            raise ValueError("Cash cost must be finite or unknown")
        if not self.proposed_action.strip() or not self.channel.strip() or not self.action_type.strip():
            raise ValueError("Specific channel and action are required")
        if self.candidate_id != candidate_identity(self) or self.action_id != action_identity(self):
            raise ValueError("Candidate or exact action identity does not match payload")
        return self


def candidate_identity(candidate: AcquisitionCandidate) -> str:
    return digest({"business": candidate.business_id, "profile_version": candidate.profile_version,
                   "channel": candidate.channel, "action_type": candidate.action_type,
                   "target": candidate.target_url,
                   "evidence": sorted((x.kind, x.identifier) for x in candidate.supporting_evidence)})


def action_identity(candidate: AcquisitionCandidate) -> str:
    return digest(candidate.model_dump(mode="json", exclude={"action_id"}))


def make_candidate(**fields) -> AcquisitionCandidate:
    fields["supporting_evidence"] = [x if isinstance(x, EvidenceRef) else EvidenceRef.model_validate(x)
                                     for x in fields["supporting_evidence"]]
    draft = AcquisitionCandidate.model_construct(candidate_id="", action_id="", **fields)
    draft.candidate_id = candidate_identity(draft)
    draft.action_id = action_identity(draft)
    return AcquisitionCandidate.model_validate(draft.model_dump())


class Eligibility(BaseModel):
    research_eligible: bool
    local_action_eligible: bool
    external_release_eligible: bool = False
    reasons: list[str] = Field(default_factory=list)


class RankedCandidate(BaseModel):
    candidate: AcquisitionCandidate
    eligibility: Eligibility
    rubric: dict[str, int]
    total_points: int
    explanation: str


class DecisionResult(BaseModel):
    business_id: str
    profile_version: int
    status: Literal["recommended", "no_eligible_action", "source_unavailable"]
    discovery_status: str = "not_run"
    primary: RankedCandidate | None = None
    alternatives: list[RankedCandidate] = Field(default_factory=list)
    rejected: list[dict] = Field(default_factory=list)
    why_primary: str | None = None
    why_alternatives_lower: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    required_approvals: list[str] = Field(default_factory=list)
    suggested_success_metrics: list[str] = Field(default_factory=list)
    execution_mode: Literal["LOCAL_REVIEW_ONLY"] = "LOCAL_REVIEW_ONLY"
