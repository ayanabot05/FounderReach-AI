"""Explicit-origin, bounded owned-site inventory and deterministic SEO audit."""
from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser
import hashlib
import json
import re
import time
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser
from xml.etree import ElementTree as ET

from pydantic import BaseModel, Field

from founderreach.models import ProductProfile
from founderreach.website import WebsiteFetcher, WebsiteFetchError, UnsafeWebsiteError

MAX_PAGES = 20
MAX_BYTES = 512_000


def origin(url: str) -> str:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.port not in (None, 443):
        raise UnsafeWebsiteError("Only approved HTTPS origins on the standard port are accepted")
    return f"https://{parsed.hostname.lower()}"


def canonical_url(url: str) -> str:
    parsed = urlsplit(url)
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path or "/", parsed.query, ""))


def same_origin_links(urls: list[str], site_origin: str) -> list[str]:
    result = []
    for url in urls:
        try:
            if origin(url) == site_origin:
                result.append(canonical_url(url))
        except (UnsafeWebsiteError, ValueError):
            continue
    return result


@dataclass(frozen=True)
class FetchOutcome:
    status: int
    content_type: str
    body: bytes
    final_url: str
    headers: dict[str, str] = field(default_factory=dict)


class ApprovedSiteFetcher:
    """Production fetch path; DNS validation and pinned TLS reuse M1's safe fetch primitives."""
    def __init__(self, approved_origin: str):
        self.approved_origin = origin(approved_origin)
        self._network = WebsiteFetcher()
        self.max_redirects = 2
        self.max_requests = 30
        self.max_duration_seconds = 60
        self.request_count = 0
        self.started_at = time.monotonic()

    def fetch(self, url: str) -> FetchOutcome:
        current = url
        for hop in range(self.max_redirects + 1):
            if origin(current) != self.approved_origin:
                raise UnsafeWebsiteError("Cross-origin website request or redirect blocked")
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
            return FetchOutcome(status, headers.get("content-type", ""), body, clean, headers)
        raise WebsiteFetchError("Too many redirects")


class FixtureSiteFetcher:
    """Network-free fixture adapter; the only test route for reserved/loopback hosts."""
    def __init__(self, pages: dict[str, tuple[int, str, str]]):
        self.pages = {canonical_url(url): value for url, value in pages.items()}
        self.calls: list[str] = []

    def fetch(self, url: str) -> FetchOutcome:
        url = canonical_url(url)
        self.calls.append(url)
        if url not in self.pages:
            raise MissingFixtureError("No fixture was supplied for this URL")
        record = self.pages[url]
        status, content_type, text = record[:3]
        headers = record[3] if len(record) > 3 else {}
        return FetchOutcome(status, content_type, text.encode("utf-8"), url, headers)


class MissingFixtureError(WebsiteFetchError):
    """A fixture omission is unknown, not an observed HTTP response."""


class SitePage(BaseModel):
    url: str
    status: int = 200
    title: str = ""
    description: str = ""
    headings: list[tuple[str, str]] = Field(default_factory=list)
    paragraphs: list[str] = Field(default_factory=list)
    links: list[str] = Field(default_factory=list)
    canonical: str | None = None
    robots_meta: str = ""
    x_robots_tag: str = ""
    jsonld: list[dict] = Field(default_factory=list)
    jsonld_errors: list[str] = Field(default_factory=list)

    @property
    def text(self) -> str:
        return " ".join([self.title, self.description] + [h[1] for h in self.headings] + self.paragraphs)


class SEOFinding(BaseModel):
    code: str
    affected_url: str
    observed_evidence: str
    problem: str
    severity: str
    suggested_correction: str
    confidence: float = Field(ge=0, le=1)
    limitations: str
    estimated_effort: str
    verification_method: str


class SiteAudit(BaseModel):
    business_id: str
    approved_origin: str
    pages: list[SitePage] = Field(default_factory=list)
    findings: list[SEOFinding] = Field(default_factory=list)
    fetch_errors: dict[str, str] = Field(default_factory=dict)
    sitemap_urls: list[str] = Field(default_factory=list)
    robots_observed: bool = False
    state: str = "complete"


