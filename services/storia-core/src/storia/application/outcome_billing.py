"""
Module: storia.application.outcome_billing
Layer: application
Ports: AuditLog
MCP integration: exposed as MCP tool `reconcile_billing` (Operator Console server)
Stack: stdlib + storia.domain

Outcome-linked billing reconciliation (ADR 0008, PRD §3.1 S12). Pure arithmetic — no LLM,
no estimation. Audit emitted on every reconciliation.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum
from typing import Literal

from storia.domain.kpis import AttributedKpis, PropertyKpis
from storia.domain.ports import AuditLog


class Tier(str, Enum):
    PILOT = "pilot"
    OPERATOR = "operator"
    ENTERPRISE = "enterprise"


_TIER_TARGETS: dict[Tier, float] = {
    Tier.PILOT: 15.0,        # £ revenue uplift per guest per night
    Tier.OPERATOR: 25.0,
    Tier.ENTERPRISE: 0.0,    # negotiated; rebate handled out-of-band
}


@dataclass(frozen=True, slots=True)
class ReconcileBillingRequest:
    tier: Tier
    base_fee_gbp: float
    baseline: PropertyKpis
    current: PropertyKpis
    correlation_id: str


@dataclass(frozen=True, slots=True)
class BillingReconciliation:
    attributed: AttributedKpis
    target_uplift: float
    achieved_uplift: float
    achievement_ratio: float       # achieved / target, capped at 1.0 for billing
    rebate_gbp: float              # what we owe back to the operator
    fee_due_gbp: float             # what the operator pays (= base_fee_gbp - rebate)
    tier_status: Literal["met", "partial", "missed"]


class OutcomeBilling:
    def __init__(self, *, audit: AuditLog) -> None:
        self._audit = audit

    async def __call__(self, req: ReconcileBillingRequest) -> BillingReconciliation:
        attributed = AttributedKpis.compute(current=req.current, baseline=req.baseline)
        target = _TIER_TARGETS[req.tier]
        achieved = max(attributed.revenue_uplift_per_guest_night, 0.0)

        if req.tier is Tier.ENTERPRISE or target == 0.0:
            ratio = 1.0
            tier_status: Literal["met", "partial", "missed"] = "met"
            rebate = 0.0
        else:
            ratio = min(achieved / target, 1.0)
            if ratio >= 1.0:
                tier_status = "met"
                rebate = 0.0
            elif ratio >= 0.5:
                tier_status = "partial"
                # Rebate proportional to shortfall, capped at 50% of fee.
                rebate = req.base_fee_gbp * (1.0 - ratio) * 0.5
            else:
                tier_status = "missed"
                # Below half-target: 50% rebate. No further reduction in v1 — the LOI
                # protects both sides; outright misses go to manual review.
                rebate = req.base_fee_gbp * 0.5

        fee_due = max(req.base_fee_gbp - rebate, 0.0)
        result = BillingReconciliation(
            attributed=attributed,
            target_uplift=target,
            achieved_uplift=achieved,
            achievement_ratio=ratio,
            rebate_gbp=rebate,
            fee_due_gbp=fee_due,
            tier_status=tier_status,
        )

        await self._audit.emit(
            actor="system:storia.application.outcome_billing",
            action=f"billing.reconciled.{tier_status}",
            before_hash=None,
            after_hash=hashlib.sha256(
                f"{req.tier.value}|{req.base_fee_gbp}|{rebate}|{achieved}".encode()
            ).hexdigest(),
            correlation_id=req.correlation_id,
        )
        return result
