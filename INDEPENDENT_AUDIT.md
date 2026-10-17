# FounderReach AI independent audit — 17 October 2026

## Decision: PIVOT discovery channel; do not start outreach

The current Hacker News sample produced **zero verified actionable opportunities**. Precision@5 is **N/A**, not 100%, because there are no positive predictions. The earlier 80% cannot be reproduced: `reports/EVALUATION_DATASET.json` contains 12 research records, no documented human labels, and no dated actionable result. AYANA's customer need is plausible, but this pipeline has not demonstrated timely customer discovery. Keep the strict 90-day gate and seek better audience sources with explicit access permission.

## Reproduce the checks

From the repository root, with Python dependencies in `requirements.txt` installed:

```powershell
python -m pytest -q
python evaluate_independent.py
```

On 17 October 2026, the original suite returned **20 passed**. After focused fixes and three new checks, it returned **23 passed**. The original tests exercise scoring, helper functions, budget arithmetic, and two named HN regressions. They do **not** establish live source authenticity, end-to-end precision, recall, cloud consistency, RLS, or external billing. The purported positive regression is a constructed sentence and checks only direct intent and freshness, not full engine acceptance.

The independent six-record challenge in `reports/INDEPENDENT_LABELS.json` uses short excerpts from two public caregiver discussions and four negative discussions. Labels were assigned from the public text before measuring the updated classifier. `evaluate_independent.py` reports **TP 2, FP 0, FN 0, TN 4; text-intent precision 2/2 and recall 2/2**. These rates have very wide uncertainty and are **not** live opportunity metrics. The first run exposed one false negative on a caregiver medication question; the narrow punctuation and plural-word fix raised recall from 1/2 to 2/2 without changing these four negative outcomes. The sample is small and partly selected to challenge known failures; it is not a representative prevalence sample.

## Discovery and opportunity quality

| Measure | Independently supportable result |
| --- | --- |
| Production actionable Precision@5 | **N/A**, 0 predicted actionable |
| Historical “80% Precision@5” | Not reproducible; no dated human label file or five qualifying predictions |
| Production recall | **N/A**; no complete human-labeled sample of the production search results |
| Six-record text-intent challenge | Precision 2/2; recall 2/2; FP 0; FN 0 |
| End-to-end source coverage on challenge | Hacker News enabled, Reddit disabled; neither positive can be discovered by the enabled connector |
| Existing SQLite records | 12 `RESEARCH_INSIGHT`, 0 actionable; all 12 have null discussion dates in the legacy evaluation JSON |
| Rejected **solely** because of age | **0 demonstrable** in the 12-record snapshot; age-only status cannot be computed for records with missing dates and unverified intent |
| Cost per verified actionable opportunity | **N/A**, denominator 0; local ledger 0 entries and ₹0 recorded |

