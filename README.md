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

### 8. Production SaaS Enhancements & Super Admin Console
- **Super Admin Portal (`AdminView.jsx` & `admin.py`):** Executive telemetry dashboard with tabs for KPI Overview, User Management (role switching, paginated user list, account deletion), Stripe Payments tracking, live audit logs, and system health status.
- **Stripe Checkout Integration (`billing.py`):** Checkout sessions for the $49 Launch Audit and recurring subscriptions ($29 Founder, $69 Growth, $199 Agency), with automated webhook ingestion and test-mode sandbox fallback.
- **Multi-Tenant JWT Auth (`auth.py`):** PBKDF2 password hashing (100,000 iterations), HS256 signed JWT tokens, and auto-bootstrapping master admin credentials (`ADMIN_EMAIL`, `ADMIN_PASSWORD` in `.env`).
- **Supabase Cloud Sync with SQLite Fallback (`db.py`):** Stores users, payments, monitored domains, analytics, and audit snapshots in Supabase PostgreSQL when configured, or transparently falls back to local SQLite.
- **Sliding-Window IP Rate Limiting (`rate_limit.py`):** Protects against audit abuse with sliding-window rate limiting (60 requests/min default) returning `HTTP 429` with `Retry-After`.
- **TTL Cache Layer (`db.py`):** In-memory and persisted caching with configurable TTL (default: 3600s) to avoid repeated public scraping within short intervals.
- **Autonomous Background Scheduler (`scheduler.py`):** Background `APScheduler` engine running 6-hour drift checks on registered domains.

---

## Repository Structure

```text
founderreach.ai/
├── frontend/                           # React 19 + Vite Single-Page Application
│   ├── src/                            # React views, components, and API client
│   │   ├── views/                      # LandingView, DashboardView, AuthView, AdminView
│   │   ├── components/                 # ThreeCanvas, Navbar, Toast
│   │   └── api/                        # ApiClient for backend communication
│   ├── public/                         # Public specifications (/llms.txt, robots.txt, sitemap.xml)
│   ├── styles/                         # CSS design system (variables, layout, components)
│   ├── dist/                           # Compiled production build
│   ├── vercel.json                     # Vercel deployment routing
│   └── package.json                    # Node dependencies & Vite build scripts
├── backend/                            # Python Backend Engine & Test Suite
│   ├── founderreach/                   # Core Python package
│   │   ├── auth.py                     # PBKDF2 password hashing & JWT authentication
│   │   ├── admin.py                    # Super Admin telemetry & management APIs
│   │   ├── billing.py                  # Stripe checkout sessions & revenue tracking
│   │   ├── db.py                       # Supabase / SQLite unified storage layer
│   │   ├── rate_limit.py               # Sliding-window IP rate limiter
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
│   └── tests/                          # Full automated test suite (156 tests passing)
├── CLIENT_BOUNDARY_POLICY.md           # Permanent client data & system boundary policy
├── railway.toml                        # Railway backend deployment manifest
├── Procfile                            # PaaS web process configuration
├── pytest.ini                          # Root pytest configuration
├── .env.example                        # Production environment template
└── .gitignore                          # Clean git ignore rules
```

---

## Quick Start

### 1. Install Dependencies

```powershell
# Backend Python requirements
python -m pip install -r backend/requirements.txt

# Frontend Node requirements
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
*(All 156 tests pass cleanly across reachability, SEO/AEO/GEO validation, auth, admin, billing, scheduler, and decision engines)*

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

### 4. Admin Access
Log in via the Sign In modal with your credentials configured in `.env`:
- **Email:** `ADMIN_EMAIL` (default: `admin@founderreach.ai`)
- **Password:** `ADMIN_PASSWORD` (configured in `.env`)
Once authenticated, click **"Admin Console"** in the top navigation bar to access the Super Admin Portal.

---

## Deployment Guide

### Frontend Deployment (Vercel)
1. Import repository on [Vercel](https://vercel.com).
2. Set **Root Directory** to `frontend`.
3. Build Command: `npm run build` | Output Directory: `dist`.
4. Add Environment Variable:
   - `VITE_API_BASE_URL`: `https://your-railway-app.up.railway.app`

### Backend Deployment (Railway)
1. Create a new service on [Railway](https://railway.app) from your GitHub repo.
2. Railway detects [`railway.toml`](railway.toml) and [`Procfile`](Procfile) automatically.
3. Add Environment Variables in Railway settings:
   - `ADMIN_EMAIL`: Your secure admin email
   - `ADMIN_PASSWORD`: Your secure admin password
   - `JWT_SECRET_KEY`: Random 64-char hex key
   - `STRIPE_SECRET_KEY`: `sk_live_...`
   - `STRIPE_PUBLISHABLE_KEY`: `pk_live_...`
   - `STRIPE_WEBHOOK_SECRET`: `whsec_...`
   - `SUPABASE_URL`: `https://your-project.supabase.co` (optional)
   - `SUPABASE_SECRET_KEY`: Service role secret (optional)
   - `SUPABASE_ENABLED`: `true` (if using Supabase)

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
