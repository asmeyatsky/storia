# STORIA — Known gaps

As of `81973c3` (2026-05-13). Updated whenever a gap closes or a new one appears.

The architecture, layer enforcement, PII handling, audit chain, tenant isolation,
observability seams, and CRUCIBLE gating are **in place**. What remains is integration
work with paid third-party services and one process item (SOC 2). Each entry below
names the gap, where it lives, what's needed to close it, and why it can't be closed
inside the current toolchain.

## 1. No live PMS pilot account

- **State.** `MewsPmsAdapter` and `CloudbedsPmsAdapter` are real `httpx` clients with
  retry, schema-drift detection, timeout, no-retry-on-4xx, Bearer auth from a
  `TokenProvider` port. They are tested with `respx` against mocked responses.
- **Closes when.** The first pilot LOI is signed and a sandbox tenant on Mews
  Marketplace (or Cloudbeds equivalent) is provisioned.
- **Work to do.** (a) Implement a `SecretManagerTokenProvider` against Google Secret
  Manager + Workload Identity. (b) Write an integration-tier test suite that runs
  outside CI against the sandbox. (c) Apply to Mews Marketplace.
- **Why not now.** Requires a signed partner agreement and tenant credentials. No
  amount of code makes these appear.

## 2. Opera SOAP envelopes are skeletons

- **State.** `crates/storia-connectors-opera/src/lib.rs` validates the response struct
  with `serde(deny_unknown_fields)`; `fetch_reservations` currently returns
  `SchemaDriftError`. The shape, error types, and timeout discipline are correct;
  the SOAP XML body is not built.
- **Closes when.** A branded-chain pilot is signed and Oracle OWS access is granted.
- **Work to do.** Build the OWS `FetchReservations` envelope, parse the SOAP response,
  fault-handling. Likely vendor a small SOAP helper crate rather than depending on
  one.
- **Why not now.** OWS access is a paid Oracle cert + per-tenant arrangement. PRD §11.3
  explicitly defers this to the Repeat phase.

## 3. Operator Console MCP server (Rules §3.5)

- **State.** Guest Signal and Action Engine MCP servers exist. The Operator Console
  bounded context (shift view, audit access, decide, KPI view) is wired via FastAPI
  routes directly, not via a third MCP server.
- **Closes when.** Before any MCP-first client (e.g. an internal Claude Desktop
  workflow for the Smeyatsky Labs CS team) needs to read the audit feed or approve
  actions over MCP.
- **Work to do.** Create `storia.infrastructure.mcp.operator_console_server` with
  `resource:shift`, `resource:audit`, `tool:decide_action`, `resource:group_kpis`.
  ~150 lines mirroring the existing two servers.
- **Why not now.** Not blocking the FastAPI surface; pure adapter work, can land in
  the next session when prioritised.

## 4. Pub/Sub adapter not implemented (ADR 0005)

- **State.** Only `InMemorySignalBus` exists. The `SignalBus` port matches the ADR-0005
  single-bus-tenant-routing shape.
- **Closes when.** Before pilot go-live — the operator's POS / messaging signals need a
  real bus to flow through.
- **Work to do.** `storia.infrastructure.pubsub_bus.PubsubSignalBus` using
  `google-cloud-pubsub`. Per-tenant subscription with filter `tenant_id=<op_uuid>`.
  IAM bound to a per-tenant service account via Workload Identity.
- **Why not now.** Needs a GCP project, KMS, and an IAM rollout. Code is mechanical
  once the project is set up.

## 5. Anthropic Reasoner adapters not implemented (ADR 0004)

- **State.** Only `StubReasoner` exists. The `Reasoner` port is shaped for ADR 0004's
  `route()` (Haiku 4.5) + `reason()` (Opus 4.7) split.
- **Closes when.** The Pilot-phase pre-arrival flow goes live at a real operator.
- **Work to do.** `HaikuRouter` + `OpusReasoner` adapters using `anthropic` SDK with
  prompt caching, model-id versioning, and per-call cost log via
  `observability.log_llm_call(...)`. Schema-validation on the way out is **already
  enforced** by the use case (`_ProposedActions`).
- **Why not now.** Requires `ANTHROPIC_API_KEY` provisioned in prod Secret Manager;
  the prompt templates need CRUCIBLE thresholds baked from real eval data, not the
  stub's 0.99.

## 6. MetricsReader adapter not implemented

- **State.** `GroupKpiView` use case, `PropertyKpis`/`GroupKpis`/`AttributedKpis`
  domain types, and `OutcomeBilling` arithmetic are all real and 100% covered. Only
  the port adapter is missing.
- **Closes when.** The first property has 90 days of measured data in BigQuery.
- **Work to do.** `storia.infrastructure.bigquery_metrics.BigQueryMetricsReader`
  running parameterised SQL against the canonical analytics dataset.
- **Why not now.** No analytics dataset until first pilot is 90 days in.

## 7. Console build / browser-level testing

- **State.** TypeScript `tsc --noEmit` and ESLint pass. No `vitest` tests for the
  React components. No browser run.
- **Closes when.** Before the first real user (Maddalena's CS team) touches the
  console.
- **Work to do.** (a) Vitest + React Testing Library tests for `PlaybookEditor`
  (DAG validation), `GuardrailEditor`, `AuditView`, `KpiView`. (b) `pnpm dev` + a
  manual walkthrough on tablet. (c) Tablet-degraded-Wi-Fi probe (PRD FR-OC-1).
- **Why not now.** UI testing benefits from a human in the loop; CLI-only iteration
  has diminishing returns once the type system + lint pass.

## 8. Composition root does not call `observability.configure()`

- **State.** `storia.main.build()` constructs use cases but never calls
  `storia.infrastructure.observability.configure()`. First prod boot needs that
  one-line add.
- **Closes when.** First Cloud Run deploy or first integration test using the
  observability surface.
- **Work to do.** One-liner in `main.py`; export the structlog/OTel resource
  attributes (`service.name = storia-core`, `service.version = __version__`).
- **Why not now.** Trivial; deliberately left out so any deploy script makes the
  decision visible.

## 9. SOC 2 Type I / Type II

- **State.** The controls SOC 2 cares about (audit log per write, encryption at rest
  via per-tenant CMEK, PII redaction in logs, tenant isolation, separated audit IAM,
  signed-commits gate, SBOM, dependency scanning) are implemented and CI-enforced.
  The formal assessment is process, not code.
- **Closes when.** Mid-pilot, before the chain-segment conversations open up.
- **Work to do.** Engage a SOC 2 firm; gap-assess against the existing controls;
  remediate. No code expected to change materially.
- **Why not now.** Process, not engineering.

---

## Gaps that are NOT here

The following were named in earlier round-1 assessment and are now closed; listed so
this document is a complete state report:

- ~~Observability wiring~~ → `storia.infrastructure.observability`
- ~~PII enforcement (encryption + log redaction + offboarding)~~ → `encryption.py`,
  `pii_redaction.py`, `OffboardTenant`
- ~~VAID / CRUCIBLE / SENTINEL seams~~ → `storia.infrastructure.synthera`
- ~~Postgres event store working + tested~~ → `postgres_event_store.py` at 97%
- ~~Real PMS Python adapters with retry / schema-drift~~ → `mews_pms.py`,
  `cloudbeds_pms.py`
- ~~CRUCIBLE eval gate in CI~~ → `crucible/suites.yaml` + `crucible/runner.py`
- ~~Visual console UI: playbook editor, guardrail editor, audit view, KPI view~~ →
  `console/src/presentation/*`
