# FounderReach AI — AI Customer Opportunity Finder

> *"Find people who need your product before you spend money on marketing."*

**Validation status:** See [INDEPENDENT_AUDIT.md](INDEPENDENT_AUDIT.md). Current outreach Precision@5 is N/A because there are no verified actionable results. The local cost ledger is zero, but external account charges were not independently available. Research records do not receive outreach drafts.

FounderReach AI is an evidence-verified customer opportunity engine built for founders. It discovers real, publicly accessible discussions where potential customers express problems that a founder's product can solve, scores them transparently, verifies them against live URLs, and drafts empathetic, non-spam suggested responses.

---

## Key Features

- **Validation Machine (6 Rigorous Checks):**
  1. *Source Verification:* Confirms the URL is reachable (HTTP 200) and the quoted excerpt exists verbatim in the live content.
  2. *Problem Fit (30 pts):* Multi-term sentence-level co-occurrence matching real customer pain points.
  3. *Customer Fit (20 pts):* Verifies participant persona (e.g. NRI, adult child living away, caregiver).
  4. *Intent Classification (20 pts):* Distinguishes active solution seekers from general or philosophical discussions.
  5. *Recency (15 pts):* Freshness decay weighting recent discussions for immediate actionability.
  6. *Evidence Quality (15 pts):* Context depth and specific situational details.
- **Cloud and Local Storage:** Best-effort Supabase writes and local SQLite writes; synchronization and live cloud permissions require verification.
- **Local Cost Ledger:** Applies estimated budget checks to the optional app-managed path. External account spending must be checked separately.
- **Compliance First:** Operates on public Hacker News APIs. Reddit connector is explicitly disabled by policy until commercial-use authorization is obtained.

## M2 local evidence intelligence

`founderreach.evidence.EvidenceObservation` is the normalized, business-scoped input for later channel engines. It keeps provenance, relevance, freshness, verification, permission and human review as separate fields. HN discovery uses bounded date windows and records page/query outcomes. The local `ResearchStore` stores observations, query runs and append-only review events; it applies source retention limits on use. `source_registry/hackernews.v1.json` permits read-only research and owned content planning only. A successful empty query differs from source failure, and neither grants outreach or publication. M2 does not enable Reddit, scheduled collection, production storage, UI workflows or external actions.

## M3 local SEO, AEO and GEO analysis

`founderreach.m3.pipeline.analyze_business` accepts a founder-confirmed profile, M2 local research store, an explicit approved HTTPS origin and URL inventory, and a fetcher. `FixtureSiteFetcher` is network-free for tests. `ApprovedSiteFetcher` uses the existing DNS-checked, pinned connection primitives and enforces same-origin redirects, response, request and time budgets. The SEO audit, AEO question analysis, GEO readiness/citation analysis and `ContentOpportunity` output remain local and review-only. No page, post, contact or publication action is executed. Run `python -m pytest -q --basetemp .pytest-m3-temp` for the full regression suite. See `reports/CTO_M3_COMPLETION_2026-10-17.md` for measured fixture results and limitations.
- **CLI & Web Interface:** Full CLI suite + responsive single-page FastAPI dashboard with 1-click response copying and founder feedback tracking.

---

## Quick Setup

### Local multi-business Phase 1

**M1 local status (17 October 2026):** The discovery engine now requires an explicit confirmed profile. Stable business/source IDs and an explicit tenant-scoped `ResearchStore` preserve research locally, including evidence blocked from outreach. `persist=True` requires that store; it never invokes the legacy SQLite/Supabase opportunity writer. A timely verified customer problem may be classified as an actionable demand signal, but that classification does not authorize a reply or generate a draft. The legacy web data API and the experimental self-service approval/outcome path fail closed pending tenant authentication and signed-gate integration. New authorized cash spend is ₹0; positive-cost usage is rejected. See `reports/M1_TENANT_BOUNDARY_DESIGN_2026-10-17.md`. No production schema or deployment has changed.

Founder-confirmed profiles are in `profiles/`. Run `python -m founderreach.cli find --profile ayana --research` or substitute `scheduleflow` to use the unrelated scheduling SaaS sample. The selected profile supplies HN search terms, scoring signals, intent rules, thresholds and channel restrictions. A draft with `confirmed: false` is rejected by the engine. Results default to non-persistent local evaluation while the existing database lacks per-founder isolation. `--research` shows verified research even when no reply is permitted. These are advisory results; outreach, publishing and paid actions remain behind explicit approval. See `reports/CTO_PHASE1_EXECUTION_2026-10-17.md` for the audit and production blockers.

### 1. Requirements
- Python 3.10+ (Tested on Python 3.13.3)
- `pip install -r requirements.txt`

