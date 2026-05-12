"""Domain unit tests — pure logic, zero mocks (Rules §5)."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from storia.domain.ids import PropertyId, StayId
from storia.domain.models import (
    Action,
    ActionStatus,
    Booking,
    Guest,
    GuestEvent,
    GuestEventKind,
    OperatorId,
    Signal,
    SignalKind,
)
from storia.domain.playbook import (
    Guardrail,
    NodeKind,
    Playbook,
    PlaybookId,
    PlaybookNode,
)


def _arrival() -> datetime:
    return datetime(2026, 6, 1, 14, 0, tzinfo=UTC)


def test_booking_rejects_naive_datetimes() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        Booking.create(
            pms_booking_id="R1", pms="mews",
            arrival=datetime(2026, 6, 1, 14, 0),
            departure=datetime(2026, 6, 2, 11, 0),
        )


def test_booking_rejects_inverted_dates() -> None:
    with pytest.raises(ValueError, match="strictly after"):
        Booking.create(
            pms_booking_id="R1", pms="mews",
            arrival=_arrival(), departure=_arrival(),
        )


def test_booking_rejects_unknown_pms() -> None:
    with pytest.raises(ValueError, match="unsupported pms"):
        Booking.create(
            pms_booking_id="R1", pms="acme-pms",
            arrival=_arrival(), departure=_arrival() + timedelta(days=2),
        )


def test_guest_requires_display_name() -> None:
    with pytest.raises(ValueError, match="display_name"):
        Guest.new(display_name="   ")


def test_signal_rejects_future_timestamps() -> None:
    with pytest.raises(ValueError, match="future"):
        Signal.observe(
            guest_id=Guest.new("X").id,
            property_id=PropertyId(uuid4()),
            kind=SignalKind.BOOKING_CREATED,
            occurred_at=datetime.now(UTC) + timedelta(hours=1),
            payload={},
        )


def test_action_requires_reasoning() -> None:
    with pytest.raises(ValueError, match="reasoning"):
        Action.propose(
            stay_id=StayId(uuid4()), property_id=PropertyId(uuid4()),
            playbook_id=uuid4(), kind="pms.note.add", payload={},
            reasoning=(), reversible=True, auto_approved=True,
        )


def test_non_reversible_action_cannot_auto_approve() -> None:
    with pytest.raises(ValueError, match="reversible"):
        Action.propose(
            stay_id=StayId(uuid4()), property_id=PropertyId(uuid4()),
            playbook_id=uuid4(), kind="pms.note.add", payload={},
            reasoning=("test",), reversible=False, auto_approved=True,
        )


def test_action_state_transitions_return_new_instance() -> None:
    a = Action.propose(
        stay_id=StayId(uuid4()), property_id=PropertyId(uuid4()),
        playbook_id=uuid4(), kind="pms.note.add", payload={},
        reasoning=("test",), reversible=True, auto_approved=True,
    )
    executed = a.executed()
    assert executed is not a
    assert executed.status is ActionStatus.EXECUTED
    assert a.status is ActionStatus.AUTO_APPROVED  # immutable

    reversed_ = executed.reversed_()
    assert reversed_.status is ActionStatus.REVERSED


def test_action_cannot_reverse_unreversible() -> None:
    a = Action.propose(
        stay_id=StayId(uuid4()), property_id=PropertyId(uuid4()),
        playbook_id=uuid4(), kind="pms.note.add", payload={},
        reasoning=("test",), reversible=False, auto_approved=False,
    )
    executed = a.executed()
    with pytest.raises(ValueError, match="not reversible"):
        executed.reversed_()


def test_guest_event_requires_source() -> None:
    with pytest.raises(ValueError, match="source"):
        GuestEvent.record(
            sequence=0, operator_id=OperatorId(uuid4()), guest_id=Guest.new("X").id,
            kind=GuestEventKind.BOOKING_ATTACHED, body={}, source="",
        )


def test_playbook_rejects_cycle() -> None:
    nodes = [
        PlaybookNode(key="t", kind=NodeKind.TRIGGER, spec={}, next=("a",)),
        PlaybookNode(key="a", kind=NodeKind.ACTION, spec={}, next=("t",)),
    ]
    with pytest.raises(ValueError, match="cycle"):
        Playbook.from_graph(
            id=PlaybookId(uuid4()), name="bad", version=1,
            nodes=nodes, guardrails=[],
        )


def test_playbook_rejects_unreachable_action() -> None:
    nodes = [
        PlaybookNode(key="t", kind=NodeKind.TRIGGER, spec={}, next=()),
        PlaybookNode(key="a", kind=NodeKind.ACTION, spec={}, next=()),
    ]
    with pytest.raises(ValueError, match="unreachable"):
        Playbook.from_graph(
            id=PlaybookId(uuid4()), name="orphan", version=1,
            nodes=nodes, guardrails=[],
        )


def test_playbook_happy_path() -> None:
    nodes = [
        PlaybookNode(key="t", kind=NodeKind.TRIGGER, spec={}, next=("g",)),
        PlaybookNode(key="g", kind=NodeKind.GUARDRAIL, spec={}, next=("a",)),
        PlaybookNode(key="a", kind=NodeKind.ACTION, spec={"kind": "pms.note.add"}, next=()),
    ]
    pb = Playbook.from_graph(
        id=PlaybookId(uuid4()), name="pre-arrival", version=1,
        nodes=nodes,
        guardrails=[Guardrail(predicate="confidence >= 0.85",
                              on_pass="auto_execute", on_fail="escalate")],
    )
    assert pb.version == 1
    assert len(pb.nodes) == 3
