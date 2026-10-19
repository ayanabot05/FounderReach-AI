"""Autonomous Background Scheduler for FounderReach AI

Provides persistent 6-hour autonomous monitoring and snapshot history:
- Scheduled background crawls using APScheduler
- Audit snapshots recorded in SQLite
- Ranking drop & reachability drift detection
- API methods for registering, listing, and scanning monitored domains
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
import sqlite3
import uuid
from typing import Optional, List, Dict, Any

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from founderreach.config import settings
from founderreach.db import db
from founderreach.web.audit_service import perform_website_audit

logger = logging.getLogger(__name__)

_scheduler: Optional[BackgroundScheduler] = None


def _init_scheduler_tables():
    """Ensure monitored_domains and audit_snapshots tables exist in database."""
    with db.get_sqlite_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS monitored_domains (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            domain TEXT UNIQUE NOT NULL,
            frequency_hours INTEGER DEFAULT 6,
            last_scan_at TIMESTAMP,
            status TEXT DEFAULT 'ACTIVE',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_snapshots (
            id TEXT PRIMARY KEY,
            domain TEXT NOT NULL,
            health_score INTEGER NOT NULL,
            http_status INTEGER,
            dns_status TEXT,
            ssl_status TEXT,
            data_json TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        conn.commit()


_init_scheduler_tables()


def add_monitored_domain(domain: str, user_id: Optional[str] = None, frequency_hours: int = 6) -> dict:
    """Register a new domain for 6-hour autonomous monitoring."""
    clean = domain.strip().lower().replace("https://", "").replace("http://", "").rstrip("/")
    if not clean:
        raise ValueError("Domain cannot be empty.")

    dom_id = str(uuid.uuid4())
    with db.get_sqlite_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO monitored_domains (id, user_id, domain, frequency_hours, status)
        VALUES (?, ?, ?, ?, 'ACTIVE')
        ON CONFLICT(domain) DO UPDATE SET
            user_id=COALESCE(excluded.user_id, monitored_domains.user_id),
            frequency_hours=excluded.frequency_hours,
            status='ACTIVE'
        """, (dom_id, user_id, clean, frequency_hours))
        conn.commit()

    return {
        "domain": clean,
        "frequency_hours": frequency_hours,
        "status": "ACTIVE",
        "message": f"Domain '{clean}' registered for autonomous {frequency_hours}-hour monitoring."
    }


def remove_monitored_domain(domain: str, user_id: Optional[str] = None) -> bool:
    """Remove a domain from autonomous monitoring."""
    clean = domain.strip().lower().replace("https://", "").replace("http://", "").rstrip("/")
    with db.get_sqlite_connection() as conn:
        cursor = conn.cursor()
        if user_id:
            cursor.execute("DELETE FROM monitored_domains WHERE domain = ? AND user_id = ?", (clean, user_id))
        else:
            cursor.execute("DELETE FROM monitored_domains WHERE domain = ?", (clean,))
        conn.commit()
        return cursor.rowcount > 0


def list_monitored_domains(user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all monitored domains and their last scan snapshot."""
    with db.get_sqlite_connection() as conn:
        cursor = conn.cursor()
        if user_id:
            cursor.execute("SELECT * FROM monitored_domains WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
        else:
            cursor.execute("SELECT * FROM monitored_domains ORDER BY created_at DESC")
        rows = cursor.fetchall()

        results = []
        for r in rows:
            domain = r["domain"]
            # Fetch latest snapshot for domain
            cursor.execute("""
            SELECT health_score, http_status, created_at FROM audit_snapshots
            WHERE domain = ? ORDER BY created_at DESC LIMIT 1
            """, (domain,))
            snap = cursor.fetchone()

            results.append({
                "id": r["id"],
                "domain": domain,
                "frequencyHours": r["frequency_hours"],
                "status": r["status"],
                "lastScanAt": r["last_scan_at"] or (snap["created_at"] if snap else None),
                "latestHealthScore": snap["health_score"] if snap else None,
                "latestHttpStatus": snap["http_status"] if snap else None
            })
        return results


def record_audit_snapshot(domain: str, audit_data: dict) -> str:
    """Store an audit result snapshot in the database and update last_scan_at."""
    clean = domain.strip().lower().replace("https://", "").replace("http://", "").rstrip("/")
    snap_id = str(uuid.uuid4())
    score = audit_data.get("action_center", {}).get("health_score", 0)
    http_st = audit_data.get("reachability_evidence", {}).get("http_status") or audit_data.get("proof_of_work", {}).get("http_status")
    dns_st = audit_data.get("reachability_evidence", {}).get("dns_status")
    ssl_st = audit_data.get("reachability_evidence", {}).get("tls_status")
    now_str = datetime.now(timezone.utc).isoformat()

    with db.get_sqlite_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO audit_snapshots (id, domain, health_score, http_status, dns_status, ssl_status, data_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (snap_id, clean, score, http_st, dns_st, ssl_st, json.dumps(audit_data), now_str))

        cursor.execute("""
        UPDATE monitored_domains SET last_scan_at = ? WHERE domain = ?
        """, (now_str, clean))
        conn.commit()

    return snap_id


def get_domain_history(domain: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Retrieve historical snapshots for a given domain."""
    clean = domain.strip().lower().replace("https://", "").replace("http://", "").rstrip("/")
    with db.get_sqlite_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT id, domain, health_score, http_status, dns_status, ssl_status, created_at
        FROM audit_snapshots
        WHERE domain = ?
        ORDER BY created_at DESC
        LIMIT ?
        """, (clean, limit))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]


def execute_monitored_scans():
    """Background task: Iterates over all active monitored domains and performs autonomous audits."""
    logger.info("Executing autonomous background monitoring scan...")
    domains = list_monitored_domains()
    if not domains:
        logger.info("No active domains registered for background monitoring.")
        return

    for item in domains:
        dom = item["domain"]
        try:
            logger.info(f"Background monitoring scanning: {dom}")
            brand = dom.split(".")[0].capitalize()
            res = perform_website_audit(url=f"https://{dom}", business_name=brand)
            record_audit_snapshot(dom, res)
            logger.info(f"Recorded autonomous snapshot for {dom}: Score {res.get('action_center', {}).get('health_score')}")
        except Exception as exc:
            logger.error(f"Error during autonomous scan for {dom}: {exc}")


def scan_domain_now(domain: str) -> dict:
    """Manually trigger an immediate scan and record its snapshot."""
    clean = domain.strip().lower().replace("https://", "").replace("http://", "").rstrip("/")
    brand = clean.split(".")[0].capitalize()
    audit_res = perform_website_audit(url=f"https://{clean}", business_name=brand)
    snap_id = record_audit_snapshot(clean, audit_res)
    return {
        "snapshot_id": snap_id,
        "domain": clean,
        "audit": audit_res
    }


def start_background_scheduler():
    """Start the APScheduler background worker daemon."""
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        return _scheduler

    try:
        _scheduler = BackgroundScheduler(daemon=True)
        # Schedule the scan to run every 6 hours
        _scheduler.add_job(
            execute_monitored_scans,
            trigger=IntervalTrigger(hours=6),
            id="autonomous_growth_sentinel_6h",
            name="6-Hour Autonomous Discoverability Sentinel",
            replace_existing=True
        )
        _scheduler.start()
        logger.info("Autonomous 6-hour background scheduler started successfully.")
        return _scheduler
    except Exception as exc:
        logger.error(f"Failed to start APScheduler: {exc}")
        return None


def stop_background_scheduler():
    """Shut down the background scheduler."""
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Autonomous background scheduler stopped.")
