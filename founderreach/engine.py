import logging
import hashlib
from typing import List, Optional, Dict, Any
from founderreach.models import ProductProfile, CustomerOpportunity, DiscussionItem
from founderreach.connectors.hackernews import HackerNewsConnector
from founderreach.connectors.reddit import RedditConnector
from founderreach.validation.verifier import source_verifier
from founderreach.validation.deduplicator import deduplicator
from founderreach.validation.scorer import opportunity_scorer
from founderreach.validation.intent import intent_classifier
from founderreach.ai.analyzer import opportunity_analyzer
from founderreach.config import settings
from founderreach.db import db

logger = logging.getLogger(__name__)

# Pre-configured Profile for First Real Test Customer: AYANA
AYANA_PROFILE = ProductProfile(
    name="AYANA",
    website="https://www.ayanabott.com/",
    description=(
        "AYANA helps families living away from their parents stay connected through "
        "WhatsApp check-ins, daily activities, medicine reminders, and return-home safety checks. "
        "Operates directly in WhatsApp in English, Telugu, and Hindi."
    ),
    target_audiences=[
        "NRIs with parents living in India",
        "Adult children living in another city",
        "Families concerned about regular parent check-ins",
        "People seeking practical ways to stay connected with parents remotely"
    ],
    target_markets=["India", "USA", "UK", "Canada", "Global NRI corridors"],
    keywords=[
        "elderly parents living alone",
        "aging parents check in",
        "parents in India care",
        "medicine reminder for parents",
        "staying connected with elderly parents",
        "nri parents alone in india"
    ],
    pain_points=[
        "worrying about elderly parents living alone",
        "ensuring aging parents take daily medication on time",
        "remote parent check-ins across time zones and distance",
        "fear of parent falling or having emergency while living alone",
        "parents resisting complicated new apps or wearables"
    ],
    negative_keywords=[
        "pet care",
        "toddler",
        "kindergarten",
        "crypto",
        "spam",
        "bulk sms marketing"
    ]
)

