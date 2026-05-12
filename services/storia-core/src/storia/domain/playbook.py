"""
Module: storia.domain.playbook
Layer: domain
Ports: none
MCP integration: none
Stack: stdlib + pydantic frozen models

Playbooks are stored as a versioned JSON graph (ADR 0006).
Invariants — no cycles, every action reachable, every guardrail terminating — enforced at
construction (Rules §3.4).
"""
from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict

from storia.domain.ids import PlaybookId

_FROZEN = ConfigDict(frozen=True, extra="forbid", strict=True)


class NodeKind(str, Enum):
    TRIGGER = "trigger"
    GUARDRAIL = "guardrail"
    ACTION = "action"


class PlaybookNode(BaseModel):
    model_config = _FROZEN
    key: str
    kind: NodeKind
    spec: dict[str, str | int | float | bool | list[str] | None]
    next: tuple[str, ...]  # downstream node keys (DAG edges)


class Guardrail(BaseModel):
    """Declarative rule constraining what may auto-execute (PRD FR-OC-5)."""
    model_config = _FROZEN
    predicate: str  # readable predicate; evaluated by application layer's guardrail engine
    on_pass: Literal["auto_execute", "queue"]
    on_fail: Literal["block", "escalate"]


class Playbook(BaseModel):
    model_config = _FROZEN

    id: PlaybookId
    name: str
    version: int
    nodes: tuple[PlaybookNode, ...]
    guardrails: tuple[Guardrail, ...]

    @classmethod
    def from_graph(cls, *, id: PlaybookId, name: str, version: int,
                   nodes: list[PlaybookNode], guardrails: list[Guardrail]) -> Playbook:
        if not name.strip():
            raise ValueError("name required")
        if version < 1:
            raise ValueError("version must be >= 1")
        keys = [n.key for n in nodes]
        if len(set(keys)) != len(keys):
            raise ValueError("node keys must be unique")
        key_set = set(keys)
        for n in nodes:
            for nxt in n.next:
                if nxt not in key_set:
                    raise ValueError(f"node {n.key!r} references unknown next {nxt!r}")
        _assert_dag(nodes)
        triggers = [n for n in nodes if n.kind is NodeKind.TRIGGER]
        actions = [n for n in nodes if n.kind is NodeKind.ACTION]
        if not triggers:
            raise ValueError("playbook must contain at least one trigger")
        if not actions:
            raise ValueError("playbook must contain at least one action")
        reachable = _reachable_from(triggers, nodes)
        unreachable_actions = [a.key for a in actions if a.key not in reachable]
        if unreachable_actions:
            raise ValueError(f"unreachable action nodes: {unreachable_actions}")
        return cls(id=id, name=name.strip(), version=version,
                   nodes=tuple(nodes), guardrails=tuple(guardrails))


def _assert_dag(nodes: list[PlaybookNode]) -> None:
    index = {n.key: n for n in nodes}
    WHITE, GREY, BLACK = 0, 1, 2
    color = {n.key: WHITE for n in nodes}

    def visit(k: str) -> None:
        if color[k] == GREY:
            raise ValueError(f"cycle detected at node {k!r}")
        if color[k] == BLACK:
            return
        color[k] = GREY
        for nxt in index[k].next:
            visit(nxt)
        color[k] = BLACK

    for k in list(color):
        if color[k] == WHITE:
            visit(k)


def _reachable_from(roots: list[PlaybookNode], nodes: list[PlaybookNode]) -> set[str]:
    index = {n.key: n for n in nodes}
    seen: set[str] = set()
    stack = [r.key for r in roots]
    while stack:
        k = stack.pop()
        if k in seen:
            continue
        seen.add(k)
        stack.extend(index[k].next)
    return seen
