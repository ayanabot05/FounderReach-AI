# CTO M1 completion — 17 October 2026

## Decision

**M1 local implementation complete for review. GO to review M2 scope; HOLD M2 implementation, production migration, deployment, outreach, publication, and paid services.** This is a foundation, not a completed acquisition agent.

## Preservation and change scope

The pre-M1 dirty working tree was preserved under `m1-preservation-2026-10-17/` before edits. Its `pre-m1-status.txt`, `pre-m1-tracked.patch`, and file copies capture the earlier local profile/routing/self-service work. No prior edit was reset. The M1 work overlapped prior local changes in the engine, models, configuration, database, legacy API, profile-routing test, README, and environment template.

M1 added `founderreach/identity.py`, `founderreach/research_store.py`, `tests/test_m1_foundation.py`, and `reports/M1_TENANT_BOUNDARY_DESIGN_2026-10-17.md`. It updated `founderreach/engine.py`, `models.py`, `validation/intent.py`, `validation/scorer.py`, `routing.py`, `recommendations.py`, `ai/analyzer.py`, `ai/cost_tracker.py`, `config.py`, `db.py`, `web/app.py`, `web/self_service_app.py`, `self_service_store.py`, `acquisition.py`, `cli.py`, `eval_discovery.py`, `evaluate_independent.py`, `.env.example`, `README.md`, and existing tests that used the legacy implicit CareFlow classifier.

## Foundation behavior

- Confirmed profiles now provide explicit business identifiers and versions. The core engine no longer defaults to CareFlow. Source identity uses platform plus native ID; opportunity identity hashes business plus source identity.
- `ResearchStore` is an explicitly injected, local-only SQLite store. It keys evidence by business and source and allows the same URL under unrelated businesses. Conflicting IDs and URLs fail closed. The legacy globally unique URL writer is disabled. No Supabase schema or production row changed.
- Fresh verified direct need may be classified `ACTIONABLE_OPPORTUNITY`, meaning a timely demand signal only. It does **not** authorize a reply. Permission/rules/approval remain advisory routing checks, and discovery never generates a community reply draft. Older or unverified relevant evidence remains `RESEARCH_INSIGHT` and is stored locally when persistence is explicitly requested. The owned-channel recommender now consumes both verified research and timely demand.
- Shared scoring specificity now uses the selected profile. The classifier requires an explicit profile; CareFlow-specific language is confined to CareFlow's profile and legacy CareFlow experiment fixtures.
- Authorized new cash spend is hard-set to ₹0. Positive-cost usage is rejected before ledger recording, even if an old target or API key exists.

## Security findings

The legacy unauthenticated data endpoints return 503. Legacy opportunity and feedback write methods reject writes. The local self-service prototype no longer exports a module-level ASGI app; its unsigned approval and outcome paths return 503, and direct store methods reject them. The signed exact-action and independent preflight gate in `approval_gate.py` is unchanged and remains the only implemented manual packet release mechanism. It is not yet integrated with authenticated founder/CEO identities or production storage.

The proposed tenant/RLS schema, conflict handling, and migration gates are documented in `M1_TENANT_BOUNDARY_DESIGN_2026-10-17.md`. They have not been applied. Existing cloud/local identity divergence still requires a separately approved reconciliation.

## Verification

- Pre-M1 baseline: 33 tests passed with a workspace pytest temp directory.
- Final M1: **39 tests passed**, one third-party `python_multipart` deprecation warning; no test failures.
- Independent six-record text-intent challenge: TP 2, FP 0, FN 0, TN 4. This is an offline selected sample, not live precision or recall.
- New tests cover two businesses sharing one source URL, stable IDs, profile-version rescoring, conflicting aliases, old/unverified research preservation, permission-blocked replies, zero-spend rejection, disabled legacy routes, and blocked unsigned approval/outcome paths.
- No live HN, Supabase, production RLS, browser, or end-to-end acquisition test was run during M1.

## Remaining gaps and M2 recommendation

Tenant ownership and RLS remain a design until an approved isolated-database implementation and migration. The local self-service application is incomplete and not deployable. HN date discovery, source registry, permission evidence, human review, source-specific verification freshness, and media/partner models belong to M2. SEO/AEO/GEO, cross-channel ranking, attribution, qualified-inquiry intake, and outcome learning remain M3–M6.

**Recommendation: GO for CEO review of an M2 plan focused on date-based HN discovery, source registry, evidence preservation, and review workflow at ₹0 new spend. HOLD M2 code work until separately approved.**
