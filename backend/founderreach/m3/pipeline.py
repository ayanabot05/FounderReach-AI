"""One-business local analysis journey from M2 evidence to M4-ready candidates."""
from founderreach.models import ProductProfile
from founderreach.research_store import ResearchStore
from founderreach.m3.site import SiteAuditor
from founderreach.m3.aeo import AEOEngine
from founderreach.m3.geo import GEOEngine, FixedQuestionSet, AICitationObservation
from founderreach.m3.content import ContentOpportunityEngine, ContentAnalysis


def analyze_business(profile: ProductProfile, store: ResearchStore, *, fetcher,
                     approved_origin: str, approved_urls: list[str],
                     question_set: FixedQuestionSet | None = None,
                     citations: list[AICitationObservation] | None = None) -> ContentAnalysis:
    if not profile.confirmed:
        raise PermissionError("A founder-confirmed profile is required")
    observations = store.list_observations(profile.identifier)
    runs = store.list_query_runs(profile.identifier)
    discovery_status = runs[-1].get("status", "not_run") if runs else "not_run"
    site = SiteAuditor(fetcher).audit(profile, approved_origin=approved_origin,
                                      approved_urls=approved_urls)
    aeo = AEOEngine().analyze(profile, observations, site)
    geo = GEOEngine().analyze(profile, site, observations, question_set=question_set,
                              citations=citations)
    return ContentOpportunityEngine().build(profile, observations, site, aeo, geo,
                                            discovery_status=discovery_status)


def analyze_business_with_fixes(profile: ProductProfile, store: ResearchStore, *, fetcher,
                                approved_origin: str, approved_urls: list[str],
                                question_set: FixedQuestionSet | None = None,
                                citations: list[AICitationObservation] | None = None):
    """Return (M3 analysis, evidence-linked fix proposals), without applying changes.

    The original analyze_business API remains unchanged for existing M4 callers.
    The caller must provide an authorized, bounded fetcher and approved URLs.
    """
    from founderreach.m3.fix_recommendations import build_fixes

    analysis = analyze_business(
        profile, store, fetcher=fetcher, approved_origin=approved_origin,
        approved_urls=approved_urls, question_set=question_set, citations=citations,
    )
    return analysis, build_fixes(profile, analysis)
