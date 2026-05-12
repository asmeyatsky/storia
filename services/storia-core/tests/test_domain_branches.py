"""Branch coverage for storia.domain.* — Rules §5 floor ≥95% per layer."""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from storia.domain.ids import GuestId, OperatorId, PropertyId, StayId
from storia.domain.models import (
    Action,
    Booking,
    GuestEvent,
    GuestEventKind,
    Signal,
    SignalKind,
    Stay,
)
from storia.domain.playbook import (
    Guardrail,
    NodeKind,
    Playbook,
    PlaybookId,
    PlaybookNode,
)


# ---- ids.py: type-check guard ----

def test_id_rejects_non_uuid() -> None:
    with pytest.raises(TypeError, match="requires UUID"):
        GuestId("not-a-uuid")  # type: ignore[arg-type]


def test_id_str_renders_uuid() -> None:
    u = uuid4()
    assert str(GuestId(u)) == str(u)


# ---- models.py: each remaining branch ----

def test_booking_rejects_empty_pms_booking_id() -> None:
    with pytest.raises(ValueError, match="pms_booking_id"):
        Booking.create(
            pms_booking_id="", pms="mews",
            arrival=datetime(2026, 6, 1, tzinfo=UTC),
            departure=datetime(2026, 6, 2, tzinfo=UTC),
        )


def test_signal_rejects_naive_occurred_at() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        Signal.observe(
            guest_id=GuestId(uuid4()),
            property_id=PropertyId(uuid4()),
            kind=SignalKind.BOOKING_CREATED,
            occurred_at=datetime(2026, 6, 1, 14, 0),  # naive
            payload={},
        )


def test_stay_begin_returns_new_instance() -> None:
    booking = Booking.create(
        pms_booking_id="R-x", pms="mews",
        arrival=datetime(2026, 6, 1, tzinfo=UTC),
        departure=datetime(2026, 6, 2, tzinfo=UTC),
    )
    s = Stay.begin(guest_id=GuestId(uuid4()), property_id=PropertyId(uuid4()), booking=booking)
    assert s.booking is booking


def test_action_propose_rejects_empty_kind() -> None:
    with pytest.raises(ValueError, match="kind required"):
        Action.propose(
            stay_id=StayId(uuid4()), property_id=PropertyId(uuid4()),
            playbook_id=uuid4(), kind="", payload={},
            reasoning=("r",), reversible=True, auto_approved=True,
        )


def test_action_executed_rejects_non_pending_status() -> None:
    a = Action.propose(
        stay_id=StayId(uuid4()), property_id=PropertyId(uuid4()),
        playbook_id=uuid4(), kind="pms.note.add", payload={},
        reasoning=("r",), reversible=True, auto_approved=True,
    )
    executed = a.executed()
    with pytest.raises(ValueError, match="cannot execute"):
        executed.executed()


def test_action_rejected_path_and_blocks_after_execute() -> None:
    a = Action.propose(
        stay_id=StayId(uuid4()), property_id=PropertyId(uuid4()),
        playbook_id=uuid4(), kind="pms.note.add", payload={},
        reasoning=("r",), reversible=True, auto_approved=False,
    )
    rej = a.rejected()
    assert rej.status.value == "rejected"

    executed = a.executed()
    with pytest.raises(ValueError, match="cannot be rejected"):
        executed.rejected()


def test_action_reverse_requires_executed_state() -> None:
    a = Action.propose(
        stay_id=StayId(uuid4()), property_id=PropertyId(uuid4()),
        playbook_id=uuid4(), kind="pms.note.add", payload={},
        reasoning=("r",), reversible=True, auto_approved=True,
    )
    with pytest.raises(ValueError, match="only executed actions"):
        a.reversed_()


def test_guest_event_rejects_negative_sequence() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        GuestEvent.record(
            sequence=-1,
            operator_id=OperatorId(uuid4()),
            guest_id=GuestId(uuid4()),
            kind=GuestEventKind.BOOKING_ATTACHED,
            body={}, source="mews",
        )


# ---- playbook.py: each remaining branch ----

def _act(key: str, nxt: tuple[str, ...] = ()) -> PlaybookNode:
    return PlaybookNode(key=key, kind=NodeKind.ACTION, spec={}, next=nxt)


def _trig(key: str, nxt: tuple[str, ...]) -> PlaybookNode:
    return PlaybookNode(key=key, kind=NodeKind.TRIGGER, spec={}, next=nxt)


def test_playbook_rejects_blank_name() -> None:
    with pytest.raises(ValueError, match="name required"):
        Playbook.from_graph(
            id=PlaybookId(uuid4()), name="   ", version=1,
            nodes=[_trig("t", ("a",)), _act("a")], guardrails=[],
        )


def test_playbook_rejects_zero_version() -> None:
    with pytest.raises(ValueError, match="version"):
        Playbook.from_graph(
            id=PlaybookId(uuid4()), name="x", version=0,
            nodes=[_trig("t", ("a",)), _act("a")], guardrails=[],
        )


def test_playbook_rejects_duplicate_keys() -> None:
    with pytest.raises(ValueError, match="unique"):
        Playbook.from_graph(
            id=PlaybookId(uuid4()), name="x", version=1,
            nodes=[_trig("t", ("a",)), _act("a"), _act("a")], guardrails=[],
        )


def test_playbook_rejects_unknown_next() -> None:
    with pytest.raises(ValueError, match="unknown next"):
        Playbook.from_graph(
            id=PlaybookId(uuid4()), name="x", version=1,
            nodes=[_trig("t", ("missing",)), _act("a")], guardrails=[],
        )


def test_playbook_rejects_no_trigger() -> None:
    with pytest.raises(ValueError, match="at least one trigger"):
        Playbook.from_graph(
            id=PlaybookId(uuid4()), name="x", version=1,
            nodes=[_act("a")], guardrails=[],
        )


def test_playbook_rejects_no_action() -> None:
    with pytest.raises(ValueError, match="at least one action"):
        Playbook.from_graph(
            id=PlaybookId(uuid4()), name="x", version=1,
            nodes=[_trig("t", ())], guardrails=[],
        )


def test_playbook_reachable_traversal_dedupes_nodes() -> None:
    """Diamond DAG: same node reachable by two paths exercises the `seen` continue branch."""
    nodes = [
        _trig("t", ("a", "b")),
        PlaybookNode(key="a", kind=NodeKind.GUARDRAIL, spec={}, next=("z",)),
        PlaybookNode(key="b", kind=NodeKind.GUARDRAIL, spec={}, next=("z",)),
        _act("z"),
    ]
    pb = Playbook.from_graph(
        id=PlaybookId(uuid4()), name="diamond", version=1,
        nodes=nodes, guardrails=[Guardrail(predicate="ok",
                                           on_pass="auto_execute", on_fail="escalate")],
    )
    assert len(pb.nodes) == 4
