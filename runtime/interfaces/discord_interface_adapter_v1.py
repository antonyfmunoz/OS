"""Discord Interface Adapter v1.

Minimal Discord bot that bridges Discord commands to the
ControlPlaneRouter via WorkPackets.

This is an INTERFACE adapter only. It does not orchestrate, plan,
reason, or make autonomous decisions. It translates Discord messages
into WorkPackets, submits them to the router, and formats the
RouterResult for Discord reply.

Supported commands:
  !ping    -- relay health check
  !chrome  -- launch Chrome via Windows relay (hardcoded safe URL)

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

import asyncio
import json
import os
import signal
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"

import discord

from core.control_plane_router.control_plane_router_v1 import (
    ControlPlaneRouterV1,
    load_config as load_router_config,
)
from core.control_plane_router.router_contracts import (
    RouterResult,
    RouterStatus,
    WorkPacket,
)
from core.environment_bridge.windows_desktop_request_builder import (
    build_ping_request,
    build_w0_chrome_open_request,
    build_w0_chrome_proof_request,
    build_w0_doc_extract_safe_test_doc_request,
    build_w0_doc_ingestion_candidate_request,
    build_w0_drive_safe_test_doc_request,
    build_w0_full_live_ingestion_request,
    build_w0_promote_safe_memory_candidate_request,
    build_w0_query_safe_memory_reference_request,
    build_w0_real_foreground_cu_ingestion_request,
)
from core.runtime.adapter_registry_contracts import AdapterRegistry
from core.runtime.worker_runtime_contracts import ProofStatus
from eos_ai.interfaces.discord_spine_integration_v1 import (
    SpineExecutionConfig,
    SpineRoutedResult,
    build_spine_infrastructure,
    execute_spine_command,
    format_spine_result,
)


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


def _log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"[{ts}] [discord-adapter] {msg}", flush=True)


def _log_error(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"[{ts}] [discord-adapter] ERROR: {msg}", flush=True)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DEFAULT_CONFIG_PATH = f"{_ROOT}/config/discord_interface_adapter_v1.json"

from core.registry.canonical_command_registry_v1 import get_canonical_registry


_REGISTRY = get_canonical_registry()

SUPPORTED_COMMANDS = _REGISTRY.commands | {"!status"}
COMMAND_ACTION_MAP: dict[str, str] = _REGISTRY.command_action_map
SPINE_ROUTED_COMMANDS = _REGISTRY.spine_routed_commands
COMMAND_CONTRACT: dict[str, dict[str, Any]] = _REGISTRY.command_contracts


def load_config(config_path: str | Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    with open(config_path, encoding="utf-8-sig") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# WorkPacket builders (interface → router)
# ---------------------------------------------------------------------------


def build_work_packet_for_router(
    command: str,
    safe_doc_url: str = "",
    safe_doc_title: str = "",
    extraction_reference_id: str = "",
    candidate_id: str = "",
    governance_review_id: str = "",
    query_scope: str = "",
    query_lookup_key: str = "",
) -> WorkPacket | None:
    """Build a WorkPacket from a Discord command for the router."""
    action_type = COMMAND_ACTION_MAP.get(command)
    if action_type is None:
        return None

    if command == "!ping":
        req = build_ping_request()
        payload = req.to_dict()
    elif command == "!chrome":
        req = build_w0_chrome_open_request()
        payload = req.to_dict()
    elif command == "!chrome-open-google-drive":
        req = build_w0_chrome_open_request()
        payload = req.to_dict()
    elif command == "!chrome-proof":
        req = build_w0_chrome_proof_request()
        payload = req.to_dict()
    elif command == "!doc":
        req = build_w0_drive_safe_test_doc_request(safe_doc_url=safe_doc_url)
        payload = req.to_dict()
    elif command == "!extract":
        req = build_w0_doc_extract_safe_test_doc_request(
            safe_doc_url=safe_doc_url,
            safe_doc_title=safe_doc_title or "EOS W0 Test Document",
        )
        payload = req.to_dict()
    elif command == "!ingest-safe-doc":
        req = build_w0_full_live_ingestion_request(
            safe_doc_url=safe_doc_url,
            safe_doc_title=safe_doc_title or "EOS W0 Test Document",
        )
        payload = req.to_dict()
    elif command == "!ingest-safe-doc-cu":
        req = build_w0_real_foreground_cu_ingestion_request(
            safe_doc_url=safe_doc_url,
            safe_doc_title=safe_doc_title or "EOS W0 Test Document",
        )
        payload = req.to_dict()
    elif command == "!ingest-candidate":
        req = build_w0_doc_ingestion_candidate_request(
            safe_doc_url=safe_doc_url,
            safe_doc_title=safe_doc_title or "EOS W0 Test Document",
            extraction_reference_id=extraction_reference_id,
        )
        payload = req.to_dict()
    elif command == "!promote-memory":
        req = build_w0_promote_safe_memory_candidate_request(
            candidate_id=candidate_id,
            governance_review_id=governance_review_id,
            safe_doc_url=safe_doc_url,
            safe_doc_title=safe_doc_title or "EOS W0 Test Document",
        )
        payload = req.to_dict()
    elif command == "!query-memory":
        req = build_w0_query_safe_memory_reference_request(
            query_scope=query_scope or "exact_memory_lookup",
            query_lookup_key=query_lookup_key,
        )
        payload = req.to_dict()
    else:
        return None

    return WorkPacket(
        packet_id=payload.get("request_id", f"PKT-{uuid.uuid4().hex[:8]}"),
        action_type=action_type,
        payload=payload,
        source_interface="discord_interface_adapter_v1",
        trace_id=payload.get("trace_id", ""),
    )


# ---------------------------------------------------------------------------
# Legacy helpers (retained for standalone/test use)
# ---------------------------------------------------------------------------


def build_work_packet(command: str) -> dict[str, Any] | None:
    """Build a filesystem work packet from a Discord command."""
    if command == "!ping":
        req = build_ping_request()
        return req.to_dict()
    if command == "!chrome":
        req = build_w0_chrome_open_request()
        return req.to_dict()
    return None


def write_work_packet(packet: dict[str, Any], inbox: Path) -> Path:
    """Write a work packet JSON to the daemon inbox."""
    inbox.mkdir(parents=True, exist_ok=True)
    request_id = packet.get("request_id", "unknown")
    filename = f"{request_id}.json"
    path = inbox / filename
    with open(path, "w") as f:
        json.dump(packet, f, indent=2)
    _log(f"packet written: {path.name}")
    return path


def poll_for_proof(
    request_id: str,
    proof_dir: Path,
    timeout_seconds: int = 60,
    poll_interval: float = 2.0,
) -> dict[str, Any] | None:
    """Poll proof directory for a proof matching the request_id."""
    deadline = time.time() + timeout_seconds
    _log(f"polling for proof: request_id={request_id} timeout={timeout_seconds}s")

    while time.time() < deadline:
        for proof_file in proof_dir.glob("PROOF-*.json"):
            try:
                with open(proof_file, encoding="utf-8-sig") as f:
                    data = json.load(f)
                if data.get("request_id") == request_id:
                    _log(f"proof found: {proof_file.name}")
                    return data
            except (json.JSONDecodeError, OSError):
                continue
        time.sleep(poll_interval)

    _log(f"proof timeout for {request_id}")
    return None


# ---------------------------------------------------------------------------
# RouterResult formatting (router → Discord reply)
# ---------------------------------------------------------------------------


def format_router_result(result: RouterResult, command: str) -> str:
    """Format a RouterResult into a compact Discord reply."""
    status = result.router_status.value

    if result.router_status == RouterStatus.TIMEOUT:
        return f"**{command}** -- timeout, no proof received. Is the daemon running?"

    if result.router_status == RouterStatus.INVALID_PACKET:
        return f"**{command}** -- rejected: {result.error_message}"

    if result.router_status in (RouterStatus.NO_ADAPTER, RouterStatus.REJECTED):
        return f"**{command}** -- {status}: {result.error_message}"

    lines = [f"**{command}** -- {status}"]

    if result.router_decision:
        lines.append(f"action: {result.router_decision.action_type}")
        lines.append(f"adapter: {result.adapter_selected}")
        lines.append(f"runtime: {result.runtime_target}")

    if result.runtime_proof_reference:
        ref = result.runtime_proof_reference
        if ref.adapter_status:
            lines.append(f"adapter_status: {ref.adapter_status}")
        if ref.request_id:
            lines.append(f"request_id: {ref.request_id}")

    if result.error_message:
        lines.append(f"error: {result.error_message}")

    return "\n".join(lines)


def format_proof_summary(proof: dict[str, Any] | None, command: str) -> str:
    """Format a RuntimeProof into a compact Discord reply (legacy)."""
    if proof is None:
        return f"**{command}** -- timeout, no proof received. Is the daemon running?"

    status = proof.get("proof_status", "unknown")
    adapter_status = proof.get("adapter_status", "unknown")
    adapter_id = proof.get("adapter_id", "unknown")
    request_id = proof.get("request_id", "unknown")
    action = proof.get("action_type", "unknown")

    lines = [
        f"**{command}** -- {status}",
        f"action: {action}",
        f"adapter: {adapter_id}",
        f"adapter_status: {adapter_status}",
        f"request_id: {request_id}",
    ]

    evidence = proof.get("evidence", {})
    if evidence.get("main_window_title"):
        lines.append(f"window: {evidence['main_window_title']}")

    notes = proof.get("notes", [])
    if notes:
        lines.append(f"notes: {notes[0]}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Discord bot
# ---------------------------------------------------------------------------


class DiscordInterfaceAdapter:
    """Thin Discord interface adapter that delegates to ControlPlaneRouterV1."""

    def __init__(self, config: dict[str, Any], base_dir: Path = Path(_ROOT)) -> None:
        self.config = config
        self.base_dir = base_dir

        self.state_dir = base_dir / config.get(
            "state_dir", "data/runtime/discord_interface_adapter"
        )

        self.allowed_channels: list[int] = [int(c) for c in config.get("allowed_channel_ids", [])]

        token_var = config.get("discord_token_env_var", "DISCORD_BOT_TOKEN")
        self.token: str = os.getenv(token_var, "")

        registry_path = base_dir / config.get(
            "adapter_registry_path",
            "data/registries/local_worker_adapter_registry_v1.json",
        )
        router_config_path = config.get("router_config_path", None)
        if router_config_path:
            r_config = load_router_config(router_config_path)
        else:
            r_config = load_router_config()

        r_config["default_timeout_seconds"] = config.get("request_timeout_seconds", 60)

        self.registry = AdapterRegistry.from_json_file(registry_path)
        self.router = ControlPlaneRouterV1(
            registry=self.registry,
            config=r_config,
            base_dir=base_dir,
        )

        spine_config = SpineExecutionConfig(
            queue_dir=Path(config.get("spine_queue_dir", "data/runtime/spine_dispatch_queue")),
            ledger_dir=Path(
                config.get("spine_ledger_dir", "data/runtime/transformation_ledger/spine")
            ),
            proof_dir=Path(config.get("spine_proof_dir", "data/runtime/spine_proofs")),
            gate_proof_dir=Path(
                config.get("spine_gate_proof_dir", "data/runtime/spine_gate_proofs")
            ),
            worker_id=config.get("spine_worker_id", "local-worker-01"),
            environment_id=config.get("spine_environment_id", "local_windows_desktop"),
        )
        self._spine = build_spine_infrastructure(spine_config, base_dir)

        intents = discord.Intents.default()
        intents.message_content = True
        self.client = discord.Client(intents=intents)

        self._setup_events()

    def _is_allowed_channel(self, channel_id: int) -> bool:
        if not self.allowed_channels:
            return True
        return channel_id in self.allowed_channels

    def _setup_events(self) -> None:
        @self.client.event
        async def on_ready() -> None:
            _log(f"connected as {self.client.user}")
            self._write_status("running")

        @self.client.event
        async def on_message(message: discord.Message) -> None:
            if message.author == self.client.user:
                return
            if not message.content.startswith("!"):
                return
            if not self._is_allowed_channel(message.channel.id):
                return

            command = message.content.strip().split()[0].lower()
            await self._handle_command(command, message)

    async def _handle_command(self, command: str, message: discord.Message) -> None:
        _log(f"command: {command} from {message.author} in #{message.channel}")

        if command == "!status":
            await message.channel.send(f"**status** -- adapter=running router=control_plane_v1")
            return

        if command not in SUPPORTED_COMMANDS:
            await message.channel.send(
                f"**{command}** -- unsupported. Available: {', '.join(sorted(SUPPORTED_COMMANDS))}"
            )
            return

        if command in SPINE_ROUTED_COMMANDS:
            await self._handle_spine_command(command, message)
            return

        work_packet = build_work_packet_for_router(command)
        if work_packet is None:
            await message.channel.send(f"**{command}** -- failed to build work packet")
            return

        _log(f"routing via control plane: {work_packet.packet_id} for {command}")
        await message.channel.send(
            f"**{command}** -- routing ({work_packet.packet_id}), waiting for proof..."
        )

        result = await asyncio.to_thread(self.router.route_work_packet, work_packet)

        summary = format_router_result(result, command)
        await message.channel.send(summary)
        _log(
            f"replied: {command} packet_id={work_packet.packet_id} "
            f"router_status={result.router_status.value}"
        )

    async def _handle_spine_command(self, command: str, message: discord.Message) -> None:
        """Route a command through the full governed execution spine."""
        _log(f"spine-routing: {command}")
        await message.channel.send(
            f"**{command}** -- spine routing (authority → gate → supervisor), waiting..."
        )

        result = await asyncio.to_thread(execute_spine_command, self._spine, command)

        summary = format_spine_result(result)
        await message.channel.send(summary)
        _log(f"spine replied: {command} succeeded={result.succeeded}")

    def _write_status(self, status: str) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        status_path = self.state_dir / "adapter_status.json"
        data = {
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "work_inbox": str(self.router.work_inbox),
            "proof_dir": str(self.router.proof_dir),
        }
        with open(status_path, "w") as f:
            json.dump(data, f, indent=2)

    def ensure_directories(self) -> None:
        for d in [
            self.state_dir,
            self.state_dir / "logs",
            self.state_dir / "processed",
            self.state_dir / "failed",
        ]:
            d.mkdir(parents=True, exist_ok=True)

    def run(self) -> None:
        if not self.token:
            _log_error("no Discord token found. Set the env var from config.")
            return
        self.ensure_directories()
        self._write_status("starting")
        _log("=" * 50)
        _log("Discord Interface Adapter v1 (routed)")
        _log(f"router: control_plane_v1")
        _log(f"router_inbox: {self.router.work_inbox}")
        _log(f"router_proof_dir: {self.router.proof_dir}")
        _log(f"router_timeout: {self.router.default_timeout}s")
        _log(f"allowed_channels: {self.allowed_channels or 'all'}")
        _log("=" * 50)
        self.client.run(self.token, log_handler=None)
        self._write_status("stopped")
        _log("adapter stopped")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Discord Interface Adapter v1")
    parser.add_argument("--config", type=str, default=DEFAULT_CONFIG_PATH)
    args = parser.parse_args()

    config = load_config(args.config)
    adapter = DiscordInterfaceAdapter(config)
    adapter.run()


if __name__ == "__main__":
    main()
