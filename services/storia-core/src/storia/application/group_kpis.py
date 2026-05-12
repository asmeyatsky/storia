"""
Module: storia.application.group_kpis
Layer: application
Ports: MetricsReader
MCP integration: surfaced via Operator Console MCP server (read resource)
Stack: stdlib + storia.domain

PRD §11.3 group-level analytics across multiple properties.
"""
from __future__ import annotations

from dataclasses import dataclass

from storia.domain.ids import PropertyId
from storia.domain.kpis import GroupKpis, PropertyKpis
from storia.domain.ports import MetricsReader
from storia.domain.tenant import TenantContext


@dataclass(frozen=True, slots=True)
class GroupKpiRequest:
    tenant: TenantContext
    property_ids: tuple[PropertyId, ...]
    window_days: int


class GroupKpiView:
    def __init__(self, *, metrics: MetricsReader) -> None:
        self._metrics = metrics

    async def __call__(self, req: GroupKpiRequest) -> GroupKpis:
        if not req.property_ids:
            raise ValueError("at least one property required")
        if req.window_days < 1:
            raise ValueError("window_days must be >= 1")
        readings: list[PropertyKpis] = []
        for pid in req.property_ids:
            result = await self._metrics.read(property_id=pid, window_days=req.window_days)
            assert isinstance(result, PropertyKpis)
            readings.append(result)
        return GroupKpis.rollup(readings)
