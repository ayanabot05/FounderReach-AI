from datetime import datetime, timedelta, timezone
import urllib.error

import pytest

from founderreach.connectors.hackernews import HackerNewsConnector, DiscoveryUnavailable
from founderreach.evidence import EvidenceObservation, founder_attestation, observation_id
from founderreach.engine import OpportunityFinderEngine
from founderreach.models import DiscussionItem, SourceVerification
from founderreach.placements import placement_from_evidence
from founderreach.profiles import load_profile
from founderreach.research_store import ResearchStore
from founderreach.source_registry import SourcePolicy, SourceRegistry, REGISTRY_DIR
from founderreach.validation.verifier import SourceVerifier


NOW = datetime.now(timezone.utc)
TEXT = "I am an independent consultant and my clients miss appointment bookings. Looking for a scheduling app to avoid no shows."


class HistoricalApprovedFixtureRegistry:
    """Model the v1 approved state only for network-free connector behavior tests."""
    def get(self, key):
        if key != "hackernews":
            return None
        return SourcePolicy.model_validate_json((REGISTRY_DIR / "hackernews.v1.json").read_text(encoding="utf-8"))


def public_evidence(business="scheduleflow", *, verified=True, old=False):
    source = "hacker-news:hn_44"
    return EvidenceObservation(
        observation_id=observation_id(business, source, "customer_need", TEXT),
        business_id=business, source_id=source, source_key="hackernews", source_policy_version=1,
        kind="customer_need", provenance="public_api",
        source_url="https://news.ycombinator.com/item?id=44", excerpt=TEXT, claim=TEXT,
        published_at=NOW - timedelta(days=200 if old else 2),
        verification_state="verified" if verified else "failed",
        verification_method="hn_exact_quote" if verified else None,
        verified_at=NOW - timedelta(hours=1) if verified else None,
        verification_expires_at=NOW + timedelta(hours=1) if verified else None,
        verification_failure=None if verified else "quote_mismatch",
        relevance_state="matched", freshness_state="evergreen" if old else "timely",
        permission_state="allowed", allowed_uses=["research", "owned_content_planning"],
        routes=["demand_evidence", "owned_content_research"])


def test_source_registry_fail_closed_on_expiry_and_unknown():
    registry = SourceRegistry()
    policy = registry.get("hackernews")
    assert policy.version == 2 and policy.status == "review_required"
    assert policy.decision("research") == "unknown"
    assert policy.decision("owned_content_planning") == "unknown"
    assert policy.max_requests_per_hour == 0
    assert registry.decision("invented_source", "research") == "unknown"


def test_current_hn_policy_blocks_live_discovery_before_network(monkeypatch):
    connector = HackerNewsConnector()
    monkeypatch.setattr(connector, "_fetch_page", lambda *args, **kwargs: pytest.fail("network request"))
    batch = connector.discover(load_profile("ayana"), start=NOW - timedelta(days=7), end=NOW)
    assert batch.status == "permission_blocked" and batch.request_count == 0


def test_hn_date_window_fair_pages_dedupe_and_query_diagnostics(monkeypatch):
    connector = HackerNewsConnector(HistoricalApprovedFixtureRegistry())
    profile = load_profile("scheduleflow").model_copy(update={"keywords": ["alpha", "beta"], "pain_points": []})
    calls = []

    def fetch(query, page, start, end, hits_per_page=20):
        calls.append((query, page, start, end))
        return {"nbPages": 2, "hits": [{"objectID": "44", "comment_text": TEXT,
                "created_at": (NOW - timedelta(days=2)).isoformat(), "author": "person"}]}

    monkeypatch.setattr(connector, "_fetch_page", fetch)
    batch = connector.discover(profile, start=NOW - timedelta(days=30), end=NOW)
    assert batch.status == "success" and len(batch.items) == 1
    assert [(q, p) for q, p, *_ in calls] == [("alpha", 0), ("beta", 0), ("alpha", 1), ("beta", 1)]
    assert len(batch.diagnostics) == 4 and batch.request_count == 4
    assert batch.items[0].raw_metadata["query"] == "alpha"


