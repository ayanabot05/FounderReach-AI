# FounderReach AI — blocker resolution and minimal patch proposal

**17 October 2026 · For CEO approval of a future patch only.** External pilot remains **HOLD**. This document makes no production change and authorizes no publishing, contact, paid activation, or Supabase policy change.

**Later status:** The CEO's 17 October owner-side check confirmed all three guides deployed with distinct titles, H1s, canonicals, HTML, sitemap entries, and mobile rendering. The CEO then authorized local-only attribution implementation. See [AYANA_LOCAL_ATTRIBUTION_ACCEPTANCE.md](AYANA_LOCAL_ATTRIBUTION_ACCEPTANCE.md) for the implemented local patch and tests; production deployment remains on HOLD.

## 1. Read-only Windows PowerShell checks

Run the following in a normal PowerShell window on the CEO's Windows machine. These commands do not change DNS or production configuration. They do not require API keys. Save the output if it will be reviewed, but do not include `.env` or credentials in screenshots or pasted logs.

```powershell
$targets = @('xsumvcqeqknshjwdnypy.supabase.co', 'www.ayanabott.com', 'ayanabott.com')
foreach ($targetHost in $targets) {
  "=== $targetHost ==="
  Resolve-DnsName -Name $targetHost -Type A -ErrorAction Continue |
    Select-Object Name, Type, NameHost, IPAddress
  Resolve-DnsName -Name $targetHost -Type A -Server 1.1.1.1 -ErrorAction Continue |
    Select-Object Name, Type, NameHost, IPAddress
  Test-NetConnection -ComputerName $targetHost -Port 443 -InformationLevel Detailed |
    Select-Object ComputerName, RemoteAddress, TcpTestSucceeded, NameResolutionResults
}
```

The first resolver is the machine's configured DNS; the second is an independent public resolver. If both fail for the same host, check the domain's owner-side DNS and provider status manually. If only one fails, investigate resolver, VPN, firewall, or cache behavior before touching records. `Test-NetConnection` tests TCP 443, not RLS or application health. Public resolver queries may be blocked by a corporate network; such a failure is inconclusive.

```powershell
$urls = @(
  'https://xsumvcqeqknshjwdnypy.supabase.co/rest/v1/',
  'https://www.ayanabott.com/',
  'https://www.ayanabott.com/sitemap.xml'
)
foreach ($url in $urls) {
  try {
    $response = Invoke-WebRequest -Uri $url -Method Get -TimeoutSec 15 -MaximumRedirection 5 -UseBasicParsing -ErrorAction Stop
    [pscustomobject]@{ Url = $url; Status = [int]$response.StatusCode }
  } catch {
    $status = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { 'no HTTP response' }
    [pscustomobject]@{ Url = $url; Status = $status; ErrorType = $_.Exception.GetType().Name }
  }
}
```

Any HTTP response from the unauthenticated Supabase `/rest/v1/` endpoint demonstrates DNS, TLS, and HTTP reachability; a 401/404 alone does **not** indicate a broken project. This is not a table permission test. Do not add service keys to these commands or URLs.

To identify whether the **three existing guides** are actually live, use this read-only content check. A generic `200` is insufficient because a single-page-app fallback can return the homepage for an unknown path.

```powershell
$guides = @(
  @{ Path = 'whatsapp-check-ins-for-parents'; Heading = 'WhatsApp check-ins for parents who live far away' },
  @{ Path = 'medicine-reminders-for-parents'; Heading = 'Medicine reminders for parents on WhatsApp' },
  @{ Path = 'nri-parent-care'; Heading = 'Stay close to parents in India while living abroad' }
)
$sitemap = Invoke-WebRequest -Uri 'https://www.ayanabott.com/sitemap.xml' -TimeoutSec 15 -UseBasicParsing -ErrorAction Stop
foreach ($guide in $guides) {
  $url = 'https://www.ayanabott.com/' + $guide.Path
  try {
    $page = Invoke-WebRequest -Uri $url -TimeoutSec 15 -UseBasicParsing -ErrorAction Stop
    [pscustomobject]@{
      Url = $url
      Status = [int]$page.StatusCode
      ListedInSitemap = $sitemap.Content.Contains($url)
      GuideSpecificHtml = $page.Content.Contains('AYANA family guide') -and $page.Content.Contains($guide.Heading)
    }
  } catch {
    [pscustomobject]@{ Url = $url; Status = 'unreachable'; ListedInSitemap = $sitemap.Content.Contains($url); GuideSpecificHtml = $false }
  }
}
```

The `GuideSpecificHtml` check is conservative and can be false even for a deployed React guide because its `AYANA family guide` marker may appear only after JavaScript runs. Use the more discriminating read-only `check_ayana_guides_readonly.ps1` script to compare each page's distinct title, H1, canonical URL, and HTML hash with the homepage. Also inspect Vercel's production deployment commit and routes, then Search Console URL Inspection for each exact `www` URL. Search Console indexing is a separate question from deployment. The 12 October owner audit said these guides were local and undeployed then. This executor's DNS and browser access both returned `ERR_NAME_NOT_RESOLVED` on 17 October, so their **current** deployment remains unknown. Do not propose new guide copy until this check is complete.

