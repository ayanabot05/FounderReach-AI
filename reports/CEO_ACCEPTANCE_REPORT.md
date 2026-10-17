# FounderReach AI — technical preflight and local acceptance

**17 October 2026. Status: CONDITIONAL, local demonstration only.** No external action, paid activation, production experiment write, policy change, or publication was performed. The later owner-side Supabase results and exact ID divergence are documented in [SUPABASE_SECURITY_RECONCILIATION_2026-10-17.md](SUPABASE_SECURITY_RECONCILIATION_2026-10-17.md); its live findings supersede the blocked cloud checks below.

## What was actually verified

| Gate | Result and evidence | Decision |
| --- | --- | --- |
| Supabase DNS | `python preflight_supabase.py` returned `DNS: unavailable (gaierror)` in this executor. Prior read-only service and anonymous client attempts also failed with connection errors. | **Blocked.** This does not prove the public service is down. |
| Deployed RLS and permissions | Local `supabase_schema.sql` enables RLS, drops earlier public-all policies, and revokes `anon`/`authenticated` table grants. No deployed policy catalog or anonymous endpoint response could be obtained. | **Unverified.** Do not apply the local SQL to production without separate CEO approval. |
| Cloud versus SQLite | SQLite contains 12 opportunities, all `RESEARCH_INSIGHT`; zero cost-ledger rows and ₹0 logged. The read-only preflight script is ready to compare cloud IDs and key fields after DNS works. | **Unreconciled.** The existing `Database` writes cloud first, then SQLite; a cloud failure falls back locally, with no queue or replay. Client construction is not a connectivity check. |
| AYANA ownership and search | CEO states Vercel hosting, Squarespace DNS, and DNS-verified Search Console. AYANA's 12 Oct owner audit reports an indexed homepage, five indexed URLs, and eight impressions/one click in its selected three-month period; sitemap processing was unresolved then. Current admin and site state could not be independently reached because this executor could not resolve `www.ayanabott.com`. | **Ownership user-attested; current deployment and Search Console data unverified.** |
| AYANA analytics | Adjacent AYANA source imports `@vercel/analytics/react` in `frontend/src/App.js`; custom `frontend/src/lib/analytics.js` sends landing page views and CTA events to backend `/api/analytics/event`; admin summary aggregates sessions, CTA sessions, and signup counts. | **Implemented in source; live delivery and Vercel activation unverified.** No need to install GA4 merely on assumption. |
| AYANA attribution | `Landing.js` tracks CTA clicks, but `GuidePage.jsx` has no custom page-view/CTA events; `Signup.js` sends name, email, phone, password without campaign/session attribution. Backend `growth_analytics.py` explicitly aggregates signup cohorts “without identity linking.” | **Missing for a guide-to-qualified-signup funnel.** Existing landing counts cannot prove which campaign produced a signup. |
| Guide deployment | AYANA source contains `whatsapp-check-ins-for-parents`, `medicine-reminders-for-parents`, and a third guide. The 12 Oct audit said guides were local and not deployed. | **Current deployed status unverified.** Reuse an existing guide if appropriate; do not create duplicate content. |
| Costs | Local FounderReach ledger is empty; the demo invokes deterministic code and no paid API. Vendor billing for Vercel, Supabase, domain, and any external APIs was not available. | **₹0 recorded and ₹0 newly authorized; actual external charges unverified.** App ledger alone is not a spending cap. |

## Frozen manual comparison

The blank [worksheet and blind rubric](AYANA_MANUAL_BASELINE_V1.md) were frozen before this implementation. SHA-256: `5AE6B4719E5FEFD18D773BC09ACB047A9E037CCF7203EBA3F7B9B2E9E460C204`. The founder must complete the timed manual exercise and preserve an unedited artifact before viewing the local assisted output. The earlier CEO pilot document already named an owned-site candidate, so record prior exposure; a truly blind founder comparison may no longer be possible. No founder baseline time or rubric score has been collected. No time-saving or superiority claim is made.

The engine accepts a completed baseline JSON with founder ID, start/stop times, active minutes, sources, selected action, draft outline, CTA, measurement plan, and whether the founder saw the earlier recommendation. This is an evidence-presence gate, not independent proof that a founder actually worked for the recorded time.

