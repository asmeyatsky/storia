# ADR 0001 — Hexagonal layering with mechanical enforcement

Status: Accepted (2026-05-12)
Resolves: Rules §2, §3.1, §3.2

## Decision

`domain ← application ← infrastructure`, `← presentation`. Domain imports nothing from infrastructure, presentation, or any third-party SDK (stdlib + typing only). Application imports only domain. Infrastructure implements domain ports. Presentation (FastAPI, MCP server) imports application use cases.

## Enforcement

- Python: `import-linter` config at `services/storia-core/.importlinter`. CI fails on contract violation.
- Rust: workspace split — `storia-events` (domain primitives, no I/O deps), connector crates depend on it but not vice versa. `cargo-deny` blocks reverse deps.
- TypeScript: `eslint-plugin-boundaries` in `console/.eslintrc.cjs`.

## Consequence

PMS clients, HTTP frameworks, ORMs never appear in domain. Tests substitute in-memory adapters for ports — no PMS sandbox required for domain/application tests.
