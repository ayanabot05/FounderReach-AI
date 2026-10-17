import pytest
from datetime import datetime, timezone, timedelta
from founderreach.models import DiscussionItem, CustomerOpportunity
from founderreach.validation.intent import intent_classifier
from founderreach.validation.scorer import opportunity_scorer
from founderreach.profiles import load_profile

CAREFLOW_PROFILE = load_profile("careflow")

def test_regression_ceo_hn_47396347_markoff():
    """
    CEO Validation Case #1: HN 47396347 (Markoff)
    Discussion is genuine (URL exists), but author is venting about intergenerational
    child-care reciprocity and boomer parents not helping with kids.
    MUST NOT be classified as an ACTIONABLE_OPPORTUNITY for CAREFLOW.
    """
    text = (
        "TBH it was also expected trade - you will take care of elderly parents in exchange "
        "for their help with kids participation, so since boomer parents don't help they also "
        "can't expect help. My (divorced) parents (5+ and 2.5+ hours away by car) didn't help."
    )
    
    # 1. Direct evidence test: Must NOT find direct problem evidence
    has_direct_evidence, direct_sentence, rejection_reasons = intent_classifier.extract_direct_evidence(
        text, CAREFLOW_PROFILE
    )
    assert has_direct_evidence is False
    assert direct_sentence is None
    assert any("child-care reciprocity" in r or "No direct evidence" in r for r in rejection_reasons)

    # 2. Scorer test
    item = DiscussionItem(
        id="hn_47396347",
        platform="Hacker News",
        original_url="https://news.ycombinator.com/item?id=47396347",
        author="Markoff",
        text=text,
        created_at=datetime.now(timezone.utc) - timedelta(days=214) # ~7 months old
    )
    score = opportunity_scorer.score(item, CAREFLOW_PROFILE)
    # Recency must be penalized (> 90 days)
    assert score.recency <= 5.0

def test_regression_ceo_hn_6227259_idank_freshness_gate():
    """
    CEO Validation Case #2: HN 6227259 (idank)
    Historical discussion from August 2013 about personal emergency-alert hardware.
    MUST NOT be classified as an ACTIONABLE_OPPORTUNITY due to strict 90-day freshness gate.
    """
    text = "It's marketed as a device for the elderly but another segment that could benefit from this are disabled people living alone."
    # Date from August 2013 (over 4,000 days old)
    created_at = datetime(2013, 8, 20, 12, 0, 0, tzinfo=timezone.utc)
    
    # 1. Freshness gate test: Must fail freshness check for actionable outreach
    is_fresh, age_days, freshness_rejections = intent_classifier.evaluate_freshness(
        created_at, max_days=CAREFLOW_PROFILE.max_actionable_age_days
    )
    assert is_fresh is False
    assert age_days > 3000
    assert "exceeding maximum outreach threshold" in freshness_rejections[0]

    # 2. Score recency must be 0
    item = DiscussionItem(
        id="hn_6227259",
        platform="Hacker News",
        original_url="https://news.ycombinator.com/item?id=6227259",
        author="idank",
        text=text,
        created_at=created_at
    )
    score = opportunity_scorer.score(item, CAREFLOW_PROFILE)
    assert score.recency == 0.0

def test_legitimate_actionable_opportunity_acceptance():
    """
    Contrast Case: A fresh post explicitly seeking a solution for parent check-ins/medicine
    within 30 days MUST be accepted as an ACTIONABLE_OPPORTUNITY.
    """
    text = (
        "How do you check in on elderly parents living alone in another country? "
        "My mom in India forgets to take her blood pressure medication every day, and I am anxious every morning."
    )
    created_at = datetime.now(timezone.utc) - timedelta(days=12) # 12 days old (Fresh)
    
    has_direct_evidence, direct_sentence, rejections = intent_classifier.extract_direct_evidence(
        text, CAREFLOW_PROFILE
    )
    assert has_direct_evidence is True
    assert direct_sentence is not None

    is_fresh, age_days, freshness_rejections = intent_classifier.evaluate_freshness(
        created_at, max_days=90
    )
    assert is_fresh is True
