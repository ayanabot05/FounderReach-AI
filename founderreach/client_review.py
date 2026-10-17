"""Permission-scoped client review (offline fixture default or bounded live HTTPS audit)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import html
import ipaddress
import json
from pathlib import Path
import re
import sqlite3
import time
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

from pydantic import BaseModel, ConfigDict, Field, model_validator

from founderreach.evidence import EvidenceObservation, founder_attestation
from founderreach.identity import business_id
from founderreach.m3.pipeline import analyze_business
from founderreach.m3.site import (
    ApprovedSiteFetcher,
    FetchOutcome,
    FixtureSiteFetcher,
    MAX_BYTES,
    MAX_PAGES,
    MissingFixtureError,
    canonical_url,
    origin,
)
from founderreach.m4.candidates import DecisionContext
from founderreach.m4.decision import AcquisitionDecisionEngine
from founderreach.models import ProductProfile
from founderreach.privacy import require_minimized_text
from founderreach.research_store import ResearchStore
from founderreach.website import UnsafeWebsiteError, WebsiteFetchError

LIVE_PERMISSION_MAX_TTL = timedelta(hours=24)


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
    """Founder supplied exact-origin and bounded page authorization (self-declared, not ownership proof)."""
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
        if self.purpose not in {"offline_fixture_audit", "live_site_audit"} or self.approved_by != "founder":
            raise ValueError("Founder permission for offline_fixture_audit or live_site_audit is required")
        if self.approved_at.tzinfo is None or self.expires_at.tzinfo is None:
            raise ValueError("Permission times must include a timezone")
        if not self.approved_at <= datetime.now(timezone.utc) < self.expires_at:
            raise ValueError("Website permission is not current")
        if self.purpose == "live_site_audit" and (self.expires_at - self.approved_at) > LIVE_PERMISSION_MAX_TTL:
            raise ValueError("Live website permission window must not exceed 24 hours")
        clean_origin = origin(offline_public_url(self.origin))
        if self.origin != clean_origin:
            raise ValueError("Permission origin must be exact and canonical")
        pages = [offline_public_url(url) for url in self.approved_pages]
        if len(set(pages)) != len(pages) or any(origin(url) != clean_origin for url in pages):
            raise ValueError("Approved pages must be distinct and on the exact origin")
        if pages != self.approved_pages:
            raise ValueError("Approved page URLs must be canonical")
        if self.purpose == "live_site_audit":
            robots_url = clean_origin + "/robots.txt"
            sitemap_url = clean_origin + "/sitemap.xml"
            if robots_url not in pages:
                raise ValueError("Live website permission must include /robots.txt")
            if not (set(pages) - {robots_url, sitemap_url}):
                raise ValueError("Live website permission must include at least one page URL")
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


class _ScopedLiveSiteFetcher(ApprovedSiteFetcher):
    """Reuse ApprovedSiteFetcher + WebsiteFetcher while locking requests to approved_pages and robots.txt."""

    def __init__(self, permission: WebsitePermission):
        super().__init__(permission.origin)
        self.permitted = set(permission.approved_pages)
        self.robots_url = permission.origin + "/robots.txt"
        self.sitemap_url = permission.origin + "/sitemap.xml"
        self.robots_verified = False
        self._robots_parser = RobotFileParser()

    def fetch(self, url: str) -> FetchOutcome:
        clean_initial = offline_public_url(url)
        if clean_initial == self.sitemap_url and clean_initial not in self.permitted:
            raise MissingFixtureError("Sitemap URL was not included in approved_pages")
        if clean_initial not in self.permitted:
            raise UnsafeWebsiteError("Live fetch URL is outside the exact permission scope")
        if clean_initial != self.robots_url and not self.robots_verified:
            raise WebsiteFetchError("Live fetch blocked because robots.txt was not verified")
        if (clean_initial not in {self.robots_url, self.sitemap_url}
                and not self._robots_parser.can_fetch("FounderReach", clean_initial)):
            raise WebsiteFetchError("Approved page is disallowed by robots.txt")

        current = clean_initial
        for hop in range(self.max_redirects + 1):
            current = offline_public_url(current)
            if origin(current) != self.approved_origin or current not in self.permitted:
                raise UnsafeWebsiteError("Cross-origin or unapproved website request or redirect blocked")
            if self.request_count >= self.max_requests or time.monotonic() - self.started_at >= self.max_duration_seconds:
                raise WebsiteFetchError("Site-audit request or time budget exhausted")
            clean, host, port, ip, path = self._network._target(current)
            self.request_count += 1
            status, headers, body = self._network._request("https", host, port, ip, path)
            if len(body) > MAX_BYTES:
                raise WebsiteFetchError("Response exceeded the site-audit size limit")
            if headers.get("content-encoding", "identity").lower() != "identity":
                raise WebsiteFetchError("Compressed response is unsupported")
            if status in (301, 302, 303, 307, 308):
                if hop == self.max_redirects or not headers.get("location"):
                    raise WebsiteFetchError("Unsafe or excessive redirect")
                current = urljoin(clean, headers["location"])
                continue
            content_type = headers.get("content-type", "")
            if clean_initial == self.robots_url:
                if status != 200 or "text/plain" not in content_type.lower():
                    raise WebsiteFetchError(f"robots.txt unavailable or invalid (HTTP {status})")
                self._robots_parser.parse(body.decode("utf-8", errors="replace").splitlines())
                self.robots_verified = True
            return FetchOutcome(status, content_type, body, clean, headers)
        raise WebsiteFetchError("Too many redirects")


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


def _jsonld_types(blocks: list[dict]) -> list[str]:
    """Extract distinct @type strings from parsed JSON-LD blocks (including @graph items)."""
    types: list[str] = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        items = block.get("@graph") if isinstance(block.get("@graph"), list) else [block]
        for item in items:
            if not isinstance(item, dict):
                continue
            raw_type = item.get("@type")
            values = raw_type if isinstance(raw_type, list) else ([raw_type] if raw_type else [])
            for val in values:
                if isinstance(val, str) and val.strip() and val.strip() not in types:
                    types.append(val.strip())
    return types


def _report(profile: ProductProfile, observations: list[EvidenceObservation], content, decision,
            *, site_evidence_mode: str = "unknown") -> str:
    profile_ref = _record_id("profile", profile.identifier, str(profile.version))
    live_mode = site_evidence_mode == "approved_live"
    site_label = "website observation; live fetch" if live_mode else "website observation; offline fixture"
    mode_summary = (
        "This review used a bounded live HTTPS fetch of founder-approved URLs only."
        if live_mode else
        "This is an offline review. Any website observations below come only from supplied HTML fixtures."
    )
    lines = [
        f"# Client review: {_md(profile.name)}",
        "",
        f"Profile: **founder-attested** for this local review. [Source record](#{profile_ref}).",
        mode_summary,
        ("No demand source was fetched. CONFIRM is a self-declaration, not identity verification; "
         "authorization is self-declared and does not prove site ownership."
         if live_mode else
         "No live website or demand source was fetched. CONFIRM is a self-declaration, not identity verification; "
         "authorization is self-declared and does not prove site ownership."),
        "",
        "## Section 1: Site improvements",
        "",
        ("Findings below come from observed site evidence only (bounded live HTTPS fetch of approved URLs)."
         if live_mode else
         "Findings below come from observed site evidence only (offline HTML and metadata fixtures)."),
        "",
    ]
    if content:
        site_origin = (
            origin(offline_public_url(str(profile.website)))
            if profile.website is not None
            else (origin(content.site.pages[0].url) if content.site.pages else "")
        )
        robots_url = f"{site_origin}/robots.txt"
        sitemap_url = f"{site_origin}/sitemap.xml"
        site_codes = {f.code for f in content.site.findings}
        has_pages = bool(content.site.pages)

        for url, error in content.site.fetch_errors.items():
            if error == "MissingFixtureError":
                lines.append(f"- Fixture data for {_md(url)}: UNKNOWN; no response was supplied.")
            else:
                lines.append(f"- **{site_label}:** Fetch error for {_md(url)}: `{_md(error)}`.")

        robots_err = content.site.fetch_errors.get(robots_url)
        if robots_err == "MissingFixtureError":
            robots_status = "UNKNOWN (no robots.txt response supplied)"
            robots_check = "unknown"
        elif robots_err:
            robots_status = f"unavailable (`{_md(robots_err)}`)"
            robots_check = "finding"
        elif "robots_blocked" in site_codes:
            robots_status = "observed (crawl rules parsed; one or more approved URLs disallowed)"
            robots_check = "finding"
        else:
            robots_status = "observed (HTTP 200 text/plain; crawl rules parsed; approved URLs allowed)"
            robots_check = "pass"
        lines.append(f"- **{site_label}:** robots.txt status ({_md(robots_url)}): {robots_status}.")

        sitemap_err = content.site.fetch_errors.get(sitemap_url)
        if sitemap_err == "MissingFixtureError":
            sitemap_status = "UNKNOWN (no sitemap.xml response supplied)"
            sitemap_check = "unknown"
        elif sitemap_err:
            sitemap_status = f"unavailable (`{_md(sitemap_err)}`)"
            sitemap_check = "finding"
        elif "missing_sitemap" in site_codes:
            sitemap_status = "finding (`missing_sitemap`; sitemap unavailable or returned no URLs)"
            sitemap_check = "finding"
        else:
            unlisted = sum(1 for f in content.site.findings if f.code == "sitemap_omission")
            sitemap_status = (
                f"observed XML sitemap ({len(content.site.sitemap_urls)} URL(s) listed"
                + (f"; {unlisted} audited page(s) missing from sitemap)" if unlisted else "; all audited pages listed)")
            )
            sitemap_check = "finding" if unlisted else "pass"
        lines.append(f"- **{site_label}:** Sitemap status ({_md(sitemap_url)}): {sitemap_status}.")

        title_label = "observed title" if live_mode else "fixture title"
        for page in content.site.pages:
            ref = _record_id("page", page.url)
            canon_text = _md(page.canonical or "none")
            desc_text = _md(page.description or "none")
            h1s = [text for tag, text in page.headings if tag == "h1"]
            h1_text = ", ".join(_md(h) for h in h1s) if h1s else "none"
            jtypes = _jsonld_types(page.jsonld)
            jtypes_text = ", ".join(_md(t) for t in jtypes) if jtypes else "none"
            lines.append(
                f'- <a id="{ref}"></a> **{site_label}** `{ref}`: {_md(page.url)}; '
                f'{title_label}: {_md(page.title or "UNKNOWN")}; '
                f'canonical: {canon_text}; '
                f'meta description: {desc_text}; '
                f'H1 ({len(h1s)}): {h1_text}; '
                f'JSON-LD types: {jtypes_text}.'
            )

        def _page_check(codes: set[str]) -> str:
            if site_codes & codes:
                return "finding"
            return "pass" if has_pages else "unknown"

        checks = [
            ("robots.txt directives", robots_check),
            ("XML sitemap availability and coverage", sitemap_check),
            (
                "Page accessibility (HTTP status and HTML content-type)",
                "finding"
                if (site_codes & {"inaccessible_page"})
                else ("pass" if has_pages else "unknown"),
            ),
            ("Page indexability (noindex meta and X-Robots-Tag)", _page_check({"noindex"})),
            ("Canonical link tag", _page_check({"canonical"})),
            ("Title and meta description", _page_check({"metadata"})),
            ("Primary H1 heading structure", _page_check({"heading_structure"})),
            ("JSON-LD structured data", _page_check({"invalid_jsonld", "missing_structured_data"})),
            (
                "AEO direct-answer and claim consistency",
                "finding" if content.aeo.findings else ("pass" if has_pages else "unknown"),
            ),
            (
                "GEO entity and schema readiness",
                "finding" if content.geo.readiness_findings else ("pass" if has_pages else "unknown"),
            ),
        ]
        lines.append("Checks performed:")
        for check_name, check_state in checks:
            lines.append(f"- **{site_label}:** Check — {check_name}: `{check_state}`.")

        for finding in content.site.findings:
            ref = _record_id("finding", finding.code, finding.affected_url, finding.observed_evidence)
            lines.append(
                f'- <a id="{ref}"></a> **{site_label}** `{ref}`: '
                f'{_md(finding.affected_url)}; `{finding.code}`; '
                f'recorded basis: {_md(finding.observed_evidence or "UNKNOWN")}.'
            )
            lines.append(
                f"- **{site_label}:** {_md(finding.problem)} at "
                f"{_md(finding.affected_url)}. Suggested technical change: {_md(finding.suggested_correction)}. "
                f"[Source record](#{ref})."
            )
        _aeo_problems = {
            "missing_page": "Observed question has no matching page in the approved site inventory",
            "missing_direct_answer": "Matching page does not state a direct answer to the observed question",
            "faq_schema_suitability": "Page answers a question directly without FAQPage structured data",
            "contradictory_answer": "Page statement conflicts with an observed claim",
            "unsupported_answer_claim": "Page paragraph contains an unverified guarantee or numeric claim",
        }
        for finding in content.aeo.findings:
            target_url = finding.affected_url or site_origin
            ref = _record_id("finding-aeo", finding.code, target_url, *finding.observation_ids)
            problem_text = _aeo_problems.get(finding.code, f"AEO check {finding.code}")
            basis = (
                "No matching answer-first page or direct answer observed in audited site HTML"
                if finding.code in {"missing_page", "missing_direct_answer"}
                else _md(finding.observed_evidence or "UNKNOWN")
            )
            lines.append(
                f'- <a id="{ref}"></a> **{site_label}** `{ref}`: '
                f'{_md(target_url)}; `{finding.code}`; '
                f'recorded basis: {basis}.'
            )
            lines.append(
                f"- **{site_label}:** AEO (`{finding.code}`): {_md(problem_text)} at "
                f"{_md(target_url)}. Suggested technical change: {_md(finding.recommendation)}. "
                f"[Source record](#{ref})."
            )
        for finding in content.geo.readiness_findings:
            target_url = finding.affected_url or site_origin
            ref = _record_id("finding-geo", finding.code, target_url, finding.observed_evidence)
            lines.append(
                f'- <a id="{ref}"></a> **{site_label}** `{ref}`: '
                f'{_md(target_url)}; `{finding.code}`; '
                f'recorded basis: {_md(finding.observed_evidence or "UNKNOWN")}.'
            )
            lines.append(
                f"- **{site_label}:** GEO (`{finding.code}`): {_md(finding.problem)} at "
                f"{_md(target_url)}. Suggested technical change: {_md(finding.suggested_correction)}. "
                f"[Source record](#{ref})."
            )
        if not (content.site.findings or content.aeo.findings or content.geo.readiness_findings):
            page_refs = ", ".join(f"[Source record](#{_record_id('page', page.url)})"
                                  for page in content.site.pages)
            lines.append(
                f"- **{site_label}:** The bounded site audit generated no site, AEO or GEO findings; "
                + ("unapproved pages were not inspected. " if live_mode else "live website condition is UNKNOWN. ")
                + (page_refs or "No page record is available.")
            )
    else:
        lines.append("- Website observation: UNKNOWN; no website was supplied.")
        lines.append(f"- Website findings: UNKNOWN; no website was supplied. [Source record](#{profile_ref}).")

    lines.extend([
        "",
        "## Section 2: Acquisition action",
        "",
        f"Status: `{decision.status}`. The existing M4 rules were used unchanged.",
        f"Input profile: [Source record](#{profile_ref}).",
    ])
    for item in observations:
        lines.append(f"Input attestation: [Source record](#{item.observation_id}).")
    if decision.primary is None:
        lines.append("Primary recommendation: none yet. Eligible demand evidence is insufficient for an acquisition action.")
    else:
        raise RuntimeError("This review input path cannot substantiate a primary recommendation without verified demand")

    lines.extend([
        "",
        "Evidence still missing:",
        ("- Customer-demand evidence: UNKNOWN; no observations were supplied."
         if not observations else
         "- Customer-demand evidence: UNKNOWN; no independently verified demand observations were supplied."),
        "- Independent customer demand: UNKNOWN; founder attestations are not source verification.",
        ("- Live website condition: bounded live fetch of approved URLs only; authorization is self-declared and does not prove site ownership."
         if live_mode else
         ("- Live website condition: UNKNOWN; only supplied HTML fixtures were analyzed."
          if content else "- Live website condition: UNKNOWN; no website was supplied.")),
        "- Authorized public demand discovery with live URL, excerpt and freshness verification: missing.",
        "- Verified channel permission and zero-spend eligibility for an acquisition placement: missing.",
        "- Visits, conversions, customers and causal impact: UNKNOWN; none were measured.",
        "- No publishing, outreach, purchase, production write or external action occurred.",
        "",
        "What to bring next:",
        "- Paste 3 to 5 real customer questions or complaints with no names or contact details, labeled **founder-attested** (via `--attestations` with `minimized_by_founder: true`).",
        "- Include the exact wording of the recurring question or pain point so AEO checks can test whether your approved pages answer it directly.",
        "- Keep personal identifiers out (no emails, phone numbers, @handles, profile URLs, or personal names); M4 acquisition actions remain `none yet` until independent demand verification exists.",
        "",
        "Founder-attested context (self-declared, not verified demand):",
        (f'- <a id="{profile_ref}"></a> **founder-attested** `{profile_ref}`: '
         f'{_md(profile.name)}; {_md(profile.description)}; '
         f'website: {_md(profile.website or "none")}. '
         "Business details were confirmed for this review, not independently verified."),
    ])
    for item in observations:
        lines.append(
            f'- <a id="{item.observation_id}"></a> **founder-attested** `{item.observation_id}`: '
            f"{_md(item.claim)} Source record: `{item.source_id}`; independently verified: no; verified demand: no."
        )
        lines.append(
            f"- **founder-attested:** {_md(item.claim)} "
            f"[Source record](#{item.observation_id}). This is not independently verified demand."
        )
    lines.extend([
        "- Automated minimization checks catch some identifiers but cannot guarantee removal of personal data; founder review is required.",
        "",
    ])
    return "\n".join(lines)


def run_client_review(profile: ProductProfile, *, permission_path: Path | None = None,
                      fixture_path: Path | None = None,
                      attestations_path: Path | None = None,
                      live_site: bool = False) -> ClientReviewResult:
    """Use in-memory inputs, temporary local M2 storage, fixture/live M3 and unchanged M4."""
    if not profile.confirmed:
        raise PermissionError("Founder confirmation is required")
    business_id(profile.identifier)
    content = None
    if profile.website is None:
        if permission_path is not None or fixture_path is not None or live_site:
            raise ValueError("Website-free review must not include a site permission, fixture or live-site flag")
    elif live_site:
        if permission_path is None or fixture_path is not None:
            raise PermissionError("Live website review requires permission and forbids local fixture files")
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
            expected_purpose = "live_site_audit" if live_site else "offline_fixture_audit"
            if permission.purpose != expected_purpose:
                raise PermissionError("Website permission purpose does not match review mode")
            if (permission.business_id != profile.identifier or
                    permission.origin != origin(submitted_url) or
                    submitted_url not in permission.approved_pages):
                raise PermissionError("Website permission does not match the confirmed profile and exact URL")
            fetcher = _ScopedLiveSiteFetcher(permission) if live_site else _fixture_fetcher(fixture_path, permission)
            audit_pages = [url for url in permission.approved_pages
                           if url not in {permission.origin + "/robots.txt",
                                          permission.origin + "/sitemap.xml"}]
            content = analyze_business(profile, store, fetcher=fetcher,
                                       approved_origin=permission.origin,
                                       approved_urls=audit_pages)
    finally:
        store.close()
    site_mode = ("approved_live" if live_site else "fixture") if content else "unknown"
    context = DecisionContext(profile=profile, observations=observations, content=content,
                              discovery_status="not_run", site_evidence_mode=site_mode)
    decision = AcquisitionDecisionEngine().decide(context)
    return ClientReviewResult(_report(profile, observations, content, decision, site_evidence_mode=site_mode),
                              decision.status, len(observations), len(content.site.pages) if content else 0)

