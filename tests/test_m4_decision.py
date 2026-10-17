"""M4 fixture-only decisions; no live source, posting or contact."""
import base64
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from founderreach.approval_gate import Approval, approval_message
from founderreach.evidence import EvidenceObservation, observation_id
from founderreach.m3.pipeline import analyze_business
from founderreach.m3.site import FixtureSiteFetcher
from founderreach.m4.candidates import CandidateFactory, DecisionContext, OwnedChannelCapability
from founderreach.m4.contracts import make_candidate
from founderreach.m4.decision import AcquisitionDecisionEngine
from founderreach.m4.gate_bridge import prepare_existing_gate_run, review_packet
from founderreach.m4.evaluation import compare_human_labels
from founderreach.placements import placement_from_evidence
from founderreach.profiles import load_profile
from founderreach.research_store import ResearchStore
from founderreach.source_registry import SourcePolicy, SourceRegistry, REGISTRY_DIR


NOW = datetime.now(timezone.utc)


@pytest.fixture(autouse=True)
def historical_policy_for_controlled_m4_fixtures(monkeypatch):
    """The live registry is held; these fixture comparisons simulate permitted v1 research."""
    prior_get = SourceRegistry.get
    approved = SourcePolicy.model_validate_json((REGISTRY_DIR / "hackernews.v1.json").read_text(encoding="utf-8"))
    def get(self, key):
        return approved if key == "hackernews" else prior_get(self, key)
    monkeypatch.setattr(SourceRegistry, "get", get)


def origin(profile):
    parts = urlsplit(str(profile.website))
    return f"{parts.scheme}://{parts.hostname}"


def verified(profile, claim, native="91", *, kind="customer_question", freshness="timely",
             permission="allowed"):
    source = f"hacker-news:hn_{native}"
    return EvidenceObservation(observation_id=observation_id(profile.identifier, source, kind, claim),
        business_id=profile.identifier, source_id=source, source_key="hackernews", source_policy_version=1,
        kind=kind, provenance="public_api", source_url=f"https://news.ycombinator.com/item?id={native}",
        excerpt=claim, claim=claim, published_at=NOW - timedelta(days=2 if freshness == "timely" else 200),
        verification_state="verified", verification_method="hn_exact_quote",
        verified_at=NOW - timedelta(hours=1), verification_expires_at=NOW + timedelta(hours=23),
        relevance_state="matched", freshness_state=freshness, permission_state=permission,
        allowed_uses=["research", "owned_content_planning"] if permission == "allowed" else [],
        routes=["demand_evidence", "owned_content_research"])


def fixture_site(profile, *, existing_answer=False, broken_canonical=False):
    base = origin(profile)
    home = base + "/"
    answer = base + "/answer"
    claim = ("How can I reduce missed client appointments with reminders?" if profile.identifier == "scheduleflow"
             else "How can I check that my parents in India took their medicine today?")
    home_html = f'''<html><head><title>Home | {profile.name}</title><meta name="description" content="Official site">
        <link rel="canonical" href="{base + '/other' if broken_canonical else home}"></head>
        <body><h1>{profile.name}</h1><p>Official product and contact information for {profile.name}.</p>
        <a href="{answer}">Answer</a></body></html>'''
    answer_html = f'''<html><head><title>{claim} | {profile.name}</title><meta name="description" content="Answer">
        <link rel="canonical" href="{answer}"></head><body><h1>{claim}</h1>
        <p>You can reduce missed client appointments by sending a reminder before each booking and confirming the appointment with each client.</p></body></html>'''
    sitemap = f'<urlset><url><loc>{home}</loc></url><url><loc>{answer}</loc></url></urlset>'
    pages = {base + "/robots.txt": (200, "text/plain", "User-agent: *\nAllow: /"),
             base + "/sitemap.xml": (200, "application/xml", sitemap),
             home: (200, "text/html", home_html), answer: (200, "text/html", answer_html)}
    return FixtureSiteFetcher(pages), base, [home, answer] if existing_answer else [home], claim


