# CTO Phase 1 execution — 17 October 2026

## A. Executive summary

**Local Phase 1 minimum slice complete; production status HOLD.** Two founder-confirmed JSON profiles now run through the same discovery, scoring, intent, verification and routing engine. Routing separates demand evidence, owned channels, community replies and partner/media leads. Reply eligibility requires current evidence, source permission, community-rule review and explicit founder approval. No remote repository, production schema, production deployment, prospect or payment was touched by this work.

## B. Existing system assessment and architecture map

`CLI / FastAPI dashboard → HN connector (Reddit disabled) → deduplicator → profile-driven scorer and intent classifier → HN URL/excerpt verifier → advisory route → deterministic explanation → optional SQLite/Supabase persistence`. The separate local acquisition decision prototype ranks AYANA-owned experiments and has a signed approval plus independent preflight gate. AYANA attribution and SEO live in a separate checkout, not in this package.

Repository on `main` tracked `origin/main` at `6366806` when inspected, with a clean initial worktree and GitHub remote `ayanabot05/FounderReach-AI`. No deployment workflow was found in this repository. Git push alone says nothing about AYANA production deployment. Supabase SQL has RLS enabled and public policies revoked; live production RLS, backups, authentication, tenant isolation and deployment state were not independently checked. `db.py` still supports server-held service-role credentials and best-effort dual writes. The FastAPI feedback endpoint accepts unauthenticated writes, and refresh can trigger discovery. Existing SQLite/Supabase `original_url UNIQUE`, plus process-global deduplication, can collapse the same source across businesses. These are production blockers.

Hardcoded AYANA dependencies identified: `engine.py` profile and evidence terms; `scorer.py` problem/persona rules; `intent.py` direct intent rules; HN connector search queries; analyzer claims and response text; CLI/web default labels and selection. The legacy AYANA-specific local experiment (`acquisition.py`) remains intentionally specific to AYANA and uses the loaded AYANA profile. No rewrite or migration was made.

## C. Architecture changes and decision

`profiles/*.json` contain founder-confirmed rules, sample audience and channels. `founderreach/profiles.py` validates local identifier and confirmation before loading. `models.py` validates URL, regexes, channels, costs and thresholds. `engine.py`, `validation/scorer.py`, `validation/intent.py`, `connectors/hackernews.py` and `ai/analyzer.py` consume the selected profile. `routing.py` returns explicit advisory routes and reply gate reasons. CLI `find --profile ayana|scheduleflow` and the web selector switch profiles without source edits. Discovery now defaults to non-persistent results; this avoids adding business records to the existing cross-profile schema. The existing signed approval prototype was left intact.

Simplest viable option was local JSON and deterministic matching: about one short engineering sprint, incremental software cost ₹0. A database-backed tenant model, learned ranking and auto-posting were rejected for this phase because they need stronger identity, isolation, source permissions and outcome evidence. Regex profiles are easy to edit but can miss paraphrases or match weak context; founder review remains necessary. Approval is required before activating any external action, production write, schema migration or deployment.

## D. Test evidence

- `python -m pytest -q --basetemp data\\pytest_phase1`: **33 passed**, including 29 existing and 4 new tests. Initial run without `--basetemp` had 24 passed and 5 setup errors because the sandbox could not create system temp directories; the workspace temp run resolved that environment issue. Intermediate regression runs were repaired before the final pass.
- `python evaluate_independent.py`: 2 TP, 0 FP, 0 FN, 4 TN on six hand-labeled texts. This is a text-intent check only; it does not establish production recall, source permissions or acquisition outcomes.
- `git diff --check`: no whitespace errors.
- Pilot workbook formula check: a temporary ₹4,999 payment, ₹100 fee, 4 hours and ₹500/hour produced ₹4,899 before labor and ₹2,899 after labor, then inputs were cleared. Formula-error scan returned zero matches. Rendered preview was reviewed.

AYANA's separate local PostgreSQL and browser suites were not rerun because their scripts target another checkout and are not affected by these local FounderReach edits. Historical pass claims remain unverified in this run. No live HN search, live Supabase RLS test or production end-to-end test was performed.

## E. Generalization proof

The new engine test feeds the same mocked, source-verified HN discussion adapter into AYANA and ScheduleFlow in turn. Each yields one profile-specific `RESEARCH_INSIGHT` with `demand_evidence`, no suggested response and no persistence. AYANA scores its parent-care example above the scheduling profile; ScheduleFlow does the reverse for an independent consultant's booking difficulty. Airline booking is disqualified for ScheduleFlow. An irrelevant Rust discussion yields an honest empty actionable result. An old relevant discussion retains demand/owned routes while failing reply freshness. Even a fresh discussion cannot pass reply eligibility without allowed channel, source permission, rule review, founder approval and verification.

## F. Security and compliance

Reddit commercial collection remains disabled. The HN verifier still rejects missing excerpts and non-200 responses, and no-verification mode now marks evidence unverified. No route publishes or contacts anyone. Existing signed exact-action and preflight tests pass. Production blockers: unauthenticated feedback write, no tenant authentication/isolation, cross-business URL uniqueness, service-role handling needing live review, and no source registry proving commercial-use rights. Confidence thresholds are schema fields only; they are not calibrated probabilities. Source verification in the test is mocked. Do not claim a production-ready multi-tenant system.

## G. Cost impact

Actual new spending from this local work: **₹0 observed**. No paid API, cloud resource or scheduled job was added. External account charges were not independently audited. Future monthly costs depend on hosting, API terms, usage and human delivery time; no reliable amount can be stated yet. The pilot tracker separates payment, fees, AI/API, hosting, support, fixed costs, labor, taxes and refunds. Profit after founder labor is explicitly separate from contribution before labor.

## H. Commercial validation

`FOUNDING_PILOT_V1.md` contains the interview script, ₹4,999 hypothesis offer, ₹2,000–₹5,000 willingness-to-pay prompts, qualification rubric, manual checklist and results template. `outputs/phase1-pilot/founding_pilot_cost_tracker.xlsx` records actual payments and costs for three founders. Next validation step after CEO approval: interview three qualified founders, record stated willingness to pay separately from money paid, and run manually approved actions. No case study or outcome is claimed.

## I. Next recommended sprint (design only until authorized)

1. **Tenant and write-path design, 2–3 days:** map auth, profile ownership, source IDs and migrations; inspect live RLS/backups read-only. Incremental spend ₹0. Risk: migration and data reconciliation; CEO approval needed for deployment.
2. **Source registry and review queue, 2–3 days:** record source permission, terms, allowed actions, rate limits, verification dates and founder-attested labels. Incremental spend ₹0. Risk: rights differ by source; CEO approval needed before new collection.
3. **Founder profile confirmation and results capture design, 2 days:** editable URL/manual onboarding, one primary action with alternatives, human-readable audit and verified outcome fields. Incremental spend ₹0 for design. Risk: unverified attribution; CEO approval needed for implementation beyond Phase 1.

Later design sequence: improve HN date search before expanding to official APIs; then zero-code onboarding, integrated SEO/AEO/GEO based on observed evidence, and outcome-informed ranking only after measured data exists. Founder-pasted evidence must be labeled founder-attested, never source-verified. No paid extraction, billing or auto-posting is proposed now.

## J. CEO decisions

- **GO** to review the local Phase 1 code and interview materials.
- **HOLD** production multi-business launch and migration until tenant isolation, authentication, URL identity, source permission and live RLS are verified.
- **Approval required** before external founder outreach, payment requests, offer publication, remote Git changes, production deployment, new spending, production data/schema changes or any action on another person's platform.
