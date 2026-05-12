"""
Module: storia.main
Layer: composition root (presentation entrypoint)
Ports: assembles adapters and use cases
MCP integration: registers MCP servers
Stack: FastAPI + Uvicorn

Single place where SDK instantiation happens. Domain and application stay SDK-free per Rules §2.
"""
from __future__ import annotations

from storia.application.ingest_booking import IngestBooking
from storia.application.queue_pre_arrival_actions import QueuePreArrivalActions
from storia.application.shift_view import ShiftView
from storia.infrastructure.in_memory import (
    InMemoryActionQueue,
    InMemoryAuditLog,
    InMemoryEventStore,
    InMemoryIdentityResolver,
    InMemorySignalBus,
    StubReasoner,
)
from storia.infrastructure.mcp.action_engine_server import ActionEngineServer
from storia.infrastructure.mcp.guest_signal_server import GuestSignalServer
from storia.presentation.api import build_app


def build() -> object:
    """Dev/test composition: in-memory adapters. Production root substitutes Postgres,
    Pub/Sub, Anthropic, Mews."""
    events = InMemoryEventStore()
    identity = InMemoryIdentityResolver()
    bus = InMemorySignalBus()
    queue = InMemoryActionQueue()
    audit = InMemoryAuditLog()
    reasoner = StubReasoner()

    ingest = IngestBooking(events=events, identity=identity, bus=bus, audit=audit)
    queue_uc = QueuePreArrivalActions(reasoner=reasoner, queue=queue, audit=audit)
    shift = ShiftView(queue=queue)

    # MCP servers per bounded context (Rules §3.5).
    GuestSignalServer(ingest_use_case=ingest)
    ActionEngineServer(queue_use_case=queue_uc, shift_use_case=shift)

    return build_app(ingest=ingest, shift=shift)


app = build()
