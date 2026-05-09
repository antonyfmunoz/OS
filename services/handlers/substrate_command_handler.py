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
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from core.registry.canonical_command_registry_v1 import get_canonical_registry
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

_CANONICAL = get_canonical_registry()


def _log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"[{ts}] [substrate-handler] {msg}", flush=True)


SUBSTRATE_COMMANDS = _CANONICAL.commands

META_COMMANDS = frozenset({"!commands", "!version", "!runtime"})

_spine = None
_router = None
_bootstrap = None
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
    global _spine, _router, _bootstrap, _initialized
    if _initialized:
        return _spine, _router

    _log("initializing substrate infrastructure")

    base_dir = Path(_REPO_ROOT)

    from core.runtime.runtime_bootstrap_state_v1 import RuntimeBootstrapStateV1

    _bootstrap = RuntimeBootstrapStateV1(base_dir)
    bv = _bootstrap.bootstrap(auto_heal=True)
    _log(
        f"bootstrap: {bv.stage.value} registry={bv.registry_hash} "
        f"healed={len(bv.auto_healed)} missing={len(bv.denial_reasons)}"
    )

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

    if cmd == "!relay-status":
        await _handle_relay_status(message)
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

    if cmd == "!chrome-proof":
        await _handle_chrome_proof(message, spine)
    elif cmd == "!ingest-safe-doc-cu":
        await _handle_ingest_safe_doc_cu(message, spine)
    elif cmd == "!explore-environment":
        await _handle_explore_environment(message, spine)
    elif cmd == "!adapter-report":
        await _handle_adapter_report(message, spine)
    elif cmd == "!capability-report":
        await _handle_capability_report(message, spine)
    elif cmd == "!orchestration-report":
        await _handle_orchestration_report(message, spine)
    elif cmd in SPINE_ROUTED_COMMANDS:
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

    bs_stage = _bootstrap.stage.value if _bootstrap else "not_initialized"
    bs_valid = _bootstrap.is_ready if _bootstrap else False
    bs_v = _bootstrap.validation if _bootstrap else None

    lines = [
        f"**Live Runtime Identity**",
        f"PID: `{_BOOT_PID}`",
        f"boot: `{_BOOT_TIME.strftime('%Y-%m-%d %H:%M:%S UTC')}`",
        f"uptime: `{uptime_h:.1f}h`",
        f"hostname: `{platform.node()}`",
        f"container: `{_container_id()}`",
        f"runtime_ready: `{bs_valid}`",
        f"bootstrap_state: `{bs_stage}`",
        f"registry_hash: `{_CANONICAL.registry_hash()}`",
        f"registry_count: `{len(_CANONICAL)}`",
        f"commands loaded: `{len(SUBSTRATE_COMMANDS)}` substrate + `{len(META_COMMANDS)}` meta",
    ]
    if bs_v and bs_v.auto_healed:
        lines.append(f"auto_healed: `{len(bs_v.auto_healed)}` dirs")
    if bs_v and bs_v.denial_reasons:
        lines.append(f"missing: `{', '.join(bs_v.denial_reasons)}`")
    await message.channel.send("\n".join(lines))
    _log(f"!runtime replied — PID={_BOOT_PID} uptime={uptime_h:.1f}h")


