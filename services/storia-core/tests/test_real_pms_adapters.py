"""Real httpx Mews / Cloudbeds adapter tests (mocked via respx)."""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest
import respx

from storia.domain.ids import OperatorId, PropertyId
from storia.infrastructure.cloudbeds_pms import CloudbedsPmsAdapter
from storia.infrastructure.mews_pms import MewsPmsAdapter, SchemaDriftError, _RetryConfig


class _StaticTokenProvider:
    async def token_for(self, *, integration: str, operator_id: OperatorId) -> str:
        return f"token-for-{integration}"


@pytest.mark.asyncio
@respx.mock
async def test_mews_fetch_recent_bookings_parses_strict_envelope() -> None:
    route = respx.post("https://mews.test/api/connector/v1/reservations/getAll").mock(
        return_value=httpx.Response(200, json=[
            {
                "id": "R-1", "guest_name": "Ada",
                "guest_email": "ada@example.com",
                "arrival_utc": "2026-06-01T14:00:00+00:00",
                "departure_utc": "2026-06-04T11:00:00+00:00",
                "room_code": "OCEAN-1", "rate_code": "BAR",
                "channel": "direct",
            }
        ])
    )
    op = OperatorId(uuid4())
    async with httpx.AsyncClient(base_url="https://mews.test", timeout=5.0) as client:
        adapter = MewsPmsAdapter(client=client, tokens=_StaticTokenProvider(),
                                 operator_id=op)
        bookings = await adapter.fetch_recent_bookings(
            property_id=PropertyId(uuid4()),
            since=datetime(2026, 5, 1, tzinfo=UTC),
        )
    assert route.called
    assert len(bookings) == 1
    assert bookings[0].pms_booking_id == "R-1"
    assert bookings[0].pms == "mews"


@pytest.mark.asyncio
@respx.mock
async def test_mews_schema_drift_raises() -> None:
    respx.post("https://mews.test/api/connector/v1/reservations/getAll").mock(
        return_value=httpx.Response(200, json=[{"surprise": 1}])
    )
    op = OperatorId(uuid4())
    async with httpx.AsyncClient(base_url="https://mews.test", timeout=5.0) as client:
        adapter = MewsPmsAdapter(client=client, tokens=_StaticTokenProvider(),
                                 operator_id=op)
        with pytest.raises(SchemaDriftError):
            await adapter.fetch_recent_bookings(
                property_id=PropertyId(uuid4()),
                since=datetime(2026, 5, 1, tzinfo=UTC),
            )


@pytest.mark.asyncio
@respx.mock
async def test_mews_retries_on_5xx_then_succeeds() -> None:
    route = respx.post("https://mews.test/api/connector/v1/notes/add")
    route.side_effect = [
        httpx.Response(503),
        httpx.Response(200, json={}),
    ]
    op = OperatorId(uuid4())
    async with httpx.AsyncClient(base_url="https://mews.test", timeout=5.0) as client:
        adapter = MewsPmsAdapter(client=client, tokens=_StaticTokenProvider(),
                                 operator_id=op,
                                 retry=_RetryConfig(attempts=2, base_delay_s=0.0))
        await adapter.add_guest_note(property_id=PropertyId(uuid4()),
                                     pms_booking_id="R-1", note="hello")
    assert route.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_mews_does_not_retry_4xx() -> None:
    route = respx.post("https://mews.test/api/connector/v1/reservations/assignRoom").mock(
        return_value=httpx.Response(401)
    )
    op = OperatorId(uuid4())
    async with httpx.AsyncClient(base_url="https://mews.test", timeout=5.0) as client:
        adapter = MewsPmsAdapter(client=client, tokens=_StaticTokenProvider(),
                                 operator_id=op,
                                 retry=_RetryConfig(attempts=3, base_delay_s=0.0))
        with pytest.raises(httpx.HTTPStatusError):
            await adapter.assign_room(property_id=PropertyId(uuid4()),
                                      pms_booking_id="R-1", room_code="A")
    assert route.call_count == 1


@pytest.mark.asyncio
@respx.mock
async def test_cloudbeds_schema_drift_raises() -> None:
    respx.get("https://cb.test/getReservations").mock(
        return_value=httpx.Response(200, json={"data": [{"foo": 1}]})
    )
    op = OperatorId(uuid4())
    async with httpx.AsyncClient(base_url="https://cb.test", timeout=5.0) as client:
        adapter = CloudbedsPmsAdapter(client=client, tokens=_StaticTokenProvider(),
                                      operator_id=op)
        with pytest.raises(SchemaDriftError):
            await adapter.fetch_recent_bookings(
                property_id=PropertyId(uuid4()),
                since=datetime(2026, 6, 1, tzinfo=UTC),
            )


@pytest.mark.asyncio
@respx.mock
async def test_cloudbeds_add_note_and_assign_room() -> None:
    respx.post("https://cb.test/postNote").mock(return_value=httpx.Response(200))
    respx.post("https://cb.test/assignRoom").mock(return_value=httpx.Response(200))
    op = OperatorId(uuid4())
    async with httpx.AsyncClient(base_url="https://cb.test", timeout=5.0) as client:
        adapter = CloudbedsPmsAdapter(client=client, tokens=_StaticTokenProvider(),
                                      operator_id=op)
        await adapter.add_guest_note(property_id=PropertyId(uuid4()),
                                     pms_booking_id="CB-2", note="welcome")
        await adapter.assign_room(property_id=PropertyId(uuid4()),
                                  pms_booking_id="CB-2", room_code="9B")


@pytest.mark.asyncio
@respx.mock
async def test_cloudbeds_retries_then_succeeds_on_get() -> None:
    route = respx.get("https://cb.test/getReservations")
    route.side_effect = [
        httpx.Response(429),
        httpx.Response(200, json={"data": []}),
    ]
    op = OperatorId(uuid4())
    async with httpx.AsyncClient(base_url="https://cb.test", timeout=5.0) as client:
        from storia.infrastructure.mews_pms import _RetryConfig
        adapter = CloudbedsPmsAdapter(client=client, tokens=_StaticTokenProvider(),
                                      operator_id=op,
                                      retry=_RetryConfig(attempts=2, base_delay_s=0.0))
        bookings = await adapter.fetch_recent_bookings(
            property_id=PropertyId(uuid4()),
            since=datetime(2026, 6, 1, tzinfo=UTC),
        )
    assert bookings == []
    assert route.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_cloudbeds_fetch_strict_envelope() -> None:
    respx.get("https://cb.test/getReservations").mock(
        return_value=httpx.Response(200, json={
            "data": [{
                "reservation_id": "CB-1", "guest_name": "Grace",
                "check_in": "2026-07-01T15:00:00+00:00",
                "check_out": "2026-07-03T11:00:00+00:00",
                "room_id": "12A", "rate_plan_id": "BAR", "source": "ota",
            }]
        })
    )
    op = OperatorId(uuid4())
    async with httpx.AsyncClient(base_url="https://cb.test", timeout=5.0) as client:
        adapter = CloudbedsPmsAdapter(client=client, tokens=_StaticTokenProvider(),
                                      operator_id=op)
        bookings = await adapter.fetch_recent_bookings(
            property_id=PropertyId(uuid4()),
            since=datetime(2026, 6, 1, tzinfo=UTC),
        )
    assert len(bookings) == 1
    assert bookings[0].pms == "cloudbeds"
