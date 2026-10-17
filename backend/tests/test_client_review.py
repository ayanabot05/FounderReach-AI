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


def test_section_1_site_improvements_never_reads_as_acquisition_recommendation(tmp_path, monkeypatch):
    forbid_network(monkeypatch)
    permission, fixtures = inputs(tmp_path)
    attestation = tmp_path / "attestations.json"
    attestation.write_text(json.dumps([{
        "native_id": "att-1",
        "excerpt": "Manual reminders cause missed bookings.",
        "claim": "Founders report manual reminder overhead.",
        "minimized_by_founder": True,
    }]), encoding="utf-8")
    result = run_client_review(
        profile("https://example.com/"),
        permission_path=permission,
        fixture_path=fixtures,
        attestations_path=attestation,
    )
    headings = re.findall(r"^## .+$", result.report, flags=re.MULTILINE)
    assert headings == ["## Section 1: Site improvements", "## Section 2: Acquisition action"]

    _, after_s1 = result.report.split("## Section 1: Site improvements\n", 1)
    section_1, section_2 = after_s1.split("\n## Section 2: Acquisition action\n", 1)

    bullets_s1 = [line for line in section_1.splitlines() if line.startswith("- ")]
    assert bullets_s1
    assert all("website observation; offline fixture" in line for line in bullets_s1)

    lower_s1 = section_1.lower()
    for forbidden in ("traffic", "ranking", "customer", "customers", "conversion", "conversions",
                      "acquisition", "outreach", "channel", "recommend", "recommendation",
                      "founder-attested", "manual reminder overhead"):
        assert forbidden not in lower_s1

    assert "Status: `no_eligible_action`. The existing M4 rules were used unchanged." in section_2
    assert "Primary recommendation: none yet." in section_2
    assert "Evidence still missing:" in section_2


def test_founder_attested_text_never_appears_as_verified_demand(tmp_path, monkeypatch):
    forbid_network(monkeypatch)
    permission, fixtures = inputs(tmp_path)
    claim_text = "Teams report losing bookings when follow-ups are manual."
    attestation = tmp_path / "attestations.json"
    attestation.write_text(json.dumps([{
        "native_id": "att-demand-check",
        "excerpt": "We lose bookings when follow-ups are manual.",
        "claim": claim_text,
        "minimized_by_founder": True,
    }]), encoding="utf-8")
    result = run_client_review(
        profile("https://example.com/"),
        permission_path=permission,
        fixture_path=fixtures,
        attestations_path=attestation,
    )
    _, after_s1 = result.report.split("## Section 1: Site improvements\n", 1)
    section_1, section_2 = after_s1.split("\n## Section 2: Acquisition action\n", 1)

    assert claim_text not in section_1
    claim_lines = [line for line in section_2.splitlines() if claim_text in line]
    assert len(claim_lines) == 2
    for line in claim_lines:
        assert "**founder-attested" in line
        assert ("independently verified: no; verified demand: no." in line
                or "This is not independently verified demand." in line)
    assert "- Customer-demand evidence: UNKNOWN; no independently verified demand observations were supplied." in section_2
    assert "- Independent customer demand: UNKNOWN; founder attestations are not source verification." in section_2
    assert result.decision_status == "no_eligible_action"


def live_permission(tmp_path, *, change=None, filename="live_permission.json"):
    now = datetime.now(timezone.utc)
    payload = {
        "business_id": "example-business",
        "origin": "https://example.com",
        "approved_pages": [
            "https://example.com/",
            "https://example.com/robots.txt",
            "https://example.com/sitemap.xml",
        ],
        "purpose": "live_site_audit",
        "approved_by": "founder",
        "approved_at": (now - timedelta(minutes=5)).isoformat(),
        "expires_at": (now + timedelta(hours=2)).isoformat(),
    }
    if change:
        payload.update(change)
    path = tmp_path / filename
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def install_mock_live_network(monkeypatch, *, responses, dns_ips=None):
    """Mock DNS + TLS connection while exercising WebsiteFetcher._target and IP pinning."""
    import http.client

    dns_map = dns_ips or {"example.com": ["93.184.216.34"]}
    state = {"dns_calls": [], "connect_calls": [], "http_requests": []}

    def fake_getaddrinfo(host, port, type=0):
        state["dns_calls"].append((host, port))
        ips = dns_map(host) if callable(dns_map) else dns_map.get(host, ["93.184.216.34"])
        if not ips:
            raise OSError("DNS lookup failed")
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port)) for ip in ips]

    def fake_create_connection(address, timeout=None, source_address=None):
        state["connect_calls"].append((address, timeout, source_address))
        return object()

    class FakeResponse:
        def __init__(self, status, headers, body):
            self.status = status
            self._headers = list(headers.items())
            self._body = body.encode("utf-8") if isinstance(body, str) else bytes(body)

        def getheaders(self):
            return self._headers

        def read(self, amt=None):
            return self._body if amt is None else self._body[:amt]

    class FakeHTTPSConnection:
        def __init__(self, host, port=None, timeout=None):
            self.host = host
            self.port = port or 443
            self.timeout = timeout
            self._create_connection = None
            self._response = None

        def request(self, method, path, headers=None):
            if self._create_connection is not None:
                self._create_connection((self.host, self.port), timeout=self.timeout)
            hdrs = dict(headers or {})
            state["http_requests"].append((method, self.host, self.port, path, hdrs))
            url = f"https://{self.host}{path}"
            spec = responses(url) if callable(responses) else responses.get(url)
            if spec is None:
                self._response = FakeResponse(404, {"Content-Type": "text/plain"}, "")
            elif isinstance(spec, Exception):
                raise spec
            else:
                status, headers_dict, body = spec
                self._response = FakeResponse(status, headers_dict, body)

        def getresponse(self):
            return self._response

        def close(self):
            pass

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(socket, "create_connection", fake_create_connection)
    monkeypatch.setattr(http.client, "HTTPSConnection", FakeHTTPSConnection)
    return state


