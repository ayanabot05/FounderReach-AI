import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel

from fastapi.middleware.cors import CORSMiddleware
from founderreach.config import settings
from founderreach.web.audit_service import perform_website_audit
from founderreach.auth import (
    register_user,
    authenticate_user,
    get_current_user,
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

logger = logging.getLogger(__name__)

FRONTEND_DIR = Path(__file__).resolve().parents[3] / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start autonomous 6-hour background scheduler
    logger.info("Initializing FounderReach AI application...")
    start_background_scheduler()
    yield
    # Shutdown: Stop scheduler
    logger.info("Shutting down FounderReach AI scheduler...")
    stop_background_scheduler()


app = FastAPI(
    title="FounderReach AI",
    description="Autonomous SEO, AEO & GEO Growth Agent with Background Scheduler & Multi-Tenant Auth",
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
# AUDIT & DISCOVERY ENDPOINTS
# =========================================================================

class AuditRequest(BaseModel):
    url: str
    business_name: str = ""
    description: str = ""
    target_audience: str = ""
    pain_point: str = ""


@app.post("/api/audit")
def audit(req: AuditRequest):
    try:
        return perform_website_audit(
            url=req.url,
            business_name=req.business_name,
            description=req.description,
            target_audience=req.target_audience,
            pain_point=req.pain_point,
        )
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


@app.post("/api/auth/register")
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


@app.post("/api/auth/login")
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
        "auth": "sqlite_jwt"
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
            "reddit": "/api/reddit/status"
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
