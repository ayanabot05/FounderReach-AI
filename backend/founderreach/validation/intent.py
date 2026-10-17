"""Profile-driven direct-problem and intent classification."""
import re
from datetime import datetime, timezone
from typing import Optional, Tuple, List
from founderreach.models import ProductProfile


class IntentClassifier:
    SEEKER_PATTERNS = (
        r"\bhow do (?:you|others|people)\b",
        r"\banyone (?:know|have|found|recommend|using)\b",
        r"\blooking for\b", r"\bis there (?:a|any)\b",
        r"\bwhat (?:do|are) (?:you|others) use to\b",
        r"\bneed (?:a|some|to find)\b", r"\bi wish there was\b",
        r"\bany recommendations for\b", r"\btrying to find a way\b",
        r"\bwhat practical things have you put in place\b",
    )

    def extract_direct_evidence(self, text: str, product: ProductProfile) -> Tuple[bool, Optional[str], List[str]]:
        normalized = text.lower().replace("’", "'")
        for pattern in product.disqualifying_patterns:
            if re.search(pattern, normalized):
                reason = "No direct evidence: profile disqualifying pattern matched."
                return False, None, [reason]

        sentences = [s.strip() for s in re.split(r"(?<=[.!?\n])\s+", text) if len(s.strip()) > 15]
        personal_context = bool(re.search(r"\b(?:my|our|i|we)\b", normalized))
        for sentence in sentences:
            low = sentence.lower().replace("’", "'")
            direct = any(re.search(pattern, low) for pattern in product.direct_problem_patterns)
            seeker = any(re.search(pattern, low) for pattern in self.SEEKER_PATTERNS)
            domain = direct or any(re.search(pattern, low) for pattern in product.problem_patterns) or any(
                keyword.lower() in low for keyword in product.keywords)
            if not domain or not (personal_context or seeker):
                continue
            if direct or seeker:
                return True, sentence, []
        return False, None, ["No direct evidence: no founder-profile problem or personal struggle was established."]

    def evaluate_freshness(self, created_at: Optional[datetime], max_days: int = 90) -> Tuple[bool, Optional[int], List[str]]:
        if not created_at:
            return False, None, ["Publication date is missing or unknown. Cannot verify freshness for actionable outreach."]
        dated = created_at if created_at.tzinfo else created_at.replace(tzinfo=timezone.utc)
        age_days = (datetime.now(timezone.utc) - dated).days
        if age_days < 0:
            return False, age_days, ["Post timestamp is in the future; freshness cannot be verified."]
        if age_days > max_days:
            return False, age_days, [f"Post is {age_days} days old, exceeding maximum outreach threshold of {max_days} days (historical research insight only)."]
        return True, age_days, []

    def classify_intent(self, text: str, product: ProductProfile) -> Tuple[str, float, str]:
        if any(re.search(pattern, text.lower().replace("’", "'")) for pattern in product.disqualifying_patterns):
            return "Off-Topic / Technical Discussion", 0.0, "Profile disqualifying pattern matched."
        direct, sentence, _ = self.extract_direct_evidence(text, product)
        if direct and any(re.search(pattern, sentence.lower()) for pattern in self.SEEKER_PATTERNS):
            return "Active Solution Seeker", 20.0, "Direct profile problem and solution request."
        if direct:
            return "Personal Problem Experiencer", 16.0, "Direct personal problem matches the founder profile."
        if any(re.search(pattern, text.lower()) for pattern in product.problem_patterns) or any(
            keyword.lower() in text.lower() for keyword in product.keywords):
            return "General Commentary / Observational", 6.0, "Profile topic appears without direct personal intent."
        return "Untargeted", 2.0, "No profile topic or customer intent established."

    classify = classify_intent


intent_classifier = IntentClassifier()
