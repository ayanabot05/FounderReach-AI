"""Versioned, fail-closed source permission records."""
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, model_validator


REGISTRY_DIR = Path(__file__).resolve().parent.parent / "source_registry"
EXTERNAL_USES = frozenset({"community_reply", "partner_contact", "publication"})


class SourcePolicy(BaseModel):
    source_key: str
    version: int = Field(ge=1)
    status: Literal["approved", "blocked", "review_required"]
    terms_url: HttpUrl | None = None
    api_documentation_url: HttpUrl | None = None
    reviewed_at: datetime
    review_due_at: datetime
    allowed_uses: list[str]
    restrictions: list[str]
    retention_days: int = Field(ge=1)
    max_requests_per_hour: int = Field(ge=0)
    max_queries_per_run: int = Field(ge=0)
    max_pages_per_query: int = Field(ge=0)
    verifier: str | None = None

    @model_validator(mode="after")
    def valid_policy(self):
        if self.reviewed_at.tzinfo is None or self.review_due_at.tzinfo is None:
            raise ValueError("Source review timestamps must have timezones")
        if self.review_due_at <= self.reviewed_at:
            raise ValueError("Source review deadline must follow review date")
        if self.status != "approved" and EXTERNAL_USES.intersection(self.allowed_uses):
            raise ValueError("Unapproved policy cannot allow external action")
        return self

    def decision(self, use: str, now: datetime | None = None) -> str:
        current = now or datetime.now(timezone.utc)
        if self.status == "blocked":
            return "blocked"
        if self.status != "approved":
            return "unknown"
        if current >= self.review_due_at:
            return "expired"
        return "allowed" if use in self.allowed_uses else "blocked"


class SourceRegistry:
    def __init__(self, directory: Path = REGISTRY_DIR):
        self.directory = Path(directory)

    def get(self, key: str) -> SourcePolicy | None:
        if not key or not key.replace("_", "").isalnum():
            raise ValueError("Invalid source key")
        files = sorted(self.directory.glob(f"{key}.v*.json"))
        if not files:
            return None
        policies = [SourcePolicy.model_validate_json(path.read_text(encoding="utf-8")) for path in files]
        if any(policy.source_key != key for policy in policies):
            raise ValueError("Source registry key mismatch")
        versions = [policy.version for policy in policies]
        if len(set(versions)) != len(versions):
            raise ValueError("Duplicate source registry version")
        return max(policies, key=lambda policy: policy.version)

    def decision(self, key: str, use: str, now: datetime | None = None) -> str:
        policy = self.get(key)
        return policy.decision(use, now) if policy else "unknown"