def test_sr1_live_fetch_requires_explicit_flag_live_purpose_and_confirm(tmp_path, monkeypatch, capsys):
    forbid_network(monkeypatch)
    offline_perm, fixtures = inputs(tmp_path)
    live_perm = live_permission(tmp_path)

    # Cannot use live_site=True with offline_fixture_audit permission or with fixtures
    with pytest.raises(PermissionError, match="purpose"):
        run_client_review(profile("https://example.com/"), permission_path=offline_perm, live_site=True)
    with pytest.raises(PermissionError, match="forbids local fixture"):
        run_client_review(profile("https://example.com/"), permission_path=live_perm,
                          fixture_path=fixtures, live_site=True)
    # Cannot use live_site_audit permission without live_site=True
    with pytest.raises(PermissionError, match="purpose"):
        run_client_review(profile("https://example.com/"), permission_path=live_perm,
                          fixture_path=fixtures, live_site=False)
    # TTL > 24h rejected for live_site_audit
    long_ttl = live_permission(
        tmp_path,
        change={"expires_at": (datetime.now(timezone.utc) + timedelta(hours=25)).isoformat()},
        filename="long_ttl.json",
    )
    with pytest.raises(ValueError, match="24 hours"):
        run_client_review(profile("https://example.com/"), permission_path=long_ttl, live_site=True)

    # CLI help explicitly states authorization is self-declared and does not prove site ownership
    with pytest.raises(SystemExit):
        main(["client-review", "--help"])
    help_out = " ".join(capsys.readouterr().out.split())
    assert "authorization is self-declared and does not prove site ownership" in help_out
    assert "--live-site" in help_out

    # Interactive CONFIRM rejection blocks execution before any network call
    monkeypatch.setattr("builtins.input", lambda prompt: "NO")
    with pytest.raises(PermissionError, match="confirmation"):
        main(["client-review", "--url", "https://example.com/", "--business-id", "example-business",
              "--name", "Example Business", "--description", "Scheduling service",
              "--permission", str(live_perm), "--live-site"])


def test_sr2_live_fetch_enforces_exact_origin_and_approved_inventory(tmp_path, monkeypatch):
    # Omit sitemap.xml from approved_pages: must not be fetched over the network
    perm_no_sitemap = live_permission(
        tmp_path,
        change={"approved_pages": ["https://example.com/", "https://example.com/robots.txt"]},
        filename="no_sitemap_perm.json",
    )
    net = install_mock_live_network(monkeypatch, responses={
        "https://example.com/robots.txt": (200, {"Content-Type": "text/plain"}, "User-agent: *\nAllow: /\n"),
        "https://example.com/": (
            200,
            {"Content-Type": "text/html"},
            "<html><head><title>Example</title><meta name='description' content='Desc'>"
            "<link rel='canonical' href='https://example.com/'></head><body><h1>Heading</h1></body></html>",
        ),
    })
    result = run_client_review(profile("https://example.com/"), permission_path=perm_no_sitemap, live_site=True)
    requested_paths = [req[3] for req in net["http_requests"]]
    assert requested_paths == ["/robots.txt", "/"]
    assert "/sitemap.xml" not in requested_paths
    assert "Fixture data for https://example.com/sitemap.xml: UNKNOWN; no response was supplied." in result.report

    # Redirect to unapproved path or cross-origin is blocked
    install_mock_live_network(monkeypatch, responses={
        "https://example.com/robots.txt": (200, {"Content-Type": "text/plain"}, "User-agent: *\nAllow: /\n"),
        "https://example.com/": (302, {"Location": "https://example.com/unapproved"}, ""),
    })
    redirect_res = run_client_review(profile("https://example.com/"), permission_path=perm_no_sitemap, live_site=True)
    assert redirect_res.website_page_count == 0
    assert "`inaccessible_page`" in redirect_res.report


