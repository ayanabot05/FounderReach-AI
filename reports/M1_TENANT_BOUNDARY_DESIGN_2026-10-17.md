# M1 local tenant and database boundary design

Status: **design and local SQLite research store only**. No Supabase migration, production write, deployment, or permission expansion was made.

## Identity and ownership

- `business_id` is an immutable lowercase slug for the M1 file-profile workflow; display name is never an identity key. A production tenant ID should be an opaque database-generated identifier linked to a founder account. Do not reuse a local slug as proof of ownership.
- `profile_version` increments whenever founder-confirmed targeting or permissions change. Old evidence remains research, but any action must be rescored against the current profile.
- `source_id` combines source platform and native item ID. `opportunity_id` hashes the versioned business/source tuple. A URL is a provenance field, not a global uniqueness key.
- The local `research_evidence` primary key is `(business_id, source_id)`; `(business_id, original_url)` is unique. The same URL can be retained by unrelated businesses. Identity/URL conflicts fail rather than silently overwrite.

## Proposed production tables and policies — not applied

Use `businesses`, `business_memberships`, `profile_versions`, `source_observations`, `business_evidence`, `action_versions`, `approvals`, `manual_execution_events`, and `outcomes`. Every business-owned row carries a non-null opaque `business_id` with a foreign key. Each action references a frozen profile version and evidence snapshot. Source observations may be shared internally; business-specific classification and review must be separate rows. Keep an alias table for legacy opportunity IDs and source URLs; do not merge historical rows by blind upsert.

RLS must check authenticated membership for each operation and deny access when membership is absent. The server's service-role key is reserved for tightly scoped administrative jobs, never browser use. API handlers must derive account and business identity from a verified session and check membership before read or write. An action approval also requires the signed exact-version gate and independent preflight; a session or hash comparison alone is insufficient. Audit events should be append-only with actor, action digest, timestamp, and evidence references.

## Migration and release gates

1. Export and checksum existing Supabase and SQLite rows read-only. Review the documented same-URL/two-ID divergence.
2. Prepare a reviewed, reversible schema migration and a mapping of legacy IDs to canonical source/business identities. No inferred tenant ownership.
3. Test RLS with two real test users and two businesses in an isolated database: own access succeeds, cross-tenant access and unauthenticated access fail for every table and API path.
4. Test rollback, backup restore, duplicate aliases, partial writes, and credential rotation. Only after CEO approval should production migration or API exposure be considered.

The legacy FastAPI data endpoints now fail closed. The local self-service prototype has no module-level ASGI application and its unsigned approval and outcome methods fail closed. Its other routes remain a disposable prototype; they are not a production authentication system.
