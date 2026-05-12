# STORIA™ — Product Requirements Document

**Guest Experience Intelligence Layer for Hotels and Resorts**

| Field | Value |
|---|---|
| Document | PRD v1.0 (working draft) |
| Owner | Allan Smeyatsky (Product & Engineering) |
| Co-owner | Maddalena Smeyatsky (Domain & Commercial) |
| Parent | Smeyatsky Labs |
| Status | Concept → Validate phase |
| Date | May 2026 |
| Source | From Stay to Story — Strategic Concept Deck, May 2026 |

---

## 0. Reader's preamble

This PRD is the engineering-grade restatement of the strategic concept. It is written to be the single artifact a builder needs to start. It assumes the strategy questions on slide 14 of the source deck are still open and treats them as gating, not as design constraints. Everything below the line `## 4. Gating decisions` is provisional until those six questions resolve.

The product name STORIA™ is a working candidate. Strong alternatives: HEARTH™, SOJOURN™, ATRIUM™, KINDRED™. Pick before the first repo commit; renaming later costs more than it should.

---

## 1. Problem and premise

### 1.1 The premise (one paragraph)

Hotels and resorts no longer compete on rooms. They compete on whether the stay felt made for the guest. Personalisation has graduated from a name on a welcome card into the mechanics of daily operations — anticipating arrival, removing friction the guest never sees, and turning every touchpoint into recognition rather than admin. The supplier landscape has not caught up. Operators run on five disconnected systems and goodwill; brands talk hyper-personalisation while shift handovers happen on paper. The gap between brochure and back-of-house is where loyalty dies and revenue leaks.

### 1.2 The five fractures (validated field observations)

These are the lived breakages Maddalena has observed across Club Med, Middle East, and Indian Ocean operations. They are the problem space STORIA™ exists to close.

| # | Fracture | Operational cost |
|---|---|---|
| F1 | Same question asked three times (allergies, occasion, preferences) | Data exists; flow is broken. Erodes recognition. |
| F2 | Staff have no situational picture (delayed flight, second honeymoon) | Each shift starts blind. Moments are missed. |
| F3 | PMS + CRM + POS + messaging + reviews = five systems, zero coherence | 60% of operators name this as their #1 blocker. |
| F4 | Upsells are scripted, mistimed, or absent | Revenue left on the table at every interaction. |
| F5 | Personalisation is a marketing claim, not a system | Promise → delivery gap kills repeat bookings. |

### 1.3 The bet

Surface personalisation → **operational personalisation**. The product is invisible to the guest. The guest just feels recognised. The operator just sees revenue and reviews move.

### 1.4 Market window — why now

Three forces have converged in the last eighteen months and create a structurally open competitive lane:

1. **Agentic AI is finally usable.** LLMs that take action, not just answer. Cost curve has bent decisively in the operator's favour.
2. **Guests expect recognition.** Travellers raised on Netflix/Spotify/Uber bring those instincts. RevPAR is flat; experience-led repeat bookings and direct-channel loyalty are the remaining levers.
3. **The PMS war is over.** Mews, Cloudbeds, Oracle hold the rooms. The layer above — guest intelligence and operational personalisation — is structurally open and has no dominant winner.

### 1.5 Anti-premise (what we are explicitly rejecting)

- We are **not** building another PMS. The PMS war is decided.
- We are **not** building a chatbot. Canary, Bookboost, Whistle already own inbound messaging.
- We are **not** building a CRM. We sit above CRM and read from it.
- We are **not** competing on AI sophistication. We are competing on operational integration depth.

---

## 2. Users and personas

STORIA™ serves three distinct user populations. Every feature must be traceable to value for one of them.

### 2.1 Buyer persona — The Operator

**Who.** General Manager, COO, or Director of Guest Experience at an independent luxury resort, boutique group (5–30 properties), or branded chain regional office.

**Mental model.** Runs on RevPAR, GOPPAR, NPS, repeat-stay rate, review sentiment, and gut feel from walking the property. Has been pitched at by hospitality tech vendors for fifteen years and is jaded.

**Pain.** Knows the guest experience is fractured. Cannot get the PMS vendor to fix it because the PMS vendor sees their job as rooms and billing. Cannot get the CRM vendor to fix it because the CRM vendor lives in marketing. Has tried "data lake" projects that produced dashboards nobody reads.

**What unlocks them.** A pilot with a defined twelve-week metric and a written escape clause. The word "outcome-linked rebate" in the pricing page. A reference call with another operator they respect.

### 2.2 Daily user persona — Front-of-House Staff

**Who.** Front desk agents, concierge, F&B managers, housekeeping supervisors, duty managers. Shift workers. Mix of seasoned career hospitality and high-churn entry staff.

