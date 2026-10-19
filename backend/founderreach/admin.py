"""Super Admin Portal Management Service for FounderReach AI

Provides complete administrative control:
- High-level executive KPIs (Users, Revenue, Audits, Monitored Domains)
- User lifecycle management (Search, Roles, Deletion)
- Payments & revenue ledger inspection
- Live audit feed across all targets
- System health, scheduler monitoring, and database telemetry
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

from founderreach.config import settings
from founderreach.db import db
from founderreach.auth import list_users_paginated, set_user_role, delete_user
from founderreach.billing import get_revenue_metrics
from founderreach.scheduler import list_monitored_domains

logger = logging.getLogger(__name__)


def get_admin_dashboard_stats() -> Dict[str, Any]:
    """Compile comprehensive executive telemetry for the Super Admin overview."""
    with db.get_sqlite_connection() as conn:
        cursor = conn.cursor()

        # Total Users
        cursor.execute("SELECT COUNT(*) as total_users FROM users")
        total_users = cursor.fetchone()["total_users"] or 0

        cursor.execute("SELECT COUNT(*) as users_today FROM users WHERE DATE(created_at) = DATE('now')")
        users_today = cursor.fetchone()["users_today"] or 0

        # Total Audits Snapshots
        cursor.execute("SELECT COUNT(*) as total_audits, AVG(health_score) as avg_score FROM audit_snapshots")
        row_audit = cursor.fetchone()
        total_audits = row_audit["total_audits"] or 0
        avg_health = round(row_audit["avg_score"] or 74.0, 1)

        cursor.execute("SELECT COUNT(*) as audits_today FROM audit_snapshots WHERE DATE(created_at) = DATE('now')")
        audits_today = cursor.fetchone()["audits_today"] or 0

        # Monitored Domains
        cursor.execute("SELECT COUNT(*) as total_monitored FROM monitored_domains WHERE status = 'ACTIVE'")
        total_monitored = cursor.fetchone()["total_monitored"] or 0

        # 7-Day Activity Stream
        cursor.execute("""
        SELECT DATE(created_at) as day, COUNT(*) as count
        FROM audit_snapshots
        WHERE created_at >= datetime('now', '-7 days')
        GROUP BY DATE(created_at)
        ORDER BY day ASC
        """)
        audit_activity = [dict(r) for r in cursor.fetchall()]

    revenue = get_revenue_metrics()

    return {
        "overview": {
            "totalUsers": total_users,
            "newUsersToday": users_today,
            "totalAudits": total_audits,
            "auditsToday": audits_today,
            "avgHealthScore": avg_health,
            "activeMonitoredDomains": total_monitored,
            "totalRevenueUsd": revenue["total_revenue_usd"],
            "revenue30dUsd": revenue["revenue_30d_usd"],
            "totalOrders": revenue["total_orders"]
        },
        "activity7d": audit_activity,
        "systemHealth": {
            "version": settings.VERSION,
            "databaseEngine": "Supabase PostgreSQL" if db.is_using_supabase() else "Local SQLite Engine",
            "schedulerInterval": "Every 6 Hours",
            "stripeStatus": "Live Gateway" if (settings.STRIPE_SECRET_KEY and settings.STRIPE_SECRET_KEY.startswith("sk_")) else "Sandbox Test Mode",
            "redditConnector": "Authorized OAuth" if settings.REDDIT_ENABLED else "Disabled by Policy (Standard)",
            "geminiApi": "Active" if settings.GEMINI_API_KEY else "Deterministic NLP (₹0 Cost)"
        }
    }


def get_admin_audits_paginated(page: int = 1, limit: int = 20, domain: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve historical audits with pagination and domain filtering."""
    offset = (page - 1) * limit
    with db.get_sqlite_connection() as conn:
        cursor = conn.cursor()
        if domain and domain.strip():
            term = f"%{domain.strip().lower()}%"
            cursor.execute("SELECT COUNT(*) as cnt FROM audit_snapshots WHERE LOWER(domain) LIKE ?", (term,))
            total = cursor.fetchone()["cnt"]
            cursor.execute("""
            SELECT id, domain, health_score, http_status, dns_status, ssl_status, created_at
            FROM audit_snapshots
            WHERE LOWER(domain) LIKE ?
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """, (term, limit, offset))
        else:
            cursor.execute("SELECT COUNT(*) as cnt FROM audit_snapshots")
            total = cursor.fetchone()["cnt"]
            cursor.execute("""
            SELECT id, domain, health_score, http_status, dns_status, ssl_status, created_at
            FROM audit_snapshots
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """, (limit, offset))

        rows = cursor.fetchall()
        return {
            "items": [dict(r) for r in rows],
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit if total > 0 else 1
        }
