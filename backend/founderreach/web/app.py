import logging
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel

from founderreach.config import settings

logger = logging.getLogger(__name__)

FRONTEND_DIR = Path(__file__).resolve().parents[3] / "frontend"

app = FastAPI(
    title="FounderReach AI",
    description="Verified Customer Opportunity Finder",
    version=settings.VERSION
)


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


@app.get("/", response_class=HTMLResponse)
def index():
    return HTMLResponse(content=(FRONTEND_DIR / "index.html").read_text(encoding="utf-8"))


@app.get("/styles.css")
def styles():
    return FileResponse(FRONTEND_DIR / "styles.css", media_type="text/css")


@app.get("/app.js")
def script():
    return FileResponse(FRONTEND_DIR / "app.js", media_type="application/javascript")
