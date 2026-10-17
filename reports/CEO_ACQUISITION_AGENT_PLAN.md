# FounderReach AI — acquisition-agent plan for CEO review

**Pilot details revised by [CEO_CONDITIONAL_GO_PILOT.md](CEO_CONDITIONAL_GO_PILOT.md) after the conditional-GO directive.**

**17 October 2026 · Research and design only · No feature or paid-service activation**

## Decision requested

Approve or revise the *experiment design* before implementation. FounderReach should aim to help one solo founder choose and carry through one defensible acquisition action, then learn from its result. It should not become a generic social-listening dashboard. The current AYANA run has zero actionable outreach opportunities; its Precision@5 is N/A. The previous [independent audit](../INDEPENDENT_AUDIT.md) remains the evidence baseline.

## Product boundary

One founder supplies a product, audience, proof of what the product can do, constraints, and channels they own. FounderReach discovers demand signals, evaluates possible acquisition actions, recommends **one** with evidence and expected effort, waits for founder approval, guides or executes the approved action where permitted, and records outcomes. A zero-lead result may correctly select an owned-channel or partnership experiment rather than manufacturing a social reply.

The unit of value is a **completed, measured acquisition experiment**, not an alert, score, generated post, or autonomous agent run. This is a product hypothesis, not a validated differentiator.

## Lightweight architecture

```text
Founder profile + constraints
          ↓
One orchestrator (durable state machine and tool selection)
          ├─ Discovery tools: HN, permitted APIs, manual research import, owned analytics
          ├─ Evidence tools: URL/content/date checks, deduplication, intent and fit scoring
          ├─ Policy tools: source permission, channel rules, freshness, claims, budget
          ├─ Action tools: prepare approved content, guide founder in owned channel
          └─ Measurement tools: tagged traffic, qualified inquiries, founder feedback
          ↓
Supabase audit record → approval → action record → outcome → next recommendation
```

The orchestrator owns a single run state: `PROFILED → DEMAND_REVIEWED → ACTION_PROPOSED → AWAITING_APPROVAL → APPROVED → EXECUTED_OR_GUIDED → MEASURED → LEARNED`. It calls small tools through clear input/output contracts; there is no team of autonomous agents negotiating with each other. A language model may summarize or rank *evidence already collected*, but deterministic gates control source permission, verified quotes, dates, claims, spend, and whether an action can run. Every proposed action has an evidence link, reason for selection, permission basis, estimated cost, success measure, and stop condition. Execution requires a recorded founder approval for the exact action and channel. Retries must be idempotent.

**Reuse now:** `ProductProfile`, HN connector, verifier, intent/scorer, cost ledger, CLI, and local labeled evaluator. **Before a real cloud run:** verify live Supabase schema/RLS and credentials, compare Supabase and SQLite records, and avoid assuming current best-effort dual writes are consistent. The existing `opportunities` table can hold demand evidence and founder feedback. It does **not** represent approvals, actions, attribution, or outcomes; those are future data requirements, not features being added in this phase. For the manual pilot, keep an immutable experiment log alongside the report and reconcile its candidate IDs with Supabase once cloud access is verified.

## Discovery and action surface

