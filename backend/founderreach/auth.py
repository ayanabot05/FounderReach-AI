"""Production User Authentication for FounderReach AI

Provides multi-tenant user authentication backed by SQLite:
- Cryptographic password hashing (PBKDF2-HMAC-SHA256 with random salt)
- Signed JWT access tokens with expiration
- User registration, login, and profile retrieval
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import logging
import os
import secrets
import sqlite3
import uuid
from typing import Optional

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt

from founderreach.config import settings
from founderreach.db import db

logger = logging.getLogger(__name__)

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "founderreach-saas-jwt-secret-key-prod-2026")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_DAYS = 7

security_scheme = HTTPBearer(auto_error=False)


def _init_auth_tables():
    """Ensure users table exists in the database."""
    with db.get_sqlite_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            name TEXT NOT NULL,
            active_domain TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        conn.commit()


_init_auth_tables()


def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    """Hash password using PBKDF2-HMAC-SHA256 with a cryptographically secure salt."""
    if not salt:
        salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
    return dk.hex(), salt


def verify_password(plain_password: str, password_hash: str, salt: str) -> bool:
    """Verify plain password against stored PBKDF2 hash."""
    computed_hash, _ = hash_password(plain_password, salt)
    return secrets.compare_digest(computed_hash, password_hash)


def create_access_token(user_id: str, email: str, name: str) -> str:
    """Generate signed JWT access token for authenticated session."""
    expire = datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRATION_DAYS)
    payload = {
        "sub": user_id,
        "email": email,
        "name": name,
        "exp": expire,
        "iat": datetime.now(timezone.utc)
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Validate and decode JWT access token."""
    try:
        return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session token has expired. Please log in again."
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token."
        )


def register_user(email: str, password: str, name: str, active_domain: str = "") -> dict:
    """Register a new user account."""
    clean_email = email.strip().lower()
    if len(password) < 6:
        raise ValueError("Password must be at least 6 characters long.")
    if not name.strip():
        name = clean_email.split("@")[0].capitalize()

    pwd_hash, salt = hash_password(password)
    user_id = str(uuid.uuid4())

    with db.get_sqlite_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = ?", (clean_email,))
        if cursor.fetchone():
            raise ValueError(f"An account with email '{clean_email}' already exists.")

        cursor.execute("""
        INSERT INTO users (id, email, password_hash, salt, name, active_domain)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, clean_email, pwd_hash, salt, name.strip(), active_domain.strip()))
        conn.commit()

    token = create_access_token(user_id, clean_email, name)
    return {
        "user": {
            "id": user_id,
            "email": clean_email,
            "name": name.strip(),
            "activeDomain": active_domain.strip() or "www.scheduleflow.io"
        },
        "token": token
    }


def authenticate_user(email: str, password: str) -> dict:
    """Authenticate existing user credentials."""
    clean_email = email.strip().lower()
    with db.get_sqlite_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, email, password_hash, salt, name, active_domain FROM users WHERE email = ?", (clean_email,))
        row = cursor.fetchone()
        if not row:
            raise ValueError("Invalid email or password.")

        user_id, db_email, pwd_hash, salt, name, active_domain = (
            row["id"], row["email"], row["password_hash"], row["salt"], row["name"], row["active_domain"]
        )

        if not verify_password(password, pwd_hash, salt):
            raise ValueError("Invalid email or password.")

    token = create_access_token(user_id, db_email, name)
    return {
        "user": {
            "id": user_id,
            "email": db_email,
            "name": name,
            "activeDomain": active_domain or "www.scheduleflow.io"
        },
        "token": token
    }


def get_user_by_id(user_id: str) -> Optional[dict]:
    """Retrieve user dictionary by primary key ID."""
    with db.get_sqlite_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, email, name, active_domain, created_at FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "email": row["email"],
            "name": row["name"],
            "activeDomain": row["active_domain"] or "www.scheduleflow.io",
            "createdAt": row["created_at"]
        }


def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Security(security_scheme)) -> dict:
    """FastAPI dependency to extract current user from Authorization: Bearer <token>."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required in Authorization header."
        )

    payload = decode_access_token(credentials.credentials)
    user = get_user_by_id(payload.get("sub"))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User belonging to this token no longer exists."
        )
    return user
