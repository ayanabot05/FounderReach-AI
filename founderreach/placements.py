"""Evidence-backed research leads for channels that require separate permission checks."""
from typing import Literal
from pydantic import BaseModel, Field, HttpUrl, model_validator

from founderreach.evidence import EvidenceObservation


class PlacementOpportunity(BaseModel):
    business_id: str
    kind: Literal["newsletter", "media", "directory", "partnership"]
    target_name: str = Field(min_length=1)
    target_url: HttpUrl
    supporting_observation_id: str
    rationale: str = Field(min_length=1)
    permission_state: Literal["unknown", "blocked", "expired", "allowed"] = "unknown"
    stage: Literal["research_only"] = "research_only"

    @model_validator(mode="after")
    def no_unsupported_claim(self):
        if not self.supporting_observation_id:
            raise ValueError("A real evidence observation is required")
        return self


def placement_from_evidence(observation: EvidenceObservation, *, kind: str,
                            target_name: str, target_url: str, rationale: str) -> PlacementOpportunity:
    if observation.kind != "placement_opportunity" or observation.relevance_state == "rejected":
        raise ValueError("Placement requires relevant placement evidence")
    if observation.current_verification_state() != "verified":
        raise ValueError("Placement source must be independently verified")
    if str(observation.source_url) != target_url:
        raise ValueError("Target URL must match verified evidence source")
    return PlacementOpportunity(business_id=observation.business_id, kind=kind,
                                target_name=target_name, target_url=target_url,
                                supporting_observation_id=observation.observation_id,
                                rationale=rationale, permission_state="unknown")