def test_sr3_live_fetch_prevents_ssrf_and_pins_verified_ip(tmp_path, monkeypatch):
    live_perm = live_permission(tmp_path)
    base_responses = {
        "https://example.com/robots.txt": (200, {"Content-Type": "text/plain"}, "User-agent: *\nAllow: /\n"),
        "https://example.com/sitemap.xml": (
            200,
            {"Content-Type": "application/xml"},
            "<urlset><url><loc>https://example.com/</loc></url></urlset>",
        ),
        "https://example.com/": (
            200,
            {"Content-Type": "text/html"},
            "<html><head><title>Example</title><link rel='canonical' href='https://example.com/'></head>"
            "<body><h1>Example</h1></body></html>",
        ),
    }

    # Private / loopback / link-local DNS resolutions fail closed with zero socket connections
    for bad_ip in ("127.0.0.1", "10.0.0.1", "192.168.1.5", "169.254.169.254", "::1"):
        net_bad = install_mock_live_network(monkeypatch, responses=base_responses,
                                            dns_ips={"example.com": [bad_ip]})
        res_bad = run_client_review(profile("https://example.com/"), permission_path=live_perm, live_site=True)
        assert net_bad["connect_calls"] == []
        assert res_bad.website_page_count == 0

    # Valid global IP pins socket.create_connection to ("93.184.216.34", 443)
    net_ok = install_mock_live_network(monkeypatch, responses=base_responses,
                                       dns_ips={"example.com": ["93.184.216.34"]})
    res_ok = run_client_review(profile("https://example.com/"), permission_path=live_perm, live_site=True)
    assert res_ok.website_page_count == 1
    assert net_ok["connect_calls"]
    assert all(call[0] == ("93.184.216.34", 443) and call[1] == 5 for call in net_ok["connect_calls"])


def test_sr4_live_fetch_enforces_redirect_request_time_size_and_encoding_limits(tmp_path, monkeypatch):
    perm = live_permission(
        tmp_path,
        change={"approved_pages": [
            "https://example.com/",
            "https://example.com/step1",
            "https://example.com/step2",
            "https://example.com/step3",
            "https://example.com/robots.txt",
        ]},
    )

    # 1. Excessive redirects (> 2 hops) fail closed
    install_mock_live_network(monkeypatch, responses={
        "https://example.com/robots.txt": (200, {"Content-Type": "text/plain"}, "User-agent: *\nAllow: /\n"),
        "https://example.com/": (302, {"Location": "https://example.com/step1"}, ""),
        "https://example.com/step1": (302, {"Location": "https://example.com/step2"}, ""),
        "https://example.com/step2": (302, {"Location": "https://example.com/step3"}, ""),
        "https://example.com/step3": (200, {"Content-Type": "text/html"}, "<html><body><h1>Too far</h1></body></html>"),
    })
    res_redir = run_client_review(profile("https://example.com/"), permission_path=perm, live_site=True)
    assert "`inaccessible_page`" in res_redir.report

    # 2. Oversized body (> 512 KB) and compressed Content-Encoding fail closed
    perm_single = live_permission(
        tmp_path,
        change={"approved_pages": ["https://example.com/", "https://example.com/robots.txt"]},
        filename="single_perm.json",
    )
    install_mock_live_network(monkeypatch, responses={
        "https://example.com/robots.txt": (200, {"Content-Type": "text/plain"}, "User-agent: *\nAllow: /\n"),
        "https://example.com/": (200, {"Content-Type": "text/html"}, "x" * 512_001),
    })
    res_huge = run_client_review(profile("https://example.com/"), permission_path=perm_single, live_site=True)
    assert res_huge.website_page_count == 0
    assert "`inaccessible_page`" in res_huge.report

    install_mock_live_network(monkeypatch, responses={
        "https://example.com/robots.txt": (200, {"Content-Type": "text/plain"}, "User-agent: *\nAllow: /\n"),
        "https://example.com/": (200, {"Content-Type": "text/html", "Content-Encoding": "gzip"}, "<html></html>"),
    })
    res_gzip = run_client_review(profile("https://example.com/"), permission_path=perm_single, live_site=True)
    assert res_gzip.website_page_count == 0
    assert "`inaccessible_page`" in res_gzip.report


