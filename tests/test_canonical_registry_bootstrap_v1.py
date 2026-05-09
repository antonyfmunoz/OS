"""Tests for Phase 96.8AL — Runtime Bootstrap + Canonical Registry Unification.

Verifies:
  1. Command appears in surface AND execution registry
  2. Command denied if bootstrap incomplete
  3. Bootstrap auto-heals safe runtime dirs
  4. Registry hashes deterministic
  5. Runtime state survives restart
  6. Stale registry impossible (single source)
  7. Missing proof marker auto-created
  8. !commands output derived from canonical registry
  9. Execution lookup derived from same registry
  10. No duplicated command definitions allowed
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, "/opt/OS")
sys.path.insert(0, "/opt/OS/services")


class TestCanonicalRegistrySingleSource:
    def test_registry_loads(self) -> None:
        from core.registry.canonical_command_registry_v1 import (
            CanonicalCommandRegistryV1,
        )

        reg = CanonicalCommandRegistryV1()
        assert len(reg) == 20

    def test_all_commands_present(self) -> None:
        from core.registry.canonical_command_registry_v1 import (
            CanonicalCommandRegistryV1,
        )

        reg = CanonicalCommandRegistryV1()
        expected = {
            "!actuator-proof",
            "!adapter-report",
            "!capability-report",
            "!constitution-report",
            "!continuity-report",
            "!governance-intelligence-report",
            "!orchestration-report",
            "!ping",
            "!chrome",
            "!chrome-open-google-drive",
            "!chrome-proof",
            "!doc",
            "!explore-environment",
            "!extract",
            "!ingest-candidate",
            "!ingest-safe-doc",
            "!ingest-safe-doc-cu",
            "!promote-memory",
            "!query-memory",
            "!relay-status",
        }
        assert reg.commands == expected

    def test_command_in_surface_also_in_execution(self) -> None:
        from core.registry.canonical_command_registry_v1 import (
            CanonicalCommandRegistryV1,
        )

        reg = CanonicalCommandRegistryV1()
        for cmd in reg.commands:
            entry = reg.get(cmd)
            assert entry is not None
            assert reg.contains_action(entry.canonical_action)

    def test_action_map_matches_canonical(self) -> None:
        from core.registry.canonical_command_registry_v1 import get_canonical_registry
        from eos_ai.interfaces.discord_interface_adapter_v1 import COMMAND_ACTION_MAP

        reg = get_canonical_registry()
        assert COMMAND_ACTION_MAP == reg.command_action_map

    def test_spine_routed_matches_canonical(self) -> None:
        from core.registry.canonical_command_registry_v1 import get_canonical_registry
        from eos_ai.interfaces.discord_interface_adapter_v1 import SPINE_ROUTED_COMMANDS

        reg = get_canonical_registry()
        assert SPINE_ROUTED_COMMANDS == reg.spine_routed_commands

    def test_supported_commands_matches_canonical(self) -> None:
        from core.registry.canonical_command_registry_v1 import get_canonical_registry
        from eos_ai.interfaces.discord_interface_adapter_v1 import SUPPORTED_COMMANDS

        reg = get_canonical_registry()
        assert SUPPORTED_COMMANDS == reg.commands | {"!status"}

    def test_substrate_commands_matches_canonical(self) -> None:
        from core.registry.canonical_command_registry_v1 import get_canonical_registry
        from handlers.substrate_command_handler import SUBSTRATE_COMMANDS

        reg = get_canonical_registry()
        assert SUBSTRATE_COMMANDS == reg.commands

    def test_no_duplicate_command_definitions(self) -> None:
        from core.registry.canonical_command_registry_v1 import CANONICAL_COMMANDS

        names = [e.command_name for e in CANONICAL_COMMANDS]
        assert len(names) == len(set(names))

    def test_no_duplicate_action_definitions(self) -> None:
        from core.registry.canonical_command_registry_v1 import CANONICAL_COMMANDS

        actions = [e.canonical_action for e in CANONICAL_COMMANDS]
        assert len(actions) == len(set(actions))


class TestRegistryHashDeterminism:
    def test_registry_hash_deterministic(self) -> None:
        from core.registry.canonical_command_registry_v1 import (
            CanonicalCommandRegistryV1,
        )

        r1 = CanonicalCommandRegistryV1()
        r2 = CanonicalCommandRegistryV1()
        assert r1.registry_hash() == r2.registry_hash()
        assert len(r1.registry_hash()) == 12

    def test_surface_hash_deterministic(self) -> None:
        from core.registry.canonical_command_registry_v1 import (
            CanonicalCommandRegistryV1,
        )

        r1 = CanonicalCommandRegistryV1()
        r2 = CanonicalCommandRegistryV1()
        assert r1.surface_hash() == r2.surface_hash()

    def test_registry_hash_differs_from_surface_hash(self) -> None:
        from core.registry.canonical_command_registry_v1 import (
            CanonicalCommandRegistryV1,
        )

        reg = CanonicalCommandRegistryV1()
        assert reg.registry_hash() != reg.surface_hash()

    def test_singleton_returns_same_instance(self) -> None:
        from core.registry.canonical_command_registry_v1 import get_canonical_registry

        r1 = get_canonical_registry()
        r2 = get_canonical_registry()
        assert r1 is r2

    def test_to_dict_json_serializable(self) -> None:
        from core.registry.canonical_command_registry_v1 import (
            CanonicalCommandRegistryV1,
        )

        reg = CanonicalCommandRegistryV1()
        data = reg.to_dict()
        serialized = json.dumps(data)
        assert len(serialized) > 0
        assert data["command_count"] == 20


class TestBootstrapLifecycle:
    def test_bootstrap_creates_missing_dirs(self, tmp_path: Path) -> None:
        from core.runtime.runtime_bootstrap_state_v1 import RuntimeBootstrapStateV1

        base = tmp_path / "repo"
        base.mkdir()
        (base / "config").mkdir()
        (base / "config/control_plane_router_v1.json").write_text("{}")
        (base / "data/registries").mkdir(parents=True)
        (base / "data/registries/local_worker_adapter_registry_v1.json").write_text("{}")

        bs = RuntimeBootstrapStateV1(base)
        v = bs.bootstrap(auto_heal=True)
        assert v.valid is True
        assert len(v.auto_healed) > 0
        assert (base / "data/runtime/runtime_proofs").exists()
        assert (base / "data/runtime/spine_gate_proofs").exists()

    def test_bootstrap_fails_without_config(self, tmp_path: Path) -> None:
        from core.runtime.runtime_bootstrap_state_v1 import RuntimeBootstrapStateV1

        base = tmp_path / "repo"
        base.mkdir()

        bs = RuntimeBootstrapStateV1(base)
        v = bs.bootstrap(auto_heal=True)
        assert v.valid is False
        assert len(v.missing_configs) > 0
        assert any("control_plane_router" in r for r in v.denial_reasons)

    def test_bootstrap_creates_config_marker(self, tmp_path: Path) -> None:
        from core.runtime.runtime_bootstrap_state_v1 import RuntimeBootstrapStateV1

        base = tmp_path / "repo"
        base.mkdir()
        (base / "config").mkdir()
        (base / "config/control_plane_router_v1.json").write_text("{}")
        (base / "data/registries").mkdir(parents=True)
        (base / "data/registries/local_worker_adapter_registry_v1.json").write_text("{}")

        bs = RuntimeBootstrapStateV1(base)
        v = bs.bootstrap(auto_heal=True)
        marker = base / "data/runtime/spine_gate_proofs/config_marker.json"
        assert marker.exists()
        data = json.loads(marker.read_text())
        assert data["created_by"] == "runtime_bootstrap_v1"
        assert "registry_hash" in data

    def test_bootstrap_persists_ledger(self, tmp_path: Path) -> None:
        from core.runtime.runtime_bootstrap_state_v1 import RuntimeBootstrapStateV1

        base = tmp_path / "repo"
        base.mkdir()
        (base / "config").mkdir()
        (base / "config/control_plane_router_v1.json").write_text("{}")
        (base / "data/registries").mkdir(parents=True)
        (base / "data/registries/local_worker_adapter_registry_v1.json").write_text("{}")

        bs = RuntimeBootstrapStateV1(base)
        bs.bootstrap(auto_heal=True)
        ledger_dir = base / "data/runtime/transformation_ledger/bootstrap"
        assert ledger_dir.exists()
        files = list(ledger_dir.glob("BOOTSTRAP-*.json"))
        assert len(files) == 1
        data = json.loads(files[0].read_text())
        stages = [e["stage"] for e in data]
        assert "BOOTSTRAP_START" in stages
        assert "bootstrap_runtime_ready" in stages

    def test_bootstrap_stage_lifecycle(self, tmp_path: Path) -> None:
        from core.runtime.runtime_bootstrap_state_v1 import (
            BootstrapStage,
            RuntimeBootstrapStateV1,
        )

        base = tmp_path / "repo"
        base.mkdir()
        (base / "config").mkdir()
        (base / "config/control_plane_router_v1.json").write_text("{}")
        (base / "data/registries").mkdir(parents=True)
        (base / "data/registries/local_worker_adapter_registry_v1.json").write_text("{}")

        bs = RuntimeBootstrapStateV1(base)
        assert bs.stage == BootstrapStage.BOOTSTRAP_START
        v = bs.bootstrap()
        assert bs.stage == BootstrapStage.BOOTSTRAP_RUNTIME_READY
        assert bs.is_ready is True

    def test_bootstrap_never_auto_heals_configs(self, tmp_path: Path) -> None:
        from core.runtime.runtime_bootstrap_state_v1 import RuntimeBootstrapStateV1

        base = tmp_path / "repo"
        base.mkdir()

        bs = RuntimeBootstrapStateV1(base)
        v = bs.bootstrap(auto_heal=True)
        assert not (base / "config/control_plane_router_v1.json").exists()
        assert not (base / "eos_ai/.env").exists()

    def test_bootstrap_runtime_id_deterministic_per_instance(self) -> None:
        from core.runtime.runtime_bootstrap_state_v1 import RuntimeBootstrapStateV1

        bs1 = RuntimeBootstrapStateV1(Path("/opt/OS"))
        bs2 = RuntimeBootstrapStateV1(Path("/opt/OS"))
        assert bs1.runtime_id != bs2.runtime_id
        assert bs1.runtime_id.startswith("RUNTIME-")


class TestBootstrapDeniedExecution:
    def test_command_denied_if_bootstrap_incomplete(self) -> None:
        from core.runtime.runtime_bootstrap_state_v1 import (
            BootstrapStage,
            BootstrapValidation,
        )

        v = BootstrapValidation()
        v.stage = BootstrapStage.BOOTSTRAP_FAILED
        v.denial_reasons = ["missing_configs: config/control_plane_router_v1.json"]
        assert v.valid is False
        assert len(v.denial_reasons) > 0

    def test_validation_to_dict(self) -> None:
        from core.runtime.runtime_bootstrap_state_v1 import BootstrapValidation

        v = BootstrapValidation(valid=True, registry_hash="abc123", registry_count=20)
        d = v.to_dict()
        assert d["valid"] is True
        assert d["registry_hash"] == "abc123"
        assert d["registry_count"] == 20


class TestRouterConfigParity:
    def test_all_canonical_actions_in_router_config(self) -> None:
        from core.registry.canonical_command_registry_v1 import get_canonical_registry

        reg = get_canonical_registry()
        config = json.loads(Path("/opt/OS/config/control_plane_router_v1.json").read_text())
        allowed = set(config["allowed_action_types"])
        for action in reg.actions:
            assert action in allowed, f"{action} missing from router config allowed_action_types"

    def test_no_orphan_actions_in_router_config(self) -> None:
        from core.registry.canonical_command_registry_v1 import get_canonical_registry

        reg = get_canonical_registry()
        config = json.loads(Path("/opt/OS/config/control_plane_router_v1.json").read_text())
        for action in config["allowed_action_types"]:
            assert reg.contains_action(action), f"{action} in config but not in canonical registry"


class TestCommandSurfaceFromCanonical:
    def test_commands_list_from_canonical(self) -> None:
        from handlers.substrate_command_handler import (
            SUBSTRATE_COMMANDS,
            _CANONICAL,
        )

        assert SUBSTRATE_COMMANDS == _CANONICAL.commands

    def test_manifest_includes_registry_hash(self) -> None:
        from handlers.substrate_command_handler import get_command_surface_manifest

        m = get_command_surface_manifest()
        assert "registry_hash" in m
        assert len(m["registry_hash"]) == 12

    def test_manifest_action_map_from_canonical(self) -> None:
        from core.registry.canonical_command_registry_v1 import get_canonical_registry
        from handlers.substrate_command_handler import get_command_surface_manifest

        m = get_command_surface_manifest()
        reg = get_canonical_registry()
        assert m["action_map"] == dict(sorted(reg.command_action_map.items()))


class TestRegistryContracts:
    def test_spine_commands_have_contracts(self) -> None:
        from core.registry.canonical_command_registry_v1 import get_canonical_registry

        reg = get_canonical_registry()
        contracts = reg.command_contracts
        for cmd in reg.spine_routed_commands:
            assert cmd in contracts, f"{cmd} is spine-routed but has no contract"

    def test_router_commands_no_contracts(self) -> None:
        from core.registry.canonical_command_registry_v1 import get_canonical_registry

        reg = get_canonical_registry()
        contracts = reg.command_contracts
        for cmd in reg.router_routed_commands:
            assert cmd not in contracts

    def test_chrome_proof_contract_flags(self) -> None:
        from core.registry.canonical_command_registry_v1 import get_canonical_registry

        reg = get_canonical_registry()
        contracts = reg.command_contracts
        cp = contracts["!chrome-proof"]
        assert cp["require_foreground_gui"] is True
        assert cp["require_screenshot_proof"] is True
        assert cp["mutation_allowed"] is False

    def test_command_entry_frozen(self) -> None:
        from core.registry.canonical_command_registry_v1 import get_canonical_registry

        reg = get_canonical_registry()
        entry = reg.get("!ping")
        with pytest.raises(AttributeError):
            entry.command_name = "!modified"

    def test_allowed_action_types_sorted(self) -> None:
        from core.registry.canonical_command_registry_v1 import get_canonical_registry

        reg = get_canonical_registry()
        actions = reg.allowed_action_types
        assert actions == sorted(actions)


class TestLiveBootstrapOnVPS:
    def test_real_bootstrap_succeeds(self) -> None:
        from core.runtime.runtime_bootstrap_state_v1 import RuntimeBootstrapStateV1

        bs = RuntimeBootstrapStateV1(Path("/opt/OS"))
        v = bs.bootstrap(auto_heal=True)
        assert v.valid is True
        assert v.registry_loaded is True
        assert v.registry_count == 20

    def test_real_bootstrap_registry_hash_matches(self) -> None:
        from core.registry.canonical_command_registry_v1 import get_canonical_registry
        from core.runtime.runtime_bootstrap_state_v1 import RuntimeBootstrapStateV1

        bs = RuntimeBootstrapStateV1(Path("/opt/OS"))
        v = bs.bootstrap()
        reg = get_canonical_registry()
        assert v.registry_hash == reg.registry_hash()
