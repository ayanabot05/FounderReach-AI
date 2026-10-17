import logging
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from founderreach.config import settings
from founderreach.models import CustomerOpportunity, ProductProfile
from founderreach.engine import engine
from founderreach.profiles import load_profile
from founderreach.db import db
from founderreach.ai.cost_tracker import cost_tracker

logger = logging.getLogger(__name__)

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
    product: str = "ayana",
    min_score: Optional[int] = Query(None, ge=0, le=100),
    limit: int = Query(10, ge=1, le=50),
    refresh: bool = False,
    include_research: bool = False
):
    raise HTTPException(status_code=503, detail="Legacy API disabled until tenant authorization is integrated")
    try:
        profile = load_profile(product.lower())
        min_score = profile.minimum_score if min_score is None else min_score
        if refresh:
            opps = engine.find_opportunities(product=profile, min_score=min_score, limit=limit, persist=False,
                                             actionable_only=not include_research)
        else:
            opps = db.get_opportunities(product_name=profile.name, min_score=float(min_score))[:limit]
            if not opps:
                opps = engine.find_opportunities(product=profile, min_score=min_score, limit=limit, persist=False,
                                                 actionable_only=not include_research)
        # Database rows may be historical or from the pre-audit schema.
        from datetime import datetime
        safe = []
        for o in opps:
            try:
                age = (datetime.utcnow().date() - datetime.fromisoformat(o.discussion_date).date()).days if o.discussion_date else None
                fresh = age is not None and 0 <= age <= profile.reply_max_age_days
            except ValueError:
                fresh = False
            actionable = (o.classification == "ACTIONABLE_OPPORTUNITY" and o.source_status == "SOURCE_VERIFIED"
                          and o.verification.verified and o.intent_status == "CUSTOMER_INTENT_VERIFIED" and fresh)
            research = (include_research and o.classification == "RESEARCH_INSIGHT" and
                        o.source_status == "SOURCE_VERIFIED" and o.verification.verified)
            if actionable or research:
                safe.append(o.model_dump(mode="json"))
        return safe[:limit]
    except Exception as e:
        logger.error(f"Error fetching opportunities: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/feedback")
def submit_feedback(req: FeedbackRequest):
    raise HTTPException(status_code=503, detail="Legacy API disabled until tenant authorization is integrated")
    if req.feedback not in ("relevant", "irrelevant"):
        raise HTTPException(status_code=400, detail="Feedback must be 'relevant' or 'irrelevant'")
    success = db.update_feedback(req.id, req.feedback, req.notes)
    if not success:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return {"status": "success", "id": req.id, "feedback": req.feedback}