def test_sr5_live_fetch_enforces_robots_txt_before_any_page_fetch(tmp_path, monkeypatch):
    # Permission without /robots.txt is rejected before network
    with pytest.raises(ValueError, match="robots.txt"):
        live_permission(
            tmp_path,
            change={"approved_pages": ["https://example.com/"]},
            filename="missing_robots.json",
        )
        run_client_review(profile("https://example.com/"),
                          permission_path=tmp_path / "missing_robots.json", live_site=True)

    # Disallowed page in robots.txt is skipped without making an HTTP GET to the page
    perm = live_permission(
        tmp_path,
        change={"approved_pages": ["https://example.com/", "https://example.com/robots.txt"]},
        filename="robots_disallow.json",
    )
    net_disallow = install_mock_live_network(monkeypatch, responses={
        "https://example.com/robots.txt": (
            200,
            {"Content-Type": "text/plain"},
            "User-agent: FounderReach\nDisallow: /\n",
        ),
        "https://example.com/": (200, {"Content-Type": "text/html"}, "<html><body><h1>Blocked</h1></body></html>"),
    })
    res_disallow = run_client_review(profile("https://example.com/"), permission_path=perm, live_site=True)
    assert [req[3] for req in net_disallow["http_requests"]] == ["/robots.txt"]
    assert res_disallow.website_page_count == 0
    assert "`robots_blocked`" in res_disallow.report

    # Unavailable robots.txt (HTTP 500) blocks page fetching
    net_500 = install_mock_live_network(monkeypatch, responses={
        "https://example.com/robots.txt": (500, {"Content-Type": "text/plain"}, "error"),
        "https://example.com/": (200, {"Content-Type": "text/html"}, "<html><body><h1>Page</h1></body></html>"),
    })
    res_500 = run_client_review(profile("https://example.com/"), permission_path=perm, live_site=True)
    assert [req[3] for req in net_500["http_requests"]] == ["/robots.txt"]
    assert res_500.website_page_count == 0
    assert "`inaccessible_page`" in res_500.report


def test_sr6_live_fetch_makes_zero_external_writes_and_zero_spend(tmp_path, monkeypatch):
    live_perm = live_permission(tmp_path)
    net = install_mock_live_network(monkeypatch, responses={
        "https://example.com/robots.txt": (200, {"Content-Type": "text/plain"}, "User-agent: *\nAllow: /\n"),
        "https://example.com/sitemap.xml": (
            200,
            {"Content-Type": "application/xml"},
            "<urlset><url><loc>https://example.com/</loc></url></urlset>",
        ),
        "https://example.com/": (
            200,
            {"Content-Type": "text/html"},
            "<html><head><title>Example Live</title><meta name='description' content='Live desc'>"
            "<link rel='canonical' href='https://example.com/'></head><body><h1>Live Heading</h1></body></html>",
        ),
    })
    monkeypatch.setattr("builtins.input", lambda prompt: "CONFIRM")
    report_path = tmp_path / "live_report.md"
    main([
        "client-review", "--url", "https://example.com/", "--business-id", "example-business",
        "--name", "Example Business", "--description", "Appointment scheduling service",
        "--permission", str(live_perm), "--live-site", "--report", str(report_path),
    ])
    # GET only, no cookies or authorization headers sent
    assert net["http_requests"]
    for method, _host, _port, _path, hdrs in net["http_requests"]:
        assert method == "GET"
        assert "cookie" not in {k.lower() for k in hdrs}
        assert "authorization" not in {k.lower() for k in hdrs}
        assert hdrs.get("Accept-Encoding") == "identity"

    # Zero durable sqlite/db files created; exclusive report file creation
    assert not list(tmp_path.glob("*.sqlite*"))
    assert not list(tmp_path.glob("*.db"))
    report_text = report_path.read_text(encoding="utf-8")
    assert "authorization is self-declared and does not prove site ownership" in report_text
    assert "**website observation; live fetch**" in report_text
    assert "Status: `no_eligible_action`" in report_text
    assert "Primary recommendation: none yet." in report_text

    with pytest.raises(FileExistsError):
        main([
            "client-review", "--url", "https://example.com/", "--business-id", "example-business",
            "--name", "Example Business", "--description", "Appointment scheduling service",
            "--permission", str(live_perm), "--live-site", "--report", str(report_path),
        ])


