"""VAID/CRUCIBLE/SENTINEL adapter tests (ADR 0002)."""
from __future__ import annotations

from uuid import uuid4

import pytest

from storia.domain.ids import OperatorId
from storia.infrastructure.synthera import (
    HmacAgentProvenance,
    StubEvalHarness,
    StubPolicyGuard,
)


@pytest.mark.asyncio
async def test_vaid_sign_verify_round_trip() -> None:
    vaid = HmacAgentProvenance(secret=b"x" * 32)
    sig = await vaid.sign(agent_id="agent-1", action_id="a-1", body_hash="abc")
    assert await vaid.verify(signature=sig, agent_id="agent-1", action_id="a-1",
                             body_hash="abc")


@pytest.mark.asyncio
async def test_vaid_verify_rejects_tampered_signature() -> None:
    vaid = HmacAgentProvenance(secret=b"x" * 32)
    sig = await vaid.sign(agent_id="agent-1", action_id="a-1", body_hash="abc")
    assert not await vaid.verify(signature=sig, agent_id="agent-1", action_id="a-1",
                                 body_hash="DIFFERENT")


@pytest.mark.asyncio
async def test_crucible_runs_suite_with_deterministic_stub() -> None:
    h = StubEvalHarness(threshold=0.0, fixed_score=0.99)
    result = await h.run_suite(suite="s", model_id="m", prompt_template_hash="p")
    assert result["passed"]
    assert result["score"] == 0.99


@pytest.mark.asyncio
async def test_crucible_fails_below_threshold() -> None:
    h = StubEvalHarness(threshold=0.95, fixed_score=0.50)
    result = await h.run_suite(suite="s", model_id="m", prompt_template_hash="p")
    assert not result["passed"]


@pytest.mark.asyncio
async def test_sentinel_policy_blocks_denied_kind() -> None:
    op = OperatorId(uuid4())
    guard = StubPolicyGuard(denied={str(op): frozenset({"pms.room.assign"})})
    assert not await guard.allow(operator_id=op, action_kind="pms.room.assign",
                                 payload_hash="x")
    assert await guard.allow(operator_id=op, action_kind="pms.note.add",
                             payload_hash="x")