@app.get("/", response_class=HTMLResponse)
def index():
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>FounderReach AI — Customer Opportunity Finder</title>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #0b0f19;
      --card-bg: #111827;
      --card-border: #1f2937;
      --accent: #2563eb;
      --accent-glow: rgba(37, 99, 235, 0.2);
      --success: #10b981;
      --warning: #f59e0b;
      --text: #f9fafb;
      --text-muted: #9ca3af;
      --font: 'Plus Jakarta Sans', sans-serif;
      --mono: 'JetBrains Mono', monospace;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background-color: var(--bg);
      color: var(--text);
      font-family: var(--font);
      line-height: 1.6;
      padding: 24px;
      min-height: 100vh;
    }
    .container { max-width: 1100px; margin: 0 auto; }
    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 24px;
      border-bottom: 1px solid var(--card-border);
      margin-bottom: 28px;
    }
    .brand h1 { font-size: 26px; font-weight: 800; letter-spacing: -0.5px; }
    .brand h1 span { color: #60a5fa; }
    .tagline { color: var(--text-muted); font-size: 14px; margin-top: 4px; }
    .budget-pill {
      background: #0f172a;
      border: 1px solid #1e293b;
      border-radius: 9999px;
      padding: 8px 16px;
      display: flex;
      align-items: center;
      gap: 12px;
      font-size: 13px;
    }
    .status-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--success); }
    .controls {
      display: flex;
      gap: 16px;
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      padding: 18px 24px;
      border-radius: 12px;
      margin-bottom: 28px;
      align-items: center;
      flex-wrap: wrap;
    }
    .control-group { display: flex; flex-direction: column; gap: 6px; }
    .control-group label { font-size: 12px; font-weight: 600; text-transform: uppercase; color: var(--text-muted); letter-spacing: 0.5px; }
    .control-group input, .control-group select {
      background: #1e293b;
      border: 1px solid #334155;
      color: var(--text);
      padding: 8px 14px;
      border-radius: 8px;
      font-family: var(--font);
      font-size: 14px;
    }
    button.btn-primary {
      background: var(--accent);
      color: white;
      border: none;
      padding: 10px 20px;
      border-radius: 8px;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 8px;
      transition: all 0.2s;
    }
    button.btn-primary:hover { background: #1d4ed8; box-shadow: 0 0 15px var(--accent-glow); }
    .opp-list { display: flex; flex-direction: column; gap: 20px; }
    .opp-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 14px;
      padding: 24px;
      transition: border-color 0.2s;
    }
    .opp-card:hover { border-color: #374151; }
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 14px;
    }
    .badge-group { display: flex; gap: 8px; align-items: center; }
    .score-badge {
      background: rgba(16, 185, 129, 0.15);
      color: #34d399;
      border: 1px solid rgba(16, 185, 129, 0.3);
      padding: 4px 10px;
      border-radius: 9999px;
      font-weight: 700;
      font-size: 13px;
    }
    .verified-badge {
      background: rgba(59, 130, 246, 0.15);
      color: #60a5fa;
      border: 1px solid rgba(59, 130, 246, 0.3);
      padding: 4px 10px;
      border-radius: 9999px;
      font-size: 12px;
      font-weight: 600;
    }
    .meta-text { font-size: 13px; color: var(--text-muted); }
    .problem-box {
      margin-bottom: 14px;
      font-size: 16px;
      font-weight: 600;
      color: #f3f4f6;
    }
    .relevance-box {
      font-size: 14px;
      color: #93c5fd;
      background: rgba(30, 58, 138, 0.2);
      border-left: 3px solid #3b82f6;
      padding: 8px 14px;
      border-radius: 0 8px 8px 0;
      margin-bottom: 16px;
    }
    .evidence-quote {
      background: #0f172a;
      border: 1px solid #1e293b;
      padding: 14px;
      border-radius: 8px;
      font-family: var(--mono);
      font-size: 13px;
      color: #cbd5e1;
      margin-bottom: 18px;
      white-space: pre-wrap;
    }
    .response-section {
      background: #182234;
      border: 1px solid #2d3e58;
      border-radius: 10px;
      padding: 16px;
      margin-bottom: 16px;
    }
    .response-title {
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: #fbbf24;
      margin-bottom: 8px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .response-text {
      font-size: 14px;
      color: #e2e8f0;
      white-space: pre-wrap;
      line-height: 1.5;
    }
    .card-footer {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-top: 14px;
      border-top: 1px solid var(--card-border);
    }
    .copy-btn {
      background: #334155;
      color: white;
      border: none;
      padding: 6px 12px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
    }
    .copy-btn:hover { background: #475569; }
    .feedback-group { display: flex; gap: 8px; align-items: center; }
    .btn-feedback {
      background: transparent;
      border: 1px solid #374151;
      color: var(--text-muted);
      padding: 6px 12px;
      border-radius: 6px;
      font-size: 12px;
      cursor: pointer;
      transition: all 0.2s;
    }
    .btn-feedback.active-relevant { background: rgba(16, 185, 129, 0.2); border-color: #10b981; color: #34d399; }
    .btn-feedback.active-irrelevant { background: rgba(239, 68, 68, 0.2); border-color: #ef4444; color: #f87171; }
    .btn-feedback:hover { border-color: #4b5563; }
    .link-original { color: #60a5fa; text-decoration: none; font-size: 13px; font-weight: 500; }
    .link-original:hover { text-decoration: underline; }
    .empty-state { text-align: center; padding: 60px 20px; color: var(--text-muted); }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="brand">
        <h1>FounderReach <span>AI</span></h1>
        <div class="tagline">"Find people who need your product before you spend money on marketing."</div>
      </div>
      <div class="budget-pill" id="budget-pill">
        <div class="status-dot"></div>
        <span>Budget: <strong id="spent-val">INR 0.00</strong> / INR 600</span>
      </div>
    </header>

    <div class="controls">
      <div class="control-group">
        <label>Product Focus</label>
        <select id="product-select">
          <option value="ayana" data-threshold="75" selected>AYANA (Parent Care)</option>
          <option value="scheduleflow" data-threshold="70">ScheduleFlow (Sample Scheduling SaaS)</option>
        </select>
      </div>
      <div class="control-group">
        <label>Minimum Relevance Score</label>
        <input type="number" id="min-score" value="75" min="0" max="100" style="width: 80px;">
      </div>
      <div class="control-group" style="align-self: flex-end;">
        <button class="btn-primary" onclick="loadOpportunities(true)">
          🔄 Discover & Verify Opportunities
        </button>
      </div>
    </div>

    <div id="opps-container" class="opp-list">
      <div class="empty-state">Loading verified opportunities...</div>
    </div>
  </div>

  <script>
    async function updateBudget() {
      try {
        const res = await fetch('/api/budget');
        const data = await res.json();
        document.getElementById('spent-val').textContent = 'INR ' + data.spent_inr.toFixed(2);
      } catch (e) {
        console.error(e);
      }
    }

    async function loadOpportunities(refresh = false) {
      const container = document.getElementById('opps-container');
      container.innerHTML = '<div class="empty-state">Searching and verifying live discussions...</div>';
      const score = document.getElementById('min-score').value || 75;
      try {
        const product = document.querySelector('#product-select').value;
        const res = await fetch(`/api/opportunities?product=${encodeURIComponent(product)}&min_score=${score}&refresh=${refresh}&include_research=true`);
        const opps = await res.json();
        if (!opps || opps.length === 0) {
          container.innerHTML = '<div class="empty-state">No opportunities found meeting score threshold ≥ ' + score + '.</div>';
          return;
        }
        renderOpportunities(opps);
        updateBudget();
      } catch (e) {
        container.innerHTML = '<div class="empty-state" style="color:#ef4444;">Error loading opportunities: ' + e.message + '</div>';
      }
    }

    function renderOpportunities(opps) {
      const container = document.getElementById('opps-container');
      container.innerHTML = '';
      opps.forEach(o => {
        const card = document.createElement('div');
        card.className = 'opp-card';
        const dateStr = o.discussion_date || 'Date unknown';
        const authorStr = o.author ? `@${escapeHtml(o.author)}` : 'Anonymous';
        
        card.innerHTML = `
          <div class="card-header">
            <div class="badge-group">
              <span class="score-badge">${o.score.total_score.toFixed(1)} / 100</span>
              <span class="verified-badge">✔ Verified ${o.platform}</span>
            </div>
            <div class="meta-text">${dateStr} • ${authorStr}</div>
          </div>
          <div class="problem-box">${escapeHtml(o.customer_problem)}</div>
          <div class="relevance-box"><strong>Route:</strong> ${escapeHtml((o.signal_routes || []).join(', ') || 'Historical record: route pending review')} — ${escapeHtml(o.classification)}</div>
          <div class="relevance-box"><strong>Relevance:</strong> ${escapeHtml(o.why_relevant)}</div>
          <div class="evidence-quote"><strong>Evidence Excerpt:</strong>\\n"${escapeHtml(o.evidence_excerpt)}"</div>
          ${o.classification === 'ACTIONABLE_OPPORTUNITY' && o.suggested_response ? `<div class="response-section">
            <div class="response-title">
              <span>Suggested Founder Response (Non-Spam, Value-First)</span>
              <span>Review platform rules and approve manually before outreach</span>
            </div>
            <div class="response-text">${escapeHtml(o.suggested_response)}</div>
          </div>` : ''}
          <div class="card-footer">
            <a class="link-original" href="${escapeHtml(o.original_url)}" target="_blank" rel="noopener">Open Original Discussion ↗</a>
            <div class="feedback-group">
              <span style="font-size:12px; color:var(--text-muted)">Feedback:</span>
              <button class="btn-feedback ${o.feedback === 'relevant' ? 'active-relevant' : ''}" onclick="submitFeedback('${o.id}', 'relevant', this)">👍 Relevant</button>
              <button class="btn-feedback ${o.feedback === 'irrelevant' ? 'active-irrelevant' : ''}" onclick="submitFeedback('${o.id}', 'irrelevant', this)">👎 Irrelevant</button>
            </div>
          </div>
        `;
        container.appendChild(card);
      });
    }

    async function submitFeedback(id, feedback, btn) {
      try {
        const res = await fetch('/api/feedback', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({id, feedback})
        });
        if (res.ok) {
          const parent = btn.parentElement;
          parent.querySelectorAll('.btn-feedback').forEach(b => {
            b.classList.remove('active-relevant', 'active-irrelevant');
          });
          btn.classList.add(feedback === 'relevant' ? 'active-relevant' : 'active-irrelevant');
        }
      } catch (e) {
        alert('Feedback error: ' + e.message);
      }
    }

    function copyText(btn, text) {
      navigator.clipboard.writeText(text).then(() => {
        const orig = btn.textContent;
        btn.textContent = '✔ Copied!';
        setTimeout(() => { btn.textContent = orig; }, 2000);
      });
    }

    function escapeHtml(text) {
      if (!text) return '';
      return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    function escapeJs(text) {
      if (!text) return '';
      return text.replace(/`/g, '\\`').replace(/\\$/g, '\\$');
    }

    document.getElementById('product-select').addEventListener('change', function () {
      document.getElementById('min-score').value = this.selectedOptions[0].dataset.threshold;
      loadOpportunities(false);
    });
    updateBudget();
    loadOpportunities(false);
  </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)
