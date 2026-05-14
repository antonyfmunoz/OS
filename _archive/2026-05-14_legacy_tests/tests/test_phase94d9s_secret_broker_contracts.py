"""Tests for Phase 94D.9S — Secret Broker Contracts."""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from runtime.substrate.secret_broker_contracts import (
    SecretBackendType,
    SecretRef,
    SecretScope,
    SecretUseAuditEvent,
    SecretUseGrant,
    SecretUseRequest,
    SecretUseStatus,
    validate_secret_use_grant,
    validate_secret_use_request,
)


def _sample_ref() -> SecretRef:
    return SecretRef(
        key="google_workspace_antonyfm_password",
        scope=SecretScope.GOOGLE_WORKSPACE,
        account="antonyfm@empyreanstudios.co",
        backend=SecretBackendType.LOCAL_ENV,
        description="Google Workspace password",
        available=True,
    )


class TestSecretRef:
    def test_repr_does_not_include_value(self) -> None:
        ref = _sample_ref()
        r = repr(ref)
        assert "value" not in r.lower() or "REDACTED" in r
        assert "password123" not in r

    def test_str_is_opaque_reference(self) -> None:
        ref = _sample_ref()
        s = str(ref)
        assert "[SECRET_REF:" in s
        assert ref.key in s

    def test_to_dict_redacts_value(self) -> None:
        ref = _sample_ref()
        d = ref.to_dict()
        assert d["value"] == "[REDACTED]"

    def test_to_dict_includes_metadata(self) -> None:
        ref = _sample_ref()
        d = ref.to_dict()
        assert d["key"] == "google_workspace_antonyfm_password"
        assert d["scope"] == "google_workspace"
        assert d["account"] == "antonyfm@empyreanstudios.co"


class TestSecretUseRequest:
    def test_serializes_without_secret_value(self) -> None:
        ref = _sample_ref()
        req = SecretUseRequest(
            secret_ref=ref,
            action_id="LOGIN_GOOGLE_DRIVE",
            work_order_id="WO-LOCAL-PILOT-GDRIVE-GDOCS-001",
            requested_by="local_pc_worker",
            reason="Login required after profile launch",
        )
        d = req.to_dict()
        assert d["secret_value"] == "[NEVER_INCLUDED]"
        assert "password" not in str(d.get("secret_value", "")).lower() or "NEVER" in str(d.get("secret_value", ""))

    def test_repr_does_not_include_value(self) -> None:
        ref = _sample_ref()
        req = SecretUseRequest(
            secret_ref=ref,
            action_id="LOGIN_GOOGLE_DRIVE",
            work_order_id="WO-001",
            requested_by="worker",
            reason="test",
        )
        r = repr(req)
        assert "value" not in r.lower()

    def test_validation_requires_action_id(self) -> None:
        ref = _sample_ref()
        req = SecretUseRequest(
            secret_ref=ref,
            action_id="",
            work_order_id="WO-001",
            requested_by="worker",
            reason="test",
        )
        errors = validate_secret_use_request(req)
        assert any("action_id" in e for e in errors)

    def test_validation_requires_work_order(self) -> None:
        ref = _sample_ref()
        req = SecretUseRequest(
            secret_ref=ref,
            action_id="LOGIN",
            work_order_id="",
            requested_by="worker",
            reason="test",
        )
        errors = validate_secret_use_request(req)
        assert any("work_order_id" in e for e in errors)

    def test_validation_requires_requested_by(self) -> None:
        ref = _sample_ref()
        req = SecretUseRequest(
            secret_ref=ref,
            action_id="LOGIN",
            work_order_id="WO-001",
            requested_by="",
            reason="test",
        )
        errors = validate_secret_use_request(req)
        assert any("requested_by" in e for e in errors)


class TestSecretUseGrant:
    def test_repr_is_redacted(self) -> None:
        ref = _sample_ref()
        grant = SecretUseGrant(
            secret_ref=ref,
            action_id="LOGIN_GOOGLE_DRIVE",
            work_order_id="WO-001",
            approved_by="founder",
            account_scope="antonyfm@empyreanstudios.co",
        )
        r = repr(grant)
        assert "[REDACTED]" in r

    def test_to_dict_redacts_value(self) -> None:
        ref = _sample_ref()
        grant = SecretUseGrant(
            secret_ref=ref,
            action_id="LOGIN",
            work_order_id="WO-001",
            approved_by="founder",
            account_scope="antonyfm@empyreanstudios.co",
        )
        d = grant.to_dict()
        assert d["secret_value"] == "[REDACTED]"

    def test_validation_requires_approved_by(self) -> None:
        ref = _sample_ref()
        grant = SecretUseGrant(
            secret_ref=ref,
            action_id="LOGIN",
            work_order_id="WO-001",
            approved_by="",
            account_scope="antonyfm@empyreanstudios.co",
        )
        errors = validate_secret_use_grant(grant)
        assert any("approved_by" in e for e in errors)

    def test_validation_requires_account_scope(self) -> None:
        ref = _sample_ref()
        grant = SecretUseGrant(
            secret_ref=ref,
            action_id="LOGIN",
            work_order_id="WO-001",
            approved_by="founder",
            account_scope="",
        )
        errors = validate_secret_use_grant(grant)
        assert any("account_scope" in e for e in errors)


class TestSecretUseAuditEvent:
    def test_serializes_without_value(self) -> None:
        ref = _sample_ref()
        event = SecretUseAuditEvent(
            secret_ref=ref,
            action_id="LOGIN_GOOGLE_DRIVE",
            work_order_id="WO-001",
            status=SecretUseStatus.USED_SUCCESS,
            performed_by="local_pc_worker",
            detail="Login successful",
        )
        d = event.to_dict()
        assert d["secret_value"] == "[NEVER_LOGGED]"
        assert d["status"] == "used_success"

    def test_repr_does_not_include_value(self) -> None:
        ref = _sample_ref()
        event = SecretUseAuditEvent(
            secret_ref=ref,
            action_id="LOGIN",
            work_order_id="WO-001",
            status=SecretUseStatus.DENIED,
            performed_by="worker",
        )
        r = repr(event)
        assert "value" not in r.lower()
