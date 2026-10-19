"""Comprehensive unit and security tests for FounderReach AI /api/audit logic."""
import socket
import pytest
from unittest.mock import patch, MagicMock

from founderreach.web.app import AuditRequest, audit
from founderreach.web.audit_service import (
    validate_public_url,
    perform_website_audit,
    SafeAuditFetcher,
    EnhancedPageParser,
    parse_robots_policy,
    MAX_BYTES
)
from founderreach.website import WebsiteFetchError, UnsafeWebsiteError


def test_validate_public_url_blocks_private_ips():
    bad_urls = [
        "http://192.168.1.1",
        "https://10.0.0.1",
        "http://127.0.0.1",
        "https://169.254.169.254",
        "http://0.0.0.0",
        "http://localhost",
        "https://service.local",
        "http://api.internal",
        "https://demo.test",
        "http://cluster.invalid",
    ]
    for ip_url in bad_urls:
        with pytest.raises(ValueError, match="prohibited"):
            validate_public_url(ip_url)


def test_validate_public_url_blocks_non_standard_ports_and_credentials():
    with pytest.raises(ValueError, match="standard ports"):
        validate_public_url("https://example.com:8443")
    with pytest.raises(ValueError, match="standard ports"):
        validate_public_url("http://example.com:8080")
    with pytest.raises(ValueError, match="credentials are prohibited"):
        validate_public_url("https://admin:secret@example.com")


def test_validate_public_url_allows_public_https():
    assert validate_public_url("https://example.com") == "https://example.com"
    assert validate_public_url("https://founderreach.ai") == "https://founderreach.ai"
    assert validate_public_url("http://scheduleflow.io") == "http://scheduleflow.io"


def test_audit_function_rejects_private_ip():
    req = AuditRequest(
        url="http://192.168.1.50",
        business_name="Test",
        description="Private target",
        target_audience="Devs",
        pain_point="None"
    )
    with pytest.raises(Exception) as exc_info:
        audit(req)
    assert "prohibited" in str(exc_info.value).lower()


def test_enhanced_page_parser_extracts_schema_and_metadata():
    html = """
    <!DOCTYPE html>
    <html>
      <head>
        <title>ScheduleFlow — Automated Appointment Reminders</title>
        <meta name="description" content="Automated appointment reminders and booking workflows for clinics.">
        <meta property="og:title" content="ScheduleFlow Reminders">
        <link rel="canonical" href="https://scheduleflow.io/">
        <script type="application/ld+json">
        {
          "@context": "https://schema.org",
          "@type": "SoftwareApplication",
          "name": "ScheduleFlow"
        }
        </script>
        <script type="application/ld+json">
        {
          "@context": "https://schema.org",
          "@type": "FAQPage",
          "mainEntity": [{
            "@type": "Question",
            "name": "How does it work?",
            "acceptedAnswer": {"@type": "Answer", "text": "It sends WhatsApp and SMS reminders."}
          }]
        }
        </script>
      </head>
      <body>
        <h1>Stop No-Shows</h1>
        <h2>Automated Clinic Scheduling</h2>
        <h3>Client Reviews</h3>
      </body>
    </html>
    """
    parser = EnhancedPageParser()
    parser.feed(html)
    assert parser.title.startswith("ScheduleFlow")
    assert "booking workflows" in [m.get("content", "") for m in parser.meta_tags if m.get("name") == "description"][0]
    assert parser.canonical == "https://scheduleflow.io/"
    assert len(parser.headings) == 3
    assert len(parser.jsonld_scripts) == 2
    assert any(s.get("@type") == "SoftwareApplication" for s in parser.jsonld_scripts)
    assert any(s.get("@type") == "FAQPage" for s in parser.jsonld_scripts)


