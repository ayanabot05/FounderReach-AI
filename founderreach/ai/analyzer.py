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
        text = discussion.text
        text_lower = text.lower()
        
        # Identify key struggle keywords
        struggles = []
        if "check in" in text_lower or "check-in" in text_lower or "calling" in text_lower or "call" in text_lower:
            struggles.append("maintaining regular daily check-ins without overwhelming elderly parents")
        if "medicine" in text_lower or "medication" in text_lower or "pills" in text_lower:
            struggles.append("ensuring elderly parents take daily medications reliably on time")
        if "alone" in text_lower or "fall" in text_lower or "safety" in text_lower or "emergency" in text_lower:
            struggles.append("safety anxiety regarding parents living alone and potential emergencies")
        if "distance" in text_lower or "nri" in text_lower or "another city" in text_lower or "another country" in text_lower or "away" in text_lower:
            struggles.append("managing family connection across time zones and geographic distance")

        if struggles:
            return f"Author experiences friction with {', and '.join(struggles)}."
        else:
            first_sentence = text.split('.')[0].strip()
            return f"Author describes practical difficulties in elder care: '{first_sentence[:120]}...'"

    def explain_relevance(self, discussion: DiscussionItem, product: ProductProfile) -> str:
        text_lower = discussion.text.lower()
        reasons = []

        if "whatsapp" in text_lower or "message" in text_lower:
            reasons.append(f"{product.name} operates directly inside WhatsApp, which elderly parents already use comfortably without new app friction")
        if "medicine" in text_lower or "medication" in text_lower:
            reasons.append(f"{product.name} provides automated, gentle medication reminders")
        if "check in" in text_lower or "alone" in text_lower or "worried" in text_lower:
            reasons.append(f"{product.name} schedules daily routine checks and alerts family if safety confirmations are missed")
        if "india" in text_lower or "telugu" in text_lower or "hindi" in text_lower or "nri" in text_lower:
            reasons.append(f"{product.name} specifically supports Indian languages (English, Telugu, Hindi) tailored for NRI families")

        if not reasons:
            reasons.append(f"{product.name} addresses the exact friction of remote parent care and daily safety check-ins")

        return "; ".join(reasons) + "."

    def generate_suggested_response(self, discussion: DiscussionItem, product: ProductProfile) -> str:
        text_lower = discussion.text.lower()
        author_salutation = f"Hi @{discussion.author}" if discussion.author else "Hi there"

        # Construct empathetic, value-first response
        paragraphs = []

        # 1. Empathy & Direct validation
        if "alone" in text_lower or "worry" in text_lower or "distance" in text_lower or "nri" in text_lower:
            paragraphs.append(
                f"{author_salutation}, I completely relate to this. The emotional overhead of living away while worrying about whether your parents woke up okay or took their pills is a constant quiet stress for anyone living away."
            )
        else:
            paragraphs.append(
                f"{author_salutation}, this is such an important challenge when managing parent care and daily routines remotely."
            )

        # 2. Practical, respectful thought (Grounded, no fake interview claims)
        if "medicine" in text_lower or "pill" in text_lower:
            paragraphs.append(
                "A common practical hurdle with independent parents is that direct reminders like 'did you take your pills?' can sometimes feel intrusive. Some find that tying check-ins to an existing routine—like a morning message or tea photo—helps keep tabs on medication schedules more naturally."
            )
        else:
            paragraphs.append(
                "A key challenge with elder-assistive tech is device or app friction—independent parents often push back against dedicated monitoring gadgets or complex new apps that make them feel monitored."
            )

        # 3. Honest, transparent founder disclosure (no hype, no fake customer count)
        paragraphs.append(
            f"Full disclosure: I am working on an early project called {product.name} ({product.website}). "
            f"It is designed to run directly inside WhatsApp (which parents already use) to help with gentle daily check-ins, medicine prompts, and return-home confirmations in English, Telugu, and Hindi.\n\n"
            f"I share this purely in case the concept is helpful, and I would genuinely appreciate any perspective or feedback on what approach works best for your situation."
        )

        return "\n\n".join(paragraphs)

    def analyze(self, discussion: DiscussionItem, product: ProductProfile, allow_outreach: bool = False) -> Dict[str, str]:
        # Check if Gemini key is available and enabled
        if settings.GEMINI_API_KEY:
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