def test_report_includes_checks_performed_robots_sitemap_and_observed_page_fields(tmp_path, monkeypatch):
    forbid_network(monkeypatch)
    jsonld = json.dumps({
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "Organization", "name": "Example Business"},
            {"@type": ["SoftwareApplication", "WebApplication"], "name": "Example Business"},
        ],
    })
    html_body = (
        "<html><head><title>Example Business — Appointment Scheduling</title>"
        "<meta name='description' content='Example Business is appointment scheduling software for small businesses.'>"
        "<link rel='canonical' href='https://example.com/'>"
        f"<script type='application/ld+json'>{jsonld}</script></head>"
        "<body><h1>Example Business appointment scheduling</h1>"
        "<p>Example Business provides appointment scheduling software for small businesses to prevent missed appointments.</p>"
        "</body></html>"
    )
    permission, fixtures = inputs(
        tmp_path,
        fixture_change=lambda f: f["pages"]["https://example.com/"].update({"body": html_body}),
    )
    result = run_client_review(
        profile("https://example.com/"),
        permission_path=permission,
        fixture_path=fixtures,
    )
    _, after_s1 = result.report.split("## Section 1: Site improvements\n", 1)
    section_1, _ = after_s1.split("\n## Section 2: Acquisition action\n", 1)

    # robots.txt and sitemap.xml status
    assert "robots.txt status (https://example.com/robots.txt): observed (HTTP 200 text/plain; crawl rules parsed; approved URLs allowed)." in section_1
    assert "Sitemap status (https://example.com/sitemap.xml): observed XML sitemap (1 URL(s) listed; all audited pages listed)." in section_1

    # Observed canonical, meta description, H1 and JSON-LD types
    assert "fixture title: Example Business — Appointment Scheduling;" in section_1
    assert "canonical: https://example.com/;" in section_1
    assert "meta description: Example Business is appointment scheduling software for small businesses.;" in section_1
    assert "H1 (1): Example Business appointment scheduling;" in section_1
    assert "JSON-LD types: Organization, SoftwareApplication, WebApplication." in section_1

    # Checks performed list with pass/finding states
    assert "Checks performed:" in section_1
    for check_line in (
        "Check — robots.txt directives: `pass`.",
        "Check — XML sitemap availability and coverage: `pass`.",
        "Check — Page accessibility (HTTP status and HTML content-type): `pass`.",
        "Check — Page indexability (noindex meta and X-Robots-Tag): `pass`.",
        "Check — Canonical link tag: `pass`.",
        "Check — Title and meta description: `pass`.",
        "Check — Primary H1 heading structure: `pass`.",
        "Check — JSON-LD structured data: `pass`.",
        "Check — AEO direct-answer and claim consistency: `pass`.",
        "Check — GEO entity and schema readiness: `finding`.",
    ):
        assert check_line in section_1


def test_aeo_and_geo_findings_shown_in_section_1_as_website_observations_without_acquisition_claims(tmp_path, monkeypatch):
    forbid_network(monkeypatch)
    html_body = (
        "<html><head><title>Unrelated Portal</title>"
        "<link rel='canonical' href='https://example.com/'></head>"
        "<body><h1>Welcome</h1>"
        "<h2>How does reminder setup work across calendar devices?</h2>"
        "<p>Reminder setup works across calendar devices automatically in two minutes with our 100% guaranteed platform.</p>"
        "</body></html>"
    )
    permission, fixtures = inputs(
        tmp_path,
        fixture_change=lambda f: f["pages"]["https://example.com/"].update({"body": html_body}),
    )
    attestation = tmp_path / "attestations.json"
    attestation.write_text(json.dumps([
        {
            "native_id": "q-sync",
            "excerpt": "How do we prevent double-booked slots across clinic rooms?",
            "claim": "Teams ask how to prevent double-booked slots across clinic rooms?",
            "minimized_by_founder": True,
        },
        {
            "native_id": "q-remind",
            "excerpt": "How does reminder setup work across calendar devices?",
            "claim": "How does reminder setup work across calendar devices?",
            "minimized_by_founder": True,
        },
    ]), encoding="utf-8")

    result = run_client_review(
        profile("https://example.com/"),
        permission_path=permission,
        fixture_path=fixtures,
        attestations_path=attestation,
    )
    _, after_s1 = result.report.split("## Section 1: Site improvements\n", 1)
    section_1, section_2 = after_s1.split("\n## Section 2: Acquisition action\n", 1)

    # Checks performed reflects finding vs pass accurately
    assert "Check — Title and meta description: `finding`." in section_1
    assert "Check — JSON-LD structured data: `finding`." in section_1
    assert "Check — AEO direct-answer and claim consistency: `finding`." in section_1
    assert "Check — GEO entity and schema readiness: `finding`." in section_1
    assert "Check — Canonical link tag: `pass`." in section_1

    # AEO findings and GEO readiness findings are rendered in Section 1
    assert "AEO (`faq_schema_suitability`):" in section_1
    assert "AEO (`unsupported_answer_claim`):" in section_1
    assert "AEO (`missing_page`):" in section_1
    assert "GEO (`brand_name_mismatch`):" in section_1
    assert "GEO (`missing_organization_schema`):" in section_1
    assert "GEO (`missing_website_schema`):" in section_1
    assert "GEO (`uncited_factual_claim`):" in section_1

    # Every bullet in Section 1 is labeled website observation
    bullets_s1 = [line for line in section_1.splitlines() if line.startswith("- ")]
    assert bullets_s1
    assert all("website observation; offline fixture" in line for line in bullets_s1)

    # Section 1 never reads as an acquisition recommendation and never makes traffic/ranking/conversion/customer claims
    lower_s1 = section_1.lower()
    for forbidden in ("traffic", "ranking", "customer", "customers", "conversion", "conversions",
                      "acquisition", "outreach", "channel", "recommend", "recommendation",
                      "founder-attested", "double-booked slots across clinic rooms"):
        assert forbidden not in lower_s1

    # All source-record links resolve to anchors in the report
    anchors = set(re.findall(r'<a id="([a-z0-9-]+)"', result.report))
    links = set(re.findall(r'\[Source record\]\(#([a-z0-9-]+)\)', result.report))
    assert links and links <= anchors
    assert result.decision_status == "no_eligible_action"
    assert "Primary recommendation: none yet." in section_2


