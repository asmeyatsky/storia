"""
Module: storia.application.shift_view
Layer: application
Ports: ActionQueue
MCP integration: exposed as MCP resource `shift://{property_id}` in infrastructure
Stack: stdlib + storia.domain

Use case for PRD FR-OC-1, FR-OC-2: shift view groups queued actions by arc.
"""
from __future__ import annotations

from dataclasses import dataclass

from storia.domain.ids import PropertyId
from storia.domain.models import Action
from storia.domain.ports import ActionQueue


@dataclass(frozen=True, slots=True)
class ShiftViewRequest:
    property_id: PropertyId


@dataclass(frozen=True, slots=True)
class ShiftViewResponse:
    arriving: tuple[Action, ...]
    in_stay: tuple[Action, ...]
    departing: tuple[Action, ...]


class ShiftView:
    def __init__(self, *, queue: ActionQueue) -> None:
        self._queue = queue

    async def __call__(self, req: ShiftViewRequest) -> ShiftViewResponse:
        pending = await self._queue.list_pending(req.property_id)
        # v1 grouping: kind heuristic. Real grouping comes from the Stay snapshot in Pilot phase.
        arriving = tuple(a for a in pending if a.kind in {"pms.note.add", "pms.room.assign"})
        in_stay = tuple(a for a in pending if a.kind in {"messaging.draft", "operator.alert"})
        departing: tuple[Action, ...] = ()
        return ShiftViewResponse(arriving=arriving, in_stay=in_stay, departing=departing)
