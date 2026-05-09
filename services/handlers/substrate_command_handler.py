"""Substrate command handler for the live Discord bot.

Intercepts UMH substrate commands (!chrome-proof, !ping, !chrome, etc.)
in on_message and routes them through the governed execution spine or
control plane router from discord_interface_adapter_v1.

Also provides runtime identity commands (!version, !runtime, !commands)
that report live process metadata for parity verification.

This handler bridges the live bot (services/discord_bot.py) to the
spine infrastructure (eos_ai/interfaces/discord_interface_adapter_v1.py).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
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

META_COMMANDS = frozenset({"!commands", "!version", "!runtime"})

_spine = None
_router = None
_initialized = False

_BOOT_TIME = datetime.now(timezone.utc)
_BOOT_PID = os.getpid()


def _get_vps_commit_hash(short: bool = True) -> str:
    try:
        cmd = ["git", "rev-parse"]
        if short:
            cmd.append("--short")
        cmd.append("HEAD")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=_REPO_ROOT,
            timeout=5,
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


def _get_origin_commit_hash(short: bool = True) -> str:
    try:
        cmd = ["git", "rev-parse"]
        if short:
            cmd.append("--short")
        cmd.append("origin/main")
        result = subprocess.run(
            cmd,
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


def _get_router_contract_hash() -> str:
    action_map = dict(sorted(COMMAND_ACTION_MAP.items()))
    return hashlib.sha256(json.dumps(action_map).encode()).hexdigest()[:12]


def _file_hash(path: str) -> str:
    try:
        data = Path(path).read_bytes()
        return hashlib.sha256(data).hexdigest()[:12]
    except Exception:
        return "missing"


def _container_id() -> str:
    try:
        cgroup = Path("/proc/self/cgroup").read_text()
        for line in cgroup.splitlines():
            if "docker" in line or "containerd" in line:
                return line.rsplit("/", 1)[-1][:12]
    except Exception:
        pass
    hostname = platform.node()
    if len(hostname) == 12 and hostname.isalnum():
        return hostname
    return "not-container"


def _is_stale_runtime() -> tuple[bool, str, str]:
    vps = _get_vps_commit_hash()
    origin = _get_origin_commit_hash()
    if vps == "unknown" or origin == "unknown":
        return False, vps, origin
    return vps != origin, vps, origin


def _ensure_infrastructure() -> tuple[Any, Any]:
    global _spine, _router, _initialized
    if _initialized:
        return _spine, _router

    _log("initializing substrate infrastructure")

    base_dir = Path(_REPO_ROOT)

    registry_path = base_dir / "data/registries/local_worker_adapter_registry_v1.json"
    registry = AdapterRegistry.from_json_file(registry_path)
    r_config = load_router_config(base_dir / "config/control_plane_router_v1.json")
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
    return cmd in SUBSTRATE_COMMANDS or cmd in META_COMMANDS


async def handle_substrate_command(message: Any, text: str) -> bool:
    """Handle a substrate command. Returns True if handled."""
    cmd = text.strip().split()[0].lower() if text.strip() else ""

    if cmd == "!commands":
        await _handle_commands_list(message)
        return True

    if cmd == "!version":
        await _handle_version(message)
        return True

    if cmd == "!runtime":
        await _handle_runtime(message)
        return True

    if cmd not in SUBSTRATE_COMMANDS:
        return False

    stale, vps_hash, origin_hash = _is_stale_runtime()
    if stale:
        await message.channel.send(
            f"**{cmd}** -- STALE_RUNTIME\n"
            f"VPS HEAD: `{vps_hash}` != origin/main: `{origin_hash}`\n"
            f"Run `git pull` on VPS then `docker restart os-discord`"
        )
        return True

    spine, router = await asyncio.to_thread(_ensure_infrastructure)

    if cmd in SPINE_ROUTED_COMMANDS:
        await _handle_spine_command(cmd, message, spine)
    else:
        await _handle_router_command(cmd, message, router)

    return True


async def _handle_version(message: Any) -> None:
    vps_hash = _get_vps_commit_hash()
    origin_hash = _get_origin_commit_hash()
    surface_hash = _get_command_surface_hash()
    contract_hash = _get_router_contract_hash()
    stale = vps_hash != origin_hash and vps_hash != "unknown"

    lines = [
        f"**Live Runtime Version**",
        f"VPS HEAD: `{vps_hash}`",
        f"origin/main: `{origin_hash}`",
        f"parity: {'SYNCED' if not stale else 'STALE'}",
        f"command surface: `{surface_hash}`",
        f"router contracts: `{contract_hash}`",
        f"substrate handler: `{_file_hash(os.path.abspath(__file__))}`",
        f"bot source: `{_file_hash(os.path.join(_REPO_ROOT, 'services/discord_bot.py'))}`",
    ]
    await message.channel.send("\n".join(lines))
    _log(f"!version replied — VPS={vps_hash} origin={origin_hash}")


async def _handle_runtime(message: Any) -> None:
    uptime_s = (datetime.now(timezone.utc) - _BOOT_TIME).total_seconds()
    uptime_h = uptime_s / 3600

    lines = [
        f"**Live Runtime Identity**",
        f"PID: `{_BOOT_PID}`",
        f"boot: `{_BOOT_TIME.strftime('%Y-%m-%d %H:%M:%S UTC')}`",
        f"uptime: `{uptime_h:.1f}h`",
        f"hostname: `{platform.node()}`",
        f"container: `{_container_id()}`",
        f"cwd: `{os.getcwd()}`",
        f"python: `{sys.executable}`",
        f"python version: `{platform.python_version()}`",
        f"substrate handler: `active`",
        f"commands loaded: `{len(SUBSTRATE_COMMANDS)}` substrate + `{len(META_COMMANDS)}` meta",
        f"handler source: `{os.path.abspath(__file__)}`",
    ]
    await message.channel.send("\n".join(lines))
    _log(f"!runtime replied — PID={_BOOT_PID} uptime={uptime_h:.1f}h")


async def _handle_commands_list(message: Any) -> None:
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
    lines.append("**Meta Commands:**")
    lines.append("  `!commands` `!version` `!runtime`")
    lines.append("")
    lines.append("**Bot Commands** (@bot.command):")
    lines.append("  `!brief` `!status` `!portfolio` `!join` `!leave` `!say` `!help` ...")

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
    return {
        "substrate_commands": sorted(SUBSTRATE_COMMANDS),
        "meta_commands": sorted(META_COMMANDS),
        "spine_routed": sorted(SPINE_ROUTED_COMMANDS),
        "action_map": dict(sorted(COMMAND_ACTION_MAP.items())),
        "contracts": {k: v for k, v in sorted(COMMAND_CONTRACT.items())},
        "surface_hash": _get_command_surface_hash(),
        "contract_hash": _get_router_contract_hash(),
        "vps_commit": _get_vps_commit_hash(),
        "origin_commit": _get_origin_commit_hash(),
        "boot_time": _BOOT_TIME.isoformat(),
        "boot_pid": _BOOT_PID,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def log_startup() -> None:
    vps_hash = _get_vps_commit_hash()
    origin_hash = _get_origin_commit_hash()
    surface_hash = _get_command_surface_hash()
    stale = vps_hash != origin_hash and vps_hash != "unknown"

    _log("=" * 50)
    _log("Substrate Command Handler — ACTIVE")
    _log(f"VPS HEAD: {vps_hash}")
    _log(f"origin/main: {origin_hash}")
    _log(f"parity: {'SYNCED' if not stale else 'STALE — commands may be blocked'}")
    _log(f"substrate commands: {len(SUBSTRATE_COMMANDS)}")
    _log(f"meta commands: {len(META_COMMANDS)}")
    _log(f"surface hash: {surface_hash}")
    _log(f"handler source: {os.path.abspath(__file__)}")
    _log(f"PID: {_BOOT_PID}")
    _log(f"commands: {', '.join(sorted(SUBSTRATE_COMMANDS))}")
    _log("=" * 50)
