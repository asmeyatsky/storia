"""
Module: storia.domain.kpis
Layer: domain
Ports: none
MCP integration: none
Stack: stdlib + pydantic frozen models

KPI shapes (PRD §9.1). Immutable. Factories enforce invariants — Rules §3.3, §3.4.

Two layers:
  PropertyKpis      — one property, one window. The thing a MetricsReader returns.
  GroupKpis         — cross-property roll-up. PRD §11.3 "group-level analytics".
  AttributedKpis    — PropertyKpis decorated with attribution to STORIA actions vs baseline.
"""
from __future__ import annotations

from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field

from storia.domain.ids import PropertyId

_FROZEN = ConfigDict(frozen=True, extra="forbid", strict=True)


class PropertyKpis(BaseModel):
    """Single property over a measurement window."""
    model_config = _FROZEN

    property_id: PropertyId
    window_start: datetime
    window_end: datetime
    revenue_per_guest_night: float = Field(ge=0.0)
    repeat_stay_rate: float = Field(ge=0.0, le=1.0)
    avg_review_score: float = Field(ge=0.0, le=5.0)
    median_recovery_minutes: float = Field(ge=0.0)
    staff_dau_ratio: float = Field(ge=0.0, le=1.0)
    storia_action_count: int = Field(ge=0)

    @classmethod
    def measured(cls, *, property_id: PropertyId, window_start: datetime,
                 window_end: datetime, revenue_per_guest_night: float,
                 repeat_stay_rate: float, avg_review_score: float,
                 median_recovery_minutes: float, staff_dau_ratio: float,
                 storia_action_count: int) -> Self:
        if window_end <= window_start:
            raise ValueError("window_end must be strictly after window_start")
        if window_start.tzinfo is None or window_end.tzinfo is None:
            raise ValueError("KPI windows must be timezone-aware")
        return cls(
            property_id=property_id,
            window_start=window_start, window_end=window_end,
            revenue_per_guest_night=revenue_per_guest_night,
            repeat_stay_rate=repeat_stay_rate,
            avg_review_score=avg_review_score,
            median_recovery_minutes=median_recovery_minutes,
            staff_dau_ratio=staff_dau_ratio,
            storia_action_count=storia_action_count,
        )


class GroupKpis(BaseModel):
    """Cross-property roll-up (PRD §11.3). Weighted by storia_action_count where the
    metric is action-attributed; simple mean otherwise (review, adoption)."""
    model_config = _FROZEN

    properties: tuple[PropertyKpis, ...]
    revenue_per_guest_night: float
    repeat_stay_rate: float
    avg_review_score: float
    median_recovery_minutes: float
    staff_dau_ratio: float
    total_action_count: int

    @classmethod
    def rollup(cls, properties: list[PropertyKpis]) -> Self:
        if not properties:
            raise ValueError("rollup requires at least one property")
        total = sum(p.storia_action_count for p in properties)
        n = len(properties)

        def weighted(attr: str) -> float:
            if total == 0:
                return sum(getattr(p, attr) for p in properties) / n
            return sum(getattr(p, attr) * p.storia_action_count for p in properties) / total

        return cls(
            properties=tuple(properties),
            revenue_per_guest_night=weighted("revenue_per_guest_night"),
            repeat_stay_rate=weighted("repeat_stay_rate"),
            avg_review_score=sum(p.avg_review_score for p in properties) / n,
            median_recovery_minutes=weighted("median_recovery_minutes"),
            staff_dau_ratio=sum(p.staff_dau_ratio for p in properties) / n,
            total_action_count=total,
        )


class AttributedKpis(BaseModel):
    """PropertyKpis with deltas vs a frozen baseline (PRD §10.2 — baseline window is
    contractually frozen before pilot; this model is the data contract for outcome-linked
    billing)."""
    model_config = _FROZEN

    current: PropertyKpis
    baseline: PropertyKpis
    revenue_uplift_per_guest_night: float
    repeat_stay_rate_delta: float
    review_score_delta: float
    recovery_time_reduction_minutes: float

    @classmethod
    def compute(cls, *, current: PropertyKpis, baseline: PropertyKpis) -> Self:
        if current.property_id != baseline.property_id:
            raise ValueError("baseline and current must be the same property")
        if current.window_start < baseline.window_end:
            raise ValueError("current window must start after baseline window ends")
        return cls(
            current=current,
            baseline=baseline,
            revenue_uplift_per_guest_night=(
                current.revenue_per_guest_night - baseline.revenue_per_guest_night
            ),
            repeat_stay_rate_delta=current.repeat_stay_rate - baseline.repeat_stay_rate,
            review_score_delta=current.avg_review_score - baseline.avg_review_score,
            recovery_time_reduction_minutes=(
                baseline.median_recovery_minutes - current.median_recovery_minutes
            ),
        )
