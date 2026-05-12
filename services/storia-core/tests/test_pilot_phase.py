"""Pilot-phase tests (PRD §11.2): record_signal, evaluate_playbook on each of P1/P2/P3,
probabilistic identity resolution, multi-tenant isolation enforcement."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from storia.application.evaluate_playbook import EvaluatePlaybook, EvaluatePlaybookRequest
from storia.application.playbooks import (
    in_stay_fb_upsell,
    in_stay_recovery_flag,
    pre_arrival_room_readiness,
)
from storia.application.record_signal import RecordSignal, RecordSignalRequest
from storia.application.ingest_booking import IngestBooking, IngestBookingRequest
from storia.domain.ids import GuestId, OperatorId, PropertyId, StayId
from storia.domain.models import Booking, Signal, SignalKind
from storia.domain.tenant import CrossTenantAccessError, TenantContext
from storia.infrastructure.in_memory import (
    InMemoryActionQueue,
    InMemoryAuditLog,
    InMemoryEventStore,
    InMemoryIdentityResolver,
    InMemoryReviewQueue,
    InMemorySignalBus,
)
from storia.infrastructure.probabilistic_identity import (
    THRESHOLD_QUEUE,
    ProbabilisticIdentityResolver,
)


def _sig(kind: SignalKind, payload: dict[str, object] | None = None) -> Signal:
    return Signal.observe(
        guest_id=GuestId(uuid4()),
        property_id=PropertyId(uuid4()),
        kind=kind,
        occurred_at=datetime.now(UTC),
        payload=dict(payload or {}),
    )


# ---- record_signal ----

@pytest.mark.asyncio
async def test_record_signal_appends_event_and_publishes() -> None:
    events = InMemoryEventStore()
    bus = InMemorySignalBus()
    audit = InMemoryAuditLog()
    operator = OperatorId(uuid4())
    rec = RecordSignal(events=events, bus=bus, audit=audit)

    signal = _sig(SignalKind.POS_TRANSACTION, {"item": "wine_pairing", "amount": 80})
    seq = await rec(RecordSignalRequest(
        tenant=TenantContext(operator_id=operator),
        operator_id=operator, signal=signal, correlation_id="c1",
    ))
    assert seq == 0
    assert len(bus.published) == 1
    assert any(e["action"] == "signal.pos.transaction" for e in audit.entries)


@pytest.mark.asyncio
async def test_record_signal_rejects_cross_tenant() -> None:
    events = InMemoryEventStore()
    rec = RecordSignal(events=events, bus=InMemorySignalBus(), audit=InMemoryAuditLog())
    own = OperatorId(uuid4())
    other = OperatorId(uuid4())
    with pytest.raises(CrossTenantAccessError):
        await rec(RecordSignalRequest(
            tenant=TenantContext(operator_id=own),
            operator_id=other,
            signal=_sig(SignalKind.POS_TRANSACTION),
            correlation_id="c-bad",
        ))


# ---- ingest_booking tenant guard ----

@pytest.mark.asyncio
async def test_ingest_booking_rejects_cross_tenant() -> None:
    own, other = OperatorId(uuid4()), OperatorId(uuid4())
    ingest = IngestBooking(
        events=InMemoryEventStore(), identity=InMemoryIdentityResolver(),
        bus=InMemorySignalBus(), audit=InMemoryAuditLog(),
    )
    booking = Booking.create(
        pms_booking_id="X", pms="mews",
        arrival=datetime(2026, 9, 1, tzinfo=UTC),
        departure=datetime(2026, 9, 3, tzinfo=UTC),
    )
    with pytest.raises(CrossTenantAccessError):
        await ingest(IngestBookingRequest(
            tenant=TenantContext(operator_id=own),
            operator_id=other,
            property_id=PropertyId(uuid4()),
            booking=booking,
            guest_display_name="Z",
            guest_email=None, guest_phone_e164=None, loyalty_number=None,
            correlation_id="c-bad",
        ))


# ---- evaluate_playbook: P1 pre-arrival ----

@pytest.mark.asyncio
async def test_p1_pre_arrival_emits_two_actions_with_sufficient_lead() -> None:
    queue = InMemoryActionQueue()
    audit = InMemoryAuditLog()
    ev = EvaluatePlaybook(queue=queue, audit=audit)

    actions = await ev(EvaluatePlaybookRequest(
        playbook=pre_arrival_room_readiness(),
        signal=_sig(SignalKind.BOOKING_CREATED),
        stay_id=StayId(uuid4()),
        property_id=PropertyId(uuid4()),
        correlation_id="p1",
        lead_hours=48,
    ))
    kinds = {a.kind for a in actions}
    assert kinds == {"pms.note.add", "operator.alert"}
    # FR-PA-6: every action carries reasoning.
    assert all(a.reasoning for a in actions)


@pytest.mark.asyncio
async def test_p1_pre_arrival_blocked_when_lead_too_short() -> None:
    queue = InMemoryActionQueue()
    ev = EvaluatePlaybook(queue=queue, audit=InMemoryAuditLog())

    actions = await ev(EvaluatePlaybookRequest(
        playbook=pre_arrival_room_readiness(),
        signal=_sig(SignalKind.BOOKING_CREATED),
        stay_id=StayId(uuid4()),
        property_id=PropertyId(uuid4()),
        correlation_id="p1-short",
        lead_hours=1,
    ))
    assert actions == []


# ---- P2 in-stay F&B upsell ----

@pytest.mark.asyncio
async def test_p2_fb_upsell_respects_fatigue_rule_fr_is_5() -> None:
    ev = EvaluatePlaybook(queue=InMemoryActionQueue(), audit=InMemoryAuditLog())

    # 2 suggestions in last 24h → ok
    actions = await ev(EvaluatePlaybookRequest(
        playbook=in_stay_fb_upsell(),
        signal=_sig(SignalKind.POS_TRANSACTION),
        stay_id=StayId(uuid4()),
        property_id=PropertyId(uuid4()),
        correlation_id="p2-ok",
        suggestions_last_24h=2,
    ))
    assert len(actions) == 1
    assert actions[0].kind == "messaging.draft"

    # 3 suggestions → blocked
    actions = await ev(EvaluatePlaybookRequest(
        playbook=in_stay_fb_upsell(),
        signal=_sig(SignalKind.POS_TRANSACTION),
        stay_id=StayId(uuid4()),
        property_id=PropertyId(uuid4()),
        correlation_id="p2-blocked",
        suggestions_last_24h=3,
    ))
    assert actions == []


# ---- P3 in-stay recovery flag ----

@pytest.mark.asyncio
async def test_p3_recovery_never_auto_executes_and_is_irreversible() -> None:
    ev = EvaluatePlaybook(queue=InMemoryActionQueue(), audit=InMemoryAuditLog())

    actions = await ev(EvaluatePlaybookRequest(
        playbook=in_stay_recovery_flag(),
        signal=_sig(SignalKind.COMPLAINT, {"summary": "cold pasta"}),
        stay_id=StayId(uuid4()),
        property_id=PropertyId(uuid4()),
        correlation_id="p3",
    ))
    assert len(actions) == 1
    a = actions[0]
    # Recovery is always human-led (PRD §5.2.2 + invariant in Action.propose).
    assert a.reversible is False
    assert a.status.value == "queued"


@pytest.mark.asyncio
async def test_evaluate_playbook_returns_empty_when_trigger_does_not_match() -> None:
    ev = EvaluatePlaybook(queue=InMemoryActionQueue(), audit=InMemoryAuditLog())
    actions = await ev(EvaluatePlaybookRequest(
        playbook=pre_arrival_room_readiness(),
        signal=_sig(SignalKind.POS_TRANSACTION),  # P1 wants booking.created
        stay_id=StayId(uuid4()),
        property_id=PropertyId(uuid4()),
        correlation_id="p1-mismatch",
        lead_hours=48,
    ))
    assert actions == []


# ---- probabilistic identity resolution ----

@pytest.mark.asyncio
async def test_probabilistic_resolver_deterministic_match_returns_existing() -> None:
    queue = InMemoryReviewQueue()
    r = ProbabilisticIdentityResolver(queue=queue)
    op = OperatorId(uuid4())

    g1 = await r.resolve(operator_id=op, email_hash="hash-1",
                         phone_hash=None, loyalty_number=None, display_name="Ada Lovelace")
    g2 = await r.resolve(operator_id=op, email_hash="hash-1",
                         phone_hash=None, loyalty_number=None, display_name="Ada L.")
    assert g1.id == g2.id
    assert await queue.list_pending(op) == []


@pytest.mark.asyncio
async def test_probabilistic_resolver_high_name_overlap_queues_merge_candidate() -> None:
    queue = InMemoryReviewQueue()
    r = ProbabilisticIdentityResolver(queue=queue)
    op = OperatorId(uuid4())

    g1 = await r.resolve(operator_id=op, email_hash="hash-A",
                         phone_hash=None, loyalty_number=None,
                         display_name="Ada Lovelace Byron")
    g2 = await r.resolve(operator_id=op, email_hash="hash-B",
                         phone_hash=None, loyalty_number=None,
                         display_name="Ada Lovelace Byron")
    # Different email hashes → no deterministic match, but identical names → queued.
    assert g1.id != g2.id  # not auto-merged (PRD §6.3 — no destructive merges in v1)
    pending = await queue.list_pending(op)
    assert len(pending) == 1
    assert pending[0]["confidence"] >= THRESHOLD_QUEUE


@pytest.mark.asyncio
async def test_probabilistic_resolver_low_overlap_does_not_queue() -> None:
    queue = InMemoryReviewQueue()
    r = ProbabilisticIdentityResolver(queue=queue)
    op = OperatorId(uuid4())

    await r.resolve(operator_id=op, email_hash=None, phone_hash=None,
                    loyalty_number=None, display_name="Ada Lovelace")
    await r.resolve(operator_id=op, email_hash=None, phone_hash=None,
                    loyalty_number=None, display_name="Grace Hopper")
    assert await queue.list_pending(op) == []


# ---- tenant context ----

def test_tenant_context_allows_matching_operator() -> None:
    op = OperatorId(uuid4())
    TenantContext(operator_id=op).assert_owns(op)  # no raise


def test_tenant_context_blocks_different_operator() -> None:
    a, b = OperatorId(uuid4()), OperatorId(uuid4())
    with pytest.raises(CrossTenantAccessError):
        TenantContext(operator_id=a).assert_owns(b)
