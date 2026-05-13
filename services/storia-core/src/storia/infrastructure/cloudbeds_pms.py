"""
Module: storia.infrastructure.cloudbeds_pms
Layer: infrastructure
Ports: implements PmsAdapter (Cloudbeds flavour). PRD §7.1 Tier 1.
MCP integration: wrapped by guest_signal_server when registered.
Stack: httpx + Cloudbeds REST API (OAuth 2.0). Schema-strict on the response envelope.
"""
from __future__ import annotations

import asyncio
from datetime import datetime

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from storia.domain.ids import OperatorId, PropertyId
from storia.domain.models import Booking
from storia.infrastructure.mews_pms import SchemaDriftError, _RetryConfig


class _CloudbedsReservation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reservation_id: str = Field(min_length=1)
    guest_name: str
    guest_email: str | None = None
    check_in: datetime
    check_out: datetime
    room_id: str | None = None
    rate_plan_id: str | None = None
    source: str | None = None


class CloudbedsPmsAdapter:
    pms_name = "cloudbeds"

    def __init__(self, *, client: httpx.AsyncClient, tokens, operator_id: OperatorId,  # type: ignore[no-untyped-def]
                 retry: _RetryConfig = _RetryConfig()) -> None:
        self._http = client
        self._tokens = tokens
        self._operator_id = operator_id
        self._retry = retry

    async def fetch_recent_bookings(self, property_id: PropertyId, since: datetime
                                    ) -> list[Booking]:
        token = await self._tokens.token_for(integration="cloudbeds",
                                             operator_id=self._operator_id)
        raw = await self._get_with_retry(
            path="/getReservations",
            token=token,
            params={
                "propertyID": str(property_id),
                "checkInFrom": since.date().isoformat(),
            },
        )
        try:
            items = [_CloudbedsReservation.model_validate(r) for r in raw.get("data", [])]
        except ValidationError as e:
            raise SchemaDriftError(str(e)) from e

        return [
            Booking.create(
                pms_booking_id=r.reservation_id,
                pms="cloudbeds",
                arrival=r.check_in,
                departure=r.check_out,
                room_code=r.room_id,
                rate_code=r.rate_plan_id,
                channel=r.source,
            )
            for r in items
        ]

    async def add_guest_note(self, *, property_id: PropertyId, pms_booking_id: str,
                             note: str) -> None:
        token = await self._tokens.token_for(integration="cloudbeds",
                                             operator_id=self._operator_id)
        await self._post_with_retry(
            path="/postNote",
            token=token,
            json_body={"reservationID": pms_booking_id, "note": note,
                       "propertyID": str(property_id)},
        )

    async def assign_room(self, *, property_id: PropertyId, pms_booking_id: str,
                          room_code: str) -> None:
        token = await self._tokens.token_for(integration="cloudbeds",
                                             operator_id=self._operator_id)
        await self._post_with_retry(
            path="/assignRoom",
            token=token,
            json_body={"reservationID": pms_booking_id, "roomID": room_code,
                       "propertyID": str(property_id)},
        )

    async def _get_with_retry(self, *, path: str, token: str, params: dict
                              ) -> dict:
        delay = self._retry.base_delay_s
        last: httpx.Response | None = None
        for attempt in range(self._retry.attempts):
            resp = await self._http.get(
                path, headers={"Authorization": f"Bearer {token}"}, params=params,
            )
            if 200 <= resp.status_code < 300:
                return resp.json()
            if resp.status_code == 429 or 500 <= resp.status_code < 600:
                last = resp
                if attempt + 1 == self._retry.attempts:
                    break
                await asyncio.sleep(delay)
                delay *= 2
                continue
            resp.raise_for_status()
        assert last is not None
        last.raise_for_status()
        return {}  # pragma: no cover

    async def _post_with_retry(self, *, path: str, token: str, json_body: dict
                               ) -> None:
        delay = self._retry.base_delay_s
        last: httpx.Response | None = None
        for attempt in range(self._retry.attempts):
            resp = await self._http.post(
                path, headers={"Authorization": f"Bearer {token}"}, json=json_body,
            )
            if 200 <= resp.status_code < 300:
                return
            if resp.status_code == 429 or 500 <= resp.status_code < 600:
                last = resp
                if attempt + 1 == self._retry.attempts:
                    break
                await asyncio.sleep(delay)
                delay *= 2
                continue
            resp.raise_for_status()
        assert last is not None
        last.raise_for_status()