class OpportunityFinderEngine:
    def __init__(self):
        self.hn_connector = HackerNewsConnector()
        self.reddit_connector = RedditConnector()
        self.connectors = [self.hn_connector, self.reddit_connector]

    def _generate_opp_id(self, source_id: str, product_name: str) -> str:
        raw = f"{product_name}:{source_id}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def find_opportunities(
        self,
        product: ProductProfile = AYANA_PROFILE,
        min_score: int = 75,
        limit: int = 20,
        verify_live: bool = True,
        actionable_only: bool = True
    ) -> List[CustomerOpportunity]:
        """
        Executes full discovery & validation pipeline:
        1. Discovery across enabled connectors (HN active; Reddit disabled by policy).
        2. Deduplication (canonical URLs and content hash).
        3. 100-point Scoring (Problem fit, Customer fit, Intent, Recency, Evidence quality).
        4. Strict 75+ threshold filtering.
        5. Live Source Verification (Confirms URL status & excerpt existence).
        6. AI synthesis of problem, relevance, and non-spam suggested response.
        7. Database persistence.
        """
        raw_discussions: List[DiscussionItem] = []

        # 1. Fetch from active connectors
        for connector in self.connectors:
            if connector.is_enabled():
                try:
                    logger.info(f"Querying connector: {connector.name}")
                    items = connector.search(product, limit=limit * 2)
                    raw_discussions.extend(items)
                except Exception as e:
                    logger.error(f"Connector error on {connector.name}: {e}")

        # 2. Filter, Deduplicate & Score
        candidate_opportunities: List[CustomerOpportunity] = []
        existing_texts: List[str] = []

        # Load already stored verified opportunities for this product that meet min_score
        stored_opps = db.get_opportunities(product.name, min_score=float(min_score))
        for s_opp in stored_opps:
            # Old rows predate the strict gate. Never surface them as outreach.
            if s_opp.classification == "ACTIONABLE_OPPORTUNITY":
                try:
                    from datetime import datetime
                    fresh, _, _ = intent_classifier.evaluate_freshness(datetime.fromisoformat(s_opp.discussion_date)) if s_opp.discussion_date else (False, None, [])
                except ValueError:
                    fresh = False
                if not fresh or not s_opp.verification.verified or s_opp.intent_status != "CUSTOMER_INTENT_VERIFIED":
                    s_opp.classification = "RESEARCH_INSIGHT"
                    s_opp.suggested_response = ""
            candidate_opportunities.append(s_opp)
            existing_texts.append(s_opp.evidence_excerpt)
            deduplicator._seen_urls.add(deduplicator.canonicalize_url(s_opp.original_url))

        for item in raw_discussions:
            # Check duplicate against both memory and existing texts
            if deduplicator.canonicalize_url(item.original_url) in deduplicator._seen_urls:
                continue
            if deduplicator.is_duplicate(item.original_url, item.text, existing_texts):
                continue

            # Calculate 100-pt Score
            score_breakdown = opportunity_scorer.score(item, product)

            # Apply default threshold (75+ by default)
            if score_breakdown.total_score < min_score:
                continue

            # Excerpt extraction for evidence verification
            excerpt = item.text.strip()
            if len(excerpt) > 300:
                # Find most relevant sentence containing parent/medicine/check-in/alone
                sentences = re_split_sentences(excerpt)
                best_sentence = ""
                for s in sentences:
                    if any(k in s.lower() for k in ["parent", "mom", "dad", "medicine", "check", "alone", "nri", "call"]):
                        best_sentence = s.strip()
                        break
                evidence = best_sentence if len(best_sentence) >= 40 else excerpt[:250]
            else:
                evidence = excerpt

            # 3. Source Verification (SOURCE_VERIFIED)
            if verify_live:
                verification = source_verifier.verify_source(item.original_url, evidence)
                # CEO DIRECTIVE: A result must be rejected if its evidence cannot be verified!
                if not verification.verified:
                    logger.info(f"Rejecting opportunity {item.original_url}: Source evidence could not be verified.")
                    continue
                source_status = "SOURCE_VERIFIED"
            else:
                from founderreach.models import SourceVerification
                verification = SourceVerification(
                    verified=True,
                    http_status=200,
                    verified_url=item.original_url,
                    evidence_excerpt=evidence,
                    verification_notes="Live verification bypassed by flag."
                )
                source_status = "SOURCE_UNVERIFIED"

            # 4. Customer Intent Verification (CUSTOMER_INTENT_VERIFIED)
            has_direct_evidence, direct_sentence, intent_rejections = intent_classifier.extract_direct_evidence(item.text, product)
            intent_status = "CUSTOMER_INTENT_VERIFIED" if has_direct_evidence else "CUSTOMER_INTENT_UNVERIFIED"

            # 5. Strict Freshness Gate (Default Max 90 Days)
            is_fresh, age_days, freshness_rejections = intent_classifier.evaluate_freshness(
                item.created_at, max_days=product.max_actionable_age_days
            )

            all_rejections = intent_rejections + freshness_rejections

            # 6. Classification: ACTIONABLE_OPPORTUNITY vs RESEARCH_INSIGHT
            if source_status == "SOURCE_VERIFIED" and intent_status == "CUSTOMER_INTENT_VERIFIED" and is_fresh and score_breakdown.total_score >= min_score:
                classification = "ACTIONABLE_OPPORTUNITY"
            elif source_status == "SOURCE_VERIFIED" and (score_breakdown.total_score >= 60 or "elderly" in item.text.lower()):
                classification = "RESEARCH_INSIGHT"
            else:
                classification = "IRRELEVANT"

            # 7. Synthesize problem, relevance & suggested response
            analysis = opportunity_analyzer.analyze(item, product, allow_outreach=classification == "ACTIONABLE_OPPORTUNITY" and verify_live)

            # Formulate CustomerOpportunity
            opp_id = self._generate_opp_id(item.id, product.name)
            date_str = item.created_at.strftime("%Y-%m-%d") if item.created_at else None

            opp = CustomerOpportunity(
                id=opp_id,
                product_name=product.name,
                platform=item.platform,
                original_url=item.original_url,
                discussion_date=date_str,
                author=item.author,
                classification=classification,
                source_status=source_status,
                intent_status=intent_status,
                direct_problem_evidence=direct_sentence,
                rejection_reasons=all_rejections,
                customer_problem=analysis["customer_problem"],
                why_relevant=analysis["why_relevant"],
                evidence_excerpt=verification.evidence_excerpt,
                score=score_breakdown,
                suggested_response=analysis["suggested_response"],
                verification=verification
            )

            # Save to Database
            db.save_opportunity(opp)
            deduplicator.mark_saved(opp_id, item.original_url, item.text)
            existing_texts.append(item.text)
            candidate_opportunities.append(opp)

            if len(candidate_opportunities) >= limit:
                break

        # Sort opportunities by score descending
        candidate_opportunities.sort(key=lambda x: x.score.total_score, reverse=True)
        if actionable_only:
            return [o for o in candidate_opportunities if o.classification == "ACTIONABLE_OPPORTUNITY"]
        return candidate_opportunities

def re_split_sentences(text: str) -> List[str]:
    import re
    return [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]

engine = OpportunityFinderEngine()
