import pytest
from founderreach.ai.cost_tracker import CostTracker, BudgetExceededError

def test_cost_tracker_allows_zero_spend():
    tracker = CostTracker()
    summary = tracker.get_spending_summary()
    assert summary["spent_inr"] <= summary["target_budget_inr"]
    assert tracker.check_can_spend(0.0) is True

def test_cost_tracker_blocks_above_ceiling():
    tracker = CostTracker()
    # Attempting to spend $15 (~ INR 1,297.50) which exceeds absolute INR 1,000 ceiling
    with pytest.raises(BudgetExceededError):
        tracker.check_can_spend(estimated_cost_usd=15.0)

def test_cost_tracker_pauses_above_target():
    tracker = CostTracker()
    # Attempting to spend $8 (~ INR 692) which exceeds INR 600 target
    with pytest.raises(BudgetExceededError) as exc_info:
        tracker.check_can_spend(estimated_cost_usd=8.0)
    assert "CEO approval required" in str(exc_info.value)
