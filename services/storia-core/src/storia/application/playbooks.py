"""
Module: storia.application.playbooks
Layer: application
Ports: domain only
MCP integration: surfaced read-only via the Action Engine MCP server
Stack: stdlib + storia.domain

Three pilot-phase playbooks (PRD §11.2 Action Engine v1). Stored as JSON graphs per
ADR 0006 — these are the canonical seeds the operator can copy and customise.

  P1  Pre-arrival room readiness + allergy routing  (FR-PA-3..6)
  P2  In-stay context-aware F&B upsell             (FR-IS-4..5)
  P3  In-stay recovery flag from sentiment signals  (FR-IS-2..3)
"""
from __future__ import annotations

from uuid import uuid4

from storia.domain.ids import PlaybookId
from storia.domain.playbook import Guardrail, NodeKind, Playbook, PlaybookNode


def pre_arrival_room_readiness() -> Playbook:
    """P1 — fires on BOOKING_CREATED. Adds an allergy-aware PMS note + flags housekeeping."""
    return Playbook.from_graph(
        id=PlaybookId(uuid4()),
        name="pre-arrival-room-readiness",
        version=1,
        nodes=[
            PlaybookNode(key="trg", kind=NodeKind.TRIGGER,
                         spec={"signal_kind": "booking.created"}, next=("guard",)),
            PlaybookNode(key="guard", kind=NodeKind.GUARDRAIL,
                         spec={"min_lead_hours": 4}, next=("note", "alert")),
            PlaybookNode(key="note", kind=NodeKind.ACTION,
                         spec={"kind": "pms.note.add",
                               "template": "Allergy / preference check for {display_name}",
                               "auto_approve": True}, next=()),
            PlaybookNode(key="alert", kind=NodeKind.ACTION,
                         spec={"kind": "operator.alert",
                               "template": "Housekeeping: pre-arrival readiness for room {room_code}",
                               "auto_approve": False}, next=()),
        ],
        guardrails=[Guardrail(
            predicate="lead_hours >= 4 AND signal_kind == 'booking.created'",
            on_pass="auto_execute", on_fail="escalate",
        )],
    )


def in_stay_fb_upsell() -> Playbook:
    """P2 — fires on POS_TRANSACTION matching F&B; respects 3-suggestion fatigue rule (FR-IS-5)."""
    return Playbook.from_graph(
        id=PlaybookId(uuid4()),
        name="in-stay-fb-upsell",
        version=1,
        nodes=[
            PlaybookNode(key="trg", kind=NodeKind.TRIGGER,
                         spec={"signal_kind": "pos.transaction",
                               "category": "fb"}, next=("fatigue",)),
            PlaybookNode(key="fatigue", kind=NodeKind.GUARDRAIL,
                         spec={"max_suggestions_24h": 3}, next=("draft",)),
            PlaybookNode(key="draft", kind=NodeKind.ACTION,
                         spec={"kind": "messaging.draft",
                               "template": "Upsell {next_item} (paired)",
                               "auto_approve": False}, next=()),
        ],
        guardrails=[Guardrail(
            predicate="suggestions_last_24h < 3",
            on_pass="queue", on_fail="block",
        )],
    )


def in_stay_recovery_flag() -> Playbook:
    """P3 — fires on COMPLAINT or negative-sentiment review. Escalates to duty manager <60s
    (FR-IS-3). Never auto-executes — recovery is always human-led in v1."""
    return Playbook.from_graph(
        id=PlaybookId(uuid4()),
        name="in-stay-recovery-flag",
        version=1,
        nodes=[
            PlaybookNode(key="trg-c", kind=NodeKind.TRIGGER,
                         spec={"signal_kind": "complaint"}, next=("guard",)),
            PlaybookNode(key="trg-r", kind=NodeKind.TRIGGER,
                         spec={"signal_kind": "review.posted",
                               "max_sentiment": -0.4}, next=("guard",)),
            PlaybookNode(key="guard", kind=NodeKind.GUARDRAIL,
                         spec={"escalate_within_seconds": 60}, next=("alert",)),
            PlaybookNode(key="alert", kind=NodeKind.ACTION,
                         spec={"kind": "operator.alert",
                               "template": "Recovery: {summary}",
                               "auto_approve": False,
                               "reversible": False}, next=()),
        ],
        guardrails=[Guardrail(
            predicate="severity >= warn",
            on_pass="queue", on_fail="escalate",
        )],
    )
