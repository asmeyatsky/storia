"""
Module: storia.domain.models
Layer: domain
Ports: none (pure model)
MCP integration: none
Stack: stdlib + pydantic frozen models

Immutable domain models. State changes return new instances (Rules §3.3).
Invariants enforced in factories (Rules §3.4) — never via setters.
"""
from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Self
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from storia.domain.ids import (
    ActionId,
    GuestId,
    OperatorId,
    PropertyId,
    SignalId,
    StayId,
)

# Re-exported for module-public surface.
__all__ = [
    "Action",
    "ActionStatus",
    "Booking",
    "Guest",
    "GuestEvent",
    "GuestEventKind",
    "GuestId",
    "OperatorId",
    "PropertyId",
    "Signal",
    "SignalKind",
    "Stay",
    "StayId",
]


_FROZEN = ConfigDict(frozen=True, extra="forbid", strict=True)


def _now() -> datetime:
    return datetime.now(UTC)


class Booking(BaseModel):
    model_config = _FROZEN

    pms_booking_id: str
    pms: str  # "mews" | "cloudbeds" | "opera"
    arrival: datetime
    departure: datetime
    room_code: str | None
    rate_code: str | None
    channel: str | None

    @classmethod
    def create(cls, *, pms_booking_id: str, pms: str, arrival: datetime, departure: datetime,
               room_code: str | None = None, rate_code: str | None = None,
               channel: str | None = None) -> Booking:
        if not pms_booking_id:
            raise ValueError("pms_booking_id is required")
        if pms not in {"mews", "cloudbeds", "opera"}:
            raise ValueError(f"unsupported pms: {pms}")
        if departure <= arrival:
            raise ValueError("departure must be strictly after arrival")
        if arrival.tzinfo is None or departure.tzinfo is None:
            raise ValueError("arrival and departure must be timezone-aware")
        return cls(pms_booking_id=pms_booking_id, pms=pms, arrival=arrival,
                   departure=departure, room_code=room_code, rate_code=rate_code,
                   channel=channel)


class Guest(BaseModel):
    """Canonical guest. Profile fields are derived from GuestEvent history."""
    model_config = _FROZEN

    id: GuestId
    primary_email_hash: str | None  # sha256 of normalised email; raw PII never in domain
    display_name: str  # operator-visible only; not used for matching

    @classmethod
    def new(cls, display_name: str, primary_email_hash: str | None = None) -> Guest:
        if not display_name.strip():
            raise ValueError("display_name required")
        return cls(id=GuestId(uuid4()), primary_email_hash=primary_email_hash,
                   display_name=display_name.strip())


class SignalKind(str, Enum):
    BOOKING_CREATED = "booking.created"
    BOOKING_MODIFIED = "booking.modified"
    POS_TRANSACTION = "pos.transaction"
    REVIEW_POSTED = "review.posted"
    FLIGHT_ARRIVED = "flight.arrived"
    WEATHER_ENRICHED = "weather.enriched"
    COMPLAINT = "complaint"
    CONCIERGE_NOTE = "concierge.note"


class Signal(BaseModel):
    model_config = _FROZEN

    id: SignalId
    guest_id: GuestId
    property_id: PropertyId
    kind: SignalKind
    occurred_at: datetime
    payload: dict[str, str | int | float | bool | None]

    @classmethod
    def observe(cls, *, guest_id: GuestId, property_id: PropertyId, kind: SignalKind,
                occurred_at: datetime, payload: dict[str, str | int | float | bool | None]
                ) -> Signal:
        if occurred_at.tzinfo is None:
            raise ValueError("occurred_at must be timezone-aware")
        if occurred_at > _now():
            raise ValueError("signals cannot be observed in the future")
        return cls(id=SignalId(uuid4()), guest_id=guest_id, property_id=property_id,
                   kind=kind, occurred_at=occurred_at, payload=dict(payload))


class Stay(BaseModel):
    model_config = _FROZEN

    id: StayId
    guest_id: GuestId
    property_id: PropertyId
    booking: Booking

    @classmethod
    def begin(cls, *, guest_id: GuestId, property_id: PropertyId, booking: Booking) -> Stay:
        return cls(id=StayId(uuid4()), guest_id=guest_id, property_id=property_id,
                   booking=booking)


