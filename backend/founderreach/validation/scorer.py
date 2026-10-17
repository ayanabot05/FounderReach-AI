import re
from datetime import datetime, timezone
from typing import Dict, Any, Tuple
from founderreach.models import ScoreBreakdown, ProductProfile, DiscussionItem
from founderreach.validation.intent import intent_classifier

class OpportunityScorer:
    """
    100-Point Transparent Scoring Engine:
    - Problem Fit: 30 pts
    - Customer Fit: 20 pts
    - Expressed Intent: 20 pts
    - Recency: 15 pts
    - Evidence Quality: 15 pts
    """

    def score(self, discussion: DiscussionItem, product: ProductProfile) -> ScoreBreakdown:
        text = discussion.text
        text_lower = text.lower()
        justification: Dict[str, str] = {}

        # -------------------------------------------------------------
        # 1. Problem Fit (Max 30)
        # -------------------------------------------------------------
        problem_score = 0.0
        problem_matches = []

        # High-signal pain point co-occurrence patterns evaluated sentence-by-sentence
        signal_patterns = [(pattern, f"profile signal {i + 1}") for i, pattern in enumerate(product.problem_patterns)]

        sentences = [s.strip().lower() for s in re.split(r'[.!?\n]+', text) if len(s.strip()) > 10]
        for pat, label in signal_patterns:
            for s in sentences:
                if re.search(pat, s):
                    problem_matches.append(label)
                    break

        # Keyword direct matches with word boundaries
        kw_matches = []
        for kw in product.keywords:
            words = kw.lower().split()
            if all(re.search(r'\b' + re.escape(w) + r'\b', text_lower) for w in words):
                kw_matches.append(kw)

        if len(problem_matches) >= 3 or (len(problem_matches) >= 2 and len(kw_matches) >= 1):
            problem_score = 30.0
            justification["problem_fit"] = f"Strong problem match: Author directly discusses multiple core pain points ({', '.join(problem_matches[:3])})."
        elif len(problem_matches) >= 2 or len(kw_matches) >= 1:
            problem_score = 22.0
            justification["problem_fit"] = f"Moderate problem match: Discussion mentions relevant problems ({', '.join((problem_matches + kw_matches)[:2])})."
        elif len(problem_matches) == 1:
            problem_score = 14.0
            justification["problem_fit"] = f"Partial problem match: Mentions {problem_matches[0]}, but lacks multi-dimensional pain depth."
        else:
            problem_score = 4.0
            justification["problem_fit"] = "Low problem match: Topic does not show profile pain signals."

        # Penalty for negative keywords
        negative_hits = [nk for nk in product.negative_keywords if nk.lower() in text_lower]
        if negative_hits:
            problem_score = max(0.0, problem_score - product.negative_keyword_penalty)
            justification["problem_fit"] += f" (Penalized -{product.negative_keyword_penalty:g} for negative keywords: {', '.join(negative_hits)})"

        # -------------------------------------------------------------
        # 2. Customer Fit (Max 20) â€” Strict Direct Evidence Only
        # -------------------------------------------------------------
        customer_score = 0.0
        persona_hits = [term for term in product.customer_fit_signals if term.lower() in text_lower]
        if len(persona_hits) >= 2:
            customer_score = 20.0
            justification["customer_fit"] = "High persona alignment: Multiple founder-defined customer signals."
        elif len(persona_hits) == 1:
            customer_score = 15.0
            justification["customer_fit"] = "Customer signal explicitly appears in the discussion."
        else:
            customer_score = 2.0
            justification["customer_fit"] = "Low persona alignment: No explicit founder-defined customer signal."

        # -------------------------------------------------------------
        # 3. Expressed Intent (Max 20)
        # -------------------------------------------------------------
        intent_cat, intent_score, intent_reason = intent_classifier.classify_intent(text, product)
        justification["expressed_intent"] = f"{intent_cat} ({intent_reason})"

        # -------------------------------------------------------------
        # 4. Recency (Max 15) â€” Strict Freshness Gate
        # -------------------------------------------------------------
        recency_score = 0.0
        now = datetime.now(timezone.utc)
        if discussion.created_at:
            dt = discussion.created_at
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            delta_days = (now - dt).days

            if delta_days <= 30:
                recency_score = 15.0
                justification["recency"] = f"Very fresh ({delta_days} days ago). High actionability."
            elif delta_days <= 90:
                recency_score = 12.0
                justification["recency"] = f"Within 90-day actionable window ({delta_days} days ago)."
            elif delta_days <= 180:
                recency_score = 5.0
                justification["recency"] = f"Past 90-day window ({delta_days} days ago). Downgraded to research tier."
            elif delta_days <= 365:
                recency_score = 3.0
                justification["recency"] = f"Past actionable window ({delta_days} days ago). Research insight only."
            elif delta_days <= 730:
                recency_score = 1.0
                justification["recency"] = f"Historical archive ({delta_days} days ago). Not actionable for outreach."
            else:
                recency_score = 0.0
                justification["recency"] = f"Historical archive (> 2 years old, {delta_days} days ago). Zero actionability."
        else:
            recency_score = 4.0
            justification["recency"] = "Publication date unavailable. Treated cautiously (max 4 pts)."

        # -------------------------------------------------------------
        # 5. Evidence Quality (Max 15)
        # -------------------------------------------------------------
        char_count = len(text.strip())
        # Specificity comes from the selected business, never from hardcoded business vocabulary.
        profile_terms = product.keywords + product.customer_fit_signals
        has_specifics = any(term.lower() in text_lower for term in profile_terms if len(term.strip()) >= 5)

        if char_count >= 150 and has_specifics:
            evidence_score = 15.0
            justification["evidence_quality"] = f"Rich contextual evidence ({char_count} chars with specific operational details)."
        elif char_count >= 80:
            evidence_score = 11.0
            justification["evidence_quality"] = f"Sufficient evidence ({char_count} chars)."
        else:
            evidence_score = 5.0
            justification["evidence_quality"] = f"Sparse evidence ({char_count} chars). Context is minimal."

        # -------------------------------------------------------------
        # Total
        # -------------------------------------------------------------
        total = round(problem_score + customer_score + intent_score + recency_score + evidence_score, 1)

        return ScoreBreakdown(
            problem_fit=problem_score,
            customer_fit=customer_score,
            expressed_intent=intent_score,
            recency=recency_score,
            evidence_quality=evidence_score,
            total_score=total,
            justification=justification
        )

opportunity_scorer = OpportunityScorer()
