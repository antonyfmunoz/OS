"""Tests for Control Plane Router v1 -- Phase 96.8N.

Tests deterministic routing, adapter resolution, capability mapping,
packet validation, proof propagation, and error handling.
Does NOT require a running daemon or live filesystem relay.
"""

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

import json
import tempfile
import time
import unittest
from pathlib import Path

from control_plane.router.router_contracts import (
    ALLOWED_ACTION_TYPES,
    CapabilityType,
    RouterStatus,
    WorkPacket,
)
from control_plane.router.control_plane_router_v1 import (
    ACTION_CAPABILITY_MAP,
    ControlPlaneRouterV1,
    load_config,
    DEFAULT_CONFIG_PATH,
)
from core.runtime.adapter_registry_contracts import (
    AdapterDescriptor,
    AdapterRegistry,
    CapabilityDescriptor,
)
from core.runtime.worker_runtime_contracts import (
    AuthorityDomain,
    MessageBusType,
    ProofStatus,
)


def _build_test_registry() -> AdapterRegistry:
    """Build a minimal registry for testing."""
    registry = AdapterRegistry()
    registry.register_adapter(
        AdapterDescriptor(
            adapter_id="windows_interactive_desktop_relay",
            adapter_type="gui_actuator",
            environment_type="local_windows_desktop",
            authority_domain=AuthorityDomain.LOCAL_GUI,
            message_bus=MessageBusType.FILESYSTEM_JSON,
            capabilities=[
                CapabilityDescriptor(
                    capability_id="ping",
                    action_type="ping",
                    requires_gui=False,
                    required_authority=AuthorityDomain.LOCAL_SHELL,
                ),
                CapabilityDescriptor(
                    capability_id="open_application_url",
                    action_type="open_application_url",
                    requires_gui=True,
                    required_authority=AuthorityDomain.LOCAL_GUI,
                ),
            ],
        )
    )
    return registry


def _build_router(tmpdir: str) -> ControlPlaneRouterV1:
    """Build a router pointed at a temp directory."""
    config = {
        "default_runtime_target": "local_worker_runtime_daemon",
        "default_timeout_seconds": 5,
        "allowed_action_types": ["ping", "open_application_url"],
        "proof_required": True,
        "work_inbox": f"{tmpdir}/inbox",
        "proof_dir": f"{tmpdir}/proofs",
    }
    return ControlPlaneRouterV1(
        registry=_build_test_registry(),
        config=config,
        base_dir=Path(tmpdir),
    )


class TestPacketValidation(unittest.TestCase):
    def test_valid_ping_packet(self):
        router = _build_router("/tmp/test-router")
        packet = WorkPacket(packet_id="PKT-001", action_type="ping")
        self.assertIsNone(router.validate_packet(packet))

    def test_valid_chrome_packet(self):
        router = _build_router("/tmp/test-router")
        packet = WorkPacket(packet_id="PKT-002", action_type="open_application_url")
        self.assertIsNone(router.validate_packet(packet))

    def test_missing_packet_id(self):
        router = _build_router("/tmp/test-router")
        packet = WorkPacket(packet_id="", action_type="ping")
        error = router.validate_packet(packet)
        self.assertIn("missing packet_id", error)

    def test_missing_action_type(self):
        router = _build_router("/tmp/test-router")
        packet = WorkPacket(packet_id="PKT-003", action_type="")
        error = router.validate_packet(packet)
        self.assertIn("missing action_type", error)

    def test_disallowed_action_type(self):
        router = _build_router("/tmp/test-router")
        packet = WorkPacket(packet_id="PKT-004", action_type="shell_exec")
        error = router.validate_packet(packet)
        self.assertIn("not allowed", error)


