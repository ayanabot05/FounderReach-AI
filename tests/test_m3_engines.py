from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

import pytest

from founderreach.evidence import EvidenceObservation, founder_attestation, observation_id
from founderreach.m3.aeo import AEOEngine
from founderreach.m3.content import ContentOpportunityEngine, evaluate_labeled_codes
from founderreach.m3.geo import AICitationObservation, FixedQuestionSet, GEOEngine, GEOObservationStore
from founderreach.m3.pipeline import analyze_business
from founderreach.m3.site import (ApprovedSiteFetcher, FixtureSiteFetcher, SiteAuditor,
                                  UnsafeWebsiteError, WebsiteFetchError)
from founderreach.profiles import load_profile
from founderreach.research_store import ResearchStore


def test_page_parser_resumes_after_non_jsonld_script():
    from founderreach.m3.site import _PageParser
    parser = _PageParser("https://example.com/")
    parser.feed('<script src="/app.js"></script><title>Example home</title>'
                '<main><h1>Automated scheduling</h1><p>Daily check-ins</p></main>')
    assert parser.title == "Example home"
    assert parser.headings == [("h1", "Automated scheduling")]
    assert parser.paragraphs == ["Daily check-ins"]


def test_script_src_before_title_and_h1_still_observed_and_counted_by_site_auditor():
    profile = load_profile("scheduleflow")
    origin_url = profile_origin(profile)
    page_url = f"{origin_url}/"
    html_body = (
        "<!doctype html><html><head>"
        '<script src="/head-bundle.js"></script>'
        "<title>ScheduleFlow Home</title>"
        '<meta name="description" content="Coordinate recurring bookings.">'
        f'<link rel="canonical" href="{page_url}">'
        "</head><body>"
        '<script src="/body-init.js"></script>'
        "<h1>Automated Scheduling for Teams</h1>"
        "<p>Prevent manual handoff delays.</p>"
        "</body></html>"
    )
    fetcher = FixtureSiteFetcher({
        f"{origin_url}/robots.txt": (200, "text/plain", "User-agent: *\nAllow: /\n"),
        f"{origin_url}/sitemap.xml": (
            200,
            "application/xml",
            f"<urlset><url><loc>{page_url}</loc></url></urlset>",
        ),
        page_url: (200, "text/html", html_body),
    })
    audit = SiteAuditor(fetcher).audit(
        profile,
        approved_origin=origin_url,
        approved_urls=[page_url],
    )
    assert len(audit.pages) == 1
    page = audit.pages[0]
    assert page.title == "ScheduleFlow Home"
    assert page.headings == [("h1", "Automated Scheduling for Teams")]
    assert len([text for tag, text in page.headings if tag == "h1"]) == 1
    finding_codes = {finding.code for finding in audit.findings}
    assert "metadata" not in finding_codes
    assert "heading_structure" not in finding_codes



NOW = datetime.now(timezone.utc)


def profile_origin(profile):
    split = urlsplit(str(profile.website))
    return f"{split.scheme}://{split.hostname}"


def evidence(profile, claim, *, kind="customer_question", source="hn_83", verified=True,
             freshness="timely", permission="allowed"):
    native = f"hacker-news:{source}"
    return EvidenceObservation(observation_id=observation_id(profile.identifier, native, kind, claim),
        business_id=profile.identifier, source_id=native, source_key="hackernews", source_policy_version=1,
        kind=kind, provenance="public_api", source_url=f"https://news.ycombinator.com/item?id={source[3:]}",
        excerpt=claim, claim=claim, published_at=NOW - timedelta(days=2 if freshness == "timely" else 200),
        verification_state="verified" if verified else "stale",
        verification_method="hn_exact_quote" if verified else None,
        verified_at=NOW - timedelta(hours=1) if verified else None,
        verification_expires_at=NOW + timedelta(hours=23) if verified else None,
        relevance_state="matched", freshness_state=freshness, permission_state=permission,
        allowed_uses=["research", "owned_content_planning"] if permission == "allowed" else [],
        routes=["demand_evidence", "owned_content_research"])


