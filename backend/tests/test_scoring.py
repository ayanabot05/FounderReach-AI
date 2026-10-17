import pytest
from datetime import datetime, timezone, timedelta
from founderreach.models import DiscussionItem, ProductProfile
from founderreach.validation.scorer import opportunity_scorer
from founderreach.validation.intent import intent_classifier
from founderreach.profiles import load_profile

CAREFLOW_PROFILE = load_profile("careflow")

def test_intent_active_solution_seeker():
    text = "How do you guys check in on your elderly parents living alone in India? Looking for an app or service recommendations."
    category, score, reason = intent_classifier.classify(text, CAREFLOW_PROFILE)
    assert category == "Active Solution Seeker"
    assert score == 20.0

def test_intent_personal_experiencer():
    text = "My mother lives alone in Hyderabad and forgotten to take her medicine last week. It was terrifying."
    category, score, reason = intent_classifier.classify(text, CAREFLOW_PROFILE)
    assert "Experiencer" in category
    assert score >= 15.0

def test_intent_offtopic_tech():
    text = "The meta api latency issues are causing webhook dropped packets in our javascript framework."
    category, score, reason = intent_classifier.classify(text, CAREFLOW_PROFILE)
    assert category == "Off-Topic / Technical Discussion"
    assert score <= 5.0

def test_scoring_high_relevance_discussion():
    discussion = DiscussionItem(
        id="test_high",
        platform="Hacker News",
        original_url="https://news.ycombinator.com/item?id=999991",
        text=(
            "I am an NRI living in the US while my elderly parents live alone in India. "
            "How do people handle daily medicine reminders and regular check in calls? "
            "I worry constantly if they had a fall or emergency in the house alone."
        ),
        created_at=datetime.now(timezone.utc) - timedelta(days=5)
    )
    score = opportunity_scorer.score(discussion, CAREFLOW_PROFILE)
    assert score.problem_fit == 30.0
    assert score.customer_fit == 20.0
    assert score.expressed_intent == 20.0
    assert score.recency == 15.0
    assert score.evidence_quality == 15.0
    assert score.total_score == 100.0

def test_scoring_irrelevant_discussion():
    discussion = DiscussionItem(
        id="test_low",
        platform="Hacker News",
        original_url="https://news.ycombinator.com/item?id=999992",
        text="Rust compiler performance has dramatically improved with the new borrow checker release.",
        created_at=datetime.now(timezone.utc) - timedelta(days=200)
    )
    score = opportunity_scorer.score(discussion, CAREFLOW_PROFILE)
    assert score.total_score < 50.0
    assert score.problem_fit <= 5.0

def test_negative_keyword_penalty():
    discussion = DiscussionItem(
        id="test_neg",
        platform="Hacker News",
        original_url="https://news.ycombinator.com/item?id=999993",
        text="Looking for bulk sms marketing to spam elderly parents with commercial crypto ads.",
        created_at=datetime.now(timezone.utc)
    )
    score = opportunity_scorer.score(discussion, CAREFLOW_PROFILE)
    assert "Penalized -10" in score.justification["problem_fit"]
