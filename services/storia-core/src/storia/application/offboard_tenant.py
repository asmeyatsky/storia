"""
Module: storia.application.offboard_tenant
Layer: application
Ports: FieldEncryptor, EventStore, AuditLog
MCP integration: exposed as MCP tool `offboard_tenant` (admin-only scope, Rules §4.6)
Stack: stdlib + storia.domain

Implements ADR 0007:
  1. Export the tenant's event ledger to caller (delegated — caller writes to GCS).
  2. Crypto-erase the tenant's CMEK — all field-encrypted PII becomes unreadable.
  3. Audit the disposition, redacting any PII fields (defence in depth — the redactor
     scrubs the log event anyway).

The export step is intentionally caller-driven so the GCS bucket lives in caller-owned
infra; this use case is the gatekeeper that authorises the erase.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from storia.domain.ids import OperatorId
from storia.domain.ports import AuditLog, FieldEncryptor
from storia.domain.tenant import TenantContext


@dataclass(frozen=True, slots=True)
class OffboardTenantRequest:
    tenant: TenantContext
    operator_id: OperatorId
    actor: str  # operator-side admin id; never a STORIA-system actor
    export_confirmation_token: str  # caller-supplied proof export completed (ADR 0007)
    correlation_id: str


class OffboardTenant:
    def __init__(self, *, encryptor: FieldEncryptor, audit: AuditLog) -> None:
        self._encryptor = encryptor
        self._audit = audit

    async def __call__(self, req: OffboardTenantRequest) -> None:
        req.tenant.assert_owns(req.operator_id)
        if not req.export_confirmation_token.strip():
            raise ValueError("export must be confirmed before crypto-erase (ADR 0007)")

        await self._encryptor.crypto_erase(operator_id=req.operator_id)
        await self._audit.emit(
            actor=req.actor,
            action="tenant.offboarded",
            before_hash=None,
            after_hash=hashlib.sha256(
                f"{req.operator_id}|{req.export_confirmation_token}".encode("utf-8")
            ).hexdigest(),
            correlation_id=req.correlation_id,
        )
