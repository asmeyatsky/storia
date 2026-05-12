# ADR 0007 — Data disposition on operator churn

Status: Accepted (2026-05-12)
Resolves: OQ7

## Decision

Every pilot LOI and MSA includes:

1. **Export within 7 days** of termination notice — full event ledger + materialised profile state delivered as gzipped JSONL into a customer-controlled GCS bucket.
2. **Deletion within 30 days** of export confirmation — tombstone all `guest_event` rows for the tenant; drop the tenant schema; cryptographic-erasure of per-tenant CMEK keys.
3. **Audit log of disposition** retained 7 years (compliance evidence), with all PII fields redacted.

The disposition flow is implemented as a domain use case (`OffboardTenant`) wired to an audit-emitting infrastructure adapter. No manual DBA work.

## Rationale

- IT/Data Officer (hostile persona) named this as a kill-switch concern.
- GDPR / POPIA / UAE PDPL all demand demonstrable deletion. Cryptographic erasure via per-tenant CMEK makes the proof tractable.

## Consequence

- Per-tenant CMEK keys provisioned at onboarding, rotated annually.
- Offboarding is reversible up to deletion confirmation (the export window) — protects against accidental termination.
