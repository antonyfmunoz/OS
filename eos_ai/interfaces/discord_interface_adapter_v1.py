"""Discord Interface Adapter v1.

Minimal Discord bot that bridges Discord commands to filesystem
work packets consumed by the Local Worker Runtime Daemon.

This is an INTERFACE adapter only. It does not orchestrate, plan,
reason, or make autonomous decisions. It translates Discord messages
into work packets and relays RuntimeProof results back.

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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, "/opt/OS")

import discord

from core.environment_bridge.windows_desktop_request_builder import (
    build_ping_request,
    build_w0_chrome_open_request,
)
from core.runtime.worker_runtime_contracts import ProofStatus


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

DEFAULT_CONFIG_PATH = "/opt/OS/config/discord_interface_adapter_v1.json"

SUPPORTED_COMMANDS = {"!ping", "!chrome", "!status"}


def load_config(config_path: str | Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    with open(config_path, encoding="utf-8-sig") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Work packet helpers
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


def format_proof_summary(proof: dict[str, Any] | None, command: str) -> str:
    """Format a RuntimeProof into a compact Discord reply."""
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
    """Minimal Discord interface adapter."""

    def __init__(self, config: dict[str, Any], base_dir: Path = Path("/opt/OS")) -> None:
        self.config = config
        self.base_dir = base_dir

        self.work_inbox = base_dir / config.get(
            "work_inbox", "data/runtime/local_worker_runtime/inbox"
        )
        self.proof_dir = base_dir / config.get("proof_dir", "data/runtime/runtime_proofs")
        self.state_dir = base_dir / config.get(
            "state_dir", "data/runtime/discord_interface_adapter"
        )
        self.poll_interval: float = config.get("poll_interval_seconds", 2)
        self.request_timeout: int = config.get("request_timeout_seconds", 60)

        self.allowed_channels: list[int] = [int(c) for c in config.get("allowed_channel_ids", [])]

        token_var = config.get("discord_token_env_var", "DISCORD_BOT_TOKEN")
        self.token: str = os.getenv(token_var, "")

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
            await message.channel.send(
                f"**status** -- adapter=running worker_inbox={self.work_inbox}"
            )
            return

        if command not in SUPPORTED_COMMANDS:
            await message.channel.send(
                f"**{command}** -- unsupported. Available: {', '.join(sorted(SUPPORTED_COMMANDS))}"
            )
            return

        packet = build_work_packet(command)
        if packet is None:
            await message.channel.send(f"**{command}** -- failed to build work packet")
            return

        request_id = packet.get("request_id", "unknown")
        _log(f"submitting packet: {request_id} for {command}")

        write_work_packet(packet, self.work_inbox)
        await message.channel.send(
            f"**{command}** -- submitted ({request_id}), waiting for proof..."
        )

        proof = await asyncio.to_thread(
            poll_for_proof,
            request_id,
            self.proof_dir,
            self.request_timeout,
            self.poll_interval,
        )

        summary = format_proof_summary(proof, command)
        await message.channel.send(summary)
        _log(
            f"replied: {command} request_id={request_id} status={proof.get('proof_status') if proof else 'timeout'}"
        )

    def _write_status(self, status: str) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        status_path = self.state_dir / "adapter_status.json"
        data = {
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "work_inbox": str(self.work_inbox),
            "proof_dir": str(self.proof_dir),
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
        _log("Discord Interface Adapter v1")
        _log(f"work_inbox: {self.work_inbox}")
        _log(f"proof_dir: {self.proof_dir}")
        _log(f"timeout: {self.request_timeout}s")
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
