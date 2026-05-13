"""
Module: storia.infrastructure.postgres_event_store
Layer: infrastructure
Ports: implements EventStore (PRD §6.2, ADR 0003).
MCP integration: none (called by application use cases via the port).
Stack: psycopg 3 async + Postgres (Cloud SQL).

Schema-per-tenant (Rules §3.6). Append-only ledger; primary key enforces sequence
contiguity on conflict. The PRD §6.2 invariant — past state reconstructible — holds:
events are never updated.

Operational notes:
- search_path is set to the tenant schema on every connection acquisition.
- All SQL uses parameter binding; no string interpolation of user input.
- Transactions are single-statement; multi-statement workflows belong in the application
  layer using `async with pool.connection() as conn: async with conn.transaction(): ...`.
"""
from __future__ import annotations

from typing import Any, Protocol

from storia.domain.ids import GuestId, OperatorId
from storia.domain.models import (
    GuestEvent,
    GuestEventKind,
    OperatorId as _OpId,
)

_DDL = """
CREATE TABLE IF NOT EXISTS guest_event (
    operator_id   UUID        NOT NULL,
    guest_id      UUID        NOT NULL,
    sequence      BIGINT      NOT NULL,
    kind          TEXT        NOT NULL,
    occurred_at   TIMESTAMPTZ NOT NULL,
    body          JSONB       NOT NULL,
    source        TEXT        NOT NULL,
    PRIMARY KEY (operator_id, guest_id, sequence)
);
CREATE INDEX IF NOT EXISTS guest_event_recency
    ON guest_event (operator_id, guest_id, sequence DESC);
"""


class _PoolLike(Protocol):
    """Minimal psycopg_pool.AsyncConnectionPool surface — lets tests inject a fake."""

    def connection(self) -> Any: ...


class PostgresEventStore:
    """Production EventStore. Identifier-safe schema-name handling: caller MUST validate
    the schema name against an allowlist before construction (raised here as a sanity guard)."""

    def __init__(self, pool: _PoolLike, schema: str) -> None:
        if not schema.replace("_", "").isalnum():
            # Defence-in-depth: any non-identifier-safe schema is rejected at construction.
            raise ValueError(f"schema name {schema!r} is not identifier-safe")
        self._pool = pool
        self._schema = schema

    async def bootstrap(self) -> None:
        async with self._pool.connection() as conn:
            await conn.execute(f'SET search_path TO "{self._schema}"')
            await conn.execute(_DDL)

    async def append(self, event: GuestEvent) -> None:
        async with self._pool.connection() as conn:
            async with conn.transaction():
                await conn.execute(f'SET search_path TO "{self._schema}"')
                await conn.execute(
                    "INSERT INTO guest_event (operator_id, guest_id, sequence, kind, "
                    "occurred_at, body, source) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (str(event.operator_id), str(event.guest_id), event.sequence,
                     event.kind.value, event.occurred_at,
                     event.model_dump(mode="json")["body"], event.source),
                )

    async def load_for_guest(self, operator_id: OperatorId, guest_id: GuestId
                             ) -> list[GuestEvent]:
        async with self._pool.connection() as conn:
            await conn.execute(f'SET search_path TO "{self._schema}"')
            cur = await conn.execute(
                "SELECT operator_id, guest_id, sequence, kind, occurred_at, body, source "
                "FROM guest_event WHERE operator_id = %s AND guest_id = %s "
                "ORDER BY sequence ASC",
                (str(operator_id), str(guest_id)),
            )
            rows = await cur.fetchall()
            return [
                GuestEvent(
                    sequence=int(row[2]),
                    operator_id=_OpId(_uuid(row[0])),
                    guest_id=GuestId(_uuid(row[1])),
                    kind=GuestEventKind(row[3]),
                    occurred_at=row[4],
                    body=dict(row[5]) if row[5] else {},
                    source=row[6],
                )
                for row in rows
            ]

    async def next_sequence(self, operator_id: OperatorId, guest_id: GuestId) -> int:
        async with self._pool.connection() as conn:
            await conn.execute(f'SET search_path TO "{self._schema}"')
            cur = await conn.execute(
                "SELECT COALESCE(MAX(sequence) + 1, 0) FROM guest_event "
                "WHERE operator_id = %s AND guest_id = %s",
                (str(operator_id), str(guest_id)),
            )
            row = await cur.fetchone()
            return int(row[0]) if row else 0


def _uuid(value: object) -> Any:
    from uuid import UUID
    if isinstance(value, UUID):
        return value
    return UUID(str(value))