**Mental model.** "Did this morning's handover happen? Where is the rooming list? Who's a VIP? Did 412 get the extra crib?" Lives in micro-tasks, time-boxed by shift.

**Pain.** Walks into a shift without the picture. The system tells them the room number; it does not tell them the guest just landed at 3am, that the wife's birthday is on day two, or that the last stay ended with a complaint about pillow firmness. They are blamed for missing moments they were never given the data to catch.

**What unlocks them.** One pane of glass per shift. Not a new app to learn — embedded into the channel they already use (PMS-front-desk view, mobile, Teams/Slack, or in-property tablet).

### 2.3 Indirect beneficiary — The Guest

**Who.** Leisure or business traveller. Does not know STORIA™ exists and should not.

**Mental model.** "Did they remember? Did I have to repeat myself? Was the friction smoother than last time?"

**Pain.** Being treated as a record number. Re-explaining allergies and preferences every visit. Generic upsells that miss the moment.

**What unlocks them.** Nothing direct. STORIA™ wins when the guest leaves a five-star review without being able to articulate why.

### 2.4 Hostile persona — IT/Data Officer

**Who.** Corporate IT lead at a chain, or outsourced MSP for an independent. Often the kill-switch on procurement.

**Concerns.** PII handling under GDPR / regional equivalents. Data residency (especially for Middle East and EU operators). Integration burden. Whether STORIA™ becomes another system that must be kept alive at 3am.

**What unlocks them.** SOC 2 Type II on the roadmap. Documented data flows. Read-only-by-default integration posture. A clear answer to "what happens if we churn?" (data export, contractual deletion SLA).

---

## 3. Scope — in, out, deferred

### 3.1 In scope (v1.0 — months 0–12)

| ID | Capability | Phase |
|---|---|---|
| S1 | Unified guest profile ingestion from PMS + CRM + POS + OTAs + reviews | Validate (0–3) |
| S2 | Preference inference from booking history and behaviour | Validate (0–3) |
| S3 | Real-time situational context enrichment (flight, weather, occasion) | Pilot (3–6) |
| S4 | Pre-arrival action flows (room readiness, allergy routing, tailored offers) | Pilot (3–6) |
| S5 | In-stay action flows (context-aware upsells, F&B prompts, recovery flags) | Pilot (3–6) |
| S6 | Operator-defined guardrails for agentic flows | Pilot (3–6) |
| S7 | Operator Console — single property, single shift view | Pilot (3–6) |
| S8 | Audit trail — every automated action human-reviewable | Pilot (3–6) |
| S9 | KPI surfacing: RevPAR lift, NPS, recovery time, repeat-stay rate | Repeat (6–12) |
| S10 | Group-level analytics across multiple properties | Repeat (6–12) |
| S11 | Custom action playbooks per property | Repeat (6–12) |
| S12 | Outcome-linked billing reconciliation | Repeat (6–12) |

### 3.2 Out of scope (explicit non-goals)

| ID | Non-goal | Rationale |
|---|---|---|
| N1 | Rooms / inventory / billing | PMS owns this. We integrate. |
| N2 | Inbound guest messaging UI | Canary/Bookboost own this. We orchestrate above. |
| N3 | Revenue management / dynamic pricing | Lighthouse/IDeaS own this. Adjacent, not ours. |
| N4 | Short-term-rental ops | Guesty/Hostaway segment. Different buyer, different ops. |
| N5 | Loyalty programme administration | Hilton Honors / Marriott Bonvoy lane. We read from it. |
| N6 | Guest-facing mobile app | The product is invisible to the guest. Hard rule. |
| N7 | Marketing email campaign management | CRM/marketing-cloud lane. We push signals into it. |

### 3.3 Deferred (post-v1.0)

- Multi-language conversation surfaces for non-English markets (Q5 2027+)
- Voice-agent integration for in-room and concierge calls
- Predictive maintenance signal (room/equipment) — adjacent but not core
- White-label SDK for PMS partners who want STORIA-as-a-feature
- F&B-only single-module SKU for restaurant groups outside hotels

---

## 4. Gating decisions

The source deck closes on six open questions. Until these resolve, the technical decisions below are provisional. They are listed here at the top — not buried — because changing answers later costs disproportionately.

| # | Decision | Why it matters technically |
|---|---|---|
| G1 | Which segment anchors first — luxury resort, boutique urban, or branded chain? | Determines which PMS integrations are tier-1 (Opera for chains; Mews/Cloudbeds for boutique/resort). |
| G2 | Standalone platform vs PMS-partnered layer? | Drives whether we build OAuth integration adapters or sit inside a PMS marketplace. |
| G3 | Insider-led discovery list — who do we call first? | Determines the pilot LOI candidate and therefore the data shape we optimise for. |
| G4 | Founder split — equity, time, decision rights? | Not a technical decision but affects velocity, especially during the validate phase. |
| G5 | 90-day budget and runway commitment from Smeyatsky Labs? | Determines whether we build with one engineer (Allan only) or fund a contract Rust/Python developer (suggest: Amarnath/Greyquill). |
| G6 | Is this the play we both want for the next two years? | Hard prerequisite. Everything else is downstream. |

