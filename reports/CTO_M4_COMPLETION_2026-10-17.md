# FounderReach AI — M4 local backend completion report

Date: 17 October 2026
Decision: M4 implemented locally; recommend **GO for a separately approved M5 design and local implementation**, with external release on HOLD.

## Scope and files

M4 adds `founderreach/m4/contracts.py`, `candidates.py`, `decision.py`, `gate_bridge.py`, `evaluation.py`, and `__init__.py`; `tests/test_m4_decision.py`; and `evals/m4_human_comparison.json`. This report and `README.md` document the work. M1–M3 implementation files were not edited for M4. The existing uncommitted tree was preserved before edits in `m4-preservation-2026-10-17/` (status, diff and selected source copies). No production migration, deployment, push, merge, UI work, outreach, or publication occurred.

## Architecture and data flow

Confirmed business profile → business-scoped M2 `EvidenceObservation` and optional M3 `ContentAnalysis` → source-supported `AcquisitionCandidate` records → current-evidence and permission eligibility → eight-dimension ordinal rank → one primary, up to three alternatives, or an honest empty result → local review packet. The optional bridge prepares an exact action in the **existing** M1 `DecisionRun` signed-approval and independent-preflight lifecycle. It creates no release route.

The common candidate has business and profile version, candidate and exact-action IDs, channel/action/scope/customer segment/target, supporting evidence with provenance and policy version where relevant, relevance/timeliness/permission, confidence basis and uncertainty, effort/cash cost/risk/reversibility, suggested metric, measurement readiness, and pending-review/unapproved state. `candidate_id` identifies the evidence-backed proposal; `action_id` covers the full exact candidate payload. Fixture candidates are explicitly marked.

Generation is channel-neutral but evidence-constrained. Owned website plans require a verified question and a linked M3 content opportunity; technical SEO, AEO answer, and GEO identity preparations require their specific findings. Owned social requires a current founder-confirmed account and planning permission. HN yields internal community research, never a reply. Media, newsletter, directory, and partnership candidates require actual business-scoped placement evidence and only propose internal permission research. Unsupported categories stay absent.

## Eligibility and ranking

Eligibility checks confirmed business/profile identity, current canonical candidate payload, matched and unexpired M2 verification, current source-registry version and allowed uses, unchanged M3 findings/opportunities, placement and owned-account state, known zero cash cost, allowed scope, and contradictory or unsupported answer findings. Research eligibility is separate from local preparation eligibility; external release eligibility is always false. Unknown or expired permissions fail closed. A source outage remains visible as `source_unavailable` if no candidate qualifies; it is not converted into a claim of no demand.

Only eligible candidates rank. The eight visible ordinal dimensions are customer fit, evidence strength, timeliness, feasibility, founder effort, cash cost, risk, and measurement readiness. Each contributes 0–2 points; the total is explanatory, not a conversion forecast or calibrated probability. Duplicate channel/action/target tuples are consolidated. The result explains the winner and alternatives, retains uncertainties and review requirements, and caps alternatives at three.

## Controlled backend demonstration and evidence-quality evaluation

All demonstrations use **fixtures**, not newly observed customer demand. ScheduleFlow's verified fixture question and owned-site content gap produce an owned-website primary. Adding a current founder-confirmed owned social account with tagged-visit measurement changes the primary to owned social. A conflicting owned-page claim blocks content preparation and leaves internal community research as primary. AYANA and ScheduleFlow are tested independently with distinct business-bound candidate identities. Unsupported media targets are not synthesized.

The CEO directly labeled the three controlled comparisons on 17 October 2026: A website, B social, C research. Those human labels are stored with explicit human provenance in `evals/m4_human_comparison.json`. Engine decisions match **3 of 3** labels; disagreements: **0**. This tiny, deliberately selected fixture set checks decision direction and does not estimate acquisition performance, general ranking accuracy, revenue, or conversions. No live outcome labels exist.

## Tests and security findings

Command: `python -m pytest -q --basetemp .pytest-m4-temp`
Result: **85 passed, 1 third-party `python_multipart` deprecation warning**. This includes the prior 70 tests and 15 new M4 tests. Cases cover tenant isolation, channel changes, observed placement, stale/blocked/changed policy, distinct research versus planning permission, unknown and positive costs, nonfinite costs, forged channel/copy, changed M3 evidence, expired owned access, duplicates, contradictions, outages/empty results, signed-gate replay/forgery, fixture blocking, network-free ranking, and human-label provenance.

Security boundary: M4 itself performs no network request, message, publication, or contact. It generates local plans and research only. The gate bridge re-runs the decision against current context before preparing an exact version, rejects fixture decisions and nonzero/unknown cost, and binds business/profile/candidate/action/copy/destination. M1 still requires CEO signature and independent preflight for a manual execution packet; edited copy changes its version. No parallel approval path or exposed route was added. Candidate evidence is input data and should be supplied only by trusted M2/M3 ingestion and confirmed founder records; M4 does not independently authenticate a caller that constructs its context in memory.

Source permissions: the current HN policy is rechecked for research and, for local content preparation, owned-content planning. HN permission does **not** authorize a community reply. Placement contact and publication remain prohibited. Founder attestation is kept distinct from source verification and cannot by itself qualify as verified demand. Current owned-social planning permission is distinct from publication permission. Expired or unknown policy removes action eligibility.

## Actual cost and remaining limits

New cash spend: **₹0**. Tests used local fixtures and existing dependencies; no paid API or service was used. M4 has no production state or migration. The rank is a transparent heuristic pending outcomes and calibrated review. Site evidence mode is supplied by a trusted upstream caller; fixtures are barred from the gate. Current source permission and observation freshness are checked at decision time, but the system has no recurring refresh, real attribution, or production approval journal. A zero-cost estimate is a local planning assertion, not a bill audit. External action remains disabled.

## M5 proposal — approval, attribution, and outcome learning

1. Add a durable, tenant-scoped approval journal containing exact action hash, signer role, expiry, evidence versions, revocation, and independent preflight record. Preserve one M1 signature verifier; require fresh evidence and policy rechecks immediately before any future release. Keep external execution disabled until a separate deployment and channel-specific permission decision.
2. Define a channel-neutral outcome event contract with business/action ID, source, event time, consent basis, attribution window, confidence, and correction/retraction lineage. Start with founder-entered or owned first-party observations only. Avoid tracking people or claiming causality from visits.
3. Add zero-spend measurement adapters for owned website and founder-controlled links, using local import or approved first-party exports. Model missing data, duplicate events, and unattributed outcomes explicitly. No paid analytics service.
4. Create an offline learning loop that compares planned metric versus observed event, records review decisions and failure reasons, and proposes rubric changes for human approval. Preserve the original decision version and do not self-modify weights from tiny samples.
5. Test tenant isolation, stale/revoked approvals, forged signatures, changed evidence, duplicate and late events, clock boundaries, zero-cost enforcement, and absence of network/external side effects. Stage behind local-only fixtures, then separately review production migration and deployment.

M5 is **not started**. UI and external channel execution remain deferred.
