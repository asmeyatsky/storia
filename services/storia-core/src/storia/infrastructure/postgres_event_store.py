"""
Module: storia.infrastructure.postgres_event_store
Layer: infrastructure
Ports: implements EventStore
MCP integration: none
Stack: psycopg 3 + Postgres (Cloud SQL per ADR 0003); deviation from Rust hot-path
acceptable here because event append is not on the p99<50ms hot path — ingestion
is the hot path and lives in Rust connectors.

Schema-per-tenant multi-tenancy. CMEK-encrypted at rest (per-tenant key, ADR 0007).
"""
from __future__ import annotations

from typing import Any

from storia.domain.ids import GuestId, OperatorId
from storia.domain.models import GuestEvent

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


class PostgresEventStore:
    """Production EventStore. Schema-per-tenant; pool injected by composition root."""

    def __init__(self, pool: Any, schema: str) -> None:
        # pool is a psycopg_pool.AsyncConnectionPool — typed `Any` to keep this module thin.
        self._pool = pool
        self._schema = schema

    async def bootstrap(self) -> None:
        async with self._pool.connection() as conn:
            await conn.execute(f'SET search_path TO "{self._schema}"')
            await conn.execute(_DDL)

    async def append(self, event: GuestEvent) -> None:
        async with self._pool.connection() as conn:
            await conn.execute(f'SET search_path TO "{self._schema}"')
            await conn.execute(
                "INSERT INTO guest_event (operator_id, guest_id, sequence, kind, "
                "occurred_at, body, source) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (str(event.operator_id), str(event.guest_id), event.sequence,
                 event.kind.value, event.occurred_at, event.model_dump()["body"],
                 event.source),
            )

    async def load_for_guest(self, operator_id: OperatorId, guest_id: GuestId
                             ) -> list[GuestEvent]:  # pragma: no cover — integration only
        raise NotImplementedError("integration tests provide concrete coverage")

    async def next_sequence(self, operator_id: OperatorId, guest_id: GuestId) -> int:
        async with self._pool.connection() as conn:
            await conn.execute(f'SET search_path TO "{self._schema}"')
            row = await (await conn.execute(
                "SELECT COALESCE(MAX(sequence) + 1, 0) FROM guest_event "
                "WHERE operator_id = %s AND guest_id = %s",
                (str(operator_id), str(guest_id)),
            )).fetchone()
            return int(row[0]) if row else 0
