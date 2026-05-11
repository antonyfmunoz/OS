"""Tests for Phase 94D.5 local worker relay packets."""

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

import json

import pytest

from runtime.substrate.computer_use_backend_contracts import ComputerUseBackend
from runtime.substrate.local_worker_relay_packets import (
    WO_001_ACCOUNT,
    WO_001_ID,
    WorkerRelayPacket,
    build_wo_001_relay_packet,
    validate_relay_packet,
)
from runtime.substrate.worker_node_contracts import WorkerMode


class TestWO001Packet:
    def test_includes_auto_mode(self):
        packet = build_wo_001_relay_packet()
        assert packet.worker_mode == WorkerMode.AUTO.value

    def test_disables_local_manual_approval(self):
        packet = build_wo_001_relay_packet()
        assert packet.local_manual_approval_enabled is False

    def test_requires_advisor_approval_for_drive(self):
        packet = build_wo_001_relay_packet()
        assert packet.approval_routing == "advisor_relay"
        assert "OPEN_GOOGLE_DRIVE" in packet.first_approval_action
        assert packet.first_approval_prompt != ""

    def test_blocks_gmail(self):
        packet = build_wo_001_relay_packet()
        assert "gmail" in packet.blocked_targets

    def test_blocks_account_switching(self):
        packet = build_wo_001_relay_packet()
        assert "account_switching" in packet.blocked_targets

    def test_blocks_edit_delete_move(self):
        packet = build_wo_001_relay_packet()
        assert "edit_documents" in packet.blocked_actions
        assert "delete_files" in packet.blocked_actions
        assert "change_permissions" in packet.blocked_actions

    def test_blocks_credentials(self):
        packet = build_wo_001_relay_packet()
        assert "capture_credentials" in packet.blocked_actions

    def test_disables_playwright(self):
        packet = build_wo_001_relay_packet()
        assert packet.playwright_enabled is False

    def test_requires_gui_healthcheck(self):
        packet = build_wo_001_relay_packet()
        assert packet.require_gui_healthcheck is True

    def test_serializes(self):
        packet = build_wo_001_relay_packet()
        json_str = packet.to_json()
        restored = WorkerRelayPacket.from_json(json_str)
        assert restored.work_order_id == WO_001_ID
        assert restored.target_account == WO_001_ACCOUNT
        assert restored.worker_mode == WorkerMode.AUTO.value


class TestPacketValidation:
    def test_valid_wo_001_packet(self):
        packet = build_wo_001_relay_packet()
        errors = validate_relay_packet(packet)
        assert errors == [], f"Unexpected errors: {errors}"

    def test_rejects_manual_mode(self):
        packet = build_wo_001_relay_packet()
        packet.worker_mode = "manual_fallback"
        errors = validate_relay_packet(packet)
        assert any("AUTO" in e for e in errors)

    def test_rejects_local_approval_routing(self):
        packet = build_wo_001_relay_packet()
        packet.approval_routing = "local_terminal"
        errors = validate_relay_packet(packet)
        assert any("advisor_relay" in e for e in errors)

    def test_rejects_playwright_enabled(self):
        packet = build_wo_001_relay_packet()
        packet.playwright_enabled = True
        errors = validate_relay_packet(packet)
        assert any("Playwright" in e for e in errors)

    def test_rejects_missing_work_order_id(self):
        packet = build_wo_001_relay_packet()
        packet.work_order_id = ""
        errors = validate_relay_packet(packet)
        assert any("Work order ID" in e for e in errors)

    def test_rejects_missing_account(self):
        packet = build_wo_001_relay_packet()
        packet.target_account = ""
        errors = validate_relay_packet(packet)
        assert any("Target account" in e for e in errors)
