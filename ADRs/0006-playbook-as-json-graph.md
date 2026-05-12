# ADR 0006 — Playbooks stored as JSON graph, edited visually

Status: Accepted (2026-05-12)
Resolves: OQ6

## Decision

Playbooks are stored as a versioned JSON graph (nodes = triggers/guards/actions; edges = ordering with explicit DAG semantics per Rules §3.6). Validated against a Pydantic + JSON Schema contract on every write. The visual editor reads and writes the same JSON graph — no separate YAML codegen layer.

## Rationale

- Single source of truth. Code-generated YAML drifts.
- DAG shape gives concurrency for free: independent branches execute in parallel (Rules §3.6).
- Pydantic on the way in, JSON Schema on the wire, lets typed clients (TS console) share the contract.

## Consequence

- `domain.playbook.Playbook.from_graph(...)` is the only constructor. Invariants (no cycles, every action reachable, every guardrail terminating) enforced at construction.
- Migration from one schema version to the next is a domain function, never a manual SQL.
