"""
Module: storia.domain
Layer: domain
Ports: defined in storia.domain.ports
MCP integration: none (domain is SDK-free)
Stack: Python 3.12 stdlib + Pydantic (frozen models only)

Pure business model. Imports nothing from infrastructure, presentation, or third-party SDKs.
Pydantic is permitted for frozen model validation only; pydantic.networks / validators with
side effects are forbidden by import-linter and review.
"""
from storia.domain.models import (
    Action,
    ActionStatus,
    Booking,
    Guest,
    GuestEvent,
    GuestId,
    OperatorId,
    PropertyId,
    Signal,
    SignalKind,
    Stay,
    StayId,
)
from storia.domain.playbook import Guardrail, Playbook, PlaybookNode

__all__ = [
    "Action",
    "ActionStatus",
    "Booking",
    "Guest",
    "GuestEvent",
    "GuestId",
    "Guardrail",
    "OperatorId",
    "Playbook",
    "PlaybookNode",
    "PropertyId",
    "Signal",
    "SignalKind",
    "Stay",
    "StayId",
]
