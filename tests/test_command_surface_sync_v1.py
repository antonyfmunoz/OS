"""Tests for Phase 96.8AJ — Command Surface + Node Runtime Sync.

Verifies:
  1. Substrate command handler registration and routing
  2. !commands command shows live surface
  3. !chrome-proof is substrate-routed (not gateway-routed)
  4. Command surface sync verification
  5. Stale process detection
  6. VPS/origin parity checks
  7. No regression on existing bot commands
  8. Merge conflict resolved (no conflict markers)
"""

import hashlib
import json
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, "/opt/OS")
sys.path.insert(0, "/opt/OS/services")


# ── Handler registration ────────────────────────────────────────────────────


class TestSubstrateHandlerRegistration:
    def test_handler_module_imports(self) -> None:
        from handlers.substrate_command_handler import (
            SUBSTRATE_COMMANDS,
            handle_substrate_command,
            is_substrate_command,
        )

        assert callable(handle_substrate_command)
        assert callable(is_substrate_command)
        assert len(SUBSTRATE_COMMANDS) > 0

    def test_chrome_proof_is_substrate(self) -> None:
        from handlers.substrate_command_handler import is_substrate_command

        assert is_substrate_command("!chrome-proof")

    def test_ping_is_substrate(self) -> None:
        from handlers.substrate_command_handler import is_substrate_command

        assert is_substrate_command("!ping")

    def test_chrome_is_substrate(self) -> None:
        from handlers.substrate_command_handler import is_substrate_command

        assert is_substrate_command("!chrome")

    def test_ingest_safe_doc_is_substrate(self) -> None:
        from handlers.substrate_command_handler import is_substrate_command

        assert is_substrate_command("!ingest-safe-doc")

    def test_ingest_safe_doc_cu_is_substrate(self) -> None:
        from handlers.substrate_command_handler import is_substrate_command

        assert is_substrate_command("!ingest-safe-doc-cu")

    def test_commands_is_substrate(self) -> None:
        from handlers.substrate_command_handler import is_substrate_command

        assert is_substrate_command("!commands")

    def test_brief_is_not_substrate(self) -> None:
        from handlers.substrate_command_handler import is_substrate_command

        assert not is_substrate_command("!brief")

    def test_help_is_not_substrate(self) -> None:
        from handlers.substrate_command_handler import is_substrate_command

        assert not is_substrate_command("!help")

    def test_status_is_not_substrate(self) -> None:
        from handlers.substrate_command_handler import is_substrate_command

        assert not is_substrate_command("!status")

    def test_empty_is_not_substrate(self) -> None:
        from handlers.substrate_command_handler import is_substrate_command

        assert not is_substrate_command("")

    def test_plain_text_is_not_substrate(self) -> None:
        from handlers.substrate_command_handler import is_substrate_command

        assert not is_substrate_command("hello world")

    def test_substrate_commands_excludes_status(self) -> None:
        from handlers.substrate_command_handler import SUBSTRATE_COMMANDS

        assert "!status" not in SUBSTRATE_COMMANDS


# ── Command surface manifest ────────────────────────────────────────────────


class TestCommandSurfaceManifest:
    def test_manifest_has_substrate_commands(self) -> None:
        from handlers.substrate_command_handler import get_command_surface_manifest

        m = get_command_surface_manifest()
        assert "!chrome-proof" in m["substrate_commands"]
        assert "!ping" in m["substrate_commands"]

    def test_manifest_has_spine_routed(self) -> None:
        from handlers.substrate_command_handler import get_command_surface_manifest

        m = get_command_surface_manifest()
        assert "!chrome-proof" in m["spine_routed"]
        assert "!ingest-safe-doc" in m["spine_routed"]

    def test_manifest_has_action_map(self) -> None:
        from handlers.substrate_command_handler import get_command_surface_manifest

        m = get_command_surface_manifest()
        assert m["action_map"]["!chrome-proof"] == "chrome_proof"
        assert m["action_map"]["!ping"] == "ping"

    def test_manifest_has_contracts(self) -> None:
        from handlers.substrate_command_handler import get_command_surface_manifest

        m = get_command_surface_manifest()
        assert "!chrome-proof" in m["contracts"]
        contract = m["contracts"]["!chrome-proof"]
        assert contract["require_foreground_gui"] is True
        assert contract["require_screenshot_proof"] is True

    def test_manifest_has_surface_hash(self) -> None:
        from handlers.substrate_command_handler import get_command_surface_manifest

        m = get_command_surface_manifest()
        assert len(m["surface_hash"]) == 12

    def test_manifest_has_vps_commit(self) -> None:
        from handlers.substrate_command_handler import get_command_surface_manifest

        m = get_command_surface_manifest()
        assert len(m["vps_commit"]) > 0

    def test_manifest_has_timestamp(self) -> None:
        from handlers.substrate_command_handler import get_command_surface_manifest

        m = get_command_surface_manifest()
        assert "T" in m["timestamp"]

    def test_manifest_json_serializable(self) -> None:
        from handlers.substrate_command_handler import get_command_surface_manifest

        m = get_command_surface_manifest()
        serialized = json.dumps(m)
        assert len(serialized) > 0