@patch.object(SafeAuditFetcher, "fetch_resource")
@patch.object(SafeAuditFetcher, "_target")
def test_successful_audit_flow(mock_target, mock_fetch):
    mock_target.return_value = ("https://example.com", "example.com", 443, "93.184.216.34", "/")
    
    def side_effect(url):
        if url.endswith("/robots.txt"):
            return 200, {"content-type": "text/plain"}, b"User-agent: *\nAllow: /\n", url, "93.184.216.34", [url]
        elif url.endswith("/sitemap.xml"):
            return 200, {"content-type": "application/xml"}, b"<urlset><url><loc>https://example.com/</loc></url></urlset>", url, "93.184.216.34", [url]
        elif url.endswith("/llms.txt"):
            return 200, {"content-type": "text/plain"}, b"# Example\n> Knowledge for LLMs\n", url, "93.184.216.34", [url]
        else:
            page_html = (
                b"<html><head><title>Example Application</title>"
                b"<meta name='description' content='A verified example app for testing.'>"
                b"<meta name='viewport' content='width=device-width, initial-scale=1.0'>"
                b"<link rel='canonical' href='https://example.com'>"
                b"<meta property='og:title' content='Example App'>"
                b"<script type='application/ld+json'>{\"@context\":\"https://schema.org\",\"@type\":\"SoftwareApplication\",\"name\":\"Example\"}</script>"
                b"</head><body><h1>Main Title</h1><h2>Sub Title</h2><h3>Section</h3><img src='logo.png' alt='Logo'></body></html>"
            )
            return 200, {"content-type": "text/html; charset=utf-8"}, page_html, url, "93.184.216.34", [url]

    mock_fetch.side_effect = side_effect

    req = AuditRequest(
        url="https://example.com",
        business_name="ExampleApp",
        description="A verified example application.",
        target_audience="Developers",
        pain_point="Manual deployments"
    )
    result = audit(req)
    assert result["success"] is True
    assert result["proof_of_work"]["pinned_ip"] == "93.184.216.34"
    assert "Parsed via RobotFileParser" in result["proof_of_work"]["robots_txt_status"]
    assert "Detected at /sitemap.xml" in result["proof_of_work"]["sitemap_xml_status"]
    assert "Detected at /llms.txt" in result["proof_of_work"]["llms_txt_status"]
    assert result["proof_of_work"]["viewport_detected"] is True
    assert result["proof_of_work"]["h1_count"] == 1
    assert result["proof_of_work"]["images_missing_alt"] == 0

    assert "reachability_evidence" in result
    assert result["reachability_evidence"]["is_html"] is True
    assert result["reachability_evidence"]["http_status"] == 200

    assert "action_center" in result
    assert result["action_center"]["health_score"] > 50

    scores = result["scores"]
    assert scores["seo"]["score"] > 50
    assert scores["aeo"]["score"] > 50
    assert scores["geo"]["score"] > 50

    # Ensure all fixes contain clear disclaimer and platform guides
    for fix in result["fixes"]:
        assert "disclaimer" in fix
        assert "platforms" in fix
        assert "wordpress" in fix["platforms"]
        assert "webflow" in fix["platforms"]
        assert "framer" in fix["platforms"]
        assert "shopify" in fix["platforms"]


@patch.object(SafeAuditFetcher, "fetch_resource")
@patch.object(SafeAuditFetcher, "_target")
def test_robots_txt_blocks_audit(mock_target, mock_fetch):
    mock_target.return_value = ("https://example.com", "example.com", 443, "93.184.216.34", "/")
    
    # robots.txt forbids all crawlers
    disallow_robots = b"User-agent: *\nDisallow: /\n"
    mock_fetch.return_value = (200, {"content-type": "text/plain"}, disallow_robots, "https://example.com/robots.txt", "93.184.216.34", ["https://example.com/robots.txt"])

    req = AuditRequest(
        url="https://example.com",
        business_name="BlockedSite"
    )
    result = audit(req)
    assert result["success"] is False
    assert "disallow" in result["proof_of_work"]["robots_txt_status"].lower()
    assert "explicitly disallows" in result["proof_of_work"]["error_note"].lower()
    # Scores must be 0 when inspection is blocked
    assert result["scores"]["seo"]["score"] == 0
    assert result["scores"]["aeo"]["score"] == 0
    assert result["scores"]["geo"]["score"] == 0


@patch.object(SafeAuditFetcher, "fetch_resource")
@patch.object(SafeAuditFetcher, "_target")
def test_robots_txt_404_defaults_to_allowed(mock_target, mock_fetch):
    mock_target.return_value = ("https://example.com", "example.com", 443, "93.184.216.34", "/")
    
    def side_effect(url):
        if url.endswith("/robots.txt"):
            return 404, {}, b"Not Found", url, "93.184.216.34", [url]
        return 200, {"content-type": "text/html"}, b"<html><head><title>Demo</title></head><body><h1>Hello</h1></body></html>", url, "93.184.216.34", [url]

    mock_fetch.side_effect = side_effect

    req = AuditRequest(url="https://example.com")
    result = audit(req)
    assert result["success"] is True
    assert "404" in result["proof_of_work"]["robots_txt_status"]
    assert "crawlers allowed" in result["proof_of_work"]["robots_txt_status"].lower()


@patch.object(SafeAuditFetcher, "_target")
def test_dns_resolution_failure(mock_target):
    mock_target.side_effect = OSError("Domain does not exist")

    req = AuditRequest(url="https://nonexistent-domain-xyz123.com")
    result = audit(req)
    assert result["success"] is False
    assert "Resolution Failed" in result["proof_of_work"]["dns_status"]
    assert "DNS Error" in result["proof_of_work"]["error_note"]
    assert result["scores"]["seo"]["score"] == 0