def site_fixture(profile, *, answer=False, broken_canonical=False, noindex=False,
                 sitemap=True, duplicate=False, conflict=False, brand_mismatch=False,
                 blocked=False, inaccessible=False, unsupported=False):
    base = profile_origin(profile)
    home = base + "/"
    answer_url = base + "/answers"
    question = "How can I reduce missed client appointments with automated reminders?" if profile.identifier == "scheduleflow" else \
               "How can I make sure my parents in India take medicine every day?"
    page_name = "Other Brand" if brand_mismatch else profile.name
    organization = '{"@context":"https://schema.org","@graph":[{"@type":"Organization","name":"' + \
                   page_name + '"},{"@type":"WebSite","url":"' + base + '"}]}'
    home_html = f'''<html><head><title>Home | {page_name}</title><meta name="description" content="Official site">
        <link rel="canonical" href="{base + '/wrong' if broken_canonical else home}">
        <script type="application/ld+json">{organization}</script></head>
        <body><h1>{page_name}</h1><p>Contact us at hello@{urlsplit(base).hostname} for factual company details.</p>
        <a href="{answer_url}">Answers</a><a href="mailto:hello@example.com">Email</a></body></html>'''
    answer_text = ("You can reduce missed client appointments by sending an automated reminder before each booking and confirming the time with clients."
                   if profile.identifier == "scheduleflow" else
                   "Families can use a daily medicine reminder and confirm with their parent that each dose was taken before marking the check-in complete.")
    if conflict:
        answer_text = "ScheduleFlow does not support SMS reminders for appointment booking. Ask the team for current options."
    if unsupported:
        answer_text += " Results are guaranteed 99% effective."
    answer_html = f'''<html><head><title>{question} | {profile.name}</title>
        <meta name="description" content="A factual answer"><meta name="robots" content="{'noindex' if noindex else 'index,follow'}">
        <link rel="canonical" href="{answer_url}"></head><body><h1>{question}</h1>
        <p>{answer_text}</p></body></html>'''
    robots = "User-agent: *\nDisallow: /answers" if blocked else "User-agent: *\nAllow: /"
    sitemap_xml = f'<urlset><url><loc>{home}</loc></url><url><loc>{answer_url}</loc></url></urlset>'
    pages = {base + "/robots.txt": (200, "text/plain", robots),
             base + "/sitemap.xml": (200, "application/xml", sitemap_xml) if sitemap else (404, "text/plain", ""),
             home: (200, "text/html", home_html),
             answer_url: (503, "text/html", "") if inaccessible else (200, "text/html", answer_html)}
    urls = [home]
    if answer or blocked or inaccessible or noindex or conflict or unsupported:
        urls.append(answer_url)
    if duplicate:
        dup_url = base + "/duplicate"
        pages[dup_url] = (200, "text/html", answer_html.replace(answer_url, dup_url))
        urls.extend([answer_url, dup_url])
    return FixtureSiteFetcher(pages), base, urls


def test_complete_ayana_journey_missing_answer_and_review_candidate(tmp_path):
    profile = load_profile("ayana")
    store = ResearchStore(tmp_path / "m3.db")
    question = "How can I make sure my parents in India take medicine every day?"
    item = evidence(profile, question)
    store.save_observation(item)
    fetcher, base, urls = site_fixture(profile)
    result = analyze_business(profile, store, fetcher=fetcher, approved_origin=base, approved_urls=urls)
    assert result.site.business_id == result.aeo.business_id == result.geo.business_id == "ayana"
    assert any(x.code == "missing_page" for x in result.aeo.findings)
    assert any(x.code == "content_gap" for x in result.site.findings)
    assert len(result.opportunities) == 1
    candidate = result.opportunities[0]
    assert candidate.proposed_acquisition_action == "create_owned_page"
    assert candidate.source_observation_ids == [item.observation_id]
    assert candidate.review_status == "pending_human_review" and candidate.execution_mode == "LOCAL_REVIEW_ONLY"
    assert result.evidence_coverage == 1 and result.unsupported_claim_rate == 0
    assert result.geo.ai_visibility == "unknown" and result.geo.citation_observations == []


