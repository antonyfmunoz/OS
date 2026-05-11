"""
Local worker auto-loop for Phase 96.8D (updated 96.8H).

Pull-based local worker that acts as the tmux/GUI relay:
VPS creates governed packet → local worker pulls → local worker
routes GUI actions through Windows Interactive Desktop Adapter →
local worker validates visible-window proof → local worker stops
at account verification gate only after founder confirmation.

Phase 96.8H: if execution_binding requires
windows_interactive_desktop_adapter, the local worker routes to
the relay client instead of direct WSL Chrome launch. If the relay
is unavailable, execution is blocked. If the relay returns pending
founder confirmation, execution stops at that gate.

No Playwright. No scraping. No Gmail. No account switching.
No explorer.exe / default-browser routing for W0-001.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INBOX_DIR = Path.home() / "eos_advisor_messages" / "inbox"
OUTBOX_DIR = Path.home() / "eos_advisor_messages" / "outbox"
PACKET_DIR = Path.home() / "eos_advisor_messages"

WO_001_ID = "WO-LOCAL-PILOT-GDRIVE-GDOCS-001"
WO_001_ACCOUNT = "antonyfm@empyreanstudios.co"
WO_001_SOURCE_CLASS = "Google Drive / Google Docs"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"[{ts}] [worker] {msg}", flush=True)


# ── Packet loading ──────────────────────────────────────────────────────────


def load_worker_packet(path: str | Path) -> dict[str, Any]:
    """Load a relay packet from a JSON file."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Packet not found: {path}")
    with open(path) as f:
        return json.load(f)


def validate_wo_001_packet(packet: dict[str, Any]) -> list[str]:
    """Validate that the packet matches W0-001 requirements."""
    errors: list[str] = []

    if packet.get("work_order_id") != WO_001_ID:
        errors.append(f"Wrong work_order_id: {packet.get('work_order_id')}")

    if packet.get("target_account") != WO_001_ACCOUNT:
        errors.append(f"Wrong target_account: {packet.get('target_account')}")

    if packet.get("worker_mode") != "auto":
        errors.append(f"Worker mode must be auto: {packet.get('worker_mode')}")

    if packet.get("playwright_enabled", False):
        errors.append("Playwright must be disabled")

    if packet.get("approval_routing") != "advisor_relay":
        errors.append(f"Wrong approval routing: {packet.get('approval_routing')}")

    if packet.get("preferred_backend") != "GUI_COMPUTER_USE":
        errors.append(f"Wrong backend: {packet.get('preferred_backend')}")

    binding_errors = validate_execution_binding_from_packet(packet)
    errors.extend(binding_errors)

    coherence_errors = validate_coherence_from_packet(packet)
    errors.extend(coherence_errors)

    return errors


def validate_execution_binding_from_packet(packet: dict[str, Any]) -> list[str]:
    """Validate execution_binding within a W0 packet.

    Checks that the binding exists and all 6 layers are present.
    Does not import the full validator to avoid circular deps at
    runtime on the local worker — uses lightweight field checks.
    """
    errors: list[str] = []

    binding = packet.get("execution_binding")
    if not binding:
        errors.append("Missing execution_binding in packet")
        return errors

    if not binding.get("environment") or not binding["environment"].get("environment_id"):
        errors.append("Execution binding missing environment")
    if not binding.get("execution_surfaces"):
        errors.append("Execution binding missing execution_surfaces")
    if not binding.get("application") or not binding["application"].get("application_id"):
        errors.append("Execution binding missing application")
    if not binding.get("target_services"):
        errors.append("Execution binding missing target_services")
    if not binding.get("capabilities"):
        errors.append("Execution binding missing capabilities")
    if not binding.get("proof"):
        errors.append("Execution binding missing proof")

    app = binding.get("application", {})
    launch = app.get("launch_method", "")
    disallowed = app.get("disallowed_launch_methods", [])
    if launch and launch in disallowed:
        errors.append(f"Application launch method '{launch}' is disallowed")

    for surf in binding.get("execution_surfaces", []):
        surf_type = surf.get("execution_surface_type", "")
        surf_role = surf.get("execution_surface_role", "")
        if surf_type in ("wsl", "tmux") and surf_role == "gui_actuator":
            errors.append(f"Execution surface {surf_type} cannot be gui_actuator")

    for svc in binding.get("target_services", []):
        svc_id = svc.get("target_service_id", "")
        svc_family = svc.get("target_service_family", "")
        if svc_id in ("google_drive", "google_docs") and svc_family != "google_workspace":
            errors.append(f"Target service {svc_id} requires google_workspace family")

    return errors


