"""
Module: storia.infrastructure.mcp.guest_signal_server
Layer: infrastructure
Ports: wraps storia.application.ingest_booking
MCP integration: bounded context = Guest Signal (ingest + unify).
                 Tools (writes): ingest_booking
Stack: stdlib

Rules §3.5 — one MCP server per bounded context. Guest Signal handles ingestion and identity
resolution; action production lives in the Action Engine server.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from storia.application.ingest_booking import IngestBooking, IngestBookingRequest
from storia.domain.ids import OperatorId, PropertyId
from storia.domain.models import Booking


@dataclass(frozen=True, slots=True)
class GuestSignalServer:
    ingest_use_case: IngestBooking

    async def tool_ingest_booking(self, payload: dict[str, Any]) -> dict[str, Any]:
        booking = Booking.create(
            pms_booking_id=payload["booking"]["pms_booking_id"],
            pms=payload["booking"]["pms"],
            arrival=datetime.fromisoformat(payload["booking"]["arrival"]),
            departure=datetime.fromisoformat(payload["booking"]["departure"]),
            room_code=payload["booking"].get("room_code"),
            rate_code=payload["booking"].get("rate_code"),
            channel=payload["booking"].get("channel"),
        )
        req = IngestBookingRequest(
            operator_id=OperatorId(UUID(payload["operator_id"])),
            property_id=PropertyId(UUID(payload["property_id"])),
            booking=booking,
            guest_display_name=payload["guest"]["display_name"],
            guest_email=payload["guest"].get("email"),
            guest_phone_e164=payload["guest"].get("phone_e164"),
            loyalty_number=payload["guest"].get("loyalty_number"),
            correlation_id=str(payload["correlation_id"]),
        )
        result = await self.ingest_use_case(req)
        return {"guest_id": result.guest_id, "sequence": result.sequence}
