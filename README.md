# FounderReach AI

> *"Improve your website & discover verified customer demand without touching client data, repositories, or credentials."*

FounderReach AI is an autonomous website analysis (SEO, AEO, GEO) and evidence-verified customer demand discovery agent built for founders. It strictly adheres to [CLIENT_BOUNDARY_POLICY.md](CLIENT_BOUNDARY_POLICY.md):
- **Read-only website observations:** Performs bounded, IP-pinned `GET` requests only to public domain assets (homepage, `/robots.txt`, `/sitemap.xml`, and `/llms.txt`).
- **Zero interference with client systems:** Never touches a client's repository, hosting, deployment, database, or credentials, and never pushes, merges, or deploys code on a client's behalf.
- **Copyable suggestions only:** Every fix is provided as copy-paste snippets with platform-specific instructions (WordPress, Webflow, Framer, Shopify, and Custom HTML) for the founder to apply on their own terms.

---

## Core Capabilities & Architectural Priorities

### 1. Priority 1: Reachability Sentinel
- **IP-Pinned TCP Sockets:** Resolves hostname to public IP and pins socket connections to prevent DNS rebinding and SSRF attacks (private IPs `127.0.0.1`, `10.x`, `192.168.x`, `169.254.169.254` are strictly blocked).
- **Hop-by-Hop SSRF Redirect Guard:** Inspects redirect destination headers (up to 3 hops) before following.
- **Payload Stream Cap:** 512 KB socket limit prevents memory exhaustion.
- **Evidence Console:** Emits exact reachability proof: Checked URL, timestamp, HTTP status, final URL, TLS certificate validity, pinned IP, response latency (ms), and real HTML confirmation.

### 2. Priority 2: SEO Basics
- **Metadata Extraction:** Title tag length & content, meta description length, canonical URL validation, OpenGraph suite (`og:title`, `og:description`, `og:url`), and mobile viewport verification.
- **Heading & Asset Hierarchy:** H1 heading count and image alt-attribute coverage ratio (`images_missing_alt` vs. `images_total`).
- **Sitemap & Robots Verification:** Direct detection and status checks for `/sitemap.xml` and `/robots.txt`.

### 3. Priority 3: Answer Engine Optimization (AEO)
- **Direct Answer Grounding:** Synthesizes `SoftwareApplication` and `FAQPage` Schema.org JSON-LD structured data for Google AI Overview grounding.
- **Syntax Validation:** Every generated JSON-LD script is programmatically verified on the backend using `json.loads()` before rendering.

### 4. Priority 4: Generative Engine Optimization (GEO)
- **Site-Specific `/llms.txt` Generator:** Creates token-efficient Markdown knowledge graphs designed for retrieval by ChatGPT, Claude, and Perplexity.
- **AI Crawler Permissions Matrix:** Official Python `RobotFileParser` validates permissions for `GPTBot`, `ClaudeBot`, `PerplexityBot`, and `Google-Extended`.

### 5. Fix Studio (Founder-Proof)
- **Standardized Metadata:** Every diagnosed issue displays **Problem**, **Why it matters**, **Recommended fix**, **Difficulty** (Easy), **Time required** (5 minutes), **Risk** (Low), and **Where to add it**.
- **Interactive Platform Switcher:** Step-by-step placement instructions for **WordPress**, **Webflow**, **Framer**, **Shopify**, and **Custom HTML**.
- **1-Click Actions:** Instant "Copy Fix" and "Copy Instructions" buttons.

### 6. Customer Demand Radar (Honest & Curated)
- **Public Community Ingestion:** Surfaces relevant discussions from Reddit (`r/SaaS`, `r/SideProject`, `r/Entrepreneur`) and Hacker News (`Ask HN`).
- **Zero Auto-Posting:** Formulates non-spam founder response playbooks for the founder to review and copy. Never posts or messages automatically.
- **Honest Evidence:** Direct links to original URLs, pain point alignment, and zero fake engagement counters.

### 7. Action Center Dashboard
- **Executive Telemetry:** Overall Health Score (0–100, Grade A/B/C), "What this means", and prioritized "Next Best Action" with estimated impact and time required.
- **Three Core Cards:** "Fixes Needed" (with direct fix triggers), "Fixes Completed / Verified" (green checkmarks), and "Customer Signals".
- **Live Evidence Console:** Shows real-time inspection parameters, "Recheck Target" button, and "Export Report" button.

