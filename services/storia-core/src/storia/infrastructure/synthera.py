"""
Module: storia.infrastructure.synthera
Layer: infrastructure
Ports: implements AgentProvenance (VAID), EvalHarness (CRUCIBLE), PolicyGuard (SENTINEL).
MCP integration: each is called from the Action Engine MCP server before/after a tool call.
Stack: HMAC for the VAID stub, plain function calls for the eval/policy stubs.

These are the seams ADR 0002 promised. Production substitutes the real SYNTHERA Labs
SDKs at the composition root; STORIA's domain remains SDK-free.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets

from storia.domain.ids import OperatorId


class HmacAgentProvenance:
    """Local-key VAID stub. Real adapter exchanges identity claims with the SYNTHERA service."""

    def __init__(self, *, secret: bytes | None = None) -> None:
        self._secret = secret or secrets.token_bytes(32)

    async def sign(self, *, agent_id: str, action_id: str, body_hash: str) -> str:
        msg = f"{agent_id}|{action_id}|{body_hash}".encode("utf-8")
        return hmac.new(self._secret, msg, hashlib.sha256).hexdigest()

    async def verify(self, *, signature: str, agent_id: str, action_id: str,
                     body_hash: str) -> bool:
        expected = await self.sign(agent_id=agent_id, action_id=action_id,
                                   body_hash=body_hash)
        return hmac.compare_digest(expected, signature)


class StubEvalHarness:
    """CRUCIBLE regression-suite stub. Real adapter posts to the CRUCIBLE service;
    this returns a deterministic shape so the CI gate has something to assert on."""

    def __init__(self, *, threshold: float = 0.85, fixed_score: float | None = None) -> None:
        self._threshold = threshold
        self._fixed = fixed_score

    async def run_suite(self, *, suite: str, model_id: str,
                        prompt_template_hash: str) -> dict[str, object]:
        if self._fixed is not None:
            score = self._fixed
        else:
            # Deterministic scoring keyed on the prompt hash so flaky tests aren't possible.
            digest = int(hashlib.sha256(
                f"{suite}|{model_id}|{prompt_template_hash}".encode("utf-8")
            ).hexdigest(), 16)
            score = (digest % 1000) / 1000.0
        return {
            "suite": suite,
            "model_id": model_id,
            "prompt_template_hash": prompt_template_hash,
            "score": score,
            "passed": score >= self._threshold,
            "threshold": self._threshold,
        }


class StubPolicyGuard:
    """SENTINEL policy stub. Maintains an operator-scoped denylist of action kinds."""

    def __init__(self, *, denied: dict[str, frozenset[str]] | None = None) -> None:
        self._denied = denied or {}

    async def allow(self, *, operator_id: OperatorId, action_kind: str,
                    payload_hash: str) -> bool:
        return action_kind not in self._denied.get(str(operator_id), frozenset())
