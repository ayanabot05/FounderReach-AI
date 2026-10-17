"""Low-cost recommendation from a confirmed profile and verified observations."""
from founderreach.engine import OpportunityFinderEngine
from founderreach.models import ProductProfile


def recommend(profile: ProductProfile, snapshot: dict, finder: OpportunityFinderEngine | None = None) -> dict:
    if not profile.confirmed:
        raise ValueError("Confirm the profile before recommendations")
    evidence = []
    if snapshot.get("description"):
        evidence.append({"source": snapshot["url"], "type": "website_meta_description",
                         "excerpt": snapshot["description"]})
    if snapshot.get("title"):
        evidence.append({"source": snapshot["url"], "type": "website_title", "excerpt": snapshot["title"]})
    demand = []
    if profile.keywords or profile.pain_points:
        finder = finder or OpportunityFinderEngine()
        try:
            for result in finder.find_opportunities(profile, limit=5, actionable_only=False, persist=False):
                if (result.source_status == "SOURCE_VERIFIED" and result.verification.verified
                        and result.classification in ("RESEARCH_INSIGHT", "ACTIONABLE_OPPORTUNITY")):
                    demand.append({"source": result.original_url, "type": "verified_public_discussion",
                                   "excerpt": result.evidence_excerpt, "routes": result.signal_routes})
        except Exception:
            # Search outages should not turn website observation into fabricated demand.
            pass
    evidence.extend(demand[:3])
    if not profile.description.strip():
        action = "Write a clear, factual description of what the business offers on its own website."
        reason = "The public page did not provide a usable product description; the founder should supply one before stronger acquisition advice."
    elif demand:
        action = "Review the verified customer questions and draft one accurate answer for the business's own website."
        reason = "Verified public discussions contain relevant questions; an owned page can answer them without community outreach."
    else:
        action = "Review the website's product description with the confirmed customer problems and clarify one owned page manually."
        reason = "The founder-confirmed profile and public website are available, but no external demand evidence was verified in this run."
    return {
        "channel": "owned_channel", "action": action, "destination": str(profile.website),
        "reasoning": reason, "evidence": evidence, "confidence": "low" if not demand else "medium",
        "confidence_note": "Heuristic evidence strength, not a calibrated probability or outcome promise.",
        "cost_estimate_inr": 0, "cost_note": "Cash estimate only; founder time is additional.",
        "effort": "30–60 minutes of founder review and manual work",
        "alternatives": ["Add missing business details and rerun research", "Wait for stronger source-verified demand evidence"],
        "permission": "Founder-owned website only; founder must approve exact publication separately.",
        "execution_mode": "MANUAL_ONLY"
    }
