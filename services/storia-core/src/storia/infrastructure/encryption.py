"""
Module: storia.infrastructure.encryption
Layer: infrastructure
Ports: implements FieldEncryptor (PRD §6.5, ADR 0007 per-tenant CMEK).
MCP integration: none
Stack: cryptography (Fernet) + stdlib

Two adapters:
  FernetFieldEncryptor   — dev/test. Per-tenant key kept in memory; rotate generates
                           a new key; crypto_erase destroys it (PRD §6.5 right-to-erasure).
  KmsFieldEncryptor      — production stub. Composition root wires Google Cloud KMS;
                           interface identical so swapping is a configuration change.
"""
from __future__ import annotations

import asyncio
import base64

from cryptography.fernet import Fernet, MultiFernet

from storia.domain.ids import OperatorId


class TenantKeyMissingError(KeyError):
    """Raised when an operator's CMEK has been crypto-erased (PRD §6.5)."""


class FernetFieldEncryptor:
    """In-memory per-tenant Fernet. Multiple-key list supports rotation."""

    def __init__(self) -> None:
        self._keys: dict[str, list[bytes]] = {}
        self._lock = asyncio.Lock()

    async def _ensure(self, operator_id: OperatorId) -> MultiFernet:
        op = str(operator_id)
        async with self._lock:
            if op not in self._keys:
                self._keys[op] = [Fernet.generate_key()]
        return MultiFernet([Fernet(k) for k in self._keys[op]])

    async def encrypt(self, *, operator_id: OperatorId, plaintext: str) -> str:
        op = str(operator_id)
        if op in self._keys and not self._keys[op]:
            raise TenantKeyMissingError(op)
        fernet = await self._ensure(operator_id)
        return base64.urlsafe_b64encode(fernet.encrypt(plaintext.encode("utf-8"))).decode("ascii")

    async def decrypt(self, *, operator_id: OperatorId, ciphertext: str) -> str:
        op = str(operator_id)
        if op not in self._keys or not self._keys[op]:
            raise TenantKeyMissingError(op)
        fernet = MultiFernet([Fernet(k) for k in self._keys[op]])
        return fernet.decrypt(base64.urlsafe_b64decode(ciphertext.encode("ascii"))).decode("utf-8")

    async def rotate(self, *, operator_id: OperatorId) -> None:
        op = str(operator_id)
        async with self._lock:
            new = Fernet.generate_key()
            self._keys.setdefault(op, [])
            # MultiFernet decrypts with any; first key is primary for new writes.
            self._keys[op] = [new, *self._keys[op]]

    async def crypto_erase(self, *, operator_id: OperatorId) -> None:
        """ADR 0007 — destroy the per-tenant key. All ciphertext becomes unreadable."""
        async with self._lock:
            self._keys[str(operator_id)] = []