The 12 URLs are plausible HN item links, but a prior `SOURCE_VERIFIED` flag is not independent evidence. I could inspect the live [HN telephony-agent item](https://news.ycombinator.com/item?id=44858694); it is a founder soliciting feedback on a competing tool, not an AYANA prospect. The [NRI parent-living-alone discussion](https://www.reddit.com/r/nri/comments/1uwnjxf/parent_living_alone_in_india_tips_to_make_life/) is a much clearer first-person request for practical help. The [caregiver medication discussion](https://www.reddit.com/r/caregivers/comments/1iaye25/struggling_to_manage_my_parents/) likewise asks for apps and systems, but is historical. Public search and page rendering are evidence of textual relevance, not permission for commercial collection or outreach. I could not independently recheck all 12 HN links or their timestamps in this environment.

The existing `eval_discovery.py` ignores source `created_at`, so it cannot evaluate freshness; it also creates suggested responses for research records. The main HN connector does parse `created_at`, but uses relevance-sorted search and stops at a result limit before testing later queries. The [HN Algolia API](https://hn.algolia.com/api) supports date-sorted search and timestamp filters. A future channel experiment should use a fixed time window, record every queried URL and disposition, then have humans label a random sample including rejections. Keep the score threshold and 90-day outreach gate unchanged.

## Confirmed bugs corrected

- Research and irrelevant records no longer retain generated outreach drafts in the model, engine, legacy JSON, or local SQLite. UI/API response exposure is gated on source, intent, classification, and freshness. Human approval and platform rules remain necessary for any draft.
- `--no-verify` no longer calls an unverified URL `SOURCE_VERIFIED` or allows an actionable classification.
- The verifier now requires an exact normalized excerpt of at least 30 characters from the HN page. Its old 70% scattered-keyword fallback could certify an unrelated quote. Verification cache keys are deterministic and versioned. It rejects unsupported hosts and empty excerpts.
- Stored actionable rows are freshness-gated when loaded into the engine. The web endpoint also checks freshness before display.
- Intent matching now requires personal, parent-related care context. The challenge found and fixed a medication false negative; known HN child-care venting and founder-product examples remain negative.
- The server now binds to localhost. `.gitignore` excludes `.env` and SQLite; the configured cloud client no longer silently falls back to an anonymous key.
- `supabase_schema.sql` now includes fields used by current writes and removes the original public `FOR ALL USING (true)` policies. **This SQL has not been applied to the live project.**

## Database consistency and security

SQLite passed `PRAGMA integrity_check`, and contains 12 research rows. All 12 legacy nonactionable drafts were cleared locally. A Supabase client can be constructed from the local configuration, but a read-only cloud query failed with DNS `ConnectError [Errno 11001] getaddrinfo failed`. Therefore cloud connectivity, primary-database status, row equality, live RLS, and credential privileges remain **unverified**. The current implementation attempts cloud first and always writes SQLite; cloud failures can leave divergent data and cloud reads can hide local-only rows. There is no reconciliation queue, write acknowledgment, or transactional dual-write guarantee. It should be described as best-effort cloud plus local storage, not synchronized primary/fallback.

The local `.env` exists and has Supabase and Gemini variable names set; values were not printed. This directory is **not a Git repository**, so no Git history scan or assurance against prior exposure is possible. `.env.example` is a template. The old SQL explicitly granted public read/write across opportunities, cost ledger, cache, and hashes if installed; this is a critical potential exposure. Apply and verify the revised RLS and grants in Supabase, and rotate credentials if the permissive policy was deployed. Backend secrets must never be shipped to a frontend. The present static UI does not embed keys, but `/api/feedback` has no authentication and remains suitable only for trusted local use.

## Spend and clean-install limits

The SQLite cost ledger has **0 entries** and sums to ₹0. That proves only that this application has recorded no charges. The tracker uses a fixed exchange rate and an estimate before an optional LLM path; it does not reserve spend atomically, inspect vendor billing, or prevent charges made outside this app. Therefore **actual external spend and compliance with ₹500–₹600 / ₹1,000 cannot be certified** without the vendor billing pages. No paid API was activated during this audit. The README claims a one-command clean setup, but the cloud schema and credentials must be configured separately. `supabase` was absent from `requirements.txt` and has now been added; no clean-environment integration test was performed. A founder can reproduce the offline tests; live discovery remains environment and network dependent.

## Source plan and recommendation

HN is a poor **demonstrated** channel for AYANA: the available 12 records yielded no outreach lead and include old commentary, off-topic text, and a competing founder. That is a channel conclusion for this sample, not proof that HN can never work. Public [r/nri](https://www.reddit.com/r/nri/) and [r/caregivers](https://www.reddit.com/r/caregivers/) show stronger audience fit. [Reddit's Data API terms](https://redditinc.com/policies/data-api-terms) require a separate agreement for commercial API use, so the connector remains disabled. Community-specific Discourse forums could be evaluated one at a time after checking each site's rules and [rate limits](https://meta.discourse.org/t/available-settings-for-global-rate-limits-and-throttling/78612/1?tl=en-9); no blanket permission is assumed. Founder-approved manual research in relevant communities is a lower-risk next experiment. Record source terms, exact timestamps, human labels, and whether the person actually welcomes product discussion. Do not infer outreach consent from a public post.

**PIVOT** the discovery channel and validation study. **Do not GO** on customer acquisition or claim precision success until a prospective, dated, permission-compliant sample yields independently labeled timely positives, with measured end-to-end precision and recall. **Do not STOP** the product thesis solely from HN failure. No dashboards, posting automation, billing modules, or paid activation were added.