def context(tmp_path, business="scheduleflow", *, existing_answer=False, broken_canonical=False,
            social=False, discovery="success"):
    profile = load_profile(business)
    fetcher, base, urls, question = fixture_site(profile, existing_answer=existing_answer,
                                                  broken_canonical=broken_canonical)
    obs = verified(profile, question)
    store = ResearchStore(tmp_path / f"{business}.db")
    store.save_observation(obs)
    store.log_query_run(profile.identifier, "hackernews", {"status": discovery, "diagnostics": []})
    analysis = analyze_business(profile, store, fetcher=fetcher, approved_origin=base, approved_urls=urls)
    capabilities = ([OwnedChannelCapability(business_id=business, account_url="https://social.example/" + business,
        owner_confirmed=True, planning_permission=True, checked_at=NOW - timedelta(hours=1),
        expires_at=NOW + timedelta(days=1), verification_method="founder_confirmed_account",
        measurement_ready=True)] if social else [])
    return DecisionContext(profile=profile, observations=[obs], content=analysis,
                           owned_channels=capabilities, discovery_status=discovery,
                           site_evidence_mode="fixture")


def clone_candidate(candidate, **changes):
    payload = candidate.model_dump(mode="json", exclude={"candidate_id", "action_id"})
    payload.update(changes)
    return make_candidate(**payload)


def test_ayana_and_scheduleflow_journey_isolated(tmp_path):
    engine = AcquisitionDecisionEngine()
    ayana = context(tmp_path, "ayana")
    saas = context(tmp_path, "scheduleflow")
    for bundle in (ayana, saas):
        decision = engine.decide(bundle)
        assert decision.primary is not None and decision.status == "recommended"
        assert decision.primary.candidate.business_id == bundle.profile.identifier
        assert decision.primary.eligibility.external_release_eligible is False
        assert review_packet(decision)["approved"] is False
        assert len(decision.alternatives) <= 3
    assert engine.decide(ayana).primary.candidate.candidate_id != engine.decide(saas).primary.candidate.candidate_id
    mixed = CandidateFactory().build(saas)[0]
    assert not engine.eligibility(ayana, mixed).local_action_eligible


def test_website_and_social_win_in_different_supported_scenarios(tmp_path):
    engine = AcquisitionDecisionEngine()
    website = engine.decide(context(tmp_path / "web", social=False))
    social = engine.decide(context(tmp_path / "social", social=True))
    assert website.primary.candidate.channel == "owned_website"
    assert social.primary.candidate.channel == "owned_social"
    assert {x.candidate.channel for x in social.alternatives} >= {"owned_website"}
    assert "customer_fit=" in social.why_primary and "measurement=" in social.why_primary
    assert social.why_alternatives_lower


def test_supported_channels_only_and_placement_requires_actual_evidence(tmp_path):
    bundle = context(tmp_path)
    factory = CandidateFactory()
    assert {x.channel for x in factory.build(bundle)} == {"owned_website", "community_research"}
    item = verified(bundle.profile, "ScheduleFlow is listed in a real directory", native="92",
                    kind="placement_opportunity")
    placement = placement_from_evidence(item, kind="directory", target_name="Observed directory",
                                        target_url=str(item.source_url), rationale="Observed listing")
    bundle.observations.append(item)
    bundle.placements.append(placement)
    channels = {x.channel for x in factory.build(bundle)}
    assert "directory" in channels and "newsletter" not in channels and "media" not in channels
    directory = next(x for x in factory.build(bundle) if x.channel == "directory")
    assert directory.action_scope == "internal_research" and "permission" in directory.proposed_action.lower()


