# FounderReach AI — M3 local backend completion report

Date: 17 October 2026. M3 SEO, AEO and GEO analysis is implemented locally. M4 remains on hold pending separate CEO approval.

## Files changed

| File | Purpose |
| --- | --- |
| `founderreach/m3/site.py` | Explicit-origin safe fetch adapter, network-free fixture adapter, bounded inventory, HTML/XML parsing and SEO findings. |
| `founderreach/m3/aeo.py` | Customer-question clustering, page matching, direct-answer checks, FAQ suitability, contradiction and unsupported-answer screens. |
| `founderreach/m3/geo.py` | Organization/product extraction, identity and schema checks, external mention eligibility, fixed question sets, manual citation schema and local history. |
| `founderreach/m3/content.py` | M4-ready `ContentOpportunity`, claim and citation links, candidate deduplication, evidence coverage and unsupported-claim measures. |
| `founderreach/m3/pipeline.py`; `founderreach/m3/__init__.py` | One-business journey from M2 store through all three engines to review-ready output. |
| `tests/test_m3_engines.py` | Cross-business, valid/broken site, answer, conflict, outage, citation, security and evaluation fixtures. |
| `README.md` | M3 entry point and local-only constraints. |

The pre-M3 tracked diff, status and relevant source copies are in `m3-preservation-2026-10-17/`. Existing M1 and M2 files and controls were retained. No production migration was made.

## Demonstrated backend journey

The integration test `test_complete_careflow_journey_missing_answer_and_review_candidate` runs a confirmed CareFlow profile, a business-scoped verified M2 customer question, a network-free approved-origin site inventory, SEO findings, AEO missing-page finding, GEO readiness and unknown-visibility report, then one deduplicated `ContentOpportunity`. Its proposed action is `create_owned_page`; execution mode is `LOCAL_REVIEW_ONLY`, review state is `pending_human_review`, and the supporting observation ID is preserved. The test does not draft or publish a page.

The ScheduleFlow journey uses two observations with the same question and an existing page containing a direct answer. It produces one cluster and one `improve_owned_page` candidate with both observation IDs; no competing new page is proposed. Separate tests consolidate distinct intents assigned to one existing page. Stale/blocked evidence plus a source outage produces an empty candidate list with `source_unavailable`, rather than a no-demand claim.

## SEO capabilities and observed fixture results

The auditor fetches `robots.txt`, a same-origin XML sitemap and at most 20 explicitly listed pages. It checks robots restrictions; HTML and HTTP `noindex`; canonical alignment; sitemap omission; title and meta description; H1 structure; internal links and apparent orphans within the bounded inventory; JSON-LD syntax and basic keys; duplicate or competing content; and evidence-backed missing-page gaps. Every `SEOFinding` contains URL, observed evidence, problem, severity, correction, confidence, limits, effort and a verification method.

The broken ScheduleFlow fixture yields canonical, missing-sitemap, noindex and duplicate-content findings. Other fixtures yield robots-blocked, inaccessible page, orphan, missing metadata/H1, malformed JSON-LD, sitemap omission and HTTP-header noindex findings. A bounded inventory cannot establish Google indexing, ranking or the site's full crawl graph; orphan status is explicitly limited to observed pages.

## AEO capabilities and observed fixture results

The engine accepts verified M2 customer questions/needs and clearly labels founder-attested alternatives. It groups deterministic paraphrases by question intent, chooses an existing page where observed, checks for a substantive direct-answer paragraph, reports missing pages or missing direct answers, and assesses FAQ markup suitability only when a visible question and answer exist. It flags simple negation conflicts and strong unsupported answer claims for human review. Evidence count is not demand volume.

CareFlow's verified medicine-reminder question has no matching page in the bounded fixture and creates a missing-page finding. ScheduleFlow's appointment question matches a direct answer. A page with a matching heading but no substantive answer is flagged. A conflicting SMS-reminder statement and an unsupported guarantee are flagged. These rules are deterministic screens; they do not prove semantic correctness in arbitrary prose.

## GEO capabilities and observed fixture results

The engine extracts the founder-confirmed organization identity and observed organization/product entities from page titles and JSON-LD. It checks brand, About, contact and schema consistency; flags uncited strong claims; and accepts an external brand mention only with independent current verification and permitted research use. A fixed, versioned question set and local citation history store accept only explicitly modeled manual captures for questions in that set.

