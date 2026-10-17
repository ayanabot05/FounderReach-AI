"""Local account-scoped FounderReach self-service prototype."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel, Field

from founderreach.models import ProductProfile
from founderreach.recommendations import recommend
from founderreach.self_service_store import SelfServiceStore
from founderreach.website import WebsiteFetcher, WebsiteFetchError, UnsafeWebsiteError, propose_profile

ROOT = Path(__file__).resolve().parents[2]
WEB = Path(__file__).resolve().parent


class Credentials(BaseModel):
    email: str
    password: str


class NewBusiness(BaseModel):
    website_url: str


class ProfileEdit(BaseModel):
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    target_audiences: list[str] = Field(default_factory=list)
    pain_points: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    negative_keywords: list[str] = Field(default_factory=list)
    customer_fit_signals: list[str] = Field(default_factory=list)
    supported_languages: list[str] = Field(default_factory=list)
    target_markets: list[str] = Field(default_factory=list)
    acquisition_objectives: list[str] = Field(default_factory=list)
    competitor_names: list[str] = Field(default_factory=list)
    allowed_acquisition_channels: list[str] = Field(default_factory=lambda: ["demand_evidence", "owned_channel"])


class ApprovalRequest(BaseModel):
    version_hash: str


class OutcomeInput(BaseModel):
    qualified_inquiries: int | None = Field(default=None, ge=0)
    customers_acquired: int | None = Field(default=None, ge=0)
    attributable_visits: int | None = Field(default=None, ge=0)
    founder_minutes: int | None = Field(default=None, ge=0)
    direct_cost_inr: float | None = Field(default=None, ge=0)
    notes: str = Field(default="", max_length=2000)


def create_app(db_path: Path | None = None, fetcher=None, recommender=None):
    store = SelfServiceStore(db_path or ROOT / "data" / "self_service.db")
    fetcher = fetcher or WebsiteFetcher()
    recommender = recommender or recommend
    app = FastAPI(title="FounderReach AI — local self-service")
    app.state.store = store

    def current(request: Request):
        session = store.session(request.cookies.get("fr_session", ""))
        if not session:
            raise HTTPException(401, "Log in to continue")
        return session

    def changing(request: Request, session=Depends(current), x_csrf_token: str = Header(default="")):
        if not x_csrf_token or x_csrf_token != session["csrf"]:
            raise HTTPException(403, "Invalid session request token")
        return session

    def own_business(session, business_id):
        business = store.business(session["account_id"], business_id)
        if not business:
            raise HTTPException(404, "Business not found")
        return business

    @app.get("/", response_class=HTMLResponse)
    def home():
        return HTMLResponse((WEB / "self_service.html").read_text(encoding="utf-8"),
                            headers={"Cache-Control": "no-store", "Content-Security-Policy":
                                     "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'self'"})

    @app.get("/app.js")
    def javascript():
        return FileResponse(WEB / "self_service.js", media_type="application/javascript",
                            headers={"Cache-Control": "no-store"})

    @app.get("/app.css")
    def css():
        return FileResponse(WEB / "self_service.css", media_type="text/css",
                            headers={"Cache-Control": "no-store"})

    @app.post("/api/register")
    def register(data: Credentials):
        try:
            store.register(data.email, data.password)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        return {"status": "registered"}

    @app.post("/api/login")
    def login(data: Credentials, request: Request, response: Response):
        try:
            token, csrf = store.login(data.email, data.password)
        except ValueError as exc:
            raise HTTPException(401, str(exc)) from exc
        response.set_cookie("fr_session", token, httponly=True, secure=request.url.scheme == "https",
                            samesite="strict", max_age=12 * 3600, path="/")
        return {"status": "logged_in", "csrf": csrf}

    @app.get("/api/me")
    def me(session=Depends(current)):
        return {"email": session["email"], "csrf": session["csrf"]}

    @app.post("/api/logout")
    def logout(request: Request, response: Response, session=Depends(changing)):
        store.logout(request.cookies.get("fr_session", ""))
        response.delete_cookie("fr_session", path="/")
        return {"status": "logged_out"}

    @app.get("/api/businesses")
    def businesses(session=Depends(current)):
        return store.list_businesses(session["account_id"])

    @app.post("/api/businesses")
    def add_business(data: NewBusiness, session=Depends(changing)):
        try:
            snapshot = fetcher.fetch(data.website_url.strip())
        except UnsafeWebsiteError as exc:
            raise HTTPException(422, str(exc)) from exc
        except WebsiteFetchError as exc:
            # Keep the manual-edit path open when the public site blocks access.
            snapshot = {"url": data.website_url.strip(), "title": "", "description": "", "keywords": "",
                        "headings": [], "text_excerpt": "", "fetch_error": str(exc)}
        proposal = propose_profile(snapshot)
        business_id = store.add_business(session["account_id"], snapshot, proposal)
        return store.business(session["account_id"], business_id)

    @app.get("/api/businesses/{business_id}")
    def business(business_id: int, session=Depends(current)):
        return own_business(session, business_id)

    @app.put("/api/businesses/{business_id}/profile")
    def confirm_profile(business_id: int, data: ProfileEdit, session=Depends(changing)):
        business = own_business(session, business_id)
        fields = data.model_dump()
        fields.update({"identifier": str(business_id), "website": business["website"], "confirmed": True})
        try:
            profile = ProductProfile.model_validate(fields)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        return store.confirm_profile(session["account_id"], business_id, profile.model_dump(mode="json"))

    @app.post("/api/businesses/{business_id}/recommendations")
    def recommendations(business_id: int, session=Depends(changing)):
        business = own_business(session, business_id)
        if not business["confirmed"]:
            raise HTTPException(409, "Review and confirm this business profile first")
        profile = ProductProfile.model_validate(business["profile"])
        payload = recommender(profile, business["snapshot"])
        version_hash = hashlib.sha256(json.dumps({"profile_version": business["version"], "payload": payload},
                                                 sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        prior = next((action for action in store.actions(session["account_id"], business_id)
                      if action["version_hash"] == version_hash), None)
        if prior:
            return prior
        action_id = store.add_action(session["account_id"], business_id, business["version"], payload, version_hash)
        return store.action(session["account_id"], business_id, action_id)

    @app.get("/api/businesses/{business_id}/actions")
    def actions(business_id: int, session=Depends(current)):
        own_business(session, business_id)
        return store.actions(session["account_id"], business_id)

    @app.post("/api/businesses/{business_id}/actions/{action_id}/approve")
    def approve(business_id: int, action_id: int, data: ApprovalRequest, session=Depends(changing)):
        raise HTTPException(503, "Approval unavailable until the signed exact-action gate is integrated")

    @app.post("/api/businesses/{business_id}/actions/{action_id}/outcome")
    def outcome(business_id: int, action_id: int, data: OutcomeInput, session=Depends(changing)):
        raise HTTPException(503, "Outcome entry unavailable until signed approval is integrated")

    return app


# Deliberately no module-level ASGI app: this local prototype is not deployable.
