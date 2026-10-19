"""Tests for P2 (User Auth), P3 (Background Scheduler), and P4 (Reddit Connector)."""
import pytest
import uuid
from founderreach.auth import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    register_user,
    authenticate_user,
    get_user_by_id,
)
from founderreach.scheduler import (
    add_monitored_domain,
    remove_monitored_domain,
    list_monitored_domains,
    record_audit_snapshot,
    get_domain_history,
)
from founderreach.connectors.reddit import RedditConnector, fetch_live_reddit_discussions
from founderreach.web.app import (
    RegisterRequest,
    LoginRequest,
    MonitoredDomainRequest,
    register,
    login,
    me,
    reddit_status,
    get_monitored_domains,
    register_domain_for_monitoring,
    delete_monitored_domain,
)


# =========================================================================
# P2: AUTHENTICATION TESTS
# =========================================================================

def test_password_hashing_and_verification():
    pwd = "founderSecret123!"
    pwd_hash, salt = hash_password(pwd)
    assert len(salt) > 10
    assert len(pwd_hash) == 64  # SHA-256 hex length
    assert verify_password(pwd, pwd_hash, salt) is True
    assert verify_password("wrongPassword", pwd_hash, salt) is False


def test_jwt_token_encode_decode():
    token = create_access_token("usr_123", "alex@test.com", "Alex")
    assert isinstance(token, str)
    decoded = decode_access_token(token)
    assert decoded["sub"] == "usr_123"
    assert decoded["email"] == "alex@test.com"
    assert decoded["name"] == "Alex"
    assert "exp" in decoded


def test_user_registration_and_authentication():
    unique_email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    reg = register_user(unique_email, "securepass123", "Sarah Connor")
    assert reg["user"]["email"] == unique_email
    assert reg["user"]["name"] == "Sarah Connor"
    assert "token" in reg

    # Duplicate registration should raise ValueError
    with pytest.raises(ValueError, match="already exists"):
        register_user(unique_email, "securepass123", "Sarah")

    # Login with valid credentials
    auth = authenticate_user(unique_email, "securepass123")
    assert auth["user"]["id"] == reg["user"]["id"]
    assert "token" in auth

    # Login with invalid password
    with pytest.raises(ValueError, match="Invalid email or password"):
        authenticate_user(unique_email, "wrongpass")


def test_api_auth_endpoints():
    unique_email = f"api_user_{uuid.uuid4().hex[:8]}@example.com"
    req = RegisterRequest(
        email=unique_email,
        password="password12345",
        name="Developer",
        active_domain="www.indie.io"
    )
    reg_res = register(req)
    assert reg_res["user"]["email"] == unique_email

    # Login via endpoint
    login_req = LoginRequest(email=unique_email, password="password12345")
    login_res = login(login_req)
    assert login_res["user"]["email"] == unique_email
    assert "token" in login_res

    # /api/auth/me
    current = me(current_user=login_res["user"])
    assert current["user"]["email"] == unique_email


# =========================================================================
# P3: BACKGROUND SCHEDULER & SNAPSHOT TESTS
# =========================================================================

def test_monitored_domains_registration_and_removal():
    domain_name = f"test-target-{uuid.uuid4().hex[:6]}.com"
    added = add_monitored_domain(domain_name, frequency_hours=6)
    assert added["domain"] == domain_name
    assert added["status"] == "ACTIVE"

    domains = list_monitored_domains()
    assert any(d["domain"] == domain_name for d in domains)

    removed = remove_monitored_domain(domain_name)
    assert removed is True

    domains_after = list_monitored_domains()
    assert not any(d["domain"] == domain_name for d in domains_after)


def test_audit_snapshots_storage_and_history():
    domain = f"snapshot-{uuid.uuid4().hex[:6]}.io"
    mock_audit = {
        "action_center": {"health_score": 85},
        "reachability_evidence": {
            "http_status": 200,
            "dns_status": "Verified (Pinned IP: 104.21.72.10)",
            "tls_status": "Valid TLS Certificate"
        }
    }
    snap_id = record_audit_snapshot(domain, mock_audit)
    assert snap_id is not None

    history = get_domain_history(domain, limit=5)
    assert len(history) >= 1
    assert history[0]["domain"] == domain
    assert history[0]["health_score"] == 85
    assert history[0]["http_status"] == 200


def test_api_monitor_endpoints():
    dom = f"api-monitored-{uuid.uuid4().hex[:6]}.com"
    req = MonitoredDomainRequest(domain=dom, frequency_hours=6)
    reg = register_domain_for_monitoring(req)
    assert reg["domain"] == dom

    listed = get_monitored_domains()
    assert any(d["domain"] == dom for d in listed["domains"])

    del_res = delete_monitored_domain(dom)
    assert del_res["deleted"] is True


# =========================================================================
# P4: REDDIT CONNECTOR TESTS
# =========================================================================

def test_reddit_connector_default_disabled():
    connector = RedditConnector()
    assert connector.is_enabled() is False
    # Live discussions helper reports status clearly when disabled
    feed = fetch_live_reddit_discussions("SEO")
    assert len(feed) > 0
    assert feed[0]["status"] == "DISABLED_BY_POLICY"


def test_reddit_connector_enabled_when_configured():
    connector = RedditConnector(
        client_id="fake_client_id_123",
        client_secret="fake_client_secret_abc",
        enabled=True
    )
    assert connector.is_enabled() is True
    assert connector.client_id == "fake_client_id_123"


def test_reddit_status_endpoint():
    status_res = reddit_status()
    assert "enabled" in status_res
    assert "user_agent" in status_res
    assert "policy" in status_res
