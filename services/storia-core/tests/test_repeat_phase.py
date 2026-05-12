"""Repeat-phase tests (PRD §11.3): group KPI roll-up, KPI attribution, outcome billing."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from storia.application.group_kpis import GroupKpiRequest, GroupKpiView
from storia.application.outcome_billing import (
    OutcomeBilling,
    ReconcileBillingRequest,
    Tier,
)
from storia.domain.ids import PropertyId
from storia.domain.kpis import AttributedKpis, GroupKpis, PropertyKpis
from storia.domain.tenant import TenantContext
from storia.infrastructure.in_memory import InMemoryAuditLog


def _kpis(*, property_id: PropertyId | None = None,
          revenue: float = 100.0, repeat: float = 0.35, review: float = 4.2,
          recovery_min: float = 30.0, dau: float = 0.8, actions: int = 50,
          start: datetime | None = None, end: datetime | None = None) -> PropertyKpis:
    start = start or datetime(2026, 1, 1, tzinfo=UTC)
    end = end or datetime(2026, 4, 1, tzinfo=UTC)
    return PropertyKpis.measured(
        property_id=property_id or PropertyId(uuid4()),
        window_start=start, window_end=end,
        revenue_per_guest_night=revenue,
        repeat_stay_rate=repeat,
        avg_review_score=review,
        median_recovery_minutes=recovery_min,
        staff_dau_ratio=dau,
        storia_action_count=actions,
    )


# ---- PropertyKpis invariants ----

def test_property_kpis_rejects_inverted_window() -> None:
    with pytest.raises(ValueError, match="strictly after"):
        PropertyKpis.measured(
            property_id=PropertyId(uuid4()),
            window_start=datetime(2026, 4, 1, tzinfo=UTC),
            window_end=datetime(2026, 1, 1, tzinfo=UTC),
            revenue_per_guest_night=1.0, repeat_stay_rate=0.0,
            avg_review_score=0.0, median_recovery_minutes=0.0,
            staff_dau_ratio=0.0, storia_action_count=0,
        )


def test_property_kpis_rejects_naive_windows() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        PropertyKpis.measured(
            property_id=PropertyId(uuid4()),
            window_start=datetime(2026, 1, 1),
            window_end=datetime(2026, 4, 1),
            revenue_per_guest_night=1.0, repeat_stay_rate=0.0,
            avg_review_score=0.0, median_recovery_minutes=0.0,
            staff_dau_ratio=0.0, storia_action_count=0,
        )


# ---- AttributedKpis ----

def test_attributed_kpis_computes_deltas() -> None:
    pid = PropertyId(uuid4())
    baseline = _kpis(property_id=pid, revenue=80.0, repeat=0.30, review=4.0,
                     recovery_min=50.0,
                     start=datetime(2025, 10, 1, tzinfo=UTC),
                     end=datetime(2025, 12, 31, tzinfo=UTC))
    current = _kpis(property_id=pid, revenue=98.0, repeat=0.34, review=4.3,
                    recovery_min=32.0,
                    start=datetime(2026, 1, 1, tzinfo=UTC),
                    end=datetime(2026, 4, 1, tzinfo=UTC))
    a = AttributedKpis.compute(current=current, baseline=baseline)
    assert a.revenue_uplift_per_guest_night == pytest.approx(18.0)
    assert a.repeat_stay_rate_delta == pytest.approx(0.04)
    assert a.review_score_delta == pytest.approx(0.3)
    assert a.recovery_time_reduction_minutes == pytest.approx(18.0)


def test_attributed_kpis_rejects_different_properties() -> None:
    baseline = _kpis()
    current = _kpis()
    with pytest.raises(ValueError, match="same property"):
        AttributedKpis.compute(current=current, baseline=baseline)


def test_attributed_kpis_rejects_overlapping_windows() -> None:
    pid = PropertyId(uuid4())
    baseline = _kpis(property_id=pid,
                     start=datetime(2026, 1, 1, tzinfo=UTC),
                     end=datetime(2026, 4, 1, tzinfo=UTC))
    current = _kpis(property_id=pid,
                    start=datetime(2026, 3, 1, tzinfo=UTC),
                    end=datetime(2026, 6, 1, tzinfo=UTC))
    with pytest.raises(ValueError, match="after baseline"):
        AttributedKpis.compute(current=current, baseline=baseline)


# ---- GroupKpis rollup ----

def test_group_rollup_weights_by_action_count() -> None:
    a = _kpis(revenue=100.0, actions=10)
    b = _kpis(revenue=50.0, actions=90)
    g = GroupKpis.rollup([a, b])
    # Weighted = (100*10 + 50*90) / 100 = 55
    assert g.revenue_per_guest_night == pytest.approx(55.0)
    assert g.total_action_count == 100


def test_group_rollup_falls_back_to_mean_when_no_actions() -> None:
    a = _kpis(revenue=100.0, actions=0)
    b = _kpis(revenue=50.0, actions=0)
    g = GroupKpis.rollup([a, b])
    assert g.revenue_per_guest_night == pytest.approx(75.0)


def test_group_rollup_rejects_empty() -> None:
    with pytest.raises(ValueError, match="at least one"):
        GroupKpis.rollup([])


# ---- GroupKpiView use case ----

class _StubMetrics:
    def __init__(self, by_property: dict[str, PropertyKpis]) -> None:
        self._by = by_property

    async def read(self, *, property_id: PropertyId, window_days: int) -> object:
        return self._by[str(property_id)]


@pytest.mark.asyncio
async def test_group_kpi_view_rolls_up_via_port() -> None:
    p1 = PropertyId(uuid4())
    p2 = PropertyId(uuid4())
    metrics = _StubMetrics({
        str(p1): _kpis(property_id=p1, revenue=110.0, actions=40),
        str(p2): _kpis(property_id=p2, revenue=90.0, actions=60),
    })
    view = GroupKpiView(metrics=metrics)
    g = await view(GroupKpiRequest(
        tenant=TenantContext(operator_id=__import__("storia.domain.ids", fromlist=["OperatorId"]).OperatorId(uuid4())),
        property_ids=(p1, p2), window_days=90,
    ))
    # Weighted = (110*40 + 90*60) / 100 = 98
    assert g.revenue_per_guest_night == pytest.approx(98.0)


@pytest.mark.asyncio
async def test_group_kpi_view_rejects_empty_property_list() -> None:
    from storia.domain.ids import OperatorId
    view = GroupKpiView(metrics=_StubMetrics({}))
    with pytest.raises(ValueError, match="at least one"):
        await view(GroupKpiRequest(
            tenant=TenantContext(operator_id=OperatorId(uuid4())),
            property_ids=(), window_days=90,
        ))


@pytest.mark.asyncio
async def test_group_kpi_view_rejects_zero_window() -> None:
    from storia.domain.ids import OperatorId
    view = GroupKpiView(metrics=_StubMetrics({}))
    with pytest.raises(ValueError, match="window_days"):
        await view(GroupKpiRequest(
            tenant=TenantContext(operator_id=OperatorId(uuid4())),
            property_ids=(PropertyId(uuid4()),), window_days=0,
        ))


# ---- OutcomeBilling ----

def _baseline_then_current(uplift: float) -> tuple[PropertyKpis, PropertyKpis]:
    pid = PropertyId(uuid4())
    baseline = _kpis(property_id=pid, revenue=80.0,
                     start=datetime(2025, 10, 1, tzinfo=UTC),
                     end=datetime(2025, 12, 31, tzinfo=UTC))
    current = _kpis(property_id=pid, revenue=80.0 + uplift,
                    start=datetime(2026, 1, 1, tzinfo=UTC),
                    end=datetime(2026, 4, 1, tzinfo=UTC))
    return baseline, current


@pytest.mark.asyncio
async def test_outcome_billing_met_target_no_rebate() -> None:
    baseline, current = _baseline_then_current(uplift=20.0)  # > £15 Pilot target
    audit = InMemoryAuditLog()
    rec = await OutcomeBilling(audit=audit)(ReconcileBillingRequest(
        tier=Tier.PILOT, base_fee_gbp=10_000.0,
        baseline=baseline, current=current, correlation_id="bill-1",
    ))
    assert rec.tier_status == "met"
    assert rec.rebate_gbp == 0.0
    assert rec.fee_due_gbp == 10_000.0
    assert any(e["action"] == "billing.reconciled.met" for e in audit.entries)


@pytest.mark.asyncio
async def test_outcome_billing_partial_proportional_rebate() -> None:
    baseline, current = _baseline_then_current(uplift=10.0)  # 10/15 = 0.667 ratio
    rec = await OutcomeBilling(audit=InMemoryAuditLog())(ReconcileBillingRequest(
        tier=Tier.PILOT, base_fee_gbp=10_000.0,
        baseline=baseline, current=current, correlation_id="bill-2",
    ))
    assert rec.tier_status == "partial"
    # Rebate = 10000 * (1 - 0.667) * 0.5 ≈ 1666.67
    assert rec.rebate_gbp == pytest.approx(10_000.0 * (1.0 - 10.0 / 15.0) * 0.5, rel=1e-3)


@pytest.mark.asyncio
async def test_outcome_billing_missed_caps_at_half_rebate() -> None:
    baseline, current = _baseline_then_current(uplift=2.0)  # < 50% of target
    rec = await OutcomeBilling(audit=InMemoryAuditLog())(ReconcileBillingRequest(
        tier=Tier.PILOT, base_fee_gbp=10_000.0,
        baseline=baseline, current=current, correlation_id="bill-3",
    ))
    assert rec.tier_status == "missed"
    assert rec.rebate_gbp == 5_000.0
    assert rec.fee_due_gbp == 5_000.0


@pytest.mark.asyncio
async def test_outcome_billing_enterprise_is_pass_through() -> None:
    baseline, current = _baseline_then_current(uplift=0.0)
    rec = await OutcomeBilling(audit=InMemoryAuditLog())(ReconcileBillingRequest(
        tier=Tier.ENTERPRISE, base_fee_gbp=100_000.0,
        baseline=baseline, current=current, correlation_id="bill-ent",
    ))
    assert rec.tier_status == "met"
    assert rec.rebate_gbp == 0.0


# ---- CRM adapter ----

@pytest.mark.asyncio
async def test_crm_adapter_returns_contact_and_interactions() -> None:
    from storia.infrastructure.in_memory import InMemoryCrmAdapter

    adapter = InMemoryCrmAdapter(
        crm_name="salesforce",
        contacts={"hash-X": {"name": "Ada", "vip": True}},
        interactions={"hash-X": [{"channel": "email", "ts": "2026-04-01"}]},
    )
    assert adapter.crm_name == "salesforce"
    assert await adapter.fetch_contact(email_hash="hash-X") == {"name": "Ada", "vip": True}
    assert await adapter.fetch_contact(email_hash="missing") is None
    interactions = await adapter.fetch_interactions_since(
        email_hash="hash-X", since=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert len(interactions) == 1


# touch timedelta to silence unused-import linter if it appears
_ = timedelta(0)