class _PageParser(HTMLParser):
    def __init__(self, url: str):
        super().__init__(convert_charrefs=True)
        self.url = url
        self.title = ""
        self.description = ""
        self.headings: list[tuple[str, str]] = []
        self.paragraphs: list[str] = []
        self.links: list[str] = []
        self.canonical: str | None = None
        self.robots_meta = ""
        self.jsonld: list[dict] = []
        self.jsonld_errors: list[str] = []
        self._capture: str | None = None
        self._buffer = ""
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ("style", "noscript"):
            self._skip += 1
        if tag == "script":
            if attrs.get("type", "").lower() == "application/ld+json":
                self._capture = "jsonld"
                self._buffer = ""
            else:
                self._skip += 1
        if tag in ("title", "h1", "h2", "h3", "p") and not self._skip:
            self._capture = tag
            self._buffer = ""
        if tag == "meta":
            name = (attrs.get("name") or "").lower()
            if name == "description":
                self.description = (attrs.get("content") or "").strip()[:500]
            if name == "robots":
                self.robots_meta = (attrs.get("content") or "").lower()
        if tag == "link" and "canonical" in (attrs.get("rel") or "").lower().split():
            self.canonical = urljoin(self.url, attrs.get("href") or "")
        if tag == "a" and attrs.get("href"):
            self.links.append(urljoin(self.url, attrs["href"]))

    def handle_data(self, data):
        if self._capture:
            self._buffer += data[:10_000]

    def handle_endtag(self, tag):
        if tag in ("style", "noscript") and self._skip:
            self._skip -= 1
        if tag == "script" and self._capture == "jsonld":
            try:
                value = json.loads(self._buffer)
                if isinstance(value, dict):
                    self.jsonld.append(value)
                elif isinstance(value, list):
                    self.jsonld.extend(x for x in value if isinstance(x, dict))
                else:
                    self.jsonld_errors.append("JSON-LD root must be an object or object list")
                for entry in self.jsonld:
                    if not entry.get("@context") or not (entry.get("@type") or entry.get("@graph")):
                        self.jsonld_errors.append("JSON-LD missing @context or @type/@graph")
            except (ValueError, TypeError):
                self.jsonld_errors.append("Invalid JSON-LD syntax")
            self._capture = None
        elif tag == self._capture:
            value = " ".join(self._buffer.split())
            if value:
                if tag == "title": self.title = value[:200]
                elif tag == "p": self.paragraphs.append(value[:1500])
                else: self.headings.append((tag, value[:300]))
            self._capture = None


def tokens(text: str) -> set[str]:
    return {x for x in re.findall(r"[a-z0-9]+", text.lower()) if len(x) > 2 and x not in
            {"the", "and", "for", "with", "that", "this", "you", "your", "our", "are", "how", "what"}}


