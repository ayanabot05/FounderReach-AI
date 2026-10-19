# FounderReach AI — Frontend Architecture Guide

Welcome to the **FounderReach AI** frontend repository. This guide is written so that any new engineer, designer, or contributor can immediately understand the architecture, folder structure, data flow, and how to extend components.

---

## Architecture Principles

1. **Modular Component Structure:** Zero monolithic 1,000-line files. Each feature (audit form, 3D visualizer, progress tracker, proof of work, scorecards, fix cards) is isolated in its own file under `js/components/`.
2. **API Isolation:** Frontend and backend communicate exclusively through JSON HTTP APIs via `js/api/client.js`. There are no hidden dependencies or backend imports.
3. **Founder-First UX:** Non-technical founders see zero marketing jargon. Everything is presented in plain English with 1-click "Copy Code" buttons.
4. **Transparent Proof of Work:** We provide verifiable technical evidence (HTTP status, response latency, DNS/SSL verification, robots.txt status, AI crawler permissions) so founders have total trust in our findings.
5. **No External CDN Dependencies:** All vendor files (such as Three.js for 3D visuals) are hosted locally inside `vendor/` to comply with the client data security boundary policy.

---

## Directory & File Structure

```text
frontend/
├── index.html                           # Single-page HTML entry point & semantic DOM targets
├── styles.css                           # Root CSS stylesheet importing modular style files
├── app.js                               # Root ESM loader connecting to ./js/app.js
├── README.md                            # Architecture documentation (you are here)
│
├── styles/                              # CSS Design System
│   ├── variables.css                    # Design tokens (colors, gradients, shadows, dark theme)
│   ├── layout.css                       # Reset, canvas layer, header, hero, responsive grids
│   └── components.css                   # Buttons, badges, codeboxes, proof-cards, scorecards, toast
│
├── vendor/                              # Local vendor dependencies (zero external CDNs)
│   └── three.module.js                  # Three.js 3D WebGL runtime
│
└── js/                                  # JavaScript Application
    ├── app.js                           # Master App controller and DOM lifecycle orchestrator
    │
    ├── api/
    │   └── client.js                    # Isolated API client for backend communication
    │
    ├── state/
    │   └── store.js                     # Reactive event store (IDLE, SCANNING, COMPLETED, ERROR)
    │
    └── components/                      # Reusable UI Components
        ├── scene3d.js                   # Three.js interactive 3D particle sphere & scan orb
        ├── toast.js                     # Temporary notification alerts (copy-to-clipboard)
        ├── auditForm.js                 # Non-IT founder onboarding form with 1-click example demo
        ├── auditProgress.js             # Live multi-stage progress tracker
        ├── proofOfWork.js               # Diagnostic verification panel (DNS, latency, headers)
        ├── scoreCards.js                # SEO, AEO, and GEO 0-100 scores with letter grades
        └── fixCard.js                   # Ready-to-copy code fixes with 1-click copy buttons
```

---

## Component Reference & How to Extend

### 1. `ApiClient` (`js/api/client.js`)
- **Purpose:** Handles all communication between the web browser and the backend server.
- **Key Method:** `auditWebsite({ url, businessName, description, targetAudience, painPoint })`
  - Sends a `POST /api/audit` request to the backend.
  - Automatically falls back to high-fidelity simulated engine audit when running offline or during UI development.
- **Adding a new endpoint:** Add a new async method to `ApiClient`, format the payload, and return the JSON response.

### 2. `Scene3D` (`js/components/scene3d.js`)
- **Purpose:** Renders the ambient 3D particle sphere and orbital rings in the background.
- **Interactivity:**
  - Mouse moves create subtle 3D parallax.
  - Calling `scene3d.updateState("scanning")` speeds up rotation and pulses particle size.
  - Calling `scene3d.updateState("completed")` smoothly stabilizes the sphere.

### 3. `AuditFormComponent` (`js/components/auditForm.js`)
- **Purpose:** Clean, frictionless onboarding for founders.
- **Fields:**
  1. Public Website URL
  2. Business Name
  3. One-sentence product description
  4. Target audience
  5. Primary customer pain point
- **Quick Demo Feature:** Clicking "⚡ Try Example Demo" automatically pre-populates all inputs.

### 4. `ProofOfWorkComponent` (`js/components/proofOfWork.js`)
- **Purpose:** Solves founder skepticism by showing undeniable proof that an audit occurred:
  - Exact URL checked
  - Server latency in milliseconds
  - HTTP status code badge
  - DNS resolution check
  - SSL validity
  - Robots.txt crawl status
  - AI crawler permission matrix (GPTBot, PerplexityBot, Google-Extended)

### 5. `ScoreCardsComponent` (`js/components/scoreCards.js`)
- **Purpose:** Displays high-level health metrics:
  - **SEO Score:** Traditional Google Search ranking readiness.
  - **AEO Score:** Direct answer & Google AI Overview readiness.
  - **GEO Score:** Generative AI recognition (ChatGPT, Gemini, Perplexity).

### 6. `FixCardsComponent` (`js/components/fixCard.js`)
- **Purpose:** Delivers copy-paste code snippets so founders don't have to hire expensive agencies:
  - `<title>` and `<meta description>` tags.
  - Schema.org JSON-LD structured data.
  - AEO FAQ Question/Answer markup.
  - GEO `llms.txt` knowledge graph definition.
  - Verified customer demand opportunities.

---

## Local Development & Testing

You can serve the frontend using Python's built-in HTTP server or the FounderReach FastAPI backend:

```powershell
# Option A: Standalone test server
python -m http.server 8000 --directory frontend

# Option B: Run with FounderReach FastAPI backend
python -m uvicorn founderreach.web.app:app --reload --port 8000
```

Open `http://localhost:8000` in any modern browser to view the application.
