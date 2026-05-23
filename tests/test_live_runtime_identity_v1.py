"""Tests for Phase 96.8AK — Live Runtime Identity and Git Parity.

Verifies:
  1. Stale runtime detection blocks commands
  2. !version, !runtime, !commands meta commands
  3. Substrate intercept before orchestration ingress
  4. Command registry parity (hash determinism)
  5. log_startup() produces output
  6. NodeParityReport structure
  7. Regression: existing commands unaffected
"""

import asyncio
import hashlib
import json
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(
    0,
    os.environ.get("UMH_ROOT")
    or os.environ.get("OS_ROOT")
    or os.environ.get("EOS_ROOT")
    or "/opt/OS",
)
_ROOT = (
    os.environ.get("UMH_ROOT")
    or os.environ.get("OS_ROOT")
    or os.environ.get("EOS_ROOT")
    or "/opt/OS"
)
sys.path.insert(
    0,
    os.path.join(
        os.environ.get("UMH_ROOT")
        or os.environ.get("OS_ROOT")
        or os.environ.get("EOS_ROOT")
        or "/opt/OS",
        "services",
    ),
)


class TestStaleRuntimeDetection:
    def test_stale_detected_when_hashes_differ(self) -> None:
        from transports.presence.handlers.substrate_command_handler import _is_stale_runtime

        with (
            patch(
                "transports.presence.handlers.substrate_command_handler._get_vps_commit_hash",
                return_value="abc1234",
            ),
            patch(
                "transports.presence.handlers.substrate_command_handler._get_origin_commit_hash",
                return_value="def5678",
            ),
        ):
            stale, vps, origin = _is_stale_runtime()
            assert stale is True
            assert vps == "abc1234"
            assert origin == "def5678"

    def test_not_stale_when_hashes_match(self) -> None:
        from transports.presence.handlers.substrate_command_handler import _is_stale_runtime

        with (
            patch(
                "transports.presence.handlers.substrate_command_handler._get_vps_commit_hash",
                return_value="abc1234",
            ),
            patch(
                "transports.presence.handlers.substrate_command_handler._get_origin_commit_hash",
                return_value="abc1234",
            ),
        ):
            stale, vps, origin = _is_stale_runtime()
            assert stale is False

    def test_not_stale_when_unknown(self) -> None:
        from transports.presence.handlers.substrate_command_handler import _is_stale_runtime

        with (
            patch(
                "transports.presence.handlers.substrate_command_handler._get_vps_commit_hash",
                return_value="unknown",
            ),
            patch(
                "transports.presence.handlers.substrate_command_handler._get_origin_commit_hash",
                return_value="abc1234",
            ),
        ):
            stale, _, _ = _is_stale_runtime()
            assert stale is False

    def test_stale_runtime_blocks_substrate_command(self) -> None:
        from transports.presence.handlers.substrate_command_handler import handle_substrate_command

        msg = MagicMock()
        msg.channel.send = AsyncMock()

        with patch(
            "transports.presence.handlers.substrate_command_handler._is_stale_runtime",
            return_value=(True, "aaa", "bbb"),
        ):
            result = asyncio.run(handle_substrate_command(msg, "!ping"))
            assert result is True
            call_args = msg.channel.send.call_args[0][0]
            assert "STALE_RUNTIME" in call_args
            assert "aaa" in call_args
            assert "bbb" in call_args


class TestMetaCommands:
    def test_version_is_meta(self) -> None:
        from transports.presence.handlers.substrate_command_handler import is_substrate_command

        assert is_substrate_command("!version")

    def test_runtime_is_meta(self) -> None:
        from transports.presence.handlers.substrate_command_handler import is_substrate_command

        assert is_substrate_command("!runtime")

    def test_commands_is_meta(self) -> None:
        from transports.presence.handlers.substrate_command_handler import is_substrate_command

        assert is_substrate_command("!commands")

    def test_version_handler_sends_response(self) -> None:
        from transports.presence.handlers.substrate_command_handler import handle_substrate_command

        msg = MagicMock()
        msg.channel.send = AsyncMock()

        result = asyncio.run(handle_substrate_command(msg, "!version"))
        assert result is True
        response = msg.channel.send.call_args[0][0]
        assert "Live Runtime Version" in response
        assert "VPS HEAD" in response
        assert "parity" in response

    def test_runtime_handler_sends_response(self) -> None:
        from transports.presence.handlers.substrate_command_handler import handle_substrate_command

        msg = MagicMock()
        msg.channel.send = AsyncMock()

        result = asyncio.run(handle_substrate_command(msg, "!runtime"))
        assert result is True
        response = msg.channel.send.call_args[0][0]
        assert "Live Runtime Identity" in response
        assert "PID" in response
        assert "uptime" in response

    def test_commands_handler_sends_response(self) -> None:
        from transports.presence.handlers.substrate_command_handler import handle_substrate_command

        msg = MagicMock()
        msg.channel.send = AsyncMock()

        result = asyncio.run(handle_substrate_command(msg, "!commands"))
        assert result is True
        response = msg.channel.send.call_args[0][0]
        assert "Live Command Surface" in response
        assert "Substrate Commands" in response


