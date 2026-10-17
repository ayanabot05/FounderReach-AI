# FounderReach AI

> *"Improve your website & discover verified customer demand without touching client data, repositories, or credentials."*

FounderReach AI is a local-first website analysis (SEO, AEO, GEO) and evidence-verified demand intelligence tool built for founders. It strictly adheres to [CLIENT_BOUNDARY_POLICY.md](CLIENT_BOUNDARY_POLICY.md):
- **Read-only website observations:** Performs bounded `GET` requests only to explicitly approved public pages (`homepage`, `/robots.txt`, `/sitemap.xml`, and approved URLs).
- **Zero interference with client systems:** Never touches a client's repository, hosting, deployment, database, or credentials, and never pushes, merges, or deploys anything for a client.
- **Copyable suggestions only:** Every recommended improvement is provided as copyable text in a local Markdown report for the founder to review and apply on their own terms.

---

## Repository Structure (`frontend/` & `backend/`)

```text
founderreach.ai/
├── frontend/                           # User Interface (HTML, CSS, JS)
│   ├── index.html                      # Single-page local client review UI
│   ├── styles.css                      # Local stylesheet (zero external CDNs)
│   ├── app.js                          # Frontend UI logic
│   └── README.md                       # Frontend documentation
├── backend/                            # Python Backend Engine & Test Suite
│   ├── founderreach/                   # Core Python package
│   │   ├── cli.py                      # CLI (`client-review`, `find`, `verify`, `budget`)
│   │   ├── client_review.py            # Offline & approved live-site client review generator
│   │   ├── m3/                         # M3 local SEO, AEO & GEO website analysis
│   │   ├── m4/                         # M4 local acquisition decision engine
│   │   ├── validation/                 # Source verification, scoring & intent checks
│   │   └── web/                        # Local FastAPI server serving `frontend/`
│   ├── profiles/                       # Founder-confirmed product profiles (`scheduleflow.json`)
│   ├── source_registry/                # Source policies (`hackernews.json`, `hackernews.v1.json`)
│   ├── evals/                          # Human comparison evaluation cases
│   ├── reports/                        # Milestone completion reports (M1–M4) & spending ledger
│   ├── tests/                          # Full automated test suite (132 tests)
│   ├── demo_acquisition.py             # Offline M4 synthetic demonstration runner
│   ├── evaluate_independent.py         # Independent intent classifier benchmark
│   ├── pytest.ini                      # Backend pytest configuration
│   └── requirements.txt                # Python dependencies
├── CLIENT_BOUNDARY_POLICY.md           # Permanent client data & system boundary policy
├── pytest.ini                          # Root pytest configuration
├── .env.example                        # Safe environment template
└── .gitignore                          # Git ignore rules
```

---

## Quick Start

### 1. Install Backend Requirements
```powershell
pip install -r backend/requirements.txt
```

### 2. Run the Safe Offline Test Suite
From the repository root:
```powershell
python backend/tests/run_safe.py -q --basetemp C:\Temp\fr_pytest
```
Or using `pytest` directly from the root or `backend/`:
```powershell
python -m pytest -q
```

### 3. Run a Local Client Website Review
```powershell
$env:PYTHONPATH = "backend"
python -m founderreach.cli client-review `
  --profile backend/profiles/scheduleflow.json `
  --permission live_permission.json `
  --live-site `
  --output client_review_report.md
```