def test_scheduleflow_good_existing_answer_and_no_competing_page(tmp_path):
    profile = load_profile("scheduleflow")
    store = ResearchStore(tmp_path / "m3.db")
    question = "How can I reduce missed client appointments with automated reminders?"
    for native in ("hn_83", "hn_84"):
        store.save_observation(evidence(profile, question, source=native))
    fetcher, base, urls = site_fixture(profile, answer=True)
    result = analyze_business(profile, store, fetcher=fetcher, approved_origin=base, approved_urls=urls)
    assert len(result.aeo.clusters) == 1 and result.aeo.clusters[0].direct_answer_observed
    assert len(result.opportunities) == 1
    assert result.opportunities[0].existing_page == base + "/answers"
    assert result.opportunities[0].proposed_page_topic is None
    assert result.opportunities[0].proposed_acquisition_action == "improve_owned_page"
    assert len(result.opportunities[0].source_observation_ids) == 2


def test_aeo_paraphrases_cluster_by_question_intent():
    profile = load_profile("scheduleflow")
    first = evidence(profile, "How can I reduce missed client appointments with automated reminders?")
    second = evidence(profile, "How do reminders reduce missed appointments for my clients?", source="hn_84")
    fetcher, base, urls = site_fixture(profile)
    audit = SiteAuditor(fetcher).audit(profile, approved_origin=base, approved_urls=urls)
    report = AEOEngine().analyze(profile, [first, second], audit)
    assert len(report.clusters) == 1
    assert set(report.clusters[0].observation_ids) == {first.observation_id, second.observation_id}


def test_matching_page_without_direct_answer_is_detected():
    profile = load_profile("scheduleflow")
    question = "How can I reduce missed client appointments with automated reminders?"
    item = evidence(profile, question)
    fetcher, base, urls = site_fixture(profile, answer=True)
    answer_url = base + "/answers"
    html = fetcher.pages[answer_url][2]
    html = html.replace("You can reduce missed client appointments by sending an automated reminder before each booking and confirming the time with clients.",
                        "Please explore our services and contact us for details.")
    fetcher.pages[answer_url] = (200, "text/html", html)
    audit = SiteAuditor(fetcher).audit(profile, approved_origin=base, approved_urls=urls)
    report = AEOEngine().analyze(profile, [item], audit)
    assert report.clusters[0].matching_page == answer_url
    assert not report.clusters[0].direct_answer_observed
    assert any(x.code == "missing_direct_answer" for x in report.findings)


def test_multiple_intents_on_one_page_consolidate_candidates():
    profile = load_profile("scheduleflow")
    first = evidence(profile, "How can I reduce missed client appointments with automated reminders?")
    second = evidence(profile, "What appointment booking options help independent consultants?", source="hn_84")
    fetcher, base, urls = site_fixture(profile, answer=True)
    audit = SiteAuditor(fetcher).audit(profile, approved_origin=base, approved_urls=urls)
    aeo = AEOEngine().analyze(profile, [first, second], audit)
    assert len(aeo.clusters) == 2
    # Both distinct intents have been assigned to one existing page for consolidation.
    for cluster in aeo.clusters:
        cluster.matching_page = base + "/answers"
    geo = GEOEngine().analyze(profile, audit, [first, second])
    content = ContentOpportunityEngine().build(profile, [first, second], audit, aeo, geo)
    assert len(content.opportunities) == 1
    assert set(content.opportunities[0].source_observation_ids) == {first.observation_id, second.observation_id}


def test_seo_broken_canonical_missing_sitemap_noindex_duplicate():
    profile = load_profile("scheduleflow")
    fetcher, base, urls = site_fixture(profile, answer=True, broken_canonical=True,
                                       noindex=True, sitemap=False, duplicate=True)
    audit = SiteAuditor(fetcher).audit(profile, approved_origin=base, approved_urls=urls)
    codes = {finding.code for finding in audit.findings}
    assert {"canonical", "missing_sitemap", "noindex"} <= codes
    assert "duplicate_content" in codes or "competing_content" in codes
    assert all(x.observed_evidence and x.suggested_correction and x.verification_method for x in audit.findings)