### 2. Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Your `.env` file supports:
```ini
# Supabase project
SUPABASE_URL=https://xsumvcqeqknshjwdnypy.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SECRET_KEY=your-secret-or-service-role-key

# Optional: Gemini API Key (when unset, operates on local NLP at ₹0)
GEMINI_API_KEY=

# Local SQLite fallback
DATABASE_PATH=data/founderreach.db

# Minimum Score Threshold (default: 75)
DEFAULT_SCORE_THRESHOLD=75
```

---

## CLI Usage

### Discover Opportunities
```bash
# Find verified customer opportunities for AYANA
python -m founderreach.cli find --threshold 75 --limit 10

# Output as JSON
python -m founderreach.cli find --threshold 75 --format json
```

### Inspect Opportunity Details & Suggested Response
```bash
python -m founderreach.cli detail 47396347
```

### Audit Spending & Financial Safeguards
```bash
python -m founderreach.cli budget
```

### Verify Any Live URL & Excerpt
```bash
python -m founderreach.cli verify --url "https://news.ycombinator.com/item?id=47396347" --excerpt "take care of elderly parents"
```

### Record Founder Quality Feedback
```bash
python -m founderreach.cli feedback --id <opportunity-id> --status relevant --notes "Excellent fit for WhatsApp check-in pilot"
```

### Launch Web Dashboard
```bash
python -m founderreach.cli serve --port 8000
```
Then open `http://localhost:8000` in your browser.

---

## Running Automated Tests

Run the full pytest suite and the independent text-intent challenge:
```bash
python -m pytest -v
python evaluate_independent.py
```

---

## Project Structure

```
founderreach.ai/
├── README.md                           # Documentation and quickstart
├── .env.example                        # Safe environment template
├── requirements.txt                    # Project dependencies
├── supabase_schema.sql                 # Supabase PostgreSQL database schema
├── eval_discovery.py                   # Multi-query evaluation discovery runner
├── founderreach/
│   ├── cli.py                          # Terminal CLI interface (rich, argparse)
│   ├── config.py                       # Configuration & budget settings
│   ├── models.py                       # Pydantic data models
│   ├── db.py                           # Dual Supabase Cloud & SQLite persistence
│   ├── engine.py                       # Central discovery and validation orchestrator
│   ├── connectors/
│   │   ├── base.py                     # Base connector contract
│   │   ├── hackernews.py               # HN Algolia public API connector
│   │   └── reddit.py                   # Reddit connector (disabled by policy)
│   ├── validation/
│   │   ├── verifier.py                 # Live HTTP status & excerpt existence check
│   │   ├── deduplicator.py             # Canonical URL & content hash deduplication
│   │   ├── scorer.py                   # 100-point transparent scoring engine
│   │   └── intent.py                   # Active solution seeker intent classifier
│   ├── ai/
│   │   ├── analyzer.py                 # Problem synthesis & suggested response drafter
│   │   └── cost_tracker.py             # Financial ceiling controller (INR & USD)
│   └── web/
│       └── app.py                      # FastAPI server & responsive web dashboard
├── reports/
│   ├── AYANA_VERIFIED_OPPORTUNITIES.md # Real verified AYANA opportunities report
│   ├── EVALUATION_DATASET.json         # Real evidence dataset with precision metrics
│   ├── COMPETITOR_RESEARCH.md          # Analysis of Common Room, Syften, F5Bot, GummySearch
│   ├── SPENDING_LEDGER.md              # Itemized financial audit showing ₹0 spend
│   ├── FINAL_VALIDATION_REPORT.md      # Comprehensive findings & precision assessment
│   └── GPT_SOL_6_HANDOFF.md            # Clean handoff documentation for GPT-SOL 6
└── tests/                              # Pytest test suite (17 tests)
```

---

## Deliverables & Documentation Index

### M4 local acquisition decision engine

`founderreach/m4/` builds evidence-linked acquisition candidates from confirmed profiles, M2 observations, M3 analysis, confirmed owned-channel access, and observed placement records. Eligibility checks precede an eight-dimension ordinal ranking. Results are local review artifacts; the optional gate bridge uses the existing signed M1 approval lifecycle and requires fresh revalidation. Run `python -m pytest -q` for the local regression suite. See [the M4 CTO completion report](reports/CTO_M4_COMPLETION_2026-10-17.md) for scope, demonstration, security limits, and M5 proposal.

- [Competitor Research Report](reports/COMPETITOR_RESEARCH.md)
- [AYANA Verified Opportunities](reports/AYANA_VERIFIED_OPPORTUNITIES.md)
- [Spending Ledger (₹0.00 spent)](reports/SPENDING_LEDGER.md)
- [Final Validation Report (80% Precision @ 5)](reports/FINAL_VALIDATION_REPORT.md)
- [GPT-SOL 6 Handoff Document](reports/GPT_SOL_6_HANDOFF.md)
- [Evaluation Dataset JSON](reports/EVALUATION_DATASET.json)
