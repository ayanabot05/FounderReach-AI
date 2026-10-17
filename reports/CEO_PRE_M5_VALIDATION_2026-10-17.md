# FounderReach AI — pre-M5 evidence validation and close-out

Date: 17 October 2026
Decision: **HOLD M5**. The product evidence gates are not met.

## What was established

The original tracked `HEAD` snapshot ran 29 tests successfully. The current tree ran 86 tests successfully with one third-party `python_multipart` deprecation warning. `evaluate_independent.py` produced the same six-row offline intent result before and after: 2 true positives, 0 false positives, 0 false negatives, and 4 true negatives. These six historical labels are not a blind live AYANA discovery evaluation. Review of changed tracked test files found profile-loading/API adaptations; the assertions in those four files were not relaxed. New M1–M4 tests are additional. The uncommitted state present before each milestone was preserved in the four preservation folders.

Preservation audit: the folders contain source copies, patches, status files, one `.env.example`, and two Python bytecode cache files. No live `.env`, database, private-key file, or known credential-format match was found in them by file inventory and targeted scan. This is a bounded scan, not a guarantee against all possible secrets. The folders are now Git-ignored and untracked. Generated local outputs and test directories are ignored. Previously tracked `data/pytest_tmp` fixture artifacts were removed from the Git index without deleting local copies. The reviewed baseline is committed locally in the close-out step; see Git `HEAD` for its hash.

## HN source review: live discovery held

The [current Y Combinator Terms of Use](https://www.ycombinator.com/legal/#tou) include restrictions on commercial exploitation and data extraction from the site. The [HN Search API documentation](https://hn.algolia.com/api) describes read-only search and a 10,000-request-per-hour service limit; API availability does not settle the separate rights and use restrictions. The [HN guidelines](https://news.ycombinator.com/newsguidelines.html) also prohibit automated posting and discourage promotional use. The CEO confirmed that FounderReach has no written rights-holder permission for its proposed commercial use.

The older `hackernews.v1.json` had marked research and owned-content planning approved without that review. `hackernews.v2.json` now supersedes it with `review_required`, no allowed uses, and zero request/query/page budgets. A local connector check returned `permission_blocked` with **zero network requests**. Network-free historical-policy tests are explicitly labeled as fixtures. No live AYANA HN collection occurred; verified yield, precision, false positives and exclusions are **unknown**, not zero. A human may review the policy, but cannot by internal sign-off alone grant rights that the provider has withheld. A future live run requires a documented permission basis, bounded scope, and then a separate independent labeling protocol.

HN also has an audience-fit risk for AYANA. If permission cannot be obtained, assess a different source with documented permitted uses and audience fit before collecting. Reddit commercial collection remains disabled. Do not treat a policy block as absence of customer demand.

## AYANA website validation attempt

The CEO reconfirmed `https://www.ayanabott.com/` as the correct owned origin. The existing read-only M3 `ApprovedSiteFetcher` was run with **one explicit approved page** (homepage), and its normal robots and sitemap checks. The DNS validation failed before any outbound request (`REQUEST_COUNT 0`); the web reader also could not access the origin. The auditor returned a partial state and generated `missing_sitemap` and `inaccessible_page` diagnostic findings. Those outputs are **not verified site defects** because no response was observed. There is no URL-by-URL SEO finding, AEO answer assessment, GEO entity finding, or AI-provider citation observation based on the real site. The next site validation needs a working DNS/network path to the confirmed origin, then a capped, founder-approved URL inventory and manual review of each observed finding. No ranking or visibility improvement is claimed.

## M4 real-evidence result

With no newly permitted HN observations and no readable site evidence, the real AYANA input has no eligible candidate. The M4 engine returned `source_unavailable`, `discovery_status=permission_blocked`, `primary=null`, and no alternatives. It explicitly retained the uncertainty that demand cannot be inferred absent. The earlier website/social/research winners and CEO's 3/3 labels remain **fixture evaluations**. The eight-dimension rubric is uncalibrated and there are no observed customer-acquisition outcomes. No synthetic candidate was promoted to a real recommendation.

## Privacy and retention

M2 `EvidenceObservation` omits HN usernames, but the connector's transient `DiscussionItem` includes `author`, and the legacy opportunity database schema can persist it. Exact excerpts may themselves contain personal details. M2 local retention pruning is applied on use, not by a recurring erasure job; legacy persistence requires separate review. The new held HN policy specifies 30 days if future collection is authorized, but no live collection occurred under it. Before any permitted live run: minimize or remove author identifiers at ingestion, redact unnecessary personal details from stored excerpts, define deletion behavior across local stores/backups and reports, and document who can access raw evidence. Do not copy raw live results into Git.

## Minimal first-party measurement design

Use a founder-controlled tagged link to an owned landing page only after separate publication approval. Locally record aggregate `visit`, `signup`, and founder-reviewed `qualified_inquiry` events with business/action ID, event time, source tag, consent basis, and deduplication key. Store no cross-site identity or third-party contact list. Report observed counts, missing instrumentation, and unattributed events separately; an unknown outcome is **unknown**, not zero. Establish a pre-action baseline and a fixed observation window before comparing actions. This design has not been implemented or deployed.

## Gate ledger and recommendation

| CEO gate | State |
| --- | --- |
| Preservation audit and Git ignore | Complete, bounded scan |
| Local baseline commit | Complete locally; no push |
| AYANA before/after snapshot and test-diff review | Complete for six offline labels and tracked test changes; no live effectiveness claim |
| HN human source-policy sign-off | Not granted; rights-holder permission absent |
| Permitted capped live AYANA discovery | Blocked by source policy |
| Independent review of actual discovery | Pending; no collection |
| Real AYANA SEO/AEO/GEO audit | Attempted; DNS failure prevented observations |
| M4 on real eligible candidates | Honest empty result; no eligible real candidate |
| Privacy and retention review | Documented, remediation remains |
| Minimal outcome measurement plan | Prepared, not implemented |
| Regression tests | 86 passing |

**Recommendation:** HOLD M5. Resolve the HN rights basis or select another compliant source, restore site access to the confirmed URL, and complete independently reviewed real evidence validation. Keep external execution disabled and preserve the ₹0 new-spend ceiling.