def test_technical_seo_and_answer_candidates_need_site_and_demand(tmp_path):
    bundle = context(tmp_path, existing_answer=True, broken_canonical=True)
    candidates = CandidateFactory().build(bundle)
    assert "owned_website" in {x.channel for x in candidates}
    assert any(x.channel == "technical_seo" for x in candidates) is False  # Homepage issue is not tied to answer URL.
    answer = bundle.content.site.pages[1].url
    from founderreach.m3.site import SEOFinding
    finding = SEOFinding(code="canonical", affected_url=answer, observed_evidence="wrong canonical",
        problem="Incorrect canonical", severity="high", suggested_correction="Correct canonical", confidence=0.95,
        limitations="Fixture", estimated_effort="small", verification_method="HTML check")
    bundle.content.site.findings.append(finding)
    bundle.content.opportunities[0].related_seo_codes.append("canonical")
    candidates = CandidateFactory().build(bundle)
    assert any(x.channel == "technical_seo" for x in candidates)


def test_stale_permission_blocked_and_policy_changed_fail_closed(tmp_path):
    bundle = context(tmp_path)
    engine = AcquisitionDecisionEngine()
    candidate = CandidateFactory().build(bundle)[0]
    stale = bundle.observations[0].model_copy(update={"verification_expires_at": NOW - timedelta(minutes=1)})
    bundle.observations = [stale]
    result = engine.eligibility(bundle, candidate)
    assert not result.local_action_eligible and any("changed" in x or "stale" in x for x in result.reasons)
    bundle.observations = [stale.model_copy(update={"verification_expires_at": NOW + timedelta(hours=1),
                                            "permission_state": "blocked", "allowed_uses": []})]
    assert not engine.eligibility(bundle, candidate).local_action_eligible
    bundle.observations = [verified(bundle.profile, fixture_site(bundle.profile)[3])]
    wrong_policy = bundle.observations[0].model_copy(update={"source_policy_version": 99})
    bundle.observations = [wrong_policy]
    assert any("policy" in x.lower() for x in engine.eligibility(bundle, candidate).reasons)


def test_research_permission_does_not_grant_owned_content_planning(tmp_path):
    from founderreach.source_registry import SourceRegistry
    bundle = context(tmp_path)
    candidate = next(x for x in CandidateFactory().build(bundle) if x.channel == "owned_website")
    policy = SourceRegistry().get("hackernews")
    research_only = policy.model_copy(update={"allowed_uses": ["research"]})
    class ResearchOnlyRegistry:
        def get(self, key):
            return research_only if key == "hackernews" else None
    result = AcquisitionDecisionEngine(registry=ResearchOnlyRegistry()).eligibility(bundle, candidate)
    assert not result.local_action_eligible
    assert any("forbids owned-content planning" in reason for reason in result.reasons)


def test_unknown_cost_and_paid_cost_never_enter_ranked_set(tmp_path):
    bundle = context(tmp_path)
    engine = AcquisitionDecisionEngine()
    candidate = CandidateFactory().build(bundle)[0]
    for cost in (None, 0.01):
        changed = clone_candidate(candidate, estimated_cash_cost_inr=cost)
        result = engine.decide(bundle, [changed])
        assert result.primary is None and result.status == "no_eligible_action"
        assert any("cost" in reason.lower() or "spend" in reason.lower()
                   for row in result.rejected for reason in row["reasons"])
    with pytest.raises(ValueError):
        clone_candidate(candidate, estimated_cash_cost_inr=float("nan"))
    with pytest.raises(ValueError):
        clone_candidate(candidate, estimated_cash_cost_inr=float("inf"))


def test_invented_channel_and_edited_m3_opportunity_rejected(tmp_path):
    bundle = context(tmp_path)
    engine = AcquisitionDecisionEngine()
    candidate = next(x for x in CandidateFactory().build(bundle) if x.channel == "owned_website")
    invented = clone_candidate(candidate, channel="paid_ad", action_type="launch_paid_campaign")
    assert any("Unsupported channel" in x for x in engine.eligibility(bundle, invented).reasons)
    forged_copy = clone_candidate(candidate, proposed_action="Contact the customer directly")
    assert any("current business evidence" in x for x in engine.eligibility(bundle, forged_copy).reasons)
    bundle.content.opportunities[0].search_or_answer_intent = "Edited after candidate construction"
    assert any("M3 content opportunity changed" in x for x in engine.eligibility(bundle, candidate).reasons)


