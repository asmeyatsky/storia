"""
Module: storia.infrastructure.in_memory
Layer: infrastructure
Ports: implements EventStore, IdentityResolver, SignalBus, ActionQueue, AuditLog, Reasoner
MCP integration: none (adapters only)
Stack: stdlib

In-memory adapters for tests and local dev. Production adapters live alongside this module
(postgres_event_store.py, pubsub_bus.py, anthropic_reasoner.py, mews_pms.py).
"""
from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any
from uuid import uuid4

from storia.domain.ids import GuestId, OperatorId, PropertyId
from storia.domain.models import Action, Guest, GuestEvent, Signal


class InMemoryEventStore:
    def __init__(self) -> None:
        self._events: dict[tuple[str, str], list[GuestEvent]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def append(self, event: GuestEvent) -> None:
        key = (str(event.operator_id), str(event.guest_id))
        async with self._lock:
            log = self._events[key]
            if log and event.sequence != log[-1].sequence + 1:
                raise RuntimeError(
                    f"sequence gap: expected {log[-1].sequence + 1}, got {event.sequence}"
                )
            log.append(event)

    async def load_for_guest(self, operator_id: OperatorId, guest_id: GuestId) -> list[GuestEvent]:
        return list(self._events[(str(operator_id), str(guest_id))])

    async def next_sequence(self, operator_id: OperatorId, guest_id: GuestId) -> int:
        log = self._events[(str(operator_id), str(guest_id))]
        return 0 if not log else log[-1].sequence + 1


class InMemoryIdentityResolver:
    """Deterministic-only resolver (PRD §6.3 v1). Probabilistic resolver lands in Pilot phase."""

    def __init__(self) -> None:
        self._by_email: dict[tuple[str, str], Guest] = {}
        self._by_phone: dict[tuple[str, str], Guest] = {}
        self._by_loyalty: dict[tuple[str, str], Guest] = {}
        self._lock = asyncio.Lock()

    async def resolve(self, *, operator_id: OperatorId, email_hash: str | None,
                      phone_hash: str | None, loyalty_number: str | None,
                      display_name: str) -> Guest:
        op = str(operator_id)
        async with self._lock:
            for table, key in (
                (self._by_loyalty, loyalty_number),
                (self._by_email, email_hash),
                (self._by_phone, phone_hash),
            ):
                if key is not None:
                    existing = table.get((op, key))
                    if existing is not None:
                        return existing
            guest = Guest.new(display_name=display_name, primary_email_hash=email_hash)
            if email_hash:
                self._by_email[(op, email_hash)] = guest
            if phone_hash:
                self._by_phone[(op, phone_hash)] = guest
            if loyalty_number:
                self._by_loyalty[(op, loyalty_number)] = guest
            return guest


class InMemorySignalBus:
    def __init__(self) -> None:
        self.published: list[Signal] = []

    async def publish(self, signal: Signal) -> None:
        self.published.append(signal)


class InMemoryActionQueue:
    def __init__(self) -> None:
        self._actions: dict[str, list[Action]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def enqueue(self, action: Action) -> None:
        async with self._lock:
            self._actions[str(action.property_id)].append(action)

    async def list_pending(self, property_id: PropertyId) -> list[Action]:
        return list(self._actions[str(property_id)])


class InMemoryAuditLog:
    def __init__(self) -> None:
        self.entries: list[dict[str, Any]] = []
        self._lock = asyncio.Lock()

    async def emit(self, *, actor: str, action: str, before_hash: str | None,
                   after_hash: str, correlation_id: str) -> None:
        async with self._lock:
            self.entries.append({
                "actor": actor,
                "action": action,
                "before_hash": before_hash,
                "after_hash": after_hash,
                "correlation_id": correlation_id,
            })


class StubReasoner:
    """Deterministic reasoner for tests. Real adapters: HaikuRouter, OpusReasoner (ADR 0004)."""

    def __init__(self, *, scripted: dict[str, dict[str, object]] | None = None) -> None:
        self._scripted = scripted or {}

    async def route(self, *, prompt: str, schema_name: str) -> dict[str, object]:
        return self._scripted.get(f"route:{schema_name}", {})

    async def reason(self, *, prompt: str, schema_name: str) -> dict[str, object]:
        return self._scripted.get(
            f"reason:{schema_name}",
            {
                "proposals": [
                    {
                        "kind": "pms.note.add",
                        "payload": {"text": "VIP arrival — verify allergy notes on file."},
                        "reasoning": [
                            "booking.created signal received",
                            "no prior allergy note on profile",
                        ],
                        "confidence": 0.92,
                        "reversible": True,
                    }
                ]
            },
        )