def test_section_2_includes_what_to_bring_next_and_preserves_none_yet_outcome(tmp_path, monkeypatch):
    forbid_network(monkeypatch)
    result = run_client_review(profile())
    _, after_s1 = result.report.split("## Section 1: Site improvements\n", 1)
    _, section_2 = after_s1.split("\n## Section 2: Acquisition action\n", 1)

    assert "Status: `no_eligible_action`. The existing M4 rules were used unchanged." in section_2
    assert "Primary recommendation: none yet. Eligible demand evidence is insufficient for an acquisition action." in section_2
    assert "What to bring next:" in section_2
    assert (
        "Paste 3 to 5 real customer questions or complaints with no names or contact details, "
        "labeled **founder-attested**"
    ) in section_2


def test_client_review_code_path_has_no_git_github_vercel_railway_or_supabase_imports_or_calls(tmp_path, monkeypatch):
    import ast
    import os
    from pathlib import Path
    import subprocess
    import sys

    forbid_network(monkeypatch)
    repo_root = Path(__file__).resolve().parents[1]
    client_review_modules = [
        "founderreach/client_review.py",
        "founderreach/cli.py",
        "founderreach/evidence.py",
        "founderreach/identity.py",
        "founderreach/models.py",
        "founderreach/privacy.py",
        "founderreach/research_store.py",
        "founderreach/website.py",
        "founderreach/m3/pipeline.py",
        "founderreach/m3/site.py",
        "founderreach/m3/aeo.py",
        "founderreach/m3/geo.py",
        "founderreach/m3/content.py",
        "founderreach/m4/candidates.py",
        "founderreach/m4/contracts.py",
        "founderreach/m4/decision.py",
        "founderreach/m4/gate_bridge.py",
    ]
    forbidden_imports = {
        "git", "gitpython", "github", "pygithub", "vercel", "railway",
        "supabase", "postgrest", "gotrue", "psycopg", "psycopg2", "asyncpg",
        "dotenv", "python_dotenv", "subprocess", "ftplib", "paramiko", " fabric",
    }
    forbidden_call_names = {
        "git", "gh", "vercel", "railway", "supabase", "system", "popen",
        "Popen", "check_call", "check_output",
    }

    for rel_path in client_review_modules:
        source = (repo_root / rel_path).read_text(encoding="utf-8")
        tree = ast.parse(source, filename=rel_path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".")[0].lower()
                    assert top not in forbidden_imports, f"Forbidden import {alias.name} in {rel_path}"
            elif isinstance(node, ast.ImportFrom) and node.module:
                top = node.module.split(".")[0].lower()
                assert top not in forbidden_imports, f"Forbidden import from {node.module} in {rel_path}"
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    assert node.func.id not in forbidden_call_names, f"Forbidden call {node.func.id} in {rel_path}"
                elif isinstance(node.func, ast.Attribute):
                    assert node.func.attr not in forbidden_call_names, f"Forbidden call .{node.func.attr} in {rel_path}"

    def fail_proc(*args, **kwargs):
        pytest.fail("External process or shell command execution attempted")

    monkeypatch.setattr(subprocess, "run", fail_proc)
    monkeypatch.setattr(subprocess, "Popen", fail_proc)
    monkeypatch.setattr(subprocess, "call", fail_proc)
    monkeypatch.setattr(subprocess, "check_call", fail_proc)
    monkeypatch.setattr(subprocess, "check_output", fail_proc)
    monkeypatch.setattr(os, "system", fail_proc)
    if hasattr(os, "popen"):
        monkeypatch.setattr(os, "popen", fail_proc)

    permission, fixtures = inputs(tmp_path)
    monkeypatch.setattr("builtins.input", lambda prompt: "CONFIRM")
    report_path = tmp_path / "boundary_check.md"
    main([
        "client-review", "--url", "https://example.com/", "--business-id", "example-business",
        "--name", "Example Business", "--description", "Appointment scheduling service",
        "--permission", str(permission), "--fixtures", str(fixtures), "--report", str(report_path),
    ])
    for mod_name in list(sys.modules):
        top = mod_name.split(".")[0].lower()
        assert top not in {"git", "github", "vercel", "railway", "supabase"}