def test_unknown_site_mode_and_expired_social_access_rejected(tmp_path):
    bundle = context(tmp_path, social=True)
    engine = AcquisitionDecisionEngine()
    website = next(x for x in CandidateFactory().build(bundle) if x.channel == "owned_website")
    bundle.site_evidence_mode = "unknown"
    assert not engine.eligibility(bundle, website).local_action_eligible
    bundle.site_evidence_mode = "fixture"
    social = next(x for x in CandidateFactory().build(bundle) if x.channel == "owned_social")
    bundle.owned_channels[0].expires_at = NOW - timedelta(minutes=1)
    assert any("access" in x.lower() for x in engine.eligibility(bundle, social).reasons)


def test_duplicate_candidates_consolidated_without_invalid_shadowing(tmp_path):
    bundle = context(tmp_path)
    engine = AcquisitionDecisionEngine()
    good = CandidateFactory().build(bundle)[0]
    bad = clone_candidate(good, estimated_cash_cost_inr=None)
    decision = engine.decide(bundle, [bad, good, good])
    assert decision.primary.candidate.action_id == good.action_id
    assert len(decision.alternatives) == 0
    assert any("Duplicate" in str(x["reasons"]) for x in decision.rejected)


def test_conflicting_claim_blocks_content_but_allows_internal_review(tmp_path):
    bundle = context(tmp_path)
    from founderreach.m3.aeo import AEOFinding
    obs_id = bundle.observations[0].observation_id
    bundle.content.aeo.findings.append(AEOFinding(code="contradictory_answer", question=bundle.observations[0].claim,
        observation_ids=[obs_id], observed_evidence="Conflicting page statement",
        recommendation="Resolve before draft", confidence=0.75,
        limitations="Human review", affected_url=bundle.content.site.approved_origin))
    decision = AcquisitionDecisionEngine().decide(bundle)
    assert all(x.candidate.channel != "owned_website" for x in [decision.primary] + decision.alternatives if x)
    assert any("Contradictory" in str(x["reasons"]) for x in decision.rejected)
    assert decision.primary.candidate.channel == "community_research"


def test_empty_outage_and_unsupported_evidence_are_honest(tmp_path):
    bundle = context(tmp_path)
    bundle.discovery_status = "unavailable"
    bundle.observations = []
    bundle.content = None
    decision = AcquisitionDecisionEngine().decide(bundle)
    assert decision.primary is None and decision.alternatives == []
    assert decision.status == "source_unavailable" and decision.discovery_status == "unavailable"
    assert CandidateFactory().build(bundle) == []


def baseline(tmp_path):
    file = tmp_path / "baseline.json"
    file.write_text(json.dumps({"founder_id": "tester", "start_time": "10:00", "stop_time": "10:45",
        "active_minutes": 45, "sources": ["fixture"], "selected_action": "Manual review",
        "draft_outline": "Outline", "cta": "CTA", "measurement_plan": "local only",
        "seen_prior_recommendation": "yes"}), encoding="utf-8")
    return file