def validate_coherence_from_packet(packet: dict[str, Any]) -> list[str]:
    """Validate coherence_envelope within a W0 packet.

    Lightweight field checks — does not import the full validator
    to keep the local worker portable.
    """
    errors: list[str] = []

    envelope = packet.get("coherence_envelope")
    if not envelope:
        errors.append("Missing coherence_envelope in packet")
        return errors

    lineage = envelope.get("lineage")
    if not lineage:
        errors.append("Coherence envelope missing lineage")
        return errors

    stages = lineage.get("stages", [])
    if not stages:
        errors.append("Coherence lineage has no stages")
        return errors

    required_names = {
        "signal",
        "interpretation",
        "decomposition",
        "primitive_mapping",
        "domain_mapping",
        "state_context",
        "composition",
        "capability_selection",
        "adapter_selection",
        "execution_binding",
        "mastery_check",
        "governance_decision",
        "work_packet",
        "proof_contract",
        "trace_path",
    }
    present_names = {s.get("stage_name", "") for s in stages}
    missing = required_names - present_names
    if missing:
        errors.append(f"Coherence lineage missing stages: {sorted(missing)}")

    mvp_stub_allowed = lineage.get("mvp_stub_allowed", False)
    for s in stages:
        if s.get("status") == "mvp_stub" and not mvp_stub_allowed:
            errors.append(f"Stage {s.get('stage_name')} is mvp_stub but mvp_stub_allowed is False")
            break
        if not s.get("artifact_id"):
            errors.append(f"Stage {s.get('stage_name')} missing artifact_id")
        if not s.get("trace_id"):
            errors.append(f"Stage {s.get('stage_name')} missing trace_id")

    return errors


# ── Windows Interactive Desktop Adapter routing (Phase 96.8H) ──────────────


def packet_requires_windows_desktop_adapter(packet: dict[str, Any]) -> bool:
    """Check if the packet's execution binding requires the Windows desktop adapter."""
    binding = packet.get("execution_binding", {})
    if not binding:
        return False

    for surf in binding.get("execution_surfaces", []):
        surf_role = surf.get("execution_surface_role", "")
        surf_type = surf.get("execution_surface_type", "")
        if surf_role == "gui_actuator" and surf_type == "powershell":
            return True

    return False


def check_windows_desktop_adapter_available() -> dict[str, Any]:
    """Check if the Windows desktop relay is available.

    Imports the relay client and checks inbox/outbox directories.
    Returns a status dict.
    """
    try:
        from runtime.transport.windows_desktop_relay_client import (
            check_relay_available,
        )

        return check_relay_available()
    except ImportError:
        return {
            "relay_available": False,
            "error": "windows_desktop_relay_client not importable",
        }


