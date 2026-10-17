from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from founderreach.ai.cost_tracker import BudgetExceededError, CostTracker
from founderreach.db import Database
from founderreach.engine import OpportunityFinderEngine
from founderreach.identity import business_id, opportunity_id, source_id
from founderreach.models import DiscussionItem, SourceVerification
from founderreach.profiles import load_profile
from founderreach.research_store import ResearchStore
from founderreach.recommendations import recommend
from founderreach.routing import route_signal
from founderreach.self_service_store import SelfServiceStore
from founderreach.web.app import get_budget, get_opportunities, submit_feedback, FeedbackRequest
from founderreach.web.self_service_app import create_app, ApprovalRequest


class FixtureConnector:
    name = "fixture"

    def __init__(self, discussion):
        self.discussion = discussion

    def is_enabled(self):
        return True

    def search(self, product, limit=25):
        return [self.discussion]


def discussion(text, age=2):
    return DiscussionItem(id="hn_4242", platform="Hacker News",
        original_url="https://news.ycombinator.com/item?id=4242", text=text,
        created_at=datetime.now(timezone.utc) - timedelta(days=age))


CareFlow = "I am an NRI. My elderly parents live alone in India. How do people handle daily medicine reminders and regular check in calls? I worry about an emergency."
SAAS = "I am an independent consultant. My clients miss appointment bookings and I waste time on back and forth scheduling. Looking for a scheduling app to avoid no shows."


def test_stable_ids_and_two_businesses_can_preserve_one_source_url(tmp_path, monkeypatch):
    store = ResearchStore(tmp_path / "research.db")
    engine = OpportunityFinderEngine(store)
    monkeypatch.setattr("founderreach.engine.source_verifier.verify_source",
        lambda url, excerpt: SourceVerification(verified=True, http_status=200,
                                                verified_url=url, evidence_excerpt=excerpt))
    results = []
    for key, text in (("careflow", CareFlow), ("scheduleflow", SAAS)):
        engine.connectors = [FixtureConnector(discussion(text))]
        result = engine.find_opportunities(load_profile(key), min_score=60, persist=True)[0]
        results.append(result)
        assert result.business_id == business_id(key)
        assert result.source_id == source_id("Hacker News", "hn_4242")
        assert result.id == opportunity_id(key, result.source_id)
        assert result.suggested_response == ""
    assert results[0].id != results[1].id
    assert results[0].original_url == results[1].original_url
    assert len(store.list_business("careflow")) == len(store.list_business("scheduleflow")) == 1
    store.save(results[0].model_copy(update={"author": "customer_handle"}))
    assert store.list_business("careflow")[0].author is None
    alias_id = source_id("Hacker News", "other-native-id")
    with pytest.raises(ValueError):
        store.save(results[0].model_copy(update={"source_id": alias_id,
                                            "id": opportunity_id("careflow", alias_id)}))
    updated = load_profile("careflow").model_copy(update={"version": 2})
    engine.connectors = [FixtureConnector(discussion(CareFlow))]
    refreshed = engine.find_opportunities(updated, min_score=60, persist=True)[0]
    assert refreshed.id == results[0].id
    assert refreshed.profile_version == 2
    assert store.list_business("careflow")[0].profile_version == 2


def test_unverified_and_old_evidence_remain_research_without_reply(tmp_path, monkeypatch):
    store = ResearchStore(tmp_path / "research.db")
    engine = OpportunityFinderEngine(store)
    engine.connectors = [FixtureConnector(discussion(SAAS, age=365))]
    monkeypatch.setattr("founderreach.engine.source_verifier.verify_source",
        lambda url, excerpt: SourceVerification(verified=False, http_status=200,
                                                verified_url=url, evidence_excerpt=excerpt))
    result = engine.find_opportunities(load_profile("scheduleflow"), min_score=50,
                                       actionable_only=False, persist=True)[0]
    assert result.classification == "RESEARCH_INSIGHT"
    assert result.source_status == "SOURCE_UNVERIFIED"
    assert "demand_evidence" in result.signal_routes
    assert "community_reply" not in result.signal_routes
    assert result.suggested_response == ""
    assert store.list_business("scheduleflow")[0].id == result.id
    assert engine.find_opportunities(load_profile("scheduleflow"), min_score=50,
                                     actionable_only=True, persist=False) == []


