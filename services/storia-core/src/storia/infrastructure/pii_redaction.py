"""
Module: storia.infrastructure.pii_redaction
Layer: infrastructure
Ports: none — supplies a structlog processor consumed by observability config.
MCP integration: none
Stack: stdlib + structlog

Log-event PII filter (PRD §6.5 — "Never logged" rows). Applied before the JSON renderer
so no PII reaches Cloud Logging. Defence-in-depth: domain hashes email/phone before they
enter the layer, this is the second wall.

Strategy:
  - Walk the event dict, redact keys matching a denylist.
  - For free-form text fields, regex-strip email-like, phone-like, and passport-like
    substrings. Conservative: false positives are fine, false negatives are not.
"""
from __future__ import annotations

import re
from typing import Any

_REDACTED = "[REDACTED]"

_PII_KEYS = frozenset({
    "email", "phone", "phone_e164", "passport", "name", "display_name",
    "first_name", "last_name", "address", "dob", "loyalty_number",
    "guest_email", "guest_phone", "guest_name",
})

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(r"\+?\d[\d\s().-]{7,}\d")
_PASSPORT_RE = re.compile(r"\b[A-Z]{1,2}[0-9]{6,9}\b")


def _scrub_text(value: str) -> str:
    value = _EMAIL_RE.sub(_REDACTED, value)
    value = _PHONE_RE.sub(_REDACTED, value)
    value = _PASSPORT_RE.sub(_REDACTED, value)
    return value


def _scrub(node: Any) -> Any:
    if isinstance(node, dict):
        return {
            k: (_REDACTED if k.lower() in _PII_KEYS else _scrub(v))
            for k, v in node.items()
        }
    if isinstance(node, list):
        return [_scrub(v) for v in node]
    if isinstance(node, tuple):
        return tuple(_scrub(v) for v in node)
    if isinstance(node, str):
        return _scrub_text(node)
    return node


def pii_filter(_: object, __: object, event_dict: dict[str, Any]) -> dict[str, Any]:
    """structlog processor — redacts the event dict in place-equivalent."""
    return _scrub(event_dict)  # type: ignore[no-any-return]
