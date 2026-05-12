"""FastAPI presentation boundary tests (Rules §4.2 — reject by default at boundaries)."""
from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from storia.application.decide_action import DecideAction
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
def wired() -> dict[str, object]:
    events = InMemoryEventStore()
    identity = InMemoryIdentityResolver()
    bus = InMemorySignalBus()
    queue = InMemoryActionQueue()
    audit = InMemoryAuditLog()
    ingest = IngestBooking(events=events, identity=identity, bus=bus, audit=audit)
    shift = ShiftView(queue=queue)
    decide = DecideAction(queue=queue, audit=audit)
    app = build_app(ingest=ingest, shift=shift, decide=decide, audit=audit)
    return {"client": TestClient(app), "queue": queue, "audit": audit}


@pytest.fixture
def client(wired: dict[str, object]) -> TestClient:
    return wired["client"]  # type: ignore[return-value]


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


def test_audit_endpoint_returns_recorded_entries(wired: dict[str, object]) -> None:
    client: TestClient = wired["client"]  # type: ignore[assignment]
    r = client.post("/v1/bookings:ingest", json={
        "operator_id": str(uuid4()),
        "property_id": str(uuid4()),
        "booking": {
            "pms_booking_id": "R-A",
            "pms": "mews",
            "arrival": "2026-10-01T14:00:00+00:00",
            "departure": "2026-10-03T11:00:00+00:00",
        },
        "guest": {"display_name": "G"},
        "correlation_id": "audit-1",
    })
    assert r.status_code == 200

    a = client.get("/v1/audit?limit=10")
    assert a.status_code == 200
    entries = a.json()["entries"]
    assert any(e["correlation_id"] == "audit-1" for e in entries)


def test_audit_endpoint_rejects_bad_limit(client: TestClient) -> None:
    assert client.get("/v1/audit?limit=0").status_code == 422
    assert client.get("/v1/audit?limit=99999").status_code == 422


def test_decide_action_approve_path(wired: dict[str, object]) -> None:
    import asyncio
    from uuid import uuid4 as _u

    from storia.domain.ids import PropertyId, StayId
    from storia.domain.models import Action

    client: TestClient = wired["client"]  # type: ignore[assignment]
    queue = wired["queue"]

    action = Action.propose(
        stay_id=StayId(_u()), property_id=PropertyId(_u()),
        playbook_id=_u(), kind="pms.note.add",
        payload={}, reasoning=("seed",), reversible=True, auto_approved=False,
    )
    asyncio.get_event_loop().run_until_complete(queue.enqueue(action))  # type: ignore[union-attr]

    r = client.post(f"/v1/actions/{action.id}:decide", json={
        "decision": "approve", "actor": "gm@example.com", "correlation_id": "dec-1",
    })
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "executed"


def test_decide_action_404_for_unknown(client: TestClient) -> None:
    r = client.post(f"/v1/actions/{uuid4()}:decide", json={
        "decision": "approve", "actor": "x", "correlation_id": "c",
    })
    assert r.status_code == 404


def test_decide_action_rejects_invalid_decision(client: TestClient) -> None:
    r = client.post(f"/v1/actions/{uuid4()}:decide", json={
        "decision": "obliterate", "actor": "x", "correlation_id": "c",
    })
    assert r.status_code == 422


def test_composition_root_imports() -> None:
    """Smoke test for storia.main (composition root)."""
    from storia import main
    assert main.app is not None