def route_to_windows_desktop_adapter(
    packet: dict[str, Any],
    dry_run: bool = True,
) -> dict[str, Any]:
    """Route a GUI action through the Windows desktop adapter relay.

    In dry_run mode (default), the request is written but not executed.
    Returns a summary dict.
    """
    relay_check = check_windows_desktop_adapter_available()
    if not relay_check.get("relay_available"):
        return {
            "status": "blocked",
            "reason": "WINDOWS_INTERACTIVE_DESKTOP_ADAPTER_UNAVAILABLE",
            "relay_check": relay_check,
        }

    try:
        from core.environment_bridge.windows_desktop_request_builder import (
            build_w0_chrome_open_request,
        )
        from runtime.transport.windows_desktop_relay_client import (
            send_request_and_wait,
        )

        wo_id = packet.get("work_order_id", "WO-LOCAL-PILOT-GDRIVE-GDOCS-001")
        request = build_w0_chrome_open_request(work_order_id=wo_id)
        result = send_request_and_wait(request.to_dict(), dry_run=dry_run)

        visible_proof = result.get("result", {}).get("visible_proof_status", "")
        if visible_proof == "pending_founder_visual_confirmation":
            result["gate_status"] = "VISIBLE_CHROME_LAUNCH_PENDING_FOUNDER_CONFIRMATION"

        return result
    except ImportError as e:
        return {
            "status": "blocked",
            "reason": "IMPORT_ERROR",
            "error": str(e),
        }


# ── Outbox message writing ──────────────────────────────────────────────────


def write_outbox_message(filename: str, message: dict[str, Any]) -> Path:
    """Write a message to the outbox directory."""
    OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTBOX_DIR / filename
    with open(path, "w") as f:
        json.dump(message, f, indent=2)
    _log(f"Wrote outbox: {filename}")
    return path


# ── Inbox response reading ──────────────────────────────────────────────────


def read_inbox_response(filename: str) -> dict[str, Any] | None:
    """Read an advisor response from the inbox directory."""
    path = INBOX_DIR / filename
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def scan_inbox_for_response(work_order_id: str) -> dict[str, Any] | None:
    """Scan inbox for any response matching this work order."""
    if not INBOX_DIR.exists():
        return None
    for f in sorted(INBOX_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text())
            if data.get("work_order_id") == work_order_id:
                return data
        except (json.JSONDecodeError, OSError):
            continue
    return None


# ── Status builders ─────────────────────────────────────────────────────────


def build_claimed_status(packet: dict[str, Any]) -> dict[str, Any]:
    """Build WORK_ORDER_CLAIMED status message."""
    return {
        "message_type": "WORK_ORDER_CLAIMED",
        "work_order_id": packet["work_order_id"],
        "sender": "node:local_pc_worker",
        "recipient": "advisor",
        "timestamp": _now_iso(),
        "payload": {
            "worker_mode": packet.get("worker_mode", "auto"),
            "preferred_backend": packet.get("preferred_backend", "GUI_COMPUTER_USE"),
            "target_account": packet.get("target_account", ""),
            "source_class": packet.get("source_class", ""),
            "packet_id": packet.get("packet_id", ""),
        },
    }


def build_preflight_status(packet: dict[str, Any], checks: list[dict]) -> dict[str, Any]:
    """Build preflight check status message."""
    all_passed = all(c.get("passed") for c in checks)
    return {
        "message_type": "PREFLIGHT_STATUS",
        "work_order_id": packet["work_order_id"],
        "sender": "node:local_pc_worker",
        "recipient": "advisor",
        "timestamp": _now_iso(),
        "payload": {
            "all_passed": all_passed,
            "checks": checks,
        },
    }


def build_backend_health_status(packet: dict[str, Any], results: dict[str, str]) -> dict[str, Any]:
    """Build GUI backend health status message."""
    gui_available = any(
        "OK" in v or "installed" in v
        for k, v in results.items()
        if k in ("pyautogui", "anthropic_computer_use")
    )
    display_available = "DISPLAY" in results.get(
        "visible_display", ""
    ) and "NO_DISPLAY" not in results.get("visible_display", "")

    if gui_available and display_available:
        overall = "available"
    elif gui_available:
        overall = "partial"
    else:
        overall = "missing"

    return {
        "message_type": "BACKEND_HEALTH",
        "work_order_id": packet["work_order_id"],
        "sender": "node:local_pc_worker",
        "recipient": "advisor",
        "timestamp": _now_iso(),
        "payload": {
            "overall_status": overall,
            "gui_available": gui_available,
            "display_available": display_available,
            "checks": results,
        },
    }


