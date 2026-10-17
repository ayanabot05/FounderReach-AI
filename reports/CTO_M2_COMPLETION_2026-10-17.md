# FounderReach AI — M2 local completion report

Date: 17 October 2026. Scope: local code and isolated tests. M3 through M6 remain on hold.

## Result

M2's evidence contract and first source connector are implemented locally. The evidence pipeline distinguishes what the source says, whether it was independently verified, whether it is timely demand, whether it fits the business, and whether a use is permitted. A source outage is surfaced as `DiscoveryUnavailable` or a partial run, not interpreted as an absence of demand. No collection job, external action, production migration, deployment, push, or merge was performed.

## Files changed for M2

| File | Change |
| --- | --- |
| `founderreach/evidence.py` | New source-independent observation, independent decision states, stable business-scoped ID, founder attestation factory. |
| `founderreach/source_registry.py`; `source_registry/hackernews.v1.json` | Versioned source permission record, review expiry, use restrictions, request and retention budgets. |
| `founderreach/connectors/hackernews.py` | Date-window Algolia retrieval, page-first query fairness, deduplication, bounded requests, explicit run diagnostics. |
| `founderreach/connectors/reddit.py` | Local environment flag cannot enable commercial Reddit collection. |
| `founderreach/validation/verifier.py`; `founderreach/models.py` | HN-specific exact-quote verification, 24-hour validity, explicit mismatch/not-found/rate-limit/network/unsupported states; removed unbounded verification cache. |
| `founderreach/research_store.py` | Additive local tables for observations, query-run diagnostics, append-only review events, business-scoped reads, retention pruning. |
| `founderreach/placements.py` | Evidence-backed research-stage media, newsletter, directory, and partnership model. |
| `founderreach/engine.py` | Normalized observation creation alongside existing opportunities; independent classification, freshness, permission and verification; outage propagation and query logging. |
| `tests/test_m2_evidence.py`; `README.md` | M2 regression, failure, isolation and documentation. |

The pre-existing M1 working tree was copied into `m2-preservation-2026-10-17/` before edits. M1 changes were retained. No files in that preservation copy were used for test collection.

## Data flow and interface

1. A confirmed business profile supplies distinct query terms and business identity.
2. The HN connector checks the current version of the source policy, searches a timezone-aware date window through `/search_by_date`, cycles through all selected queries before deeper pages, and emits a `DiscoveryBatch` with page diagnostics. It keeps one native HN ID per run.
3. The engine scores and classifies discussions using the existing profile-driven logic. The HN-specific verifier independently checks the HN page and full quote. It returns an explicit failure state and a short expiry for a successful check.
4. The engine emits `EvidenceObservation` with business/source identity, claim, excerpt, URL, provenance, publication and observation times, verification method and expiry, relevance, freshness, permission, review state and future routes. The `CustomerOpportunity` remains a compatibility view. Research and owned content routes are advisory only.
5. An explicitly supplied local `ResearchStore` can persist observations and query diagnostics. `record_review` appends an audit event and changes only review state. Founder attestation stays `attested` even after confirmation; human review cannot make it source-verified.
6. Placement opportunities can be created only from a relevant, currently independently verified `placement_opportunity` observation with a matching target URL; the stage remains `research_only` and contact permission remains unknown.

`EvidenceObservation` is the M3/M4 input contract. Channel engines should consume its `may_support`, freshness, relevance, provenance, policy version and routes, then apply their own content quality and signed approval gates. They must never treat `ACTIONABLE_OPPORTUNITY` as action authorization.

## Tests and evidence-quality evaluation

Run from the repository root: `python -m pytest -q --basetemp .pytest-m2-temp`. Result: **51 passed**, one third-party `python_multipart` deprecation warning. All 39 original tests passed; 12 M2 tests passed. `git diff --check` found no whitespace errors. Tests use stubbed HN HTTP responses and local SQLite; no live HN collection was used to assert quality.

The fixture evaluation separates: exact verified quote; missing quote; 404; network timeout; stale verification; founder attestation; uncertain relevance; blocked or expired permission; old evergreen discussion; partial HN failure; total HN failure; successful empty retrieval; AYANA and ScheduleFlow with the same source URL. No fixture claims measured live precision, recall, demand volume or acquisition success. This is a contract and failure-behavior evaluation, not a field validation of customer demand.

## Source permission and security review