def test_hn_partial_and_full_failure_not_empty_demand(monkeypatch):
    connector = HackerNewsConnector(HistoricalApprovedFixtureRegistry())
    profile = load_profile("scheduleflow").model_copy(update={"keywords": ["alpha", "beta"], "pain_points": []})

    def partial(query, page, start, end, hits_per_page=20):
        if query == "alpha":
            raise urllib.error.HTTPError("url", 429, "limit", {}, None)
        return {"nbPages": 1, "hits": []}

    monkeypatch.setattr(connector, "_fetch_page", partial)
    batch = connector.discover(profile, start=NOW - timedelta(days=1), end=NOW)
    assert batch.status == "partial" and batch.items == []
    assert any(d.status == "rate_limited" for d in batch.diagnostics)

    monkeypatch.setattr(connector, "_fetch_page", lambda *args: (_ for _ in ()).throw(TimeoutError()))
    batch = connector.discover(profile, start=NOW - timedelta(days=1), end=NOW)
    assert batch.status == "unavailable" and batch.items == []
    engine = OpportunityFinderEngine()
    engine.connectors = [connector]
    with pytest.raises(DiscoveryUnavailable):
        engine.find_opportunities(profile)


def test_hn_request_contains_dates_and_pagination(monkeypatch):
    connector = HackerNewsConnector(HistoricalApprovedFixtureRegistry())
    captured = []
    class Response:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, n): return b'{"nbPages":1,"hits":[]}'
    def open_request(request, timeout):
        captured.append(request.full_url)
        return Response()
    monkeypatch.setattr("urllib.request.urlopen", open_request)
    connector._fetch_page("appointment booking", 2, NOW - timedelta(days=7), NOW)
    from urllib.parse import parse_qs, urlparse
    parsed = urlparse(captured[0])
    query = parse_qs(parsed.query)
    assert parsed.netloc == "hn.algolia.com" and parsed.path.endswith("/search_by_date")
    assert query["page"] == ["2"] and query["query"] == ["appointment booking"]
    assert "created_at_i>=" in query["numericFilters"][0]


def test_hn_request_budget_fails_without_network(monkeypatch):
    import time
    connector = HackerNewsConnector(HistoricalApprovedFixtureRegistry())
    connector._request_times.extend([time.monotonic()] * 60)
    monkeypatch.setattr(connector, "_fetch_page", lambda *args: pytest.fail("budget allowed a network request"))
    profile = load_profile("scheduleflow").model_copy(update={"keywords": ["appointment"], "pain_points": []})
    batch = connector.discover(profile, start=NOW - timedelta(days=7), end=NOW)
    assert batch.status == "unavailable" and batch.request_count == 0
    assert batch.diagnostics[0].status == "budget_exhausted"


def test_verifier_explicit_failure_states_and_expiry(monkeypatch):
    verifier = SourceVerifier()
    url = "https://news.ycombinator.com/item?id=44"

    class Response:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def geturl(self): return url
        def read(self, n): return f"<html>{TEXT}</html>".encode()

    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: Response())
    good = verifier.verify_source(url, TEXT)
    assert good.status == "verified" and good.expires_at > good.checked_at
    assert public_evidence().current_verification_state(NOW + timedelta(days=1)) == "stale"
    mismatch = verifier.verify_source(url, "This detailed sentence is entirely absent from the source document")
    assert mismatch.status == "quote_mismatch"
    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: (_ for _ in ()).throw(
        urllib.error.HTTPError(url, 404, "not found", {}, None)))
    assert verifier.verify_source(url, TEXT).status == "not_found"
    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: (_ for _ in ()).throw(TimeoutError()))
    assert verifier.verify_source(url, TEXT).status == "network_error"
    assert verifier.verify_source("https://example.com/item?id=44", TEXT).status == "unsupported_source"


def test_attestation_review_and_cross_business_isolation(tmp_path):
    store = ResearchStore(tmp_path / "research.db")
    attested = founder_attestation(business="ayana", native_id="founder-1", excerpt=TEXT,
                                   claim=TEXT, attested_by="founder")
    store.save_observation(attested)
    assert store.list_observations("scheduleflow") == []
    with pytest.raises(LookupError):
        store.record_review("scheduleflow", attested.observation_id, "reviewer", "confirmed", "checked")
    reviewed = store.record_review("ayana", attested.observation_id, "reviewer", "confirmed", "checked")
    assert reviewed.verification_state == "attested" and reviewed.provenance == "founder_attested"
    assert len(store.list_reviews("ayana", attested.observation_id)) == 1
    with pytest.raises(ValueError):
        store.record_review("ayana", attested.observation_id, "reviewer", "confirmed", "again")
    with pytest.raises(ValueError):
        EvidenceObservation.model_validate(attested.model_dump() | {"verification_state": "verified"})
    with pytest.raises(ValueError):
        store.save_observation(attested)
    with pytest.raises(ValueError):
        store.save_observation(reviewed.model_copy(update={"provenance": "independent_review"}))


