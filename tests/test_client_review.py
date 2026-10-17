"""The client-review entry point stays fixture-only and evidence-linked."""
from datetime import datetime, timedelta, timezone
import json
import re
import socket
import urllib.request

import pytest

from founderreach.cli import main
from founderreach.client_review import offline_public_url, run_client_review
from founderreach.models import ProductProfile


def profile(website=None, confirmed=True):
    return ProductProfile(identifier="example-business", name="Example Business",
                          description="A service for appointment scheduling",
                          website=website, confirmed=confirmed,
                          target_audiences=["small businesses"],
                          pain_points=["missed appointments"])


def inputs(tmp_path, *, permission_change=None, fixture_change=None):
    now = datetime.now(timezone.utc)
    permission = {
        "business_id": "example-business", "origin": "https://example.com",
        "approved_pages": ["https://example.com/", "https://example.com/robots.txt",
                           "https://example.com/sitemap.xml"],
        "purpose": "offline_fixture_audit", "approved_by": "founder",
        "approved_at": (now - timedelta(minutes=1)).isoformat(),
        "expires_at": (now + timedelta(days=1)).isoformat(),
    }
    if permission_change:
        permission.update(permission_change)
    fixtures = {"pages": {
        "https://example.com/robots.txt": {"status": 200, "content_type": "text/plain",
                                           "body": "User-agent: *\nAllow: /"},
        "https://example.com/sitemap.xml": {"status": 200, "content_type": "application/xml",
                                            "body": "<urlset><url><loc>https://example.com/</loc></url></urlset>"},
        "https://example.com/": {"status": 200, "content_type": "text/html",
                                 "body": "<html><head><title>Example Business</title>"
                                         "<link rel='canonical' href='https://example.com/'></head>"
                                         "<body><h1>Scheduling help</h1><p>Appointments.</p></body></html>"},
    }}
    if fixture_change:
        fixture_change(fixtures)
    permission_path = tmp_path / "permission.json"
    fixtures_path = tmp_path / "fixtures.json"
    permission_path.write_text(json.dumps(permission), encoding="utf-8")
    fixtures_path.write_text(json.dumps(fixtures), encoding="utf-8")
    return permission_path, fixtures_path


def forbid_network(monkeypatch):
    def fail(*args, **kwargs):
        pytest.fail("External network request attempted")
    monkeypatch.setattr(socket, "getaddrinfo", fail)
    monkeypatch.setattr(socket, "create_connection", fail)
    monkeypatch.setattr(urllib.request, "urlopen", fail)


def test_url_mode_uses_offline_html_and_m4_empty_result(tmp_path, monkeypatch):
    forbid_network(monkeypatch)
    permission, fixtures = inputs(tmp_path)
    result = run_client_review(profile("https://example.com/"),
                               permission_path=permission, fixture_path=fixtures)
    assert result.website_page_count == 1
    assert result.decision_status == "no_eligible_action"
    assert "website observation; offline fixture" in result.report
    assert "https://example.com/" in result.report
    assert "Primary recommendation: none" in result.report
    assert "CONFIRM is a self-declaration, not identity verification" in result.report
    assert "conversions, customers and causal impact: UNKNOWN" in result.report
    assert not list(tmp_path.glob("*.sqlite"))
    anchors = set(re.findall(r'<a id="([a-z0-9-]+)"', result.report))
    links = set(re.findall(r'\[Source record\]\(#([a-z0-9-]+)\)', result.report))
    assert links and links <= anchors


def test_typed_details_have_no_fabricated_website_and_no_evidence(tmp_path, monkeypatch, capsys):
    forbid_network(monkeypatch)
    monkeypatch.setattr("builtins.input", lambda prompt: "CONFIRM")
    main(["client-review", "--business-id", "example-business", "--name", "Example Business",
          "--description", "A service for appointment scheduling"])
    output = capsys.readouterr().out
    assert '"website": null' in output
    assert "Website observation: UNKNOWN" in output
    assert "Customer-demand evidence: UNKNOWN" in output
    assert "no_eligible_action" in output
    assert "https://" not in output


