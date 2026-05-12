"""
Module: storia.application.record_signal
Layer: application
Ports: EventStore, SignalBus, AuditLog
MCP integration: exposed as MCP tool `record_signal` in the Action Engine server
Stack: stdlib + storia.domain

Use case for FR-IS-1..3: ingest a near-real-time signal (POS, review, complaint, concierge
note), append to ledger, publish to bus, audit.

Latency budget (PRD §9.2): p50 < 2s, p99 < 5s signal-to-action — this use case is the front
half of that budget. EventStore.append + Bus.publish are both single-shot.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from storia.domain.ids import OperatorId
from storia.domain.models import GuestEvent, GuestEventKind, Signal
from storia.domain.ports import AuditLog, EventStore, SignalBus
from storia.domain.tenant import TenantContext


@dataclass(frozen=True, slots=True)
class RecordSignalRequest:
    tenant: TenantContext
    operator_id: OperatorId
    signal: Signal
    correlation_id: str


class RecordSignal:
    def __init__(self, *, events: EventStore, bus: SignalBus, audit: AuditLog) -> None:
        self._events = events
        self._bus = bus
        self._audit = audit

    async def __call__(self, req: RecordSignalRequest) -> int:
        req.tenant.assert_owns(req.operator_id)  # Rules §3.6
        sequence = await self._events.next_sequence(req.operator_id, req.signal.guest_id)
        event = GuestEvent.record(
            sequence=sequence,
            operator_id=req.operator_id,
            guest_id=req.signal.guest_id,
            kind=GuestEventKind.SIGNAL_RECORDED,
            body={"kind": req.signal.kind.value, **{k: v for k, v in req.signal.payload.items()}},
            source=req.signal.kind.value,
        )
        await self._events.append(event)
        await self._bus.publish(req.signal)
        await self._audit.emit(
            actor="system:storia.application.record_signal",
            action=f"signal.{req.signal.kind.value}",
            before_hash=None,
            after_hash=hashlib.sha256(event.model_dump_json().encode()).hexdigest(),
            correlation_id=req.correlation_id,
        )
        return sequence