class TestCapabilityResolution(unittest.TestCase):
    def test_ping_resolves_to_shell(self):
        router = _build_router("/tmp/test-router")
        cap = router.resolve_capability("ping")
        self.assertIsNotNone(cap)
        self.assertEqual(cap.capability_type, CapabilityType.SHELL_EXECUTION)
        self.assertFalse(cap.requires_gui)

    def test_chrome_resolves_to_gui(self):
        router = _build_router("/tmp/test-router")
        cap = router.resolve_capability("open_application_url")
        self.assertIsNotNone(cap)
        self.assertEqual(cap.capability_type, CapabilityType.WINDOWS_GUI_EXECUTION)
        self.assertTrue(cap.requires_gui)

    def test_unknown_action_returns_none(self):
        router = _build_router("/tmp/test-router")
        cap = router.resolve_capability("delete_everything")
        self.assertIsNone(cap)


class TestAdapterResolution(unittest.TestCase):
    def test_ping_finds_adapter(self):
        router = _build_router("/tmp/test-router")
        adapter = router.resolve_adapter("ping")
        self.assertIsNotNone(adapter)
        self.assertEqual(adapter.adapter_id, "windows_interactive_desktop_relay")

    def test_chrome_finds_adapter(self):
        router = _build_router("/tmp/test-router")
        adapter = router.resolve_adapter("open_application_url")
        self.assertIsNotNone(adapter)
        self.assertEqual(adapter.adapter_id, "windows_interactive_desktop_relay")

    def test_unknown_action_no_adapter(self):
        router = _build_router("/tmp/test-router")
        adapter = router.resolve_adapter("launch_missile")
        self.assertIsNone(adapter)


class TestRuntimeResolution(unittest.TestCase):
    def test_default_runtime(self):
        router = _build_router("/tmp/test-router")
        packet = WorkPacket(packet_id="PKT-005", action_type="ping")
        self.assertEqual(router.resolve_runtime(packet), "local_worker_runtime_daemon")

    def test_explicit_runtime_override(self):
        router = _build_router("/tmp/test-router")
        packet = WorkPacket(
            packet_id="PKT-006",
            action_type="ping",
            requested_runtime="custom_runtime",
        )
        self.assertEqual(router.resolve_runtime(packet), "custom_runtime")


class TestDryRunRouting(unittest.TestCase):
    def test_ping_dry_run_routes(self):
        router = _build_router("/tmp/test-router")
        packet = WorkPacket(packet_id="PKT-DRY-001", action_type="ping")
        result = router.route_dry_run(packet)
        self.assertEqual(result.router_status, RouterStatus.ROUTED)
        self.assertEqual(result.runtime_target, "local_worker_runtime_daemon")
        self.assertEqual(result.adapter_selected, "windows_interactive_desktop_relay")
        self.assertIsNotNone(result.router_decision)
        self.assertEqual(result.router_decision.action_type, "ping")

    def test_chrome_dry_run_routes(self):
        router = _build_router("/tmp/test-router")
        packet = WorkPacket(packet_id="PKT-DRY-002", action_type="open_application_url")
        result = router.route_dry_run(packet)
        self.assertEqual(result.router_status, RouterStatus.ROUTED)
        self.assertEqual(
            result.router_decision.capability_matched,
            CapabilityType.WINDOWS_GUI_EXECUTION.value,
        )

    def test_invalid_packet_dry_run_rejected(self):
        router = _build_router("/tmp/test-router")
        packet = WorkPacket(packet_id="", action_type="ping")
        result = router.route_dry_run(packet)
        self.assertEqual(result.router_status, RouterStatus.INVALID_PACKET)
        self.assertIn("missing packet_id", result.error_message)

    def test_unknown_action_dry_run_rejected(self):
        router = _build_router("/tmp/test-router")
        packet = WorkPacket(packet_id="PKT-DRY-003", action_type="hack_something")
        result = router.route_dry_run(packet)
        self.assertEqual(result.router_status, RouterStatus.INVALID_PACKET)

    def test_no_adapter_dry_run(self):
        empty_registry = AdapterRegistry()
        config = {
            "allowed_action_types": ["ping"],
            "default_timeout_seconds": 5,
        }
        router = ControlPlaneRouterV1(registry=empty_registry, config=config)
        packet = WorkPacket(packet_id="PKT-DRY-004", action_type="ping")
        result = router.route_dry_run(packet)
        self.assertEqual(result.router_status, RouterStatus.NO_ADAPTER)