def test_cli_url_input_and_local_report(tmp_path, monkeypatch):
    forbid_network(monkeypatch)
    permission, fixtures = inputs(tmp_path)
    monkeypatch.setattr("builtins.input", lambda prompt: "CONFIRM")
    report = tmp_path / "report.md"
    main(["client-review", "--url", "https://example.com/", "--business-id", "example-business",
          "--name", "Example Business", "--description", "Appointment scheduling service",
          "--permission", str(permission), "--fixtures", str(fixtures), "--report", str(report)])
    assert report.exists()
    assert "[Source record](#finding-" in report.read_text(encoding="utf-8")
    with pytest.raises(FileExistsError):
        main(["client-review", "--url", "https://example.com/", "--business-id", "example-business",
              "--name", "Example Business", "--description", "Appointment scheduling service",
              "--permission", str(permission), "--fixtures", str(fixtures), "--report", str(report)])


def test_url_alone_prompts_for_business_details_before_confirmation(tmp_path, monkeypatch):
    forbid_network(monkeypatch)
    permission, fixtures = inputs(tmp_path)
    answers = iter(["example-business", "Example Business", "Scheduling service", "CONFIRM"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))
    report = tmp_path / "url-only.md"
    main(["client-review", "--url", "https://example.com/",
          "--permission", str(permission), "--fixtures", str(fixtures), "--report", str(report)])
    assert "no_eligible_action" in report.read_text(encoding="utf-8")


def test_profile_confirmation_rejection(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "NO")
    with pytest.raises(PermissionError, match="confirmation"):
        main(["client-review", "--business-id", "example-business", "--name", "Example Business",
              "--description", "Scheduling service"])
    with pytest.raises(PermissionError, match="confirmation"):
        run_client_review(profile(confirmed=False))