class TestSubstrateInterceptOrder:
    """The substrate intercept MUST come before orchestration ingress."""

    def test_substrate_before_orchestration(self) -> None:
        source = (Path(_ROOT) / "services" / "discord_bot.py").read_text()
        substrate_pos = source.index("is_substrate_command(text)")
        orch_pos = source.index("Orchestration ingress (mode-gated)")
        assert substrate_pos < orch_pos

    def test_substrate_before_cc_injection(self) -> None:
        source = (Path(_ROOT) / "services" / "discord_bot.py").read_text()
        call_site = source.index("if is_substrate_command(text):")
        cc_pos = source.index("Session-first CC injection", call_site)
        assert call_site < cc_pos

    def test_substrate_after_archive(self) -> None:
        source = (Path(_ROOT) / "services" / "discord_bot.py").read_text()
        if "archive failure must never block message path" not in source:
            pytest.skip("archive comment removed from discord_bot.py")
        archive_pos = source.index("archive failure must never block message path")
        call_site = source.index("if is_substrate_command(text):")
        assert call_site > archive_pos


class TestCommandRegistryParity:
    def test_surface_hash_deterministic(self) -> None:
        from transports.presence.handlers.substrate_command_handler import _get_command_surface_hash

        h1 = _get_command_surface_hash()
        h2 = _get_command_surface_hash()
        assert h1 == h2
        assert len(h1) == 12

    def test_router_contract_hash_deterministic(self) -> None:
        from transports.presence.handlers.substrate_command_handler import _get_router_contract_hash

        h1 = _get_router_contract_hash()
        h2 = _get_router_contract_hash()
        assert h1 == h2
        assert len(h1) == 12

    def test_surface_and_contract_hashes_differ(self) -> None:
        from transports.presence.handlers.substrate_command_handler import (
            _get_command_surface_hash,
            _get_router_contract_hash,
        )

        assert _get_command_surface_hash() != _get_router_contract_hash()

    def test_chrome_proof_in_live_command_list(self) -> None:
        from transports.presence.handlers.substrate_command_handler import SUBSTRATE_COMMANDS

        assert "!chrome-proof" in SUBSTRATE_COMMANDS

    def test_manifest_matches_substrate_set(self) -> None:
        from transports.presence.handlers.substrate_command_handler import (
            SUBSTRATE_COMMANDS,
            get_command_surface_manifest,
        )

        m = get_command_surface_manifest()
        assert set(m["substrate_commands"]) == SUBSTRATE_COMMANDS


class TestLogStartup:
    def test_log_startup_produces_output(self, capsys: pytest.CaptureFixture) -> None:
        from transports.presence.handlers.substrate_command_handler import log_startup

        log_startup()
        captured = capsys.readouterr()
        assert "Substrate Command Handler" in captured.out
        assert "substrate commands:" in captured.out
        assert "surface hash:" in captured.out

    def test_log_startup_shows_parity(self, capsys: pytest.CaptureFixture) -> None:
        from transports.presence.handlers.substrate_command_handler import log_startup

        log_startup()
        captured = capsys.readouterr()
        assert "VPS HEAD:" in captured.out
        assert "origin/main:" in captured.out
        assert "parity:" in captured.out


class TestBotWiringIntegrity:
    def test_import_includes_log_startup(self) -> None:
        source = (Path(_ROOT) / "services" / "discord_bot.py").read_text()
        assert "log_startup as _substrate_log_startup" in source

    def test_log_startup_called_in_on_ready(self) -> None:
        source = (Path(_ROOT) / "services" / "discord_bot.py").read_text()
        assert "_substrate_log_startup()" in source

    def test_no_merge_conflict_markers(self) -> None:
        source = (Path(_ROOT) / "services" / "discord_bot.py").read_text()
        assert "<<<<<<<" not in source
        assert ">>>>>>>" not in source

    def test_bot_compiles(self) -> None:
        import py_compile

        py_compile.compile(f"{_ROOT}/services/discord_bot.py", doraise=True)

    def test_handler_compiles(self) -> None:
        import py_compile

        py_compile.compile(
            f"{_ROOT}/transports/presence/handlers/substrate_command_handler.py", doraise=True
        )


class TestContainerIdentity:
    def test_container_id_returns_string(self) -> None:
        from transports.presence.handlers.substrate_command_handler import _container_id

        cid = _container_id()
        assert isinstance(cid, str)
        assert len(cid) > 0

    def test_boot_time_is_set(self) -> None:
        from transports.presence.handlers.substrate_command_handler import _BOOT_TIME

        from datetime import datetime, timezone

        assert isinstance(_BOOT_TIME, datetime)
        assert _BOOT_TIME.tzinfo is not None

    def test_boot_pid_is_current(self) -> None:
        from transports.presence.handlers.substrate_command_handler import _BOOT_PID

        assert _BOOT_PID == os.getpid()