After DNS succeeds, the existing read-only repository script can check anonymous table reads and compare up to 1,000 cloud opportunity rows with local SQLite:

```powershell
Set-Location 'C:\Users\gunak\Downloads\founderreach.ai'
python preflight_supabase.py
```

Its result is **not** a full RLS or cost reconciliation. It does not prove deployed policy definitions, test writes, paginate beyond 1,000 rows, or compare all tables. Do not use a service key in the browser or frontend. A privileged operator should inspect deployed policy and grant metadata through a read-only SQL session using the queries below; review the result without copying secrets:

```sql
SELECT n.nspname, c.relname, c.relrowsecurity, c.relforcerowsecurity
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relname IN ('opportunities','cost_ledger','cache','content_hashes')
ORDER BY c.relname;

SELECT schemaname, tablename, policyname, roles, cmd, qual, with_check
FROM pg_policies
WHERE schemaname = 'public' AND tablename IN ('opportunities','cost_ledger','cache','content_hashes')
ORDER BY tablename, policyname;

SELECT table_name, grantee, privilege_type
FROM information_schema.role_table_grants
WHERE table_schema = 'public' AND table_name IN ('opportunities','cost_ledger','cache','content_hashes')
ORDER BY table_name, grantee, privilege_type;

SELECT c.relname,
       has_table_privilege('anon', c.oid, 'SELECT') AS anon_select,
       has_table_privilege('anon', c.oid, 'INSERT') AS anon_insert,
       has_table_privilege('authenticated', c.oid, 'SELECT') AS authenticated_select,
       has_table_privilege('authenticated', c.oid, 'INSERT') AS authenticated_insert
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relname IN ('opportunities','cost_ledger','cache','content_hashes')
ORDER BY c.relname;
```

These are `SELECT` statements only. Compare live results with `supabase_schema.sql`; the local file is **not** proof of deployment. A separate anonymous-client read should return 401/403 or no protected rows. Do not test anonymous writes against production merely to prove a negative; use a disposable staging table/project if a write-denial test is needed.

## 2. AYANA analytics audit and smallest change

**Present in source:** `@vercel/analytics/react` is mounted in `frontend/src/App.js`. `frontend/src/lib/analytics.js` creates a per-tab session ID, records best-effort local events, and sends page/CTA beacons to `backend/server.py:/api/analytics/event`. It stores only a small source allowlist or `other`, not raw referrers or query strings. The backend validates event fields and meta keys, stores events for 90 days, and the admin-only summary in `backend/services/growth_analytics.py` counts landing sessions and CTA sessions. The sink also stores IP and user agent; any privacy review must include that existing practice. Live receipt, Vercel Analytics activation, and Search Console current data are unverified.

**Gap:** `frontend/src/pages/GuidePage.jsx` emits neither a page-view event nor a guide CTA event. `frontend/src/pages/Signup.js` sends no acquisition/session data and emits no success event. `backend/services/growth_analytics.py` filters to the landing route and aggregates signup cohorts separately, explicitly without identity linking. Thus guide → CTA → signup cannot be measured with current data. There is no verified contact/WhatsApp inquiry event or source attribution.

**Proposed patch, after CEO approval and deployment check:**

1. In `GuidePage.jsx`, call existing `trackPageView('guide')` once per valid guide slug and call `trackEvent('cta_click', {id: 'guide-primary', guide: <allowlisted slug>})` before the existing signup link navigates. Use the route's exact slug from `seoGuides.json`, not a raw URL.
2. In `backend/models.py:AnalyticsEventInput`, add only a bounded `guide` metadata field with an allowlist of the three known guide slugs; keep current source allowlist and 90-day retention. Keep event ingestion best-effort, and do not put email, phone, parent data, raw referrers, or full query strings in event metadata.
3. Measure signup completion with the same anonymous session ID. Expose a narrow read-only session-token accessor from `analytics.js` and pass it as an optional, length-bounded field in `RegisterInput`. Prefer a backend-recorded `signup_completed` event in the existing registration transaction, **without storing user ID in analytics**, if privacy review accepts this. A frontend success beacon is a smaller code change but can be lost on navigation, so it is weaker for a 28-day decision. Do not call a signup a qualified inquiry.
4. Extend the existing admin-only aggregate query to count distinct guide view → guide CTA → signup-completed sessions in temporal order, plus direct/unknown. Restrict the result to counts and suppress very small cohorts if a privacy review requires it. Preserve the existing landing summary unchanged. Test route changes, duplicate events, missing beacons, direct traffic, spoofed or invalid guide slugs, and opt-out/consent behavior as applicable.
5. For **qualified inquiries**, first identify an existing voluntary intake route and founder review process. If none exists, propose a separate small consented inquiry capture with the same bounded campaign ID in a later review. A signup event alone cannot establish AYANA fit or a real customer need. The 28-day pilot cannot start until this measure is defined and verified.

