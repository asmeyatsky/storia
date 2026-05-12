"""
Module: storia.application.decide_action
Layer: application
Ports: ActionQueue, AuditLog
MCP integration: exposed as MCP tool `decide_action` (Operator Console server)
Stack: stdlib + storia.domain

Operator approval surface (PRD FR-OC-3): every automated action is one tap from audit
detail. Decisions go through this use case so the audit chain stays unbroken.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Literal

from storia.domain.ids import ActionId
from storia.domain.models import Action
from storia.domain.ports import ActionQueue, AuditLog


Decision = Literal["approve", "reject", "reverse"]


@dataclass(frozen=True, slots=True)
class DecideActionRequest:
    action_id: ActionId
    decision: Decision
    actor: str  # operator user id / role
    correlation_id: str


class ActionNotFound(LookupError): ...


class DecideAction:
    def __init__(self, *, queue: ActionQueue, audit: AuditLog) -> None:
        self._queue = queue
        self._audit = audit

    async def __call__(self, req: DecideActionRequest) -> Action:
        existing = await self._queue.get(req.action_id)
        if existing is None:
            raise ActionNotFound(str(req.action_id))
        before_hash = _hash(existing.model_dump_json())
        if req.decision == "approve":
            updated = existing.executed()
        elif req.decision == "reject":
            updated = existing.rejected()
        else:
            updated = existing.reversed_()
        await self._queue.replace(updated)
        await self._audit.emit(
            actor=req.actor,
            action=f"action.{req.decision}",
            before_hash=before_hash,
            after_hash=_hash(updated.model_dump_json()),
            correlation_id=req.correlation_id,
        )
        return updated


def _hash(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()
