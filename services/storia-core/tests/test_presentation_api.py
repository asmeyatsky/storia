"""FastAPI presentation boundary tests (Rules §4.2 — reject by default at boundaries)."""
from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from storia.application.ingest_booking import IngestBooking
from storia.application.shift_view import ShiftView
from storia.infrastructure.in_memory import (
    InMemoryActionQueue,
    InMemoryAuditLog,
    InMemoryEventStore,
    InMemoryIdentityResolver,
    InMemorySignalBus,
)
from storia.presentation.api import build_app


@pytest.fixture
def client() -> TestClient:
    events = InMemoryEventStore()
    identity = InMemoryIdentityResolver()
    bus = InMemorySignalBus()
    queue = InMemoryActionQueue()
    audit = InMemoryAuditLog()
    ingest = IngestBooking(events=events, identity=identity, bus=bus, audit=audit)
    shift = ShiftView(queue=queue)
    return TestClient(build_app(ingest=ingest, shift=shift))


def test_healthz(client: TestClient) -> None:
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_ingest_happy_path(client: TestClient) -> None:
    r = client.post("/v1/bookings:ingest", json={
        "operator_id": str(uuid4()),
        "property_id": str(uuid4()),
        "booking": {
            "pms_booking_id": "R-1",
            "pms": "mews",
            "arrival": "2026-08-01T14:00:00+00:00",
            "departure": "2026-08-04T11:00:00+00:00",
        },
        "guest": {"display_name": "Margaret Hamilton", "email": "mh@example.com"},
        "correlation_id": "api-corr-1",
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["sequence"] == 0
    assert body["guest_id"]


def test_ingest_rejects_unknown_pms(client: TestClient) -> None:
    """Rules §3.4 — invariants in factories surface as 422 at the boundary."""
    r = client.post("/v1/bookings:ingest", json={
        "operator_id": str(uuid4()),
        "property_id": str(uuid4()),
        "booking": {
            "pms_booking_id": "R-2",
            "pms": "acme-pms",
            "arrival": "2026-08-01T14:00:00+00:00",
            "departure": "2026-08-04T11:00:00+00:00",
        },
        "guest": {"display_name": "Margaret Hamilton"},
        "correlation_id": "api-corr-2",
    })
    assert r.status_code == 422
    assert "unsupported pms" in r.text


def test_ingest_rejects_extra_fields(client: TestClient) -> None:
    """Rules §4.2 — extra=forbid on input schema rejects unknown keys."""
    r = client.post("/v1/bookings:ingest", json={
        "operator_id": str(uuid4()),
        "property_id": str(uuid4()),
        "booking": {
            "pms_booking_id": "R-3",
            "pms": "mews",
            "arrival": "2026-08-01T14:00:00+00:00",
            "departure": "2026-08-04T11:00:00+00:00",
            "rogue_field": "no",
        },
        "guest": {"display_name": "X"},
        "correlation_id": "api-corr-3",
    })
    assert r.status_code == 422


def test_shift_view_empty(client: TestClient) -> None:
    r = client.get(f"/v1/properties/{uuid4()}/shift")
    assert r.status_code == 200
    body = r.json()
    assert body == {"arriving": [], "in_stay": [], "departing": []}


def test_composition_root_imports() -> None:
    """Smoke test for storia.main (composition root)."""
    from storia import main
    assert main.app is not None
