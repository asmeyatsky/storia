"""
Module: storia.infrastructure.observability
Layer: infrastructure
Ports: implements no domain port — it provides operators (loggers, tracers) the
       application layer is given by the composition root.
MCP integration: every MCP tool wraps a use case call in tool_span().
Stack: structlog + OpenTelemetry SDK (Rules §6).

What this module gives the rest of the system (Rules §6):
  - JSON structured logs with a correlation id, NO PII
  - OpenTelemetry trace propagation through MCP calls
  - RED helpers (request/error/duration) per endpoint and per MCP tool
  - Per-AI-call log capture: model_id, prompt_hash, tokens in/out, latency_ms, cost_usd

The PII redaction filter (storia.infrastructure.pii_redaction) is composed in before this
module — by the time a log event arrives here it must already be PII-free.
"""
from __future__ import annotations

import contextvars
import hashlib
import logging
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

import structlog
from opentelemetry import metrics, trace
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.trace import TracerProvider

_correlation_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id", default="-"
)


def set_correlation_id(value: str) -> contextvars.Token[str]:
    return _correlation_id.set(value)


def reset_correlation_id(token: contextvars.Token[str]) -> None:
    _correlation_id.reset(token)


def _inject_correlation(_: object, __: object, event_dict: dict[str, Any]) -> dict[str, Any]:
    event_dict.setdefault("correlation_id", _correlation_id.get())
    return event_dict


def configure(*, service_name: str = "storia-core",
              metric_reader: InMemoryMetricReader | None = None,
              tracer_provider: TracerProvider | None = None) -> None:
    """Composition-root call. Idempotent."""
    from storia.infrastructure.pii_redaction import pii_filter
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            _inject_correlation,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.add_log_level,
            pii_filter,  # PRD §6.5 — must run BEFORE the renderer
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        cache_logger_on_first_use=True,
    )
    trace.set_tracer_provider(tracer_provider or TracerProvider())
    reader = metric_reader or InMemoryMetricReader()
    metrics.set_meter_provider(MeterProvider(metric_readers=[reader]))
    # Stash the reader so tests can drain it; meter providers don't expose readers natively.
    global _METRIC_READER
    _METRIC_READER = reader


_METRIC_READER: InMemoryMetricReader | None = None


def get_metric_reader() -> InMemoryMetricReader | None:
    """Test-only accessor to drain in-memory metrics."""
    return _METRIC_READER


_tracer = trace.get_tracer("storia")
_meter = metrics.get_meter("storia")

# RED metric registry. Names follow the OTel HTTP/RPC convention.
_request_counter = _meter.create_counter("storia.requests", unit="1",
                                         description="Total requests per operation")
_error_counter = _meter.create_counter("storia.errors", unit="1",
                                       description="Total errored requests per operation")
_duration_hist = _meter.create_histogram("storia.duration_ms", unit="ms",
                                         description="Duration per operation")


@dataclass(frozen=True, slots=True)
class LlmCall:
    model_id: str
    prompt_hash: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    cost_usd: float


def log_llm_call(call: LlmCall) -> None:
    """Per-AI-call log (Rules §6 — model ID, version, prompt hash, tokens in/out, latency, cost)."""
    structlog.get_logger("storia.llm").info(
        "llm.call",
        model_id=call.model_id,
        prompt_hash=call.prompt_hash,
        input_tokens=call.input_tokens,
        output_tokens=call.output_tokens,
        latency_ms=call.latency_ms,
        cost_usd=call.cost_usd,
    )


def hash_prompt(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]


@contextmanager
def operation(name: str, **attrs: object) -> Iterator[None]:
    """RED + tracing helper. Use to wrap a use case call from the composition root,
    presentation layer, or MCP boundary.

      with operation("ingest_booking", tenant="op-1"):
          ...
    """
    started = time.perf_counter()
    _request_counter.add(1, {"operation": name})
    span = _tracer.start_as_current_span(name)
    cm = span.__enter__()
    for k, v in attrs.items():
        try:
            cm.set_attribute(k, str(v))
        except Exception:
            pass
    errored = False
    try:
        yield
    except Exception:
        errored = True
        _error_counter.add(1, {"operation": name})
        raise
    finally:
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        _duration_hist.record(elapsed_ms, {"operation": name})
        span.__exit__(None, None, None)
        structlog.get_logger("storia.op").info(
            "op.done",
            operation=name, duration_ms=elapsed_ms, errored=errored,
        )