| Surface | Evidence or action | Initial treatment |
| --- | --- | --- |
| Hacker News | Public dated discussions via [HN Algolia API](https://hn.algolia.com/api) | Existing connector; use as measured baseline, not presumed AYANA lead source. Outreach only after specific rule and human review. |
| Reddit | NRI and caregiver language has strong apparent audience fit | [Commercial Data API use needs a separate agreement](https://redditinc.com/policies/data-api-terms). Keep automated connector disabled; do not route around it with scraping. |
| YouTube | Relevant elder-care video comment threads | [Official API exposes comment threads and search terms](https://developers.google.com/youtube/data/reference/rest/v3/commentThreads/list). Candidate research path after API, quota, and use-case review; no key enabled now. |
| Search and AI search | Demand phrasing, competing answers, owned-site visibility | Manual search research initially. Use authorized [Search Console data for an owned site](https://developers.google.com/webmaster-tools/v1/searchanalytics/query) if AYANA grants access. Google says its [AI search features use ordinary SEO foundations](https://developers.google.com/search/docs/appearance/ai-features); do not promise separate “GEO” ranking. No automated scraping of search results or AI answers. |
| Directories | Category demand, reviews, founder-controlled listing | Manual review or owner submission. Do not assume APIs permit commercial use: [Product Hunt's API says commercial use requires contact](https://api.producthunt.com/v2/docs). |
| Partnerships | NRI associations, caregiver groups, clinics or service providers | Research public organizational information; founder approves each introduction. No automated messages. Measure referred qualified inquiries, not number of contacts. |
| Founder-owned channels | AYANA site, opt-in email, existing social accounts | Lowest permission friction for an approved helpful resource and attributed CTA. Use only channels AYANA controls and existing analytics/consent. |

**Selection rule:** choose the highest expected *qualified learning per rupee and founder hour* among permitted actions, with evidence quality and reversibility as gates. Source breadth is not a goal by itself. A public discussion can support a content experiment without becoming an outreach target.

## Competitive comparison and falsifiable differentiation hypothesis

| Product | Publicly described strength | Implication for FounderReach |
| --- | --- | --- |
| [F5Bot](https://f5bot.com/) | Keyword alerts for Reddit, HN, Lobsters | Alerts are commoditized. |
| [Syften](https://syften.com/) | Broad community/web coverage, AI filtering, API, webhooks, MCP | Multi-platform discovery and “AI agent compatible” are not differentiators. |
| [GummySearch](https://gummysearch.com/product/) | Reddit audience research, pain points, solution requests | Demand classification is not novel. Its [release log](https://gummysearch.com/releases/) says signups/payments closed in late 2025; verify current availability before a head-to-head purchase. |
| [Common Room](https://www.commonroom.io/product/ai/) | AI-assisted prospect research, prioritization, messaging, automated B2B outbound | Even signal-to-action automation exists. FounderReach cannot claim to invent that workflow. |

**Hypothesis:** Solo founders will prefer a smaller system that shows *why one permitted action is worth doing now*, obtains approval, and closes the loop with attributed qualified demand. This may differ from alerts and enterprise prospecting, but the distinction is **unproven**. Test against each founder's current method and at least one available competitor or manual alert baseline. Ask blinded reviewers to rate opportunity quality and compare time to an executed action, false positives, and attributable qualified inquiries. If FounderReach offers no meaningful improvement, reposition or stop; do not add more agents or connectors as a substitute for evidence.

## Smallest AYANA end-to-end experiment

**Question:** Can FounderReach turn verified demand about an adult child abroad supporting a parent alone in India into one founder-approved action that attracts a qualified inquiry?

**One action to propose:** a useful AYANA-owned resource titled provisionally “A practical check-in and safety plan for a parent living alone in India,” with a single honest AYANA CTA. The content must answer the actual caregiver question before mentioning the product and make no unverified safety or medical promises. Publish on an AYANA-controlled page, then share once through an AYANA-owned channel *if that channel and its audience already exist*. No reply to a Reddit or HN author is part of this pilot. The founder approves the exact copy, page, channel, and CTA before publication. If AYANA has no accessible owned page or measurable CTA, this experiment is **not ready**; the prerequisite is access, not a new FounderReach feature.

**Why select it:** The current HN pipeline has no actionable person to contact; Reddit shows clearer problem language but its commercial collection permissions are unresolved. An owned page permits an action without treating a public caregiver discussion as consent. Search/AI-search appearance is a possible later effect, not a promised short-term result.

**Manual runbook, using existing code and Supabase where verified:**

1. Freeze AYANA product claims and audience profile. Record three competing actions: HN reply (no qualifying candidate), Reddit reply (permission unresolved), and owned resource (permitted if AYANA controls the channel). Save decision reasons.
2. Run the existing discovery/evaluation commands and preserve raw queries, candidate IDs, exclusions, dates, and costs. Independently label a small random sample of accepted and rejected items. Sync/check the evidence rows in Supabase only after the audit's cloud/RLS blocker is resolved.
3. Prepare one resource and CTA from verified demand themes. Founder reviews the evidence and exact action; log approval or rejection. No publication occurs on inferred approval.
4. Founder publishes manually in AYANA's existing channel. Record the canonical URL, publish time, and distinct UTM link or equivalent attribution. No FounderReach posting integration is required.
5. Observe for **28 days**. Record page visits by source, CTA clicks, and inquiries whose stated situation matches the AYANA audience. Review inquiries manually; do not count generic traffic as customers. Record founder time and ₹ spend.
6. Recommend one next action from outcomes: repeat with another problem, change channel/message, or stop this route.

**Predeclared measures:** source coverage; labeled precision and recall with denominators; false positives/negatives; time from demand review to approved action; founder acceptance; 28-day qualified visits, CTA clicks, and qualified inquiries; cost per qualified inquiry. If visits are too few to assess conversion, report a distribution failure. If visits occur but no qualified inquiries, report a message/offer problem. A single inquiry is a feasibility signal, **not** proof of product-market fit. Success for this pilot is a fully traced approved action plus at least one attributable qualified inquiry; a stronger decision requires repeating with more founders/actions. Cost per verified opportunity remains N/A when its denominator is zero.

**Budget:** Use local code, free permitted reads, existing AYANA channels, and manual review. Planned paid spend **₹0**. The ₹500–₹600 figure is a ceiling target for a later approved test, not a quota to consume; absolute ceiling ₹1,000. No paid key, ad, tool subscription, or API activation without CEO approval and a vendor-side spending check. The application's local ledger is not proof of actual account charges.

## CEO review gates

1. Confirm AYANA controls a page/channel and can measure its CTA and qualified inquiries.
2. Confirm the product claims and who may approve publication.
3. Resolve Supabase cloud access, RLS, and SQLite divergence before treating cloud data as the experiment record.
4. Approve or revise the single action and its 28-day thresholds. Only then prepare implementation or publication work.