class ActionStatus(str, Enum):
    QUEUED = "queued"               # waiting for human approval
    AUTO_APPROVED = "auto_approved"  # guardrail permits auto-execute
    EXECUTED = "executed"
    REJECTED = "rejected"
    REVERSED = "reversed"


class Action(BaseModel):
    """An operational behaviour produced by the Action Engine.

    Invariant (Rules §4.5, PRD §5.2.2): every action is reversible OR requires human approval.
    """
    model_config = _FROZEN

    id: ActionId
    stay_id: StayId
    property_id: PropertyId
    playbook_id: UUID
    kind: str  # e.g. "pms.note.add", "pms.room.assign", "messaging.draft"
    payload: dict[str, str | int | float | bool | None]
    reasoning: tuple[str, ...]  # the "why" — signal ids / plain-language causes (FR-PA-6)
    status: ActionStatus
    reversible: bool
    created_at: datetime

    @classmethod
    def propose(cls, *, stay_id: StayId, property_id: PropertyId, playbook_id: UUID,
                kind: str, payload: dict[str, str | int | float | bool | None],
                reasoning: tuple[str, ...], reversible: bool,
                auto_approved: bool) -> Action:
        if not kind:
            raise ValueError("kind required")
        if not reasoning:
            raise ValueError("every action must carry reasoning (FR-PA-6)")
        if not reversible and auto_approved:
            raise ValueError(
                "non-reversible actions must require human approval (Rules §4.5, PRD §5.2.2)"
            )
        status = ActionStatus.AUTO_APPROVED if auto_approved else ActionStatus.QUEUED
        return cls(id=ActionId(uuid4()), stay_id=stay_id, property_id=property_id,
                   playbook_id=playbook_id, kind=kind, payload=dict(payload),
                   reasoning=tuple(reasoning), status=status, reversible=reversible,
                   created_at=_now())

    def executed(self) -> Self:
        if self.status not in {ActionStatus.AUTO_APPROVED, ActionStatus.QUEUED}:
            raise ValueError(f"cannot execute action in status {self.status}")
        return self.model_copy(update={"status": ActionStatus.EXECUTED})

    def rejected(self) -> Self:
        if self.status is ActionStatus.EXECUTED:
            raise ValueError("executed actions cannot be rejected; reverse instead")
        return self.model_copy(update={"status": ActionStatus.REJECTED})

    def reversed_(self) -> Self:
        if not self.reversible:
            raise ValueError("action is not reversible")
        if self.status is not ActionStatus.EXECUTED:
            raise ValueError("only executed actions can be reversed")
        return self.model_copy(update={"status": ActionStatus.REVERSED})


class GuestEventKind(str, Enum):
    PROFILE_OBSERVED = "profile.observed"
    PROFILE_MERGED = "profile.merged"
    BOOKING_ATTACHED = "booking.attached"
    SIGNAL_RECORDED = "signal.recorded"
    ACTION_APPENDED = "action.appended"


class GuestEvent(BaseModel):
    """Append-only ledger event (PRD §6.2). The guest profile is derived state."""
    model_config = _FROZEN

    sequence: int = Field(ge=0)
    operator_id: OperatorId
    guest_id: GuestId
    kind: GuestEventKind
    occurred_at: datetime
    body: dict[str, str | int | float | bool | None]
    source: str  # "mews" | "cloudbeds" | "concierge" | etc — provenance is mandatory

    @classmethod
    def record(cls, *, sequence: int, operator_id: OperatorId, guest_id: GuestId,
               kind: GuestEventKind, body: dict[str, str | int | float | bool | None],
               source: str) -> GuestEvent:
        if not source:
            raise ValueError("source is mandatory — no synthetic data without provenance (PRD §5.2.1)")
        if sequence < 0:
            raise ValueError("sequence must be non-negative")
        return cls(sequence=sequence, operator_id=operator_id, guest_id=guest_id, kind=kind,
                   occurred_at=_now(), body=dict(body), source=source)
