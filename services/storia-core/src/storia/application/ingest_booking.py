"""
Module: storia.application.ingest_booking
Layer: application
Ports: EventStore, IdentityResolver, SignalBus, AuditLog
MCP integration: exposed as MCP tool `ingest_booking` in infrastructure
Stack: stdlib + storia.domain

Use case for PRD FR-PA-1: on booking ingestion, identity resolve and profile assemble
within 60 seconds. Emits a SignalKind.BOOKING_CREATED for downstream playbook evaluation.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime

from storia.domain.ids import OperatorId, PropertyId
from storia.domain.models import (
    Booking,
    GuestEvent,
    GuestEventKind,
    Signal,
    SignalKind,
)
from storia.domain.ports import (
    AuditLog,
    EventStore,
    IdentityResolver,
    SignalBus,
)


@dataclass(frozen=True, slots=True)
class IngestBookingRequest:
    operator_id: OperatorId
    property_id: PropertyId
    booking: Booking
    guest_display_name: str
    guest_email: str | None
    guest_phone_e164: str | None
    loyalty_number: str | None
    correlation_id: str


@dataclass(frozen=True, slots=True)
class IngestBookingResult:
    guest_id: str
    sequence: int


class IngestBooking:
    def __init__(self, *, events: EventStore, identity: IdentityResolver,
                 bus: SignalBus, audit: AuditLog) -> None:
        self._events = events
        self._identity = identity
        self._bus = bus
        self._audit = audit

    async def __call__(self, req: IngestBookingRequest) -> IngestBookingResult:
        email_hash = _sha256(req.guest_email.lower().strip()) if req.guest_email else None
        phone_hash = _sha256(req.guest_phone_e164) if req.guest_phone_e164 else None

        guest = await self._identity.resolve(
            operator_id=req.operator_id,
            email_hash=email_hash,
            phone_hash=phone_hash,
            loyalty_number=req.loyalty_number,
            display_name=req.guest_display_name,
        )

        sequence = await self._events.next_sequence(req.operator_id, guest.id)
        event = GuestEvent.record(
            sequence=sequence,
            operator_id=req.operator_id,
            guest_id=guest.id,
            kind=GuestEventKind.BOOKING_ATTACHED,
            body={
                "pms": req.booking.pms,
                "pms_booking_id": req.booking.pms_booking_id,
                "arrival": req.booking.arrival.isoformat(),
                "departure": req.booking.departure.isoformat(),
                "room_code": req.booking.room_code,
            },
            source=req.booking.pms,
        )
        await self._events.append(event)

        signal = Signal.observe(
            guest_id=guest.id,
            property_id=req.property_id,
            kind=SignalKind.BOOKING_CREATED,
            occurred_at=datetime.now(UTC),
            payload={
                "pms_booking_id": req.booking.pms_booking_id,
                "arrival": req.booking.arrival.isoformat(),
            },
        )
        await self._bus.publish(signal)

        await self._audit.emit(
            actor=f"system:storia.application.ingest_booking",
            action="booking.ingested",
            before_hash=None,
            after_hash=_hash_event(event),
            correlation_id=req.correlation_id,
        )

        return IngestBookingResult(guest_id=str(guest.id), sequence=sequence)


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _hash_event(event: GuestEvent) -> str:
    return _sha256(event.model_dump_json())
