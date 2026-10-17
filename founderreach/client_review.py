"""Offline, permission-scoped client review. This module has no live fetch path."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import html
import ipaddress
import json
from pathlib import Path
import re
import sqlite3
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, model_validator

from founderreach.evidence import EvidenceObservation, founder_attestation
from founderreach.identity import business_id
from founderreach.m3.pipeline import analyze_business
from founderreach.m3.site import FixtureSiteFetcher, MAX_BYTES, MAX_PAGES, canonical_url, origin
from founderreach.m4.candidates import DecisionContext
from founderreach.m4.decision import AcquisitionDecisionEngine
from founderreach.models import ProductProfile
from founderreach.privacy import require_minimized_text
from founderreach.research_store import ResearchStore


def offline_public_url(url: str) -> str:
    """Reject unsafe URL shapes without DNS or any network request."""
    parsed = urlsplit(url)
    site_origin = origin(url)
    host = parsed.hostname or ""
    if parsed.query or parsed.fragment or len(url) > 2048:
        raise ValueError("Website URLs must not contain query strings or fragments")
    if not re.fullmatch(r"[a-z0-9.-]+", host, flags=re.IGNORECASE):
        raise ValueError("A public DNS hostname is required")
    labels = host.lower().rstrip(".").split(".")
    if (len(labels) < 2 or any(not part or len(part) > 63 or part.startswith("-")
                              or part.endswith("-") for part in labels)
            or labels[-1] in {"local", "localhost", "internal", "test", "invalid"}):
        raise ValueError("A public DNS hostname is required")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise ValueError("IP-address URLs are not allowed")
    if site_origin != origin(canonical_url(url)):
        raise ValueError("Website origin is inconsistent")
    return canonical_url(url)


class WebsitePermission(BaseModel):
    """Founder supplied exact-origin and bounded page authorization for fixtures."""
    model_config = ConfigDict(extra="forbid")

    business_id: str
    origin: str
    approved_pages: list[str] = Field(min_length=1, max_length=MAX_PAGES)
    purpose: str
    approved_by: str
    approved_at: datetime
    expires_at: datetime

    @model_validator(mode="after")
    def valid_scope(self):
        business_id(self.business_id)
        if self.purpose != "offline_fixture_audit" or self.approved_by != "founder":
            raise ValueError("Founder permission for offline fixture audit is required")
        if self.approved_at.tzinfo is None or self.expires_at.tzinfo is None:
            raise ValueError("Permission times must include a timezone")
        if not self.approved_at <= datetime.now(timezone.utc) < self.expires_at:
            raise ValueError("Website permission is not current")
        clean_origin = origin(offline_public_url(self.origin))
        if self.origin != clean_origin:
            raise ValueError("Permission origin must be exact and canonical")
        pages = [offline_public_url(url) for url in self.approved_pages]
        if len(set(pages)) != len(pages) or any(origin(url) != clean_origin for url in pages):
            raise ValueError("Approved pages must be distinct and on the exact origin")
        if pages != self.approved_pages:
            raise ValueError("Approved page URLs must be canonical")
        return self


def _read_json(path: Path, *, max_bytes: int) -> object:
    if (path.suffix.lower() != ".json" or path.is_symlink() or not path.is_file()
            or path.stat().st_size > max_bytes):
        raise ValueError("A bounded local JSON input file is required")
    return json.loads(path.read_text(encoding="utf-8"))


def _fixture_fetcher(path: Path, permission: WebsitePermission) -> FixtureSiteFetcher:
    raw = _read_json(path, max_bytes=(MAX_PAGES + 2) * (MAX_BYTES + 1024))
    if not isinstance(raw, dict) or not isinstance(raw.get("pages"), dict):
        raise ValueError("Fixture JSON must contain a pages object")
    pages = raw["pages"]
    permitted = set(permission.approved_pages)
    optional_metadata = {permission.origin + "/robots.txt", permission.origin + "/sitemap.xml"}
    required_pages = permitted - optional_metadata
    if len(pages) > MAX_PAGES or not required_pages <= set(pages):
        raise ValueError("Every approved page needs a fixture, within the page limit")
    fixtures = {}
    for url, record in pages.items():
        clean = offline_public_url(url)
        if clean != url or url not in permitted or not isinstance(record, dict):
            raise ValueError("Fixture URL is outside the exact permission scope")
        if set(record) != {"status", "content_type", "body"}:
            raise ValueError("Fixture records need status, content_type and body")
        status, content_type, body = record["status"], record["content_type"], record["body"]
        if (type(status) is not int or not 100 <= status <= 599 or not isinstance(content_type, str)
                or not isinstance(body, str) or len(body.encode("utf-8")) > MAX_BYTES):
            raise ValueError("Fixture response is invalid or too large")
        fixtures[url] = (status, content_type, body)
    return FixtureSiteFetcher(fixtures)


def _attestations(path: Path | None, business: str) -> list[EvidenceObservation]:
    if path is None:
        return []
    raw = _read_json(path, max_bytes=64_000)
    if not isinstance(raw, list) or len(raw) > 10:
        raise ValueError("At most ten minimized attestations are allowed")
    observations = []
    native_ids = set()
    for row in raw:
        if not isinstance(row, dict) or set(row) != {"native_id", "excerpt", "claim", "minimized_by_founder"}:
            raise ValueError("Attestations need native_id, excerpt, claim and minimization confirmation")
        if row["minimized_by_founder"] is not True:
            raise ValueError("Founder must confirm that attestation text was minimized")
        native_id, excerpt, claim = row["native_id"], row["excerpt"], row["claim"]
        if not isinstance(native_id, str) or not re.fullmatch(r"[a-z0-9_-]{1,64}", native_id):
            raise ValueError("Attestation ID must be a nonpersonal local slug")
        if native_id in native_ids:
            raise ValueError("Duplicate attestation ID")
        native_ids.add(native_id)
        if not isinstance(excerpt, str) or not isinstance(claim, str):
            raise ValueError("Attestation text must be plain text")
        require_minimized_text(excerpt, claim)
        observations.append(founder_attestation(
            business=business, native_id=native_id, excerpt=excerpt, claim=claim,
            attested_by="founder"
        ))
    return observations


@dataclass(frozen=True)
class ClientReviewResult:
    report: str
    decision_status: str
    observation_count: int
    website_page_count: int


class _MemoryResearchStore(ResearchStore):
    """Reuse ResearchStore's M2 contract without creating a durable evidence file."""

    def __init__(self):
        self._memory_connection = sqlite3.connect(":memory:")
        super().__init__(Path(":memory:"))

    def _connect(self):
        return self._memory_connection

    def close(self):
        self._memory_connection.close()


