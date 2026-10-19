"""Sliding-window IP rate limiter for FounderReach AI API."""
from __future__ import annotations

from collections import defaultdict
import time
from threading import Lock
from typing import Dict, List
from fastapi import Request, HTTPException, status
from founderreach.config import settings

_rate_limit_lock = Lock()
_ip_request_history: Dict[str, List[float]] = defaultdict(list)


def check_rate_limit(request: Request, max_requests: int = 60, window_seconds: int = 60):
    """FastAPI dependency to enforce rate limits per client IP."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    # Respect X-Forwarded-For if deployed behind reverse proxy
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()

    now = time.time()
    cutoff = now - window_seconds

    with _rate_limit_lock:
        timestamps = _ip_request_history[client_ip]
        # Discard timestamps older than window
        _ip_request_history[client_ip] = [t for t in timestamps if t > cutoff]

        if len(_ip_request_history[client_ip]) >= max_requests:
            retry_after = int(window_seconds - (now - _ip_request_history[client_ip][0])) + 1
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded ({max_requests} req/min). Please try again in {retry_after} seconds.",
                headers={"Retry-After": str(retry_after)}
            )

        _ip_request_history[client_ip].append(now)


def rate_limit_audit(request: Request):
    """Specific rate limit for live domain audits (max 15/minute per IP)."""
    check_rate_limit(request, max_requests=15, window_seconds=60)


def rate_limit_auth(request: Request):
    """Specific rate limit for login/registration attempts (max 20/minute per IP)."""
    check_rate_limit(request, max_requests=20, window_seconds=60)
