# What FounderReach will and will not do for clients

This document defines the permanent, non-negotiable client boundary rules for FounderReach AI.

## Permanent Product Rule

FounderReach **never** touches a client's repository, hosting, deployment, database, or credentials, and **never** pushes, merges, or deploys anything for a client.

---

## 1. What FounderReach WILL do for clients

1. **Run locally in read-only review mode (`client-review`):**
   - Accept a founder-confirmed business profile (`ProductProfile`, confirmed interactively via `CONFIRM` as a self-declaration).
   - Optionally accept up to 10 minimized, founder-attested customer questions or complaints (`--attestations`), checked for personal-identifier minimization (`require_minimized_text`) and labeled `founder-attested` (never treated as independently verified demand).
2. **Inspect website pages only within an explicit, bounded permission scope:**
   - **Offline fixture mode (default):** Analyze only local HTML, `robots.txt`, and `sitemap.xml` fixture responses (`--fixtures`) that match the exact approved origin and URL list in `--permission`.
   - **Bounded live HTTPS mode (`--live-site`):** Perform only unauthenticated HTTP `GET` requests over HTTPS (`port 443`, `Accept-Encoding: identity`, no cookies or auth headers) to URLs explicitly listed in `permission.approved_pages` after verifying `robots.txt` first, enforcing DNS/IP SSRF blocks and pinning the verified public IP.
3. **Use ephemeral in-memory storage during `client-review`:**
   - Process M1–M4 review state in `:memory:` SQLite (`_MemoryResearchStore`) without creating or mutating any durable database file.
4. **Emit a single new local Markdown report file (`--report`):**
   - Write the review output only to a brand-new local `.md` file using exclusive creation (`open("x")`), never overwriting existing files.
5. **Present technical fixes strictly as copyable suggestions for the client to apply:**
   - Every site, AEO, or GEO fix in Section 1 is labeled as a **suggestion** with copyable text (`Suggestion (copyable text for client to apply; never applied by FounderReach)`) so the client or their engineering team can review and apply it themselves.
6. **Keep M4 acquisition decisions honest (`none yet` without verified demand):**
   - Section 2 applies the unchanged M4 decision rules (`no_eligible_action` / `Primary recommendation: none yet.`) whenever independently verified demand evidence is absent, and lists the exact evidence still missing.

---

## 2. What FounderReach WILL NOT do for clients

1. **No repository or source-control access:**
   - FounderReach never clones, reads, edits, stages, commits, branches, tags, pushes, or merges in a client's Git repository, GitHub, GitLab, or Bitbucket account.
2. **No hosting, infrastructure, or deployment access:**
   - FounderReach never connects to, configures, or triggers deployments on a client's hosting or cloud platform (including Vercel, Railway, Render, Netlify, Cloudflare, AWS, GCP, Azure, or any CI/CD pipeline).
3. **No client database access:**
   - FounderReach never connects to, queries, migrates, or writes to a client's database (including Supabase, PostgreSQL, MySQL, MongoDB, Firebase, or Redis).
4. **No client credentials or `.env` access:**
   - FounderReach never asks for, reads, loads, stores, or transmits client `.env` files, API keys, database connection strings, OAuth tokens, SSH keys, cookies, or session headers.
5. **No automatic code, CMS, or site mutations:**
   - FounderReach never applies fixes directly to a client's website, CMS, DNS, `robots.txt`, `sitemap.xml`, or HTML templates, and never sends `POST`, `PUT`, `PATCH`, or `DELETE` requests to a client origin.
6. **No unapproved crawling, outreach, publishing, or spending:**
   - FounderReach never crawls links outside `permission.approved_pages`, never bypasses `robots.txt`, never publishes content or sends outreach messages on a client's behalf, and never incurs external paid API spend during a client review (`₹0`).
