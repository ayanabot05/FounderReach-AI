import re
from datetime import datetime, timezone
from typing import Tuple, Optional, List, Dict
from founderreach.models import ProductProfile

class IntentClassifier:
    """
    Validation Machine Intent Engine:
    Separates CUSTOMER_INTENT_VERIFIED from CUSTOMER_INTENT_UNVERIFIED.
    Requires DIRECT, non-inferred evidence of an appropriate customer problem.
    """

    # Explicit direct seeker expressions (must be seeking a solution to the domain problem)
    ACTIVE_SEEKER_PATTERNS = [
        r'\bhow do (?:you|others|people)\b.*\b(?:check in|remind|monitor|care for|handle)\b',
        r'\banyone (?:know|have|found|recommend|using)\b.*\b(?:tool|app|service|way|solution|bot)\b',
        r'\blooking for\b.*\b(?:tool|app|service|solution|recommendation|way to)\b',
        r'\bis there (?:a|any)\b.*\b(?:app|service|tool|bot|system)\b',
        r'\bwhat (?:do|are) (?:you|others) use to\b',
        r'\bneed (?:a|some|to find)\b.*\b(?:way to|help with|reminder for)\b',
        r'\bi wish there was\b',
        r'\bany recommendations for\b',
        r'\btrying to find a way to (?:check|remind|monitor|stay connected)\b'
        ,r'\bwhat practical things have you put in place\b'
    ]

    # Explicit direct problem struggles (must describe direct personal pain, NOT general opinions or child-care venting)
    DIRECT_PROBLEM_PATTERNS = [
        r'\bmy (?:mom|mother|dad|father|parents?)\b.*\b(?:forgot|forgets|forgetting|forgotten)\b.*\b(?:medicine|medication|pills?|dose)\b',
        r'\bworried (?:that|about)\b.*\b(?:mom|mother|dad|father|parents?)\b.*\b(?:fall|alone|emergency|woke up|not answering)\b',
        r'\bhard (?:to|for me to)\b.*\b(?:call|check in|reach)\b.*\b(?:every day|daily|morning)\b',
        r'\banxious\b.*\b(?:living alone|living away|not answering the phone)\b',
        r'\bemergency\b.*\b(?:mom|dad|parents?)\b.*\b(?:alone|house|hospital)\b',
        r'\bparents? (?:refuse|refuses|hates?|struggle with)\b.*\b(?:apps?|smartphones?|tech|complicated)\b'
        ,r'\b(?:i am|i.m) really struggling to manage my parent.*\bmedication'
    ]

    OFFTOPIC_OR_DISQUALIFYING_PATTERNS = [
        r'\bboomer parents don\'t help\b',  # Family resentment / child-care trade-off venting
        r'\bmeta api\b',
        r'\bwebhook\b',
        r'\bsql query\b',
        r'\bmacroeconomic\b',
        r'\bcopyright\b',
        r'\bip law\b'
    ]

    def extract_direct_evidence(self, text: str, product: ProductProfile) -> Tuple[bool, Optional[str], List[str]]:
        """
        Extracts verbatim sentence that directly proves customer problem exists.
        Returns (is_verified, direct_evidence_sentence, rejection_reasons).
        """
        text_lower = text.lower()
        rejection_reasons = []

        # Check for explicit disqualifiers
        for p in self.OFFTOPIC_OR_DISQUALIFYING_PATTERNS:
            if re.search(p, text_lower):
                if "boomer" in p:
                    rejection_reasons.append("Discussion is venting about intergenerational child-care reciprocity, not expressing an elder-care check-in problem.")
                else:
                    rejection_reasons.append("Discussion is technical or macroeconomic commentary without personal customer need.")
                return False, None, rejection_reasons

        # Check sentences for direct seeker or direct personal struggle
        sentences = [s.strip() for s in re.split(r'(?<=[.!?\n])\s+', text) if len(s.strip()) > 15]

        personal_context = bool(re.search(r'\b(?:my|our)\s+(?:mom|mother|dad|father|parents?)\b', text_lower))
        for s in sentences:
            s_low = s.lower().replace('’', "'")
            # A generic request for an app is not evidence of AYANA's problem.
            domain = bool(re.search(r'\b(?:mom|mother|dad|father|parents?|elderly|aging)\b', s_low))
            care = bool(re.search(r'\b(?:medicin\w*|medicat\w*|pills?|check[ -]?in|remind\w*|living alone|emergency|safety|care|monitor\w*)\b', s_low))
            personal = bool(re.search(r'\b(?:my|our|i|we)\b', s_low))
            if not (domain and care and (personal or personal_context)):
                continue
            # Check seeker patterns
            for pat in self.ACTIVE_SEEKER_PATTERNS:
                if re.search(pat, s_low):
                    return True, s, []

            # Check direct problem struggle
            for pat in self.DIRECT_PROBLEM_PATTERNS:
                if re.search(pat, s_low):
                    return True, s, []

        rejection_reasons.append(
            "No direct evidence: post mentions related keywords, but author does NOT explicitly state personal struggle with parent check-ins, medicine reminders, or living-alone emergencies."
        )
        return False, None, rejection_reasons

    def evaluate_freshness(self, created_at: Optional[datetime], max_days: int = 90) -> Tuple[bool, Optional[int], List[str]]:
        """
        Strict freshness gate for actionable outreach.
        """
        if not created_at:
            return False, None, ["Publication date is missing or unknown. Cannot verify freshness for actionable outreach."]

        dt = created_at
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        
        now = datetime.now(timezone.utc)
        age_days = (now - dt).days

        if age_days < 0:
            return False, age_days, ["Post timestamp is in the future; freshness cannot be verified."]

        if age_days > max_days:
            return False, age_days, [f"Post is {age_days} days old, exceeding maximum outreach threshold of {max_days} days (historical research insight only)."]

        return True, age_days, []

    def classify_intent(self, text: str) -> Tuple[str, float, str]:
        """Provides intent subscore (0 to 20) with transparent reasoning."""
        text_lower = text.lower()
        # Check for offtopic/disqualifiers first
        for p in self.OFFTOPIC_OR_DISQUALIFYING_PATTERNS:
            if re.search(p, text_lower):
                return (
                    "Off-Topic / Technical Discussion",
                    0.0,
                    "Discussion focuses on technical, legal, or unrelated matters without personal customer need."
                )

        # Check active seeker
        for pat in self.ACTIVE_SEEKER_PATTERNS:
            if re.search(pat, text_lower):
                return (
                    "Active Solution Seeker",
                    20.0,
                    "Author is actively seeking tools, recommendations, or solutions for this specific problem."
                )

        # Check direct problem struggle
        for pat in self.DIRECT_PROBLEM_PATTERNS:
            if re.search(pat, text_lower):
                return (
                    "Personal Problem Experiencer",
                    16.0,
                    "Author explicitly recounts a direct first-hand struggle with parent care, medicine, or check-ins."
                )

        # Observational / Narrative
        if "parents" in text_lower or "elderly" in text_lower or "care" in text_lower:
            return (
                "General Commentary / Observational",
                6.0,
                "Discussion mentions eldercare or family topics, but lacks an active solution request or direct check-in problem."
            )

        return (
            "Untargeted",
            2.0,
            "Discussion does not exhibit customer intent."
        )

    # Alias for compatibility
    classify = classify_intent

intent_classifier = IntentClassifier()
