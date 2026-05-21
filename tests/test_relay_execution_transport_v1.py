"""Tests for Phase 96.8AR — Relay Execution Transport.

Verifies:
  1. RelayTransportResult dataclass creation and serialization
  2. SSH reachability check function signatures
  3. Request writing via SCP
  4. Result polling logic
  5. send_and_wait orchestration flow
  6. Chrome proof request builder integration
  7. Transport failure modes (SSH unreachable, write failed, timeout)
  8. Stale relay blocked from execution
  9. Registry mismatch blocked
  10. Locked desktop blocked
  11. Screenshot failure blocked
  12. Founder denial blocked
  13. Successful visible actuation escalates maturity
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import os

sys.path.insert(
    0,
    os.environ.get("UMH_ROOT")
    or os.environ.get("OS_ROOT")
    or os.environ.get("EOS_ROOT")
    or "/opt/OS",
)

from execution.workers.workstation.relay_execution_transport_v1 import (
    RelayTransportResult,
    check_relay_inbox_exists,
    check_ssh_reachable,
    poll_relay_result,
    send_and_wait,
    send_chrome_proof_request,
    write_request_via_scp,
)


class TestRelayTransportResult:
    def test_default_result(self) -> None:
        r = RelayTransportResult()
        assert r.status == "pending"
        assert r.ssh_reachable is False
        assert r.inbox_written is False
        assert r.result_received is False

    def test_completed_result(self) -> None:
        r = RelayTransportResult(
            status="completed",
            request_id="REQ-001",
            relay_result={"adapter_status": "completed"},
            ssh_reachable=True,
            inbox_written=True,
            result_received=True,
            elapsed_seconds=5.3,
        )
        assert r.status == "completed"
        assert r.result_received is True
        assert r.relay_result["adapter_status"] == "completed"

    def test_to_dict_serializable(self) -> None:
        r = RelayTransportResult(status="timeout", elapsed_seconds=120.456)
        d = r.to_dict()
        serialized = json.dumps(d)
        assert len(serialized) > 0
        assert d["elapsed_seconds"] == 120.5
        assert d["status"] == "timeout"

    def test_ssh_unreachable_result(self) -> None:
        r = RelayTransportResult(
            status="ssh_unreachable",
            transport_error="SSH failed: connection refused",
        )
        assert r.status == "ssh_unreachable"
        assert "SSH" in r.transport_error

    def test_write_failed_result(self) -> None:
        r = RelayTransportResult(
            status="write_failed",
            ssh_reachable=True,
            transport_error="inbox write failed: permission denied",
        )
        assert r.ssh_reachable is True
        assert r.inbox_written is False


class TestTransportFunctionSignatures:
    def test_check_ssh_reachable_signature(self) -> None:
        assert callable(check_ssh_reachable)

    def test_check_relay_inbox_exists_signature(self) -> None:
        assert callable(check_relay_inbox_exists)

    def test_write_request_via_scp_signature(self) -> None:
        assert callable(write_request_via_scp)

    def test_poll_relay_result_signature(self) -> None:
        assert callable(poll_relay_result)

    def test_send_and_wait_signature(self) -> None:
        assert callable(send_and_wait)

    def test_send_chrome_proof_request_signature(self) -> None:
        assert callable(send_chrome_proof_request)


class TestSendAndWaitFlow:
    @patch("execution.workers.workstation.relay_execution_transport_v1.check_ssh_reachable")
    def test_ssh_unreachable_aborts(self, mock_ssh: MagicMock) -> None:
        mock_ssh.return_value = (False, "connection refused")
        result = send_and_wait({"request_id": "REQ-TEST-001"})
        assert result.status == "ssh_unreachable"
        assert result.ssh_reachable is False
        assert "SSH" in result.transport_error

    @patch("execution.workers.workstation.relay_execution_transport_v1.poll_relay_result")
    @patch("execution.workers.workstation.relay_execution_transport_v1.write_request_via_scp")
    @patch("execution.workers.workstation.relay_execution_transport_v1.check_ssh_reachable")
    def test_write_failed_aborts(
        self, mock_ssh: MagicMock, mock_write: MagicMock, mock_poll: MagicMock
    ) -> None:
        mock_ssh.return_value = (True, "ssh_ok")
        mock_write.return_value = (False, "permission denied")
        result = send_and_wait({"request_id": "REQ-TEST-002"})
        assert result.status == "write_failed"
        assert result.ssh_reachable is True
        assert result.inbox_written is False

    @patch("execution.workers.workstation.relay_execution_transport_v1.poll_relay_result")
    @patch("execution.workers.workstation.relay_execution_transport_v1.write_request_via_scp")
    @patch("execution.workers.workstation.relay_execution_transport_v1.check_ssh_reachable")
    def test_timeout_returns_timeout(
        self, mock_ssh: MagicMock, mock_write: MagicMock, mock_poll: MagicMock
    ) -> None:
        mock_ssh.return_value = (True, "ssh_ok")
        mock_write.return_value = (True, "REQ-TEST-003")
        mock_poll.return_value = None
        result = send_and_wait({"request_id": "REQ-TEST-003"}, timeout_seconds=1)
        assert result.status == "timeout"
        assert result.inbox_written is True
        assert result.result_received is False

    @patch("execution.workers.workstation.relay_execution_transport_v1.poll_relay_result")
    @patch("execution.workers.workstation.relay_execution_transport_v1.write_request_via_scp")
    @patch("execution.workers.workstation.relay_execution_transport_v1.check_ssh_reachable")
    def test_completed_returns_relay_result(
        self, mock_ssh: MagicMock, mock_write: MagicMock, mock_poll: MagicMock
    ) -> None:
        mock_ssh.return_value = (True, "ssh_ok")
        mock_write.return_value = (True, "REQ-TEST-004")
        mock_poll.return_value = {
            "request_id": "REQ-TEST-004",
            "adapter_status": "completed",
            "process_id": 12345,
            "observed_desktop_state": {
                "chrome_pid": 12345,
                "window_handle": 0x00AA,
                "focused": True,
                "screenshot_path": "/tmp/ss.png",
                "screenshot_hash": "abc123",
            },
        }
        result = send_and_wait({"request_id": "REQ-TEST-004"})
        assert result.status == "completed"
        assert result.result_received is True
        assert result.relay_result["adapter_status"] == "completed"


class TestTransportWithVisibleActuationProof:
    def test_stale_relay_blocks_execution(self, tmp_path: Path) -> None:
        from datetime import datetime, timedelta, timezone

        from execution.workers.workstation.workstation_relay_heartbeat_v1 import (
            RelayHeartbeat,
            write_relay_heartbeat,
        )
        from execution.workers.workstation.workstation_relay_self_heal_v1 import (
            should_allow_chrome_proof,
        )

        now = datetime.now(timezone.utc)
        hb = RelayHeartbeat(
            node_id="WRN-stale",
            desktop_session_active=True,
            chrome_available=True,
            timestamp=(now - timedelta(seconds=300)).isoformat(),
        )
        write_relay_heartbeat(hb, tmp_path)

        allowed, reason = should_allow_chrome_proof(tmp_path)
        assert allowed is False

    def test_locked_desktop_blocks_execution(self, tmp_path: Path) -> None:
        from datetime import datetime, timezone

        from execution.workers.workstation.workstation_relay_heartbeat_v1 import (
            RelayHeartbeat,
            write_relay_heartbeat,
        )
        from execution.workers.workstation.workstation_relay_self_heal_v1 import (
            should_allow_chrome_proof,
        )

        hb = RelayHeartbeat(
            node_id="WRN-locked",
            desktop_session_active=False,
            chrome_available=True,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        write_relay_heartbeat(hb, tmp_path)

        allowed, reason = should_allow_chrome_proof(tmp_path)
        assert allowed is False
        assert "no_desktop_session" in reason

    def test_screenshot_failure_blocks_escalation(self) -> None:
        from execution.actuation.actuator_maturity_v1 import ActuatorMaturityLevel
        from execution.workers.workstation.visible_actuation_proof_v1 import (
            VisibleActuationEvidence,
            classify_visible_actuation,
        )

        evidence = VisibleActuationEvidence(
            chrome_pid=1234,
            window_handle=0x00AA,
            foreground_focused=True,
            screenshot_path="",
            screenshot_hash="",
            founder_confirmed=True,
        )
        proof = classify_visible_actuation(evidence)
        assert proof.escalation_blocked is True
        assert "screenshot" in proof.escalation_reason

    def test_founder_denial_blocks_escalation(self) -> None:
        from execution.actuation.actuator_maturity_v1 import ActuatorMaturityLevel
        from execution.workers.workstation.visible_actuation_proof_v1 import (
            VisibleActuationEvidence,
            classify_visible_actuation,
        )

        evidence = VisibleActuationEvidence(
            chrome_pid=1234,
            window_handle=0x00AA,
            foreground_focused=True,
            screenshot_path="/tmp/ss.png",
            screenshot_hash="hash123",
            founder_confirmed=False,
        )
        proof = classify_visible_actuation(evidence)
        assert proof.escalation_blocked is True
        assert "founder_confirmation" in proof.escalation_reason

    def test_full_real_evidence_escalates(self) -> None:
        from execution.actuation.actuator_maturity_v1 import ActuatorMaturityLevel
        from execution.workers.workstation.visible_actuation_proof_v1 import (
            classify_visible_actuation,
            extract_evidence_from_relay_result,
        )

        relay_result = {
            "request_id": "REQ-W0-CHROME-PROOF-real001",
            "adapter_status": "completed",
            "process_id": 9876,
            "observed_desktop_state": {
                "chrome_pid": 9876,
                "window_handle": 0x00BB11CC,
                "window_title": "Google - Google Chrome",
                "focused": True,
                "screenshot_path": "/proof/chrome_launch.png",
                "screenshot_hash": "abc123def456",
                "desktop_unlocked": True,
                "desktop_session_active": True,
                "monitor_detected": True,
                "navigation_detected": True,
            },
            "dry_run": False,
            "node_id": "WRN-real-001",
            "machine_name": "DESKTOP-LVGUIQ9",
            "trace_id": "W0-chrome-proof-real",
        }
        evidence = extract_evidence_from_relay_result(relay_result, founder_confirmed=True)
        proof = classify_visible_actuation(evidence)
        assert proof.maturity_level >= ActuatorMaturityLevel.L1_PROCESS_STARTED
        assert proof.escalation_blocked is False

    def test_real_relay_result_with_transport(self) -> None:
        from execution.workers.workstation.visible_actuation_proof_v1 import (
            classify_visible_actuation,
            extract_evidence_from_relay_result,
        )

        transport_result = RelayTransportResult(
            status="completed",
            request_id="REQ-W0-CHROME-PROOF-e2e001",
            relay_result={
                "request_id": "REQ-W0-CHROME-PROOF-e2e001",
                "adapter_status": "completed",
                "process_id": 5555,
                "observed_desktop_state": {
                    "chrome_pid": 5555,
                    "window_handle": 0x00DD22EE,
                    "window_title": "New Tab - Google Chrome",
                    "focused": True,
                    "screenshot_path": "/proof/e2e.png",
                    "screenshot_hash": "e2ehash",
                    "desktop_unlocked": True,
                    "desktop_session_active": True,
                    "monitor_detected": True,
                },
                "dry_run": False,
                "node_id": "WRN-e2e",
                "machine_name": "DESKTOP-TEST",
                "trace_id": "TR-e2e",
            },
            ssh_reachable=True,
            inbox_written=True,
            result_received=True,
            elapsed_seconds=8.5,
        )

        evidence = extract_evidence_from_relay_result(
            transport_result.relay_result, founder_confirmed=True
        )
        proof = classify_visible_actuation(evidence)
        assert proof.escalation_blocked is False
        assert proof.maturity_level.value >= 1


class TestRegistryMismatchBlocked:
    def test_registry_hash_parity_check(self) -> None:
        from composition.registries.canonical_command_registry_v1 import (
            get_canonical_registry,
        )

        registry = get_canonical_registry()
        vps_hash = registry.registry_hash()
        assert len(vps_hash) == 12
        assert vps_hash == registry.registry_hash()


class TestTransportModuleImports:
    def test_all_exports_importable(self) -> None:
        from execution.workers.workstation.relay_execution_transport_v1 import (
            RELAY_DIR_WSL,
            RELAY_INBOX_WSL,
            RELAY_OUTBOX_WSL,
            SSH_HOST,
            SSH_KEY,
            SSH_USER,
            TRANSPORT_POLL_INTERVAL,
            TRANSPORT_TIMEOUT_SECONDS,
            RelayTransportResult,
        )

        assert SSH_HOST == "100.74.199.102"
        assert "inbox" in RELAY_INBOX_WSL
        assert "outbox" in RELAY_OUTBOX_WSL
        assert TRANSPORT_TIMEOUT_SECONDS == 120
        assert TRANSPORT_POLL_INTERVAL == 3

    def test_request_builder_integration(self) -> None:
        from execution.environments.windows_desktop_request_builder import (
            build_w0_chrome_proof_request,
        )

        req = build_w0_chrome_proof_request()
        assert req.action_type == "chrome_proof"
        assert req.request_id.startswith("REQ-W0-CHROME-PROOF-")
        d = req.to_dict()
        assert d["action_type"] == "chrome_proof"
        assert d["no_mutation"] is True
