import json
from pathlib import Path
from evaluate_independent import evaluate
from founderreach.ai.analyzer import opportunity_analyzer
from founderreach.engine import AYANA_PROFILE
from founderreach.models import DiscussionItem


def test_independent_challenge_has_real_positives_and_negatives():
    rows = json.loads((Path(__file__).parents[1] / "reports" / "INDEPENDENT_LABELS.json").read_text(encoding="utf-8"))
    result = evaluate(rows)
    assert result["counts"]["tp"] >= 2
    assert result["counts"]["fn"] == 0
    assert result["counts"]["fp"] == 0


def test_empty_predictions_precision_is_na():
    result = evaluate([{"id": "n", "label": "NOT_CUSTOMER_INTENT", "text": "Unrelated programming discussion."}])
    assert result["counts"]["precision"] is None


def test_research_analysis_never_generates_outreach_draft():
    item = DiscussionItem(id="x", platform="Hacker News", original_url="https://news.ycombinator.com/item?id=1",
                          text="My mom in India lives alone and I worry about daily check-ins.")
    assert opportunity_analyzer.analyze(item, AYANA_PROFILE)["suggested_response"] == ""