# ── Command surface sync verification ───────────────────────────────────────


class TestCommandSurfaceSync:
    def test_sync_result_defaults(self) -> None:
        from core.runtime.command_surface_sync_v1 import CommandSurfaceSyncResult

        r = CommandSurfaceSyncResult()
        assert r.synced is False
        assert r.process_stale is False
        assert r.missing_commands == []
        assert r.errors == []

    def test_sync_result_auto_timestamp(self) -> None:
        from core.runtime.command_surface_sync_v1 import CommandSurfaceSyncResult

        r = CommandSurfaceSyncResult()
        assert "T" in r.timestamp

    def test_sync_result_to_dict(self) -> None:
        from core.runtime.command_surface_sync_v1 import CommandSurfaceSyncResult

        r = CommandSurfaceSyncResult(synced=True, vps_commit="abc123")
        d = r.to_dict()
        assert d["synced"] is True
        assert d["vps_commit"] == "abc123"

    def test_surface_hash_deterministic(self) -> None:
        from core.runtime.command_surface_sync_v1 import compute_surface_hash

        h1 = compute_surface_hash(["!ping", "!chrome"])
        h2 = compute_surface_hash(["!chrome", "!ping"])
        assert h1 == h2
        assert len(h1) == 12

    def test_surface_hash_changes_with_commands(self) -> None:
        from core.runtime.command_surface_sync_v1 import compute_surface_hash

        h1 = compute_surface_hash(["!ping"])
        h2 = compute_surface_hash(["!ping", "!chrome"])
        assert h1 != h2

    def test_verify_in_sync(self) -> None:
        from core.runtime.command_surface_sync_v1 import verify_command_surface

        cmds = {"!ping", "!chrome", "!chrome-proof"}
        result = verify_command_surface(
            source_commands=cmds,
            live_commands=cmds,
        )
        assert not result.missing_commands
        assert not result.extra_commands
        assert result.source_surface_hash == result.live_surface_hash

    def test_verify_missing_command(self) -> None:
        from core.runtime.command_surface_sync_v1 import verify_command_surface

        result = verify_command_surface(
            source_commands={"!ping", "!chrome-proof"},
            live_commands={"!ping"},
        )
        assert "!chrome-proof" in result.missing_commands
        assert not result.synced

    def test_verify_extra_command(self) -> None:
        from core.runtime.command_surface_sync_v1 import verify_command_surface

        result = verify_command_surface(
            source_commands={"!ping"},
            live_commands={"!ping", "!ghost"},
        )
        assert "!ghost" in result.extra_commands


class TestSyncProofPersistence:
    def test_persist_proof(self, tmp_path: Path) -> None:
        from core.runtime.command_surface_sync_v1 import (
            CommandSurfaceSyncResult,
            persist_sync_proof,
        )

        result = CommandSurfaceSyncResult(synced=True, vps_commit="abc123")
        path = persist_sync_proof(result, proof_dir=tmp_path)
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["synced"] is True
        assert data["vps_commit"] == "abc123"

    def test_persist_proof_naming(self, tmp_path: Path) -> None:
        from core.runtime.command_surface_sync_v1 import (
            CommandSurfaceSyncResult,
            persist_sync_proof,
        )

        result = CommandSurfaceSyncResult()
        path = persist_sync_proof(result, proof_dir=tmp_path)
        assert path.name.startswith("SYNC-")
        assert path.suffix == ".json"


# ── Live bot integration ────────────────────────────────────────────────────


class TestLiveBotIntegration:
    def test_bot_imports_substrate_handler(self) -> None:
        source = Path("/opt/OS/services/discord_bot.py").read_text()
        assert "from handlers.substrate_command_handler import" in source

    def test_bot_calls_is_substrate_command(self) -> None:
        source = Path("/opt/OS/services/discord_bot.py").read_text()
        assert "is_substrate_command(text)" in source

    def test_bot_calls_handle_substrate_command(self) -> None:
        source = Path("/opt/OS/services/discord_bot.py").read_text()
        assert "handle_substrate_command(message, text)" in source

    def test_substrate_before_inline(self) -> None:
        source = Path("/opt/OS/services/discord_bot.py").read_text()
        substrate_pos = source.index("is_substrate_command(text)")
        inline_pos = source.index("try_inline_commands(message")
        assert substrate_pos < inline_pos

    def test_no_merge_conflict_markers(self) -> None:
        source = Path("/opt/OS/services/discord_bot.py").read_text()
        assert "<<<<<<<" not in source
        assert "=======" not in source
        assert ">>>>>>>" not in source

    def test_bot_compiles(self) -> None:
        import py_compile

        py_compile.compile(
            "/opt/OS/services/discord_bot.py",
            doraise=True,
        )


# ── Spine routing correctness ───────────────────────────────────────────────


