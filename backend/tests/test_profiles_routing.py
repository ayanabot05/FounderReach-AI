from datetime import datetime, timedelta, timezone
import json

import pytest
from pydantic import ValidationError

from founderreach.engine import OpportunityFinderEngine
from founderreach.models import DiscussionItem, ProductProfile, SourceVerification
from founderreach.profiles import load_profile
from founderreach.routing import route_signal
from founderreach.validation.intent import intent_classifier
from founderreach.validation.scorer import opportunity_scorer


CareFlow_TEXT = ("I am an NRI living in the US while my elderly parents live alone in India. "
              "How do people handle daily medicine reminders and regular check in calls? "
              "I worry constantly if they had a fall or emergency in the house alone.")
SAAS_TEXT = ("I am an independent consultant. My clients miss appointment bookings and "
             "I waste time on back and forth scheduling. Looking for a scheduling app "
             "to avoid no show reminders.")


def item(text, id="sample", age=2):
    return DiscussionItem(id=id, platform="Hacker News", original_url=f"https://news.ycombinator.com/item?id={id}",
                          text=text, created_at=datetime.now(timezone.utc) - timedelta(days=age))


def test_confirmed_profiles_load_and_suggestions_cannot_drive_engine(tmp_path):
    careflow, saas = load_profile("careflow"), load_profile("scheduleflow")
    assert careflow.name == "Synthetic Care" and saas.name == "ScheduleFlow"
    assert careflow.confirmed and saas.confirmed
    with pytest.raises(ValueError):
        load_profile("../careflow")
    (tmp_path / "draft.json").write_text(json.dumps({"identifier": "draft", "name": "Draft", "website": "https://example.com", "description": "x"}))
    with pytest.raises(ValueError):
        load_profile("draft", tmp_path)
    with pytest.raises(ValueError):
        OpportunityFinderEngine().find_opportunities(ProductProfile(name="Draft", website="https://example.com", description="x"), persist=False)


def test_profile_schema_and_positive_negative_matching():
    with pytest.raises(ValidationError):
        ProductProfile(identifier="bad", confirmed=True, name="Bad", website="x", description="x", problem_patterns=["["])
    careflow, saas = load_profile("careflow"), load_profile("scheduleflow")
    assert opportunity_scorer.score(item(CareFlow_TEXT), careflow).problem_fit > opportunity_scorer.score(item(CareFlow_TEXT), saas).problem_fit
    assert opportunity_scorer.score(item(SAAS_TEXT), saas).problem_fit > opportunity_scorer.score(item(SAAS_TEXT), careflow).problem_fit
    assert intent_classifier.extract_direct_evidence(SAAS_TEXT, saas)[0]
    assert not intent_classifier.extract_direct_evidence(SAAS_TEXT, careflow)[0]
    assert not intent_classifier.extract_direct_evidence("Airline booking schedules are complex.", saas)[0]


def test_action_specific_freshness_and_approval():
    profile = load_profile("scheduleflow")
    old = route_signal(item(SAAS_TEXT, age=365), profile, True, True, True)
    assert "demand_evidence" in old.routes and "owned_channel" in old.routes
    assert not old.community_reply_eligible
    assert "partner_media" in old.routes
    assert any("current independent verification" in reason for reason in old.reasons)
    checked = route_signal(item(SAAS_TEXT, age=365), profile, True, True, True,
                           partner_verified_at=datetime.now(timezone.utc) - timedelta(days=2))
    assert not any("current independent verification" in reason for reason in checked.reasons)
    fresh = route_signal(item(SAAS_TEXT), profile, True, True, True,
                         source_permission=True, community_rules_checked=True, founder_approved=True)
    assert not fresh.community_reply_eligible  # profile disallows replies by default
    permitted = profile.model_copy(update={"allowed_acquisition_channels": profile.allowed_acquisition_channels + ["community_reply"]})
    assert route_signal(item(SAAS_TEXT), permitted, True, True, True,
                        source_permission=True, community_rules_checked=True, founder_approved=True).community_reply_eligible
    assert not route_signal(item(SAAS_TEXT), permitted, False, True, True,
                            source_permission=True, community_rules_checked=True, founder_approved=True).community_reply_eligible


def test_same_engine_switches_profiles_and_returns_honest_empty(monkeypatch):
    engine = OpportunityFinderEngine()
    class Connector:
        name = "fixture"
        def __init__(self, discussion): self.discussion = discussion
        def is_enabled(self): return True
        def search(self, product, limit=25): return [self.discussion]
    monkeypatch.setattr("founderreach.engine.source_verifier.verify_source",
                        lambda url, excerpt: SourceVerification(verified=True, http_status=200,
                        verified_url=url, evidence_excerpt=excerpt))
    for profile_id, text in (("careflow", CareFlow_TEXT), ("scheduleflow", SAAS_TEXT)):
        profile = load_profile(profile_id)
        engine.connectors = [Connector(item(text, id=profile_id))]
        results = engine.find_opportunities(profile, min_score=60, actionable_only=False, persist=False)
        assert len(results) == 1
        assert results[0].product_name == profile.name
        assert "demand_evidence" in results[0].signal_routes
        assert results[0].classification == "ACTIONABLE_OPPORTUNITY"
        assert "community_reply" not in results[0].signal_routes
        assert results[0].suggested_response == ""
    engine.connectors = [Connector(item("Rust compiler internals and build caching.", id="empty"))]
    assert engine.find_opportunities(load_profile("scheduleflow"), min_score=60, persist=False) == []
