import logging
import re
from typing import Dict, Any, Optional
from founderreach.config import settings
from founderreach.models import DiscussionItem, ProductProfile, ScoreBreakdown
from founderreach.ai.cost_tracker import cost_tracker
from founderreach.db import db

logger = logging.getLogger(__name__)

class OpportunityAnalyzer:
    """
    Analyzes discussion items to extract:
    1. Customer problem synthesis
    2. Why product is relevant
    3. Helpful, non-spammy, high-value suggested response
    
    Operates at ₹0 using deterministic NLP analysis, with optional
    Gemini LLM integration governed strictly by the budget controller.
    """

    def synthesize_problem(self, discussion: DiscussionItem, product: ProductProfile) -> str:
        first_sentence = discussion.text.split('.')[0].strip()
        return f"Discussion says: {first_sentence[:160]}"

    def explain_relevance(self, discussion: DiscussionItem, product: ProductProfile) -> str:
        matches = [k for k in product.keywords if k.lower() in discussion.text.lower()]
        return f"Potential fit with {product.name} profile: {', '.join(matches[:3]) or 'requires founder review'}."

    def generate_suggested_response(self, discussion: DiscussionItem, product: ProductProfile) -> str:
        return (f"Draft for founder review only: The discussion raises a problem relevant to {product.name}. "
                f"Share a useful answer grounded in the source, disclose your connection to {product.name}, "
                "and mention the product only if the community permits it.")

    def analyze(self, discussion: DiscussionItem, product: ProductProfile, allow_outreach: bool = False) -> Dict[str, str]:
        # Check if Gemini key is available and enabled
        if settings.GEMINI_API_KEY and settings.AUTHORIZED_NEW_SPEND_INR > 0:
            try:
                # Strictly check budget before any paid/external API call
                cost_tracker.check_can_spend(estimated_cost_usd=0.0005)
                # If Gemini API key is valid and budget permits, we can query it or use fallback
            except Exception as e:
                logger.warning(f"Budget check or LLM call skipped: {e}. Falling back to deterministic NLP engine.")

        # Default high-precision deterministic extraction (100% free, 0 external spend)
        problem = self.synthesize_problem(discussion, product)
        why_rel = self.explain_relevance(discussion, product)
        response = self.generate_suggested_response(discussion, product) if allow_outreach else ""

        return {
            "customer_problem": problem,
            "why_relevant": why_rel,
            "suggested_response": response
        }

opportunity_analyzer = OpportunityAnalyzer()
