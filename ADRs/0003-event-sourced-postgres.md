# ADR 0003 — Event-sourced Postgres, defer Spanner

Status: Accepted (2026-05-12)
Resolves: OQ2

## Decision

Primary store is regional Postgres on Cloud SQL with append-only `guest_event` ledger and a materialised `guest_profile` view. Per-tenant region pinning (`europe-west1`, `me-central1`, etc). Each operator's data is logically separable (schema-per-tenant) and supports physical separation when contractually required.

Spanner is deferred until a tenant requires multi-region active-active writes. The migration path is held open by keeping all writes go through the event-store port — no SQL in domain or application.

## Rationale

- Rules §1 names Postgres as primary. Spanner is a justified deviation only when multi-region writes are real.
- Event sourcing is required by PRD §6.2: any past state reconstructible, right-to-erasure via source tombstoning, inference re-runs.
- Schema-per-tenant gives single-tenant-shaped multi-tenancy (Rules §3, multi-tenancy = single-tenant-shaped) without the operational cost of physical separation by default.

## Consequence

- `storia.domain.ports.EventStore` is the only interface application code knows. Postgres lives behind it.
- ADR 0006 will revisit if a Middle East operator requires `me-central1` + `eu` synchronous writes.
