# ADR 0004 — Model split: Opus 4.7 for reasoning, Haiku 4.5 for routing

Status: Accepted (2026-05-12)
Resolves: OQ3

## Decision

Action Engine is dual-model. Haiku 4.5 routes signals to playbooks and produces structured field extractions (high throughput, low latency). Opus 4.7 reasons over multi-signal pre-arrival and recovery flows where the cost of a bad action is high. Routing decision is per-playbook, declared in the playbook spec.

All AI output that mutates state is validated against an explicit Pydantic schema before reaching any adapter (Rules §4.5). Free-text guest-facing output is prohibited in v1.

## Rationale

- Per-call cost asymmetry: Haiku for the 90% routing volume, Opus for the 10% high-stakes reasoning.
- Prompt caching applied on both, keyed on playbook + property guardrails.
- CRUCIBLE evaluation suites required for each playbook × model pairing before promotion.

## Consequence

- `infrastructure/llm/` exposes a `Reasoner` port with `route()` and `reason()` methods. Adapters: `HaikuRouter`, `OpusReasoner`. Tests use a deterministic stub.
- Model ID, version, prompt hash, tokens, latency, cost logged per call (Rules §6).
