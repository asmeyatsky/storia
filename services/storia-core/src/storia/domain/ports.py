"""
Module: storia.domain.ports
Layer: domain
Ports: this module IS the port catalogue
MCP integration: none — MCP servers live in infrastructure and wrap application use cases
Stack: stdlib only (Protocol)

Every external dependency has a port here (Rules §3.2). Adapters live in infrastructure.
Tests substitute in-memory implementations.
"""
from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable

from storia.domain.ids import GuestId, OperatorId, PlaybookId, PropertyId
from storia.domain.models import Action, Booking, Guest, GuestEvent, Signal


@runtime_checkable
class EventStore(Protocol):
    """Append-only ledger (PRD §6.2, ADR 0003)."""

    async def append(self, event: GuestEvent) -> None: ...

    async def load_for_guest(self, operator_id: OperatorId, guest_id: GuestId
                             ) -> list[GuestEvent]: ...

    async def next_sequence(self, operator_id: OperatorId, guest_id: GuestId) -> int: ...


@runtime_checkable
class IdentityResolver(Protocol):
    """Deterministic in v1; probabilistic queue in Pilot phase (PRD §6.3)."""

    async def resolve(self, *, operator_id: OperatorId, email_hash: str | None,
                      phone_hash: str | None, loyalty_number: str | None,
                      display_name: str) -> Guest: ...


@runtime_checkable
class PmsAdapter(Protocol):
    """Read/write port for a PMS. Implementations: Mews, Cloudbeds, Opera. Rules §3.2."""

    pms_name: str

    async def fetch_recent_bookings(self, property_id: PropertyId, since: datetime
                                    ) -> list[Booking]: ...

    async def add_guest_note(self, *, property_id: PropertyId, pms_booking_id: str,
                             note: str) -> None: ...

    async def assign_room(self, *, property_id: PropertyId, pms_booking_id: str,
                          room_code: str) -> None: ...


@runtime_checkable
class SignalBus(Protocol):
    """Pub/Sub abstraction (ADR 0005). Single bus, tenant routing."""

    async def publish(self, signal: Signal) -> None: ...


@runtime_checkable
class ActionQueue(Protocol):
    async def enqueue(self, action: Action) -> None: ...

    async def list_pending(self, property_id: PropertyId) -> list[Action]: ...


@runtime_checkable
class AuditLog(Protocol):
    """Tamper-evident, append-only, separate IAM (Rules §4.3, PRD §5.2.2)."""

    async def emit(self, *, actor: str, action: str, before_hash: str | None,
                   after_hash: str, correlation_id: str) -> None: ...


@runtime_checkable
class PlaybookRepository(Protocol):
    async def get(self, playbook_id: PlaybookId) -> "object": ...  # returns Playbook

    async def list_for_property(self, property_id: PropertyId) -> list["object"]: ...


@runtime_checkable
class Reasoner(Protocol):
    """LLM port. Two adapters per ADR 0004: HaikuRouter, OpusReasoner.

    Output is validated against an explicit Pydantic schema by the caller before any
    state mutation (Rules §4.5).
    """

    async def route(self, *, prompt: str, schema_name: str) -> dict[str, object]: ...

    async def reason(self, *, prompt: str, schema_name: str) -> dict[str, object]: ...
