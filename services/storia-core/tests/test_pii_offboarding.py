"""PII encryption + tenant offboarding (PRD §6.5, ADR 0007)."""
from __future__ import annotations

from uuid import uuid4

import pytest

from storia.application.offboard_tenant import OffboardTenant, OffboardTenantRequest
from storia.domain.ids import OperatorId
from storia.domain.tenant import CrossTenantAccessError, TenantContext
from storia.infrastructure.encryption import FernetFieldEncryptor, TenantKeyMissingError
from storia.infrastructure.in_memory import InMemoryAuditLog


@pytest.mark.asyncio
async def test_encrypt_decrypt_round_trip() -> None:
    enc = FernetFieldEncryptor()
    op = OperatorId(uuid4())
    cipher = await enc.encrypt(operator_id=op, plaintext="passport AB123456")
    assert "AB123456" not in cipher
    plain = await enc.decrypt(operator_id=op, ciphertext=cipher)
    assert plain == "passport AB123456"


@pytest.mark.asyncio
async def test_rotation_keeps_old_ciphertext_readable() -> None:
    enc = FernetFieldEncryptor()
    op = OperatorId(uuid4())
    cipher_v1 = await enc.encrypt(operator_id=op, plaintext="value-v1")
    await enc.rotate(operator_id=op)
    # Old ciphertext still readable; new writes use the new key.
    assert await enc.decrypt(operator_id=op, ciphertext=cipher_v1) == "value-v1"
    cipher_v2 = await enc.encrypt(operator_id=op, plaintext="value-v2")
    assert cipher_v1 != cipher_v2
    assert await enc.decrypt(operator_id=op, ciphertext=cipher_v2) == "value-v2"


@pytest.mark.asyncio
async def test_crypto_erase_makes_data_unreadable() -> None:
    enc = FernetFieldEncryptor()
    op = OperatorId(uuid4())
    cipher = await enc.encrypt(operator_id=op, plaintext="x")
    await enc.crypto_erase(operator_id=op)
    with pytest.raises(TenantKeyMissingError):
        await enc.decrypt(operator_id=op, ciphertext=cipher)
    with pytest.raises(TenantKeyMissingError):
        await enc.encrypt(operator_id=op, plaintext="y")


@pytest.mark.asyncio
async def test_offboard_tenant_requires_export_confirmation() -> None:
    enc = FernetFieldEncryptor()
    audit = InMemoryAuditLog()
    op = OperatorId(uuid4())
    uc = OffboardTenant(encryptor=enc, audit=audit)
    with pytest.raises(ValueError, match="export must be confirmed"):
        await uc(OffboardTenantRequest(
            tenant=TenantContext(operator_id=op), operator_id=op,
            actor="admin@op", export_confirmation_token="", correlation_id="c",
        ))


@pytest.mark.asyncio
async def test_offboard_tenant_rejects_cross_tenant() -> None:
    enc = FernetFieldEncryptor()
    uc = OffboardTenant(encryptor=enc, audit=InMemoryAuditLog())
    own, other = OperatorId(uuid4()), OperatorId(uuid4())
    with pytest.raises(CrossTenantAccessError):
        await uc(OffboardTenantRequest(
            tenant=TenantContext(operator_id=own), operator_id=other,
            actor="admin", export_confirmation_token="ok", correlation_id="c",
        ))


@pytest.mark.asyncio
async def test_offboard_tenant_crypto_erases_and_audits() -> None:
    enc = FernetFieldEncryptor()
    audit = InMemoryAuditLog()
    op = OperatorId(uuid4())
    cipher = await enc.encrypt(operator_id=op, plaintext="passport")
    uc = OffboardTenant(encryptor=enc, audit=audit)
    await uc(OffboardTenantRequest(
        tenant=TenantContext(operator_id=op), operator_id=op,
        actor="admin@op", export_confirmation_token="gs://exports/op-1.jsonl.gz",
        correlation_id="off-1",
    ))
    with pytest.raises(TenantKeyMissingError):
        await enc.decrypt(operator_id=op, ciphertext=cipher)
    assert any(e["action"] == "tenant.offboarded" for e in audit.entries)
