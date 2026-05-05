"""
Local worker auto-loop for Phase 94D.7R.

Minimal auto-loop that runs on the local PC (WSL) and processes relay
packets dispatched from the VPS advisor. Reads packets, claims work
orders, runs safe preflight, runs GUI backend healthcheck, emits
approval requests, waits for advisor response, and executes approved
actions via visible Chrome launch (preferred) or reports BACKEND_MISSING.

No Playwright. No scraping. No Gmail. No account switching.
No silent fallback to Explorer/default browser.
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

    return errors


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


def _try_import_executor():
    """Try to import the approved action executor from local worker dir."""
    worker_dir = Path(__file__).parent
    if str(worker_dir) not in sys.path:
        sys.path.insert(0, str(worker_dir))
    try:
        import approved_action_executor as executor
        import visible_browser_launch_backend as browser

        return executor, browser
    except ImportError:
        return None, None


def _execute_approved_action(packet: dict[str, Any], response: dict[str, Any]) -> dict[str, Any]:
    """Validate approval and prepare the Chrome launch for VPS-side execution.

    WSL tmux sessions created via SSH lack the Windows interop socket,
    so powershell.exe/cmd.exe cannot launch browsers from within the
    worker process. Instead, the worker validates and writes a
    pending_action file. The VPS executes the Chrome launch via
    direct SSH (which has interop) and writes the result back.

    Backend: VISIBLE_CHROME_LAUNCH (not Explorer/default handler).
    Does NOT silently fall back if Chrome is missing.
    """
    wo_id = packet["work_order_id"]
    executor, browser = _try_import_executor()

    if executor is None or browser is None:
        _log("ERROR: Cannot import executor modules")
        return {"success": False, "error": "Executor modules not available"}

    errors = executor.validate_approval_for_action(response, "OPEN_GOOGLE_DRIVE", wo_id)
    if errors:
        _log(f"Approval validation failed: {errors}")
        return {"success": False, "error": f"Validation failed: {errors}"}

    url_errors = browser.validate_url_allowed(browser.DRIVE_URL)
    if url_errors:
        _log(f"URL validation failed: {url_errors}")
        return {"success": False, "error": f"URL blocked: {url_errors}"}

    chrome_command = browser.build_open_url_in_chrome_command(browser.DRIVE_URL)

    pending_action = {
        "action": "OPEN_GOOGLE_DRIVE",
        "url": browser.DRIVE_URL,
        "backend": browser.BACKEND_CLASS,
        "target_account": WO_001_ACCOUNT,
        "work_order_id": wo_id,
        "status": "PENDING_VPS_EXECUTION",
        "timestamp": _now_iso(),
        "chrome_command": chrome_command,
        "execution_method": "VPS direct SSH → PowerShell → chrome.exe",
        "reason": "WSL tmux sessions lack Windows interop socket; Chrome preferred over default handler",
        "silent_fallback_allowed": False,
    }
    write_outbox_message(f"pending_action_{wo_id}.json", pending_action)
    _log("Wrote pending_action (VISIBLE_CHROME_LAUNCH) — waiting for VPS execution...")

    _log("Polling for action result from VPS...")
    for i in range(60):
        result_path = INBOX_DIR / f"action_result_{wo_id}.json"
        if result_path.exists():
            try:
                result_data = json.loads(result_path.read_text())
                success = result_data.get("success", False)
                detail = result_data.get("detail", "")
                chrome_path = result_data.get("chrome_path")
                _log(f"VPS action result received: success={success}, detail={detail}")

                if not success and "CHROME_NOT_FOUND" in str(detail):
                    _log("CHROME_NOT_FOUND — emitting BACKEND_MISSING (no silent fallback)")
                    missing_msg = browser.build_backend_missing_message(
                        "Chrome executable not found on local PC"
                    )
                    write_outbox_message(f"backend_missing_{wo_id}.json", missing_msg)
                    return {
                        "success": False,
                        "backend": browser.BACKEND_CLASS,
                        "detail": "CHROME_NOT_FOUND",
                        "next_gate": None,
                        "error": "CHROME_NOT_FOUND — advisor decision required",
                        "backend_missing": True,
                    }

                action_msg = executor.build_action_executed_result(
                    work_order_id=wo_id,
                    action="OPEN_GOOGLE_DRIVE",
                    backend=browser.BACKEND_CLASS,
                    success=success,
                    detail=detail,
                    chrome_path=chrome_path,
                )
                write_outbox_message(f"action_result_{wo_id}.json", action_msg)

                if success:
                    next_gate = executor.build_next_gate_request(
                        work_order_id=wo_id,
                        gate_action="VERIFY_ACTIVE_GOOGLE_ACCOUNT",
                        description=(
                            f"Verify active Google account is {WO_001_ACCOUNT}. "
                            "Visual confirmation required — is the correct account "
                            "active in Chrome? If login required, respond "
                            "LOGIN_REQUIRED_MANUAL_INTERVENTION. If wrong account, "
                            "respond WRONG_ACCOUNT_PAUSE."
                        ),
                        possible_states=[
                            "DRIVE_OPEN_ACCOUNT_VISIBLE",
                            "LOGIN_REQUIRED_MANUAL_INTERVENTION",
                            "WRONG_ACCOUNT_PAUSE",
                            "CORRECT_ACCOUNT_CONFIRMED",
                            "UNKNOWN_VISUAL_STATE",
                        ],
                    )
                    write_outbox_message(f"next_gate_{wo_id}.json", next_gate)
                    _log("NEXT GATE: VERIFY_ACTIVE_GOOGLE_ACCOUNT")
                    _log("Worker stopped at verification gate.")

                return {
                    "success": success,
                    "backend": browser.BACKEND_CLASS,
                    "detail": detail,
                    "chrome_path": chrome_path,
                    "next_gate": "VERIFY_ACTIVE_GOOGLE_ACCOUNT" if success else None,
                    "error": None if success else detail,
                }
            except (json.JSONDecodeError, OSError) as e:
                _log(f"Error reading action result: {e}")

        if i % 12 == 0 and i > 0:
            _log(f"Still waiting for VPS execution... ({i * 5}s)")
        time.sleep(5)

    _log("Timed out waiting for VPS to execute action (5 min)")
    return {
        "success": False,
        "backend": browser.BACKEND_CLASS,
        "detail": "Timed out waiting for VPS-side Chrome launch execution",
        "next_gate": None,
        "error": "VPS execution timeout",
    }


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
