"""
Module: storia.application.evaluate_playbook
Layer: application
Ports: ActionQueue, AuditLog
MCP integration: exposed as MCP tool `evaluate_playbook` in the Action Engine server
Stack: stdlib + storia.domain

Deterministic playbook evaluation. Walks the JSON-graph playbook (ADR 0006), matches
triggers against the incoming signal, applies guardrails declaratively, and produces
Actions for every reachable ACTION node.

This is the non-LLM path. The LLM-assisted reasoning (QueuePreArrivalActions, ADR 0004)
sits on top of this for the open-ended pre-arrival flow. The three pilot flows in
storia.application.playbooks all run on this deterministic evaluator.
"""
from __future__ import annotations

from dataclasses import dataclass

from storia.domain.ids import PropertyId, StayId
from storia.domain.models import Action, Signal
from storia.domain.playbook import NodeKind, Playbook
from storia.domain.ports import ActionQueue, AuditLog


@dataclass(frozen=True, slots=True)
class EvaluatePlaybookRequest:
    playbook: Playbook
    signal: Signal
    stay_id: StayId
    property_id: PropertyId
    correlation_id: str
    # Counters supplied by the caller — kept domain-pure (the caller owns time/state lookup).
    suggestions_last_24h: int = 0
    lead_hours: int | None = None


class EvaluatePlaybook:
    def __init__(self, *, queue: ActionQueue, audit: AuditLog) -> None:
        self._queue = queue
        self._audit = audit

    async def __call__(self, req: EvaluatePlaybookRequest) -> list[Action]:
        triggers = [n for n in req.playbook.nodes if n.kind is NodeKind.TRIGGER]
        if not any(self._trigger_matches(n.spec, req) for n in triggers):
            return []

        if not self._guardrails_pass(req):
            return []

        index = {n.key: n for n in req.playbook.nodes}
        reachable_action_keys = self._collect_reachable_actions(triggers, index)

        produced: list[Action] = []
        for key in reachable_action_keys:
            node = index[key]
            spec = node.spec
            kind = str(spec.get("kind", ""))
            template = str(spec.get("template", ""))
            auto = bool(spec.get("auto_approve", False))
            reversible = bool(spec.get("reversible", True))
            action = Action.propose(
                stay_id=req.stay_id,
                property_id=req.property_id,
                playbook_id=req.playbook.id.value,
                kind=kind,
                payload={"template": template,
                         "signal_kind": req.signal.kind.value},
                reasoning=(
                    f"playbook={req.playbook.name}@v{req.playbook.version}",
                    f"signal={req.signal.kind.value}@{req.signal.occurred_at.isoformat()}",
                ),
                reversible=reversible,
                auto_approved=auto and reversible,
            )
            await self._queue.enqueue(action)
            await self._audit.emit(
                actor="system:storia.application.evaluate_playbook",
                action=f"action.{action.status.value}",
                before_hash=None,
                after_hash=_hash(action.model_dump_json()),
                correlation_id=req.correlation_id,
            )
            produced.append(action)
        return produced

    @staticmethod
    def _trigger_matches(spec: dict[str, object], req: EvaluatePlaybookRequest) -> bool:
        want = spec.get("signal_kind")
        return want is None or want == req.signal.kind.value

    @staticmethod
    def _guardrails_pass(req: EvaluatePlaybookRequest) -> bool:
        # Declarative guardrails: spec keys checked against request counters.
        for node in req.playbook.nodes:
            if node.kind is not NodeKind.GUARDRAIL:
                continue
            spec = node.spec
            if "min_lead_hours" in spec and req.lead_hours is not None:
                if req.lead_hours < int(spec["min_lead_hours"]):  # type: ignore[arg-type]
                    return False
            if "max_suggestions_24h" in spec:
                if req.suggestions_last_24h >= int(spec["max_suggestions_24h"]):  # type: ignore[arg-type]
                    return False
        return True

    @staticmethod
    def _collect_reachable_actions(triggers: list, index: dict) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []
        stack = [t.key for t in triggers]
        while stack:
            k = stack.pop(0)
            if k in seen:
                continue
            seen.add(k)
            node = index[k]
            if node.kind is NodeKind.ACTION:
                ordered.append(k)
            stack.extend(node.next)
        return ordered


def _hash(s: str) -> str:
    import hashlib
    return hashlib.sha256(s.encode("utf-8")).hexdigest()
