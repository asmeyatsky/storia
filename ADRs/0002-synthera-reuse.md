# ADR 0002 — Reuse SYNTHERA primitives, ship STORIA as a vertical

Status: Accepted (2026-05-12)
Resolves: PRD G2, OQ1

## Decision

STORIA is built as a vertical application on top of SYNTHERA™/SynapticBridge™ primitives, not a standalone platform. VAID provides agent identity and action provenance. CRUCIBLE™ gates model and prompt changes. SENTINEL™/CODEX™ provide audit and policy.

PMS integrations land via OAuth and official APIs; PMS-marketplace partnerships are a Phase-2 lever, not a v1 dependency.

## Rationale

- The Action Engine, audit log, and agent identity are already solved Labs primitives. Re-implementing them inside STORIA duplicates work and weakens both products.
- A vertical-on-platform shape creates an architectural moat smaller competitors cannot replicate.
- It keeps STORIA narrow: ingestion, identity resolution, guest profile, action playbooks. Everything else delegates.

## Consequence

- `services/storia-core/infrastructure/synthera/` wraps SYNTHERA's action and provenance APIs as adapters behind domain ports — STORIA's domain stays SDK-free.
- CRUCIBLE eval suites are mandatory CI gates for any LLM-touching change.