def test_expired_permission_and_retention_fail_closed(tmp_path):
    evidence = public_evidence()
    assert evidence.may_support("owned_content_planning") is True
    expired = evidence.model_copy(update={"permission_state": "expired", "allowed_uses": []})
    assert expired.may_support("owned_content_planning") is False
    store = ResearchStore(tmp_path / "research.db")
    old = evidence.model_copy(update={"observed_at": NOW - timedelta(days=400)})
    store.save_observation(old)
    store.log_query_run("scheduleflow", "hackernews", {"status": "success", "diagnostics": []})
    assert store.prune_retention(SourceRegistry(), NOW) == 1
    assert store.list_observations("scheduleflow") == []
    assert len(store.list_query_runs("scheduleflow")) == 1


def test_quality_states_are_independent():
    verified = public_evidence()
    uncertain = verified.model_copy(update={"relevance_state": "uncertain", "review_state": "pending"})
    blocked = verified.model_copy(update={"permission_state": "blocked", "allowed_uses": []})
    attested = founder_attestation(business="ayana", native_id="one", excerpt=TEXT,
                                   claim=TEXT, attested_by="founder")
    assert verified.current_verification_state(NOW) == "verified"
    assert verified.current_verification_state(NOW + timedelta(days=2)) == "stale"
    assert uncertain.current_verification_state(NOW) == "verified" and uncertain.relevance_state == "uncertain"
    assert blocked.current_verification_state(NOW) == "verified" and blocked.permission_state == "blocked"
    assert attested.verification_state == "attested" and attested.provenance == "founder_attested"
    assert not any(x.may_support("publication") for x in (verified, uncertain, blocked, attested))


def test_placement_requires_real_verified_evidence_and_no_contact():
    evidence = public_evidence()
    with pytest.raises(ValueError):
        placement_from_evidence(evidence, kind="newsletter", target_name="Unknown",
                                target_url=str(evidence.source_url), rationale="Possible fit")
    candidate = evidence.model_copy(update={"kind": "placement_opportunity"})
    lead = placement_from_evidence(candidate, kind="media", target_name="Observed publisher",
                                   target_url=str(candidate.source_url), rationale="Visible editorial listing")
    assert lead.stage == "research_only" and lead.permission_state == "unknown"
    assert lead.supporting_observation_id == candidate.observation_id


def test_engine_normalized_evidence_two_businesses_and_query_log(tmp_path, monkeypatch):
    store = ResearchStore(tmp_path / "research.db")
    engine = OpportunityFinderEngine(store)
    class Fixture:
        name = "fixture"
        def is_enabled(self): return True
        def search(self, product, limit):
            return [DiscussionItem(id="hn_44", platform="Hacker News",
                original_url="https://news.ycombinator.com/item?id=44", text=TEXT,
                created_at=NOW - timedelta(days=200))]
    engine.connectors = [Fixture()]
    monkeypatch.setattr("founderreach.engine.source_verifier.verify_source", lambda url, excerpt:
        SourceVerification(verified=False, http_status=200, verified_url=url,
                           evidence_excerpt=excerpt, status="quote_mismatch"))
    for name in ("ayana", "scheduleflow"):
        engine.find_opportunities(load_profile(name), min_score=0, actionable_only=False, persist=True)
    ayana = store.list_observations("ayana")
    saas = store.list_observations("scheduleflow")
    assert len(ayana) == len(saas) == 1
    assert ayana[0].observation_id != saas[0].observation_id
    assert saas[0].freshness_state == "evergreen" and saas[0].verification_state == "failed"
    assert "owned_content_research" in saas[0].routes
    assert saas[0].may_support("community_reply") is False


def test_engine_logs_successful_empty_discovery_separately(tmp_path):
    from founderreach.connectors.hackernews import DiscoveryBatch, QueryDiagnostic
    store = ResearchStore(tmp_path / "research.db")
    engine = OpportunityFinderEngine(store)
    class EmptySource:
        name = "fixture"
        def is_enabled(self): return True
        def discover(self, product, limit):
            return DiscoveryBatch("hackernews", "success", [],
                                  [QueryDiagnostic("appointments", 0, "ok", 0)], 1, NOW - timedelta(days=1), NOW, 1)
    engine.connectors = [EmptySource()]
    assert engine.find_opportunities(load_profile("scheduleflow"), persist=True) == []
    runs = store.list_query_runs("scheduleflow")
    assert runs[0]["status"] == "success" and runs[0]["diagnostics"][0]["query"] == "appointments"