class TestFullRouteWithProof(unittest.TestCase):
    def test_route_writes_packet_and_finds_proof(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            router = _build_router(tmpdir)
            inbox = Path(tmpdir) / "inbox"
            proof_dir = Path(tmpdir) / "proofs"
            router.work_inbox = inbox
            router.proof_dir = proof_dir
            proof_dir.mkdir(parents=True, exist_ok=True)

            proof_file = proof_dir / "PROOF-test001.json"
            proof_file.write_text(
                json.dumps(
                    {
                        "proof_id": "PROOF-test001",
                        "request_id": "PKT-FULL-001",
                        "proof_status": "completed",
                        "adapter_status": "pong",
                        "worker_id": "local_wsl_worker",
                        "adapter_id": "windows_interactive_desktop_relay",
                        "action_type": "ping",
                    }
                )
            )

            packet = WorkPacket(packet_id="PKT-FULL-001", action_type="ping")
            result = router.route_work_packet(packet)

            self.assertEqual(result.router_status, RouterStatus.COMPLETED)
            self.assertIsNotNone(result.runtime_proof_reference)
            self.assertEqual(result.runtime_proof_reference.proof_id, "PROOF-test001")
            self.assertEqual(result.runtime_proof_reference.proof_status, "completed")
            self.assertEqual(result.runtime_proof_reference.adapter_status, "pong")

            written = list(inbox.glob("*.json"))
            self.assertEqual(len(written), 1)

    def test_route_timeout_when_no_proof(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {
                "default_runtime_target": "local_worker_runtime_daemon",
                "default_timeout_seconds": 1,
                "allowed_action_types": ["ping"],
                "work_inbox": f"{tmpdir}/inbox",
                "proof_dir": f"{tmpdir}/proofs",
            }
            router = ControlPlaneRouterV1(
                registry=_build_test_registry(),
                config=config,
                base_dir=Path(tmpdir),
            )
            router.work_inbox = Path(tmpdir) / "inbox"
            router.proof_dir = Path(tmpdir) / "proofs"
            Path(f"{tmpdir}/proofs").mkdir(parents=True, exist_ok=True)

            packet = WorkPacket(
                packet_id="PKT-TIMEOUT-001",
                action_type="ping",
                timeout_seconds=1,
            )
            result = router.route_work_packet(packet)
            self.assertEqual(result.router_status, RouterStatus.TIMEOUT)

    def test_route_with_failed_proof(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            router = _build_router(tmpdir)
            inbox = Path(tmpdir) / "inbox"
            proof_dir = Path(tmpdir) / "proofs"
            router.work_inbox = inbox
            router.proof_dir = proof_dir
            proof_dir.mkdir(parents=True, exist_ok=True)

            proof_file = proof_dir / "PROOF-fail001.json"
            proof_file.write_text(
                json.dumps(
                    {
                        "proof_id": "PROOF-fail001",
                        "request_id": "PKT-FAIL-001",
                        "proof_status": "failed",
                        "adapter_status": "rejected",
                        "action_type": "ping",
                    }
                )
            )

            packet = WorkPacket(packet_id="PKT-FAIL-001", action_type="ping")
            result = router.route_work_packet(packet)
            self.assertEqual(result.router_status, RouterStatus.FAILED)
            self.assertEqual(result.runtime_proof_reference.proof_status, "failed")


class TestMalformedPacketHandling(unittest.TestCase):
    def test_route_rejects_empty_packet_id(self):
        router = _build_router("/tmp/test-router")
        packet = WorkPacket(packet_id="", action_type="ping")
        result = router.route_work_packet(packet)
        self.assertEqual(result.router_status, RouterStatus.INVALID_PACKET)

    def test_route_rejects_empty_action(self):
        router = _build_router("/tmp/test-router")
        packet = WorkPacket(packet_id="PKT-BAD-001", action_type="")
        result = router.route_work_packet(packet)
        self.assertEqual(result.router_status, RouterStatus.INVALID_PACKET)


class TestDeterministicRouting(unittest.TestCase):
    def test_same_packet_same_result(self):
        router = _build_router("/tmp/test-router")
        for _ in range(5):
            packet = WorkPacket(packet_id="PKT-DET-001", action_type="ping")
            result = router.route_dry_run(packet)
            self.assertEqual(result.router_status, RouterStatus.ROUTED)
            self.assertEqual(result.adapter_selected, "windows_interactive_desktop_relay")
            self.assertEqual(result.runtime_target, "local_worker_runtime_daemon")

    def test_routing_is_stateless(self):
        router = _build_router("/tmp/test-router")
        p1 = WorkPacket(packet_id="PKT-S1", action_type="ping")
        p2 = WorkPacket(packet_id="PKT-S2", action_type="open_application_url")
        r1 = router.route_dry_run(p1)
        r2 = router.route_dry_run(p2)
        r1b = router.route_dry_run(p1)
        self.assertEqual(r1.adapter_selected, r1b.adapter_selected)
        self.assertEqual(r1.runtime_target, r1b.runtime_target)
        self.assertNotEqual(
            r1.router_decision.capability_matched, r2.router_decision.capability_matched
        )


class TestRouterResultStructure(unittest.TestCase):
    def test_result_has_timestamps(self):
        router = _build_router("/tmp/test-router")
        packet = WorkPacket(packet_id="PKT-TS-001", action_type="ping")
        result = router.route_dry_run(packet)
        self.assertTrue(result.started_at)
        self.assertTrue(result.completed_at)

    def test_result_has_trace_id(self):
        router = _build_router("/tmp/test-router")
        packet = WorkPacket(packet_id="PKT-TR-001", action_type="ping")
        result = router.route_dry_run(packet)
        self.assertEqual(result.execution_trace_id, "PKT-TR-001")

    def test_failed_result_has_error_message(self):
        router = _build_router("/tmp/test-router")
        packet = WorkPacket(packet_id="", action_type="")
        result = router.route_dry_run(packet)
        self.assertTrue(result.error_message)


class TestConfigLoading(unittest.TestCase):
    def test_default_config_loads(self):
        config = load_config(DEFAULT_CONFIG_PATH)
        self.assertIn("default_runtime_target", config)
        self.assertIn("allowed_action_types", config)
        self.assertIn("proof_required", config)

    def test_config_has_runtime_targets(self):
        config = load_config(DEFAULT_CONFIG_PATH)
        self.assertIn("runtime_targets", config)
        self.assertIn("local_worker_runtime_daemon", config["runtime_targets"])


class TestAllowedActionTypes(unittest.TestCase):
    def test_ping_is_allowed(self):
        self.assertIn("ping", ALLOWED_ACTION_TYPES)

    def test_chrome_is_allowed(self):
        self.assertIn("open_application_url", ALLOWED_ACTION_TYPES)

    def test_shell_exec_not_allowed(self):
        self.assertNotIn("shell_exec", ALLOWED_ACTION_TYPES)
        self.assertNotIn("exec", ALLOWED_ACTION_TYPES)
        self.assertNotIn("arbitrary", ALLOWED_ACTION_TYPES)


class TestCapabilityMap(unittest.TestCase):
    def test_ping_mapped(self):
        self.assertIn("ping", ACTION_CAPABILITY_MAP)

    def test_chrome_mapped(self):
        self.assertIn("open_application_url", ACTION_CAPABILITY_MAP)

    def test_map_entries_match_allowed(self):
        for action in ACTION_CAPABILITY_MAP:
            self.assertIn(action, ALLOWED_ACTION_TYPES)


if __name__ == "__main__":
    unittest.main()
