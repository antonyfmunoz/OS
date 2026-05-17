"""bridge_health.py — VPS-side watchdog for the Windows bridge.

Ensures the Windows bridge is live before any operation that depends on it.
If unreachable, SSHs to Windows over Tailscale (OpenSSH Server) and starts
the bridge process.

SSH uses key auth via OpenSSH Server bound to the Tailscale interface on
Windows. Username has spaces — always use list-form subprocess args with
explicit -l flag, never user@host concatenation.

Usage:
    # Programmatic — call before any bridge-dependent operation
    from services.bridge_health import ensure_bridge_live
    result = ensure_bridge_live()  # blocks up to 30s, returns status dict

    # CLI — manual check/start
    python3 services/bridge_health.py
    python3 services/bridge_health.py --verbose
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import requests

_REPO_ROOT = Path(__file__).parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")
load_dotenv(_REPO_ROOT / "runtime" / ".env")

logger = logging.getLogger(__name__)

# Windows machine — OpenSSH Server on Tailscale interface
_WINDOWS_HOST = os.getenv("EOS_WINDOWS_TAILSCALE_HOST", "100.74.199.102")
_WINDOWS_USER = os.getenv("EOS_WINDOWS_TAILSCALE_USER", "antonys beast pc")
_BRIDGE_PORT = int(os.getenv("EOS_LOCAL_BRIDGE_PORT", "8767"))
_BRIDGE_URL = f"http://{_WINDOWS_HOST}:{_BRIDGE_PORT}"

_SSH_TIMEOUT_S = 15
_HEALTH_TIMEOUT_S = 3.0
_POLL_INTERVAL_S = 3
_MAX_WAIT_S = 30

# Path to bridge server on Windows (native Windows path)
_WINDOWS_REPO = os.getenv(
    "EOS_WINDOWS_REPO_PATH",
    r"C:\Users\antonys beast pc\dev\OSv2",
)
_WINDOWS_BRIDGE_SCRIPT = os.getenv(
    "EOS_WINDOWS_BRIDGE_SCRIPT",
    rf"{_WINDOWS_REPO}\services\local_bridge_server.py",
)
_WINDOWS_BRIDGE_LOG = os.getenv(
    "EOS_WINDOWS_BRIDGE_LOG",
    r"C:\Users\antonys beast pc\eos_bridge.log",
)


def _ssh_cmd(remote_command: list[str]) -> list[str]:
    """Build SSH command with proper handling of spaced username.

    Always uses list-form args with -l flag. Never concatenates user@host.
    """
    return [
        "ssh",
        "-o", "ConnectTimeout=5",
        "-o", "StrictHostKeyChecking=accept-new",
        "-o", "BatchMode=yes",
        "-l", _WINDOWS_USER,
        _WINDOWS_HOST,
        *remote_command,
    ]


def _check_health() -> bool:
    """Quick health check — is the bridge port responding?"""
    try:
        resp = requests.get(f"{_BRIDGE_URL}/health", timeout=_HEALTH_TIMEOUT_S)
        return resp.status_code == 200
    except (requests.ConnectionError, requests.Timeout, OSError):
        return False


def _check_ssh() -> dict[str, Any]:
    """Verify OpenSSH connectivity to Windows via Tailscale interface."""
    try:
        cmd = _ssh_cmd(["powershell", "-c", "echo ok"])
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=_SSH_TIMEOUT_S,
        )
        if result.returncode == 0 and "ok" in result.stdout:
            return {"ok": True}
        return {
            "ok": False,
            "error": f"SSH returned code {result.returncode}: {result.stderr.strip()[:200]}",
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "SSH connection timed out (5s)"}
    except FileNotFoundError:
        return {"ok": False, "error": "ssh binary not found"}
    except Exception as exc:
        return {"ok": False, "error": f"SSH check failed: {exc}"}


def _start_bridge_via_ssh() -> dict[str, Any]:
    """SSH to Windows and start the bridge server via scheduled task.

    Uses `schtasks /run` to trigger the pre-installed EOS-Bridge task.
    This creates a persistent process that survives SSH session closure
    (unlike `start /b` or `Start-Process` which die with the session).
    """
    try:
        cmd = _ssh_cmd(["powershell", "-c", "schtasks /run /tn 'EOS-Bridge'"])
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=_SSH_TIMEOUT_S,
        )
        if result.returncode == 0:
            logger.info("[BridgeHealth] Started bridge on Windows via schtasks")
            return {"ok": True, "pid": "schtask"}
        return {
            "ok": False,
            "error": f"schtasks /run failed (code {result.returncode}): {result.stderr.strip()[:300]}",
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "SSH start command timed out"}
    except Exception as exc:
        return {"ok": False, "error": f"SSH start failed: {exc}"}


def _kill_bridge_via_ssh() -> dict[str, Any]:
    """SSH to Windows and kill any running bridge Python process.

    Only kills python.exe processes whose command line contains
    'local_bridge_server'. Never kills svchost or other system processes.
    """
    # Use taskkill with /fi to target only python processes with our script name.
    # This is safer than Stop-Process on arbitrary PIDs.
    kill_cmd = 'taskkill /f /fi "IMAGENAME eq python.exe" /fi "WINDOWTITLE eq *bridge*"'
    # Fallback: PowerShell filtering by command line (more accurate)
    ps_kill = (
        "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
        "Where-Object {$_.CommandLine -like '*local_bridge_server*'} | "
        "ForEach-Object {Stop-Process -Id $_.ProcessId -Force}"
    )
    try:
        cmd = _ssh_cmd(["powershell", "-c", ps_kill])
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=_SSH_TIMEOUT_S,
        )
        return {"ok": True, "output": result.stdout.strip()}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _surface_error(message: str) -> None:
    """Surface a bridge lifecycle error to Discord."""
    try:
        from interface.discord.discord_utils import post_to_webhook

        post_to_webhook(
            content=f"🚨 **Bridge Lifecycle Error**\n```\n{message}\n```",
            title="",
            username="DEX-WATCHDOG",
        )
    except Exception:
        logger.warning("[BridgeHealth] Could not surface error to Discord")


def _surface_setup_gate() -> None:
    """Surface a one-time setup gate to Discord with remediation steps."""
    msg = (
        "🔧 **ONE-TIME SETUP REQUIRED — OpenSSH on Windows**\n\n"
        "The VPS cannot SSH to your Windows machine. This is needed for "
        "automatic bridge lifecycle management.\n\n"
        "**Fix (run once on Windows, admin PowerShell):**\n"
        "```\n"
        "# 1. Install OpenSSH Server\n"
        "Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0\n"
        "\n"
        "# 2. Start and enable sshd\n"
        "Start-Service sshd\n"
        "Set-Service -Name sshd -StartupType Automatic\n"
        "\n"
        "# 3. Bind sshd to Tailscale interface (edit sshd_config):\n"
        "#    ListenAddress 100.74.199.102\n"
        "\n"
        "# 4. Paste VPS pubkey into:\n"
        "#    C:\\ProgramData\\ssh\\administrators_authorized_keys\n"
        "#    (icacls: only SYSTEM + Administrators, no inheritance)\n"
        "\n"
        "# 5. Restart sshd\n"
        "Restart-Service sshd\n"
        "```\n"
        "\n"
        "**Verify from VPS:**\n"
        f"```\nssh -l \"{_WINDOWS_USER}\" {_WINDOWS_HOST} powershell -c \"echo ok\"\n```\n"
        "\n"
        "After this, bridge auto-recovery works forever. Zero awareness needed."
    )
    try:
        from interface.discord.discord_utils import post_to_webhook

        post_to_webhook(content=msg, title="", username="DEX-WATCHDOG")
    except Exception:
        pass
    logger.error("[BridgeHealth] %s", msg)


def ensure_bridge_live(timeout: float = _MAX_WAIT_S) -> dict[str, Any]:
    """Ensure the Windows bridge is responding. Start it if necessary.

    Returns:
        {"ok": True, "action": "already_live"|"started", "elapsed_s": float}
        {"ok": False, "error": str, "action": "failed"}

    This is the single entry point for all bridge-dependent operations.
    Call it before dispatching — if bridge is up, returns instantly (~3s max).
    If bridge is down, attempts SSH autostart and polls up to timeout.
    """
    start_time = time.time()

    # Fast path: bridge already up
    if _check_health():
        return {"ok": True, "action": "already_live", "elapsed_s": 0.0}

    logger.info("[BridgeHealth] Bridge unreachable — attempting autostart via OpenSSH")

    # Check SSH connectivity first
    ssh_check = _check_ssh()
    if not ssh_check["ok"]:
        _surface_setup_gate()
        return {
            "ok": False,
            "error": f"Cannot SSH to Windows: {ssh_check['error']}",
            "action": "ssh_failed",
        }

    # Start the bridge
    start_result = _start_bridge_via_ssh()
    if not start_result["ok"]:
        error_msg = f"Bridge start failed: {start_result['error']}"
        _surface_error(error_msg)
        return {"ok": False, "error": error_msg, "action": "start_failed"}

    # Poll until bridge responds or timeout
    elapsed = time.time() - start_time
    while elapsed < timeout:
        time.sleep(_POLL_INTERVAL_S)
        elapsed = time.time() - start_time

        if _check_health():
            logger.info("[BridgeHealth] Bridge came up in %.1fs", elapsed)
            return {"ok": True, "action": "started", "elapsed_s": round(elapsed, 1)}

    # Timeout
    error_msg = f"Bridge did not respond within {timeout}s after SSH start"
    _surface_error(error_msg)
    return {"ok": False, "error": error_msg, "action": "timeout"}


def main() -> None:
    """CLI entrypoint for manual bridge health check/start."""
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    parser = argparse.ArgumentParser(description="Windows bridge health watchdog")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--check-only", action="store_true", help="Only check, don't start")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.check_only:
        healthy = _check_health()
        print(f"Bridge healthy: {healthy}")
        ssh = _check_ssh()
        print(f"SSH to Windows: {ssh}")
        sys.exit(0 if healthy else 1)

    result = ensure_bridge_live()
    if result["ok"]:
        print(f"✓ Bridge live ({result['action']}, {result.get('elapsed_s', 0):.1f}s)")
    else:
        print(f"✗ Bridge failed: {result['error']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
