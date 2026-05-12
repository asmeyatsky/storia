# ADR 0008 — Outcome-linked billing reconciliation

Status: Accepted (2026-05-12)
Resolves: PRD §3.1 S12, §10.2 commercial risk

## Decision

The rebate model is **threshold-based on attributed deltas, against a frozen baseline**.

Inputs (all domain types):
- `baseline: PropertyKpis` — measured T-90 to T-0 before pilot start; **frozen at LOI signature** (`baseline_locked_at` recorded immutably).
- `current: PropertyKpis` — measurement window at billing time.

Computation: `AttributedKpis.compute(current, baseline)` produces the four canonical deltas (revenue-per-guest-night, repeat-stay rate, review score, recovery time). The rebate is a function of how those deltas compare to the per-tier targets:

| Tier | Revenue lift target | Rebate behaviour |
|---|---|---|
| Pilot | £15 / guest-night | Hit ≥ target → full fee retained. Miss → tiered rebate. |
| Operator | £25 / guest-night | Same shape, higher bar. |
| Enterprise | Negotiated | Quarterly true-up. |

No estimation, no LLM. Pure arithmetic in the domain layer. Audit-emitted on every reconciliation run.

## Rationale

- PRD §10.2 names "outcome-linked rebate becomes a liability if baselines are gamed" as a Medium/Medium risk. Domain-enforced baseline lock removes the path.
- Buying objection (PRD §2.1 — operator needs "outcome-linked rebate" on the pricing page) is resolved by an auditable mechanism, not a marketing claim.
- The same `AttributedKpis` is what powers the Operator Console's KPI view, so attribution and billing share one math path.

## Consequence

- `OutcomeBilling` use case is the only writer to the `billing_reconciliation` ledger.
- Baseline windows cannot be re-recorded — domain invariant in `AttributedKpis.compute()`.
- Material baseline changes require a manual contract amendment + new ADR.
