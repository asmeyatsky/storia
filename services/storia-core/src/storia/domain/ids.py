"""
Module: storia.domain.ids
Layer: domain
Strongly-typed identifiers. Constructors enforce invariants (Rules §3.4).
"""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class _Id:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise TypeError(f"{type(self).__name__} requires UUID, got {type(self.value).__name__}")

    def __str__(self) -> str:
        return str(self.value)


class OperatorId(_Id): ...
class PropertyId(_Id): ...
class GuestId(_Id): ...
class StayId(_Id): ...
class ActionId(_Id): ...
class SignalId(_Id): ...
class PlaybookId(_Id): ...