async def _handle_commands_list(message: Any) -> None:
    vps_hash = _get_vps_commit_hash()
    surface_hash = _get_command_surface_hash()

    lines = [
        f"**Live Command Surface** (VPS: `{vps_hash}`, surface: `{surface_hash}`, registry: `{_CANONICAL.registry_hash()}`)",
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


async def _handle_relay_status(message: Any) -> None:
    from core.workstation.workstation_node_registry_v1 import WorkstationNodeRegistry
    from core.workstation.workstation_relay_self_heal_v1 import assess_relay_health

    base = Path(_REPO_ROOT)
    registry = WorkstationNodeRegistry(base)
    status = registry.get_relay_status()
    heal = assess_relay_health(base)

    health_emoji = {
        "alive": "ONLINE",
        "degraded": "DEGRADED",
        "timeout": "STALE",
        "dead": "OFFLINE",
    }
    health_label = health_emoji.get(status.get("health", "dead"), "UNKNOWN")

    lines = [f"**!relay-status** -- {health_label}"]
    lines.append(f"online: `{status['online']}`")
    lines.append(f"health: `{status.get('health', 'dead')}`")

    if status.get("node_id"):
        lines.append(f"node_id: `{status['node_id']}`")
    if status.get("machine_name"):
        lines.append(f"machine: `{status['machine_name']}`")
    if status.get("user_name"):
        lines.append(f"user: `{status['user_name']}`")
    if status.get("relay_version"):
        lines.append(f"relay_version: `{status['relay_version']}`")
    if status.get("relay_pid"):
        lines.append(f"relay_pid: `{status['relay_pid']}`")

    lines.append(f"desktop_active: `{status.get('desktop_active', False)}`")
    lines.append(f"desktop_unlocked: `{status.get('desktop_unlocked', False)}`")
    lines.append(f"chrome_available: `{status.get('chrome_available', False)}`")
    lines.append(f"monitor_detected: `{status.get('monitor_detected', False)}`")

    lines.append(f"autostart: `{heal.autostart_installed}`")
    if heal.autostart_task_name:
        lines.append(f"autostart_task: `{heal.autostart_task_name}`")

    lines.append(f"maturity_ceiling: `{status.get('maturity_ceiling', 'L0_SIMULATED')}`")
    if status.get("maturity_ceiling_reason"):
        lines.append(f"ceiling_reason: `{status['maturity_ceiling_reason']}`")

    if heal.heartbeat_age_seconds >= 0:
        lines.append(f"heartbeat_age: `{heal.heartbeat_age_seconds:.0f}s`")
    lines.append(f"heartbeat_fresh: `{heal.heartbeat_fresh}`")
    lines.append(f"execution_allowed: `{heal.execution_allowed}`")
    if heal.denial_reason:
        lines.append(f"denial_reason: `{heal.denial_reason}`")

    if status.get("last_heartbeat"):
        lines.append(f"last_heartbeat: `{status['last_heartbeat']}`")
    elif status.get("reason"):
        lines.append(f"reason: `{status['reason']}`")

    if status.get("capabilities"):
        lines.append(f"capabilities: `{len(status['capabilities'])}`")

    # Registry hash parity
    relay_hash = status.get("registry_hash", "")
    vps_reg_hash = _CANONICAL.registry_hash()
    if relay_hash:
        parity = "MATCH" if relay_hash == vps_reg_hash else "MISMATCH"
        lines.append(f"registry_parity: `{parity}` (relay=`{relay_hash}` vps=`{vps_reg_hash}`)")
    else:
        lines.append(f"vps_registry: `{vps_reg_hash}`")

    # SSH transport check (non-blocking, short timeout)
    from core.workstation.relay_execution_transport_v1 import check_ssh_reachable

    ssh_ok, ssh_reason = await asyncio.to_thread(check_ssh_reachable)
    lines.append(f"ssh_transport: `{'LIVE' if ssh_ok else 'UNREACHABLE'}` ({ssh_reason})")

    await message.channel.send("\n".join(lines))
    _log(
        f"!relay-status replied — online={status['online']} "
        f"health={status.get('health')} autostart={heal.autostart_installed} "
        f"ssh={'ok' if ssh_ok else 'fail'}"
    )


async def _handle_chrome_proof(message: Any, spine: Any) -> None:
    from core.workstation.workstation_relay_self_heal_v1 import should_allow_chrome_proof
    from core.workstation.visible_actuation_proof_v1 import (
        FounderConfirmationArtifact,
        classify_visible_actuation,
        extract_evidence_from_relay_result,
        persist_founder_confirmation,
        persist_visible_actuation_proof,
    )
    from core.workstation.relay_execution_transport_v1 import (
        check_ssh_reachable,
        send_chrome_proof_request,
    )

    base = Path(_REPO_ROOT)

    # Gate 1: relay health (heartbeat, desktop, chrome)
    allowed, reason = should_allow_chrome_proof(base)
    if not allowed:
        await message.channel.send(
            f"**!chrome-proof** -- BLOCKED\nrelay gate: `{reason}`\nRun `!relay-status` for details"
        )
        _log(f"!chrome-proof blocked by relay gate: {reason}")
        return

    # Gate 2: SSH transport reachable
    ssh_ok, ssh_reason = await asyncio.to_thread(check_ssh_reachable)
    if not ssh_ok:
        await message.channel.send(
            f"**!chrome-proof** -- BLOCKED\n"
            f"transport: SSH unreachable (`{ssh_reason}`)\n"
            f"Windows workstation must be online via Tailscale"
        )
        _log(f"!chrome-proof blocked: SSH unreachable ({ssh_reason})")
        return

    await message.channel.send(
        "**!chrome-proof** -- relay healthy, transport live\n"
        "Dispatching real Chrome launch to Windows workstation..."
    )

    # Real execution via relay transport (no simulation)
    transport_result = await asyncio.to_thread(send_chrome_proof_request)

    if transport_result.status != "completed":
        await message.channel.send(
            f"**!chrome-proof** -- TRANSPORT FAILED\n"
            f"status: `{transport_result.status}`\n"
            f"error: `{transport_result.transport_error}`\n"
            f"ssh: `{transport_result.ssh_reachable}` "
            f"inbox: `{transport_result.inbox_written}` "
            f"result: `{transport_result.result_received}`"
        )
        _log(
            f"!chrome-proof transport failed: {transport_result.status} "
            f"error={transport_result.transport_error}"
        )
        return

    relay_data = transport_result.relay_result
    adapter_status = relay_data.get("adapter_status", "unknown")
    stages = relay_data.get("stages_completed", [])

    await message.channel.send(
        f"**!chrome-proof** -- relay executed\n"
        f"adapter: `{adapter_status}`\n"
        f"stages: `{', '.join(stages) if stages else 'none'}`\n"
        f"elapsed: `{transport_result.elapsed_seconds:.1f}s`"
    )
    _log(
        f"!chrome-proof relay completed: adapter={adapter_status} "
        f"elapsed={transport_result.elapsed_seconds:.1f}s"
    )

    # Extract evidence from real relay result
    evidence = extract_evidence_from_relay_result(relay_data, founder_confirmed=False)

    # Founder confirmation
    await message.channel.send(
        "**Founder confirmation required.**\n"
        "Did Chrome visibly open on the Windows desktop?\n"
        "Reply **YES** or **NO** within 60 seconds."
    )

    def check_response(m: Any) -> bool:
        return (
            m.author.id == message.author.id
            and m.channel.id == message.channel.id
            and m.content.strip().upper() in ("YES", "NO")
        )

    try:
        client = message.channel._state._get_client()
        response = await client.wait_for("message", check=check_response, timeout=60.0)
        founder_answer = response.content.strip().upper()
    except asyncio.TimeoutError:
        founder_answer = "TIMEOUT"
    except AttributeError:
        await message.channel.send("Could not access bot for confirmation — skipping.")
        founder_answer = "TIMEOUT"

    confirmed = founder_answer == "YES"

    confirmation = FounderConfirmationArtifact(
        confirmed=confirmed,
        trace_id=relay_data.get("trace_id", ""),
        request_id=transport_result.request_id,
        channel="discord",
        founder_response=founder_answer,
    )
    persist_founder_confirmation(confirmation, base_dir=base)

    # Classify visible actuation proof from real evidence
    evidence.founder_confirmed = confirmed
    proof = classify_visible_actuation(evidence)
    proof_path = persist_visible_actuation_proof(proof, base_dir=base)

    maturity_name = proof.maturity_level.name
    lines = [
        f"**!chrome-proof** -- PROOF CLASSIFIED",
        f"maturity: `{maturity_name}` (level {proof.maturity_level.value})",
        f"ceiling: `{proof.maturity_ceiling.name}`",
        f"escalation_blocked: `{proof.escalation_blocked}`",
    ]
    if proof.escalation_reason:
        lines.append(f"reason: `{proof.escalation_reason}`")
    lines.append(f"founder: `{founder_answer}`")
    lines.append(f"proof_id: `{proof.proof_id}`")
    lines.append(f"artifact: `{proof_path.name}`")
    lines.append(f"transport: `real_relay` ({transport_result.elapsed_seconds:.1f}s)")

    await message.channel.send("\n".join(lines))
    _log(
        f"!chrome-proof classified: maturity={maturity_name} "
        f"blocked={proof.escalation_blocked} founder={founder_answer} "
        f"transport=real_relay"
    )


async def _handle_ingest_safe_doc_cu(message: Any, spine: Any) -> None:
    from core.workstation.workstation_relay_self_heal_v1 import should_allow_chrome_proof
    from core.workstation.relay_execution_transport_v1 import check_ssh_reachable
    from core.workstation.foreground_cu_ingestion_execution_v1 import (
        build_full_ingestion_proof,
        extract_ingestion_evidence,
        persist_cu_ingestion_proof,
        send_ingest_safe_doc_request,
    )
    from core.workstation.visible_actuation_proof_v1 import (
        FounderConfirmationArtifact,
        persist_founder_confirmation,
    )

    base = Path(_REPO_ROOT)

    # Gate 1: relay health (heartbeat, desktop, chrome)
    allowed, reason = should_allow_chrome_proof(base)
    if not allowed:
        await message.channel.send(
            f"**!ingest-safe-doc-cu** -- BLOCKED\nrelay gate: `{reason}`\nRun `!relay-status` for details"
        )
        _log(f"!ingest-safe-doc-cu blocked by relay gate: {reason}")
        return

    # Gate 2: SSH transport reachable
    ssh_ok, ssh_reason = await asyncio.to_thread(check_ssh_reachable)
    if not ssh_ok:
        await message.channel.send(
            f"**!ingest-safe-doc-cu** -- BLOCKED\n"
            f"transport: SSH unreachable (`{ssh_reason}`)\n"
            f"Windows workstation must be online via Tailscale"
        )
        _log(f"!ingest-safe-doc-cu blocked: SSH unreachable ({ssh_reason})")
        return

    await message.channel.send(
        "**!ingest-safe-doc-cu** -- relay healthy, transport live\n"
        "Dispatching foreground CU ingestion to Windows workstation...\n"
        "Chrome will open to the safe test document."
    )

    # Real execution via relay transport
    transport_result = await asyncio.to_thread(send_ingest_safe_doc_request)

    if transport_result.status != "completed":
        await message.channel.send(
            f"**!ingest-safe-doc-cu** -- TRANSPORT FAILED\n"
            f"status: `{transport_result.status}`\n"
            f"error: `{transport_result.transport_error}`\n"
            f"ssh: `{transport_result.ssh_reachable}` "
            f"inbox: `{transport_result.inbox_written}` "
            f"result: `{transport_result.result_received}`"
        )
        _log(
            f"!ingest-safe-doc-cu transport failed: {transport_result.status} "
            f"error={transport_result.transport_error}"
        )
        return

    relay_data = transport_result.relay_result
    adapter_status = relay_data.get("adapter_status", "unknown")
    stages = relay_data.get("stages_completed", [])
    extraction = relay_data.get("extraction_result", {})
    extracted_len = extraction.get("content_length", 0)

    await message.channel.send(
        f"**!ingest-safe-doc-cu** -- relay executed\n"
        f"adapter: `{adapter_status}`\n"
        f"stages: `{', '.join(stages) if stages else 'none'}`\n"
        f"extraction: `{extracted_len} chars` "
        f"method=`{extraction.get('method', 'unknown')}`\n"
        f"elapsed: `{transport_result.elapsed_seconds:.1f}s`"
    )
    _log(
        f"!ingest-safe-doc-cu relay completed: adapter={adapter_status} "
        f"extraction={extracted_len}chars elapsed={transport_result.elapsed_seconds:.1f}s"
    )

    # Founder confirmation
    await message.channel.send(
        "**Founder confirmation required.**\n"
        "Did Chrome visibly open to the document and was content extracted?\n"
        "Reply **YES** or **NO** within 60 seconds."
    )

    def check_response(m: Any) -> bool:
        return (
            m.author.id == message.author.id
            and m.channel.id == message.channel.id
            and m.content.strip().upper() in ("YES", "NO")
        )

    try:
        client = message.channel._state._get_client()
        response = await client.wait_for("message", check=check_response, timeout=60.0)
        founder_answer = response.content.strip().upper()
    except asyncio.TimeoutError:
        founder_answer = "TIMEOUT"
    except AttributeError:
        await message.channel.send("Could not access bot for confirmation — skipping.")
        founder_answer = "TIMEOUT"

    confirmed = founder_answer == "YES"

    confirmation = FounderConfirmationArtifact(
        confirmed=confirmed,
        trace_id=relay_data.get("trace_id", ""),
        request_id=transport_result.request_id,
        channel="discord",
        founder_response=founder_answer,
    )
    persist_founder_confirmation(confirmation, base_dir=base)

    # Build full ingestion proof with candidate generation
    proof = build_full_ingestion_proof(relay_data, founder_confirmed=confirmed)
    proof_path = persist_cu_ingestion_proof(proof, base_dir=base)

    maturity_name = proof.maturity_level.name
    lines = [
        f"**!ingest-safe-doc-cu** -- PROOF CLASSIFIED",
        f"maturity: `{maturity_name}` (level {proof.maturity_level.value})",
        f"ceiling: `{proof.maturity_ceiling.name}`",
        f"escalation_blocked: `{proof.escalation_blocked}`",
    ]
    if proof.escalation_reason:
        lines.append(f"reason: `{proof.escalation_reason}`")
    lines.append(f"founder: `{founder_answer}`")
    lines.append(
        f"candidates: `{len(proof.candidates)}` "
        f"(canonical={proof.canonical_count}, instance={proof.instance_count})"
    )
    lines.append(f"proof_id: `{proof.proof_id}`")
    lines.append(f"artifact: `{proof_path.name}`")
    lines.append(f"transport: `real_relay` ({transport_result.elapsed_seconds:.1f}s)")

    await message.channel.send("\n".join(lines))
    _log(
        f"!ingest-safe-doc-cu classified: maturity={maturity_name} "
        f"blocked={proof.escalation_blocked} founder={founder_answer} "
        f"candidates={len(proof.candidates)} transport=real_relay"
    )


async def _handle_explore_environment(message: Any, spine: Any) -> None:
    from core.workstation.workstation_relay_self_heal_v1 import should_allow_chrome_proof
    from core.workstation.relay_execution_transport_v1 import check_ssh_reachable
    from core.workstation.environment_mapping_engine_v1 import (
        build_full_environment_proof,
        persist_environment_mapping_proof,
        send_explore_environment_request,
    )
    from core.workstation.visible_actuation_proof_v1 import (
        FounderConfirmationArtifact,
        persist_founder_confirmation,
    )

    base = Path(_REPO_ROOT)

    allowed, reason = should_allow_chrome_proof(base)
    if not allowed:
        await message.channel.send(
            f"**!explore-environment** -- BLOCKED\nrelay gate: `{reason}`\nRun `!relay-status` for details"
        )
        _log(f"!explore-environment blocked by relay gate: {reason}")
        return

    ssh_ok, ssh_reason = await asyncio.to_thread(check_ssh_reachable)
    if not ssh_ok:
        await message.channel.send(
            f"**!explore-environment** -- BLOCKED\n"
            f"transport: SSH unreachable (`{ssh_reason}`)\n"
            f"Windows workstation must be online via Tailscale"
        )
        _log(f"!explore-environment blocked: SSH unreachable ({ssh_reason})")
        return

    await message.channel.send(
        "**!explore-environment** -- relay healthy, transport live\n"
        "Dispatching environment exploration to Windows workstation...\n"
        "Enumerating processes, apps, Chrome profiles, browser sessions, workspaces."
    )

    transport_result = await asyncio.to_thread(send_explore_environment_request)

    if transport_result.status != "completed":
        await message.channel.send(
            f"**!explore-environment** -- TRANSPORT FAILED\n"
            f"status: `{transport_result.status}`\n"
            f"error: `{transport_result.transport_error}`"
        )
        _log(f"!explore-environment transport failed: {transport_result.status}")
        return

    relay_data = transport_result.relay_result
    adapter_status = relay_data.get("adapter_status", "unknown")
    stages = relay_data.get("stages_completed", [])
    discovery = relay_data.get("discovery_result", {})

    proc_count = len(discovery.get("processes", []))
    app_count = len(discovery.get("installed_apps", []))
    profile_count = len(discovery.get("chrome_profiles", []))
    session_count = len(discovery.get("browser_sessions", []))
    ws_count = len(discovery.get("workspaces", []))

    await message.channel.send(
        f"**!explore-environment** -- relay executed\n"
        f"adapter: `{adapter_status}`\n"
        f"stages: `{', '.join(stages) if stages else 'none'}`\n"
        f"processes: `{proc_count}` | apps: `{app_count}` | "
        f"profiles: `{profile_count}` | sessions: `{session_count}` | "
        f"workspaces: `{ws_count}`\n"
        f"elapsed: `{transport_result.elapsed_seconds:.1f}s`"
    )

    await message.channel.send(
        "**Founder confirmation required.**\n"
        "Did the environment exploration complete successfully on the workstation?\n"
        "Reply **YES** or **NO** within 60 seconds."
    )

    def check_response(m: Any) -> bool:
        return (
            m.author.id == message.author.id
            and m.channel.id == message.channel.id
            and m.content.strip().upper() in ("YES", "NO")
        )

    try:
        client = message.channel._state._get_client()
        response = await client.wait_for("message", check=check_response, timeout=60.0)
        founder_answer = response.content.strip().upper()
    except asyncio.TimeoutError:
        founder_answer = "TIMEOUT"
    except AttributeError:
        await message.channel.send("Could not access bot for confirmation — skipping.")
        founder_answer = "TIMEOUT"

    confirmed = founder_answer == "YES"

    confirmation = FounderConfirmationArtifact(
        confirmed=confirmed,
        trace_id=relay_data.get("trace_id", ""),
        request_id=transport_result.request_id,
        channel="discord",
        founder_response=founder_answer,
    )
    persist_founder_confirmation(confirmation, base_dir=base)

    proof = build_full_environment_proof(relay_data, founder_confirmed=confirmed)
    proof_path = persist_environment_mapping_proof(proof, base_dir=base)

    topo = proof.topology
    lines = [
        f"**!explore-environment** -- PROOF CLASSIFIED",
        f"maturity: `{proof.maturity_level}`",
        f"ceiling: `{proof.maturity_ceiling}`",
        f"escalation_blocked: `{proof.escalation_blocked}`",
    ]
    if proof.escalation_reason:
        lines.append(f"reason: `{proof.escalation_reason}`")
    lines.append(f"founder: `{founder_answer}`")
    if topo:
        lines.append(
            f"topology: platforms=`{topo.platform_count}` accounts=`{topo.account_count}` "
            f"workspaces=`{topo.workspace_count}` relationships=`{topo.relationship_count}` "
            f"lanes=`{topo.lane_count}`"
        )
        lines.append(
            f"separation: canonical=`{len(topo.canonical_candidates)}` "
            f"instance=`{len(topo.instance_candidates)}`"
        )
    lines.append(f"proof_id: `{proof.proof_id}`")
    lines.append(f"artifact: `{proof_path.name}`")
    lines.append(f"transport: `real_relay` ({transport_result.elapsed_seconds:.1f}s)")

    await message.channel.send("\n".join(lines))
    _log(
        f"!explore-environment classified: maturity={proof.maturity_level} "
        f"blocked={proof.escalation_blocked} founder={founder_answer} "
        f"transport=real_relay"
    )


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
        "registry_hash": _CANONICAL.registry_hash(),
        "vps_commit": _get_vps_commit_hash(),
        "origin_commit": _get_origin_commit_hash(),
        "boot_time": _BOOT_TIME.isoformat(),
        "boot_pid": _BOOT_PID,
        "bootstrap_ready": _bootstrap.is_ready if _bootstrap else False,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


async def _handle_adapter_report(message: Any, spine: Any) -> None:
    from core.workstation.adapter_autogeneration_engine_v1 import (
        build_full_adapter_proof,
        persist_adapter_proof,
        persist_blueprints,
        ADAPTER_TARGET_PLATFORMS,
    )
    from core.workstation.environment_mapping_engine_v1 import (
        ENVIRONMENT_MAP_DIR,
        EnvironmentMappingProof,
        EnvironmentTopology,
        build_environment_topology,
    )
    from core.workstation.visible_actuation_proof_v1 import (
        FounderConfirmationArtifact,
        persist_founder_confirmation,
    )

    base = Path(_REPO_ROOT)

    env_map_dir = base / ENVIRONMENT_MAP_DIR
    env_proof = None
    topology = None

    if env_map_dir.exists():
        proof_files = sorted(env_map_dir.glob("ENVMAP-*.json"), reverse=True)
        if proof_files:
            try:
                with open(proof_files[0], encoding="utf-8-sig") as f:
                    proof_data = json.load(f)
                topo_data = proof_data.get("topology")
                if topo_data:
                    from core.workstation.environment_mapping_engine_v1 import (
                        DiscoveredPlatform,
                        DiscoveredAccount,
                        DiscoveredWorkspace,
                        RelationshipEdge,
                        IngestionLane,
                        EnvironmentMappingEvidence,
                    )
                    from core.actuation.actuator_maturity_v1 import ActuatorMaturityLevel

                    platforms = [
                        DiscoveredPlatform(
                            **{
                                k: v
                                for k, v in p.items()
                                if k in DiscoveredPlatform.__dataclass_fields__
                            }
                        )
                        for p in topo_data.get("platforms", [])
                    ]
                    topology = EnvironmentTopology(
                        topology_id=topo_data.get("topology_id", ""),
                        platforms=platforms,
                    )

                evidence_data = proof_data.get("evidence", {})
                env_evidence = (
                    EnvironmentMappingEvidence(
                        **{
                            k: v
                            for k, v in evidence_data.items()
                            if k in EnvironmentMappingEvidence.__dataclass_fields__
                        }
                    )
                    if evidence_data
                    else None
                )

                env_proof = EnvironmentMappingProof(
                    proof_id=proof_data.get("proof_id", ""),
                    maturity_level=proof_data.get("maturity_level", "L0_NO_MAPPING"),
                    evidence=env_evidence,
                    topology=topology,
                )
                _log(f"!adapter-report loaded env proof: {proof_files[0].name}")
            except (json.JSONDecodeError, OSError, TypeError) as e:
                _log(f"!adapter-report env proof load failed: {e}")

    has_env = env_proof is not None and env_proof.maturity_level != "L0_NO_MAPPING"
    env_label = env_proof.maturity_level if env_proof else "none"

    await message.channel.send(
        f"**!adapter-report** -- analyzing topology\n"
        f"environment proof: `{env_label}`\n"
        f"target platforms: `{len(ADAPTER_TARGET_PLATFORMS)}`\n"
        f"Generating adapter blueprints..."
    )

    trace_id = f"W0-adapter-report-{uuid.uuid4().hex[:8]}"
    request_id = f"REQ-W0-ADAPTER-RPT-{uuid.uuid4().hex[:8]}"

    proof = build_full_adapter_proof(
        topology=topology,
        env_proof=env_proof,
        founder_confirmed=False,
        is_dry_run=False,
        trace_id=trace_id,
        request_id=request_id,
    )

    bp_count = len(proof.blueprints)
    detected = sum(1 for bp in proof.blueprints if bp.detected_on_workstation)
    cu_required = sum(1 for bp in proof.blueprints if bp.requires_cu)
    local_only = sum(1 for bp in proof.blueprints if not bp.requires_cu)

    eval_result = proof.maturity_evaluation
    missing_str = (
        ", ".join(eval_result.missing_evidence)
        if eval_result and eval_result.missing_evidence
        else "none"
    )
    risk_str = (
        ", ".join(eval_result.execution_risks[:3])
        if eval_result and eval_result.execution_risks
        else "none"
    )

    await message.channel.send(
        f"**!adapter-report** -- blueprints generated\n"
        f"blueprints: `{bp_count}` | detected: `{detected}` | "
        f"CU required: `{cu_required}` | local only: `{local_only}`\n"
        f"maturity: `{proof.maturity_level}` | ceiling: `{proof.maturity_ceiling}`\n"
        f"strategy: `{proof.execution_strategy}`\n"
        f"missing: `{missing_str}`\n"
        f"risks: `{risk_str}`"
    )

    await message.channel.send(
        "**Founder confirmation required.**\n"
        "Approve adapter blueprint generation?\n"
        "Reply **YES** or **NO** within 60 seconds."
    )

    def check_response(m: Any) -> bool:
        return (
            m.author.id == message.author.id
            and m.channel.id == message.channel.id
            and m.content.strip().upper() in ("YES", "NO")
        )

    try:
        client = message.channel._state._get_client()
        response = await client.wait_for("message", check=check_response, timeout=60.0)
        founder_answer = response.content.strip().upper()
    except asyncio.TimeoutError:
        founder_answer = "TIMEOUT"
    except AttributeError:
        await message.channel.send("Could not access bot for confirmation — skipping.")
        founder_answer = "TIMEOUT"

    confirmed = founder_answer == "YES"

    confirmation = FounderConfirmationArtifact(
        confirmed=confirmed,
        trace_id=trace_id,
        request_id=request_id,
        channel="discord",
        founder_response=founder_answer,
    )
    persist_founder_confirmation(confirmation, base_dir=base)

    proof_final = build_full_adapter_proof(
        topology=topology,
        env_proof=env_proof,
        founder_confirmed=confirmed,
        is_dry_run=False,
        trace_id=trace_id,
        request_id=request_id,
    )

    proof_path = persist_adapter_proof(proof_final, base_dir=base)
    bp_dir = persist_blueprints(proof_final.blueprints, base_dir=base)

    canonical_bps = sum(1 for bp in proof_final.blueprints if bp.canonical_likelihood > 0.4)
    instance_bps = len(proof_final.blueprints) - canonical_bps
    replay_count = sum(
        1 for bp in proof_final.blueprints if bp.replay_contract and bp.replay_contract.replayable
    )
    gov_count = sum(1 for bp in proof_final.blueprints if bp.governance is not None)

    lines = [
        f"**!adapter-report** -- PROOF CLASSIFIED",
        f"maturity: `{proof_final.maturity_level}`",
        f"ceiling: `{proof_final.maturity_ceiling}`",
        f"escalation_blocked: `{proof_final.escalation_blocked}`",
    ]
    if proof_final.escalation_reason:
        lines.append(f"reason: `{proof_final.escalation_reason}`")
    lines.append(f"founder: `{founder_answer}`")
    lines.append(f"blueprints: `{len(proof_final.blueprints)}`")
    lines.append(f"replay contracts: `{replay_count}`")
    lines.append(f"governance: `{gov_count}`")
    lines.append(f"canonical patterns: `{canonical_bps}`")
    lines.append(f"instance scoped: `{instance_bps}`")
    lines.append(f"strategy: `{proof_final.execution_strategy}`")
    lines.append(f"proof: `{proof_path.name}`")

    await message.channel.send("\n".join(lines))
    _log(
        f"!adapter-report completed: maturity={proof_final.maturity_level} "
        f"blueprints={len(proof_final.blueprints)} founder={founder_answer}"
    )


async def _handle_capability_report(message: Any, spine: Any) -> None:
    from core.workstation.recursive_capability_planning_engine_v1 import (
        build_full_capability_proof,
        persist_capability_proof,
        SUBSTRATE_CAPABILITIES,
        BOTTLENECK_CATEGORIES,
    )
    from core.workstation.adapter_autogeneration_engine_v1 import (
        AdapterAutogenProof,
        AdapterAutogenEvidence,
    )
    from core.workstation.environment_mapping_engine_v1 import (
        ENVIRONMENT_MAP_DIR,
        EnvironmentMappingProof,
        EnvironmentTopology,
        EnvironmentMappingEvidence,
        DiscoveredPlatform,
    )
    from core.workstation.visible_actuation_proof_v1 import (
        FounderConfirmationArtifact,
        persist_founder_confirmation,
    )

    base = Path(_REPO_ROOT)
    trace_id = f"W0-capability-report-{uuid.uuid4().hex[:8]}"
    request_id = f"REQ-W0-CAP-RPT-{uuid.uuid4().hex[:8]}"

    await message.channel.send(
        f"**!capability-report** -- analyzing substrate\n"
        f"capabilities: `{len(SUBSTRATE_CAPABILITIES)}`\n"
        f"bottleneck categories: `{len(BOTTLENECK_CATEGORIES)}`\n"
        f"Loading proofs and building capability graph..."
    )

    env_proof = None
    env_map_dir = base / ENVIRONMENT_MAP_DIR
    if env_map_dir.exists():
        proof_files = sorted(env_map_dir.glob("ENVMAP-*.json"), reverse=True)
        if proof_files:
            try:
                with open(proof_files[0], encoding="utf-8-sig") as f:
                    proof_data = json.load(f)
                topo_data = proof_data.get("topology")
                topology = None
                if topo_data:
                    platforms = [
                        DiscoveredPlatform(
                            **{
                                k: v
                                for k, v in p.items()
                                if k in DiscoveredPlatform.__dataclass_fields__
                            }
                        )
                        for p in topo_data.get("platforms", [])
                    ]
                    topology = EnvironmentTopology(
                        topology_id=topo_data.get("topology_id", ""),
                        platforms=platforms,
                    )
                evidence_data = proof_data.get("evidence", {})
                env_evidence = (
                    EnvironmentMappingEvidence(
                        **{
                            k: v
                            for k, v in evidence_data.items()
                            if k in EnvironmentMappingEvidence.__dataclass_fields__
                        }
                    )
                    if evidence_data
                    else None
                )
                env_proof = EnvironmentMappingProof(
                    proof_id=proof_data.get("proof_id", ""),
                    maturity_level=proof_data.get("maturity_level", "L0_NO_MAPPING"),
                    evidence=env_evidence,
                    topology=topology,
                )
            except (json.JSONDecodeError, OSError, TypeError):
                pass

    adapter_proof = None
    adapter_dir = base / "data/runtime/workstation_relay/adapter_reports"
    if adapter_dir.exists():
        adapter_files = sorted(adapter_dir.glob("ADPTGEN-*.json"), reverse=True)
        if adapter_files:
            try:
                with open(adapter_files[0], encoding="utf-8-sig") as f:
                    adapter_data = json.load(f)
                ev_data = adapter_data.get("evidence", {})
                adapter_evidence = (
                    AdapterAutogenEvidence(
                        **{
                            k: v
                            for k, v in ev_data.items()
                            if k in AdapterAutogenEvidence.__dataclass_fields__
                        }
                    )
                    if ev_data
                    else None
                )
                adapter_proof = AdapterAutogenProof(
                    proof_id=adapter_data.get("proof_id", ""),
                    maturity_level=adapter_data.get("maturity_level", "L0_SIMULATED"),
                    evidence=adapter_evidence,
                )
            except (json.JSONDecodeError, OSError, TypeError):
                pass

    proof = build_full_capability_proof(
        env_proof=env_proof,
        adapter_proof=adapter_proof,
        founder_confirmed=False,
        is_dry_run=False,
        trace_id=trace_id,
        request_id=request_id,
    )

    graph = proof.capability_graph
    bottleneck_count = len(proof.bottlenecks)
    proposal_count = len(proof.upgrade_proposals)
    top_proposal = proof.upgrade_proposals[0] if proof.upgrade_proposals else None

    lines = [
        f"**!capability-report** -- analysis complete",
        f"capabilities: `{len(graph.nodes)}` | "
        f"proven: `{graph.proven_count}` | missing: `{graph.missing_count}`",
        f"bottlenecks: `{bottleneck_count}`",
        f"upgrade proposals: `{proposal_count}`",
    ]
    if top_proposal:
        lines.append(
            f"top proposal: `{top_proposal.proposal_id}` "
            f"(leverage: `{top_proposal.leverage_score.composite_score:.3f}`)"
        )
    lines.append(f"maturity: `{proof.maturity_level}` | ceiling: `{proof.maturity_ceiling}`")
    lines.append(f"strategy: `{proof.execution_strategy}`")

    await message.channel.send("\n".join(lines))

    await message.channel.send(
        "**Founder confirmation required.**\n"
        "Approve capability planning proof generation?\n"
        "Reply **YES** or **NO** within 60 seconds."
    )

    def check_response(m: Any) -> bool:
        return (
            m.author.id == message.author.id
            and m.channel.id == message.channel.id
            and m.content.strip().upper() in ("YES", "NO")
        )

    try:
        client = message.channel._state._get_client()
        response = await client.wait_for("message", check=check_response, timeout=60.0)
        founder_answer = response.content.strip().upper()
    except asyncio.TimeoutError:
        founder_answer = "TIMEOUT"
    except AttributeError:
        await message.channel.send("Could not access bot for confirmation — skipping.")
        founder_answer = "TIMEOUT"

    confirmed = founder_answer == "YES"

    confirmation = FounderConfirmationArtifact(
        confirmed=confirmed,
        trace_id=trace_id,
        request_id=request_id,
        channel="discord",
        founder_response=founder_answer,
    )
    persist_founder_confirmation(confirmation, base_dir=base)

    proof_final = build_full_capability_proof(
        env_proof=env_proof,
        adapter_proof=adapter_proof,
        founder_confirmed=confirmed,
        is_dry_run=False,
        trace_id=trace_id,
        request_id=request_id,
    )

    proof_path = persist_capability_proof(proof_final, base_dir=base)

    graph_final = proof_final.capability_graph
    lines = [
        f"**!capability-report** -- PROOF CLASSIFIED",
        f"maturity: `{proof_final.maturity_level}`",
        f"ceiling: `{proof_final.maturity_ceiling}`",
        f"escalation_blocked: `{proof_final.escalation_blocked}`",
    ]
    if proof_final.escalation_reason:
        lines.append(f"reason: `{proof_final.escalation_reason}`")
    lines.append(f"founder: `{founder_answer}`")
    lines.append(
        f"graph: `{len(graph_final.nodes)}` capabilities | "
        f"proven=`{graph_final.proven_count}` missing=`{graph_final.missing_count}`"
    )
    lines.append(f"bottlenecks: `{len(proof_final.bottlenecks)}`")
    lines.append(f"proposals: `{len(proof_final.upgrade_proposals)}`")
    lines.append(f"strategy: `{proof_final.execution_strategy}`")
    lines.append(f"proof: `{proof_path.name}`")

    await message.channel.send("\n".join(lines))
    _log(
        f"!capability-report completed: maturity={proof_final.maturity_level} "
        f"capabilities={len(graph_final.nodes)} "
        f"bottlenecks={len(proof_final.bottlenecks)} "
        f"proposals={len(proof_final.upgrade_proposals)} "
        f"founder={founder_answer}"
    )


async def _handle_orchestration_report(message: Any, spine: Any) -> None:
    from core.workstation.governed_recursive_orchestration_engine_v1 import (
        build_full_orchestration_proof,
        persist_orchestration_proof,
        DAG_TYPES,
        SIMULATION_OUTCOMES,
        ORCHESTRATION_MATURITY_LEVELS,
    )
    from core.workstation.recursive_capability_planning_engine_v1 import (
        build_full_capability_proof,
        SUBSTRATE_CAPABILITIES,
    )
    from core.workstation.adapter_autogeneration_engine_v1 import (
        AdapterAutogenProof,
        AdapterAutogenEvidence,
    )
    from core.workstation.environment_mapping_engine_v1 import (
        ENVIRONMENT_MAP_DIR,
        EnvironmentMappingProof,
        EnvironmentTopology,
        EnvironmentMappingEvidence,
        DiscoveredPlatform,
    )
    from core.workstation.visible_actuation_proof_v1 import (
        FounderConfirmationArtifact,
        persist_founder_confirmation,
    )

    base = Path(_REPO_ROOT)
    trace_id = f"W0-orchestration-report-{uuid.uuid4().hex[:8]}"
    request_id = f"REQ-W0-ORCH-RPT-{uuid.uuid4().hex[:8]}"

    await message.channel.send(
        f"**!orchestration-report** -- analyzing orchestration\n"
        f"DAG types: `{len(DAG_TYPES)}` | simulation outcomes: `{len(SIMULATION_OUTCOMES)}`\n"
        f"maturity levels: `{len(ORCHESTRATION_MATURITY_LEVELS)}`\n"
        f"Loading upstream proofs and building orchestration graph..."
    )

    env_proof = None
    env_map_dir = base / ENVIRONMENT_MAP_DIR
    if env_map_dir.exists():
        proof_files = sorted(env_map_dir.glob("ENVMAP-*.json"), reverse=True)
        if proof_files:
            try:
                with open(proof_files[0], encoding="utf-8-sig") as f:
                    proof_data = json.load(f)
                topo_data = proof_data.get("topology")
                topology = None
                if topo_data:
                    platforms = [
                        DiscoveredPlatform(
                            **{
                                k: v
                                for k, v in p.items()
                                if k in DiscoveredPlatform.__dataclass_fields__
                            }
                        )
                        for p in topo_data.get("platforms", [])
                    ]
                    topology = EnvironmentTopology(
                        topology_id=topo_data.get("topology_id", ""),
                        platforms=platforms,
                    )
                evidence_data = proof_data.get("evidence", {})
                env_evidence = (
                    EnvironmentMappingEvidence(
                        **{
                            k: v
                            for k, v in evidence_data.items()
                            if k in EnvironmentMappingEvidence.__dataclass_fields__
                        }
                    )
                    if evidence_data
                    else None
                )
                env_proof = EnvironmentMappingProof(
                    proof_id=proof_data.get("proof_id", ""),
                    maturity_level=proof_data.get("maturity_level", "L0_NO_MAPPING"),
                    evidence=env_evidence,
                    topology=topology,
                )
            except (json.JSONDecodeError, OSError, TypeError):
                pass

    adapter_proof = None
    adapter_dir = base / "data/runtime/workstation_relay/adapter_reports"
    if adapter_dir.exists():
        adapter_files = sorted(adapter_dir.glob("ADPTGEN-*.json"), reverse=True)
        if adapter_files:
            try:
                with open(adapter_files[0], encoding="utf-8-sig") as f:
                    adapter_data = json.load(f)
                ev_data = adapter_data.get("evidence", {})
                adapter_evidence = (
                    AdapterAutogenEvidence(
                        **{
                            k: v
                            for k, v in ev_data.items()
                            if k in AdapterAutogenEvidence.__dataclass_fields__
                        }
                    )
                    if ev_data
                    else None
                )
                adapter_proof = AdapterAutogenProof(
                    proof_id=adapter_data.get("proof_id", ""),
                    maturity_level=adapter_data.get("maturity_level", "L0_SIMULATED"),
                    evidence=adapter_evidence,
                )
            except (json.JSONDecodeError, OSError, TypeError):
                pass

    capability_proof = build_full_capability_proof(
        env_proof=env_proof,
        adapter_proof=adapter_proof,
        founder_confirmed=False,
        is_dry_run=False,
        trace_id=trace_id,
        request_id=request_id,
    )

    proof = build_full_orchestration_proof(
        capability_proof=capability_proof,
        founder_confirmed=False,
        is_dry_run=False,
        trace_id=trace_id,
        request_id=request_id,
    )

    ev = proof.evidence
    sim_success = ev.simulation_success_count if ev else 0
    sim_total = ev.simulation_count if ev else 0
    unsafe_count = ev.unsafe_chains_detected if ev else 0

    lines = [
        f"**!orchestration-report** -- analysis complete",
        f"DAGs: `{len(proof.dags)}`",
        f"blast radii: `{len(proof.blast_radii)}` (max risk: `{ev.max_blast_radius:.3f}`)"
        if ev
        else f"blast radii: `{len(proof.blast_radii)}`",
        f"rollback plans: `{len(proof.rollback_plans)}` "
        f"(safe: `{ev.rollback_safe_count}` unsafe: `{ev.rollback_unsafe_count}`)"
        if ev
        else f"rollback plans: `{len(proof.rollback_plans)}`",
        f"simulations: `{sim_total}` (success: `{sim_success}`)",
        f"unsafe chains: `{unsafe_count}`",
        f"sequenced upgrades: `{len(proof.sequenced_upgrades)}`",
        f"maturity: `{proof.maturity_level}` | ceiling: `{proof.maturity_ceiling}`",
        f"strategy: `{proof.execution_strategy}`",
    ]
    if proof.governance_bottlenecks:
        lines.append(f"governance bottlenecks: `{len(proof.governance_bottlenecks)}`")

    await message.channel.send("\n".join(lines))

    await message.channel.send(
        "**Founder confirmation required.**\n"
        "Approve orchestration proof generation?\n"
        "Reply **YES** or **NO** within 60 seconds."
    )

    def check_response(m: Any) -> bool:
        return (
            m.author.id == message.author.id
            and m.channel.id == message.channel.id
            and m.content.strip().upper() in ("YES", "NO")
        )

    try:
        client = message.channel._state._get_client()
        response = await client.wait_for("message", check=check_response, timeout=60.0)
        founder_answer = response.content.strip().upper()
    except asyncio.TimeoutError:
        founder_answer = "TIMEOUT"
    except AttributeError:
        await message.channel.send("Could not access bot for confirmation — skipping.")
        founder_answer = "TIMEOUT"

    confirmed = founder_answer == "YES"

    confirmation = FounderConfirmationArtifact(
        confirmed=confirmed,
        trace_id=trace_id,
        request_id=request_id,
        channel="discord",
        founder_response=founder_answer,
    )
    persist_founder_confirmation(confirmation, base_dir=base)

    proof_final = build_full_orchestration_proof(
        capability_proof=capability_proof,
        founder_confirmed=confirmed,
        is_dry_run=False,
        trace_id=trace_id,
        request_id=request_id,
    )

    proof_path = persist_orchestration_proof(proof_final, base_dir=base)

    ev_final = proof_final.evidence
    lines = [
        f"**!orchestration-report** -- PROOF CLASSIFIED",
        f"maturity: `{proof_final.maturity_level}`",
        f"ceiling: `{proof_final.maturity_ceiling}`",
        f"escalation_blocked: `{proof_final.escalation_blocked}`",
    ]
    if proof_final.escalation_reason:
        lines.append(f"reason: `{proof_final.escalation_reason}`")
    lines.append(f"founder: `{founder_answer}`")
    lines.append(f"DAGs: `{len(proof_final.dags)}`")
    lines.append(
        f"blast radii: `{len(proof_final.blast_radii)}` (max: `{ev_final.max_blast_radius:.3f}`)"
        if ev_final
        else f"blast radii: `{len(proof_final.blast_radii)}`"
    )
    lines.append(
        f"rollback: safe=`{ev_final.rollback_safe_count}` unsafe=`{ev_final.rollback_unsafe_count}`"
        if ev_final
        else "rollback: unknown"
    )
    lines.append(
        f"simulations: `{ev_final.simulation_count}` "
        f"(success=`{ev_final.simulation_success_count}`)"
        if ev_final
        else "simulations: none"
    )
    lines.append(f"sequenced: `{', '.join(proof_final.sequenced_upgrades[:5])}`")
    lines.append(f"strategy: `{proof_final.execution_strategy}`")
    lines.append(f"proof: `{proof_path.name}`")

    await message.channel.send("\n".join(lines))
    _log(
        f"!orchestration-report completed: maturity={proof_final.maturity_level} "
        f"dags={len(proof_final.dags)} "
        f"simulations={ev_final.simulation_count if ev_final else 0} "
        f"founder={founder_answer}"
    )


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
    _log(f"registry hash: {_CANONICAL.registry_hash()}")
    _log(f"registry source: canonical_command_registry_v1")
    _log(f"handler source: {os.path.abspath(__file__)}")
    _log(f"PID: {_BOOT_PID}")
    _log(f"commands: {', '.join(sorted(SUBSTRATE_COMMANDS))}")
    _log("=" * 50)