def test_website_permission_is_required_and_exact(tmp_path):
    permission, fixtures = inputs(tmp_path)
    with pytest.raises(PermissionError, match="permission"):
        run_client_review(profile("https://example.com/"), fixture_path=fixtures)
    wrong, _ = inputs(tmp_path, permission_change={"business_id": "other-business"})
    with pytest.raises(PermissionError, match="does not match"):
        run_client_review(profile("https://example.com/"), permission_path=wrong, fixture_path=fixtures)
    expired, _ = inputs(tmp_path, permission_change={
        "expires_at": (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()})
    with pytest.raises(ValueError, match="not current"):
        run_client_review(profile("https://example.com/"), permission_path=expired, fixture_path=fixtures)


def test_cross_origin_page_and_fixture_are_rejected(tmp_path):
    permission, fixtures = inputs(tmp_path, permission_change={
        "approved_pages": ["https://other.example.com/"]})
    with pytest.raises(ValueError, match="exact origin"):
        run_client_review(profile("https://example.com/"), permission_path=permission, fixture_path=fixtures)
    permission, fixtures = inputs(tmp_path, fixture_change=lambda f: f["pages"].update({
        "https://other.example.com/": {"status": 200, "content_type": "text/html", "body": "<h1>Other</h1>"}}))
    with pytest.raises(ValueError, match="outside the exact permission scope"):
        run_client_review(profile("https://example.com/"), permission_path=permission, fixture_path=fixtures)


@pytest.mark.parametrize("metadata_url", ["https://example.com/robots.txt",
                                           "https://example.com/sitemap.xml"])
def test_metadata_fixture_requires_explicit_page_permission(tmp_path, metadata_url):
    approved = ["https://example.com/", "https://example.com/robots.txt",
                "https://example.com/sitemap.xml"]
    approved.remove(metadata_url)
    permission, fixtures = inputs(tmp_path, permission_change={"approved_pages": approved})
    with pytest.raises(ValueError, match="outside the exact permission scope"):
        run_client_review(profile("https://example.com/"),
                          permission_path=permission, fixture_path=fixtures)


@pytest.mark.parametrize("metadata_url", ["https://example.com/robots.txt",
                                           "https://example.com/sitemap.xml"])
def test_omitted_metadata_fixture_is_unknown_not_observed(tmp_path, metadata_url):
    permission, fixtures = inputs(tmp_path, fixture_change=lambda f: f["pages"].pop(metadata_url))
    result = run_client_review(profile("https://example.com/"),
                               permission_path=permission, fixture_path=fixtures)
    assert f"Fixture data for {metadata_url}: UNKNOWN; no response was supplied" in result.report
    assert "HTTP 404" not in result.report
    assert "`missing_sitemap`" not in result.report
    assert result.website_page_count == 1


def test_explicit_sitemap_404_is_recorded_fixture_response(tmp_path):
    def set_404(fixtures):
        fixtures["pages"]["https://example.com/sitemap.xml"] = {
            "status": 404, "content_type": "text/plain", "body": ""}
    permission, fixtures = inputs(tmp_path, fixture_change=set_404)
    result = run_client_review(profile("https://example.com/"),
                               permission_path=permission, fixture_path=fixtures)
    assert "`missing_sitemap`" in result.report
    assert "HTTP 404" in result.report
    assert "Fixture data for https://example.com/sitemap.xml: UNKNOWN" not in result.report


def test_profile_url_must_be_in_approved_inventory(tmp_path):
    permission, fixtures = inputs(tmp_path)
    with pytest.raises(PermissionError, match="does not match"):
        run_client_review(profile("https://example.com/other"),
                          permission_path=permission, fixture_path=fixtures)


@pytest.mark.parametrize("url", ["https://127.0.0.1/", "https://localhost/",
                                      "https://service.internal/", "https://user:pass@example.com/",
                                      "https://example.com/?secret=1", "http://example.com/"])
def test_offline_ssrf_shape_guard_never_resolves_dns(url, monkeypatch):
    forbid_network(monkeypatch)
    with pytest.raises(ValueError):
        offline_public_url(url)


def test_attestation_is_minimized_and_never_independent_verification(tmp_path, monkeypatch):
    forbid_network(monkeypatch)
    attestation = tmp_path / "attestations.json"
    attestation.write_text(json.dumps([{"native_id": "q1",
        "excerpt": "We lose appointments when reminders are manual.",
        "claim": "A founder reports missed appointments.",
        "minimized_by_founder": True}]), encoding="utf-8")
    result = run_client_review(profile(), attestations_path=attestation)
    assert result.observation_count == 1
    assert result.decision_status == "no_eligible_action"
    assert "**founder-attested**" in result.report
    assert "[Source record](#" in result.report
    assert "independently verified: no" in result.report
    assert "Independent customer demand: UNKNOWN" in result.report
    assert "cannot guarantee removal of personal data" in result.report
    attestation.write_text(json.dumps([{"native_id": "q2", "excerpt": "Email me at person@example.com",
                                       "claim": "A founder reports missed appointments.",
                                       "minimized_by_founder": True}]), encoding="utf-8")
    with pytest.raises(ValueError, match="personal identifier"):
        run_client_review(profile(), attestations_path=attestation)
    attestation.write_text(json.dumps([{"native_id": "q3", "excerpt": "A family missed appointments",
                                       "claim": "A founder reports missed appointments.",
                                       "minimized_by_founder": False}]), encoding="utf-8")
    with pytest.raises(ValueError, match="Founder must confirm"):
        run_client_review(profile(), attestations_path=attestation)


def test_website_free_profile_rejects_site_inputs(tmp_path):
    permission, fixtures = inputs(tmp_path)
    with pytest.raises(ValueError, match="Website-free"):
        run_client_review(profile(), permission_path=permission, fixture_path=fixtures)


def test_untrusted_attestation_markdown_is_inert(tmp_path):
    attestation = tmp_path / "attestations.json"
    attestation.write_text(json.dumps([{
        "native_id": "safe-id", "excerpt": "Scheduling is hard",
        "claim": "See ![tracker](https://outside.example/pixel) <script>alert(1)</script>",
        "minimized_by_founder": True,
    }]), encoding="utf-8")
    report = run_client_review(profile(), attestations_path=attestation).report
    assert "![tracker]" not in report
    assert "<script>" not in report
    assert "founder-attested" in report
