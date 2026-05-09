"""Substrate command handler for the live Discord bot.

Intercepts UMH substrate commands (!chrome-proof, !ping, !chrome, etc.)
in on_message and routes them through the governed execution spine or
control plane router from discord_interface_adapter_v1.

This handler bridges the live bot (services/discord_bot.py) to the
spine infrastructure (eos_ai/interfaces/discord_interface_adapter_v1.py).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from eos_ai.interfaces.discord_interface_adapter_v1 import (
    COMMAND_ACTION_MAP,
    COMMAND_CONTRACT,
    SPINE_ROUTED_COMMANDS,
    SUPPORTED_COMMANDS,
    build_work_packet_for_router,
    format_router_result,
)
from eos_ai.interfaces.discord_spine_integration_v1 import (
    SpineExecutionConfig,
    build_spine_infrastructure,
    execute_spine_command,
    format_spine_result,
)
from core.control_plane_router.control_plane_router_v1 import (
    ControlPlaneRouterV1,
    load_config as load_router_config,
)
from core.runtime.adapter_registry_contracts import AdapterRegistry


def _log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"[{ts}] [substrate-handler] {msg}", flush=True)


SUBSTRATE_COMMANDS = frozenset(SUPPORTED_COMMANDS - {"!status"})

_spine = None
_router = None
_initialized = False


def _get_vps_commit_hash() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            cwd=_REPO_ROOT,
            timeout=5,
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


def _get_command_surface_hash() -> str:
    surface = sorted(SUPPORTED_COMMANDS)
    return hashlib.sha256(json.dumps(surface).encode()).hexdigest()[:12]


def _ensure_infrastructure() -> tuple[Any, Any]:
    global _spine, _router, _initialized
    if _initialized:
        return _spine, _router

    _log("initializing substrate infrastructure")

    base_dir = Path(_REPO_ROOT)

    registry_path = base_dir / "data/registries/local_worker_adapter_registry_v1.json"
    registry = AdapterRegistry.from_json_file(registry_path)
    r_config = load_router_config()
    _router = ControlPlaneRouterV1(
        registry=registry,
        config=r_config,
        base_dir=base_dir,
    )

    spine_config = SpineExecutionConfig()
    _spine = build_spine_infrastructure(spine_config, base_dir)

    _initialized = True
    _log(f"infrastructure ready — {len(SUBSTRATE_COMMANDS)} substrate commands")
    return _spine, _router


def is_substrate_command(text: str) -> bool:
    cmd = text.strip().split()[0].lower() if text.strip() else ""
    return cmd in SUBSTRATE_COMMANDS or cmd == "!commands"


async def handle_substrate_command(message: Any, text: str) -> bool:
    """Handle a substrate command. Returns True if handled."""
    cmd = text.strip().split()[0].lower() if text.strip() else ""

    if cmd == "!commands":
        await _handle_commands_list(message)
        return True

    if cmd not in SUBSTRATE_COMMANDS:
        return False

    spine, router = await asyncio.to_thread(_ensure_infrastructure)

    if cmd in SPINE_ROUTED_COMMANDS:
        await _handle_spine_command(cmd, message, spine)
    else:
        await _handle_router_command(cmd, message, router)

    return True


async def _handle_commands_list(message: Any) -> None:
    """!commands — show all live registered commands with status."""
    vps_hash = _get_vps_commit_hash()
    surface_hash = _get_command_surface_hash()

    lines = [
        f"**Live Command Surface** (VPS: `{vps_hash}`, surface: `{surface_hash}`)",
        "",
        "**Substrate Commands** (spine/router routed):",
    ]

    for cmd in sorted(SUBSTRATE_COMMANDS):
        action = COMMAND_ACTION_MAP.get(cmd, "?")
        route = "spine" if cmd in SPINE_ROUTED_COMMANDS else "router"
        contract = COMMAND_CONTRACT.get(cmd)
        flags = []
        if contract:
            if contract.get("require_foreground_gui") or contract.get("require_foreground_cu"):
                flags.append("FG")
            if contract.get("require_screenshot_proof"):
                flags.append("SS")
            if contract.get("mutation_allowed") is False:
                flags.append("RO")
        flag_str = f" [{','.join(flags)}]" if flags else ""
        lines.append(f"  `{cmd}` -> `{action}` ({route}){flag_str}")

    lines.append("")
    lines.append("**Bot Commands** (@bot.command):")
    lines.append("  `!brief` `!status` `!portfolio` `!join` `!leave` `!say` `!help` ...")
    lines.append("")
    lines.append("**Inline Commands** (cc_command_handler):")
    lines.append("  `!followup` `!travel` `!nomeetings` `!documents` `!audit` ...")

    await message.channel.send("\n".join(lines))
    _log(f"!commands replied — {len(SUBSTRATE_COMMANDS)} substrate commands listed")


async def _handle_spine_command(cmd: str, message: Any, spine: Any) -> None:
    _log(f"spine-routing: {cmd}")
    await message.channel.send(
        f"**{cmd}** -- spine routing (authority -> gate -> supervisor), waiting..."
    )
    result = await asyncio.to_thread(execute_spine_command, spine, cmd)
    summary = format_spine_result(result)
    await message.channel.send(summary)
    _log(f"spine replied: {cmd} succeeded={result.succeeded}")


async def _handle_router_command(cmd: str, message: Any, router: Any) -> None:
    work_packet = build_work_packet_for_router(cmd)
    if work_packet is None:
        await message.channel.send(f"**{cmd}** -- failed to build work packet")
        return

    _log(f"router-routing: {cmd} packet={work_packet.packet_id}")
    await message.channel.send(
        f"**{cmd}** -- routing ({work_packet.packet_id}), waiting for proof..."
    )

    result = await asyncio.to_thread(router.route_work_packet, work_packet)
    summary = format_router_result(result, cmd)
    await message.channel.send(summary)
    _log(f"router replied: {cmd} status={result.router_status.value}")


def get_command_surface_manifest() -> dict[str, Any]:
    """Return the live command surface manifest for sync verification."""
    return {
        "substrate_commands": sorted(SUBSTRATE_COMMANDS),
        "spine_routed": sorted(SPINE_ROUTED_COMMANDS),
        "action_map": dict(sorted(COMMAND_ACTION_MAP.items())),
        "contracts": {k: v for k, v in sorted(COMMAND_CONTRACT.items())},
        "surface_hash": _get_command_surface_hash(),
        "vps_commit": _get_vps_commit_hash(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