The reviewed HN registry permits `research` and `owned_content_planning` only. It has a 17 November 2026 re-review deadline, 365-day local retention, and local budgets of 60 requests/hour, five queries/run and three pages/query. It records HN guidelines and Algolia API documentation separately. These documents do not grant outreach permission; the local policy is a conservative operating rule, not a legal determination of every commercial use. Unknown or expired policy blocks HN collection and external uses; HN posting and automated comments are not enabled. The request budget is in-memory per connector instance, so process-wide or distributed collection would need a stronger limiter before any production use.

HN discovery is locked to the documented HTTPS Algolia endpoint. Verification accepts only HTTPS HN item pages and rejects cross-host redirects. The full normalized quote must be present. An expired verification is stale; an empty successful query is distinguishable from unavailable or partial source results. Tenant keys scope observations, review events and query runs; cross-business reads and review attempts are tested. The local retention sweep removes expired HN observations, associated review events, query logs and compatibility opportunities when the store is used. No production migration is included.

The M1 legacy and unsigned approval paths remain blocked. Normalized routes and placement models cannot publish, contact, or approve. Reddit stays disabled even if `REDDIT_ENABLED` is set. There is no source-verified promotion for founder attestation. Review state cannot be overwritten through ordinary observation saving; it changes through an audit event. Model constructors are internal Python code, not an authenticated ingestion API; production trust boundaries and reviewer identity remain to be designed.

## Actual cost and limitations

New cash spend: **₹0**. No paid API or new service/dependency was added. No live source calls, recurring job, outreach or publication was executed as part of evaluation. Local execution cost only.

Remaining limits: HN is the only active connector; coverage is capped by query terms and pages; the request counter is per connector process; the registry needs scheduled policy re-review before use after its deadline; verification is HN HTML exact-quote and may fail closed if HN changes rendering; source-specific media/newsletter/directory/partner collection and independent verification are not implemented; no real-world relevance precision has been measured; review has no authenticated API or UI; local SQLite is not a production tenant database. These limits prevent a claim that the full acquisition agent is complete.

## M3 SEO/AEO/GEO recommendation — proposal only

**Recommendation: GO for a separate, gated M3 local implementation after CEO approval.** Keep UI deferred. Build an owned-content decision engine over `EvidenceObservation`, not a content production conveyor belt.

1. Define a `ContentOpportunity` contract containing business/profile version, one or more observation IDs, target audience and market, search or answer intent, proposed page or FAQ type, claim-to-source map, freshness, source policy snapshot, quality score, and review status. Require at least one usable traceable observation; label attested input separately. A source failure must not lower estimated demand to zero.
2. Add a deterministic clustering pass that groups evidence by the underlying question or task, not by repeated keywords. Keep a per-business canonical topic key, deduplicate URLs and claims, and distinguish new pages from updates to existing owned pages.
3. Add a read-only owned-site inventory and technical audit for existing URLs, titles, headings, canonical tags, robots directives, sitemap entries and structured data. Use local files or explicitly approved public owned URLs only; do not create a broad crawler. Flag crawl/indexability issues separately from topic demand.
4. Build three recommendation views from the same evidence: SEO page/update candidates; AEO concise answer and FAQ candidates with direct source attribution; GEO entity/fact consistency candidates with claim provenance. Do not assert ranking, citation, or AI answer placement without independent measurement.
5. Add claim validation before drafting: citation availability, expiry, contradictory evidence, sensitive or regulated claims, unsupported statistics, and permission. Drafts stay local with visible evidence links and founder review; no publishing endpoint.
6. Add evaluation fixtures for two businesses, shared URLs, stale/attested/uncertain/blocked evidence, contradictory claims, source outage, duplicate topics, low-quality keyword match and page cannibalization. Measure evidence coverage, unsupported-claim rate, cluster purity and reviewer acceptance on a fixed labeled set before broadening discovery.
7. Integrate only through the M1 signed gate when a later milestone authorizes publication. M3 output should be `research_only` or `draft_for_review`; deployment and content publication remain separate approvals.

Estimated local M3 engineering effort: 5–8 focused development days plus 1–2 days of fixture labeling and evaluation, subject to owned-site access and founder review capacity. Incremental cash budget can remain ₹0 using existing runtime and local tests. Dependencies: confirmed profiles, stable owned-site URL inventory, source policy review, a small founder-labeled evidence set, and agreement on claims requiring manual review. M4 can consume the resulting channel-neutral candidate and evidence graph; neither M3 nor M4 should depend on an HN-specific model.
