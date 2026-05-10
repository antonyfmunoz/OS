"""Tests for worker runtime contracts -- Phase 96.8K."""

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

import unittest

from core.runtime.worker_runtime_contracts import (
    AuthorityDomain,
    EnvironmentAuthorityDescriptor,
    EnvironmentType,
    MessageBusType,
    ProofStatus,
    RuntimeProofRecord,
    VPS_AUTHORITY,
    WINDOWS_DESKTOP_AUTHORITY,
    WSL_AUTHORITY,
    WorkerHeartbeat,
    WorkerRuntimeDescriptor,
)


class TestEnvironmentAuthority(unittest.TestCase):
    def test_vps_cannot_own_gui(self):
        self.assertFalse(VPS_AUTHORITY.can_own_gui)
        self.assertFalse(VPS_AUTHORITY.has_authority(AuthorityDomain.LOCAL_GUI))

    def test_wsl_cannot_own_gui(self):
        self.assertFalse(WSL_AUTHORITY.can_own_gui)
        self.assertFalse(WSL_AUTHORITY.has_authority(AuthorityDomain.LOCAL_GUI))

    def test_wsl_owns_local_shell(self):
        self.assertTrue(WSL_AUTHORITY.can_own_local_shell)
        self.assertTrue(WSL_AUTHORITY.has_authority(AuthorityDomain.LOCAL_SHELL))

    def test_wsl_owns_filesystem_relay(self):
        self.assertTrue(WSL_AUTHORITY.has_authority(AuthorityDomain.FILESYSTEM_RELAY))

    def test_windows_desktop_owns_gui(self):
        self.assertTrue(WINDOWS_DESKTOP_AUTHORITY.can_own_gui)
        self.assertTrue(WINDOWS_DESKTOP_AUTHORITY.has_authority(AuthorityDomain.LOCAL_GUI))

    def test_windows_desktop_owns_local_shell(self):
        self.assertTrue(WINDOWS_DESKTOP_AUTHORITY.can_own_local_shell)

    def test_vps_owns_remote_orchestration(self):
        self.assertTrue(VPS_AUTHORITY.can_own_remote_orchestration)
        self.assertTrue(VPS_AUTHORITY.has_authority(AuthorityDomain.REMOTE_ORCHESTRATION))


class TestWorkerRuntimeDescriptor(unittest.TestCase):
    def test_wsl_worker_can_handle_ping(self):
        worker = WorkerRuntimeDescriptor(
            worker_id="local_wsl_worker",
            environment_type=EnvironmentType.LOCAL_WSL,
            authority=WSL_AUTHORITY,
            capabilities=["ping", "relay_to_windows_adapter"],
            message_bus=MessageBusType.FILESYSTEM_JSON,
        )
        self.assertTrue(worker.can_handle("ping"))
        self.assertTrue(worker.can_handle("relay_to_windows_adapter"))
        self.assertFalse(worker.can_handle("open_application_url"))

    def test_windows_relay_can_handle_chrome_open(self):
        worker = WorkerRuntimeDescriptor(
            worker_id="windows_interactive_desktop_relay",
            environment_type=EnvironmentType.LOCAL_WINDOWS_DESKTOP,
            authority=WINDOWS_DESKTOP_AUTHORITY,
            capabilities=["ping", "open_application_url"],
        )
        self.assertTrue(worker.can_handle("open_application_url"))
        self.assertTrue(worker.can_handle("ping"))


class TestWorkerHeartbeat(unittest.TestCase):
    def test_heartbeat_has_timestamp(self):
        hb = WorkerHeartbeat(worker_id="test_worker")
        self.assertNotEqual(hb.timestamp, "")
        self.assertEqual(hb.status, "alive")

    def test_heartbeat_with_capabilities(self):
        hb = WorkerHeartbeat(
            worker_id="test_worker",
            capabilities_active=["ping", "open_application_url"],
        )
        self.assertEqual(len(hb.capabilities_active), 2)


class TestRuntimeProofRecord(unittest.TestCase):
    def test_completed_proof_succeeds(self):
        proof = RuntimeProofRecord(
            proof_id="PROOF-001",
            worker_id="windows_interactive_desktop_relay",
            adapter_id="windows_interactive_desktop_relay",
            action_type="open_application_url",
            proof_status=ProofStatus.COMPLETED,
            adapter_status="completed",
            request_id="REQ-001",
        )
        self.assertTrue(proof.succeeded)
        self.assertEqual(proof.adapter_status, "completed")

    def test_failed_proof_does_not_succeed(self):
        proof = RuntimeProofRecord(
            proof_id="PROOF-002",
            worker_id="windows_interactive_desktop_relay",
            adapter_id="windows_interactive_desktop_relay",
            action_type="open_application_url",
            proof_status=ProofStatus.FAILED,
            adapter_status="failed",
        )
        self.assertFalse(proof.succeeded)

    def test_proof_has_timestamp(self):
        proof = RuntimeProofRecord(
            proof_id="PROOF-003",
            worker_id="test",
            adapter_id="test",
            action_type="ping",
            proof_status=ProofStatus.COMPLETED,
        )
        self.assertNotEqual(proof.timestamp, "")

    def test_proof_with_evidence(self):
        proof = RuntimeProofRecord(
            proof_id="PROOF-004",
            worker_id="windows_interactive_desktop_relay",
            adapter_id="windows_interactive_desktop_relay",
            action_type="open_application_url",
            proof_status=ProofStatus.COMPLETED,
            adapter_status="completed",
            evidence={
                "main_window_title": "Google Drive - Google Chrome",
                "process_detected": True,
            },
        )
        self.assertIn("main_window_title", proof.evidence)
        self.assertTrue(proof.succeeded)


if __name__ == "__main__":
    unittest.main()