def _record_id(kind: str, *parts: str) -> str:
    return kind + "-" + sha256("|".join(parts).encode("utf-8")).hexdigest()[:12]


def _md(value: object) -> str:
    """Keep untrusted fixture and attestation text inert in Markdown reports."""
    escaped = html.escape(str(value), quote=False)
    return re.sub(r"([\\`*_{}\[\]()#+!|])", r"\\\1", escaped)


def _report(profile: ProductProfile, observations: list[EvidenceObservation], content, decision) -> str:
    profile_ref = _record_id("profile", profile.identifier, str(profile.version))
    lines = [f"# Client review: {_md(profile.name)}", "",
             f"Profile: **founder-attested** for this local review. [Source record](#{profile_ref}).",
             "This is an offline review. Any website observations below come only from supplied HTML fixtures.",
             "No live website or demand source was fetched. CONFIRM is a self-declaration, not identity verification.", "",
             "## Source records", "",
             f'- <a id="{profile_ref}"></a> **founder-attested** `{profile_ref}`: '
             f'{_md(profile.name)}; {_md(profile.description)}; '
             f'website: {_md(profile.website or "none")}. '
             'Business details were confirmed for this review, not independently verified.']
    if content:
        for url, error in content.site.fetch_errors.items():
            if error == "MissingFixtureError":
                lines.append(f'- Fixture data for {_md(url)}: UNKNOWN; no response was supplied.')
        for page in content.site.pages:
            ref = _record_id("page", page.url)
            lines.append(f'- <a id="{ref}"></a> **website observation; offline fixture** `{ref}`: {_md(page.url)}; '
                         f'fixture title: {_md(page.title or "UNKNOWN")}.')
        for finding in content.site.findings:
            ref = _record_id("finding", finding.code, finding.affected_url, finding.observed_evidence)
            lines.append(f'- <a id="{ref}"></a> **website observation; offline fixture** `{ref}`: '
                         f'{_md(finding.affected_url)}; `{finding.code}`; '
                         f'recorded basis: {_md(finding.observed_evidence or "UNKNOWN")}.')
    else:
        lines.append("- Website observation: UNKNOWN; no website was supplied.")
    for item in observations:
        lines.append(f'- <a id="{item.observation_id}"></a> **founder-attested** `{item.observation_id}` '
                     f': {_md(item.claim)} Source record: `{item.source_id}`; independently verified: no.')
    if not observations:
        lines.append("- Customer-demand evidence: UNKNOWN; no observations were supplied.")
    lines.extend(["", "## Findings", ""])
    if content:
        for finding in content.site.findings:
            ref = _record_id("finding", finding.code, finding.affected_url, finding.observed_evidence)
            lines.append(f'- **website observation; offline fixture:** {_md(finding.problem)} at '
                         f'{_md(finding.affected_url)}. [Source record](#{ref}).')
        if not content.site.findings:
            page_refs = ", ".join(f"[Source record](#{_record_id('page', page.url)})"
                                  for page in content.site.pages)
            lines.append("- The bounded fixture audit generated no site findings; live website condition is UNKNOWN. "
                         + (page_refs or "No page record is available."))
    else:
        lines.append(f"- Website findings: UNKNOWN; no website was supplied. [Source record](#{profile_ref}).")
    for item in observations:
        lines.append(f'- **founder-attested:** {_md(item.claim)} '
                     f'[Source record](#{item.observation_id}). This is not independently verified demand.')
    lines.extend(["", "## M4 decision", "",
                  f"Status: `{decision.status}`. The existing M4 rules were used unchanged.",
                  f"Input profile: [Source record](#{profile_ref})."])
    for item in observations:
        lines.append(f"Input attestation: [Source record](#{item.observation_id}).")
    if decision.primary is None:
        lines.append("Primary recommendation: none. Eligible demand evidence is insufficient for an acquisition action.")
    else:
        raise RuntimeError("This offline input path cannot substantiate a primary recommendation")
    lines.extend(["", "## Unknowns and limits", "",
                  ("- Live website condition: UNKNOWN; only supplied HTML fixtures were analyzed."
                   if content else "- Live website condition: UNKNOWN; no website was supplied."),
                  "- Independent customer demand: UNKNOWN; founder attestations are not source verification.",
                  "- Automated minimization checks catch some identifiers but cannot guarantee removal of personal data; founder review is required.",
                  "- Visits, conversions, customers and causal impact: UNKNOWN; none were measured.",
                  "- No publishing, outreach, purchase, production write or external action occurred.", ""])
    return "\n".join(lines)