No GA4 installation is justified by the current audit. The proposed session funnel estimates attribution; it does not prove causal acquisition or unique people across tabs/devices.

## 3. Authenticated approval and independent gates

The prototype `founderreach/acquisition.py` accepts a caller-supplied `Approval(approver=...)` and three Boolean preflight flags. These are useful **test fixtures only**. Any caller can forge them. The local JSON audit is editable. They must not authorize a real action.

**Minimal production design for later approval:**

1. Use an existing trusted identity provider if one is available. The backend verifies the signed access token against the provider's current issuer, audience, signature/JWKS, expiry, and stable subject. The configured CEO subject is stored server-side; role or email supplied in the request body is ignored. Require recent authentication and MFA if the provider supports it. If no suitable auth exists, treat that as a blocker rather than replacing identity with a shared secret or name field.
2. Canonicalize and hash the entire proposed action: exact copy, claims, URL and destination host, channel, distribution scope, experiment ID, amount/currency, and expiry. Show those fields to the authenticated CEO. Record approval for that digest only, with actor subject, timestamp, auth context, and an append-only audit event. Any edit generates a new digest and invalidates approval. Prevent replay with one-time state transition and idempotency key.
3. Replace caller-supplied security/measurement/permission Booleans with **server-produced evidence records**. A read-only verifier collects deployed RLS/grants, anonymous read outcome, cloud/local reconciliation, live guide and event checks, and channel ownership evidence. Store checksums, observed values, source, verifier version, time, and short expiry. The release endpoint independently reevaluates required gates and rejects stale, failed, or missing evidence. The action packet remains manual-only.
4. Require a separate CEO approval for any paid cost or publication. Check current vendor billing and committed spend before a paid action; ₹500–₹600 remains a target and ₹1,000 a hard ceiling. Because external charges may bypass the app ledger, the ledger cannot alone enforce this ceiling.
5. Keep all keys server-side. Do not persist a new production experiment, approval, or audit event until live Supabase security and synchronization pass; use a local review artifact meanwhile. A future append-only production audit requires authenticated writes and restricted reads, not open table access.

## 4. Cloud/local reconciliation

`founderreach/db.py` constructs a Supabase client without probing connectivity. `save_opportunity()` tries a cloud upsert, then always writes SQLite; on cloud failure it logs a warning and writes SQLite. `get_opportunities()` prefers cloud when reachable, which can hide local-only records. Feedback and costs are also best-effort dual writes. `get_total_spend()` reads only SQLite, so it cannot see provider charges or cloud-only ledger entries. There is no delivery queue, common revision, conflict policy, or repair log. This is **two stores with possible divergence**, not a synchronized primary/replica pair.

**Safe plan:** First take read-only snapshots of counts and stable IDs from both stores, including opportunities, feedback, cost ledger, and content hashes. Compare critical fields and timestamps; produce `cloud_only`, `local_only`, and `conflict` lists without automatically overwriting either side. Independently compare billing invoices/usage with both ledgers. Freeze production experiment writes during ambiguity. After CEO reviews conflicts, choose the authoritative record for each ID and record a reconciliation decision. For later implementation, add a durable outbox with stable operation IDs, versions, retry state, idempotent cloud writes, and explicit `pending/synced/conflict` status. Never call client construction or a successful local write “Supabase synced.” No automatic replay or migration is proposed now.

## Blocker-resolution checklist

| Check | Pass evidence | Current state |
| --- | --- | --- |
| CEO machine DNS and HTTPS | Resolver outputs, TCP 443, HTTP status for Supabase and AYANA | Pending owner-side commands; sandbox DNS failed |
| Existing guide deployment | Live distinct guide HTML + Vercel production commit + exact Search Console URL status | Unknown; 12 Oct report said undeployed |
| Supabase RLS/grants | Read-only live SQL and anonymous read show protected tables inaccessible | Unknown; local SQL is insufficient |
| Cloud/local records | Full paginated ID/field comparison and reviewed conflicts | Unknown; local 12 research rows only |
| Existing analytics delivery | Production guide/landing beacon receipt and admin aggregates | Source implementation verified, deployment unknown |
| Guide attribution | Guide view, CTA, signup path counted by anonymous session | Missing in source; patch proposed only |
| Qualified inquiry | Voluntary contact and manual qualification with campaign evidence | Missing/unverified |
| CEO approval | Backend-authenticated stable subject, exact digest, append-only audit, fresh independent gates | Prototype accepts forgeable inputs; patch proposed only |
| Actual cost | Vendor statements plus ledgers reconciled | Local ledger ₹0; vendor bills unknown |

**Decision:** approve only the narrow code patch after the CEO has reviewed this design and the live preflight evidence. Keep the external pilot on HOLD until deployment, security, attribution, inquiry measurement, and authenticated approval are independently verified.