class TestSpineRouting:
    def test_chrome_proof_spine_routed(self) -> None:
        from eos_ai.interfaces.discord_interface_adapter_v1 import SPINE_ROUTED_COMMANDS

        assert "!chrome-proof" in SPINE_ROUTED_COMMANDS

    def test_ping_not_spine_routed(self) -> None:
        from eos_ai.interfaces.discord_interface_adapter_v1 import SPINE_ROUTED_COMMANDS

        assert "!ping" not in SPINE_ROUTED_COMMANDS

    def test_chrome_not_spine_routed(self) -> None:
        from eos_ai.interfaces.discord_interface_adapter_v1 import SPINE_ROUTED_COMMANDS

        assert "!chrome" not in SPINE_ROUTED_COMMANDS

    def test_ingest_safe_doc_spine_routed(self) -> None:
        from eos_ai.interfaces.discord_interface_adapter_v1 import SPINE_ROUTED_COMMANDS

        assert "!ingest-safe-doc" in SPINE_ROUTED_COMMANDS

    def test_ingest_safe_doc_cu_spine_routed(self) -> None:
        from eos_ai.interfaces.discord_interface_adapter_v1 import SPINE_ROUTED_COMMANDS

        assert "!ingest-safe-doc-cu" in SPINE_ROUTED_COMMANDS


# ── Interface adapter source parity ─────────────────────────────────────────


class TestSourceParity:
    def test_all_supported_are_substrate_or_status(self) -> None:
        from handlers.substrate_command_handler import SUBSTRATE_COMMANDS
        from eos_ai.interfaces.discord_interface_adapter_v1 import SUPPORTED_COMMANDS

        for cmd in SUPPORTED_COMMANDS:
            if cmd == "!status":
                continue
            assert cmd in SUBSTRATE_COMMANDS, f"{cmd} in SUPPORTED but not SUBSTRATE"

    def test_all_action_map_keys_are_substrate(self) -> None:
        from handlers.substrate_command_handler import SUBSTRATE_COMMANDS
        from eos_ai.interfaces.discord_interface_adapter_v1 import COMMAND_ACTION_MAP

        for cmd in COMMAND_ACTION_MAP:
            assert cmd in SUBSTRATE_COMMANDS, f"{cmd} in ACTION_MAP but not SUBSTRATE"

    def test_every_substrate_has_action_mapping(self) -> None:
        from handlers.substrate_command_handler import SUBSTRATE_COMMANDS
        from eos_ai.interfaces.discord_interface_adapter_v1 import COMMAND_ACTION_MAP

        for cmd in SUBSTRATE_COMMANDS:
            assert cmd in COMMAND_ACTION_MAP, f"{cmd} in SUBSTRATE but not ACTION_MAP"


# ── Regression: existing bot commands still work ─────────────────────────────


class TestRegressionExistingBotCommands:
    def test_brief_not_intercepted(self) -> None:
        from handlers.substrate_command_handler import is_substrate_command

        assert not is_substrate_command("!brief")

    def test_join_not_intercepted(self) -> None:
        from handlers.substrate_command_handler import is_substrate_command

        assert not is_substrate_command("!join")

    def test_leave_not_intercepted(self) -> None:
        from handlers.substrate_command_handler import is_substrate_command

        assert not is_substrate_command("!leave")

    def test_portfolio_not_intercepted(self) -> None:
        from handlers.substrate_command_handler import is_substrate_command

        assert not is_substrate_command("!portfolio")

    def test_say_not_intercepted(self) -> None:
        from handlers.substrate_command_handler import is_substrate_command

        assert not is_substrate_command("!say")

    def test_help_not_intercepted(self) -> None:
        from handlers.substrate_command_handler import is_substrate_command

        assert not is_substrate_command("!help")

    def test_setup_not_intercepted(self) -> None:
        from handlers.substrate_command_handler import is_substrate_command

        assert not is_substrate_command("!setup")

    def test_inbox_not_intercepted(self) -> None:
        from handlers.substrate_command_handler import is_substrate_command

        assert not is_substrate_command("!inbox")

    def test_drive_not_intercepted(self) -> None:
        from handlers.substrate_command_handler import is_substrate_command

        assert not is_substrate_command("!drive")

    def test_cal_not_intercepted(self) -> None:
        from handlers.substrate_command_handler import is_substrate_command

        assert not is_substrate_command("!cal")


# ── Regression: inline commands not intercepted ──────────────────────────────


class TestRegressionInlineCommands:
    def test_followup_not_intercepted(self) -> None:
        from handlers.substrate_command_handler import is_substrate_command

        assert not is_substrate_command("!followup")

    def test_travel_not_intercepted(self) -> None:
        from handlers.substrate_command_handler import is_substrate_command

        assert not is_substrate_command("!travel")

    def test_nomeetings_not_intercepted(self) -> None:
        from handlers.substrate_command_handler import is_substrate_command

        assert not is_substrate_command("!nomeetings")

    def test_documents_not_intercepted(self) -> None:
        from handlers.substrate_command_handler import is_substrate_command

        assert not is_substrate_command("!documents")

    def test_audit_not_intercepted(self) -> None:
        from handlers.substrate_command_handler import is_substrate_command

        assert not is_substrate_command("!audit")
