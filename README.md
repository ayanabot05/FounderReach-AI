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
├── frontend/                           # React 19 + Vite Single-Page Application
│   ├── src/                            # React views, components, and API client
│   │   ├── views/                      # LandingView, DashboardView, AuthView
│   │   ├── components/                 # ThreeCanvas, Navbar, Toast
│   │   └── api/                        # Isolated ApiClient for backend communication
│   ├── public/                         # Public specifications (/llms.txt, robots.txt, sitemap.xml)
│   ├── dist/                           # Compiled production build
│   └── package.json                    # Node dependencies & Vite build scripts
├── backend/                            # Python Backend Engine & Test Suite
│   ├── founderreach/                   # Core Python package
│   │   ├── cli.py                      # CLI (`client-review`, `find`, `verify`, `budget`)
│   │   ├── client_review.py            # Offline & approved live-site client review generator
│   │   ├── m3/                         # M3 local SEO, AEO & GEO website analysis
│   │   ├── m4/                         # M4 local acquisition decision engine
│   │   ├── validation/                 # Source verification, scoring & intent checks
│   │   └── web/                        # FastAPI server with IP-pinned audit service & CORS
│   ├── profiles/                       # Founder-confirmed product profiles (`scheduleflow.json`)
│   ├── source_registry/                # Source policies (`hackernews.json`, `hackernews.v1.json`)
│   ├── reports/                        # Milestone completion reports & spending ledger
│   └── tests/                          # Full automated test suite (141 tests)
├── CLIENT_BOUNDARY_POLICY.md           # Permanent client data & system boundary policy
├── pytest.ini                          # Root pytest configuration
├── .env.example                        # Safe environment template
└── .gitignore                          # Git ignore rules
```

---

## Quick Start

### 1. Install Dependencies
```powershell
# Backend Python requirements
pip install -r backend/requirements.txt

# Frontend Node requirements (optional if using pre-compiled dist)
cd frontend
npm install
npm run build
cd ..
```

### 2. Run the Full Automated Test Suite
From the repository root or `backend/`:
```powershell
python -m pytest -q
```
*(All 141 tests pass)*

### 3. Run the Web Application
```powershell
# Start the FastAPI backend server (serves API & pre-compiled React frontend)
$env:PYTHONPATH = "backend"
python -m uvicorn founderreach.web.app:app --port 8004 --reload
```
Open `http://localhost:8004` to view the application.

Or run the Vite development server in `frontend/`:
```powershell
cd frontend
npm run dev
```
Open `http://localhost:3005` (proxies `/api` to port 8004).

### 4. Run a Local Client Website Review CLI
```powershell
$env:PYTHONPATH = "backend"
python -m founderreach.cli client-review `
  --profile backend/profiles/scheduleflow.json `
  --permission live_permission.json `
  --live-site `
  --output client_review_report.md
```
