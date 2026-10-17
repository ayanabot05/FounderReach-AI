# FounderReach AI — deployed Supabase access and reconciliation audit

**17 October 2026 · Read-only owner-side verification.** The CEO ran `python audit_supabase_readonly.py` on a Windows machine with working Supabase connectivity and supplied the complete output. This executor independently inspected the local SQLite database, saved evaluation dataset, and write/read code; its own network still cannot resolve Supabase. No production row, grant, policy, or migration was changed.

## Deployed access result

| Table | Anonymous REST read | Service REST read | Live RLS | `authenticated` grants | Policies |
| --- | --- | --- | --- | --- | --- |
| `opportunities` | HTTP 401 | HTTP 200, 12 rows | Enabled | None of SELECT/INSERT/UPDATE/DELETE | None |
| `cost_ledger` | HTTP 401 | HTTP 200, 0 sampled rows | Enabled | None of SELECT/INSERT/UPDATE/DELETE | None |
| `cache` | HTTP 401 | HTTP 200, 0 sampled rows | Enabled | None of SELECT/INSERT/UPDATE/DELETE | None |
| `content_hashes` | HTTP 401 | HTTP 200, 0 sampled rows | Enabled | None of SELECT/INSERT/UPDATE/DELETE | None |

The privileged read-only SQL catalog returned all four tables with `relrowsecurity=true`, `relforcerowsecurity=false`, no deployed policies, and no `anon` SELECT/INSERT or `authenticated` SELECT/INSERT/UPDATE/DELETE privileges. The anonymous REST 401 checks confirm no anonymous read through the tested endpoint; the service 200 checks confirm legitimate privileged reads still work. **No broader authenticated-role table access was found.** No production write-denial request was attempted. Absent grants and policies support a deny assessment, but this audit did not test every possible RPC, view, exposed schema, or credential distribution path. `relforcerowsecurity=false` means privileged table owners may bypass RLS; this is expected for the server role, and backend key custody still matters.

## Exact unmatched records

The live comparison returned **cloud=12, local=12, shared IDs=11, cloud-only=1, local-only=1, zero mismatches among shared rows**. Both unmatched records refer to the same [Hacker News discussion](https://news.ycombinator.com/item?id=47396347):

| Store | Stable ID | Row created (UTC as reported) | Discussion date | Classification |
| --- | --- | --- | --- | --- |
| Cloud only | `eval_hn_47396347` | 2026-10-16 19:24:53.028102+00:00 | Missing | `RESEARCH_INSIGHT` |
| SQLite only | `696355b55fa12c36` | 2026-10-16 19:21:20 | 2026-03-16 | `RESEARCH_INSIGHT` |

Local code generates `696355b55fa12c36` as the first 16 hex characters of SHA-256(`AYANA:hn_47396347`). `eval_discovery.py` instead assigns `eval_` + the source ID. The saved evaluation dataset contains `eval_hn_47396347` for that same URL, author, score (60), classification, and source verification timestamp; its excerpt length differs from the local row. The cloud row's actual creation time differs from the saved dataset's `created_at`, so the dataset is corroboration of the ID convention, not a byte-for-byte cloud snapshot.

**Conclusion:** these are duplicate representations of **one source discussion**, not two independent customer opportunities. The discussion remains research-only and outside the 90-day outreach window. The records' different IDs and dates are a synchronization/identity divergence. The exact historical cloud failure cannot be proven from current snapshots alone.

**Likely mechanism, supported by code and chronology:** the hashed SQLite row was created first. `Database.save_opportunity()` upserts Supabase by `id` and always writes SQLite. SQLite resolves conflicts on `original_url` but does **not** replace the existing `id`. When the evaluation importer later used the `eval_` ID for the same URL, cloud retained/created the evaluation ID while SQLite retained its earlier hashed ID. A transient failed cloud write during the first save is plausible; so is a prior cloud state that lacked the hashed row. Neither mechanism should be asserted as a proved outage without historical request logs.

## Proposed reconciliation — no mutation approved

1. Preserve both row snapshots and the owner-side audit output. Record the URL-based alias pair and field differences in a **local review artifact** only. Do not delete, upsert, or rewrite either production row now.
2. Compare the complete pair read-only before choosing an authority for `discussion_date`, evidence excerpt, verification notes, feedback, and timestamps. The local record has a useful source date; do not copy it to cloud until its provenance is checked. No opportunity should become actionable from this reconciliation.
3. Treat this URL as **one research discussion** in reports, with both storage IDs listed. Flag any future cloud/local read that shows one version as `unsynchronized`; do not report the stores as synchronized merely because each contains 12 rows.
4. For a later approved repair, define a single stable ID algorithm and a URL-level alias/conflict policy. First preserve the old row versions and audit trail; apply an idempotent transaction or reviewed migration with rollback evidence. Do not use blind upsert or overwrite by URL. Separately verify feedback and cost-ledger reconciliation before considering cloud primary.
5. Keep production experiment writes on HOLD until the chosen conflict policy and authenticated approval storage are reviewed. The current service credential can read, but safe dual-write behavior is still unproven.

## AYANA continuation

The local AYANA repository contains three guide routes and content: `/whatsapp-check-ins-for-parents`, `/medicine-reminders-for-parents`, and `/nri-parent-care`. The CEO's later owner-side `check_ayana_guides_readonly.ps1` run on 17 October **passed**: all three returned 200, had distinct HTML hashes, page-specific titles and H1s, self-referencing canonicals, and sitemap entries. The CEO also confirmed correct mobile rendering. The earlier false React text-marker result was a limitation of that marker test, not evidence that the pages were absent. Do not repeat deployment checks unless the deployment changes.

The code-level conversion gap identified before the CEO's deployment verification was addressed in **local AYANA source only** after the CEO authorized local implementation. The test results and remaining production blockers are in [AYANA_LOCAL_ATTRIBUTION_ACCEPTANCE.md](AYANA_LOCAL_ATTRIBUTION_ACCEPTANCE.md). A signup is not a qualified inquiry, and no production tracking patch is approved or deployed.

**Decision:** deployed table access checks pass for the four tested tables; the two opportunity rows are a confirmed same-source ID divergence. Reconciliation repair and AYANA external pilot remain on HOLD pending CEO review and live guide/measurement verification.