def test_client_review_never_reads_credentials_or_dotenv_and_rejects_dotenv_inputs(tmp_path, monkeypatch):
    import builtins
    import os
    from pathlib import Path

    forbid_network(monkeypatch)
    canary_secret = "CANARY_SECRET_VALUE_998877"
    dotenv_file = tmp_path / ".env"
    dotenv_json = tmp_path / ".env.json"

    for env_key in ("SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_KEY", "GITHUB_TOKEN",
                    "VERCEL_TOKEN", "RAILWAY_TOKEN", "GEMINI_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.setenv(env_key, canary_secret)

    permission, fixtures = inputs(tmp_path)

    # Reject .env or .env.json if supplied as any client-review file input (without opening the file)
    with pytest.raises(ValueError, match="JSON input file"):
        run_client_review(profile("https://example.com/"), permission_path=dotenv_file, fixture_path=fixtures)
    with pytest.raises(ValueError, match="JSON input file"):
        run_client_review(profile("https://example.com/"), permission_path=dotenv_json, fixture_path=fixtures)
    with pytest.raises(ValueError, match="JSON input file"):
        run_client_review(profile("https://example.com/"), permission_path=permission, fixture_path=dotenv_json)
    with pytest.raises(ValueError, match="JSON input file"):
        run_client_review(profile(), attestations_path=dotenv_json)

    real_open = builtins.open
    real_path_open = Path.open
    real_read_text = Path.read_text
    real_read_bytes = Path.read_bytes
    real_getenv = os.getenv

    def guard_path(p):
        name = Path(p).name.lower()
        if ".env" in name or name in {"id_rsa", "credentials", "credentials.json"} or name.endswith((".pem", ".key")):
            pytest.fail(f"Credential or .env file access attempted: {p}")

    def checked_open(file, *args, **kwargs):
        if isinstance(file, (str, Path)):
            guard_path(file)
        return real_open(file, *args, **kwargs)

    def checked_path_open(self, *args, **kwargs):
        guard_path(self)
        return real_path_open(self, *args, **kwargs)

    def checked_read_text(self, *args, **kwargs):
        guard_path(self)
        return real_read_text(self, *args, **kwargs)

    def checked_read_bytes(self, *args, **kwargs):
        guard_path(self)
        return real_read_bytes(self, *args, **kwargs)

    def checked_getenv(key, default=None):
        if any(tok in key.upper() for tok in ("SUPABASE", "GITHUB", "VERCEL", "RAILWAY", "SECRET", "TOKEN", "API_KEY", "PASSWORD")):
            pytest.fail(f"Credential environment variable read attempted: {key}")
        return real_getenv(key, default)

    monkeypatch.setattr(builtins, "open", checked_open)
    monkeypatch.setattr(Path, "open", checked_path_open)
    monkeypatch.setattr(Path, "read_text", checked_read_text)
    monkeypatch.setattr(Path, "read_bytes", checked_read_bytes)
    monkeypatch.setattr(os, "getenv", checked_getenv)

    result = run_client_review(profile("https://example.com/"), permission_path=permission, fixture_path=fixtures)
    assert canary_secret not in result.report


def test_client_review_performs_only_get_to_approved_pages_and_writes_only_new_report_file(tmp_path, monkeypatch):
    import builtins
    from pathlib import Path
    import sqlite3

    live_perm = live_permission(tmp_path)
    net = install_mock_live_network(monkeypatch, responses={
        "https://example.com/robots.txt": (200, {"Content-Type": "text/plain"}, "User-agent: *\nAllow: /\n"),
        "https://example.com/sitemap.xml": (
            200,
            {"Content-Type": "application/xml"},
            "<urlset><url><loc>https://example.com/</loc><loc>https://example.com/unapproved-page</loc></url></urlset>",
        ),
        "https://example.com/": (
            200,
            {"Content-Type": "text/html"},
            "<html><head><title>Example Business</title><link rel='canonical' href='https://example.com/'></head>"
            "<body><h1>Example Business</h1><a href='https://example.com/unapproved-link'>More</a></body></html>",
        ),
        "https://example.com/unapproved-page": (200, {"Content-Type": "text/html"}, "<html><body>Unapproved</body></html>"),
        "https://example.com/unapproved-link": (200, {"Content-Type": "text/html"}, "<html><body>Unapproved</body></html>"),
    })

    write_opens = []
    sqlite_targets = []
    real_open = builtins.open
    real_path_open = Path.open
    real_sqlite_connect = sqlite3.connect

    def is_write_mode(mode: str) -> bool:
        return any(ch in mode for ch in ("w", "a", "x", "+"))

    def track_open(file, mode="r", *args, **kwargs):
        if is_write_mode(str(mode)):
            write_opens.append((Path(file).resolve(), str(mode)))
        return real_open(file, mode, *args, **kwargs)

    def track_path_open(self, mode="r", *args, **kwargs):
        if is_write_mode(str(mode)):
            write_opens.append((self.resolve(), str(mode)))
        return real_path_open(self, mode, *args, **kwargs)

    def fail_write(*args, **kwargs):
        pytest.fail("Direct Path.write_text or Path.write_bytes is forbidden; must use exclusive open('x')")

    def track_sqlite(database, *args, **kwargs):
        sqlite_targets.append(str(database))
        return real_sqlite_connect(database, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", track_open)
    monkeypatch.setattr(Path, "open", track_path_open)
    monkeypatch.setattr(Path, "write_text", fail_write)
    monkeypatch.setattr(Path, "write_bytes", fail_write)
    monkeypatch.setattr(sqlite3, "connect", track_sqlite)
    monkeypatch.setattr("builtins.input", lambda prompt: "CONFIRM")

    report_path = (tmp_path / "exclusive_report.md").resolve()
    main([
        "client-review", "--url", "https://example.com/", "--business-id", "example-business",
        "--name", "Example Business", "--description", "Appointment scheduling service",
        "--permission", str(live_perm), "--live-site", "--report", str(report_path),
    ])

    # Only GET requests to explicitly approved pages (unapproved links in HTML/sitemap are never fetched)
    approved_set = {"https://example.com/", "https://example.com/robots.txt", "https://example.com/sitemap.xml"}
    assert net["http_requests"]
    for method, host, _port, path, hdrs in net["http_requests"]:
        assert method == "GET"
        assert f"https://{host}{path}" in approved_set
        assert not ({"authorization", "cookie", "x-api-key"} & {k.lower() for k in hdrs})

    # Only in-memory SQLite was used, and the ONLY file opened for writing is the new report file with mode 'x'
    assert sqlite_targets == [":memory:"]
    assert write_opens == [(report_path, "x")]
    assert report_path.is_file()


def test_report_fixes_appear_as_copyable_suggestions_for_client_to_apply_and_never_mutate_inputs(tmp_path, monkeypatch):
    from hashlib import sha256

    forbid_network(monkeypatch)
    html_body = (
        "<html><head><title>Portal</title></head>"
        "<body><h2>How does reminder setup work across calendar devices?</h2>"
        "<p>Reminder setup works across calendar devices automatically in two minutes with our 100% guaranteed platform.</p>"
        "</body></html>"
    )
    permission, fixtures = inputs(
        tmp_path,
        fixture_change=lambda f: f["pages"]["https://example.com/"].update({"body": html_body}),
    )
    attestation = tmp_path / "attestations.json"
    attestation.write_text(json.dumps([{
        "native_id": "q-remind",
        "excerpt": "How does reminder setup work across calendar devices?",
        "claim": "How does reminder setup work across calendar devices?",
        "minimized_by_founder": True,
    }]), encoding="utf-8")

    before_hashes = {
        p.name: sha256(p.read_bytes()).hexdigest()
        for p in (permission, fixtures, attestation)
    }

    result = run_client_review(
        profile("https://example.com/"),
        permission_path=permission,
        fixture_path=fixtures,
        attestations_path=attestation,
    )
    after_hashes = {
        p.name: sha256(p.read_bytes()).hexdigest()
        for p in (permission, fixtures, attestation)
    }
    assert before_hashes == after_hashes

    _, after_s1 = result.report.split("## Section 1: Site improvements\n", 1)
    section_1, _ = after_s1.split("\n## Section 2: Acquisition action\n", 1)

    assert (
        "Any fix offered below is a suggestion only (copyable text for the client to apply); "
        "FounderReach never modifies a client repository, hosting, deployment or database."
    ) in section_1

    finding_lines = [line for line in section_1.splitlines() if "Suggested technical change:" in line]
    assert len(finding_lines) >= 6
    for line in finding_lines:
        assert "Suggestion (copyable text for client to apply; never applied by FounderReach): `" in line
        match = re.search(r"Suggestion \(copyable text for client to apply; never applied by FounderReach\): `([^`]+)`\.", line)
        assert match and match.group(1).strip()