## Local decision engine

`founderreach/acquisition.py` reuses the AYANA profile, human-labeled research, intent classifier, problem-fit scorer, and cost tracker. It makes **no live discovery request**. Reddit remains disabled. Two positive labeled excerpts are direct problem evidence, not verified current outreach permission; all labeled source examples are marked `outreach_eligible: false`. The scorer is used only for problem diagnosis. No result is promoted to an actionable social lead.

The engine generates three distinct, zero-paid-cost experiment candidates: an existing AYANA-owned guide, a founder-owned LinkedIn post, and an opted-in diaspora partner contribution. The local ranking favors the guide because AYANA controls the asset and the direct NRI/parent-care problem is documented. LinkedIn audience ownership and qualified reach are unknown; no partner invitation is established. Reach is ordinal and uncertain, not a forecast. The guide recommendation is **conditional** on deployed status and measurement readiness. It does not authorize content creation or publication.

An action has a SHA-256 version over exact copy, destination, channel, experiment, and maximum cost. Preparing a new version clears approval. The local workflow requires a completed baseline before preparing an action, an explicit version-matched CEO approval record, and positive security, measurement, and channel-permission flags before it can emit a **manual-only** execution packet. Outcome recording also requires that packet to have been released for the current version. There is no posting, messaging, deployment, or payment adapter. The audit trail records decision, baseline, version, approval, packet release, and outcome events. Outcome snapshots preserve `null` for unknown visits, clicks, inquiries, founder time, and cost; no missing measure is silently converted to zero.

**Limit:** approval identity and preflight flags are supplied by local callers and are not independently authenticated. This is a local demonstration, not a production approval service. The audit list and demo JSON are local artifacts, not immutable server records. Before operational use, bind approval to authenticated CEO identity and store versioned records only after live database security and synchronization are verified.

## Reproduce

From the repository root with `requirements.txt` installed:

```powershell
python preflight_supabase.py
python demo_acquisition.py
python -m pytest -q --basetemp=data/pytest_tmp
```

Observed on 17 Oct 2026: preflight exits before network reads due to `gaierror`; demo writes `data/ayana_decision_local_demo.json`, reports three candidates/two positive research examples, and stops with no approval or action; final pytest run reports **28 passed in 3.70s**. The default pytest temp path was outside this workspace's write permission, so `--basetemp` is required here. The local demo file contains the assisted ranking and should be withheld from the founder until the manual baseline is complete.

## Smallest remaining prerequisites

1. In an environment with working network, run the read-only preflight. Inspect deployed `pg_policies`, table grants, and RLS state through privileged **read-only** SQL; confirm anonymous reads cannot access protected rows. Reconcile all cloud and local opportunities and cost rows before any production experiment storage. The script compares opportunities only and caps its cloud read at 1,000 rows; expand or paginate if needed.
2. Inspect the current Vercel deployment and Search Console account, including the three guide URLs, indexed status, impressions/clicks, and whether Vercel Analytics is active. Verify the backend beacon receives landing events in production. Do not change DNS based on this executor's failure.
3. For a guide experiment, make the smallest measurement change after review: record guide page view and CTA events with a bounded campaign ID, then carry that ID through signup or a voluntary inquiry. Do not add GA4 unless existing telemetry is insufficient. Define the qualified inquiry review process and confirm claims and parent consent language with the founder.
4. Complete the founder-only baseline first. After technical gates and exact content are prepared, seek separate CEO approval for the action version. The founder publishes manually if approved. Start the 28-day clock only when attributable visits, CTA clicks, qualified inquiries, active founder time, and actual vendor costs can all be captured.

## CEO acceptance judgment

**Technical preflight: partial pass. Local decision engine: pass as a demonstration. External pilot: HOLD.** The decision engine can compare permitted acquisition channels without inventing a customer lead, but current Supabase security, cloud/local consistency, guide deployment, and full attribution remain unverified. There is no evidence yet that FounderReach outperforms a founder's manual decision or produces a qualified inquiry. The next GO decision requires the listed gates and a completed 28-day measurement, not another passing test count.