def test_existing_signed_gate_binds_exact_m4_action_and_rejects_forgery(tmp_path, monkeypatch):
    profile = load_profile("scheduleflow")
    question = "How can I reduce missed client appointments with reminders?"
    item = verified(profile, question)
    bundle = DecisionContext(profile=profile, observations=[item], discovery_status="success")
    decision = AcquisitionDecisionEngine().decide(bundle)
    assert decision.primary.candidate.channel == "community_research"
    action = decision.primary.candidate
    run = prepare_existing_gate_run(decision, bundle, baseline_artifact=str(baseline(tmp_path)),
                                    exact_human_copy="Review this question internally", destination=action.target_url)
    assert run.action and run.approval is None and run.preflight is None
    with pytest.raises(PermissionError):
        run.manual_execution_packet()
    key = Ed25519PrivateKey.generate()
    public = base64.b64encode(key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)).decode()
    monkeypatch.setenv("FOUNDERREACH_CEO_PUBLIC_KEY", public)
    now = datetime.now(timezone.utc)
    approval = Approval(run.action.version, now.isoformat(), (now + timedelta(hours=1)).isoformat(), "")
    approval = Approval(approval.version, approval.approved_at, approval.expires_at,
                        base64.b64encode(key.sign(approval_message(approval))).decode())
    run.record_ceo_approval(approval)
    with pytest.raises(PermissionError):
        run.manual_execution_packet()  # Independent preflight is still required.
    revised = prepare_existing_gate_run(decision, bundle, baseline_artifact=str(baseline(tmp_path)),
                                        exact_human_copy="Edited exact action", destination=action.target_url)
    assert revised.action.version != run.action.version
    bundle.observations[0].verification_expires_at = NOW - timedelta(minutes=1)
    with pytest.raises(PermissionError):
        prepare_existing_gate_run(decision, bundle, baseline_artifact=str(baseline(tmp_path)),
                                  exact_human_copy="Review this question internally", destination=action.target_url)
    with pytest.raises(PermissionError):
        revised.record_ceo_approval(approval)
    with pytest.raises(PermissionError):
        run.record_ceo_approval(Approval(run.action.version, approval.approved_at,
                                        approval.expires_at, base64.b64encode(b"forged").decode()))


def test_fixture_gate_blocked_and_no_rank_stage_network_or_contact(tmp_path, monkeypatch):
    bundle = context(tmp_path)
    import socket
    import urllib.request
    monkeypatch.setattr(socket, "create_connection", lambda *args, **kwargs: pytest.fail("network called"))
    monkeypatch.setattr(urllib.request, "urlopen", lambda *args, **kwargs: pytest.fail("network called"))
    decision = AcquisitionDecisionEngine().decide(bundle)
    assert decision.primary is not None
    with pytest.raises(PermissionError):
        prepare_existing_gate_run(decision, bundle, baseline_artifact=str(baseline(tmp_path)),
                                  exact_human_copy="Copy", destination=decision.primary.candidate.target_url)
    assert decision.execution_mode == "LOCAL_REVIEW_ONLY"


def test_comparison_requires_real_human_provenance(tmp_path):
    engine = AcquisitionDecisionEngine()
    a = engine.decide(context(tmp_path / "a"))
    b = engine.decide(context(tmp_path / "b", social=True))
    c_bundle = context(tmp_path / "c")
    from founderreach.m3.aeo import AEOFinding
    c_bundle.content.aeo.findings.append(AEOFinding(
        code="contradictory_answer", question=c_bundle.observations[0].claim,
        observation_ids=[c_bundle.observations[0].observation_id],
        observed_evidence="Conflicting page statement", recommendation="Resolve before draft",
        confidence=0.75, limitations="Human review",
        affected_url=c_bundle.content.site.approved_origin))
    c = engine.decide(c_bundle)
    choices = {case: decision.primary.candidate.channel if decision.primary else "no_action"
               for case, decision in {"A": a, "B": b, "C": c}.items()}
    synthetic = tmp_path / "synthetic_labels.json"
    synthetic.write_text(json.dumps([{"case_id": "A", "human_label": None,
                                      "label_origin": "pending"}]), encoding="utf-8")
    report = compare_human_labels(choices, synthetic)
    assert report["labeled_count"] == 0 and report["pending_case_ids"] == ["A"]
    synthetic.write_text(json.dumps([{"case_id": "A", "human_label": "owned_social",
                                      "label_origin": "agent"}]), encoding="utf-8")
    with pytest.raises(ValueError):
        compare_human_labels({"A": "owned_website"}, synthetic)