**Default assumptions** used to write the rest of this PRD (revise on decision):
- G1: Luxury resort and boutique groups (segment with Maddalena's deepest network).
- G2: Standalone platform with PMS integrations via official APIs. PMS partnership a Phase 2 lever.
- G3: Indian Ocean and Middle East operator network (Maddalena-owned).
- G5: Lean — Allan as builder, no funded headcount in months 0–3. Greyquill contract option from month 4 if pilot LOI signed.

---

## 5. System architecture

### 5.1 Architectural principle

STORIA™ sits **above** the operational stack as an intelligence and orchestration layer. It reads from systems of record, writes back through their APIs, and never owns rooms, billing, or guest-facing inbound messaging.

```
                            ┌─────────────────────┐
                            │       Guest         │
                            └──────────┬──────────┘
                                       │ experiences
                                       ▼
┌──────────────────────────────────────────────────────────────────┐
│                          STORIA™ Layer                           │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐      │
│  │  Guest Signal  │→ │ Action Engine  │→ │ Operator       │      │
│  │  (ingest +     │  │ (agentic flows │  │ Console        │      │
│  │  unify)        │  │ + guardrails)  │  │ (one-pane UI)  │      │
│  └────────────────┘  └────────────────┘  └────────────────┘      │
└──────┬─────────────────────┬──────────────────────┬──────────────┘
       │ read/write          │ orchestrate          │ surface
       ▼                     ▼                      ▼
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│   PMS    │  │   CRM    │  │   POS    │  │ Messaging│  │ Reviews  │
│ Mews     │  │ Salesforce│ │ Lightspeed│ │ Canary   │  │ Revinate │
│ Cloudbeds│  │ HubSpot  │  │ Square   │  │ Bookboost│  │ TrustYou │
│ Opera    │  │ Mailchimp│  │ Toast    │  │ Whistle  │  │ Reputation│
└──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘
                  Systems of record (operator-owned)
```

### 5.2 Module breakdown

#### 5.2.1 Guest Signal — the unification layer

**Responsibility.** Ingest events from every system of record. Resolve guest identity across them. Build and maintain a unified, time-versioned guest profile. Infer preferences from behaviour where they are not declared.

**Inputs.**
- PMS booking events (created, modified, arrival, departure, cancellation)
- CRM contact records and interaction history
- POS transactions (F&B, spa, retail, room service)
- OTA reservation feeds (Booking.com, Expedia)
- Review platform sentiment and content (TrustYou, Revinate, public TripAdvisor)
- External enrichment: flight status (FlightAware API), weather (OpenWeather), local event calendars
- Manual operator notes (concierge entries)

**Outputs.**
- Canonical `Guest` entity (see data model §6)
- `Signal` events emitted to Action Engine
- Confidence-scored preference inferences (e.g. "prefers high floor", confidence 0.78 from 4 of 5 stays)

**Hard requirements.**
- Identity resolution must handle: name variants, multiple emails per guest, family/group bookings, returning guests with new contact details.
- Profile must be queryable in < 100ms p99 from the Action Engine.
- Every field on the profile must be traceable to a source event (no synthetic data without provenance).

#### 5.2.2 Action Engine — the agentic core

**Responsibility.** Take guest signals and contextual events, run them through operator-defined guardrails, and produce actions. Actions are either auto-executed (where guardrails permit) or queued for human approval.

**Inputs.**
- `Signal` events from Guest Signal
- Operator-defined guardrails (rules, thresholds, approval gates) from Operator Console
- Action playbooks (templates for common flows — pre-arrival, in-stay upsell, recovery, post-stay follow-up)
- Real-time situational context (flight status, weather, occupancy, staff availability)

**Outputs.**
- Actions written back to PMS (room assignment, notes, billing items)
- Actions written to messaging systems (queued message drafts, not direct sends, in v1)
- Actions surfaced to operator console (recommendations, alerts, recovery flags)
- Audit log entries — one per action, every action

**Hard requirements.**
- Every action must be reversible OR require human approval before execution. No exceptions in v1.
- Action latency from signal to execution: < 5 seconds for in-stay, < 5 minutes for pre-arrival.
- Guardrails must be expressible as declarative rules, not code (so Maddalena and customer success staff can edit them).
- Audit trail must be tamper-evident and exportable.

#### 5.2.3 Operator Console — the human interface

**Responsibility.** Give the operator one pane of glass per property and per shift. Make every automated action human-reviewable. Surface revenue lift, NPS, recovery time as native KPIs.

**Surfaces.**
- **Shift view** — what's happening right now on this shift, organised by guest arc (arriving today, in-stay, departing today).
- **Guest view** — drill-down into a single guest's profile, history, current state, queued actions.
- **Playbook editor** — visual editor for action flows and guardrails. No code.
- **Audit view** — every automated action, who approved it (if applicable), what happened next.
- **KPI view** — RevPAR lift attributed to STORIA™ actions, NPS delta, recovery time trend, repeat-stay rate.
- **Group view** (Phase 2) — cross-property roll-up for multi-property operators.

**Hard requirements.**
- Console must be usable on a tablet (front desk and concierge use tablets, not desktops).
- Must work in poor connectivity (Indian Ocean resort context — Wi-Fi is sometimes the failure point).
- Role-based access: GM sees all; front desk sees their shift; F&B sees their outlet; housekeeping sees their floors.

### 5.3 Cross-cutting architectural rules

These are non-negotiable. They are in this PRD because they are in `skill2026.md` v3 and apply to every Smeyatsky Labs product.

1. **Layer direction enforced in CI.** Guest Signal → Action Engine → Operator Console. No backwards dependencies. CI fails on violation.
2. **No direct PMS writes outside the Action Engine adapter layer.** Every write is auditable, retryable, and rate-limited per integration.
3. **Read-only-by-default integration posture.** New integrations land as read-only and are promoted to read-write only after a written check with the operator.
4. **PII handled per data classification table** (§6.5). Encryption at rest, in transit, and in logs. Right-to-erasure honoured within 30 days.
5. **Every action is auditable.** No silent automation. Ever.
6. **Multi-tenancy is single-tenant-shaped.** Each operator's data is logically and physically separable. No shared-table designs.
7. **Observability is non-optional.** Every signal, action, and console interaction is traced. We will be debugging a missed dinner reservation on a Saturday night — design for it.

### 5.4 Tech stack (canonical Smeyatsky Labs stack)

| Layer | Choice | Rationale |
|---|---|---|
| Ingestion adapters | Rust (tokio, reqwest, sqlx) | High-throughput connector layer; reliability under PMS rate limits; matches SYNTHERA primitives. |
| Identity resolution + signal enrichment | Rust (core), Python 3.12+ (ML models) | Rust for hot path; Python for the inference layer (preference inference, sentiment, embeddings). |
| Action Engine | Python 3.12+ (LangGraph or custom orchestration on SYNTHERA primitives) | Agentic flows live where the LLM tooling lives. Consider SYNTHERA VAID for action provenance. |
| Operator Console — backend | Python (FastAPI) | Standard Labs choice. |
| Operator Console — frontend | TypeScript + React + shadcn/ui | Matches Healthi Phase A pattern. Tablet-friendly. |
| Primary database | PostgreSQL (Cloud SQL or Spanner) | Event-sourced ledger for guest events; Spanner if multi-region from day one. |
| Event bus | Pub/Sub (GCP) | Native integration; per-operator topic isolation. |
| Inference / embeddings | Vertex AI + Anthropic API (Opus 4.7 for agentic, Haiku 4.5 for high-throughput inference) | Multi-model by design. CRUCIBLE™ evaluation harness gates every model swap. |
| Hosting | GCP (Cloud Run for stateless, GKE for orchestrator if needed) | Aligned with Searce expertise and Allan's daily environment. |
| Secret management | Google Secret Manager | Standard. |
| Observability | OpenTelemetry → Cloud Trace + Cloud Logging | Standard. |

### 5.5 Reuse from existing Smeyatsky Labs portfolio

This is where STORIA™ stops being a one-off and starts compounding the portfolio.

| Component | Reused from | What it provides |
|---|---|---|
| Agent identity and provenance | SYNTHERA™ (VAID) | Every Action Engine agent has a verifiable identity; every action is provably attributed. |
| Action eval harness | CRUCIBLE™ | Gate every model and prompt change against a fixed regression set before production. |
| AI governance and audit | SENTINEL™ / CODEX™ | Audit trail, policy enforcement, compliance reporting. |
| Cross-system orchestration primitive | SynapticBridge™ | If standalone, this is just STORIA™. If we already have SynapticBridge as a Labs primitive, STORIA™ is a vertical application of it. **G2 decision affects this materially.** |
| LLM-visibility / GEO insights | LUMINA™ | Adjacent — could power "how does our property show up in AI travel agents" as a future module. Not v1.0. |

**Strategic note.** Treating STORIA™ as a vertical on top of SYNTHERA™/SynapticBridge™ rather than a standalone strengthens both: it gives SYNTHERA a real customer use-case to point at; it gives STORIA an architectural moat smaller competitors will struggle to replicate.

---

## 6. Data model

### 6.1 Core entities

```
Operator
  ├─ Property (1..N)
  │    ├─ IntegrationConfig (1..N) — one per connected system
  │    ├─ Playbook (0..N) — operator-authored action templates
  │    ├─ Guardrail (0..N) — declarative rules constraining actions
  │    └─ Shift (1..N) — time-bounded operational window
  │
  └─ User (1..N) — operator staff with role + property scope

Guest
  ├─ IdentityResolution — links to PMS/CRM/POS guest IDs
  ├─ ProfileFact (1..N) — versioned, source-attributed preferences
  ├─ Stay (0..N)
  │    ├─ Booking — canonical reservation
  │    ├─ Signal (0..N) — observed events during stay
  │    └─ Action (0..N) — actions taken or queued
  └─ ConsentRecord (1..N) — granular consent per data category
```

### 6.2 Event sourcing

The guest profile is **derived state**, not authoritative state. The authoritative store is an append-only `GuestEvent` log. Profile reads are served from a materialised view rebuilt from events. This means:

- Any past state is reconstructible.
- Right-to-erasure can be honoured by tombstoning the source events.
- Bug fixes in the inference layer can be re-run against the event log without losing data.
- Matches the Zetu Rust event-sourced ledger pattern — proven Labs architecture.

### 6.3 Identity resolution

Identity resolution is the highest-risk technical sub-problem in this product. Failure modes:

- **False merge** — two guests collapsed into one. Catastrophic for trust. We will see complaints.
- **False split** — one guest seen as two. Misses repeat-guest recognition. Erodes core value prop.

**Strategy.**
1. Deterministic match first (email exact match, phone E.164 match, loyalty number match).
2. Probabilistic match second, with confidence threshold gating auto-merge. Below threshold: queue for operator review.
3. All merges are reversible. No destructive merges in v1.
4. Confidence scores surfaced in the console — operators can audit and override.

### 6.4 Preference inference

| Preference category | Source signal | Confidence threshold for use |
|---|---|---|
| Dietary restrictions | Declared in booking; POS history (avoidance pattern) | High — direct claim OR 3+ avoidance instances |
| Room type / floor / view | Past PMS bookings (repeat selection) | Medium — 2+ stays same selection |
| Occasion sensitivity | Booking notes; CRM tags; date-of-stay anniversaries | High — explicit; Low — date-proximate (offer, don't assume) |
| Spend tier | POS aggregate over rolling 12 months | Medium — used for upsell calibration, not segmentation |
| Communication preference | Channel response history | Medium — favour the channel they last replied on |

**Rule.** Inferred preferences below threshold are surfaced to staff as *hypotheses with sources*, never as facts. The console UI must make the inference vs. declared distinction visually obvious.

### 6.5 PII classification and handling

| Category | Examples | Storage | Logs | Erasure SLA |
|---|---|---|---|---|
| Identity PII | Name, email, phone, passport | Encrypted at rest, field-level for passport | Never logged | 30 days from request |
| Booking metadata | Dates, room, rate, channel | Encrypted at rest | Hashed in logs | 30 days from request |
| Preference data | Dietary, room preference, occasion | Encrypted at rest | Hashed in logs | 30 days from request |
| Behavioural | POS items, in-stay actions | Encrypted at rest | Anonymised in logs (no guest ID) | 30 days from request |
| Inferred | ML-derived preferences | Encrypted at rest | Not logged | Recomputed on source erasure |
| Communications | Message content with guest | Encrypted at rest, field-level | Never logged | 30 days from request |

Compliance reference points: GDPR (EU operators), UK Data Protection Act 2018, POPIA (South African operators), UAE PDPL (Middle East operators). Data residency is per-tenant configurable — EU tenants stay in `europe-west1`, Middle East in `me-central1`, etc.

---

## 7. Integrations

### 7.1 Integration tiers

Integrations are tiered by anchor-segment relevance. G1 (segment decision) determines which tier is built first.

**Tier 1 — must-have for pilot.**

| System category | Vendor | Auth model | Integration depth |
|---|---|---|---|
| PMS | Mews | OAuth 2.0 via Marketplace API | Read: bookings, guests, room state. Write: notes, guest preferences, room assignments. |
| PMS | Cloudbeds | OAuth 2.0 | Read + write (similar scope) |
| POS | Lightspeed | OAuth 2.0 | Read: transactions, items. Write: not in v1. |
| Reviews | TrustYou | API key | Read only. Sentiment, content. |
| Flight data | FlightAware | API key | Read only. Arrival enrichment. |
| Weather | OpenWeather | API key | Read only. Pre-arrival packing nudges, in-stay context. |

**Tier 2 — required for branded chain segment.**

| System | Notes |
|---|---|
| Oracle Opera | OPERA Web Services (OWS) — legacy SOAP API, painful but necessary for chains. |
| Salesforce (CRM) | Standard REST + Connected App. |
| Revinate | Reviews + CRM hybrid; relevant for groups already using it. |

**Tier 3 — Phase 2.**

| System | Notes |
|---|---|
| HubSpot CRM | Boutique-segment relevant. |
| Square POS | Smaller properties. |
| Toast POS | F&B-led properties. |
| Canary / Bookboost / Whistle | Messaging — for action queueing into the channel the operator already uses. |

### 7.2 Integration architectural rule

Every integration is built as a Rust connector with a **strict schema contract** on both ingress and egress. Schema drift in the partner API is treated as a Sev-2 incident, not a passive problem. Each connector exposes:

- Health endpoint (am I authenticated and reachable?)
- Throughput metrics (events ingested, actions written, latency)
- Schema-violation counter (incremented on every unexpected field shape)

---

## 8. Functional requirements

### 8.1 Pre-arrival flow

| ID | Requirement |
|---|---|
| FR-PA-1 | On booking ingestion, STORIA™ resolves the guest identity and assembles the profile within 60 seconds. |
| FR-PA-2 | 48 hours before arrival, situational context is enriched (flight, weather, special date proximity). |
| FR-PA-3 | The Action Engine evaluates pre-arrival playbooks and produces a ranked list of actions. |
| FR-PA-4 | Actions above the auto-execute guardrail threshold are written to the PMS as guest notes and tasks. |
| FR-PA-5 | Actions below threshold are queued in the Operator Console for the morning shift. |
| FR-PA-6 | Every action carries a "why" — the signal(s) that triggered it, in plain language. |

### 8.2 In-stay flow

| ID | Requirement |
|---|---|
| FR-IS-1 | POS, messaging, and operational events are ingested in near-real-time (< 30 sec). |
| FR-IS-2 | Sentiment-bearing signals (negative POS interaction, complaint mention, repeated request) trigger recovery flags. |
| FR-IS-3 | Recovery flags appear in the duty manager's Operator Console within 60 seconds of detection. |
| FR-IS-4 | Context-aware upsell recommendations are surfaced to staff at the right interaction point (concierge desk, F&B service, spa booking). |
| FR-IS-5 | Upsells respect a per-guest fatigue rule — no guest is shown more than three suggestions in a 24-hour period. |

### 8.3 Post-stay flow

| ID | Requirement |
|---|---|
| FR-PS-1 | On departure, the stay's signal history is rolled into the guest profile with full provenance. |
| FR-PS-2 | If a review is posted within 14 days, sentiment is attached to the stay record and to any actions taken. |
| FR-PS-3 | A post-stay summary is available for the operator: what we did, what worked, what did not. |
| FR-PS-4 | Inferred preferences are updated. New inferences are flagged for staff awareness on next booking. |

### 8.4 Operator Console

| ID | Requirement |
|---|---|
| FR-OC-1 | The shift view loads in < 2 seconds on tablet (Wi-Fi-degraded conditions tested). |
| FR-OC-2 | The shift view groups guests by arc: arriving, in-stay (by floor or building), departing. |
| FR-OC-3 | Every automated action is one tap from the audit detail. |
| FR-OC-4 | The playbook editor allows non-engineers (Maddalena, operator CS team) to build action flows visually. No code path required. |
| FR-OC-5 | Guardrails are expressed as readable predicates ("if guest stayed > 3 nights AND last review < 4 stars, escalate to GM before any action"). |
| FR-OC-6 | KPI view shows RevPAR lift, NPS delta, recovery time, repeat-stay rate, all attributable to STORIA™ actions vs. baseline. |

---

## 9. Success metrics

### 9.1 Pilot success criteria (one property, twelve weeks)

The pilot is the gate. These are the numbers we sign in the LOI.

| Metric | Baseline | Target at week 12 | Measurement |
|---|---|---|---|
| Per-guest-per-night revenue uplift | Property baseline (T-90 days) | +£15 per guest per night | POS attributable to STORIA™ actions |
| Repeat-stay rate (90-day rolling) | Property baseline | +3 percentage points | PMS booking data |
| Average review score (TrustYou or equivalent) | Property baseline | +0.2 points on 5-point scale | Review platform |
| Recovery time (complaint → resolution) | Property baseline | -30% median | STORIA™ audit + PMS logs |
| Staff adoption (console daily active users / total relevant staff) | n/a | > 75% by week 8 | Console telemetry |

### 9.2 Product health metrics

| Metric | Target |
|---|---|
| Signal-to-action latency (in-stay) | p50 < 2s, p99 < 5s |
| Pre-arrival action coverage (% of bookings with at least one action) | > 90% |
| False-merge incidents (identity resolution) | 0 per property per quarter |
| Audit trail completeness | 100% — every action accounted for |
| Operator-reported "I would not run my property without it" qualitative | Yes from anchor pilot by month 6 |

### 9.3 Commercial milestones

| By month | Milestone |
|---|---|
| 3 | 10 operator discovery interviews complete; friction map per archetype; one signed pilot LOI |
| 6 | Pilot live, weekly review cadence, week-12 metric in flight |
| 9 | Written case study published; three further pilots signed in same segment |
| 12 | Pricing model validated by outcome data; Series Seed conversation if warranted |

---

## 10. Risks and mitigations

### 10.1 Technical risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Mews/Cloudbeds/Opera API access denied or rate-limited beyond viability | Medium | High | Apply to Mews Marketplace early; have read-only fallback (CSV import) for stubborn properties; cultivate one PMS partner relationship as Plan B. |
| Identity resolution false-merge incident in pilot | Medium | High | Probabilistic threshold deliberately conservative in v1; all merges reversible; pilot operator briefed before go-live. |
| Action latency exceeds operational tolerance | Low | High | Rust hot-path proven in SYNTHERA/Zetu; load test before pilot. |
| LLM hallucination produces an embarrassing action | Medium | High | All v1 actions human-approved or guardrail-gated; CRUCIBLE™ regression suite gates every model swap; no free-text guest-facing output in v1. |
| Multi-region data residency complexity (especially Middle East) | Medium | Medium | Per-tenant region pinning from day one; Spanner if we need multi-region writes. |

### 10.2 Commercial risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Pilot operator churn before week 12 | Medium | High | Tight LOI with mutual escape and pre-agreed metrics; weekly review cadence prevents surprise. |
| "PMS will build this" objection from buyer | High | Medium | Position as integration layer, not feature. Honest answer: Mews will probably build a thinner version of one module in 24 months. By then we should own the multi-PMS, multi-property buyer. |
| Outcome-linked rebate becomes a liability if baselines are gamed | Medium | Medium | Baseline measurement window contractually defined and frozen before pilot starts. Audit clause for material baseline changes. |
| Maddalena's network exhausts before product matures | Low | High | Start a parallel inbound channel (LinkedIn content from Allan, conference presence) by month 4. |

### 10.3 Strategic risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Searce September 2026 vest pulls Allan's attention from pilot delivery | High | High | Pilot scoped to one property to fit available capacity. Contract engineer (Greyquill) on standby for month 4 if LOI signs. |
| One of Mews/Cloudbeds acquires a competing layer (Canary, Bookboost) and bundles | Medium | High | Stay multi-PMS; refuse exclusivity offers in pilot phase; the integration layer's value compounds with multi-system reach. |
| Founder split conversation (G4) stalls | Medium | High | Resolve before any code commit. Non-technical hard prerequisite. |

---

## 11. Phasing and roadmap

Maps directly to the source deck's three-phase roadmap. Engineering work is annotated underneath each phase.

### 11.1 Months 0–3 — Validate

**Commercial (Maddalena-led):**
- 10 operator interviews; friction map per archetype.
- Anchor segment chosen (resolves G1).
- One signed pilot LOI with twelve-week metric defined.

**Engineering (Allan-led, no funded headcount):**
- Repo bootstrap, monorepo with crates/ (Rust) + services/ (Python) + console/ (React) — matches CloudShift v2 layout.
- Mews connector v1 (read-only): bookings, guests, rooms.
- Cloudbeds connector v1 (read-only): same scope.
- `GuestEvent` schema and event-sourced store (PostgreSQL).
- Identity resolution v1 (deterministic match only — probabilistic deferred to Pilot phase).
- Basic Operator Console scaffold (auth, shift view, guest view skeleton).
- SYNTHERA™ VAID wiring for agent provenance.
- CRUCIBLE™ harness skeleton for action evaluation.

**Exit gate to Pilot phase:** signed LOI + working ingestion from at least one PMS into a queryable guest profile.

### 11.2 Months 3–6 — Pilot

**Commercial:**
- Twelve-week pilot live at one property.
- Weekly review with operator; written case study draft started by week 8.
- Defined metrics (§9.1) measured against frozen baseline.

**Engineering:**
- POS connector v1 (Lightspeed or property-specific).
- TrustYou or equivalent reviews connector.
- FlightAware + OpenWeather enrichment.
- Identity resolution v2 (probabilistic, with operator review queue).
- Action Engine v1 — three flows live:
  - Pre-arrival room readiness with allergy routing.
  - In-stay context-aware F&B upsell.
  - In-stay recovery flag from sentiment signals.
- Operator Console:
  - Shift view, guest view, audit view production-ready.
  - Playbook editor v1 (curated templates, not full visual builder yet).
  - Guardrail editor v1.
- Multi-tenant isolation hardened.
- SOC 2 Type I gap assessment commenced.

**Exit gate to Repeat phase:** week-12 metrics met or credibly missed-with-learning; case study published.

### 11.3 Months 6–12 — Repeat

**Commercial:**
- Three further pilots in the anchor segment.
- Pricing model validated by outcome data — Pilot, Operator, Enterprise tiers tested.
- Series Seed conversation initiated if warranted (G6 still holding; warrant criterion = signed Operator-tier contract).

**Engineering:**
- Opera connector (chain-segment readiness — depends on G1).
- Salesforce CRM connector (chain-segment readiness).
- HubSpot CRM connector (boutique-segment readiness).
- Operator Console:
  - Group-level analytics view across multiple properties.
  - Full visual playbook builder.
  - KPI attribution model production-ready.
- Outcome-linked billing reconciliation (ties pricing tier rebates to measured metric lift).
- SOC 2 Type II preparation.
- White-label SDK proof-of-concept (deferred from v1 — moved here only if a PMS partner asks).

**Exit gate from v1.0:** three paying pilots converted to Operator-tier contracts; product is self-sustaining at the pilot-pricing tier; G6 (two-year commitment) reaffirmed or reconsidered.

---

## 12. Open questions (engineering-specific)

These are below the strategic gating decisions in §4 but need answers before or during the Validate phase.

| # | Question | When it needs answering |
|---|---|---|
| OQ1 | Build on SYNTHERA™/SynapticBridge™ primitives or standalone? (Architectural reuse depth) | Before first Action Engine commit |
| OQ2 | Cloud SQL or Spanner for primary store? (Multi-region tenancy timing) | Before pilot infra provisioning |
| OQ3 | Anthropic Opus 4.7 for Action Engine reasoning vs. Haiku 4.5 for routing — split or single? | Before pilot model contracts signed |
| OQ4 | Self-host the Operator Console or use Vercel? (Affects ops surface) | Before Pilot phase |
| OQ5 | Per-tenant Pub/Sub topics or single bus with tenant routing keys? | Before second pilot |
| OQ6 | Build the playbook editor as code-generated YAML or store as JSON graph? | Before Pilot phase Action Engine v1 |
| OQ7 | What is the contractual disposition of guest data if the operator churns? Export-and-delete with 30-day SLA — formalised in MSA template? | Before pilot LOI signed |

---

## 13. Appendix

### 13.1 Glossary

| Term | Definition |
|---|---|
| **Operator** | The buying customer — a hotel, resort, or hospitality group |
| **Property** | A single physical location operated by an Operator |
| **PMS** | Property Management System (Mews, Cloudbeds, Opera) — the system of record for rooms, bookings, billing |
| **POS** | Point of Sale — F&B, retail, spa, room service transactional systems |
| **Signal** | A discrete observed event about a guest (booking, transaction, message, sentiment) |
| **Action** | A discrete operational behaviour produced by the Action Engine (note, recommendation, task, message draft) |
| **Playbook** | A reusable template combining triggers, guardrails, and actions |
| **Guardrail** | A declarative rule constraining what the Action Engine may auto-execute vs. queue for approval |
| **RevPAR** | Revenue Per Available Room — hotel industry standard revenue metric |
| **NPS** | Net Promoter Score — guest satisfaction proxy |

### 13.2 Source-deck traceability

Every section of this PRD traces to slides in the source concept deck. If a reader asks "where did this come from?", the answer is one of:

| PRD section | Source slide |
|---|---|
| §1 Problem and premise | Slides 1, 2, 4, 5 |
| §1.4 Why now | Slide 6 |
| §1.5 Anti-premise | Slide 7 (competitive landscape) |
| §2 Personas | Inferred from slide 4 and slide 12 |
| §3 Scope | Slide 8 (wedge), slide 9 (modules) |
| §5 Architecture | Slide 8 (layer diagram), slide 9 |
| §8 Functional requirements | Slide 9 (three modules) |
| §9 Success metrics | Slides 10, 11, 13 |
| §11 Phasing | Slide 13 (roadmap) |
| §4 Gating decisions | Slide 14 verbatim |

### 13.3 Related Smeyatsky Labs documents

- *From Stay to Story* — Strategic Concept Deck, May 2026 (source for this PRD)
- SYNTHERA™ PRD v2 — parent platform candidate for Action Engine primitives
- CRUCIBLE™ PRD — evaluation harness, mandatory dependency
- SENTINEL™ / CODEX™ — governance dependencies for production deployment
- skill2026.md v3 — Smeyatsky Labs architectural constitution (applies to STORIA™)

---

*End of document. v1.0 working draft. Revise on G1–G6 resolution.*
