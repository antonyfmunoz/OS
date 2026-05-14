"""Tests for Phase 94D.7 — Approved Action Executor."""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from runtime.substrate.approved_action_executor import (
    BLOCKED_ACTIONS,
    SUPPORTED_ACTIONS,
    WO_001_ACCOUNT,
    WO_001_ID,
    build_action_executed_result,
    build_next_gate_request,
    execute_approved_action,
    extract_approved_action,
    extract_decision,
    is_action_blocked,
    is_action_supported,
    normalize_decision,
    validate_approval_for_action,
)


def _approval_response(
    decision: str = "APPROVE",
    action: str = "",
    wo_id: str = WO_001_ID,
) -> dict:
    resp: dict = {
        "work_order_id": wo_id,
        "payload": {"decision": decision},
    }
    if action:
        resp["payload"]["approved_action"] = action
    return resp


class TestNormalizeDecision:
    def test_approve(self) -> None:
        assert normalize_decision("APPROVE") == "APPROVE"

    def test_approved_normalizes(self) -> None:
        assert normalize_decision("APPROVED") == "APPROVE"

    def test_deny(self) -> None:
        assert normalize_decision("DENY") == "DENY"

    def test_case_insensitive(self) -> None:
        assert normalize_decision("approved") == "APPROVE"


class TestExtractDecision:
    def test_from_payload(self) -> None:
        resp = {"payload": {"decision": "APPROVE"}}
        assert extract_decision(resp) == "APPROVE"

    def test_from_top_level(self) -> None:
        resp = {"decision": "APPROVED"}
        assert extract_decision(resp) == "APPROVE"

    def test_payload_takes_priority(self) -> None:
        resp = {"decision": "DENY", "payload": {"decision": "APPROVE"}}
        assert extract_decision(resp) == "APPROVE"


class TestExtractApprovedAction:
    def test_from_payload(self) -> None:
        resp = {"payload": {"approved_action": "OPEN_GOOGLE_DRIVE"}}
        assert extract_approved_action(resp) == "OPEN_GOOGLE_DRIVE"

    def test_from_top_level(self) -> None:
        resp = {"approved_action": "OPEN_GOOGLE_DRIVE"}
        assert extract_approved_action(resp) == "OPEN_GOOGLE_DRIVE"

    def test_empty_when_missing(self) -> None:
        resp = {"payload": {}}
        assert extract_approved_action(resp) == ""


class TestValidateApproval:
    def test_approved_open_google_drive_validates(self) -> None:
        resp = _approval_response("APPROVE", "OPEN_GOOGLE_DRIVE")
        errors = validate_approval_for_action(resp, "OPEN_GOOGLE_DRIVE")
        assert errors == []

    def test_approved_no_explicit_action_validates(self) -> None:
        resp = _approval_response("APPROVE")
        errors = validate_approval_for_action(resp, "OPEN_GOOGLE_DRIVE")
        assert errors == []

    def test_denied_blocks(self) -> None:
        resp = _approval_response("DENY")
        errors = validate_approval_for_action(resp, "OPEN_GOOGLE_DRIVE")
        assert any("not APPROVE" in e for e in errors)

    def test_unapproved_action_blocks(self) -> None:
        resp = _approval_response("APPROVE", "OPEN_GOOGLE_DRIVE")
        errors = validate_approval_for_action(resp, "OPEN_DOCUMENT")
        assert any("not supported" in e.lower() for e in errors)

    def test_gmail_action_blocks(self) -> None:
        resp = _approval_response("APPROVE", "OPEN_GMAIL")
        errors = validate_approval_for_action(resp, "OPEN_GMAIL")
        assert any("blocked" in e.lower() for e in errors)

    def test_export_download_blocks(self) -> None:
        resp = _approval_response("APPROVE", "EXPORT_DOCUMENT")
        errors = validate_approval_for_action(resp, "EXPORT_DOCUMENT")
        assert any("blocked" in e.lower() for e in errors)

    def test_edit_delete_move_blocks(self) -> None:
        for action in ("EDIT_DOCUMENT", "DELETE_FILE", "MOVE_FILE"):
            resp = _approval_response("APPROVE", action)
            errors = validate_approval_for_action(resp, action)
            assert any("blocked" in e.lower() for e in errors), f"{action} should be blocked"

    def test_approval_permits_only_one_named_action(self) -> None:
        resp = _approval_response("APPROVE", "OPEN_GOOGLE_DRIVE")
        errors = validate_approval_for_action(resp, "SWITCH_ACCOUNT")
        assert len(errors) > 0

    def test_wrong_work_order_id(self) -> None:
        resp = _approval_response(wo_id="WRONG-WO")
        errors = validate_approval_for_action(resp, "OPEN_GOOGLE_DRIVE")
        assert any("work_order_id" in e for e in errors)


