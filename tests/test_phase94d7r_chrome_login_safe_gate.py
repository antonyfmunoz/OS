"""Tests for Phase 94D.7R — Chrome Login-Safe Account Gate."""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from eos_ai.substrate.approved_action_executor import (
    BLOCKED_ACTIONS,
    WO_001_ACCOUNT,
    WO_001_ID,
    WO_001_PREFERRED_BACKEND,
    build_login_required_gate,
    build_next_gate_request,
    get_preferred_backend,
    is_action_blocked,
)


class TestLoginRequiredGate:
    def test_login_required_blocks_further_automation(self) -> None:
        gate = build_login_required_gate(WO_001_ID)
        assert gate["payload"]["action"] == "LOGIN_REQUIRED_MANUAL_INTERVENTION"
        assert gate["payload"]["blocked_until_approved"] is True

    def test_login_required_does_not_capture_credentials(self) -> None:
        gate = build_login_required_gate(WO_001_ID)
        desc = gate["payload"]["description"]
        assert "NOT type" in desc or "will NOT" in desc.upper() or "NOT" in desc
        assert "capture" in desc.lower() or "store" in desc.lower()

    def test_login_required_includes_possible_states(self) -> None:
        gate = build_login_required_gate(WO_001_ID)
        states = gate["payload"]["possible_states"]
        assert "LOGIN_REQUIRED_MANUAL_INTERVENTION" in states
        assert "WRONG_ACCOUNT_PAUSE" in states
        assert "CORRECT_ACCOUNT_CONFIRMED" in states


class TestWrongAccountGate:
    def test_wrong_account_pause_blocks_switching(self) -> None:
        assert is_action_blocked("SWITCH_ACCOUNT")

    def test_account_switching_requires_separate_approval(self) -> None:
        assert "SWITCH_ACCOUNT" in BLOCKED_ACTIONS


class TestCorrectAccountGate:
    def test_correct_account_routes_to_discovery_approval(self) -> None:
        gate = build_next_gate_request(
            work_order_id=WO_001_ID,
            gate_action="VERIFY_ACTIVE_GOOGLE_ACCOUNT",
            description="Check account",
            possible_states=[
                "DRIVE_OPEN_ACCOUNT_VISIBLE",
                "LOGIN_REQUIRED_MANUAL_INTERVENTION",
                "WRONG_ACCOUNT_PAUSE",
                "CORRECT_ACCOUNT_CONFIRMED",
                "UNKNOWN_VISUAL_STATE",
            ],
        )
        assert gate["payload"]["blocked_until_approved"] is True
        assert "CORRECT_ACCOUNT_CONFIRMED" in gate["payload"]["possible_states"]

    def test_gate_requires_human_visual_confirmation(self) -> None:
        gate = build_next_gate_request(
            work_order_id=WO_001_ID,
            gate_action="VERIFY_ACTIVE_GOOGLE_ACCOUNT",
            description="Check account",
        )
        assert gate["payload"]["backend"] == "HUMAN_VISUAL_CONFIRMATION"


class TestCredentialSafety:
    def test_capture_credentials_blocked(self) -> None:
        assert is_action_blocked("CAPTURE_CREDENTIALS")

    def test_screenshot_blocked(self) -> None:
        assert is_action_blocked("SCREENSHOT")


class TestBackendPreference:
    def test_preferred_backend_is_chrome(self) -> None:
        assert WO_001_PREFERRED_BACKEND == "VISIBLE_CHROME_LAUNCH"

    def test_open_google_drive_maps_to_chrome(self) -> None:
        backend = get_preferred_backend("OPEN_GOOGLE_DRIVE")
        assert backend == "VISIBLE_CHROME_LAUNCH"
