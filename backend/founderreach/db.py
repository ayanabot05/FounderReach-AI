import sqlite3
import json
import logging
import time
from pathlib import Path
from typing import List, Optional, Dict, Any
from founderreach.config import settings
from founderreach.models import CustomerOpportunity, ScoreBreakdown, SourceVerification

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path) if db_path else settings.DB_PATH
        self.supabase_client = None
        self._sqlite_initialized = False
        self._initializing = False
        self._init_supabase()
        if db_path is not None:
            self._init_sqlite()

    def _init_supabase(self):
        """Initialize connection to Supabase if configured."""
        if settings.SUPABASE_ENABLED and settings.SUPABASE_URL and (settings.SUPABASE_SECRET_KEY or settings.SUPABASE_ANON_KEY):
            try:
                from supabase import create_client
                key = settings.SUPABASE_SECRET_KEY or settings.SUPABASE_ANON_KEY
                self.supabase_client = create_client(settings.SUPABASE_URL, key)
                logger.info("Connected to Supabase PostgreSQL database.")
            except Exception as exc:
                logger.warning(f"Failed to initialize Supabase client: {exc}. Falling back to SQLite.")
                self.supabase_client = None
        else:
            self.supabase_client = None
            logger.info("Using local SQLite database engine.")

    def get_sqlite_connection(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        if not self._sqlite_initialized and not self._initializing:
            self._initializing = True
            try:
                self._init_sqlite()
                self._sqlite_initialized = True
            finally:
                self._initializing = False
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_sqlite(self):
        self._sqlite_initialized = True
        with self.get_sqlite_connection() as conn:
            cursor = conn.cursor()
            
            # Users Table (with role for Super Admin access)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                name TEXT NOT NULL,
                active_domain TEXT,
                role TEXT DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
            except Exception:
                pass

            # Payments & Transactions Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                user_email TEXT NOT NULL,
                domain TEXT NOT NULL,
                plan_id TEXT NOT NULL,
                amount_cents INTEGER NOT NULL,
                currency TEXT DEFAULT 'usd',
                status TEXT NOT NULL,
                stripe_session_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # Daily Analytics & Activity Log
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS analytics_events (
                id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                user_id TEXT,
                domain TEXT,
                metadata_json TEXT,
                ip_address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # Monitored Domains for Autonomous 6-Hour Scheduler
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

            # Audit Snapshots History
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
            
            # Key-Value Cache with TTL
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                cache_key TEXT PRIMARY KEY,
                cache_value TEXT NOT NULL,
                expires_at REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            try:
                cursor.execute("ALTER TABLE cache ADD COLUMN expires_at REAL")
            except Exception:
                pass
            
            # Opportunities Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS opportunities (
                id TEXT PRIMARY KEY,
                product_name TEXT NOT NULL,
                platform TEXT NOT NULL,
                original_url TEXT NOT NULL UNIQUE,
                discussion_date TEXT,
                author TEXT,
                classification TEXT DEFAULT 'RESEARCH_INSIGHT',
                source_status TEXT DEFAULT 'SOURCE_UNVERIFIED',
                intent_status TEXT DEFAULT 'CUSTOMER_INTENT_UNVERIFIED',
                direct_problem_evidence TEXT,
                rejection_reasons_json TEXT DEFAULT '[]',
                customer_problem TEXT NOT NULL,
                why_relevant TEXT NOT NULL,
                evidence_excerpt TEXT NOT NULL,
                total_score REAL NOT NULL,
                score_json TEXT NOT NULL,
                suggested_response TEXT NOT NULL,
                verification_json TEXT NOT NULL,
                feedback TEXT,
                feedback_notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # Cost Ledger Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS cost_ledger (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                service TEXT NOT NULL,
                model TEXT,
                operation TEXT NOT NULL,
                tokens_in INTEGER DEFAULT 0,
                tokens_out INTEGER DEFAULT 0,
                cost_usd REAL DEFAULT 0.0,
                cost_inr REAL DEFAULT 0.0,
                cached BOOLEAN DEFAULT 0,
                notes TEXT
            )
            """)
            
            # Content Hashes
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS content_hashes (
                content_hash TEXT PRIMARY KEY,
                opportunity_id TEXT NOT NULL,
                original_url TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            conn.commit()

    def is_using_supabase(self) -> bool:
        return self.supabase_client is not None

    # =========================================================================
    # PAYMENTS & REVENUE QUERIES
    # =========================================================================

    def record_payment(self, payment_id: str, user_id: Optional[str], user_email: str,
                       domain: str, plan_id: str, amount_cents: int, status: str,
                       stripe_session_id: Optional[str] = None, currency: str = "usd"):
        if self.supabase_client:
            try:
                self.supabase_client.table("payments").insert({
                    "id": payment_id,
                    "user_id": user_id,
                    "user_email": user_email,
                    "domain": domain,
                    "plan_id": plan_id,
                    "amount_cents": amount_cents,
                    "currency": currency,
                    "status": status,
                    "stripe_session_id": stripe_session_id
                }).execute()
            except Exception as exc:
                logger.warning(f"Error inserting payment to Supabase: {exc}")

        with self.get_sqlite_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO payments (id, user_id, user_email, domain, plan_id, amount_cents, currency, status, stripe_session_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (payment_id, user_id, user_email, domain, plan_id, amount_cents, currency, status, stripe_session_id))
            conn.commit()

    def get_payments(self, page: int = 1, limit: int = 20, status: Optional[str] = None) -> Dict[str, Any]:
        offset = (page - 1) * limit
        with self.get_sqlite_connection() as conn:
            cursor = conn.cursor()
            if status:
                cursor.execute("SELECT COUNT(*) as cnt FROM payments WHERE status = ?", (status,))
                total = cursor.fetchone()["cnt"]
                cursor.execute("""
                SELECT * FROM payments WHERE status = ? ORDER BY created_at DESC LIMIT ? OFFSET ?
                """, (status, limit, offset))
            else:
                cursor.execute("SELECT COUNT(*) as cnt FROM payments")
                total = cursor.fetchone()["cnt"]
                cursor.execute("""
                SELECT * FROM payments ORDER BY created_at DESC LIMIT ? OFFSET ?
                """, (limit, offset))
            rows = cursor.fetchall()
            return {
                "items": [dict(r) for r in rows],
                "total": total,
                "page": page,
                "limit": limit,
                "pages": (total + limit - 1) // limit if total > 0 else 1
            }

    # =========================================================================
    # ANALYTICS & ACTIVITY LOGGING
    # =========================================================================

    def log_analytics_event(self, event_id: str, event_type: str, user_id: Optional[str] = None,
                            domain: Optional[str] = None, metadata: Optional[dict] = None,
                            ip_address: Optional[str] = None):
        meta_str = json.dumps(metadata or {})
        with self.get_sqlite_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO analytics_events (id, event_type, user_id, domain, metadata_json, ip_address)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (event_id, event_type, user_id, domain, meta_str, ip_address))
            conn.commit()

    # =========================================================================
    # CACHING WITH TTL
    # =========================================================================

    def get_cache(self, key: str) -> Optional[str]:
        now = time.time()
        with self.get_sqlite_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT cache_value, expires_at FROM cache WHERE cache_key = ?", (key,))
                row = cursor.fetchone()
                if not row:
                    return None
                if row["expires_at"] and row["expires_at"] < now:
                    cursor.execute("DELETE FROM cache WHERE cache_key = ?", (key,))
                    conn.commit()
                    return None
                return row["cache_value"]
            except sqlite3.OperationalError:
                # Column expires_at might be missing in legacy table
                cursor.execute("SELECT cache_value FROM cache WHERE cache_key = ?", (key,))
                row = cursor.fetchone()
                return row["cache_value"] if row else None

    def set_cache(self, key: str, value: str, ttl_seconds: Optional[int] = None):
        expires_at = time.time() + (ttl_seconds or settings.CACHE_TTL_SECONDS)
        with self.get_sqlite_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT OR REPLACE INTO cache (cache_key, cache_value, expires_at) VALUES (?, ?, ?)",
                               (key, value, expires_at))
            except sqlite3.OperationalError:
                cursor.execute("INSERT OR REPLACE INTO cache (cache_key, cache_value) VALUES (?, ?)", (key, value))
            conn.commit()

    # =========================================================================
    # DEDUPLICATION HASHES & OPPORTUNITY PROTOCOL
    # =========================================================================

    def is_hash_seen(self, content_hash: str) -> bool:
        with self.get_sqlite_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM content_hashes WHERE content_hash = ?", (content_hash,))
            return cursor.fetchone() is not None

    def record_content_hash(self, content_hash: str, opportunity_id: str, original_url: str):
        with self.get_sqlite_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO content_hashes (content_hash, opportunity_id, original_url) VALUES (?, ?, ?)",
                           (content_hash, opportunity_id, original_url))
            conn.commit()

    def save_opportunity(self, opp: Any):
        raise PermissionError("Legacy opportunity writes are disabled until tenant migration")

    def update_feedback(self, opp_id: str, feedback: str, notes: Optional[str] = None) -> bool:
        raise PermissionError("Legacy feedback writes are disabled until tenant authorization")

    # =========================================================================
    # COST LEDGER
    # =========================================================================

    def record_cost(self, service: str, model: str, operation: str, tokens_in: int, tokens_out: int, 
                    cost_usd: float, cost_inr: float, cached: bool = False, notes: str = ""):
        with self.get_sqlite_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO cost_ledger (service, model, operation, tokens_in, tokens_out, cost_usd, cost_inr, cached, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (service, model, operation, tokens_in, tokens_out, cost_usd, cost_inr, 1 if cached else 0, notes))
            conn.commit()

    def get_total_spend(self) -> Dict[str, float]:
        with self.get_sqlite_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT SUM(cost_inr) as total_inr, SUM(cost_usd) as total_usd FROM cost_ledger")
            row = cursor.fetchone()
            return {
                "total_inr": row["total_inr"] or 0.0,
                "total_usd": row["total_usd"] or 0.0
            }

db = Database()
