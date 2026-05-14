"""Tests for Phase 96.8AM — Execution-Time Canonical Registry Propagation.

Verifies:
  1. !commands and node sync use same registry hash
  2. chrome_proof resolves in node sync
  3. chrome_open_google_drive resolves in node sync
  4. Action type lookup works in sync gate
  5. Stale static allowed_action_types cannot deny canonical command
  6. Duplicated command maps are not used
  7. ExecutionGate validates via canonical registry
  8. NodeSyncGate validates both command names and action types
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"
sys.path.insert(0, os.path.join(os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS", "services"))


class TestNodeSyncAcceptsCanonicalActions:
    """The sync gate must accept action types, not just command names."""

    def test_chrome_proof_accepted_by_action(self) -> None:
        from composition.registries.canonical_command_registry_v1 import get_canonical_registry
        from execution.runtime.node_sync_gate_v1 import NodeSyncGate, SyncPolicy

        reg = get_canonical_registry()
        gate = NodeSyncGate(
            command_registry=reg.command_action_map,
            worker_capabilities=["chrome_proof"],
            sync_policy=SyncPolicy.WARN_ONLY,
            registry_hash=reg.registry_hash(),
        )
        result = gate.validate(
            requested_command="chrome_proof",
            requested_capability="chrome_proof",
        )
        cmd_denials = [r for r in result.denial_reasons if "command_not_in_registry" in r]
        assert len(cmd_denials) == 0

    def test_chrome_open_google_drive_accepted_by_action(self) -> None:
        from composition.registries.canonical_command_registry_v1 import get_canonical_registry
        from execution.runtime.node_sync_gate_v1 import NodeSyncGate, SyncPolicy

        reg = get_canonical_registry()
        gate = NodeSyncGate(
            command_registry=reg.command_action_map,
            worker_capabilities=["chrome_open_google_drive"],
            sync_policy=SyncPolicy.WARN_ONLY,
            registry_hash=reg.registry_hash(),
        )
        result = gate.validate(
            requested_command="chrome_open_google_drive",
            requested_capability="chrome_open_google_drive",
        )
        cmd_denials = [r for r in result.denial_reasons if "command_not_in_registry" in r]
        assert len(cmd_denials) == 0

    def test_command_name_still_accepted(self) -> None:
        from composition.registries.canonical_command_registry_v1 import get_canonical_registry
        from execution.runtime.node_sync_gate_v1 import NodeSyncGate, SyncPolicy

        reg = get_canonical_registry()
        gate = NodeSyncGate(
            command_registry=reg.command_action_map,
            worker_capabilities=["chrome_proof"],
            sync_policy=SyncPolicy.WARN_ONLY,
            registry_hash=reg.registry_hash(),
        )
        result = gate.validate(
            requested_command="!chrome-proof",
            requested_capability="chrome_proof",
        )
        cmd_denials = [r for r in result.denial_reasons if "command_not_in_registry" in r]
        assert len(cmd_denials) == 0

    def test_unknown_action_still_denied(self) -> None:
        from composition.registries.canonical_command_registry_v1 import get_canonical_registry
        from execution.runtime.node_sync_gate_v1 import NodeSyncGate, SyncPolicy

        reg = get_canonical_registry()
        gate = NodeSyncGate(
            command_registry=reg.command_action_map,
            worker_capabilities=[],
            sync_policy=SyncPolicy.WARN_ONLY,
            registry_hash=reg.registry_hash(),
        )
        result = gate.validate(
            requested_command="totally_fake_action",
        )
        cmd_denials = [r for r in result.denial_reasons if "command_not_in_registry" in r]
        assert len(cmd_denials) == 1

    def test_all_canonical_actions_accepted(self) -> None:
        from composition.registries.canonical_command_registry_v1 import get_canonical_registry
        from execution.runtime.node_sync_gate_v1 import NodeSyncGate, SyncPolicy

        reg = get_canonical_registry()
        gate = NodeSyncGate(
            command_registry=reg.command_action_map,
            worker_capabilities=list(reg.actions),
            sync_policy=SyncPolicy.WARN_ONLY,
            registry_hash=reg.registry_hash(),
        )
        for action in reg.actions:
            result = gate.validate(
                requested_command=action,
                requested_capability=action,
            )
            cmd_denials = [r for r in result.denial_reasons if "command_not_in_registry" in r]
            assert len(cmd_denials) == 0, f"{action} denied by node sync"


class TestRegistryHashPropagation:
    def test_surface_and_sync_gate_same_hash(self) -> None:
        from composition.registries.canonical_command_registry_v1 import get_canonical_registry

        reg = get_canonical_registry()
        from handlers.substrate_command_handler import _CANONICAL

        assert _CANONICAL.registry_hash() == reg.registry_hash()

    def test_adapter_and_canonical_same_source(self) -> None:
        from composition.registries.canonical_command_registry_v1 import get_canonical_registry
        from runtime.interfaces.discord_interface_adapter_v1 import COMMAND_ACTION_MAP

        reg = get_canonical_registry()
        assert COMMAND_ACTION_MAP == reg.command_action_map

    def test_sync_gate_gets_registry_hash(self) -> None:
        from composition.registries.canonical_command_registry_v1 import get_canonical_registry
        from execution.runtime.node_sync_gate_v1 import NodeSyncGate, SyncPolicy

        reg = get_canonical_registry()
        gate = NodeSyncGate(
            command_registry=reg.command_action_map,
            registry_hash=reg.registry_hash(),
            sync_policy=SyncPolicy.WARN_ONLY,
        )
        assert gate._registry_hash == reg.registry_hash()

    def test_manifest_registry_hash_matches(self) -> None:
        from composition.registries.canonical_command_registry_v1 import get_canonical_registry
        from handlers.substrate_command_handler import get_command_surface_manifest

        reg = get_canonical_registry()
        m = get_command_surface_manifest()
        assert m["registry_hash"] == reg.registry_hash()


class TestRouterConfigParity:
    def test_router_config_allows_all_canonical_actions(self) -> None:
        config = json.loads((Path(_ROOT) / "config" / "control_plane_router_v1.json").read_text())
        from composition.registries.canonical_command_registry_v1 import get_canonical_registry

        reg = get_canonical_registry()
        allowed = set(config["allowed_action_types"])
        for action in reg.actions:
            assert action in allowed, f"{action} missing from router config"

    def test_router_contracts_allow_all_actions(self) -> None:
        from control_plane.router.router_contracts import ALLOWED_ACTION_TYPES
        from composition.registries.canonical_command_registry_v1 import get_canonical_registry

        reg = get_canonical_registry()
        for action in reg.actions:
            assert action in ALLOWED_ACTION_TYPES, f"{action} missing from ALLOWED_ACTION_TYPES"

    def test_capability_map_has_all_actions(self) -> None:
        from control_plane.router.control_plane_router_v1 import (
            ACTION_CAPABILITY_MAP,
        )
        from composition.registries.canonical_command_registry_v1 import get_canonical_registry

        reg = get_canonical_registry()
        for action in reg.actions:
            assert action in ACTION_CAPABILITY_MAP, f"{action} missing from ACTION_CAPABILITY_MAP"


class TestSpineExecutionPropagation:
    def test_spine_builder_passes_registry_hash(self) -> None:
        source = (Path(_ROOT) / "runtime" / "interfaces" / "discord_spine_integration_v1.py").read_text()
        assert "registry_hash=_reg.registry_hash()" in source

    def test_spine_builder_uses_canonical_registry(self) -> None:
        source = (Path(_ROOT) / "runtime" / "interfaces" / "discord_spine_integration_v1.py").read_text()
        assert "get_canonical_registry" in source
        assert "_reg.command_action_map" in source

    def test_spine_execution_passes_action_type_to_sync(self) -> None:
        source = (Path(_ROOT) / "core" / "runtime" / "live_local_runtime_execution_v1.py").read_text()
        assert "requested_command=action_type" in source


class TestNoDuplicatedRegistries:
    def test_adapter_no_hardcoded_command_map(self) -> None:
        source = (Path(_ROOT) / "runtime" / "interfaces" / "discord_interface_adapter_v1.py").read_text()
        assert '"!ping": "ping"' not in source
        assert '"!chrome-proof": "chrome_proof"' not in source

    def test_adapter_derives_from_canonical(self) -> None:
        source = (Path(_ROOT) / "runtime" / "interfaces" / "discord_interface_adapter_v1.py").read_text()
        assert "_REGISTRY.command_action_map" in source
        assert "_REGISTRY.spine_routed_commands" in source
        assert "_REGISTRY.command_contracts" in source

    def test_handler_derives_from_canonical(self) -> None:
        source = (Path(_ROOT) / "services" / "handlers" / "substrate_command_handler.py").read_text()
        assert "_CANONICAL.commands" in source


class TestFullSpineSimulation:
    """Simulate the full spine path to verify no command_not_in_registry."""

    def test_chrome_proof_through_sync_gate(self) -> None:
        from composition.registries.canonical_command_registry_v1 import get_canonical_registry
        from execution.runtime.node_sync_gate_v1 import NodeSyncGate, SyncPolicy

        reg = get_canonical_registry()
        gate = NodeSyncGate(
            vps_repo_path=Path(_ROOT),
            command_registry=reg.command_action_map,
            worker_capabilities=[
                "browser_execution",
                "chrome_launch",
                "chrome_open_google_drive",
                "chrome_proof",
                "ingest_safe_doc",
                "ingest_safe_doc_cu",
                "open_application_url",
            ],
            config_path=Path(_ROOT) / "data" / "runtime" / "spine_gate_proofs" / "config_marker.json",
            sync_policy=SyncPolicy.WARN_ONLY,
            registry_hash=reg.registry_hash(),
        )
        result = gate.validate(
            requested_command="chrome_proof",
            requested_capability="chrome_proof",
        )
        for reason in result.denial_reasons:
            assert "command_not_in_registry" not in reason, f"chrome_proof still denied: {reason}"

    def test_chrome_open_google_drive_through_sync_gate(self) -> None:
        from composition.registries.canonical_command_registry_v1 import get_canonical_registry
        from execution.runtime.node_sync_gate_v1 import NodeSyncGate, SyncPolicy

        reg = get_canonical_registry()
        gate = NodeSyncGate(
            vps_repo_path=Path(_ROOT),
            command_registry=reg.command_action_map,
            worker_capabilities=[
                "browser_execution",
                "chrome_launch",
                "chrome_open_google_drive",
                "chrome_proof",
                "ingest_safe_doc",
                "ingest_safe_doc_cu",
                "open_application_url",
            ],
            config_path=Path(_ROOT) / "data" / "runtime" / "spine_gate_proofs" / "config_marker.json",
            sync_policy=SyncPolicy.WARN_ONLY,
            registry_hash=reg.registry_hash(),
        )
        result = gate.validate(
            requested_command="chrome_open_google_drive",
            requested_capability="chrome_open_google_drive",
        )
        for reason in result.denial_reasons:
            assert "command_not_in_registry" not in reason, (
                f"chrome_open_google_drive still denied: {reason}"
            )


class TestRegressionIntegrity:
    def test_all_files_compile(self) -> None:
        import py_compile

        files = [
            f"{_ROOT}/core/runtime/node_sync_gate_v1.py",
            f"{_ROOT}/core/registry/canonical_command_registry_v1.py",
            f"{_ROOT}/runtime/interfaces/discord_interface_adapter_v1.py",
            f"{_ROOT}/runtime/interfaces/discord_spine_integration_v1.py",
            f"{_ROOT}/services/handlers/substrate_command_handler.py",
            f"{_ROOT}/services/discord_bot.py",
        ]
        for f in files:
            py_compile.compile(f, doraise=True)

    def test_bot_compiles(self) -> None:
        import py_compile

        py_compile.compile(f"{_ROOT}/services/discord_bot.py", doraise=True)