def test_implicit_or_invalid_persistence_is_rejected():
    with pytest.raises(PermissionError):
        OpportunityFinderEngine().find_opportunities(load_profile("careflow"), persist=True)
    with pytest.raises(ValueError):
        business_id("../careflow")


def test_permission_blocked_reply_keeps_demand_signal(tmp_path, monkeypatch):
    profile = load_profile("scheduleflow").model_copy(update={
        "allowed_acquisition_channels": ["demand_evidence", "owned_channel", "community_reply"]})
    item = discussion(SAAS)
    route = route_signal(item, profile, True, True, True)
    assert "demand_evidence" in route.routes
    assert "community_reply" in route.routes
    assert route.community_reply_eligible is False
    assert any("permission" in reason for reason in route.reasons)
    engine = OpportunityFinderEngine(ResearchStore(tmp_path / "research.db"))
    engine.connectors = [FixtureConnector(item)]
    monkeypatch.setattr("founderreach.engine.source_verifier.verify_source",
        lambda url, excerpt: SourceVerification(verified=True, http_status=200,
                                                verified_url=url, evidence_excerpt=excerpt))
    result = engine.find_opportunities(profile, min_score=50, persist=True)[0]
    assert result.classification == "ACTIONABLE_OPPORTUNITY"
    assert result.suggested_response == ""
    assert engine.research_store.list_business("scheduleflow")[0].id == result.id
    recommendation = recommend(profile, {"url": str(profile.website), "title": "ScheduleFlow", "description": profile.description}, finder=engine)
    assert any(evidence["type"] == "verified_public_discussion" for evidence in recommendation["evidence"])
    assert recommendation["execution_mode"] == "MANUAL_ONLY"


def test_zero_new_spend_is_hard_gate():
    tracker = CostTracker()
    assert tracker.get_spending_summary()["authorized_new_spend_inr"] == 0
    assert tracker.check_can_spend(0) is True
    with pytest.raises(BudgetExceededError):
        tracker.check_can_spend(0.001)
    with pytest.raises(BudgetExceededError):
        tracker.record_usage("test", "paid", cost_usd=0.001)


def test_legacy_routes_and_unsigned_approval_fail_closed(tmp_path):
    legacy_db = Database(tmp_path / "legacy.db")
    with pytest.raises(PermissionError):
        legacy_db.save_opportunity(None)
    with pytest.raises(PermissionError):
        legacy_db.update_feedback("legacy", "relevant")
    with pytest.raises(HTTPException) as exc:
        get_opportunities()
    assert exc.value.status_code == 503
    with pytest.raises(HTTPException) as exc:
        get_budget()
    assert exc.value.status_code == 503
    with pytest.raises(HTTPException) as exc:
        submit_feedback(FeedbackRequest(id="x", feedback="relevant"))
    assert exc.value.status_code == 503
    store = SelfServiceStore(tmp_path / "self_service.db")
    with pytest.raises(PermissionError):
        store.approve(1, 1, 1, "forged", "2026-10-17T00:00:00Z")
    with pytest.raises(PermissionError):
        store.record_outcome(1, 1, 1, {"qualified_inquiries": 1})
    app = create_app(tmp_path / "prototype.db")
    route = next(route for route in app.routes if route.path.endswith("/{action_id}/approve"))
    with pytest.raises(HTTPException) as exc:
        route.endpoint(1, 1, ApprovalRequest(version_hash="forged"), session=None)
    assert exc.value.status_code == 503
