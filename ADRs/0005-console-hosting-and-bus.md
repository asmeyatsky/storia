# ADR 0005 — Console on Cloud Run, single Pub/Sub bus with tenant routing

Status: Accepted (2026-05-12)
Resolves: OQ4, OQ5

## Decision

- Operator Console is served from Cloud Run (matches Rules §1 GCP defaults; no Vercel). Static assets from Cloud CDN.
- Event bus is a single Pub/Sub topic per **event family** (`guest.events`, `actions.queued`, `audit.entries`) with `tenant_id` as a routing attribute and per-tenant subscriptions. Filter subscriptions enforce tenant isolation at the bus layer.
- Per-tenant dedicated topics are introduced only on contractual data-residency or noisy-neighbour grounds.

## Rationale

- Self-hosting on the canonical stack keeps ops surface single (Rules §1, GCP only).
- Single bus + tenant routing is cheaper and simpler at pilot scale (1–4 operators). Per-tenant topic explosion is real cost overhead.
- Both shapes are hidden behind the `MessageBus` port — migration is a config change, not a code change.

## Consequence

- IAM: each tenant subscription bound to a tenant-scoped service account via Workload Identity.
- Multi-tenancy invariant (Rules §3): logical isolation in app layer, physical isolation available on request.
