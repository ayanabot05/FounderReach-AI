"""Bounded, dated Hacker News research via the documented Algolia API."""
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import html
import json
import logging
import re
import time
import urllib.error
import urllib.parse
import urllib.request

from founderreach.config import settings
from founderreach.connectors.base import BaseConnector
from founderreach.models import DiscussionItem, ProductProfile
from founderreach.source_registry import SourceRegistry

logger = logging.getLogger(__name__)


class DiscoveryUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class QueryDiagnostic:
    query: str
    page: int
    status: str
    returned_hits: int = 0
    detail: str = ""


@dataclass
class DiscoveryBatch:
    source_key: str
    status: str
    items: list[DiscussionItem] = field(default_factory=list)
    diagnostics: list[QueryDiagnostic] = field(default_factory=list)
    request_count: int = 0
    window_start: datetime | None = None
    window_end: datetime | None = None
    source_policy_version: int | None = None


class HackerNewsConnector(BaseConnector):
    def __init__(self, registry: SourceRegistry | None = None):
        super().__init__("Hacker News")
        self.api_base = settings.HN_API_BASE
        parsed = urllib.parse.urlparse(self.api_base)
        if parsed.scheme != "https" or parsed.hostname != "hn.algolia.com" or parsed.path.rstrip("/") != "/api/v1":
            raise ValueError("HN API endpoint must be the documented HTTPS Algolia endpoint")
        self.user_agent = "FounderReach-AI/1.0 (bounded public research)"
        self.registry = registry or SourceRegistry()
        self._request_times: deque[float] = deque()

    def is_enabled(self) -> bool:
        return settings.HN_ENABLED

    def _clean_html(self, raw_html: str) -> str:
        text = re.sub(r"<p(?:\s[^>]*)?>", "\n\n", raw_html or "", flags=re.I)
        text = re.sub(r"<[^>]+>", " ", text)
        return re.sub(r"\s+", " ", html.unescape(text)).strip()

    def _fetch_page(self, query: str, page: int, start: datetime, end: datetime,
                    hits_per_page: int = 20) -> dict:
        params = {
            "query": query, "tags": "comment", "page": page, "hitsPerPage": hits_per_page,
            "numericFilters": f"created_at_i>={int(start.timestamp())},created_at_i<{int(end.timestamp())}",
        }
        url = f"{self.api_base}/search_by_date?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status != 200:
                raise urllib.error.HTTPError(url, response.status, "Search failed", response.headers, None)
            return json.loads(response.read(1_000_000).decode("utf-8"))

    def _reserve_request(self, hourly_limit: int) -> bool:
        now = time.monotonic()
        while self._request_times and now - self._request_times[0] >= 3600:
            self._request_times.popleft()
        if len(self._request_times) >= hourly_limit:
            return False
        self._request_times.append(now)
        return True

    @staticmethod
    def _queries(profile: ProductProfile, maximum: int) -> list[str]:
        return list(dict.fromkeys(q.strip() for q in profile.keywords + profile.pain_points
                                  if q.strip()))[:maximum]

    def discover(self, product: ProductProfile, limit: int = 30, *,
                 start: datetime | None = None, end: datetime | None = None) -> DiscoveryBatch:
        end = end or datetime.now(timezone.utc)
        start = start or end - timedelta(days=365)
        if start.tzinfo is None or end.tzinfo is None or start >= end:
            raise ValueError("A valid timezone-aware HN date window is required")
        batch = DiscoveryBatch("hackernews", "unavailable", window_start=start, window_end=end)
        if not self.is_enabled():
            batch.status = "disabled"
            return batch
        policy = self.registry.get("hackernews")
        if not policy or policy.decision("research") != "allowed":
            batch.status = "permission_blocked"
            return batch
        batch.source_policy_version = policy.version
        queries = self._queries(product, policy.max_queries_per_run)
        if not queries:
            batch.status = "no_queries"
            return batch

        page_counts = {query: policy.max_pages_per_query for query in queries}
        seen: set[str] = set()
        failures = 0
        successes = 0
        # Page-first order gives every query its first page before deeper paging.
        for page in range(policy.max_pages_per_query):
            for query in queries:
                if page >= page_counts[query]:
                    continue
                if not self._reserve_request(policy.max_requests_per_hour):
                    batch.diagnostics.append(QueryDiagnostic(query, page, "budget_exhausted"))
                    failures += 1
                    continue
                batch.request_count += 1
                try:
                    payload = self._fetch_page(query, page, start, end)
                    if not isinstance(payload, dict) or not isinstance(payload.get("hits"), list):
                        raise ValueError("Malformed HN response")
                    hits = payload["hits"]
                    count = payload.get("nbPages")
                    if not isinstance(count, int) or count < 0:
                        raise ValueError("Missing HN pagination metadata")
                    page_counts[query] = min(count, policy.max_pages_per_query)
                    batch.diagnostics.append(QueryDiagnostic(query, page, "ok", len(hits)))
                    successes += 1
                except urllib.error.HTTPError as exc:
                    state = "rate_limited" if exc.code == 429 else f"http_{exc.code}"
                    batch.diagnostics.append(QueryDiagnostic(query, page, state))
                    page_counts[query] = page
                    failures += 1
                    continue
                except (urllib.error.URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
                    batch.diagnostics.append(QueryDiagnostic(query, page, "source_error", detail=type(exc).__name__))
                    page_counts[query] = page
                    failures += 1
                    continue
                for hit in hits:
                    if not isinstance(hit, dict):
                        continue
                    native_id = str(hit.get("objectID") or "")
                    if not native_id.isdigit() or native_id in seen:
                        continue
                    seen.add(native_id)
                    text = self._clean_html(hit.get("comment_text") or "")
                    if len(text) < 50:
                        continue
                    created_at = None
                    if hit.get("created_at"):
                        try:
                            created_at = datetime.fromisoformat(hit["created_at"].replace("Z", "+00:00"))
                        except (TypeError, ValueError):
                            pass
                    if created_at is None or created_at.tzinfo is None or not start <= created_at < end:
                        continue
                    batch.items.append(DiscussionItem(
                        id=f"hn_{native_id}", platform="Hacker News",
                        original_url=f"https://news.ycombinator.com/item?id={native_id}",
                        title=hit.get("story_title") or hit.get("title") or "Hacker News Discussion",
                        author=hit.get("author"), text=text, created_at=created_at,
                        raw_metadata={"story_id": hit.get("story_id"), "parent_id": hit.get("parent_id"),
                                      "query": query, "page": page}))
        batch.items = batch.items[:limit]
        batch.status = "partial" if successes and failures else "success" if successes else "unavailable"
        return batch

    def search(self, product: ProductProfile, limit: int = 30) -> list[DiscussionItem]:
        batch = self.discover(product, limit)
        if batch.status in ("unavailable", "permission_blocked", "no_queries"):
            raise DiscoveryUnavailable(f"HN discovery state: {batch.status}")
        return batch.items
