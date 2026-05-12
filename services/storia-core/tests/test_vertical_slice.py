"""End-to-end vertical slice (PRD §5, §8.1, Rules §5).

Mews-shaped booking payload → IngestBooking use case → GuestEvent appended →
identity resolved deterministically → BOOKING_CREATED signal published →
QueuePreArrivalActions produces an Action → audit log emitted →
ShiftView returns the queued action grouped under 'arriving'.

Substitutes in-memory adapters for every port (Rules §3.2, §5).
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from storia.application.ingest_booking import IngestBooking, IngestBookingRequest
from storia.application.queue_pre_arrival_actions import (
    QueuePreArrivalActions,
    QueuePreArrivalActionsRequest,
)
from storia.application.shift_view import ShiftView, ShiftViewRequest
from storia.domain.ids import OperatorId, PropertyId, StayId
from storia.domain.models import Booking, Signal, SignalKind
from storia.infrastructure.in_memory import (
    InMemoryActionQueue,
    InMemoryAuditLog,
    InMemoryEventStore,
    InMemoryIdentityResolver,
    InMemorySignalBus,
    StubReasoner,
)


@pytest.mark.asyncio
async def test_mews_booking_to_shift_view_end_to_end() -> None:
    events = InMemoryEventStore()
    identity = InMemoryIdentityResolver()
    bus = InMemorySignalBus()
    queue = InMemoryActionQueue()
    audit = InMemoryAuditLog()
    reasoner = StubReasoner()

    operator_id = OperatorId(uuid4())
    property_id = PropertyId(uuid4())

    booking = Booking.create(
        pms_booking_id="MEWS-R-1024",
        pms="mews",
        arrival=datetime(2026, 6, 1, 14, 0, tzinfo=UTC),
        departure=datetime(2026, 6, 4, 11, 0, tzinfo=UTC),
        room_code="OCEAN-412",
        rate_code="BAR",
        channel="direct",
    )

    ingest = IngestBooking(events=events, identity=identity, bus=bus, audit=audit)
    result = await ingest(IngestBookingRequest(
        operator_id=operator_id,
        property_id=property_id,
        booking=booking,
        guest_display_name="Ada Lovelace",
        guest_email="ada@example.com",
        guest_phone_e164="+447700900123",
        loyalty_number=None,
        correlation_id="corr-1",
    ))

    # Event ledger has one append for this guest.
    log = await events.load_for_guest(operator_id, type(booking).__name__ and result_to_guest_id(result))  # noqa: E501
    assert len(log) == 1
    assert log[0].source == "mews"
    assert log[0].body["pms_booking_id"] == "MEWS-R-1024"

    # BOOKING_CREATED published on the signal bus.
    assert len(bus.published) == 1
    assert bus.published[0].kind is SignalKind.BOOKING_CREATED

    # Audit entry recorded for ingestion.
    assert any(e["action"] == "booking.ingested" for e in audit.entries)

    # Idempotent identity: re-ingesting the same email yields the same guest.
    result2 = await ingest(IngestBookingRequest(
        operator_id=operator_id,
        property_id=property_id,
        booking=Booking.create(
            pms_booking_id="MEWS-R-1025", pms="mews",
            arrival=booking.arrival + timedelta(days=90),
            departure=booking.departure + timedelta(days=92),
        ),
        guest_display_name="Ada Lovelace",
        guest_email="ada@example.com",
        guest_phone_e164=None,
        loyalty_number=None,
        correlation_id="corr-2",
    ))
    assert result2.guest_id == result.guest_id

    # Action engine produces and queues actions from the booking signal.
    queue_uc = QueuePreArrivalActions(reasoner=reasoner, queue=queue, audit=audit)
    actions = await queue_uc(QueuePreArrivalActionsRequest(
        property_id=property_id,
        stay_id=StayId(uuid4()),
        playbook_id=uuid4(),
        auto_approve_threshold=0.85,
        triggering_signals=tuple(bus.published[:1]),
        correlation_id="corr-3",
    ))
    assert len(actions) == 1
    a = actions[0]
    assert a.kind == "pms.note.add"
    assert a.status.value == "auto_approved"  # confidence 0.92, reversible True
    assert a.reasoning  # every action carries the "why" (FR-PA-6)

    # Audit log includes the action entry.
    assert any(e["action"].startswith("action.") for e in audit.entries)

    # Shift view picks up the queued action.
    shift = ShiftView(queue=queue)
    view = await shift(ShiftViewRequest(property_id=property_id))
    assert len(view.arriving) == 1
    assert view.arriving[0].id == a.id


def result_to_guest_id(result):  # tiny helper to keep the test readable
    from uuid import UUID

    from storia.domain.ids import GuestId
    return GuestId(UUID(result.guest_id))
