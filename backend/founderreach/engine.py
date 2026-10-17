import logging
from typing import List, Optional, Dict, Any
from founderreach.models import ProductProfile, CustomerOpportunity, DiscussionItem
from founderreach.connectors.hackernews import HackerNewsConnector, DiscoveryUnavailable
from founderreach.connectors.reddit import RedditConnector
from founderreach.validation.verifier import source_verifier
from founderreach.validation.deduplicator import deduplicator
from founderreach.validation.scorer import opportunity_scorer
from founderreach.validation.intent import intent_classifier
from founderreach.ai.analyzer import opportunity_analyzer
from founderreach.config import settings
from founderreach.db import db
from founderreach.routing import route_signal
from founderreach.identity import business_id, source_id, opportunity_id
from founderreach.research_store import ResearchStore
from founderreach.evidence import EvidenceObservation, observation_id
from founderreach.source_registry import SourceRegistry
from dataclasses import asdict
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class OpportunityFinderEngine:
    def __init__(self, research_store: ResearchStore | None = None):
        self.hn_connector = HackerNewsConnector()
        self.reddit_connector = RedditConnector()
        self.connectors = [self.hn_connector, self.reddit_connector]
        self.research_store = research_store
        self.registry = SourceRegistry()
        self.last_run_diagnostics = []

    def _generate_opp_id(self, source_id: str, product_name: str) -> str:
        return opportunity_id(product_name, source_id)

    def find_opportunities(
        self,
        product: ProductProfile,
        min_score: Optional[int] = None,
        limit: int = 20,
        verify_live: bool = True,
        actionable_only: bool = True,
        persist: bool = False
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
        if not product.confirmed:
            raise ValueError("A founder-confirmed profile is required")
        owner_id = business_id(product.identifier)
        if persist and self.research_store is None:
            raise PermissionError("Persistence requires an explicit tenant-scoped local research store")
        if persist:
            self.research_store.prune_retention(self.registry)
        min_score = product.minimum_score if min_score is None else min_score
        raw_discussions: List[DiscussionItem] = []
        self.last_run_diagnostics = []
        attempted = 0
        successful = 0

        # 1. Fetch from active connectors
        for connector in self.connectors:
            if connector.is_enabled():
                attempted += 1
                try:
                    logger.info(f"Querying connector: {connector.name}")
                    if hasattr(connector, "discover"):
                        batch = connector.discover(product, limit=limit * 2)
                        self.last_run_diagnostics.append(batch)
                        if persist:
                            self.research_store.log_query_run(owner_id, batch.source_key, {
                                "status": batch.status, "request_count": batch.request_count,
                                "window_start": batch.window_start, "window_end": batch.window_end,
                                "source_policy_version": batch.source_policy_version,
                                "diagnostics": [asdict(d) for d in batch.diagnostics]})
                        items = batch.items
                        if batch.status in ("success", "partial"):
                            successful += 1
                    else:
                        items = connector.search(product, limit=limit * 2)
                        successful += 1
                    raw_discussions.extend(items)
                except Exception as e:
                    logger.error(f"Connector error on {connector.name}: {e}")
                    failure = {"source": connector.name, "status": "unavailable",
                               "error_type": type(e).__name__}
                    self.last_run_diagnostics.append(failure)
                    if persist:
                        self.research_store.log_query_run(owner_id, connector.name.lower().replace(" ", "_"), failure)
        if attempted and not successful:
            raise DiscoveryUnavailable("All enabled sources failed or were permission blocked; demand is unknown")

        # 2. Filter, Deduplicate & Score
        candidate_opportunities: List[CustomerOpportunity] = []

        # Load already stored verified opportunities for this product that meet min_score
        stored_opps = self.research_store.list_business(owner_id) if persist else []
        for s_opp in stored_opps:
            if s_opp.profile_version != product.version:
                s_opp.classification = "RESEARCH_INSIGHT"
                s_opp.suggested_response = ""
                s_opp.signal_routes = ["demand_evidence"]
                s_opp.rejection_reasons.append("Profile changed; rescore before any action")
            # Old rows predate the strict gate. Never surface them as outreach.
            if s_opp.classification == "ACTIONABLE_OPPORTUNITY":
                try:
                    from datetime import datetime
                    fresh, _, _ = intent_classifier.evaluate_freshness(datetime.fromisoformat(s_opp.discussion_date)) if s_opp.discussion_date else (False, None, [])
                except ValueError:
                    fresh = False
                bounded = bool(s_opp.verification.expires_at and s_opp.verification.expires_at > datetime.now(timezone.utc))
                if not fresh or not s_opp.verification.verified or not bounded or s_opp.intent_status != "CUSTOMER_INTENT_VERIFIED":
                    s_opp.classification = "RESEARCH_INSIGHT"
                    s_opp.suggested_response = ""
            candidate_opportunities.append(s_opp)

        local_urls = set()
        for item in raw_discussions:
            # Check duplicate against both memory and existing texts
            canonical = deduplicator.canonicalize_url(item.original_url)
            stored_match = next((s for s in stored_opps
                                 if canonical == deduplicator.canonicalize_url(s.original_url)), None)
            if canonical in local_urls or (stored_match and stored_match.profile_version == product.version):
                continue
            if stored_match:
                candidate_opportunities.remove(stored_match)
            local_urls.add(canonical)

            # Calculate 100-pt Score
            score_breakdown = opportunity_scorer.score(item, product)

            # Excerpt extraction for evidence verification
            excerpt = item.text.strip()
            if len(excerpt) > 300:
                # Find most relevant sentence containing parent/medicine/check-in/alone
                sentences = re_split_sentences(excerpt)
                best_sentence = ""
                for s in sentences:
                    if any(k.lower() in s.lower() for k in product.keywords + product.pain_points):
                        best_sentence = s.strip()
                        break
                evidence = best_sentence if len(best_sentence) >= 40 else excerpt[:250]
            else:
                evidence = excerpt

            # 3. Source Verification (SOURCE_VERIFIED)
            if verify_live:
                verification = source_verifier.verify_source(item.original_url, evidence)
                source_status = "SOURCE_VERIFIED" if verification.verified else "SOURCE_UNVERIFIED"
            else:
                from founderreach.models import SourceVerification
                verification = SourceVerification(
                    verified=False,
                    http_status=None,
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
                item.created_at, max_days=product.reply_max_age_days
            )
            route = route_signal(item, product, source_status == "SOURCE_VERIFIED",
                                 has_direct_evidence, score_breakdown.total_score >= min_score)

            all_rejections = intent_rejections + freshness_rejections

            # 6. Classification: ACTIONABLE_OPPORTUNITY vs RESEARCH_INSIGHT
            if (source_status == "SOURCE_VERIFIED" and has_direct_evidence and is_fresh
                    and score_breakdown.total_score >= min_score):
                classification = "ACTIONABLE_OPPORTUNITY"
            elif score_breakdown.total_score >= min_score or has_direct_evidence:
                classification = "RESEARCH_INSIGHT"
            else:
                classification = "IRRELEVANT"

            # 7. Synthesize problem, relevance & suggested response
            analysis = opportunity_analyzer.analyze(item, product, allow_outreach=False)

            # Formulate CustomerOpportunity
            native_source_id = source_id(item.platform, item.id)
            opp_id = self._generate_opp_id(native_source_id, owner_id)
            date_str = item.created_at.strftime("%Y-%m-%d") if item.created_at else None

            opp = CustomerOpportunity(
                id=opp_id,
                business_id=owner_id,
                source_id=native_source_id,
                profile_version=product.version,
                product_name=product.name,
                platform=item.platform,
                original_url=item.original_url,
                discussion_date=date_str,
                author=item.author,
                classification=classification,
                source_status=source_status,
                intent_status=intent_status,
                direct_problem_evidence=direct_sentence,
                rejection_reasons=all_rejections + list(route.reasons),
                signal_routes=list(route.routes),
                customer_problem=analysis["customer_problem"],
                why_relevant=analysis["why_relevant"],
                evidence_excerpt=verification.evidence_excerpt,
                score=score_breakdown,
                suggested_response=analysis["suggested_response"],
                verification=verification
            )

            # Classification, freshness, and source permission remain separate.
            source_key = "hackernews" if item.platform == "Hacker News" else item.platform.lower().replace(" ", "_")
            policy = self.registry.get(source_key)
            permission = policy.decision("research") if policy else "unknown"
            verified_bounded = bool(verification.verified and verification.expires_at
                                    and verification.expires_at > datetime.now(timezone.utc)
                                    and verification.method and verification.checked_at)
            relevance = "matched" if classification != "IRRELEVANT" else "rejected"
            observation = EvidenceObservation(
                observation_id=observation_id(owner_id, native_source_id,
                                              "customer_need" if has_direct_evidence else "third_party_mention", evidence),
                business_id=owner_id, source_id=native_source_id, source_key=source_key,
                source_policy_version=policy.version if policy else None,
                kind="customer_need" if has_direct_evidence else "third_party_mention",
                provenance="public_api", source_url=item.original_url,
                excerpt=evidence, claim=direct_sentence or "Topical research mention; customer demand unconfirmed",
                published_at=item.created_at,
                verification_state="verified" if verified_bounded else "failed" if verification.status in (
                    "quote_mismatch", "not_found", "rate_limited", "network_error") else "unverified",
                verification_method=verification.method if verified_bounded else None,
                verified_at=verification.checked_at if verified_bounded else None,
                verification_expires_at=verification.expires_at if verified_bounded else None,
                verification_failure=None if verified_bounded else verification.status,
                relevance_state=relevance,
                freshness_state="timely" if is_fresh else "evergreen" if item.created_at else "unknown",
                permission_state=permission,
                allowed_uses=policy.allowed_uses if permission == "allowed" else [],
                review_state="pending" if classification == "RESEARCH_INSIGHT" or not verified_bounded else "not_required",
                routes=list(dict.fromkeys(list(route.routes) + (["owned_content_research"] if relevance == "matched" else []))))

            # Save to Database
            if persist and classification != "IRRELEVANT":
                self.research_store.save(opp)
                prior_observation = self.research_store.get_observation(owner_id, observation.observation_id)
                if prior_observation and prior_observation.review_state != observation.review_state:
                    observation = observation.model_copy(update={"review_state": prior_observation.review_state})
                self.research_store.save_observation(observation)
            if classification != "IRRELEVANT":
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
