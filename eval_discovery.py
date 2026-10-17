import json
from founderreach.connectors.hackernews import HackerNewsConnector
from founderreach.validation.scorer import opportunity_scorer
from founderreach.validation.intent import intent_classifier
from founderreach.engine import AYANA_PROFILE
from founderreach.models import DiscussionItem
from founderreach.validation.verifier import source_verifier
from founderreach.ai.analyzer import opportunity_analyzer
from founderreach.models import CustomerOpportunity
from founderreach.db import db

hn = HackerNewsConnector()
queries = [
    "elderly parents living alone",
    "aging parents check in",
    "taking care of elderly parents",
    "parents live alone",
    "parents in India",
    "medicine reminder parents",
    "elder care check in",
    "caring for aging parents",
    "parents alone falling",
    "nri parents care"
]

seen_urls = set()
candidate_items = []

for q in queries:
    hits = hn._execute_query(q, tags="comment", hits_per_page=20)
    for h in hits:
        oid = str(h.get("objectID"))
        url = f"https://news.ycombinator.com/item?id={oid}"
        if url in seen_urls:
            continue
        seen_urls.add(url)
        text = hn._clean_html(h.get("comment_text", ""))
        if len(text) < 60:
            continue
            
        item = DiscussionItem(
            id=f"hn_{oid}",
            platform="Hacker News",
            original_url=url,
            title=h.get("story_title") or "Discussion",
            author=h.get("author"),
            text=text,
            created_at=None
        )
        
        score = opportunity_scorer.score(item, AYANA_PROFILE)
        candidate_items.append((score.total_score, item, score))

candidate_items.sort(key=lambda x: x[0], reverse=True)

print(f"Total evaluated candidate items: {len(candidate_items)}")
print("\n--- TOP CANDIDATE DISCUSSIONS ---")

verified_opportunities = []
for tot_score, item, score in candidate_items:
    if tot_score < 60:
        continue
    
    # Live verify source
    verif = source_verifier.verify_source(item.original_url, item.text[:120])
    status_str = "VERIFIED" if verif.verified else "UNVERIFIED"
    
    print(f"[{tot_score:.1f}] [{status_str}] {item.original_url} | Author: {item.author}")
    print(f"   Problem: {score.justification.get('problem_fit')}")
    print(f"   Customer: {score.justification.get('customer_fit')}")
    print(f"   Intent: {score.justification.get('expressed_intent')}")
    print(f"   Excerpt: {item.text[:140]}...\n")
    
    if verif.verified and tot_score >= 60:
        has_direct_evidence, direct_sentence, intent_rejections = intent_classifier.extract_direct_evidence(item.text, AYANA_PROFILE)
        intent_status = "CUSTOMER_INTENT_VERIFIED" if has_direct_evidence else "CUSTOMER_INTENT_UNVERIFIED"
        
        is_fresh, age_days, freshness_rejections = intent_classifier.evaluate_freshness(
            item.created_at, max_days=AYANA_PROFILE.max_actionable_age_days
        )
        all_rejections = intent_rejections + freshness_rejections

        if verif.verified and intent_status == "CUSTOMER_INTENT_VERIFIED" and is_fresh and tot_score >= 75:
            classification = "ACTIONABLE_OPPORTUNITY"
        else:
            classification = "RESEARCH_INSIGHT"

        analysis = opportunity_analyzer.analyze(item, AYANA_PROFILE, allow_outreach=classification == "ACTIONABLE_OPPORTUNITY")
        opp = CustomerOpportunity(
            id=f"eval_{item.id}",
            product_name="AYANA",
            platform=item.platform,
            original_url=item.original_url,
            discussion_date=None,
            author=item.author,
            classification=classification,
            source_status="SOURCE_VERIFIED" if verif.verified else "SOURCE_UNVERIFIED",
            intent_status=intent_status,
            direct_problem_evidence=direct_sentence,
            rejection_reasons=all_rejections,
            customer_problem=analysis["customer_problem"],
            why_relevant=analysis["why_relevant"],
            evidence_excerpt=verif.evidence_excerpt,
            score=score,
            suggested_response=analysis["suggested_response"],
            verification=verif
        )
        db.save_opportunity(opp)
        verified_opportunities.append(opp)

print(f"Total opportunities meeting threshold and verified: {len(verified_opportunities)}")
