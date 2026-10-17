# AYANA local guide attribution — CEO acceptance report

**17 October 2026 · Local source and tests only. Production deployment: HOLD.** The CEO's owner-side verification passed for all three existing guides: unique initial HTML, correct title/H1/canonical, sitemap inclusion, and mobile rendering. No new guide, publication, paid service, or production database change was made.

## Local implementation

The existing analytics sink and 90-day event retention remain in place. The patch records a `guide` page view for valid guide routes and tracks **both** existing “Get started” links with a known guide slug. A bounded first-touch `utm_source` category is kept in the tab's `sessionStorage`, so a guide URL such as `?utm_source=chatgpt.com` becomes the `chatgpt` category and survives the route change to signup. Arbitrary query strings, referrers, `utm_medium`, and `utm_campaign` are not retained. Unknown sources are grouped as `other`; the backend also bounds source and guide metadata.

Only a tab that viewed a guide supplies its anonymous session token with registration. The backend validates the token shape and, after account creation, records `signup_completed` only if that session has a guide page view within 24 hours. The analytics row has **no user ID, email, phone, or parent details**. Registration continues if analytics fails; a sanitized exception type is logged for diagnosis. The admin-only growth summary now includes a guide funnel with ordered, distinct view sessions, CTA sessions, and signup sessions. A session that clicks multiple guides is assigned to its latest eligible guide CTA for signup counting. Duplicate events do not inflate session counts.

`qualified_inquiries` is returned as **null**, not a signup count or an invented zero. No verified voluntary inquiry intake or qualification process exists yet. This implementation measures a same-tab, event-observed funnel; it does not prove a unique person, causal acquisition, or a customer problem. Best-effort page/CTA beacons and session changes across tabs or devices can undercount conversions. Public analytics events are not authenticated, so funnel counts are directional rather than fraud-resistant.

## Exact AYANA files changed

| File | Change |
| --- | --- |
| `frontend/src/lib/analytics.js` | Bounded first-touch source persistence and guide-only session accessor |
| `frontend/src/pages/GuidePage.jsx` | Guide page view and both existing CTA events |
| `frontend/src/pages/Signup.js` | Optional anonymous guide-session token on registration |
| `backend/models.py` | Bounded optional token and allowlisted guide/source event metadata |
| `backend/routes/auth.py` | Best-effort anonymous signup completion after account creation |
| `backend/services/growth_analytics.py` | Recent-guide signup recorder and deduplicated guide funnel aggregate |
| `frontend/src/lib/analytics.test.js` | Source privacy and same-session UTM tests |
| `frontend/src/pages/GuidePage.test.jsx` | Guide view and both CTA tests (new) |
| `frontend/src/pages/Signup.test.js` | Registration payload includes a guide session only after a guide view |
| `backend/tests/test_guide_attribution_unit.py` | Funnel, validation, and SQL-helper tests (new) |

## Verified tests

| Command scope | Result |
| --- | --- |
| AYANA frontend focused Jest, `analytics.test.js`, `GuidePage.test.jsx`, and `Signup.test.js` | **3 suites, 10 tests passed**; the final standalone Signup rerun also passed cleanly |
| AYANA backend focused pytest with `APP_ENV=test`, dummy `127.0.0.1/ayana_local`, and outbound services disabled | **4 tests passed** |
| Python AST syntax parse for three modified backend files | **Passed** |
| FounderReach `tests/test_acquisition.py` | **5 tests passed**, but these exercise a caller-supplied approval object, not real authentication |

The AYANA backend database integration suite was **not run**. Its safety fixture requires an isolated local PostgreSQL database named `*_local`; none is available here. The dummy URL used for pure unit tests did not connect or write. Before deployment, run the database-backed registration and admin-summary tests against an isolated local database, confirm that the signup event is recorded once after a successful guide-origin registration, and confirm no event is recorded for non-guide or failed registration. Then verify a local browser flow with an actual backend beacon before using the metrics for a 28-day pilot.

## Security and approval gate

The Supabase deployed access audit passed for the four tested FounderReach tables: anonymous REST reads returned 401, service reads returned 200, RLS is enabled, no policies exist, and `authenticated` has no table grants. The 12/12 cloud/local opportunity comparison identified one same-source ID divergence; a no-overwrite reconciliation plan is in [SUPABASE_SECURITY_RECONCILIATION_2026-10-17.md](SUPABASE_SECURITY_RECONCILIATION_2026-10-17.md). No repair was applied.

**Authenticated CEO approval control: FAIL / not implemented.** FounderReach's prototype `record_ceo_approval()` trusts a caller-created `Approval` name and `manual_execution_packet()` trusts caller-supplied gate Booleans. The local tests demonstrate this interface, not CEO identity verification. The packet remains manual-only and has no publication adapter, but it must not be treated as operational authorization. The required future control is a backend-verified CEO subject, exact action-version digest, append-only audit, and independently collected fresh preflight evidence as described in [CEO_BLOCKER_RESOLUTION_PATCH_PROPOSAL.md](CEO_BLOCKER_RESOLUTION_PATCH_PROPOSAL.md). No approval-service implementation or production write is authorized by this local patch.

## Remaining blockers before the external pilot

1. Run database-backed AYANA integration and browser funnel checks in an isolated local environment; review analytics privacy notice, event retention, and data access for the anonymous session token.
2. Define a voluntary qualified-inquiry intake and manual qualification rubric. Keep inquiry counts separate from signups.
3. Verify campaign attribution requirements. The local patch preserves only a bounded `utm_source` category; an exact experiment-specific campaign identifier is **not** implemented and requires a privacy-safe allowlist and CEO-approved measurement plan if needed.
4. Implement and verify authenticated CEO approval and independently generated preflight gates before any action packet is operational.
5. Review the same-source cloud/local ID divergence and cost/vendor billing separately. Do not assume the stores are synchronized.
6. Obtain explicit CEO approval for any production deployment, publication, external contact, or spend. Current newly authorized spend: **₹0**; ₹500–₹600 target and ₹1,000 ceiling remain unchanged.

**Decision:** local attribution implementation passes focused tests; production deployment and the 28-day pilot remain **HOLD**.
