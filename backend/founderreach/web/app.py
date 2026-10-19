import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Query, Depends, Request
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel

from fastapi.middleware.cors import CORSMiddleware
from founderreach.config import settings
from founderreach.db import db
from founderreach.web.audit_service import perform_website_audit
from founderreach.auth import (
    register_user,
    authenticate_user,
    get_current_user,
    require_admin_user,
    list_users_paginated,
    set_user_role,
    delete_user,
)
from founderreach.scheduler import (
    add_monitored_domain,
    remove_monitored_domain,
    list_monitored_domains,
    get_domain_history,
    scan_domain_now,
    start_background_scheduler,
    stop_background_scheduler,
)
from founderreach.connectors.reddit import RedditConnector, fetch_live_reddit_discussions
from founderreach.billing import (
    create_checkout_session,
    handle_stripe_webhook,
    get_revenue_metrics,
    PLANS
)
from founderreach.admin import (
    get_admin_dashboard_stats,
    get_admin_audits_paginated
)
from founderreach.rate_limit import rate_limit_audit, rate_limit_auth

logger = logging.getLogger(__name__)

FRONTEND_DIR = Path(__file__).resolve().parents[3] / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start autonomous 6-hour background scheduler
    logger.info("Initializing FounderReach AI application & scheduler...")
    start_background_scheduler()
    yield
    # Shutdown: Stop scheduler
    logger.info("Shutting down FounderReach AI scheduler...")
    stop_background_scheduler()


