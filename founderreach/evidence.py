"""Source-independent, business-scoped evidence for later audit and decision engines."""
from datetime import datetime, timezone
from hashlib import sha256
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, model_validator

from founderreach.identity import business_id


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class EvidenceObservation(BaseModel):
    observation_id: str
    business_id: str
    source_id: str
    source_key: str
    source_policy_version: int | None = None
    kind: Literal["customer_question", "customer_need", "complaint", "site_signal",
                  "third_party_mention", "placement_opportunity"]
    provenance: Literal["public_api", "founder_attested", "owned_site", "independent_review"]
    source_url: HttpUrl | None = None
    excerpt: str = Field(min_length=1, max_length=1000)
    claim: str = Field(min_length=1, max_length=1000)
    published_at: datetime | None = None
    observed_at: datetime = Field(default_factory=utc_now)
    verification_state: Literal["verified", "unverified", "stale", "attested", "failed"]
    verification_method: str | None = None
    verified_at: datetime | None = None
    verification_expires_at: datetime | None = None
    verification_failure: str | None = None
    relevance_state: Literal["matched", "uncertain", "rejected"]
    freshness_state: Literal["timely", "evergreen", "unknown"]
    permission_state: Literal["allowed", "blocked", "unknown", "expired"]
    allowed_uses: list[str] = Field(default_factory=list)
    review_state: Literal["not_required", "pending", "confirmed", "rejected"] = "not_required"
    routes: list[str] = Field(default_factory=list)
    attested_by: str | None = None

    @model_validator(mode="after")
    def validate_provenance(self):
        business_id(self.business_id)
        for value in (self.published_at, self.observed_at, self.verified_at, self.verification_expires_at):
            if value is not None and value.tzinfo is None:
                raise ValueError("Evidence timestamps must have timezones")
        if self.provenance == "founder_attested":
            if self.verification_state != "attested" or self.verified_at or self.verification_method:
                raise ValueError("Founder attestation is not independent source verification")
            if not self.attested_by:
                raise ValueError("Founder attestation requires an attestor")
        if self.verification_state == "verified":
            if not self.verified_at or not self.verification_expires_at or not self.verification_method:
                raise ValueError("Verified evidence requires method and bounded verification time")
            if self.verification_expires_at <= self.verified_at:
                raise ValueError("Verification expiry must follow the check")
        if self.provenance == "public_api" and not self.source_url:
            raise ValueError("Public API evidence requires a source URL")
        if self.permission_state != "allowed" and any(
                use in self.allowed_uses for use in ("community_reply", "partner_contact", "publication")):
            raise ValueError("Blocked or unknown permission cannot allow external action")
        return self

    def current_verification_state(self, now: datetime | None = None) -> str:
        if self.verification_state == "verified" and self.verification_expires_at:
            if (now or utc_now()) >= self.verification_expires_at:
                return "stale"
        return self.verification_state

    def may_support(self, use: str, now: datetime | None = None) -> bool:
        if self.permission_state != "allowed" or use not in self.allowed_uses:
            return False
        if self.review_state == "rejected" or self.relevance_state == "rejected":
            return False
        if use != "research" and (self.review_state == "pending" or self.relevance_state == "uncertain"):
            return False
        if use in ("community_reply", "partner_contact", "publication"):
            return self.current_verification_state(now) == "verified" and self.review_state in ("confirmed", "not_required")
        return True


def observation_id(business: str, source: str, kind: str, excerpt: str) -> str:
    digest = sha256(f"evidence:v1:{business_id(business)}:{source}:{kind}:{excerpt.strip()}".encode()).hexdigest()
    return digest[:24]


def founder_attestation(*, business: str, native_id: str, excerpt: str, claim: str,
                        attested_by: str, source_url: str | None = None,
                        kind: str = "customer_question") -> EvidenceObservation:
    source = f"founder-attested:{native_id}"
    return EvidenceObservation(
        observation_id=observation_id(business, source, kind, excerpt), business_id=business,
        source_id=source, source_key="founder_attested", kind=kind, provenance="founder_attested",
        source_url=source_url, excerpt=excerpt, claim=claim, verification_state="attested",
        relevance_state="uncertain", freshness_state="unknown", permission_state="unknown",
        review_state="pending", routes=["demand_evidence", "owned_content_research"], attested_by=attested_by)
