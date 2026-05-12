"""
Module: storia.infrastructure.mews_pms
Layer: infrastructure
Ports: implements PmsAdapter
MCP integration: wrapped by storia.infrastructure.mcp.pms_server
Stack: httpx + Mews Marketplace OAuth (Rules §1 — Python at the integration boundary;
hot-path bulk pulls live in the Rust connector crate `storia-connectors-mews`).

Schema-contract enforcement on ingress/egress per PRD §7.2 — schema drift is Sev-2.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from storia.domain.ids import PropertyId
from storia.domain.models import Booking


class MewsPmsAdapter:
    pms_name = "mews"

    def __init__(self, *, client: Any, token_provider: Any, timeout_s: float = 5.0) -> None:
        # Every external call has a timeout (Rules §4). Circuit breaker provided by `client`.
        self._client = client
        self._tokens = token_provider
        self._timeout = timeout_s

    async def fetch_recent_bookings(self, property_id: PropertyId, since: datetime
                                    ) -> list[Booking]:  # pragma: no cover — integration only
        # See crates/storia-connectors-mews for the bulk hot-path implementation.
        # This Python adapter is for low-volume operator-triggered re-syncs.
        raise NotImplementedError("see Rust crate storia-connectors-mews for bulk ingest")

    async def add_guest_note(self, *, property_id: PropertyId, pms_booking_id: str,
                             note: str) -> None:  # pragma: no cover
        raise NotImplementedError

    async def assign_room(self, *, property_id: PropertyId, pms_booking_id: str,
                          room_code: str) -> None:  # pragma: no cover
        raise NotImplementedError
