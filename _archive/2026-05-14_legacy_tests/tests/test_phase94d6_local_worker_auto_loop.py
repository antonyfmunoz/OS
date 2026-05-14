"""Tests for Phase 94D.6 — Local Worker Auto-Loop."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from runtime.substrate.local_worker_auto_loop import (
    WO_001_ACCOUNT,
    WO_001_ID,
    build_backend_health_status,
    build_claimed_status,
    build_first_gate_approval_request,
    build_preflight_status,
    load_worker_packet,
    run_auto_loop,
    run_safe_preflight,
    scan_inbox_for_response,
    validate_wo_001_packet,
    worker_should_stop,
    worker_should_wait_for_advisor,
    write_outbox_message,
)


def _valid_packet() -> dict:
    return {
        "work_order_id": WO_001_ID,
        "target_account": WO_001_ACCOUNT,
        "worker_mode": "auto",
        "playwright_enabled": False,
        "approval_routing": "advisor_relay",
        "preferred_backend": "GUI_COMPUTER_USE",
        "require_gui_healthcheck": True,
        "source_class": "Google Drive / Google Docs",
        "packet_id": "test-packet-001",
    }


class TestLoadWorkerPacket:
    def test_loads_valid_json(self, tmp_path: Path) -> None:
        pkt = _valid_packet()
        f = tmp_path / "packet.json"
        f.write_text(json.dumps(pkt))
        loaded = load_worker_packet(f)
        assert loaded["work_order_id"] == WO_001_ID

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_worker_packet(tmp_path / "nonexistent.json")


class TestValidateWo001Packet:
    def test_valid_packet_no_errors(self) -> None:
        errors = validate_wo_001_packet(_valid_packet())
        assert errors == []

    def test_wrong_work_order_id(self) -> None:
        pkt = _valid_packet()
        pkt["work_order_id"] = "WRONG"
        errors = validate_wo_001_packet(pkt)
        assert any("work_order_id" in e for e in errors)

    def test_playwright_enabled_rejected(self) -> None:
        pkt = _valid_packet()
        pkt["playwright_enabled"] = True
        errors = validate_wo_001_packet(pkt)
        assert any("Playwright" in e for e in errors)

    def test_wrong_approval_routing(self) -> None:
        pkt = _valid_packet()
        pkt["approval_routing"] = "local_manual"
        errors = validate_wo_001_packet(pkt)
        assert any(
            "approval routing" in e.lower() or "approval_routing" in e.lower() for e in errors
        )


class TestBuildMessages:
    def test_claimed_status_type(self) -> None:
        msg = build_claimed_status(_valid_packet())
        assert msg["message_type"] == "WORK_ORDER_CLAIMED"
        assert msg["work_order_id"] == WO_001_ID
        assert msg["sender"] == "node:local_pc_worker"

    def test_preflight_status_all_passed(self) -> None:
        checks = [{"name": "a", "passed": True}, {"name": "b", "passed": True}]
        msg = build_preflight_status(_valid_packet(), checks)
        assert msg["message_type"] == "PREFLIGHT_STATUS"
        assert msg["payload"]["all_passed"] is True

    def test_preflight_status_some_failed(self) -> None:
        checks = [{"name": "a", "passed": True}, {"name": "b", "passed": False}]
        msg = build_preflight_status(_valid_packet(), checks)
        assert msg["payload"]["all_passed"] is False

    def test_backend_health_available(self) -> None:
        results = {
            "visible_display": "DISPLAY",
            "pyautogui": "pyautogui OK",
            "anthropic_computer_use": "anthropic SDK OK",
            "manual_fallback": "manual fallback always available",
        }
        msg = build_backend_health_status(_valid_packet(), results)
        assert msg["message_type"] == "BACKEND_HEALTH"
        assert msg["payload"]["overall_status"] == "available"
        assert msg["payload"]["gui_available"] is True
        assert msg["payload"]["display_available"] is True

    def test_backend_health_missing(self) -> None:
        results = {
            "visible_display": "NO_DISPLAY",
            "pyautogui": "",
            "anthropic_computer_use": "",
            "manual_fallback": "manual fallback always available",
        }
        msg = build_backend_health_status(_valid_packet(), results)
        assert msg["payload"]["overall_status"] == "missing"
        assert msg["payload"]["gui_available"] is False

    def test_backend_health_partial(self) -> None:
        results = {
            "visible_display": "NO_DISPLAY",
            "pyautogui": "pyautogui OK",
            "anthropic_computer_use": "",
            "manual_fallback": "manual fallback always available",
        }
        msg = build_backend_health_status(_valid_packet(), results)
        assert msg["payload"]["overall_status"] == "partial"

    def test_first_gate_approval_request(self) -> None:
        msg = build_first_gate_approval_request(_valid_packet())
        assert msg["message_type"] == "APPROVAL_NEEDED"
        assert msg["priority"] == "HIGH"
        assert msg["requires_response"] is True
        payload = msg["payload"]
        assert payload["action"] == "OPEN_GOOGLE_DRIVE"
        assert payload["target"] == WO_001_ACCOUNT
        assert payload["risk_level"] == "MEDIUM"
        assert payload["backend"] == "GUI_COMPUTER_USE"
        assert payload["blocked_until_approved"] is True


class TestSafePreflight:
    def test_all_pass_on_valid_packet(self) -> None:
        checks = run_safe_preflight(_valid_packet())
        assert all(c["passed"] for c in checks), [c for c in checks if not c["passed"]]
        assert len(checks) == 8

    def test_fails_on_wrong_worker_mode(self) -> None:
        pkt = _valid_packet()
        pkt["worker_mode"] = "manual"
        checks = run_safe_preflight(pkt)
        worker_mode_check = next(c for c in checks if c["name"] == "worker_mode")
        assert worker_mode_check["passed"] is False


class TestOutboxInbox:
    def test_write_outbox_message(self, tmp_path: Path) -> None:
        with patch("runtime.substrate.local_worker_auto_loop.OUTBOX_DIR", tmp_path):
            msg = {"test": True}
            path = write_outbox_message("test.json", msg)
            assert path.exists()
            loaded = json.loads(path.read_text())
            assert loaded["test"] is True

    def test_scan_inbox_finds_match(self, tmp_path: Path) -> None:
        with patch("runtime.substrate.local_worker_auto_loop.INBOX_DIR", tmp_path):
            resp = {
                "work_order_id": WO_001_ID,
                "payload": {"decision": "APPROVE"},
            }
            (tmp_path / "response.json").write_text(json.dumps(resp))
            found = scan_inbox_for_response(WO_001_ID)
            assert found is not None
            assert found["payload"]["decision"] == "APPROVE"

    def test_scan_inbox_no_match(self, tmp_path: Path) -> None:
        with patch("runtime.substrate.local_worker_auto_loop.INBOX_DIR", tmp_path):
            resp = {
                "work_order_id": "OTHER-WO",
                "payload": {"decision": "APPROVE"},
            }
            (tmp_path / "response.json").write_text(json.dumps(resp))
            found = scan_inbox_for_response(WO_001_ID)
            assert found is None


class TestWorkerDecisions:
    def test_should_wait_when_no_response(self) -> None:
        assert worker_should_wait_for_advisor(None) is True

    def test_should_wait_when_empty_decision(self) -> None:
        assert worker_should_wait_for_advisor({"payload": {"decision": ""}}) is True

    def test_should_not_wait_when_approved(self) -> None:
        assert worker_should_wait_for_advisor({"payload": {"decision": "APPROVE"}}) is False

    def test_should_stop_on_deny(self) -> None:
        assert worker_should_stop({"payload": {"decision": "DENY"}}) is True

    def test_should_stop_on_stop(self) -> None:
        assert worker_should_stop({"payload": {"decision": "STOP"}}) is True

    def test_should_not_stop_on_approve(self) -> None:
        assert worker_should_stop({"payload": {"decision": "APPROVE"}}) is False

    def test_should_not_stop_on_none(self) -> None:
        assert worker_should_stop(None) is False


class TestRunAutoLoop:
    def test_loop_fails_on_missing_packet(self, tmp_path: Path) -> None:
        result = run_auto_loop(tmp_path / "missing.json")
        assert result["status"] == "failed"
        assert result["packet_loaded"] is False

    def test_loop_fails_on_invalid_packet(self, tmp_path: Path) -> None:
        pkt = _valid_packet()
        pkt["work_order_id"] = "WRONG"
        f = tmp_path / "bad.json"
        f.write_text(json.dumps(pkt))
        with patch("runtime.substrate.local_worker_auto_loop.OUTBOX_DIR", tmp_path / "out"):
            with patch("runtime.substrate.local_worker_auto_loop.INBOX_DIR", tmp_path / "in"):
                result = run_auto_loop(f)
        assert result["status"] == "failed"
        assert result["validation_passed"] is False

    def test_loop_stops_on_deny(self, tmp_path: Path) -> None:
        pkt = _valid_packet()
        f = tmp_path / "packet.json"
        f.write_text(json.dumps(pkt))
        inbox = tmp_path / "inbox"
        inbox.mkdir()
        outbox = tmp_path / "outbox"
        outbox.mkdir()

        deny_response = {
            "work_order_id": WO_001_ID,
            "payload": {"decision": "DENY"},
        }
        (inbox / "deny.json").write_text(json.dumps(deny_response))

        with (
            patch("runtime.substrate.local_worker_auto_loop.OUTBOX_DIR", outbox),
            patch("runtime.substrate.local_worker_auto_loop.INBOX_DIR", inbox),
            patch(
                "runtime.substrate.local_worker_auto_loop.run_gui_backend_healthcheck",
                return_value={
                    "visible_display": "DISPLAY",
                    "pyautogui": "pyautogui OK",
                    "anthropic_computer_use": "",
                    "manual_fallback": "ok",
                },
            ),
        ):
            result = run_auto_loop(f)
        assert result["status"] == "stopped"
        assert result["approval_request_sent"] is True

    def test_loop_executes_approved_action(self, tmp_path: Path) -> None:
        pkt = _valid_packet()
        f = tmp_path / "packet.json"
        f.write_text(json.dumps(pkt))
        inbox = tmp_path / "inbox"
        inbox.mkdir()
        outbox = tmp_path / "outbox"
        outbox.mkdir()

        approve_response = {
            "work_order_id": WO_001_ID,
            "payload": {"decision": "APPROVE"},
        }
        (inbox / "approve.json").write_text(json.dumps(approve_response))

        mock_action_result = {
            "success": True,
            "backend": "VISIBLE_BROWSER_LAUNCH",
            "detail": "mock browser launch",
            "next_gate": "VERIFY_ACTIVE_GOOGLE_ACCOUNT",
            "error": None,
        }

        with (
            patch("runtime.substrate.local_worker_auto_loop.OUTBOX_DIR", outbox),
            patch("runtime.substrate.local_worker_auto_loop.INBOX_DIR", inbox),
            patch(
                "runtime.substrate.local_worker_auto_loop.run_gui_backend_healthcheck",
                return_value={
                    "visible_display": "DISPLAY",
                    "pyautogui": "pyautogui OK",
                    "anthropic_computer_use": "",
                    "manual_fallback": "ok",
                },
            ),
            patch(
                "runtime.substrate.local_worker_auto_loop._execute_approved_action",
                return_value=mock_action_result,
            ),
        ):
            result = run_auto_loop(f)
        assert result["status"] == "action_executed"
        assert result["claimed"] is True
        assert result["preflight_passed"] is True
        assert result["approval_request_sent"] is True
        assert result["action_result"]["success"] is True
        outbox_files = list(outbox.glob("*.json"))
        assert len(outbox_files) >= 4
