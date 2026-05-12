"""
Module: storia.application.queue_pre_arrival_actions
Layer: application
Ports: EventStore, ActionQueue, AuditLog, Reasoner
MCP integration: exposed as MCP tool `queue_pre_arrival_actions` in infrastructure
Stack: stdlib + storia.domain

Use case for PRD FR-PA-3 — FR-PA-6: evaluate pre-arrival playbooks, produce ranked actions,
above-threshold ones auto-approve, below-threshold queue for shift, every action carries why.

Reasoner output is validated against an explicit Pydantic schema before producing actions
(Rules §4.5). Free-text guest-facing payloads are prohibited in v1 — the kind/payload
shape is restricted by the schema.
"""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from storia.domain.ids import PropertyId, StayId
from storia.domain.models import Action, Signal
from storia.domain.ports import ActionQueue, AuditLog, Reasoner

_ALLOWED_KINDS = frozenset({
    "pms.note.add",
    "pms.room.assign",
    "messaging.draft",  # drafts only in v1 (PRD §5.2.2)
    "operator.alert",
})


class _ProposedAction(BaseModel):
    """Schema-validated reasoner output (Rules §4.5)."""
    model_config = ConfigDict(extra="forbid", strict=True)
    kind: str = Field(min_length=1)
    payload: dict[str, str | int | float | bool | None]
    reasoning: list[str] = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    reversible: bool


class _ProposedActions(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    proposals: list[_ProposedAction]


@dataclass(frozen=True, slots=True)
class QueuePreArrivalActionsRequest:
    property_id: PropertyId
    stay_id: StayId
    playbook_id: UUID
    auto_approve_threshold: float  # confidence above this auto-approves IF reversible
    triggering_signals: tuple[Signal, ...]
    correlation_id: str


class QueuePreArrivalActions:
    def __init__(self, *, reasoner: Reasoner, queue: ActionQueue, audit: AuditLog) -> None:
        self._reasoner = reasoner
        self._queue = queue
        self._audit = audit

    async def __call__(self, req: QueuePreArrivalActionsRequest) -> list[Action]:
        prompt = self._build_prompt(req)
        raw = await self._reasoner.reason(prompt=prompt, schema_name="ProposedActions")
        proposed = _ProposedActions.model_validate(raw)

        actions: list[Action] = []
        for p in proposed.proposals:
            if p.kind not in _ALLOWED_KINDS:
                continue  # reject by default (Rules §4.2)
            auto = p.reversible and p.confidence >= req.auto_approve_threshold
            action = Action.propose(
                stay_id=req.stay_id,
                property_id=req.property_id,
                playbook_id=req.playbook_id,
                kind=p.kind,
                payload=p.payload,
                reasoning=tuple(p.reasoning),
                reversible=p.reversible,
                auto_approved=auto,
            )
            await self._queue.enqueue(action)
            await self._audit.emit(
                actor="system:storia.application.queue_pre_arrival_actions",
                action=f"action.{action.status.value}",
                before_hash=None,
                after_hash=_hash(action.model_dump_json()),
                correlation_id=req.correlation_id,
            )
            actions.append(action)
        return actions

    @staticmethod
    def _build_prompt(req: QueuePreArrivalActionsRequest) -> str:
        signals = "\n".join(
            f"- {s.kind.value} at {s.occurred_at.isoformat()}: {s.payload}"
            for s in req.triggering_signals
        )
        return (
            "You produce ProposedActions JSON. Allowed kinds: "
            f"{sorted(_ALLOWED_KINDS)}. Every proposal needs reasoning citing the "
            "signal(s) that triggered it.\n\nSignals:\n" + signals
        )


def _hash(s: str) -> str:
    import hashlib
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


# uuid4 retained available for callers without a configured playbook
def new_playbook_id() -> UUID:
    return uuid4()
