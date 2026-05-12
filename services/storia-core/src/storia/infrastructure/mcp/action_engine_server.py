"""
Module: storia.infrastructure.mcp.action_engine_server
Layer: infrastructure
Ports: wraps storia.application.queue_pre_arrival_actions and shift_view
MCP integration: bounded context = Action Engine (Rules §3.5).
                 Tools (writes): queue_pre_arrival_actions
                 Resources (reads): shift://{property_id}
Stack: stdlib JSON-RPC scaffold. Wire to mcp-sdk in composition root.

Schema-validated against ProposedActions and Action shapes — Rules §4.2 reject by default.
Agents calling this server receive scoped, time-boxed access (Rules §4.6).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID  # noqa: F401  (used by _signal_from_wire)

from storia.application.queue_pre_arrival_actions import (
    QueuePreArrivalActions,
    QueuePreArrivalActionsRequest,
)
from storia.application.shift_view import ShiftView, ShiftViewRequest
from datetime import datetime

from storia.domain.ids import GuestId, PropertyId, SignalId, StayId
from storia.domain.models import Signal, SignalKind


def _signal_from_wire(raw: dict[str, Any]) -> Signal:
    """Boundary deserializer: JSON wire shape → Signal (Rules §4.2)."""
    return Signal(
        id=SignalId(UUID(raw["id"]["value"] if isinstance(raw["id"], dict) else raw["id"])),
        guest_id=GuestId(UUID(raw["guest_id"]["value"] if isinstance(raw["guest_id"], dict) else raw["guest_id"])),
        property_id=PropertyId(UUID(raw["property_id"]["value"] if isinstance(raw["property_id"], dict) else raw["property_id"])),
        kind=SignalKind(raw["kind"]),
        occurred_at=datetime.fromisoformat(raw["occurred_at"].replace("Z", "+00:00")),
        payload=dict(raw["payload"]),
    )


@dataclass(frozen=True, slots=True)
class ActionEngineServer:
    queue_use_case: QueuePreArrivalActions
    shift_use_case: ShiftView

    async def tool_queue_pre_arrival_actions(self, payload: dict[str, Any]) -> dict[str, Any]:
        """MCP tool. Writes. Returns the queued actions."""
        req = QueuePreArrivalActionsRequest(
            property_id=PropertyId(UUID(payload["property_id"])),
            stay_id=StayId(UUID(payload["stay_id"])),
            playbook_id=UUID(payload["playbook_id"]),
            auto_approve_threshold=float(payload.get("auto_approve_threshold", 0.85)),
            triggering_signals=tuple(_signal_from_wire(s) for s in payload["signals"]),
            correlation_id=str(payload["correlation_id"]),
        )
        actions = await self.queue_use_case(req)
        return {"actions": [a.model_dump(mode="json") for a in actions]}

    async def resource_shift(self, property_id: str) -> dict[str, Any]:
        """MCP resource. Reads. Returns the shift view."""
        resp = await self.shift_use_case(
            ShiftViewRequest(property_id=PropertyId(UUID(property_id)))
        )
        return {
            "arriving": [a.model_dump(mode="json") for a in resp.arriving],
            "in_stay": [a.model_dump(mode="json") for a in resp.in_stay],
            "departing": [a.model_dump(mode="json") for a in resp.departing],
        }