The inconsistent-brand fixture yields title and Organization schema mismatches. Missing independent external evidence is reported as unknown. Without supplied actual AI citation captures, `ai_visibility` is `unknown` and history is empty. Citation-history tests use **fixture-only records** to verify schema and tenant boundaries; they are not presented as real observations of an AI provider. GEO readiness does not imply AI recommendation or citation.

## Evidence-to-recommendation data flow

`ProductProfile` + tenant-scoped `EvidenceObservation` → explicit approved-site `SiteAudit` → SEO/AEO/GEO findings → deduplicated `ContentOpportunity`. The handoff includes business/profile version, observation IDs, existing URL or proposed topic, audience, question intent, claims, citation URLs and provenance labels, permission, freshness, confidence, effort, review status, suggested outcome metric and `LOCAL_REVIEW_ONLY` execution mode. Founder attestation can yield `research_only`; stale, blocked and irrelevant records cannot silently become content actions. No recommendation claims observed traffic, demand volume, ranking or AI visibility.

## Tests and evaluation

Command: `python -m pytest -q --basetemp .pytest-m3-temp` from the repository root. Result: **70 passed** (51 prior M1/M2 tests plus 19 M3 tests), one existing third-party `python_multipart` deprecation warning. `git diff --check` reported no whitespace errors.

Measured fixed-fixture outcomes: the CareFlow journey used 1/1 relevant supplied observation (`evidence_coverage=1.0`) and attached 1/1 independently verified claims (`unsupported_claim_rate=0`). A founder-attested alternative remains research-only and yields an unsupported-claim rate of 1.0 for publication-quality support. On the explicitly labeled broken-site target classes (canonical, noindex, missing sitemap, duplicate content, with robots-blocked as a negative class), classification precision, recall and F1 were each 1.0 **on that small deterministic fixture**. These numbers are not field precision, organic growth, citations or acquisition outcomes.

## Security and spending

No broad crawler exists. A live fetch requires an explicit HTTPS origin matching the confirmed profile and an explicit inventory. The production fetch path rejects IP-literal, private, loopback and reserved destinations through DNS checks, pins the connection to the checked IP, checks TLS against the hostname, blocks cross-origin redirects, accepts only bounded uncompressed responses and supported content types, and has request and time budgets. Loopback/reserved-host fixtures use only `FixtureSiteFetcher`, which makes no network requests. Tests cover unsafe redirects, loopback, oversized responses, timeouts, request budget, unsupported content and cross-business isolation. No live website was fetched during completion tests.

Actual new cash spend: **₹0**. No paid API, service or dependency, production database migration, deployment, external outreach, content publication, automated Git push or merge, UI, unauthorized collection, or recurring job was added.

## Remaining limitations

The page inventory is deliberately small and founder approved; unlisted pages may change conclusions. HTML parsing does not execute JavaScript, so client-rendered content may be missed. Robots handling covers the observed `robots.txt` and page directives but is not a search-engine simulator. Question clustering, answer detection and contradiction screens are rules requiring human review. Fixed AI questions and manual citation history have no automated provider collection; unknown visibility is the default. Local fixture scores are too small to establish general accuracy. Product ownership is represented by a confirmed profile and explicit origin input; production ownership proof, authenticated reviewers, centralized fetch budgets and production tenant boundaries remain future work. The full acquisition agent is not complete.

## Recommended M4 acquisition decision engine — proposal only

**Recommendation: conditional GO for a separately approved local M4 design and implementation.** Keep UI, execution and publication gated. M4 should consume `ContentOpportunity` alongside M1/M2 research and any later approved channel candidates through a channel-neutral `AcquisitionCandidate` contract. Each candidate should carry business/profile version, observed evidence and policy versions, proposed action, channel, expected outcome metric, effort, cash cost, reversibility, confidence, owner and approval state.

Decision stages: (1) reject cross-business, stale, unsupported or permission-blocked candidates; (2) collapse duplicate intent/page/channel actions; (3) score evidence quality, customer fit, timeliness, implementation effort and risk separately; (4) rank options within the explicit ₹0 spend ceiling; (5) produce an explanation and counterfactual reason for non-selected options; (6) require human review and the existing signed gate before any external action; (7) record decisions and actual outcomes without inventing impact. M4 evaluation should include two-business isolation, source outages, policy expiry, contradictory evidence, duplicate candidates, metric uncertainty, budget attempts and forged approvals. A small founder-labeled comparison set is needed before using rankings operationally. Do not auto-enable collection, outreach, publication or deployment as part of M4.
