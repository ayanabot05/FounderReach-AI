"""Disposable local self-service store with account-scoped queries."""
import hashlib
import hmac
import json
import secrets
import sqlite3
import time
from pathlib import Path


def _password_hash(password: str, salt: bytes) -> str:
    return hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1).hex()


class SelfServiceStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS accounts (
                    id INTEGER PRIMARY KEY, email TEXT NOT NULL UNIQUE,
                    salt TEXT NOT NULL, password_hash TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS sessions (
                    token_hash TEXT PRIMARY KEY, account_id INTEGER NOT NULL,
                    csrf TEXT NOT NULL, expires_at INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS businesses (
                    id INTEGER PRIMARY KEY, account_id INTEGER NOT NULL,
                    website TEXT NOT NULL, snapshot_json TEXT NOT NULL,
                    profile_json TEXT NOT NULL, confirmed INTEGER NOT NULL DEFAULT 0,
                    version INTEGER NOT NULL DEFAULT 1);
                CREATE INDEX IF NOT EXISTS businesses_account ON businesses(account_id);
                CREATE TABLE IF NOT EXISTS actions (
                    id INTEGER PRIMARY KEY, account_id INTEGER NOT NULL, business_id INTEGER NOT NULL,
                    profile_version INTEGER NOT NULL, payload_json TEXT NOT NULL,
                    version_hash TEXT NOT NULL, status TEXT NOT NULL,
                    approved_at TEXT, outcome_json TEXT);
                CREATE INDEX IF NOT EXISTS actions_owner ON actions(account_id,business_id);
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY, account_id INTEGER NOT NULL, business_id INTEGER,
                    action_id INTEGER, event TEXT NOT NULL, detail_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
            """)

    def connection(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        return db

    def register(self, email: str, password: str):
        email = email.strip().lower()
        if "@" not in email or len(email) > 254 or len(password) < 12:
            raise ValueError("Enter an email and a password of at least 12 characters")
        salt = secrets.token_bytes(16)
        with self.connection() as db:
            try:
                cursor = db.execute("INSERT INTO accounts(email,salt,password_hash) VALUES(?,?,?)",
                                    (email, salt.hex(), _password_hash(password, salt)))
            except sqlite3.IntegrityError as exc:
                raise ValueError("Account already exists") from exc
            return cursor.lastrowid

    def login(self, email: str, password: str):
        with self.connection() as db:
            row = db.execute("SELECT * FROM accounts WHERE email=?", (email.strip().lower(),)).fetchone()
            if not row or not hmac.compare_digest(row["password_hash"], _password_hash(password, bytes.fromhex(row["salt"]))):
                raise ValueError("Invalid email or password")
            token = secrets.token_urlsafe(32)
            csrf = secrets.token_urlsafe(24)
            db.execute("INSERT INTO sessions VALUES(?,?,?,?)",
                       (hashlib.sha256(token.encode()).hexdigest(), row["id"], csrf, int(time.time()) + 12 * 3600))
            return token, csrf

    def session(self, token: str):
        if not token:
            return None
        digest = hashlib.sha256(token.encode()).hexdigest()
        with self.connection() as db:
            return db.execute("SELECT sessions.account_id, sessions.csrf, accounts.email FROM sessions "
                              "JOIN accounts ON accounts.id=sessions.account_id WHERE token_hash=? AND expires_at>?",
                              (digest, int(time.time()))).fetchone()

    def logout(self, token: str):
        with self.connection() as db:
            db.execute("DELETE FROM sessions WHERE token_hash=?", (hashlib.sha256(token.encode()).hexdigest(),))

    def add_business(self, account_id: int, snapshot: dict, proposal: dict):
        with self.connection() as db:
            cursor = db.execute("INSERT INTO businesses(account_id,website,snapshot_json,profile_json) VALUES(?,?,?,?)",
                                (account_id, snapshot["url"], json.dumps(snapshot), json.dumps(proposal)))
            business_id = cursor.lastrowid
            db.execute("INSERT INTO audit_events(account_id,business_id,event,detail_json) VALUES(?,?,?,?)",
                       (account_id, business_id, "business_added", json.dumps({"url": snapshot["url"]})))
            return business_id

    def list_businesses(self, account_id: int):
        with self.connection() as db:
            rows = db.execute("SELECT * FROM businesses WHERE account_id=? ORDER BY id DESC", (account_id,)).fetchall()
            return [self._business(row) for row in rows]

    def business(self, account_id: int, business_id: int):
        with self.connection() as db:
            row = db.execute("SELECT * FROM businesses WHERE id=? AND account_id=?", (business_id, account_id)).fetchone()
            return self._business(row) if row else None

    @staticmethod
    def _business(row):
        return {"id": row["id"], "website": row["website"], "snapshot": json.loads(row["snapshot_json"]),
                "profile": json.loads(row["profile_json"]), "confirmed": bool(row["confirmed"]),
                "version": row["version"]}

    def confirm_profile(self, account_id: int, business_id: int, profile: dict):
        with self.connection() as db:
            cursor = db.execute("UPDATE businesses SET profile_json=?, confirmed=1, version=version+1 "
                                "WHERE id=? AND account_id=?", (json.dumps(profile), business_id, account_id))
            if cursor.rowcount != 1:
                raise KeyError("Business not found")
            db.execute("INSERT INTO audit_events(account_id,business_id,event,detail_json) VALUES(?,?,?,?)",
                       (account_id, business_id, "profile_confirmed", json.dumps({"name": profile["name"]})))
        return self.business(account_id, business_id)

    def add_action(self, account_id: int, business_id: int, profile_version: int, payload: dict, digest: str):
        with self.connection() as db:
            cursor = db.execute("INSERT INTO actions(account_id,business_id,profile_version,payload_json,version_hash,status) "
                                "VALUES(?,?,?,?,?,?)", (account_id, business_id, profile_version, json.dumps(payload), digest, "proposed"))
            action_id = cursor.lastrowid
            db.execute("INSERT INTO audit_events(account_id,business_id,action_id,event,detail_json) VALUES(?,?,?,?,?)",
                       (account_id, business_id, action_id, "action_proposed", json.dumps({"version": digest})))
            return action_id

    def actions(self, account_id: int, business_id: int):
        with self.connection() as db:
            rows = db.execute("SELECT * FROM actions WHERE account_id=? AND business_id=? ORDER BY id DESC",
                              (account_id, business_id)).fetchall()
            return [self._action(row) for row in rows]

    def action(self, account_id: int, business_id: int, action_id: int):
        with self.connection() as db:
            row = db.execute("SELECT * FROM actions WHERE id=? AND account_id=? AND business_id=?",
                             (action_id, account_id, business_id)).fetchone()
            return self._action(row) if row else None

    @staticmethod
    def _action(row):
        return {"id": row["id"], "business_id": row["business_id"], "profile_version": row["profile_version"],
                "payload": json.loads(row["payload_json"]), "version_hash": row["version_hash"],
                "status": row["status"], "approved_at": row["approved_at"],
                "outcome": json.loads(row["outcome_json"]) if row["outcome_json"] else None}

    def approve(self, account_id: int, business_id: int, action_id: int, version_hash: str, approved_at: str):
        raise PermissionError("Unsigned self-service approval is disabled; use the signed gate")

    def record_outcome(self, account_id: int, business_id: int, action_id: int, outcome: dict):
        raise PermissionError("Outcome recording requires the integrated signed action lifecycle")
