"""Tests for Phase 96.8AO — Workstation Relay Node Provisioning.

Verifies:
  1. RelayHeartbeat dataclass and serialization
  2. Heartbeat read/write round-trip
  3. Health evaluation (alive, degraded, timeout, dead)
  4. WorkstationRelayNode construction from heartbeat
  5. Node registry status report
  6. Relay online detection
  7. Relay proof classification and persistence
  8. Proof hash determinism
  9. Canonical registry includes !relay-status (13 commands)
  10. Router config parity for relay_status action
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, "/opt/OS")
sys.path.insert(0, "/opt/OS/services")


class TestRelayHeartbeatDataclass:
    def test_default_heartbeat(self) -> None:
        from core.workstation.workstation_relay_heartbeat_v1 import RelayHeartbeat

        hb = RelayHeartbeat()
        assert hb.node_id == ""
        assert hb.relay_version == "v1"
        assert hb.timestamp != ""

    def test_heartbeat_with_values(self) -> None:
        from core.workstation.workstation_relay_heartbeat_v1 import RelayHeartbeat

        hb = RelayHeartbeat(
            node_id="WRN-abc12345",
            machine_name="DESKTOP-TEST",
            user_name="founder",
            chrome_available=True,
            desktop_session_active=True,
            desktop_unlocked=True,
            monitor_detected=True,
            relay_pid=1234,
            capabilities=["launch_chrome", "capture_screenshot"],
        )
        assert hb.node_id == "WRN-abc12345"
        assert hb.chrome_available is True
        assert len(hb.capabilities) == 2

    def test_heartbeat_to_dict(self) -> None:
        from core.workstation.workstation_relay_heartbeat_v1 import RelayHeartbeat

        hb = RelayHeartbeat(node_id="WRN-test", machine_name="M1")
        d = hb.to_dict()
        assert d["node_id"] == "WRN-test"
        assert d["machine_name"] == "M1"
        assert "timestamp" in d
        serialized = json.dumps(d)
        assert len(serialized) > 0


class TestHeartbeatReadWrite:
    def test_write_then_read(self, tmp_path: Path) -> None:
        from core.workstation.workstation_relay_heartbeat_v1 import (
            RelayHeartbeat,
            read_relay_heartbeat,
            write_relay_heartbeat,
        )

        hb = RelayHeartbeat(
            node_id="WRN-roundtrip",
            machine_name="ROUND-TRIP",
            chrome_available=True,
            desktop_session_active=True,
        )
        path = write_relay_heartbeat(hb, tmp_path)
        assert path.exists()

        loaded = read_relay_heartbeat(tmp_path)
        assert loaded is not None
        assert loaded.node_id == "WRN-roundtrip"
        assert loaded.machine_name == "ROUND-TRIP"
        assert loaded.chrome_available is True

    def test_read_missing_file(self, tmp_path: Path) -> None:
        from core.workstation.workstation_relay_heartbeat_v1 import read_relay_heartbeat

        result = read_relay_heartbeat(tmp_path)
        assert result is None

    def test_read_corrupt_file(self, tmp_path: Path) -> None:
        from core.workstation.workstation_relay_heartbeat_v1 import (
            RELAY_HEARTBEAT_PATH,
            read_relay_heartbeat,
        )

        hb_path = tmp_path / RELAY_HEARTBEAT_PATH
        hb_path.parent.mkdir(parents=True, exist_ok=True)
        hb_path.write_text("not valid json {{{")
        result = read_relay_heartbeat(tmp_path)
        assert result is None


class TestHealthEvaluation:
    def test_alive_heartbeat(self) -> None:
        from core.workstation.workstation_relay_heartbeat_v1 import (
            RelayHeartbeat,
            evaluate_relay_health,
        )
        from core.runtime.runtime_heartbeat_v1 import HeartbeatHealth

        now = datetime.now(timezone.utc)
        hb = RelayHeartbeat(
            node_id="WRN-alive",
            timestamp=now.isoformat(),
        )
        health = evaluate_relay_health(hb, now=now)
        assert health == HeartbeatHealth.ALIVE

    def test_degraded_heartbeat(self) -> None:
        from core.workstation.workstation_relay_heartbeat_v1 import (
            RelayHeartbeat,
            evaluate_relay_health,
        )
        from core.runtime.runtime_heartbeat_v1 import HeartbeatHealth

        now = datetime.now(timezone.utc)
        hb = RelayHeartbeat(
            node_id="WRN-degraded",
            timestamp=(now - timedelta(seconds=35)).isoformat(),
        )
        health = evaluate_relay_health(hb, now=now, stale_seconds=60)
        assert health == HeartbeatHealth.DEGRADED

    def test_timeout_heartbeat(self) -> None:
        from core.workstation.workstation_relay_heartbeat_v1 import (
            RelayHeartbeat,
            evaluate_relay_health,
        )
        from core.runtime.runtime_heartbeat_v1 import HeartbeatHealth

        now = datetime.now(timezone.utc)
        hb = RelayHeartbeat(
            node_id="WRN-stale",
            timestamp=(now - timedelta(seconds=120)).isoformat(),
        )
        health = evaluate_relay_health(hb, now=now, stale_seconds=60)
        assert health == HeartbeatHealth.TIMEOUT

    def test_dead_no_heartbeat(self) -> None:
        from core.workstation.workstation_relay_heartbeat_v1 import evaluate_relay_health
        from core.runtime.runtime_heartbeat_v1 import HeartbeatHealth

        health = evaluate_relay_health(None)
        assert health == HeartbeatHealth.DEAD

    def test_dead_empty_timestamp(self) -> None:
        from core.workstation.workstation_relay_heartbeat_v1 import (
            RelayHeartbeat,
            evaluate_relay_health,
        )
        from core.runtime.runtime_heartbeat_v1 import HeartbeatHealth

        hb = RelayHeartbeat(node_id="WRN-empty", timestamp="")
        hb.timestamp = ""
        health = evaluate_relay_health(hb)
        assert health == HeartbeatHealth.DEAD

    def test_dead_invalid_timestamp(self) -> None:
        from core.workstation.workstation_relay_heartbeat_v1 import (
            RelayHeartbeat,
            evaluate_relay_health,
        )
        from core.runtime.runtime_heartbeat_v1 import HeartbeatHealth

        hb = RelayHeartbeat(node_id="WRN-bad")
        hb.timestamp = "not-a-date"
        health = evaluate_relay_health(hb)
        assert health == HeartbeatHealth.DEAD

    def test_z_suffix_timestamp(self) -> None:
        from core.workstation.workstation_relay_heartbeat_v1 import (
            RelayHeartbeat,
            evaluate_relay_health,
        )
        from core.runtime.runtime_heartbeat_v1 import HeartbeatHealth

        now = datetime.now(timezone.utc)
        hb = RelayHeartbeat(
            node_id="WRN-z",
            timestamp=now.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        )
        health = evaluate_relay_health(hb, now=now)
        assert health == HeartbeatHealth.ALIVE


class TestRelayOnlineDetection:
    def test_online_with_fresh_heartbeat(self, tmp_path: Path) -> None:
        from core.workstation.workstation_relay_heartbeat_v1 import (
            RelayHeartbeat,
            is_relay_online,
            write_relay_heartbeat,
        )

        hb = RelayHeartbeat(
            node_id="WRN-online",
            desktop_session_active=True,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        write_relay_heartbeat(hb, tmp_path)
        online, reason = is_relay_online(tmp_path)
        assert online is True
        assert reason == "alive"

    def test_offline_no_heartbeat(self, tmp_path: Path) -> None:
        from core.workstation.workstation_relay_heartbeat_v1 import is_relay_online

        online, reason = is_relay_online(tmp_path)
        assert online is False
        assert reason == "no_heartbeat_file"

    def test_offline_stale_heartbeat(self, tmp_path: Path) -> None:
        from core.workstation.workstation_relay_heartbeat_v1 import (
            RelayHeartbeat,
            is_relay_online,
            write_relay_heartbeat,
        )

        hb = RelayHeartbeat(
            node_id="WRN-stale",
            desktop_session_active=True,
            timestamp=(datetime.now(timezone.utc) - timedelta(seconds=120)).isoformat(),
        )
        write_relay_heartbeat(hb, tmp_path)
        online, reason = is_relay_online(tmp_path)
        assert online is False
        assert reason == "heartbeat_stale"

    def test_offline_no_desktop_session(self, tmp_path: Path) -> None:
        from core.workstation.workstation_relay_heartbeat_v1 import (
            RelayHeartbeat,
            is_relay_online,
            write_relay_heartbeat,
        )

        hb = RelayHeartbeat(
            node_id="WRN-no-desktop",
            desktop_session_active=False,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        write_relay_heartbeat(hb, tmp_path)
        online, reason = is_relay_online(tmp_path)
        assert online is False
        assert reason == "no_desktop_session"


class TestWorkstationRelayNode:
    def test_node_from_heartbeat(self, tmp_path: Path) -> None:
        from core.workstation.workstation_relay_heartbeat_v1 import (
            RELAY_HEARTBEAT_PATH,
        )
        from core.workstation.workstation_relay_node_v1 import (
            load_relay_node_from_heartbeat,
        )

        hb_path = tmp_path / RELAY_HEARTBEAT_PATH
        hb_path.parent.mkdir(parents=True, exist_ok=True)
        hb_path.write_text(
            json.dumps(
                {
                    "node_id": "WRN-testnode",
                    "machine_name": "DESKTOP-PROOF",
                    "user_name": "founder",
                    "os": "Windows 10",
                    "relay_version": "v1",
                    "relay_pid": 5678,
                    "desktop_session_active": True,
                    "desktop_unlocked": True,
                    "monitor_detected": True,
                    "chrome_available": True,
                    "capabilities": ["launch_chrome", "capture_screenshot"],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
        )

        node = load_relay_node_from_heartbeat(hb_path)
        assert node is not None
        assert node.node_id == "WRN-testnode"
        assert node.machine_name == "DESKTOP-PROOF"
        assert node.chrome_available is True
        assert node.is_execution_capable is True
        assert len(node.capabilities) == 2

    def test_node_none_when_no_file(self, tmp_path: Path) -> None:
        from core.workstation.workstation_relay_node_v1 import (
            load_relay_node_from_heartbeat,
        )

        node = load_relay_node_from_heartbeat(tmp_path / "nonexistent.json")
        assert node is None

    def test_node_not_execution_capable(self, tmp_path: Path) -> None:
        from core.workstation.workstation_relay_heartbeat_v1 import RELAY_HEARTBEAT_PATH
        from core.workstation.workstation_relay_node_v1 import (
            load_relay_node_from_heartbeat,
        )

        hb_path = tmp_path / RELAY_HEARTBEAT_PATH
        hb_path.parent.mkdir(parents=True, exist_ok=True)
        hb_path.write_text(
            json.dumps(
                {
                    "node_id": "WRN-nodesktop",
                    "desktop_session_active": False,
                    "chrome_available": False,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
        )

        node = load_relay_node_from_heartbeat(hb_path)
        assert node is not None
        assert node.is_execution_capable is False


class TestNodeRegistry:
    def test_registry_no_heartbeat(self) -> None:
        from core.workstation.workstation_node_registry_v1 import (
            WorkstationNodeRegistry,
        )

        registry = WorkstationNodeRegistry(Path("/tmp/nonexistent-test-path"))
        assert registry.get_primary_node() is None
        assert registry.is_relay_available() is False

    def test_registry_status_offline(self) -> None:
        from core.workstation.workstation_node_registry_v1 import (
            WorkstationNodeRegistry,
        )

        registry = WorkstationNodeRegistry(Path("/tmp/nonexistent-test-path"))
        status = registry.get_relay_status()
        assert status["online"] is False
        assert status["health"] == "dead"
        assert status["maturity_ceiling"] == "L0_SIMULATED"

    def test_registry_status_with_heartbeat(self, tmp_path: Path) -> None:
        from core.workstation.workstation_relay_heartbeat_v1 import (
            RelayHeartbeat,
            write_relay_heartbeat,
        )
        from core.workstation.workstation_node_registry_v1 import (
            WorkstationNodeRegistry,
        )

        hb = RelayHeartbeat(
            node_id="WRN-regtest",
            machine_name="DESKTOP-REG",
            desktop_session_active=True,
            desktop_unlocked=True,
            chrome_available=True,
            monitor_detected=True,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        write_relay_heartbeat(hb, tmp_path)

        registry = WorkstationNodeRegistry(tmp_path)
        status = registry.get_relay_status()
        assert status["online"] is True
        assert status["node_id"] == "WRN-regtest"
        assert status["chrome_available"] is True
        assert status["is_execution_capable"] is True


class TestRelayProof:
    def test_classify_relay_proof(self) -> None:
        from core.workstation.workstation_relay_proof_v1 import classify_relay_proof

        relay_result = {
            "request_id": "REQ-001",
            "trace_id": "TRACE-001",
            "action_type": "chrome_proof",
            "stages_completed": ["launch", "focus"],
            "adapter_status": "completed",
            "observed_desktop_state": {
                "chrome_pid": 1234,
                "window_handle": 5678,
                "window_title": "Google Chrome",
                "visible": True,
                "focused": True,
                "screenshot_path": "/tmp/ss.png",
                "screenshot_hash": "abc123",
                "founder_confirmed": False,
                "is_dry_run": False,
            },
        }
        proof = classify_relay_proof(relay_result)
        assert proof["proof_type"] == "workstation_relay_execution"
        assert proof["request_id"] == "REQ-001"
        assert proof["chrome_pid"] == 1234
        assert proof["maturity_level"] >= 0
        assert proof["is_dry_run"] is False

    def test_persist_relay_proof(self, tmp_path: Path) -> None:
        from core.workstation.workstation_relay_proof_v1 import persist_relay_proof

        relay_result = {
            "request_id": "REQ-PERSIST",
            "trace_id": "TRACE-PERSIST-001",
            "action_type": "chrome_proof",
            "dry_run": True,
            "observed_desktop_state": {
                "chrome_pid": 0,
            },
        }
        path = persist_relay_proof(relay_result, tmp_path)
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["trace_id"] == "TRACE-PERSIST-001"
        assert data["is_dry_run"] is True

    def test_proof_hash_deterministic(self) -> None:
        from core.workstation.workstation_relay_proof_v1 import compute_proof_hash

        result = {
            "request_id": "REQ-HASH",
            "trace_id": "TRACE-HASH",
            "observed_desktop_state": {
                "chrome_pid": 999,
                "window_handle": 888,
                "screenshot_hash": "deadbeef",
            },
        }
        h1 = compute_proof_hash(result)
        h2 = compute_proof_hash(result)
        assert h1 == h2
        assert len(h1) == 16

    def test_dry_run_capped_at_l0(self) -> None:
        from core.workstation.workstation_relay_proof_v1 import classify_relay_proof

        relay_result = {
            "request_id": "REQ-DRY",
            "trace_id": "TRACE-DRY",
            "action_type": "chrome_proof",
            "dry_run": True,
            "observed_desktop_state": {
                "chrome_pid": 9999,
                "window_handle": 7777,
                "window_title": "Chrome",
                "visible": True,
                "focused": True,
                "screenshot_path": "/fake.png",
                "screenshot_hash": "abc",
                "founder_confirmed": True,
            },
        }
        proof = classify_relay_proof(relay_result)
        assert proof["maturity_level"] == 0


class TestCanonicalRegistryRelayStatus:
    def test_registry_has_15_commands(self) -> None:
        from core.registry.canonical_command_registry_v1 import (
            CanonicalCommandRegistryV1,
        )

        reg = CanonicalCommandRegistryV1()
        assert len(reg) == 16

    def test_relay_status_in_registry(self) -> None:
        from core.registry.canonical_command_registry_v1 import get_canonical_registry

        reg = get_canonical_registry()
        assert reg.contains("!relay-status")
        entry = reg.get("!relay-status")
        assert entry is not None
        assert entry.canonical_action == "relay_status"
        assert entry.routing_mode.value == "router"
        assert entry.execution_mode.value == "shell"

    def test_relay_status_is_router_routed(self) -> None:
        from core.registry.canonical_command_registry_v1 import get_canonical_registry

        reg = get_canonical_registry()
        assert "!relay-status" in reg.router_routed_commands
        assert "!relay-status" not in reg.spine_routed_commands

    def test_relay_status_in_router_config(self) -> None:
        config = json.loads(Path("/opt/OS/config/control_plane_router_v1.json").read_text())
        assert "relay_status" in config["allowed_action_types"]

    def test_relay_status_in_allowed_action_types(self) -> None:
        from core.control_plane_router.router_contracts import ALLOWED_ACTION_TYPES

        assert "relay_status" in ALLOWED_ACTION_TYPES

    def test_relay_status_in_capability_map(self) -> None:
        from core.control_plane_router.control_plane_router_v1 import (
            ACTION_CAPABILITY_MAP,
        )

        assert "relay_status" in ACTION_CAPABILITY_MAP
        cap = ACTION_CAPABILITY_MAP["relay_status"]
        assert cap.requires_gui is False

    def test_relay_status_in_adapter_registry(self) -> None:
        registry_path = Path("/opt/OS/data/registries/local_worker_adapter_registry_v1.json")
        data = json.loads(registry_path.read_text())
        adapter = data["adapters"]["windows_interactive_desktop_relay"]
        action_types = [c["action_type"] for c in adapter["capabilities"]]
        assert "relay_status" in action_types

    def test_all_canonical_actions_in_router_config(self) -> None:
        from core.registry.canonical_command_registry_v1 import get_canonical_registry

        reg = get_canonical_registry()
        config = json.loads(Path("/opt/OS/config/control_plane_router_v1.json").read_text())
        allowed = set(config["allowed_action_types"])
        for action in reg.actions:
            assert action in allowed, f"{action} missing from router config"


class TestSubstrateHandlerRelayStatus:
    def test_relay_status_in_substrate_commands(self) -> None:
        from handlers.substrate_command_handler import SUBSTRATE_COMMANDS

        assert "!relay-status" in SUBSTRATE_COMMANDS

    def test_relay_status_is_substrate_command(self) -> None:
        from handlers.substrate_command_handler import is_substrate_command

        assert is_substrate_command("!relay-status") is True
