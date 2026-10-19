"""Production User Authentication & Access Control for FounderReach AI

Provides multi-tenant user authentication backed by SQLite / Supabase:
- Cryptographic password hashing (PBKDF2-HMAC-SHA256 with random salt)
- Signed JWT access tokens with role claims ('user' vs 'admin')
- Super Admin auto-bootstrap from environment variables (ADMIN_EMAIL, ADMIN_PASSWORD)
- Pagination, search, and role management for the admin back-office
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import logging
import os
import secrets
import sqlite3
import uuid
from typing import Optional, Dict, Any, List

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt

from founderreach.config import settings
from founderreach.db import db

logger = logging.getLogger(__name__)

security_scheme = HTTPBearer(auto_error=False)


def _init_auth_tables():
    """Ensure users table exists in the database and includes role column."""
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
            role TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        # Ensure role column exists if migrated
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
        except Exception:
            pass
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


def create_access_token(user_id: str, email: str, name: str, role: str = "user") -> str:
    """Generate signed JWT access token for authenticated session."""
    expire = datetime.now(timezone.utc) + timedelta(days=settings.JWT_EXPIRATION_DAYS)
    payload = {
        "sub": user_id,
        "email": email,
        "name": name,
        "role": role,
        "exp": expire,
        "iat": datetime.now(timezone.utc)
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Validate and decode JWT access token."""
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
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


def register_user(email: str, password: str, name: str, active_domain: str = "", role: str = "user") -> dict:
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
        INSERT INTO users (id, email, password_hash, salt, name, active_domain, role)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, clean_email, pwd_hash, salt, name.strip(), active_domain.strip(), role))
        conn.commit()

    token = create_access_token(user_id, clean_email, name, role)
    return {
        "user": {
            "id": user_id,
            "email": clean_email,
            "name": name.strip(),
            "role": role,
            "activeDomain": active_domain.strip() or "www.scheduleflow.io"
        },
        "token": token
    }


def authenticate_user(email: str, password: str) -> dict:
    """Authenticate existing user credentials."""
    clean_email = email.strip().lower()
    with db.get_sqlite_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, email, password_hash, salt, name, active_domain, role FROM users WHERE email = ?", (clean_email,))
        row = cursor.fetchone()
        if not row:
            raise ValueError("Invalid email or password.")

        user_id, db_email, pwd_hash, salt, name, active_domain, role = (
            row["id"], row["email"], row["password_hash"], row["salt"], row["name"], row["active_domain"], row["role"] or "user"
        )

        if not verify_password(password, pwd_hash, salt):
            raise ValueError("Invalid email or password.")

    token = create_access_token(user_id, db_email, name, role)
    return {
        "user": {
            "id": user_id,
            "email": db_email,
            "name": name,
            "role": role,
            "activeDomain": active_domain or "www.scheduleflow.io"
        },
        "token": token
    }


def get_user_by_id(user_id: str) -> Optional[dict]:
    """Retrieve user dictionary by primary key ID."""
    with db.get_sqlite_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, email, name, active_domain, role, created_at FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "email": row["email"],
            "name": row["name"],
            "role": row["role"] or "user",
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


def require_admin_user(current_user: dict = Depends(get_current_user)) -> dict:
    """FastAPI security dependency: requires caller to possess admin role."""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super Admin authorization required for this resource."
        )
    return current_user


def bootstrap_admin_user():
    """Ensure the Super Admin defined in environment variables exists with 'admin' role."""
    admin_email = settings.ADMIN_EMAIL.strip().lower()
    admin_password = settings.ADMIN_PASSWORD
    if not admin_email or not admin_password:
        return

    pwd_hash, salt = hash_password(admin_password)
    with db.get_sqlite_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = ?", (admin_email,))
        row = cursor.fetchone()
        if row:
            # Update password and guarantee admin role
            cursor.execute("""
            UPDATE users SET password_hash = ?, salt = ?, role = 'admin' WHERE email = ?
            """, (pwd_hash, salt, admin_email))
        else:
            admin_id = str(uuid.uuid4())
            cursor.execute("""
            INSERT INTO users (id, email, password_hash, salt, name, active_domain, role)
            VALUES (?, ?, ?, ?, 'Super Admin', 'founderreach.ai', 'admin')
            """, (admin_id, admin_email, pwd_hash, salt))
        conn.commit()
    logger.info(f"Super Admin verified for email: {admin_email}")


# Auto-bootstrap admin user on import
bootstrap_admin_user()


# =========================================================================
# ADMIN USER MANAGEMENT FUNCTIONS (PAGINATED)
# =========================================================================

def list_users_paginated(page: int = 1, limit: int = 20, search: Optional[str] = None) -> Dict[str, Any]:
    offset = (page - 1) * limit
    with db.get_sqlite_connection() as conn:
        cursor = conn.cursor()
        if search and search.strip():
            term = f"%{search.strip().lower()}%"
            cursor.execute("SELECT COUNT(*) as cnt FROM users WHERE LOWER(email) LIKE ? OR LOWER(name) LIKE ?", (term, term))
            total = cursor.fetchone()["cnt"]
            cursor.execute("""
            SELECT id, email, name, active_domain, role, created_at FROM users
            WHERE LOWER(email) LIKE ? OR LOWER(name) LIKE ?
            ORDER BY created_at DESC LIMIT ? OFFSET ?
            """, (term, term, limit, offset))
        else:
            cursor.execute("SELECT COUNT(*) as cnt FROM users")
            total = cursor.fetchone()["cnt"]
            cursor.execute("""
            SELECT id, email, name, active_domain, role, created_at FROM users
            ORDER BY created_at DESC LIMIT ? OFFSET ?
            """, (limit, offset))

        rows = cursor.fetchall()
        return {
            "items": [dict(r) for r in rows],
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit if total > 0 else 1
        }


def set_user_role(user_id: str, role: str) -> bool:
    if role not in ("admin", "user"):
        raise ValueError("Role must be 'admin' or 'user'")
    with db.get_sqlite_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
        conn.commit()
        return cursor.rowcount > 0


def delete_user(user_id: str) -> bool:
    with db.get_sqlite_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        return cursor.rowcount > 0
