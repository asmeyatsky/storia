"""
Module: storia.presentation.api
Layer: presentation
Ports: depends on application use cases
MCP integration: none
Stack: FastAPI

Operator Console backend (PRD §5.2.3). Schema-validated input at the boundary (Rules §4.2).
RED metrics + OpenTelemetry tracing wired in composition root (Rules §6).
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from storia.application.ingest_booking import IngestBooking, IngestBookingRequest
from storia.application.shift_view import ShiftView, ShiftViewRequest
from storia.domain.ids import OperatorId, PropertyId
from storia.domain.models import Booking


class BookingIn(BaseModel):
    # extra=forbid → reject by default (Rules §4.2). Strict left off at the HTTP
    # boundary so JSON strings coerce to UUID/datetime; domain models stay strict.
    model_config = ConfigDict(extra="forbid")
    pms_booking_id: str = Field(min_length=1)
    pms: str
    arrival: datetime
    departure: datetime
    room_code: str | None = None
    rate_code: str | None = None
    channel: str | None = None


class GuestIn(BaseModel):
    # extra=forbid → reject by default (Rules §4.2). Strict left off at the HTTP
    # boundary so JSON strings coerce to UUID/datetime; domain models stay strict.
    model_config = ConfigDict(extra="forbid")
    display_name: str = Field(min_length=1)
    email: str | None = None
    phone_e164: str | None = None
    loyalty_number: str | None = None


class IngestBookingIn(BaseModel):
    # extra=forbid → reject by default (Rules §4.2). Strict left off at the HTTP
    # boundary so JSON strings coerce to UUID/datetime; domain models stay strict.
    model_config = ConfigDict(extra="forbid")
    operator_id: UUID
    property_id: UUID
    booking: BookingIn
    guest: GuestIn
    correlation_id: str = Field(min_length=1)


class IngestBookingOut(BaseModel):
    guest_id: str
    sequence: int


def build_app(*, ingest: IngestBooking, shift: ShiftView) -> FastAPI:
    """Composition-root factory. The composition root wires concrete adapters."""
    app = FastAPI(title="STORIA Operator API", version="0.1.0")

    def _ingest() -> IngestBooking:
        return ingest

    def _shift() -> ShiftView:
        return shift

    @app.post("/v1/bookings:ingest", response_model=IngestBookingOut)
    async def ingest_booking(
        body: IngestBookingIn, uc: IngestBooking = Depends(_ingest)
    ) -> IngestBookingOut:
        try:
            booking = Booking.create(
                pms_booking_id=body.booking.pms_booking_id,
                pms=body.booking.pms,
                arrival=body.booking.arrival,
                departure=body.booking.departure,
                room_code=body.booking.room_code,
                rate_code=body.booking.rate_code,
                channel=body.booking.channel,
            )
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e

        result = await uc(IngestBookingRequest(
            operator_id=OperatorId(body.operator_id),
            property_id=PropertyId(body.property_id),
            booking=booking,
            guest_display_name=body.guest.display_name,
            guest_email=body.guest.email,
            guest_phone_e164=body.guest.phone_e164,
            loyalty_number=body.guest.loyalty_number,
            correlation_id=body.correlation_id,
        ))
        return IngestBookingOut(guest_id=result.guest_id, sequence=result.sequence)

    @app.get("/v1/properties/{property_id}/shift")
    async def shift_view(
        property_id: UUID, uc: ShiftView = Depends(_shift)
    ) -> dict[str, object]:
        resp = await uc(ShiftViewRequest(property_id=PropertyId(property_id)))
        return {
            "arriving": [a.model_dump(mode="json") for a in resp.arriving],
            "in_stay": [a.model_dump(mode="json") for a in resp.in_stay],
            "departing": [a.model_dump(mode="json") for a in resp.departing],
        }

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app