app = FastAPI(
    title="FounderReach AI",
    description="Autonomous SEO, AEO & GEO Growth Agent with Admin Console, Stripe Billing & Scheduler",
    version=settings.VERSION,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3005",
        "http://127.0.0.1:3005",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8004",
        "http://127.0.0.1:8004",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================================
# AUDIT & DISCOVERY ENDPOINTS (WITH CACHING & RATE LIMITING)
# =========================================================================

class AuditRequest(BaseModel):
    url: str
    business_name: str = ""
    description: str = ""
    target_audience: str = ""
    pain_point: str = ""
    refresh: bool = False


@app.post("/api/audit", dependencies=[Depends(rate_limit_audit)])
def audit(req: AuditRequest):
    clean_domain = req.url.strip().lower().replace("https://", "").replace("http://", "").rstrip("/")
    cache_key = f"audit:{clean_domain}"

    # Return cached snapshot if recent and refresh not requested (disabled in unit test runner)
    import os
    if not req.refresh and not os.getenv("PYTEST_CURRENT_TEST"):
        cached = db.get_cache(cache_key)
        if cached:
            try:
                data = json.loads(cached)
                data["_cached"] = True
                return data
            except Exception:
                pass

    try:
        result = perform_website_audit(
            url=req.url,
            business_name=req.business_name,
            description=req.description,
            target_audience=req.target_audience,
            pain_point=req.pain_point,
        )
        # Store in cache with 15-minute TTL
        db.set_cache(cache_key, json.dumps(result), ttl_seconds=settings.CACHE_TTL_SECONDS)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Audit failed unexpectedly")
        raise HTTPException(status_code=500, detail=f"Audit failed: {str(exc)}") from exc


class FeedbackRequest(BaseModel):
    id: str
    feedback: str
    notes: Optional[str] = None


@app.get("/api/budget")
def get_budget():
    raise HTTPException(status_code=503, detail="Legacy API disabled until tenant authorization is integrated")


@app.get("/api/opportunities")
def get_opportunities(
    product: str = "scheduleflow",
    min_score: Optional[int] = Query(None, ge=0, le=100),
    limit: int = Query(10, ge=1, le=50),
    refresh: bool = False,
    include_research: bool = False
):
    raise HTTPException(status_code=503, detail="Legacy API disabled until tenant authorization is integrated")


@app.post("/api/feedback")
def submit_feedback(req: FeedbackRequest):
    raise HTTPException(status_code=503, detail="Legacy API disabled until tenant authorization is integrated")


# =========================================================================
# P2: PRODUCTION USER AUTHENTICATION ENDPOINTS
# =========================================================================

class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str = ""
    active_domain: str = ""


class LoginRequest(BaseModel):
    email: str
    password: str


@app.post("/api/auth/register", dependencies=[Depends(rate_limit_auth)])
def register(req: RegisterRequest):
    try:
        return register_user(
            email=req.email,
            password=req.password,
            name=req.name,
            active_domain=req.active_domain
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Registration failed")
        raise HTTPException(status_code=500, detail=f"Registration error: {str(exc)}") from exc


@app.post("/api/auth/login", dependencies=[Depends(rate_limit_auth)])
def login(req: LoginRequest):
    try:
        return authenticate_user(
            email=req.email,
            password=req.password
        )
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Login failed")
        raise HTTPException(status_code=500, detail="Authentication error") from exc


@app.get("/api/auth/me")
def me(current_user: dict = Depends(get_current_user)):
    return {"user": current_user}


# =========================================================================
# PAYMENTS & STRIPE CHECKOUT ENDPOINTS
# =========================================================================

class CheckoutRequest(BaseModel):
    plan_id: str
    domain: str
    user_email: str
    user_id: Optional[str] = None
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


@app.post("/api/billing/create-checkout-session")
def create_checkout(req: CheckoutRequest):
    try:
        return create_checkout_session(
            plan_id=req.plan_id,
            domain=req.domain,
            user_email=req.user_email,
            user_id=req.user_id,
            success_url=req.success_url,
            cancel_url=req.cancel_url
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Checkout session creation failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/billing/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    try:
        return handle_stripe_webhook(payload, sig_header)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Stripe webhook processing error")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# =========================================================================
# P3: AUTONOMOUS BACKGROUND SCHEDULER & MONITORING ENDPOINTS
# =========================================================================

class MonitoredDomainRequest(BaseModel):
    domain: str
    frequency_hours: int = 6


class ScanNowRequest(BaseModel):
    domain: str


@app.get("/api/monitor/domains")
def get_monitored_domains():
    try:
        return {"domains": list_monitored_domains()}
    except Exception as exc:
        logger.exception("Failed to retrieve monitored domains")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/monitor/domains")
def register_domain_for_monitoring(req: MonitoredDomainRequest):
    try:
        return add_monitored_domain(domain=req.domain, frequency_hours=req.frequency_hours)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to monitor domain")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.delete("/api/monitor/domains/{domain}")
def delete_monitored_domain(domain: str):
    success = remove_monitored_domain(domain)
    if not success:
        raise HTTPException(status_code=404, detail=f"Domain '{domain}' was not found in monitoring list.")
    return {"deleted": True, "domain": domain}


@app.post("/api/monitor/scan-now")
def trigger_immediate_scan(req: ScanNowRequest):
    try:
        return scan_domain_now(req.domain)
    except Exception as exc:
        logger.exception("Immediate scan failed")
        raise HTTPException(status_code=500, detail=f"Scan error: {str(exc)}") from exc


@app.get("/api/monitor/history/{domain}")
def get_history(domain: str, limit: int = Query(10, ge=1, le=50)):
    return {
        "domain": domain,
        "history": get_domain_history(domain, limit=limit)
    }


# =========================================================================
# SUPER ADMIN BACK-OFFICE PORTAL ENDPOINTS (RBAC: ADMIN REQUIRED)
# =========================================================================

class UserRoleRequest(BaseModel):
    role: str  # 'admin' or 'user'


@app.get("/api/admin/stats")
def admin_stats(admin_user: dict = Depends(require_admin_user)):
    """Executive stats & telemetry for the Super Admin overview."""
    return get_admin_dashboard_stats()


@app.get("/api/admin/users")
def admin_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    admin_user: dict = Depends(require_admin_user)
):
    """Paginated user management with search."""
    search_str = search if isinstance(search, str) else None
    return list_users_paginated(page=page, limit=limit, search=search_str)


@app.post("/api/admin/users/{user_id}/role")
def admin_set_user_role(user_id: str, req: UserRoleRequest, admin_user: dict = Depends(require_admin_user)):
    """Update user role (user <-> admin)."""
    try:
        success = set_user_role(user_id, req.role)
        if not success:
            raise HTTPException(status_code=404, detail="User not found")
        return {"updated": True, "userId": user_id, "newRole": req.role}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.delete("/api/admin/users/{user_id}")
def admin_delete_user(user_id: str, admin_user: dict = Depends(require_admin_user)):
    """Delete a user account."""
    if user_id == admin_user.get("id"):
        raise HTTPException(status_code=400, detail="Cannot delete your own active admin account.")
    success = delete_user(user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"deleted": True, "userId": user_id}


@app.get("/api/admin/payments")
def admin_payments(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    admin_user: dict = Depends(require_admin_user)
):
    """Paginated payments and transactions log."""
    status_str = status if isinstance(status, str) else None
    return db.get_payments(page=page, limit=limit, status=status_str)


@app.get("/api/admin/audits")
def admin_audits(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    domain: Optional[str] = Query(None),
    admin_user: dict = Depends(require_admin_user)
):
    """Paginated real-time audits stream across all targets."""
    domain_str = domain if isinstance(domain, str) else None
    return get_admin_audits_paginated(page=page, limit=limit, domain=domain_str)


# =========================================================================
# P4: REDDIT API CONNECTOR ENDPOINTS
# =========================================================================

@app.get("/api/reddit/status")
def reddit_status():
    connector = RedditConnector()
    return {
        "enabled": connector.is_enabled(),
        "client_id_configured": bool(settings.REDDIT_CLIENT_ID),
        "user_agent": settings.REDDIT_USER_AGENT,
        "policy": "Read-only commercial discussion discovery. Suggestion only (zero auto-posting)."
    }


@app.get("/api/reddit/feed")
def reddit_feed(query: str = Query("SaaS", min_length=2), limit: int = Query(10, ge=1, le=50)):
    return {
        "query": query,
        "signals": fetch_live_reddit_discussions(query=query, limit=limit)
    }


# =========================================================================
# SYSTEM HEALTH & STATIC ASSETS
# =========================================================================

@app.get("/api/health")
def health():
    return {
        "status": "healthy",
        "service": "FounderReach AI Backend API",
        "version": settings.VERSION,
        "scheduler": "active",
        "database": "supabase" if db.is_using_supabase() else "sqlite",
        "stripe": "configured" if settings.STRIPE_SECRET_KEY else "sandbox"
    }


DIST_DIR = FRONTEND_DIR / "dist"
if (DIST_DIR / "assets").exists():
    from fastapi.staticfiles import StaticFiles
    app.mount("/assets", StaticFiles(directory=DIST_DIR / "assets"), name="assets")


@app.get("/", response_class=FileResponse)
def index():
    if (DIST_DIR / "index.html").exists():
        return FileResponse(DIST_DIR / "index.html")
    return {
        "name": "FounderReach AI API",
        "version": settings.VERSION,
        "docs": "/docs",
        "endpoints": {
            "health": "/api/health",
            "audit": "POST /api/audit",
            "auth": "/api/auth/login, /api/auth/register",
            "monitor": "/api/monitor/domains",
            "admin": "/api/admin/stats, /api/admin/users, /api/admin/payments"
        }
    }


@app.get("/llms.txt", response_class=FileResponse)
def llms_txt():
    for candidate in [DIST_DIR / "llms.txt", FRONTEND_DIR / "public" / "llms.txt"]:
        if candidate.exists():
            return FileResponse(candidate, media_type="text/plain")
    raise HTTPException(status_code=404, detail="llms.txt not found")


@app.get("/robots.txt", response_class=FileResponse)
def robots_txt():
    for candidate in [DIST_DIR / "robots.txt", FRONTEND_DIR / "public" / "robots.txt"]:
        if candidate.exists():
            return FileResponse(candidate, media_type="text/plain")
    raise HTTPException(status_code=404, detail="robots.txt not found")


@app.get("/sitemap.xml", response_class=FileResponse)
def sitemap_xml():
    for candidate in [DIST_DIR / "sitemap.xml", FRONTEND_DIR / "public" / "sitemap.xml"]:
        if candidate.exists():
            return FileResponse(candidate, media_type="application/xml")
    raise HTTPException(status_code=404, detail="sitemap.xml not found")