### 8. Production SaaS Enhancements (P2 – P4)
- **P2 User Authentication (`backend/founderreach/auth.py`):** Multi-tenant auth with salted `PBKDF2-HMAC-SHA256` password hashing (100,000 iterations), signed `PyJWT` tokens (HS256, 7-day expiration), and SQLite user persistence.
- **P3 Autonomous Background Scheduler (`backend/founderreach/scheduler.py`):** `APScheduler` background daemon executing 6-hour recurring scans for registered domains with audit snapshots and drift history.
- **P4 Reddit API Connector (`backend/founderreach/connectors/reddit.py`):** OAuth2 client credentials flow for commercial Reddit API ingestion (disabled by default unless configured in `.env`).

---

## Repository Structure

```text
founderreach.ai/
├── frontend/                           # React 19 + Vite Single-Page Application
│   ├── src/                            # React views, components, and API client
│   │   ├── views/                      # LandingView, DashboardView, AuthView
│   │   ├── components/                 # ThreeCanvas, Navbar, Toast
│   │   └── api/                        # ApiClient for backend communication
│   ├── public/                         # Public specifications (/llms.txt, robots.txt, sitemap.xml)
│   ├── styles/                         # CSS design system (variables, layout, components)
│   ├── dist/                           # Compiled production build
│   └── package.json                    # Node dependencies & Vite build scripts
├── backend/                            # Python Backend Engine & Test Suite
│   ├── founderreach/                   # Core Python package
│   │   ├── auth.py                     # PBKDF2 password hashing & JWT authentication
│   │   ├── scheduler.py                # APScheduler 6-hour autonomous monitoring worker
│   │   ├── cli.py                      # CLI (`client-review`, `find`, `verify`, `budget`)
│   │   ├── client_review.py            # Offline & approved live-site review generator
│   │   ├── connectors/                 # Reddit OAuth & Hacker News Algolia connectors
│   │   ├── m3/                         # M3 local SEO, AEO & GEO website analysis
│   │   ├── m4/                         # M4 local acquisition decision engine
│   │   ├── validation/                 # Source verification, scoring & intent checks
│   │   └── web/                        # FastAPI server with IP-pinned audit service & CORS
│   ├── profiles/                       # Founder-confirmed product profiles (`scheduleflow.json`)
│   ├── source_registry/                # Source policies (`hackernews.json`, `hackernews.v1.json`)
│   ├── reports/                        # Milestone completion reports & spending ledger
│   └── tests/                          # Full automated test suite (151 tests)
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
python -m pip install -r backend/requirements.txt

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
*(All 151 tests pass cleanly across reachability, SEO/AEO/GEO validation, auth, scheduler, and decision engines)*

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

---

## Pricing & Packaging Matrix

| Tier | Price | Highlights |
| :--- | :--- | :--- |
| **Free Visibility Scan** | **$0 / forever** | Instant SEO, AEO & GEO diagnostic, Schema.org scripts, `/llms.txt` file, evidence console. |
| **Founder** *(Featured)* | **$29 / month** | 24/7 Sentinel crawl monitoring (every 6 hrs), full Fix Studio with platform guides, curated Demand Radar (up to 3 domains). |
| **Growth** | **$69 / month** | Up to 10 domains, instant Slack/Discord webhook alerts, weekly automated re-checks. |
| **Agency** | **$199 / month** | Unlimited domain audits, white-labeled client PDF/MD reports, multi-seat workspaces, direct REST API access. |
| **FounderReach Launch Audit** | **$49 one-time** | Done-with-you deep verification of Schema & `/llms.txt`, targeted crawler permissions check, personalized outreach review, 14-day recheck guarantee. |

---

## Unit Economics & Margins

Because FounderReach AI uses deterministic network parsers and standard library sockets rather than continuous high-token LLM queries:
- **Cost per Audit:** ~$0.0004 – $0.002
- **Fixed Monthly Infrastructure:** ~$7.00 – $11.00/mo (VPS + SQLite)
- **Gross Margins:** **~95% – 96%** across all paid packages.
- **Break-Even:** Just **1 Launch Audit ($49)** or **1 Founder Subscription ($29/mo)** completely covers monthly fixed infrastructure.
