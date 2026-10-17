"""Advisory signal routes; no route grants publication or outreach permission."""
from dataclasses import dataclass
from datetime import datetime, timezone
from founderreach.models import DiscussionItem, ProductProfile


@dataclass(frozen=True)
class SignalRoute:
    routes: tuple[str, ...]
    # Advisory readiness only. Exact action release is exclusively approval_gate.py.
    community_reply_eligible: bool
    reasons: tuple[str, ...]


def route_signal(item: DiscussionItem, profile: ProductProfile, source_verified: bool,
                 direct_problem: bool, relevant: bool, *, source_permission: bool = False,
                 community_rules_checked: bool = False, founder_approved: bool = False,
                 partner_verified_at: datetime | None = None,
                 now: datetime | None = None) -> SignalRoute:
    """Categorize evidence; returned flags never authorize an external action."""
    routes = ["demand_evidence"]
    reasons = []
    if not relevant:
        reasons.append("Relevance is uncertain or below the profile threshold")
    now = now or datetime.now(timezone.utc)
    age = None
    if item.created_at:
        dated = item.created_at if item.created_at.tzinfo else item.created_at.replace(tzinfo=timezone.utc)
        age = (now - dated).days
    if relevant and "owned_channel" in profile.allowed_acquisition_channels:
        routes.append("owned_channel")
    reply_fresh = age is not None and 0 <= age <= profile.reply_max_age_days
    if not reply_fresh:
        reasons.append("Discussion is not verified fresh enough for a reply")
    eligible = all((profile.confirmed, relevant, source_verified, direct_problem, reply_fresh,
                    "community_reply" in profile.allowed_acquisition_channels,
                    source_permission, community_rules_checked, founder_approved))
    if relevant and direct_problem and "community_reply" in profile.allowed_acquisition_channels:
        routes.append("community_reply")
        if not eligible:
            reasons.append("Community reply requires source permission, rule check and founder approval")
    if relevant and "partner_media" in profile.allowed_acquisition_channels:
        routes.append("partner_media")
        partner_age = None
        if partner_verified_at:
            partner_date = (partner_verified_at if partner_verified_at.tzinfo else
                            partner_verified_at.replace(tzinfo=timezone.utc))
            partner_age = (now - partner_date).days
        if partner_age is None or not 0 <= partner_age <= profile.partner_recheck_days:
            reasons.append("Partner or media contact requires current independent verification")
    return SignalRoute(tuple(routes), eligible, tuple(reasons))
