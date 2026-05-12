# STORIA™

Guest Experience Intelligence Layer for hotels and resorts. See `STORIA_PRD_v1.md`.

## Layout

```
ADRs/                  Architecture Decision Records (resolve PRD §4 + §12)
crates/                Rust — connectors, event ledger primitives (hot path, p99 < 50ms)
services/storia-core/  Python — domain, application, infrastructure, presentation
services/storia-mcp/   Python — one MCP server per bounded context
console/               TypeScript + React — operator console (tablet-first)
```

## Architecture

Hexagonal. Layer direction enforced in CI per `Architectural Rules — 2026.md` §2:

```
domain ← application ← infrastructure
                    ← presentation
```

- `domain/` — pure, immutable models, invariants in factories, no SDKs
- `application/` — use cases, depends only on domain ports
- `infrastructure/` — adapters: Postgres event store, PMS connectors (via Rust FFI / IPC), audit log
- `presentation/` — FastAPI routes, MCP server entrypoints
- `console/` — React tablet UI, no business logic

## Stack (canonical, per Rules §1)

| Concern | Choice |
|---|---|
| Hot-path connectors, event ledger | Rust |
| Domain + orchestration | Python 3.12+ |
| Operator Console | TypeScript + React + shadcn/ui |
| Primary store | Postgres (event-sourced ledger) |
| Cache | Redis |
| Analytics | BigQuery |
| Hosting | GCP Cloud Run |
| Secrets | Google Secret Manager + Workload Identity |

## Quickstart

```
# Rust
cargo build --workspace

# Python
cd services/storia-core
uv sync
uv run pytest

# Console
cd console && pnpm install && pnpm dev
```

## CI gates

- `import-linter` — Python layer boundaries
- `cargo-deny` — Rust dependency policy
- `eslint-plugin-boundaries` — TS layer boundaries
- Coverage floors: domain ≥95%, application ≥85%, overall ≥80%
- `pip-audit`, `cargo-audit`, `npm audit`
- Signed commits on `main`
