"""Postgres event store unit tests against an in-process fake psycopg pool."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest

from storia.domain.ids import GuestId, OperatorId
from storia.domain.models import GuestEvent, GuestEventKind
from storia.infrastructure.postgres_event_store import PostgresEventStore


class _FakeCursor:
    def __init__(self, rows: list[tuple[Any, ...]] | None) -> None:
        self._rows = rows or []

    async def fetchall(self) -> list[tuple[Any, ...]]:
        return self._rows

    async def fetchone(self) -> tuple[Any, ...] | None:
        return self._rows[0] if self._rows else None


class _FakeConnection:
    def __init__(self, store: dict[str, list[tuple[Any, ...]]]) -> None:
        self._store = store
        self.last_sql: list[str] = []

    async def execute(self, sql: str, params: tuple[Any, ...] | None = None
                      ) -> _FakeCursor:
        self.last_sql.append(sql)
        sql_l = sql.lstrip().lower()
        if sql_l.startswith("insert into guest_event"):
            self._store.setdefault("rows", []).append(params or ())
            return _FakeCursor(None)
        if sql_l.startswith("select coalesce(max(sequence)"):
            assert params is not None
            op, gid = params
            rows = [r for r in self._store.get("rows", [])
                    if r[0] == op and r[1] == gid]
            next_seq = max((r[2] for r in rows), default=-1) + 1
            return _FakeCursor([(next_seq,)])
        if sql_l.startswith("select operator_id, guest_id, sequence"):
            assert params is not None
            op, gid = params
            rows = [r for r in self._store.get("rows", [])
                    if r[0] == op and r[1] == gid]
            rows.sort(key=lambda r: r[2])
            return _FakeCursor(rows)
        # set search_path / DDL — no-op for the fake.
        return _FakeCursor(None)

    async def __aenter__(self) -> "_FakeConnection":
        return self

    async def __aexit__(self, *a: Any) -> None:
        return None

    def transaction(self) -> "_FakeConnection":
        return self


class _FakePool:
    def __init__(self) -> None:
        self._store: dict[str, list[tuple[Any, ...]]] = {}

    def connection(self) -> _FakeConnection:
        return _FakeConnection(self._store)


def _event(op: OperatorId, guest: GuestId, sequence: int) -> GuestEvent:
    return GuestEvent.record(
        sequence=sequence, operator_id=op, guest_id=guest,
        kind=GuestEventKind.BOOKING_ATTACHED,
        body={"pms_booking_id": f"R-{sequence}"}, source="mews",
    )


def test_rejects_unsafe_schema_name() -> None:
    with pytest.raises(ValueError, match="identifier-safe"):
        PostgresEventStore(pool=_FakePool(), schema="evil; DROP TABLE x; --")


@pytest.mark.asyncio
async def test_append_then_load_round_trip() -> None:
    store = PostgresEventStore(pool=_FakePool(), schema="tenant_op1")
    op = OperatorId(uuid4())
    guest = GuestId(uuid4())

    seq0 = await store.next_sequence(op, guest)
    assert seq0 == 0
    await store.append(_event(op, guest, sequence=0))

    seq1 = await store.next_sequence(op, guest)
    assert seq1 == 1
    await store.append(_event(op, guest, sequence=1))

    loaded = await store.load_for_guest(op, guest)
    assert len(loaded) == 2
    assert [e.sequence for e in loaded] == [0, 1]
    assert all(e.source == "mews" for e in loaded)


@pytest.mark.asyncio
async def test_bootstrap_runs_ddl() -> None:
    pool = _FakePool()
    await PostgresEventStore(pool=pool, schema="ok_schema").bootstrap()
    # No exception = ok; the fake records the SQL but we don't introspect it here.