def test_robots_restricted_and_inaccessible_pages_are_not_silent():
    profile = load_profile("scheduleflow")
    fetcher, base, urls = site_fixture(profile, blocked=True)
    audit = SiteAuditor(fetcher).audit(profile, approved_origin=base, approved_urls=urls)
    assert any(x.code == "robots_blocked" for x in audit.findings)
    assert base + "/answers" not in {x.url for x in audit.pages}
    fetcher, base, urls = site_fixture(profile, inaccessible=True)
    audit = SiteAuditor(fetcher).audit(profile, approved_origin=base, approved_urls=urls)
    assert audit.state == "partial"
    assert any(x.code == "inaccessible_page" for x in audit.findings)


def test_seo_metadata_heading_orphan_and_bad_structured_data():
    profile = load_profile("scheduleflow")
    fetcher, base, urls = site_fixture(profile, answer=True)
    orphan_url = base + "/orphan"
    fetcher.pages[orphan_url] = (200, "text/html", '''<html><head><title>Orphan | ScheduleFlow</title>
        <link rel="canonical" href="''' + orphan_url + '''"><script type="application/ld+json">{bad}</script></head>
        <body><h2>Secondary heading only</h2><p>Short factual page.</p></body></html>''')
    audit = SiteAuditor(fetcher).audit(profile, approved_origin=base, approved_urls=urls + [orphan_url])
    codes = {x.code for x in audit.findings if x.affected_url == orphan_url}
    assert {"metadata", "heading_structure", "orphan_page", "invalid_jsonld", "sitemap_omission"} <= codes


def test_http_noindex_header_is_an_indexability_signal():
    profile = load_profile("scheduleflow")
    fetcher, base, urls = site_fixture(profile, answer=True)
    answer_url = base + "/answers"
    status, content_type, html = fetcher.pages[answer_url]
    fetcher.pages[answer_url] = (status, content_type, html, {"x-robots-tag": "noindex, nofollow"})
    audit = SiteAuditor(fetcher).audit(profile, approved_origin=base, approved_urls=urls)
    assert any(x.code == "noindex" and x.affected_url == answer_url for x in audit.findings)


def test_aeo_conflict_unsupported_claim_and_attested_alternative():
    profile = load_profile("scheduleflow")
    claim = "ScheduleFlow supports SMS reminders for appointment booking"
    item = evidence(profile, claim)
    fetcher, base, urls = site_fixture(profile, conflict=True, unsupported=True)
    audit = SiteAuditor(fetcher).audit(profile, approved_origin=base, approved_urls=urls)
    report = AEOEngine().analyze(profile, [item], audit)
    codes = {finding.code for finding in report.findings}
    assert "contradictory_answer" in codes
    assert "unsupported_answer_claim" in codes
    attested = founder_attestation(business=profile.identifier, native_id="f1", excerpt=claim,
                                   claim=claim, attested_by="founder")
    alternative = AEOEngine().analyze(profile, [attested], audit)
    assert alternative.clusters[0].evidence_state == "founder_attested_alternative"
    content = ContentOpportunityEngine().build(profile, [attested], audit, alternative,
                                                GEOEngine().analyze(profile, audit, [attested]))
    assert content.opportunities[0].proposed_acquisition_action == "research_only"
    assert content.opportunities[0].permission_state == "unknown_attested"
    assert content.unsupported_claim_rate == 1


def test_geo_brand_schema_third_party_and_unknown_citations():
    profile = load_profile("scheduleflow")
    fetcher, base, urls = site_fixture(profile, brand_mismatch=True)
    audit = SiteAuditor(fetcher).audit(profile, approved_origin=base, approved_urls=urls)
    report = GEOEngine().analyze(profile, audit, [])
    codes = {x.code for x in report.readiness_findings}
    assert "brand_name_mismatch" in codes and "schema_brand_mismatch" in codes
    assert "missing_third_party_evidence" in codes
    assert report.ai_visibility == "unknown" and report.historical_comparison == {}
    assert any(x.entity_type == "organization" and x.provenance == "owned_site_schema" for x in report.entities)
    mention = evidence(profile, "ScheduleFlow was independently mentioned by a third-party publisher",
                       kind="third_party_mention")
    with_mention = GEOEngine().analyze(profile, audit, [mention])
    assert mention.observation_id in with_mention.third_party_observation_ids


