"""
Module: storia.infrastructure.mews_pms
Layer: infrastructure
Ports: implements PmsAdapter (Mews flavour). Depends on TokenProvider for OAuth.
MCP integration: wrapped by storia.infrastructure.mcp.guest_signal_server when registered.
Stack: httpx (Python). Hot-path bulk pulls still live in crates/storia-connectors-mews.

PRD §7.1 Tier 1 + §7.2 — strict schema contract, drift = Sev-2. Every external call
has a timeout (Rules §4.4). Retries: up to 3 with exponential backoff on 429/5xx; never
retry 4xx (those are real client errors).
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from storia.domain.ids import OperatorId, PropertyId
from storia.domain.models import Booking

logger = logging.getLogger(__name__)


class SchemaDriftError(RuntimeError):
    """PRD §7.2 — unexpected response shape from Mews."""


class _MewsBooking(BaseModel):
    """Wire contract. extra=forbid → reject by default (Rules §4.2)."""
    model_config = ConfigDict(extra="forbid", strict=False)
    id: str = Field(min_length=1)
    guest_name: str
    guest_email: str | None = None
    arrival_utc: datetime
    departure_utc: datetime
    room_code: str | None = None
    rate_code: str | None = None
    channel: str | None = None


@dataclass(frozen=True, slots=True)
class _RetryConfig:
    attempts: int = 3
    base_delay_s: float = 0.25


class MewsPmsAdapter:
    pms_name = "mews"

    def __init__(self, *, client: httpx.AsyncClient, tokens, operator_id: OperatorId,  # type: ignore[no-untyped-def]
                 retry: _RetryConfig = _RetryConfig()) -> None:
        # Composition root supplies `tokens: TokenProvider` and a configured `httpx.AsyncClient`
        # with timeout already set per Rules §4.4.
        self._http = client
        self._tokens = tokens
        self._operator_id = operator_id
        self._retry = retry

    async def fetch_recent_bookings(self, property_id: PropertyId, since: datetime
                                    ) -> list[Booking]:
        token = await self._tokens.token_for(integration="mews",
                                             operator_id=self._operator_id)
        body = {
            "TimeFilter": "Created",
            "StartUtc": since.isoformat(),
            "EndUtc": datetime.utcnow().isoformat() + "Z",
            "PropertyId": str(property_id),
        }
        raw = await self._post_with_retry(
            path="/api/connector/v1/reservations/getAll",
            token=token, json_body=body,
        )
        try:
            envelope = [_MewsBooking.model_validate(item) for item in raw]
        except ValidationError as e:
            raise SchemaDriftError(str(e)) from e

        bookings: list[Booking] = []
        for b in envelope:
            bookings.append(Booking.create(
                pms_booking_id=b.id,
                pms="mews",
                arrival=b.arrival_utc,
                departure=b.departure_utc,
                room_code=b.room_code,
                rate_code=b.rate_code,
                channel=b.channel,
            ))
        return bookings

    async def add_guest_note(self, *, property_id: PropertyId, pms_booking_id: str,
                             note: str) -> None:
        token = await self._tokens.token_for(integration="mews",
                                             operator_id=self._operator_id)
        await self._post_with_retry(
            path="/api/connector/v1/notes/add",
            token=token,
            json_body={
                "PropertyId": str(property_id),
                "ReservationId": pms_booking_id,
                "Text": note,
            },
        )

    async def assign_room(self, *, property_id: PropertyId, pms_booking_id: str,
                          room_code: str) -> None:
        token = await self._tokens.token_for(integration="mews",
                                             operator_id=self._operator_id)
        await self._post_with_retry(
            path="/api/connector/v1/reservations/assignRoom",
            token=token,
            json_body={
                "PropertyId": str(property_id),
                "ReservationId": pms_booking_id,
                "RoomCode": room_code,
            },
        )

    async def _post_with_retry(self, *, path: str, token: str, json_body: dict
                               ) -> object:
        delay = self._retry.base_delay_s
        last: httpx.Response | None = None
        for attempt in range(self._retry.attempts):
            resp = await self._http.post(
                path,
                headers={"Authorization": f"Bearer {token}"},
                json=json_body,
            )
            if 200 <= resp.status_code < 300:
                return resp.json()
            if resp.status_code in (429,) or 500 <= resp.status_code < 600:
                last = resp
                if attempt + 1 == self._retry.attempts:
                    break
                await asyncio.sleep(delay)
                delay *= 2
                continue
            # 4xx (non-429) — fail fast.
            resp.raise_for_status()
        assert last is not None
        last.raise_for_status()
        return None  # pragma: no cover — raise_for_status always raises here
