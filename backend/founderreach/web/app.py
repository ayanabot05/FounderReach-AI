import logging
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel

from fastapi.middleware.cors import CORSMiddleware
from founderreach.config import settings
from founderreach.web.audit_service import perform_website_audit

logger = logging.getLogger(__name__)

FRONTEND_DIR = Path(__file__).resolve().parents[3] / "frontend"

app = FastAPI(
    title="FounderReach AI",
    description="Autonomous SEO, AEO & GEO Growth Agent",
    version=settings.VERSION
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
    feedback: str  # "relevant" or "irrelevant"
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


@app.get("/api/health")
def health():
    return {
        "status": "healthy",
        "service": "FounderReach AI Backend API",
        "version": settings.VERSION
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
            "audit": "POST /api/audit"
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