def run_client_review(profile: ProductProfile, *, permission_path: Path | None = None,
                      fixture_path: Path | None = None,
                      attestations_path: Path | None = None) -> ClientReviewResult:
    """Use in-memory inputs, temporary local M2 storage, fixture M3 and unchanged M4."""
    if not profile.confirmed:
        raise PermissionError("Founder confirmation is required")
    business_id(profile.identifier)
    content = None
    if profile.website is None:
        if permission_path is not None or fixture_path is not None:
            raise ValueError("Website-free review must not include a site permission or fixture")
    elif permission_path is None or fixture_path is None:
        raise PermissionError("Website review requires permission and HTML fixtures")
    observations = _attestations(attestations_path, profile.identifier)
    store = _MemoryResearchStore()
    try:
        for item in observations:
            store.save_observation(item)
        if profile.website is not None:
            submitted_url = offline_public_url(str(profile.website))
            permission = WebsitePermission.model_validate(_read_json(permission_path, max_bytes=16_000))
            if (permission.business_id != profile.identifier or
                    permission.origin != origin(submitted_url) or
                    submitted_url not in permission.approved_pages):
                raise PermissionError("Website permission does not match the confirmed profile and exact URL")
            fetcher = _fixture_fetcher(fixture_path, permission)
            audit_pages = [url for url in permission.approved_pages
                           if url not in {permission.origin + "/robots.txt",
                                          permission.origin + "/sitemap.xml"}]
            content = analyze_business(profile, store, fetcher=fetcher,
                                       approved_origin=permission.origin,
                                       approved_urls=audit_pages)
    finally:
        store.close()
    context = DecisionContext(profile=profile, observations=observations, content=content,
                              discovery_status="not_run", site_evidence_mode="fixture" if content else "unknown")
    decision = AcquisitionDecisionEngine().decide(context)
    return ClientReviewResult(_report(profile, observations, content, decision), decision.status,
                              len(observations), len(content.site.pages) if content else 0)