def test_geo_product_entities_and_contact_consistency():
    profile = load_profile("scheduleflow")
    fetcher, base, urls = site_fixture(profile, answer=True)
    answer_url = base + "/answers"
    old = fetcher.pages[answer_url][2]
    enriched = old.replace("</body>", '''<script type="application/ld+json">
        {"@context":"https://schema.org","@type":"Product","name":"ScheduleFlow"}</script>
        <p>Contact sales@another.example for product details.</p></body>''')
    fetcher.pages[answer_url] = (200, "text/html", enriched)
    audit = SiteAuditor(fetcher).audit(profile, approved_origin=base, approved_urls=urls)
    report = GEOEngine().analyze(profile, audit, [])
    assert any(x.entity_type == "product" and x.provenance == "owned_site_schema" for x in report.entities)
    assert any(x.code == "contact_inconsistency" for x in report.readiness_findings)


def test_fixed_question_set_and_citation_provenance_validation():
    question = "What is ScheduleFlow?"
    fixed = FixedQuestionSet(business_id="scheduleflow", version=1, questions=[question])
    with pytest.raises(ValueError):
        FixedQuestionSet(business_id="scheduleflow", version=1, questions=[question, question])
    with pytest.raises(ValueError):
        AICitationObservation(business_id="scheduleflow", question_set_version=1, question=question,
            provider="fixture", answer_excerpt="fixture answer", citation_url="https://example.com/",
            captured_at=NOW, capture_method="simulation")
    profile = load_profile("scheduleflow")
    fetcher, base, urls = site_fixture(profile)
    audit = SiteAuditor(fetcher).audit(profile, approved_origin=base, approved_urls=urls)
    report = GEOEngine().analyze(profile, audit, [], question_set=fixed)
    assert report.ai_visibility == "unknown" and report.citation_observations == []


def test_question_set_versions_and_actual_history_are_business_scoped(tmp_path):
    manager = GEOObservationStore(tmp_path / "geo.db")
    fixed = FixedQuestionSet(business_id="scheduleflow", version=1, questions=["What is ScheduleFlow?"])
    manager.save_question_set(fixed)
    assert manager.latest_question_set("ayana") is None
    with pytest.raises(ValueError):
        manager.save_question_set(fixed.model_copy(update={"questions": ["A changed question?"]}))
    # These are labeled local schema fixtures, not observations of a real AI service.
    captures = [AICitationObservation(business_id="scheduleflow", question_set_version=1,
        question="What is ScheduleFlow?", provider="fixture-only", answer_excerpt="fixture answer",
        citation_url="https://example.com/", captured_at=NOW - timedelta(days=days)) for days in (2, 1)]
    for capture in captures:
        manager.add_citation(capture)
    assert len(manager.list_citations("scheduleflow", 1)) == 2
    assert manager.list_citations("ayana", 1) == []
    with pytest.raises(LookupError):
        manager.add_citation(captures[0].model_copy(update={"business_id": "ayana"}))
    profile = load_profile("scheduleflow")
    fetcher, base, urls = site_fixture(profile)
    audit = SiteAuditor(fetcher).audit(profile, approved_origin=base, approved_urls=urls)
    report = GEOEngine().analyze(profile, audit, [], question_set=fixed,
                                 citations=manager.list_citations("scheduleflow", 1))
    assert report.historical_comparison["actual_observation_count"] == 2
    assert report.ai_visibility == "observed_citations"


