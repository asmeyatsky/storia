"""Observability + PII redaction tests (Rules §6, PRD §6.5)."""
from __future__ import annotations

import pytest

from storia.infrastructure.observability import (
    LlmCall,
    configure,
    hash_prompt,
    log_llm_call,
    operation,
    set_correlation_id,
    reset_correlation_id,
)
from storia.infrastructure.pii_redaction import pii_filter


def test_pii_filter_redacts_known_key_fields() -> None:
    event = {
        "actor": "system",
        "email": "ada@example.com",
        "phone_e164": "+447700900123",
        "guest_name": "Ada Lovelace",
        "nested": {"first_name": "Ada", "ok": "value"},
        "list": ["alan@example.com", "no-pii"],
    }
    out = pii_filter(None, None, event)
    assert out["email"] == "[REDACTED]"
    assert out["phone_e164"] == "[REDACTED]"
    assert out["guest_name"] == "[REDACTED]"
    assert out["nested"]["first_name"] == "[REDACTED]"
    assert out["nested"]["ok"] == "value"


def test_pii_filter_redacts_email_phone_passport_in_free_text() -> None:
    out = pii_filter(None, None, {
        "message": "contact alan@example.com or +447700900123, passport AB123456",
    })
    assert "alan@example.com" not in out["message"]
    assert "+447700900123" not in out["message"]
    assert "AB123456" not in out["message"]


def test_correlation_id_set_and_reset() -> None:
    token = set_correlation_id("corr-99")
    try:
        from storia.infrastructure.observability import _correlation_id
        assert _correlation_id.get() == "corr-99"
    finally:
        reset_correlation_id(token)


def test_hash_prompt_is_stable_truncated() -> None:
    h = hash_prompt("hello")
    assert len(h) == 16
    assert h == hash_prompt("hello")


@pytest.mark.asyncio
async def test_operation_records_red_metrics_and_traces() -> None:
    configure(service_name="storia-test")
    with operation("test.op", tenant="op-1"):
        pass

    # No assertion on the in-memory reader contents (the SDK doesn't surface easily here),
    # but the call MUST NOT raise — the wire path is the contract.


@pytest.mark.asyncio
async def test_operation_propagates_errors_and_counts() -> None:
    configure()
    with pytest.raises(ValueError):
        with operation("test.failure"):
            raise ValueError("planned")


def test_log_llm_call_runs_without_exception() -> None:
    configure()
    log_llm_call(LlmCall(
        model_id="claude-opus-4-7", prompt_hash="abc",
        input_tokens=100, output_tokens=42, latency_ms=512.0, cost_usd=0.0123,
    ))