class SiteAuditor:
    def __init__(self, fetcher, *, max_pages: int = MAX_PAGES):
        self.fetcher = fetcher
        self.max_pages = min(max_pages, MAX_PAGES)

    def audit(self, profile: ProductProfile, *, approved_origin: str,
              approved_urls: list[str]) -> SiteAudit:
        if not profile.confirmed:
            raise PermissionError("A confirmed profile is required")
        if profile.website is None:
            raise ValueError("A confirmed website is required for a site audit")
        site_origin = origin(str(profile.website))
        if origin(approved_origin) != site_origin:
            raise PermissionError("Origin must match the founder-confirmed website")
        if not approved_urls or len(approved_urls) > self.max_pages:
            raise ValueError("An explicit bounded URL inventory is required")
        if any(origin(url) != site_origin for url in approved_urls):
            raise UnsafeWebsiteError("Inventory contains an unapproved origin")
        if isinstance(self.fetcher, ApprovedSiteFetcher) and self.fetcher.approved_origin != site_origin:
            raise PermissionError("Fetcher approval does not match the business")
        result = SiteAudit(business_id=profile.identifier, approved_origin=site_origin)
        robots_url = site_origin + "/robots.txt"
        sitemap_url = site_origin + "/sitemap.xml"
        robots_lines: list[str] = []
        try:
            robots = self.fetcher.fetch(robots_url)
            if robots.status == 200 and "text/plain" in robots.content_type.lower() and len(robots.body) <= MAX_BYTES:
                robots_lines = robots.body.decode("utf-8", errors="replace").splitlines()
                result.robots_observed = True
                for line in robots_lines:
                    if line.lower().startswith("sitemap:"):
                        proposed = line.partition(":")[2].strip()
                        if origin(proposed) == site_origin:
                            sitemap_url = proposed
        except (WebsiteFetchError, UnsafeWebsiteError, ValueError) as exc:
            result.fetch_errors[robots_url] = type(exc).__name__
        parser = RobotFileParser()
        parser.parse(robots_lines)
        try:
            sitemap = self.fetcher.fetch(sitemap_url)
            if sitemap.status == 200 and "xml" in sitemap.content_type.lower() and len(sitemap.body) <= MAX_BYTES:
                if b"<!DOCTYPE" in sitemap.body.upper():
                    raise ValueError("DTD not allowed")
                root = ET.fromstring(sitemap.body)
                result.sitemap_urls = same_origin_links([node.text.strip() for node in root.iter()
                    if node.tag.endswith("loc") and node.text], site_origin)[:MAX_PAGES]
            else:
                result.findings.append(self._finding("missing_sitemap", sitemap_url,
                    f"HTTP {sitemap.status}; content type {sitemap.content_type}", "Sitemap was not available as XML",
                    "medium", "Provide an XML sitemap for the approved inventory", 0.9, "Check sitemap XML manually"))
        except MissingFixtureError:
            result.fetch_errors[sitemap_url] = "MissingFixtureError"
        except (WebsiteFetchError, UnsafeWebsiteError, ET.ParseError, ValueError) as exc:
            result.fetch_errors[sitemap_url] = type(exc).__name__
            result.findings.append(self._finding("missing_sitemap", sitemap_url, type(exc).__name__,
                "Sitemap could not be verified", "medium", "Provide a readable XML sitemap", 0.7,
                "Check sitemap retrieval and XML syntax"))
        inventory = list(dict.fromkeys(canonical_url(url) for url in approved_urls))
        for url in inventory:
            if result.robots_observed and not parser.can_fetch("FounderReach", url):
                result.findings.append(self._finding("robots_blocked", url, "robots.txt disallow rule",
                    "Approved page is blocked by robots directives", "high", "Review the disallow rule if indexing is intended",
                    0.95, "Recheck robots.txt as the same user agent"))
                continue
            try:
                response = self.fetcher.fetch(url)
                if response.status != 200:
                    raise WebsiteFetchError(f"HTTP {response.status}")
                if "text/html" not in response.content_type.lower():
                    raise WebsiteFetchError("Unsupported content type")
                if len(response.body) > MAX_BYTES:
                    raise WebsiteFetchError("Oversized HTML")
                if origin(response.final_url) != site_origin:
                    raise UnsafeWebsiteError("Cross-origin result")
                html = _PageParser(response.final_url)
                html.feed(response.body.decode("utf-8", errors="replace"))
                result.pages.append(SitePage(url=canonical_url(response.final_url), title=html.title,
                    description=html.description, headings=html.headings, paragraphs=html.paragraphs,
                    links=same_origin_links(html.links, site_origin),
                    canonical=canonical_url(html.canonical) if html.canonical else None,
                    robots_meta=html.robots_meta,
                    x_robots_tag=response.headers.get("x-robots-tag", "").lower(),
                    jsonld=html.jsonld, jsonld_errors=html.jsonld_errors))
            except (WebsiteFetchError, UnsafeWebsiteError, ValueError) as exc:
                result.fetch_errors[url] = str(exc)[:200]
                result.findings.append(self._finding("inaccessible_page", url, type(exc).__name__,
                    "Approved page could not be audited", "high", "Check accessibility and content type",
                    0.8, "Fetch the page with the same bounded client"))
        self._assess(result, inventory)
        result.state = "partial" if result.fetch_errors or any(x.code == "inaccessible_page" for x in result.findings) else "complete"
        return result

    @staticmethod
    def _finding(code, url, observed, problem, severity, correction, confidence, verification):
        return SEOFinding(code=code, affected_url=url, observed_evidence=observed[:500], problem=problem,
            severity=severity, suggested_correction=correction, confidence=confidence,
            limitations="Local read-only audit cannot establish search-engine indexing or ranking",
            estimated_effort="small" if severity == "low" else "medium", verification_method=verification)

    def _assess(self, audit: SiteAudit, inventory: list[str]):
        page_urls = {p.url for p in audit.pages}
        incoming = {url: 0 for url in page_urls}
        for page in audit.pages:
            for link in set(page.links):
                if link in incoming and link != page.url:
                    incoming[link] += 1
        for page in audit.pages:
            url = page.url
            if "noindex" in page.robots_meta or "noindex" in page.x_robots_tag:
                audit.findings.append(self._finding("noindex", url,
                    f"meta={page.robots_meta}; x-robots-tag={page.x_robots_tag}", "Page declares noindex",
                    "high", "Remove noindex only if indexing is intended", 0.99, "Inspect robots meta and HTTP response"))
            if not page.canonical or page.canonical != url:
                audit.findings.append(self._finding("canonical", url, str(page.canonical),
                    "Canonical is missing or points away from this inventory URL", "high",
                    "Set a deliberate canonical for the preferred page", 0.95, "Inspect canonical tag and final URL"))
            if not page.title or not page.description:
                audit.findings.append(self._finding("metadata", url, f"title={page.title!r}; description={page.description!r}",
                    "Title or meta description is missing", "medium", "Write a descriptive title and summary",
                    0.99, "Inspect rendered HTML head"))
            h1s = [text for tag, text in page.headings if tag == "h1"]
            if len(h1s) != 1:
                audit.findings.append(self._finding("heading_structure", url, f"H1 count: {len(h1s)}",
                    "Page should have one clear primary heading", "medium", "Use one descriptive H1",
                    0.99, "Inspect HTML heading structure"))
            if page.jsonld_errors:
                audit.findings.append(self._finding("invalid_jsonld", url, ", ".join(page.jsonld_errors),
                    "Structured data has invalid JSON syntax", "medium", "Correct the JSON-LD",
                    0.95, "Parse JSON-LD and validate type-specific fields"))
            if not page.jsonld:
                audit.findings.append(self._finding("missing_structured_data", url, "No JSON-LD object found",
                    "No structured data was observed", "low", "Assess appropriate schema before adding markup",
                    0.95, "Inspect JSON-LD in HTML"))
            if audit.sitemap_urls and url not in audit.sitemap_urls:
                audit.findings.append(self._finding("sitemap_omission", url, "URL absent from observed sitemap",
                    "Audited page is not listed in the sitemap", "low", "Add the preferred canonical URL if appropriate",
                    0.9, "Compare approved inventory with XML sitemap"))
            if url != audit.approved_origin + "/" and incoming.get(url, 0) == 0:
                audit.findings.append(self._finding("orphan_page", url, "No incoming links in approved inventory",
                    "Page appears orphaned within the audited inventory", "medium",
                    "Add a relevant internal link from an audited page", 0.7,
                    "Compare internal links across the approved inventory"))
        for index, left in enumerate(audit.pages):
            for right in audit.pages[index + 1:]:
                content_left = " ".join(left.paragraphs).lower().strip()
                content_right = " ".join(right.paragraphs).lower().strip()
                exact = bool(content_left and content_left == content_right)
                titles = tokens(left.title + " " + " ".join(h[1] for h in left.headings))
                other = tokens(right.title + " " + " ".join(h[1] for h in right.headings))
                competing = bool(titles and other and len(titles & other) / len(titles | other) >= 0.75)
                if exact or competing:
                    audit.findings.append(self._finding("duplicate_content" if exact else "competing_content",
                        right.url, f"Overlaps {left.url}", "Pages duplicate or compete for the same topic",
                        "medium", "Choose one preferred page or differentiate their intent", 0.9 if exact else 0.7,
                        "Compare page text, titles and canonical targets"))
