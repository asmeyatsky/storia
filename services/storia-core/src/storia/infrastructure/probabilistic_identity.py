"""
Module: storia.infrastructure.probabilistic_identity
Layer: infrastructure
Ports: implements IdentityResolver; depends on ReviewQueue
MCP integration: none (called by application use cases)
Stack: stdlib

PRD §6.3 strategy:
  1. Deterministic match first (email hash, phone hash, loyalty number).
  2. Probabilistic match second — Jaro-Winkler on normalised display_name + token-set
     overlap on partial identifiers. Above THRESHOLD_AUTO → merge candidate written to
     the operator review queue (NOT auto-merged — Rules §3.4 invariants in factories,
     PRD §6.3 "all merges reversible, no destructive merges in v1").
  3. Below THRESHOLD_AUTO → new guest.

The pilot-phase deliberately writes candidates to the review queue rather than auto-merging.
Auto-merge is a Repeat-phase decision once we have a per-operator false-merge rate.
"""
from __future__ import annotations

import asyncio
import unicodedata
from collections import defaultdict

from storia.domain.ids import GuestId, OperatorId
from storia.domain.models import Guest
from storia.domain.ports import ReviewQueue

THRESHOLD_QUEUE = 0.80  # below this → new guest; above → queue for operator review


def _normalise_name(name: str) -> str:
    folded = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    return " ".join(folded.lower().split())


def _jaccard(a: str, b: str) -> float:
    """Simple token-set Jaccard. Deterministic and cheap; replaceable by Jaro-Winkler
    later behind the same port."""
    sa, sb = set(a.split()), set(b.split())
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


class ProbabilisticIdentityResolver:
    """Deterministic-first, probabilistic-second, queue-don't-merge resolver."""

    def __init__(self, *, queue: ReviewQueue) -> None:
        self._queue = queue
        self._by_email: dict[tuple[str, str], Guest] = {}
        self._by_phone: dict[tuple[str, str], Guest] = {}
        self._by_loyalty: dict[tuple[str, str], Guest] = {}
        self._by_name: dict[str, list[Guest]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def resolve(self, *, operator_id: OperatorId, email_hash: str | None,
                      phone_hash: str | None, loyalty_number: str | None,
                      display_name: str) -> Guest:
        op = str(operator_id)
        async with self._lock:
            # Deterministic pass.
            for table, key in (
                (self._by_loyalty, loyalty_number),
                (self._by_email, email_hash),
                (self._by_phone, phone_hash),
            ):
                if key is not None:
                    existing = table.get((op, key))
                    if existing is not None:
                        return existing

            # Probabilistic pass — name token overlap among same-operator candidates.
            normalised = _normalise_name(display_name)
            best: tuple[float, Guest] | None = None
            for candidate in self._by_name[op]:
                score = _jaccard(normalised, _normalise_name(candidate.display_name))
                if best is None or score > best[0]:
                    best = (score, candidate)

            new_guest = Guest.new(display_name=display_name, primary_email_hash=email_hash)
            if best is not None and best[0] >= THRESHOLD_QUEUE:
                # Don't auto-merge. Surface to operator review queue (PRD §6.3).
                await self._queue.enqueue_merge_candidate(
                    operator_id=operator_id,
                    candidate_a_id=best[1].id,
                    candidate_b_id=new_guest.id,
                    confidence=best[0],
                    evidence={"matched_on": "display_name", "score": f"{best[0]:.3f}"},
                )

            if email_hash:
                self._by_email[(op, email_hash)] = new_guest
            if phone_hash:
                self._by_phone[(op, phone_hash)] = new_guest
            if loyalty_number:
                self._by_loyalty[(op, loyalty_number)] = new_guest
            self._by_name[op].append(new_guest)
            return new_guest
