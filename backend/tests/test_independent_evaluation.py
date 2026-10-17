from evaluate_independent import evaluate
from founderreach.ai.analyzer import opportunity_analyzer
from founderreach.profiles import load_profile
from founderreach.models import DiscussionItem
from _synthetic_profiles import CARE_SYNTHETIC_LABELS

CARE_PROFILE = load_profile("careflow")


def test_independent_challenge_has_real_positives_and_negatives():
    result = evaluate(CARE_SYNTHETIC_LABELS)
    assert result["counts"]["tp"] >= 2
    assert result["counts"]["fn"] == 0
    assert result["counts"]["fp"] == 0


def test_empty_predictions_precision_is_na():
    result = evaluate([{"id": "n", "label": "NOT_CUSTOMER_INTENT", "text": "Unrelated programming discussion."}])
    assert result["counts"]["precision"] is None


def test_research_analysis_never_generates_outreach_draft():
    item = DiscussionItem(id="x", platform="Hacker News", original_url="https://news.ycombinator.com/item?id=1",
                          text="My mom in India lives alone and I worry about daily check-ins.")
    assert opportunity_analyzer.analyze(item, CARE_PROFILE)["suggested_response"] == ""
