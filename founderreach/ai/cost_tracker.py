import logging
from typing import Dict, Any, Optional
from founderreach.config import settings
from founderreach.db import db

logger = logging.getLogger(__name__)

# Hard limits from CEO directive
USD_TO_INR_RATE = 86.50  # Conservative conversion rate

class BudgetExceededError(Exception):
    """Raised when an operation would exceed budget limits."""
    pass

class CostTracker:
    def __init__(self):
        self.budget_target_inr = settings.BUDGET_TARGET_INR  # 600.00
        self.budget_ceiling_inr = settings.BUDGET_CEILING_INR  # 1000.00

    def get_spending_summary(self) -> Dict[str, Any]:
        """Returns actual spend and budget headroom."""
        spend = db.get_total_spend()
        actual_inr = spend["total_inr"]
        actual_usd = spend["total_usd"]
        return {
            "spent_inr": round(actual_inr, 2),
            "spent_usd": round(actual_usd, 4),
            "target_budget_inr": self.budget_target_inr,
            "ceiling_budget_inr": self.budget_ceiling_inr,
            "remaining_target_inr": max(0.0, round(self.budget_target_inr - actual_inr, 2)),
            "remaining_ceiling_inr": max(0.0, round(self.budget_ceiling_inr - actual_inr, 2)),
            "requires_ceo_approval": actual_inr >= self.budget_target_inr,
            "is_within_ceiling": actual_inr < self.budget_ceiling_inr
        }

    def check_can_spend(self, estimated_cost_usd: float = 0.0) -> bool:
        """
        Guarantees we never exceed budget ceilings.
        Raises BudgetExceededError if limit is breached.
        """
        estimated_inr = estimated_cost_usd * USD_TO_INR_RATE
        summary = self.get_spending_summary()
        current_inr = summary["spent_inr"]
        
        projected_inr = current_inr + estimated_inr
        
        if projected_inr >= self.budget_ceiling_inr:
            raise BudgetExceededError(
                f"BLOCKED: Projected spend of ₹{projected_inr:.2f} breaches absolute ceiling of ₹{self.budget_ceiling_inr:.2f}!"
            )
            
        if projected_inr >= self.budget_target_inr:
            raise BudgetExceededError(
                f"PAUSED: Projected spend of ₹{projected_inr:.2f} exceeds target threshold of ₹{self.budget_target_inr:.2f}. "
                "CEO approval required before exceeding ₹600."
            )
            
        return True

    def record_usage(self, service: str, operation: str, tokens_in: int = 0, tokens_out: int = 0,
                     cost_usd: float = 0.0, model: str = "none", cached: bool = False, notes: str = ""):
        """Records an expense item into the SQLite ledger."""
        cost_inr = cost_usd * USD_TO_INR_RATE
        db.record_cost(
            service=service,
            model=model,
            operation=operation,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost_usd,
            cost_inr=cost_inr,
            cached=cached,
            notes=notes
        )
        logger.info(f"Cost recorded: {service} ({operation}) - ${cost_usd:.4f} (₹{cost_inr:.2f}) [cached={cached}]")

cost_tracker = CostTracker()