class TestBlockedAndSupported:
    def test_gmail_blocked(self) -> None:
        assert is_action_blocked("OPEN_GMAIL")

    def test_switch_account_blocked(self) -> None:
        assert is_action_blocked("SWITCH_ACCOUNT")

    def test_capture_credentials_blocked(self) -> None:
        assert is_action_blocked("CAPTURE_CREDENTIALS")

    def test_playwright_blocked(self) -> None:
        assert is_action_blocked("RUN_PLAYWRIGHT")

    def test_open_drive_supported(self) -> None:
        assert is_action_supported("OPEN_GOOGLE_DRIVE")

    def test_open_document_not_supported(self) -> None:
        assert not is_action_supported("OPEN_DOCUMENT")


class TestBuildResults:
    def test_action_result_serializes(self) -> None:
        result = build_action_executed_result(
            work_order_id=WO_001_ID,
            action="OPEN_GOOGLE_DRIVE",
            backend="VISIBLE_BROWSER_LAUNCH",
            success=True,
            detail="Browser opened",
        )
        assert result["message_type"] == "ACTION_EXECUTED"
        assert result["payload"]["action"] == "OPEN_GOOGLE_DRIVE"
        assert result["payload"]["success"] is True
        assert result["payload"]["backend"] == "VISIBLE_BROWSER_LAUNCH"

    def test_next_gate_request(self) -> None:
        gate = build_next_gate_request(
            work_order_id=WO_001_ID,
            gate_action="VERIFY_ACTIVE_GOOGLE_ACCOUNT",
            description="Check account",
        )
        assert gate["message_type"] == "APPROVAL_NEEDED"
        assert gate["payload"]["action"] == "VERIFY_ACTIVE_GOOGLE_ACCOUNT"
        assert gate["payload"]["blocked_until_approved"] is True


class TestExecuteApprovedAction:
    def test_executes_with_valid_approval(self) -> None:
        resp = _approval_response("APPROVE", "OPEN_GOOGLE_DRIVE")

        def mock_executor():
            return {"success": True, "detail": "mock launch", "backend": "VISIBLE_BROWSER_LAUNCH"}

        result = execute_approved_action(resp, "OPEN_GOOGLE_DRIVE", executor_fn=mock_executor)
        assert result["validated"] is True
        assert result["executed"] is True
        assert result["success"] is True
        assert len(result["messages_to_write"]) == 2
        assert result["next_gate"] == "VERIFY_ACTIVE_GOOGLE_ACCOUNT"

    def test_rejects_denied_approval(self) -> None:
        resp = _approval_response("DENY")
        result = execute_approved_action(resp, "OPEN_GOOGLE_DRIVE", executor_fn=lambda: {})
        assert result["validated"] is False
        assert result["error"] is not None

    def test_rejects_blocked_action(self) -> None:
        resp = _approval_response("APPROVE", "OPEN_GMAIL")
        result = execute_approved_action(resp, "OPEN_GMAIL", executor_fn=lambda: {})
        assert result["validated"] is False

    def test_no_executor_fails(self) -> None:
        resp = _approval_response("APPROVE")
        result = execute_approved_action(resp, "OPEN_GOOGLE_DRIVE", executor_fn=None)
        assert result["executed"] is False
        assert "No executor" in result["error"]

    def test_executor_exception_handled(self) -> None:
        resp = _approval_response("APPROVE")

        def bad_executor():
            raise RuntimeError("boom")

        result = execute_approved_action(resp, "OPEN_GOOGLE_DRIVE", executor_fn=bad_executor)
        assert result["executed"] is True
        assert result["success"] is False
        assert "boom" in result["error"]