def test_empty_stale_blocked_and_source_outage_are_honest(tmp_path):
    profile = load_profile("ayana")
    store = ResearchStore(tmp_path / "m3.db")
    stale = evidence(profile, "How can I check on my parents?", verified=False)
    blocked = evidence(profile, "How can I remind my parents of medicine?", source="hn_84", permission="blocked")
    store.save_observation(stale)
    store.save_observation(blocked)
    store.log_query_run("ayana", "hackernews", {"status": "unavailable", "diagnostics": []})
    fetcher, base, urls = site_fixture(profile)
    result = analyze_business(profile, store, fetcher=fetcher, approved_origin=base, approved_urls=urls)
    assert result.opportunities == [] and result.status == "source_unavailable"
    assert "No-demand inference" not in str(result.model_dump())
    assert result.aeo.excluded_observation_ids == [stale.observation_id, blocked.observation_id] or set(
        result.aeo.excluded_observation_ids) == {stale.observation_id, blocked.observation_id}
    assert any("no-demand inference" in x for x in result.limitations)


def test_cross_business_and_site_scope_fail_closed(tmp_path):
    ayana = load_profile("ayana")
    saas = load_profile("scheduleflow")
    fetcher, base, urls = site_fixture(ayana)
    with pytest.raises(PermissionError):
        SiteAuditor(fetcher).audit(ayana, approved_origin=profile_origin(saas), approved_urls=urls)
    with pytest.raises(UnsafeWebsiteError):
        SiteAuditor(fetcher).audit(ayana, approved_origin=base, approved_urls=urls + [profile_origin(saas)])
    store = ResearchStore(tmp_path / "m3.db")
    store.save_observation(evidence(saas, "How do I book my clients?"))
    result = analyze_business(ayana, store, fetcher=fetcher, approved_origin=base, approved_urls=urls)
    assert result.opportunities == [] and result.business_id == "ayana"


def test_live_fetch_guard_rejects_loopback_redirect_and_oversized_response(monkeypatch):
    live = ApprovedSiteFetcher("https://example.com")
    with pytest.raises(UnsafeWebsiteError):
        live.fetch("https://127.0.0.1/private")
    monkeypatch.setattr(live._network, "_target", lambda url: (url, "example.com", 443, "93.184.215.14", "/"))
    monkeypatch.setattr(live._network, "_request", lambda *args: (302, {"location": "http://127.0.0.1/admin"}, b""))
    with pytest.raises(UnsafeWebsiteError):
        live.fetch("https://example.com/")
    monkeypatch.setattr(live._network, "_request", lambda *args: (200, {"content-type": "text/html"}, b"x" * 512_001))
    with pytest.raises(WebsiteFetchError):
        live.fetch("https://example.com/")
    live.request_count = live.max_requests
    monkeypatch.setattr(live._network, "_request", lambda *args: pytest.fail("budget allowed a request"))
    with pytest.raises(WebsiteFetchError):
        live.fetch("https://example.com/")
    monkeypatch.setattr(live._network, "_request", lambda *args: (_ for _ in ()).throw(
        WebsiteFetchError("Website could not be reached within the time limit")))
    with pytest.raises(WebsiteFetchError):
        live.fetch("https://example.com/")


def test_inventory_budget_and_unsupported_content_type():
    profile = load_profile("scheduleflow")
    fetcher, base, urls = site_fixture(profile)
    with pytest.raises(ValueError):
        SiteAuditor(fetcher).audit(profile, approved_origin=base,
                                   approved_urls=[base + f"/page-{i}" for i in range(21)])
    fetcher.pages[base + "/"] = (200, "application/pdf", "%PDF")
    audit = SiteAuditor(fetcher).audit(profile, approved_origin=base, approved_urls=urls)
    assert audit.state == "partial" and any(x.code == "inaccessible_page" for x in audit.findings)


def test_fixture_classification_quality_measure():
    profile = load_profile("scheduleflow")
    fetcher, base, urls = site_fixture(profile, answer=True, broken_canonical=True,
                                       noindex=True, sitemap=False, duplicate=True)
    audit = SiteAuditor(fetcher).audit(profile, approved_origin=base, approved_urls=urls)
    actual = {x.code for x in audit.findings}
    # Labeled fixture target classes; unrelated audit findings are evaluated elsewhere.
    universe = {"canonical", "noindex", "missing_sitemap", "duplicate_content", "robots_blocked"}
    measured = evaluate_labeled_codes(sorted(actual & universe),
                                      ["canonical", "noindex", "missing_sitemap", "duplicate_content"])
    assert measured == {"precision": 1, "recall": 1, "f1": 1}
