"""MCP server schema-compliance + round-trip tests (Rules §5).

Servers are thin delegators to application use cases. These tests assert that the
JSON payloads on the wire validate and dispatch correctly.
"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from storia.application.ingest_booking import IngestBooking
from storia.application.queue_pre_arrival_actions import QueuePreArrivalActions
from storia.application.shift_view import ShiftView
from storia.domain.ids import PropertyId
from storia.domain.models import Signal, SignalKind
from storia.infrastructure.in_memory import (
    InMemoryActionQueue,
    InMemoryAuditLog,
    InMemoryEventStore,
    InMemoryIdentityResolver,
    InMemorySignalBus,
    StubReasoner,
)
from storia.infrastructure.mcp.action_engine_server import ActionEngineServer
from storia.infrastructure.mcp.guest_signal_server import GuestSignalServer


def _wire() -> tuple[GuestSignalServer, ActionEngineServer, InMemoryActionQueue, InMemorySignalBus]:
    events = InMemoryEventStore()
    identity = InMemoryIdentityResolver()
    bus = InMemorySignalBus()
    queue = InMemoryActionQueue()
    audit = InMemoryAuditLog()
    reasoner = StubReasoner()
    ingest = IngestBooking(events=events, identity=identity, bus=bus, audit=audit)
    queue_uc = QueuePreArrivalActions(reasoner=reasoner, queue=queue, audit=audit)
    shift = ShiftView(queue=queue)
    return (
        GuestSignalServer(ingest_use_case=ingest),
        ActionEngineServer(queue_use_case=queue_uc, shift_use_case=shift),
        queue,
        bus,
    )


@pytest.mark.asyncio
async def test_guest_signal_server_ingest_round_trip() -> None:
    gs, _, _, bus = _wire()
    operator_id = str(uuid4())
    property_id = str(uuid4())

    result = await gs.tool_ingest_booking({
        "operator_id": operator_id,
        "property_id": property_id,
        "booking": {
            "pms_booking_id": "MEWS-77",
            "pms": "mews",
            "arrival": "2026-06-01T14:00:00+00:00",
            "departure": "2026-06-04T11:00:00+00:00",
            "room_code": "OCEAN-412",
            "rate_code": "BAR",
            "channel": "direct",
        },
        "guest": {
            "display_name": "Grace Hopper",
            "email": "grace@example.com",
            "phone_e164": None,
            "loyalty_number": None,
        },
        "correlation_id": "mcp-corr-1",
    })
    assert "guest_id" in result
    assert result["sequence"] == 0
    assert len(bus.published) == 1


@pytest.mark.asyncio
async def test_action_engine_server_queue_and_shift_round_trip() -> None:
    gs, ae, queue, bus = _wire()
    operator_id = str(uuid4())
    property_id = str(uuid4())

    # Seed a signal via Guest Signal server.
    await gs.tool_ingest_booking({
        "operator_id": operator_id,
        "property_id": property_id,
        "booking": {
            "pms_booking_id": "MEWS-99",
            "pms": "mews",
            "arrival": "2026-07-01T14:00:00+00:00",
            "departure": "2026-07-03T11:00:00+00:00",
            "room_code": None, "rate_code": None, "channel": None,
        },
        "guest": {
            "display_name": "Alan Turing",
            "email": "alan@example.com",
            "phone_e164": None, "loyalty_number": None,
        },
        "correlation_id": "mcp-corr-2",
    })

    # Queue actions via Action Engine server.
    signal_payload = bus.published[0].model_dump(mode="json")
    queued = await ae.tool_queue_pre_arrival_actions({
        "property_id": property_id,
        "stay_id": str(uuid4()),
        "playbook_id": str(uuid4()),
        "auto_approve_threshold": 0.85,
        "signals": [signal_payload],
        "correlation_id": "mcp-corr-3",
    })
    assert len(queued["actions"]) == 1
    assert queued["actions"][0]["kind"] == "pms.note.add"

    # Shift resource picks it up.
    view = await ae.resource_shift(property_id)
    assert len(view["arriving"]) == 1


@pytest.mark.asyncio
async def test_action_engine_rejects_disallowed_kind_from_reasoner() -> None:
    """Rules §4.2 — reject by default. Reasoner emitting an unknown action kind is dropped."""
    queue = InMemoryActionQueue()
    audit = InMemoryAuditLog()
    reasoner = StubReasoner(scripted={
        "reason:ProposedActions": {
            "proposals": [
                {
                    "kind": "delete.guest.row",  # not in allowlist
                    "payload": {},
                    "reasoning": ["bad actor"],
                    "confidence": 0.99,
                    "reversible": False,
                },
            ]
        }
    })
    queue_uc = QueuePreArrivalActions(reasoner=reasoner, queue=queue, audit=audit)
    ae = ActionEngineServer(queue_use_case=queue_uc, shift_use_case=ShiftView(queue=queue))

    from storia.domain.ids import GuestId
    fake_signal = Signal.observe(
        guest_id=GuestId(uuid4()),
        property_id=PropertyId(uuid4()),
        kind=SignalKind.BOOKING_CREATED,
        occurred_at=datetime.now(UTC),
        payload={},
    )
    result = await ae.tool_queue_pre_arrival_actions({
        "property_id": str(fake_signal.property_id),
        "stay_id": str(uuid4()),
        "playbook_id": str(uuid4()),
        "auto_approve_threshold": 0.85,
        "signals": [fake_signal.model_dump(mode="json")],
        "correlation_id": "mcp-corr-4",
    })
    assert result["actions"] == []
