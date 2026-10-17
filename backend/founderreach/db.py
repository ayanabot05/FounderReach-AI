import sqlite3
import json
import logging
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
        self.supabase_client = None
        logger.info("Using local SQLite database.")

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

            # Ensure new columns exist in existing SQLite databases
            for col, col_type in [
                ("classification", "TEXT DEFAULT 'RESEARCH_INSIGHT'"),
                ("source_status", "TEXT DEFAULT 'SOURCE_UNVERIFIED'"),
                ("intent_status", "TEXT DEFAULT 'CUSTOMER_INTENT_UNVERIFIED'"),
                ("direct_problem_evidence", "TEXT"),
                ("rejection_reasons_json", "TEXT DEFAULT '[]'")
            ]:
                try:
                    cursor.execute(f"ALTER TABLE opportunities ADD COLUMN {col} {col_type}")
                except Exception:
                    pass
            
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
            
            # HTTP / Query Cache Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                cache_key TEXT PRIMARY KEY,
                cache_value TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            # Content Hash Table for Deduplication
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

    def save_opportunity(self, opp: CustomerOpportunity):
        # Legacy schema has global URL uniqueness and no tenant owner. M1 uses ResearchStore.
        raise PermissionError("Legacy opportunity writes are disabled until tenant migration")
        # 1. Save to Supabase if active
        if self.supabase_client:
            try:
                row_data = {
                    "id": opp.id,
                    "product_name": opp.product_name,
                    "platform": opp.platform,
                    "original_url": opp.original_url,
                    "discussion_date": opp.discussion_date,
                    "author": opp.author,
                    "classification": opp.classification,
                    "source_status": opp.source_status,
                    "intent_status": opp.intent_status,
                    "direct_problem_evidence": opp.direct_problem_evidence,
                    "rejection_reasons": opp.rejection_reasons,
                    "customer_problem": opp.customer_problem,
                    "why_relevant": opp.why_relevant,
                    "evidence_excerpt": opp.evidence_excerpt,
                    "total_score": opp.score.total_score,
                    "score_json": opp.score.model_dump(mode="json"),
                    "suggested_response": opp.suggested_response,
                    "verification_json": opp.verification.model_dump(mode="json"),
                    "feedback": opp.feedback,
                    "feedback_notes": opp.feedback_notes
                }
                self.supabase_client.table("opportunities").upsert(row_data).execute()
            except Exception as e:
                logger.warning(f"Error saving opportunity to Supabase: {e}. Writing to SQLite fallback.")

        # 2. Always persist to SQLite for local reliability
        with self.get_sqlite_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO opportunities (
                id, product_name, platform, original_url, discussion_date, author,
                classification, source_status, intent_status, direct_problem_evidence, rejection_reasons_json,
                customer_problem, why_relevant, evidence_excerpt, total_score,
                score_json, suggested_response, verification_json, feedback, feedback_notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(original_url) DO UPDATE SET
                classification=excluded.classification,
                source_status=excluded.source_status,
                intent_status=excluded.intent_status,
                direct_problem_evidence=excluded.direct_problem_evidence,
                rejection_reasons_json=excluded.rejection_reasons_json,
                total_score=excluded.total_score,
                score_json=excluded.score_json,
                suggested_response=excluded.suggested_response,
                verification_json=excluded.verification_json,
                feedback=COALESCE(opportunities.feedback, excluded.feedback),
                feedback_notes=COALESCE(opportunities.feedback_notes, excluded.feedback_notes)
            """, (
                opp.id,
                opp.product_name,
                opp.platform,
                opp.original_url,
                opp.discussion_date,
                opp.author,
                opp.classification,
                opp.source_status,
                opp.intent_status,
                opp.direct_problem_evidence,
                json.dumps(opp.rejection_reasons),
                opp.customer_problem,
                opp.why_relevant,
                opp.evidence_excerpt,
                opp.score.total_score,
                opp.score.model_dump_json(),
                opp.suggested_response,
                opp.verification.model_dump_json(),
                opp.feedback,
                opp.feedback_notes
            ))
            conn.commit()

    def get_opportunities(self, product_name: Optional[str] = None, min_score: float = 0.0) -> List[CustomerOpportunity]:
        # Try fetching from Supabase first if active
        if self.supabase_client:
            try:
                query = self.supabase_client.table("opportunities").select("*").gte("total_score", min_score)
                if product_name:
                    query = query.eq("product_name", product_name)
                res = query.order("total_score", desc=True).execute()
                
                results = []
                for r in res.data:
                    score_dict = r["score_json"] if isinstance(r["score_json"], dict) else json.loads(r["score_json"])
                    verif_dict = r["verification_json"] if isinstance(r["verification_json"], dict) else json.loads(r["verification_json"])
                    rejections = r.get("rejection_reasons") or []
                    if isinstance(rejections, str):
                        try:
                            rejections = json.loads(rejections)
                        except Exception:
                            rejections = [rejections]

                    results.append(CustomerOpportunity(
                        id=r["id"],
                        product_name=r["product_name"],
                        platform=r["platform"],
                        original_url=r["original_url"],
                        discussion_date=r["discussion_date"],
                        author=r["author"],
                        classification=r.get("classification") or "RESEARCH_INSIGHT",
                        source_status=r.get("source_status") or "SOURCE_UNVERIFIED",
                        intent_status=r.get("intent_status") or "CUSTOMER_INTENT_UNVERIFIED",
                        direct_problem_evidence=r.get("direct_problem_evidence"),
                        rejection_reasons=rejections,
                        customer_problem=r["customer_problem"],
                        why_relevant=r["why_relevant"],
                        evidence_excerpt=r["evidence_excerpt"],
                        score=ScoreBreakdown(**score_dict),
                        suggested_response=r["suggested_response"],
                        verification=SourceVerification(**verif_dict),
                        feedback=r.get("feedback"),
                        feedback_notes=r.get("feedback_notes")
                    ))
                return results
            except Exception as e:
                logger.warning(f"Error reading from Supabase: {e}. Reading from SQLite.")

        # Fallback to SQLite
        with self.get_sqlite_connection() as conn:
            cursor = conn.cursor()
            if product_name:
                cursor.execute("""
                SELECT * FROM opportunities 
                WHERE product_name = ? AND total_score >= ?
                ORDER BY total_score DESC
                """, (product_name, min_score))
            else:
                cursor.execute("""
                SELECT * FROM opportunities 
                WHERE total_score >= ?
                ORDER BY total_score DESC
                """, (min_score,))
            
            rows = cursor.fetchall()
            results = []
            for r in rows:
                score_dict = json.loads(r["score_json"])
                verif_dict = json.loads(r["verification_json"])
                try:
                    rejections = json.loads(r["rejection_reasons_json"]) if "rejection_reasons_json" in r.keys() and r["rejection_reasons_json"] else []
                except Exception:
                    rejections = []

                results.append(CustomerOpportunity(
                    id=r["id"],
                    product_name=r["product_name"],
                    platform=r["platform"],
                    original_url=r["original_url"],
                    discussion_date=r["discussion_date"],
                    author=r["author"],
                    classification=r["classification"] if "classification" in r.keys() and r["classification"] else "RESEARCH_INSIGHT",
                    source_status=r["source_status"] if "source_status" in r.keys() and r["source_status"] else "SOURCE_UNVERIFIED",
                    intent_status=r["intent_status"] if "intent_status" in r.keys() and r["intent_status"] else "CUSTOMER_INTENT_UNVERIFIED",
                    direct_problem_evidence=r["direct_problem_evidence"] if "direct_problem_evidence" in r.keys() else None,
                    rejection_reasons=rejections,
                    customer_problem=r["customer_problem"],
                    why_relevant=r["why_relevant"],
                    evidence_excerpt=r["evidence_excerpt"],
                    score=ScoreBreakdown(**score_dict),
                    suggested_response=r["suggested_response"],
                    verification=SourceVerification(**verif_dict),
                    feedback=r["feedback"],
                    feedback_notes=r["feedback_notes"]
                ))
            return results

    def update_feedback(self, opp_id: str, feedback: str, notes: Optional[str] = None) -> bool:
        raise PermissionError("Legacy feedback writes are disabled until tenant authorization")
        if self.supabase_client:
            try:
                update_data = {"feedback": feedback}
                if notes:
                    update_data["feedback_notes"] = notes
                self.supabase_client.table("opportunities").update(update_data).eq("id", opp_id).execute()
            except Exception as e:
                logger.warning(f"Error updating feedback in Supabase: {e}")

        with self.get_sqlite_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE opportunities 
            SET feedback = ?, feedback_notes = COALESCE(?, feedback_notes)
            WHERE id = ?
            """, (feedback, notes, opp_id))
            conn.commit()
            return cursor.rowcount > 0

    def record_cost(self, service: str, model: str, operation: str, tokens_in: int, tokens_out: int, 
                    cost_usd: float, cost_inr: float, cached: bool = False, notes: str = ""):
        if self.supabase_client:
            try:
                self.supabase_client.table("cost_ledger").insert({
                    "service": service,
                    "model": model,
                    "operation": operation,
                    "tokens_in": tokens_in,
                    "tokens_out": tokens_out,
                    "cost_usd": cost_usd,
                    "cost_inr": cost_inr,
                    "cached": cached,
                    "notes": notes
                }).execute()
            except Exception as e:
                logger.warning(f"Error logging cost to Supabase: {e}")

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

    def get_cache(self, key: str) -> Optional[str]:
        with self.get_sqlite_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT cache_value FROM cache WHERE cache_key = ?", (key,))
            row = cursor.fetchone()
            return row["cache_value"] if row else None

    def set_cache(self, key: str, value: str):
        with self.get_sqlite_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO cache (cache_key, cache_value) VALUES (?, ?)", (key, value))
            conn.commit()

    def record_content_hash(self, content_hash: str, opp_id: str, original_url: str):
        if self.supabase_client:
            try:
                self.supabase_client.table("content_hashes").insert({
                    "content_hash": content_hash,
                    "opportunity_id": opp_id,
                    "original_url": original_url
                }).execute()
            except Exception:
                pass

        with self.get_sqlite_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO content_hashes (content_hash, opportunity_id, original_url) VALUES (?, ?, ?)",
                           (content_hash, opp_id, original_url))
            conn.commit()

    def is_hash_seen(self, content_hash: str) -> bool:
        with self.get_sqlite_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM content_hashes WHERE content_hash = ?", (content_hash,))
            return cursor.fetchone() is not None

db = Database()
