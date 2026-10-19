"""Stripe Billing & Payment Integration for FounderReach AI

Handles:
- Stripe Checkout Session generation for $49 Launch Audit, $29 Founder, $69 Growth, and $199 Agency tiers
- Stripe webhook signature verification & fulfillment
- Graceful test sandbox fallback when live Stripe keys are not yet configured
- Transaction records and revenue telemetry in SQLite & Supabase
"""
from __future__ import annotations

import logging
import os
import uuid
from typing import Optional, Dict, Any

from founderreach.config import settings
from founderreach.db import db

logger = logging.getLogger(__name__)

# Standard Plan Definitions
PLANS = {
    "launch_audit": {
        "name": "FounderReach Launch Audit",
        "description": "Full technical deep audit + done-with-you verification + 14-day recheck guarantee",
        "amount_cents": 4900,
        "currency": "usd",
        "mode": "payment"
    },
    "founder_monthly": {
        "name": "Founder Plan",
        "description": "24/7 Sentinel monitoring (every 6 hours) & curated Demand Radar for up to 3 domains",
        "amount_cents": 2900,
        "currency": "usd",
        "mode": "subscription"
    },
    "growth_monthly": {
        "name": "Growth Plan",
        "description": "Autonomous monitoring for up to 10 domains with Slack/Discord webhooks",
        "amount_cents": 6900,
        "currency": "usd",
        "mode": "subscription"
    },
    "agency_monthly": {
        "name": "Agency Plan",
        "description": "Unlimited domain audits, white-labeled PDF/MD reports, and API access",
        "amount_cents": 19900,
        "currency": "usd",
        "mode": "subscription"
    }
}


def create_checkout_session(
    plan_id: str,
    domain: str,
    user_email: str,
    user_id: Optional[str] = None,
    success_url: Optional[str] = None,
    cancel_url: Optional[str] = None
) -> Dict[str, Any]:
    """Create a Stripe checkout session or sandbox test session."""
    plan = PLANS.get(plan_id)
    if not plan:
        raise ValueError(f"Unknown plan '{plan_id}'. Choose from: {list(PLANS.keys())}")

    clean_domain = domain.strip().lower().replace("https://", "").replace("http://", "").rstrip("/")
    fallback_success = success_url or f"http://localhost:3005/#stage-pricing?payment=success&domain={clean_domain}&plan={plan_id}"
    fallback_cancel = cancel_url or f"http://localhost:3005/#stage-pricing?payment=cancelled"

    # Live Stripe Integration if STRIPE_SECRET_KEY is configured
    if settings.STRIPE_SECRET_KEY and settings.STRIPE_SECRET_KEY.startswith("sk_"):
        try:
            import stripe
            stripe.api_key = settings.STRIPE_SECRET_KEY

            line_items = [{
                "price_data": {
                    "currency": plan["currency"],
                    "product_data": {
                        "name": plan["name"],
                        "description": f"{plan['description']} (Domain: {clean_domain})"
                    },
                    "unit_amount": plan["amount_cents"],
                    **({"recurring": {"interval": "month"}} if plan["mode"] == "subscription" else {})
                },
                "quantity": 1
            }]

            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                customer_email=user_email,
                line_items=line_items,
                mode=plan["mode"],
                success_url=fallback_success + "&session_id={CHECKOUT_SESSION_ID}",
                cancel_url=fallback_cancel,
                metadata={
                    "plan_id": plan_id,
                    "domain": clean_domain,
                    "user_id": user_id or "anonymous",
                    "user_email": user_email
                }
            )

            payment_id = str(uuid.uuid4())
            db.record_payment(
                payment_id=payment_id,
                user_id=user_id,
                user_email=user_email,
                domain=clean_domain,
                plan_id=plan_id,
                amount_cents=plan["amount_cents"],
                status="pending",
                stripe_session_id=session.id
            )

            return {
                "checkout_url": session.url,
                "session_id": session.id,
                "plan_id": plan_id,
                "amount_cents": plan["amount_cents"],
                "provider": "stripe_live"
            }
        except Exception as exc:
            logger.error(f"Stripe session creation error: {exc}")
            raise RuntimeError(f"Payment gateway error: {str(exc)}")

    # Test Sandbox Simulation (Works with zero keys for local dev & testing)
    sim_session_id = f"sim_sess_{uuid.uuid4().hex[:12]}"
    payment_id = str(uuid.uuid4())
    db.record_payment(
        payment_id=payment_id,
        user_id=user_id,
        user_email=user_email,
        domain=clean_domain,
        plan_id=plan_id,
        amount_cents=plan["amount_cents"],
        status="paid_sandbox",
        stripe_session_id=sim_session_id
    )

    logger.info(f"Sandbox payment created for {user_email}: {plan_id} (${plan['amount_cents']/100:.2f})")
    return {
        "checkout_url": f"{fallback_success}&session_id={sim_session_id}&sandbox=true",
        "session_id": sim_session_id,
        "plan_id": plan_id,
        "amount_cents": plan["amount_cents"],
        "provider": "sandbox_mode",
        "message": "Stripe keys not set in .env. Order processed in sandbox test mode."
    }


def handle_stripe_webhook(payload: bytes, sig_header: Optional[str] = None) -> Dict[str, Any]:
    """Process incoming Stripe webhook event."""
    if not settings.STRIPE_SECRET_KEY or not settings.STRIPE_WEBHOOK_SECRET:
        return {"received": True, "note": "Stripe webhook secret not configured in .env"}

    import stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except Exception as exc:
        logger.error(f"Webhook signature verification failed: {exc}")
        raise ValueError(f"Webhook verification failed: {exc}")

    event_type = event["type"]
    if event_type == "checkout.session.completed":
        session = event["data"]["object"]
        session_id = session.get("id")
        meta = session.get("metadata", {})
        plan_id = meta.get("plan_id", "launch_audit")
        domain = meta.get("domain", "")
        email = session.get("customer_details", {}).get("email") or meta.get("user_email", "")
        amount = session.get("amount_total", 0)

        payment_id = str(uuid.uuid4())
        db.record_payment(
            payment_id=payment_id,
            user_id=meta.get("user_id"),
            user_email=email,
            domain=domain,
            plan_id=plan_id,
            amount_cents=amount,
            status="completed",
            stripe_session_id=session_id
        )
        logger.info(f"Payment completed via Stripe: {session_id} for {email} ({plan_id})")

    return {"status": "success", "event": event_type}


def get_revenue_metrics() -> Dict[str, Any]:
    """Calculate aggregate revenue numbers for the admin portal."""
    with db.get_sqlite_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total_orders, SUM(amount_cents) as total_cents FROM payments WHERE status IN ('completed', 'paid_sandbox')")
        row = cursor.fetchone()
        total_orders = row["total_orders"] or 0
        total_cents = row["total_cents"] or 0

        # Past 30 days
        cursor.execute("""
        SELECT COUNT(*) as orders_30d, SUM(amount_cents) as cents_30d
        FROM payments
        WHERE status IN ('completed', 'paid_sandbox')
          AND created_at >= datetime('now', '-30 days')
        """)
        row_30d = cursor.fetchone()
        orders_30d = row_30d["orders_30d"] or 0
        cents_30d = row_30d["cents_30d"] or 0

        return {
            "total_orders": total_orders,
            "total_revenue_usd": round(total_cents / 100.0, 2),
            "orders_30d": orders_30d,
            "revenue_30d_usd": round(cents_30d / 100.0, 2)
        }