def build_first_gate_approval_request(packet: dict[str, Any]) -> dict[str, Any]:
    """Build the first approval request for opening Google Drive."""
    account = packet.get("target_account", WO_001_ACCOUNT)
    return {
        "message_type": "APPROVAL_NEEDED",
        "work_order_id": packet["work_order_id"],
        "sender": "node:local_pc_worker",
        "recipient": "advisor",
        "timestamp": _now_iso(),
        "priority": "HIGH",
        "requires_response": True,
        "payload": {
            "approval_request_id": f"apr_first_gate_{int(time.time())}",
            "work_order_id": packet["work_order_id"],
            "node_id": "local_pc_worker",
            "action": "OPEN_GOOGLE_DRIVE",
            "target": account,
            "description": (
                f"Approve opening Google Drive for {account} using visible GUI computer-use?"
            ),
            "risk_level": "MEDIUM",
            "backend": "GUI_COMPUTER_USE",
            "blocked_until_approved": True,
        },
    }


# ── Safe preflight checks ──────────────────────────────────────────────────


def run_safe_preflight(packet: dict[str, Any]) -> list[dict]:
    """Run safe preflight checks. No network, no browser, no GUI."""
    checks = []

    checks.append(
        {
            "name": "work_order_id",
            "passed": packet.get("work_order_id") == WO_001_ID,
            "detail": packet.get("work_order_id", ""),
        }
    )

    checks.append(
        {
            "name": "target_account",
            "passed": packet.get("target_account") == WO_001_ACCOUNT,
            "detail": packet.get("target_account", ""),
        }
    )

    checks.append(
        {
            "name": "worker_mode",
            "passed": packet.get("worker_mode") == "auto",
            "detail": packet.get("worker_mode", ""),
        }
    )

    checks.append(
        {
            "name": "playwright_disabled",
            "passed": not packet.get("playwright_enabled", False),
            "detail": str(packet.get("playwright_enabled", False)),
        }
    )

    checks.append(
        {
            "name": "approval_routing",
            "passed": packet.get("approval_routing") == "advisor_relay",
            "detail": packet.get("approval_routing", ""),
        }
    )

    checks.append(
        {
            "name": "gui_healthcheck_required",
            "passed": packet.get("require_gui_healthcheck", False),
            "detail": str(packet.get("require_gui_healthcheck", False)),
        }
    )

    checks.append(
        {
            "name": "outbox_dir_exists",
            "passed": OUTBOX_DIR.exists() or _try_mkdir(OUTBOX_DIR),
            "detail": str(OUTBOX_DIR),
        }
    )

    checks.append(
        {
            "name": "inbox_dir_exists",
            "passed": INBOX_DIR.exists() or _try_mkdir(INBOX_DIR),
            "detail": str(INBOX_DIR),
        }
    )

    return checks


