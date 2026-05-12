"""
Module: storia.domain.tenant
Layer: domain
Ports: none
MCP integration: none — TenantContext is passed down by every MCP tool / API call
Stack: stdlib

Rules §3.6 — multi-tenancy is single-tenant-shaped. The TenantContext is the single
runtime carrier of operator scope. Every cross-operator data access raises
CrossTenantAccessError. Domain-level invariant; infrastructure cannot weaken it.
"""
from __future__ import annotations

from dataclasses import dataclass

from storia.domain.ids import OperatorId


class CrossTenantAccessError(RuntimeError):
    """Raised when code attempts to operate on a different operator's data than the
    one bound to the current TenantContext."""


@dataclass(frozen=True, slots=True)
class TenantContext:
    operator_id: OperatorId

    def assert_owns(self, operator_id: OperatorId) -> None:
        if operator_id != self.operator_id:
            raise CrossTenantAccessError(
                f"tenant {self.operator_id} attempted to access tenant {operator_id}"
            )
