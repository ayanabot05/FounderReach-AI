"""Tests for Super Admin Portal, Stripe Checkout, and Rate Limiting."""
import pytest
import uuid
from founderreach.config import settings
from founderreach.auth import (
    register_user,
    authenticate_user,
    set_user_role,
    create_access_token,
    decode_access_token,
    bootstrap_admin_user
)
from founderreach.billing import (
    create_checkout_session,
    get_revenue_metrics,
    PLANS
)
from founderreach.admin import (
    get_admin_dashboard_stats,
    get_admin_audits_paginated
)
from founderreach.web.app import (
    CheckoutRequest,
    UserRoleRequest,
    create_checkout,
    admin_stats,
    admin_users,
    admin_set_user_role,
    admin_payments,
    admin_audits,
)


def test_admin_bootstrap_and_credentials():
    bootstrap_admin_user()
    admin_auth = authenticate_user(settings.ADMIN_EMAIL, settings.ADMIN_PASSWORD)
    assert admin_auth["user"]["email"] == settings.ADMIN_EMAIL.lower()
    assert admin_auth["user"]["role"] == "admin"
    assert "token" in admin_auth


def test_admin_stats_and_overview():
    admin = {"id": "adm_1", "email": settings.ADMIN_EMAIL, "role": "admin"}
    stats = admin_stats(admin_user=admin)
    assert "overview" in stats
    assert "totalUsers" in stats["overview"]
    assert "totalRevenueUsd" in stats["overview"]
    assert "systemHealth" in stats
    assert "databaseEngine" in stats["systemHealth"]


def test_admin_user_management():
    unique_email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    reg = register_user(unique_email, "mypassword123", "Demo User")
    user_id = reg["user"]["id"]
    assert reg["user"]["role"] == "user"

    admin = {"id": "adm_1", "email": settings.ADMIN_EMAIL, "role": "admin"}
    # List users
    users_page = admin_users(page=1, limit=10, search=unique_email, admin_user=admin)
    assert users_page["total"] >= 1
    assert any(u["id"] == user_id for u in users_page["items"])

    # Promote to admin
    role_res = admin_set_user_role(user_id, UserRoleRequest(role="admin"), admin_user=admin)
    assert role_res["updated"] is True
    assert role_res["newRole"] == "admin"


def test_stripe_checkout_session_creation():
    # Test Launch Audit $49
    req_launch = CheckoutRequest(
        plan_id="launch_audit",
        domain="www.indieproduct.com",
        user_email="buyer@indie.com"
    )
    res_launch = create_checkout(req_launch)
    assert "checkout_url" in res_launch
    assert res_launch["amount_cents"] == 4900

    # Test Founder Plan $29/mo
    req_founder = CheckoutRequest(
        plan_id="founder_monthly",
        domain="www.indieproduct.com",
        user_email="buyer@indie.com"
    )
    res_founder = create_checkout(req_founder)
    assert "checkout_url" in res_founder
    assert res_founder["amount_cents"] == 2900

    # Revenue metrics should reflect orders
    rev = get_revenue_metrics()
    assert rev["total_orders"] >= 2
    assert rev["total_revenue_usd"] >= 78.0


def test_admin_payments_and_audits_pagination():
    admin = {"id": "adm_1", "email": settings.ADMIN_EMAIL, "role": "admin"}
    payments = admin_payments(page=1, limit=5, admin_user=admin)
    assert "items" in payments
    assert "total" in payments
    assert "pages" in payments

    audits = admin_audits(page=1, limit=5, admin_user=admin)
    assert "items" in audits
    assert "total" in audits
    assert "pages" in audits