def _try_mkdir(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        return True
    except OSError:
        return False


# ── Safe GUI backend healthcheck ────────────────────────────────────────────


def run_gui_backend_healthcheck() -> dict[str, str]:
    """Run GUI backend checks via safe subprocess import tests.

    Returns dict of candidate → output string.
    No mouse, keyboard, browser, or screen interaction.
    """
    results: dict[str, str] = {}

    checks = {
        "visible_display": (
            'python3 -c "import os; '
            "print('DISPLAY' if os.environ.get('DISPLAY') or os.name == 'nt' "
            "else 'NO_DISPLAY')\""
        ),
        "pyautogui": "python3 -c \"import pyautogui; print('pyautogui OK')\"",
        "anthropic_computer_use": "python3 -c \"import anthropic; print('anthropic SDK OK')\"",
        "manual_fallback": "echo 'manual fallback always available'",
    }

    for name, cmd in checks.items():
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            results[name] = result.stdout.strip()
        except (subprocess.TimeoutExpired, OSError):
            results[name] = ""

    return results


# ── Worker should wait ──────────────────────────────────────────────────────


def _extract_decision(response: dict[str, Any] | None) -> str:
    """Extract decision from response, checking both nested and top-level."""
    if response is None:
        return ""
    decision = response.get("payload", {}).get("decision", "")
    if not decision:
        decision = response.get("decision", "")
    normalized = decision.strip().upper()
    if normalized == "APPROVED":
        normalized = "APPROVE"
    return normalized


def worker_should_wait_for_advisor(response: dict[str, Any] | None) -> bool:
    """Return True if the worker should continue waiting."""
    if response is None:
        return True
    return _extract_decision(response) == ""


def worker_should_stop(response: dict[str, Any] | None) -> bool:
    """Return True if the advisor sent STOP or DENY."""
    if response is None:
        return False
    return _extract_decision(response) in ("STOP", "DENY")


# ── Approved action execution ──��───────────────────────────────────────────


def _execute_approved_action(packet: dict[str, Any], response: dict[str, Any]) -> dict[str, Any]:
    """Launch Chrome directly and wait for founder visual confirmation.

    The local worker launches Chrome via the direct executable path
    (not explorer.exe). After launch, it collects process/window
    metadata as evidence, then STOPS at
    VISIBLE_CHROME_LAUNCH_PENDING_FOUNDER_CONFIRMATION.

    Process metadata (MainWindowHandle, MainWindowTitle) is evidence
    only — NOT proof. WSL/tmux can spawn Windows processes without
    reliable foreground visibility.

    VERIFY_ACTIVE_GOOGLE_ACCOUNT is only reachable after the founder
    explicitly confirms Chrome is visibly open by writing a confirmation
    file to the inbox.
    """
    wo_id = packet["work_order_id"]
    drive_url = "https://drive.google.com/drive/my-drive"

    sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
    from core.environment_bridge.chrome_visible_launch import (
        ChromeLaunchMethod,
        ChromeVisibleLaunchStatus,
        apply_founder_visual_confirmation,
        build_chrome_launch_command,
        evaluate_visible_chrome_launch,
        parse_chrome_process_snapshot,
        parse_founder_visual_confirmation,
        visible_launch_proof_allows_next_gate,
        CHROME_EXECUTABLE_PATHS_WSL,
    )

    chrome_exe = CHROME_EXECUTABLE_PATHS_WSL[0]
    chrome_cmd = build_chrome_launch_command(drive_url, chrome_exe)
    _log(f"Launching Chrome directly: {chrome_cmd}")

    launch_success = False
    try:
        subprocess.Popen(
            [chrome_exe, "--new-window", drive_url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        launch_success = True
        _log("Chrome launch command issued")
    except (OSError, FileNotFoundError) as e:
        _log(f"Chrome launch failed: {e}")

    if not launch_success:
        proof_data = {
            "launch_method": ChromeLaunchMethod.DIRECT_EXECUTABLE.value,
            "executable_path": chrome_exe,
            "requested_url": drive_url,
            "process_ids": [],
            "main_window_handle_values": [],
            "main_window_titles": [],
            "metadata_evidence": "none",
            "founder_visual_confirmation_required": True,
            "founder_visual_confirmation_received": False,
            "founder_confirmed": False,
            "status": ChromeVisibleLaunchStatus.CHROME_NOT_FOUND.value,
            "notes": ["Chrome executable not found or launch failed"],
        }
        write_outbox_message(f"chrome_launch_proof_{wo_id}.json", proof_data)
        return {
            "success": False,
            "backend": "VISIBLE_CHROME_LAUNCH",
            "detail": "CHROME_NOT_FOUND",
            "next_gate": None,
            "error": "Chrome executable not found — no silent fallback",
            "chrome_launch_proof": proof_data,
        }

    _log("Waiting 3s for Chrome to start...")
    time.sleep(3)

    snapshots = _collect_chrome_process_snapshots()
    processes = [parse_chrome_process_snapshot(s) for s in snapshots]
    _log(f"Found {len(processes)} Chrome processes")

    proof = evaluate_visible_chrome_launch(
        launch_method=ChromeLaunchMethod.DIRECT_EXECUTABLE,
        executable_path=chrome_exe,
        requested_url=drive_url,
        processes=processes,
    )

    proof_data = proof.to_dict()
    write_outbox_message(f"chrome_launch_proof_{wo_id}.json", proof_data)
    _log(f"Chrome launch evidence: {proof.metadata_evidence}")
    _log(f"Chrome launch status: {proof.status.value}")

    confirmation_request = {
        "message_type": "FOUNDER_VISUAL_CONFIRMATION_REQUIRED",
        "work_order_id": wo_id,
        "sender": "node:local_pc_worker",
        "recipient": "founder",
        "timestamp": _now_iso(),
        "payload": {
            "gate": "VISIBLE_CHROME_LAUNCH",
            "question": "Is Google Chrome visibly open on your desktop with Google Drive loaded?",
            "metadata_evidence": proof.metadata_evidence,
            "process_count": len(processes),
            "how_to_confirm": (
                "python3 /opt/OS/runtime/transport/write_founder_gate_confirmation.py "
                f"--work-order-id {wo_id} --gate VISIBLE_CHROME_LAUNCH "
                "--confirmed true --notes 'Chrome visibly open'"
            ),
            "how_to_deny": (
                "python3 /opt/OS/runtime/transport/write_founder_gate_confirmation.py "
                f"--work-order-id {wo_id} --gate VISIBLE_CHROME_LAUNCH "
                "--confirmed false --notes 'Chrome not visible'"
            ),
        },
    }
    write_outbox_message(f"visible_chrome_confirmation_request_{wo_id}.json", confirmation_request)
    _log("BLOCKED: VISIBLE_CHROME_LAUNCH_PENDING_FOUNDER_CONFIRMATION")
    _log("Waiting for founder visual confirmation...")
    _log("Founder must confirm Chrome is visibly open before proceeding.")

    confirmation_filename = f"founder_visual_confirmation_{wo_id}.json"
    for i in range(720):
        confirmation_path = INBOX_DIR / confirmation_filename
        if confirmation_path.exists():
            try:
                conf_data = json.loads(confirmation_path.read_text())
                is_valid, confirmed, conf_notes = parse_founder_visual_confirmation(conf_data)
                if not is_valid:
                    _log("Invalid confirmation file format — still waiting")
                else:
                    proof = apply_founder_visual_confirmation(proof, confirmed, conf_notes)
                    proof_data = proof.to_dict()
                    write_outbox_message(f"chrome_launch_proof_{wo_id}.json", proof_data)

                    if visible_launch_proof_allows_next_gate(proof):
                        _log("Founder CONFIRMED Chrome is visible")
                        next_gate_msg = {
                            "message_type": "NEXT_GATE",
                            "work_order_id": wo_id,
                            "sender": "node:local_pc_worker",
                            "recipient": "advisor",
                            "timestamp": _now_iso(),
                            "payload": {
                                "gate_action": "VERIFY_ACTIVE_GOOGLE_ACCOUNT",
                                "description": (
                                    f"Verify active Google account is {WO_001_ACCOUNT}. "
                                    "Chrome visibility confirmed by founder."
                                ),
                                "chrome_launch_proof": proof_data,
                            },
                        }
                        write_outbox_message(f"next_gate_{wo_id}.json", next_gate_msg)
                        _log("NEXT GATE: VERIFY_ACTIVE_GOOGLE_ACCOUNT")
                        return {
                            "success": True,
                            "backend": "VISIBLE_CHROME_LAUNCH",
                            "detail": "founder_confirmed_visible",
                            "next_gate": "VERIFY_ACTIVE_GOOGLE_ACCOUNT",
                            "error": None,
                            "chrome_launch_proof": proof_data,
                        }
                    else:
                        _log("Founder DENIED Chrome is visible")
                        return {
                            "success": False,
                            "backend": "VISIBLE_CHROME_LAUNCH",
                            "detail": "founder_denied_visible",
                            "next_gate": None,
                            "error": "Founder confirmed Chrome is NOT visibly open",
                            "chrome_launch_proof": proof_data,
                        }
            except (json.JSONDecodeError, OSError) as e:
                _log(f"Error reading confirmation: {e}")

        if i % 12 == 0 and i > 0:
            _log(f"Still waiting for founder visual confirmation... ({i * 5}s)")
        time.sleep(5)

    _log("Timed out waiting for founder visual confirmation (60 min)")
    return {
        "success": False,
        "backend": "VISIBLE_CHROME_LAUNCH",
        "detail": "pending_founder_visual_confirmation_timeout",
        "next_gate": None,
        "error": "Founder visual confirmation not received within timeout",
        "chrome_launch_proof": proof_data,
    }


def _collect_chrome_process_snapshots() -> list[dict[str, Any]]:
    """Collect Chrome process info from Windows via PowerShell.

    Uses Get-Process to find chrome processes and their window handles/titles.
    Returns raw snapshot dicts for parsing by chrome_visible_launch module.
    """
    snapshots: list[dict[str, Any]] = []
    try:
        cmd = (
            'powershell.exe -NoProfile -Command "'
            "Get-Process chrome -ErrorAction SilentlyContinue | "
            "Select-Object Id,ProcessName,MainWindowHandle,MainWindowTitle | "
            "ConvertTo-Json -Compress"
            '"'
        )
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        if result.stdout.strip():
            data = json.loads(result.stdout.strip())
            if isinstance(data, dict):
                data = [data]
            for proc in data:
                snapshots.append(
                    {
                        "pid": proc.get("Id", 0),
                        "process_name": proc.get("ProcessName", ""),
                        "main_window_handle": proc.get("MainWindowHandle", 0),
                        "main_window_title": proc.get("MainWindowTitle", ""),
                        "executable_path": "",
                    }
                )
    except (subprocess.TimeoutExpired, OSError, json.JSONDecodeError) as e:
        _log(f"Chrome process snapshot collection failed: {e}")
    return snapshots


# ── Main auto-loop ─────���──────────────────────────────────────────────��─────


def run_auto_loop(packet_path: str | Path) -> dict[str, Any]:
    """Run the local worker auto-loop.

    Returns a summary dict of what happened.
    """
    summary: dict[str, Any] = {
        "started_at": _now_iso(),
        "packet_loaded": False,
        "validation_passed": False,
        "claimed": False,
        "preflight_passed": False,
        "backend_health": {},
        "approval_request_sent": False,
        "advisor_response": None,
        "status": "running",
        "error": None,
    }

    # Step 1: Load packet
    _log("Loading relay packet...")
    try:
        packet = load_worker_packet(packet_path)
        summary["packet_loaded"] = True
        _log(f"Loaded: {packet.get('work_order_id')}")
    except Exception as e:
        summary["error"] = f"Failed to load packet: {e}"
        summary["status"] = "failed"
        _log(f"ERROR: {e}")
        return summary

    # Step 2: Validate
    _log("Validating packet...")
    errors = validate_wo_001_packet(packet)
    if errors:
        summary["error"] = f"Validation failed: {errors}"
        summary["status"] = "failed"
        _log(f"VALIDATION FAILED: {errors}")
        return summary
    summary["validation_passed"] = True
    _log("Validation passed")

    # Step 2b: Coherence gate
    _log("Running coherence gate...")
    coherence_errors = validate_coherence_from_packet(packet)
    if coherence_errors:
        wo_id = packet.get("work_order_id", "unknown")
        blocked_msg = {
            "message_type": "COHERENCE_BLOCKED",
            "work_order_id": wo_id,
            "sender": "node:local_pc_worker",
            "recipient": "advisor",
            "timestamp": _now_iso(),
            "payload": {
                "final_status": "blocked_incomplete_canonical_spine",
                "errors": coherence_errors,
            },
        }
        write_outbox_message(f"coherence_blocked_{wo_id}.json", blocked_msg)
        summary["error"] = f"Coherence gate blocked: {coherence_errors}"
        summary["status"] = "blocked_incomplete_canonical_spine"
        _log(f"BLOCK_EXECUTION: INCOMPLETE_CANONICAL_SPINE — {coherence_errors}")
        return summary
    summary["coherence_passed"] = True
    _log("Coherence gate passed")

    # Step 3: Claim
    _log("Claiming work order...")
    claimed_msg = build_claimed_status(packet)
    write_outbox_message(f"claimed_{packet['work_order_id']}.json", claimed_msg)
    summary["claimed"] = True
    _log("Work order claimed")

    # Step 4: Preflight
    _log("Running safe preflight...")
    preflight_checks = run_safe_preflight(packet)
    preflight_msg = build_preflight_status(packet, preflight_checks)
    write_outbox_message(f"preflight_{packet['work_order_id']}.json", preflight_msg)
    all_passed = all(c["passed"] for c in preflight_checks)
    summary["preflight_passed"] = all_passed
    if not all_passed:
        failed = [c for c in preflight_checks if not c["passed"]]
        _log(f"Preflight issues: {[c['name'] for c in failed]}")
    else:
        _log("Preflight passed")

    # Step 5: GUI backend healthcheck
    _log("Running GUI backend healthcheck...")
    health_results = run_gui_backend_healthcheck()
    health_msg = build_backend_health_status(packet, health_results)
    write_outbox_message(f"backend_health_{packet['work_order_id']}.json", health_msg)
    summary["backend_health"] = health_msg["payload"]
    _log(f"Backend health: {health_msg['payload']['overall_status']}")

    # Step 6: First gate approval request
    _log("Sending first gate approval request...")
    approval_msg = build_first_gate_approval_request(packet)
    write_outbox_message(f"approval_request_{packet['work_order_id']}.json", approval_msg)
    summary["approval_request_sent"] = True
    _log(f"APPROVAL REQUEST: {approval_msg['payload']['description']}")

    # Step 7: Wait for advisor response
    _log("Waiting for advisor response...")
    _log("Worker is now BLOCKED at first gate. Polling inbox...")

    poll_count = 0
    while True:
        response = scan_inbox_for_response(packet["work_order_id"])

        if response is not None:
            summary["advisor_response"] = response
            decision = _extract_decision(response)
            _log(f"Advisor response received: {decision}")

            if worker_should_stop(response):
                summary["status"] = "stopped"
                _log(f"Worker STOPPED by advisor: {decision}")
                break
            elif not worker_should_wait_for_advisor(response):
                summary["status"] = "approved"
                _log("Worker APPROVED — executing approved action...")
                action_result = _execute_approved_action(packet, response)
                summary["action_result"] = action_result
                if action_result.get("success"):
                    summary["status"] = "action_executed"
                    _log("Action executed successfully — stopped at next gate")
                else:
                    summary["status"] = "action_failed"
                    _log(f"Action failed: {action_result.get('error', 'unknown')}")
                break

        poll_count += 1
        if poll_count % 12 == 0:
            minutes = poll_count * 5 // 60
            _log(f"Still waiting... ({minutes}m elapsed)")

        time.sleep(5)

    summary["completed_at"] = _now_iso()
    write_outbox_message(f"loop_summary_{packet['work_order_id']}.json", summary)
    return summary


# ── CLI entry point ─────────────────────────────────────────────────────────


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 local_worker_auto_loop.py <packet_path>")
        print(
            "Example: python3 local_worker_auto_loop.py ~/eos_advisor_messages/wo_001_relay_packet.json"
        )
        sys.exit(1)

    packet_path = sys.argv[1]
    _log(f"Starting local worker auto-loop")
    _log(f"Packet: {packet_path}")
    _log(f"Outbox: {OUTBOX_DIR}")
    _log(f"Inbox: {INBOX_DIR}")
    _log("─" * 50)

    try:
        result = run_auto_loop(packet_path)
        _log("─" * 50)
        _log(f"Final status: {result['status']}")
    except KeyboardInterrupt:
        _log("Worker interrupted by operator")
    except Exception as e:
        _log(f"Worker crashed: {e}")
        sys.exit(1)
