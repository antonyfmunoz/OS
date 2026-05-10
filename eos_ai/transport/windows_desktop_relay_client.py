"""WSL-side relay client for the Windows Interactive Desktop Adapter.

Writes action request JSON to the relay inbox and reads result JSON
from the relay outbox. The relay inbox/outbox are shared directories
accessible from both WSL and Windows.

This module runs on the WSL/tmux side. It never executes GUI actions
itself — it delegates to the Windows-native relay.

Path resolution: on WSL, the relay directories live under the Windows
user home via /mnt/c/Users/<username>/. Path.home() returns the Linux
home, not the Windows home, so we resolve the Windows user path
explicitly when running under WSL.

Canonical relay root:
  Windows: %USERPROFILE%/eos_advisor_messages/windows_desktop_relay
  WSL:     /mnt/c/Users/<username>/eos_advisor_messages/windows_desktop_relay

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RELAY_DIR_NAME = os.path.join("eos_advisor_messages", "windows_desktop_relay")


def _resolve_windows_home() -> Path | None:
    """Resolve the Windows user home directory from WSL.

    Returns the /mnt/c/Users/<username> path if running under WSL,
    or None if not in WSL or resolution fails.
    """
    if not Path("/mnt/c").exists():
        return None
    try:
        result = subprocess.run(
            ["cmd.exe", "/C", "echo", "%USERPROFILE%"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        win_path = result.stdout.strip()
        if win_path and "Users" in win_path:
            drive_letter = win_path[0].lower()
            unix_path = win_path.replace("\\", "/")
            unix_path = f"/mnt/{drive_letter}" + unix_path[2:]
            resolved = Path(unix_path)
            if resolved.exists():
                return resolved
    except (OSError, subprocess.TimeoutExpired):
        pass

    try:
        for candidate in Path("/mnt/c/Users").iterdir():
            if candidate.name in ("Public", "Default", "Default User", "All Users"):
                continue
            if candidate.is_dir():
                return candidate
    except OSError:
        pass

    return None


def _default_relay_root() -> Path:
    """Determine the correct relay root directory.

    On WSL: uses the Windows user home via /mnt/c/Users/<username>.
    On Windows: uses Path.home() directly.
    On VPS/Linux without /mnt/c: returns Path.home() fallback (tests only).
    """
    if os.name == "nt":
        return Path.home() / RELAY_DIR_NAME

    win_home = _resolve_windows_home()
    if win_home is not None:
        return win_home / RELAY_DIR_NAME

    return Path.home() / RELAY_DIR_NAME


def _is_windows_relay_environment() -> bool:
    """Return True if this machine can reach a Windows relay.

    True on native Windows or WSL with /mnt/c. False on VPS/Linux.
    """
    if os.name == "nt":
        return True
    return Path("/mnt/c").exists()


def _log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"[{ts}] [relay-client] {msg}", flush=True)


RELAY_ROOT = _default_relay_root()
RELAY_INBOX_DEFAULT = RELAY_ROOT / "inbox"
RELAY_OUTBOX_DEFAULT = RELAY_ROOT / "outbox"

RELAY_TIMEOUT_SECONDS = 120
RELAY_POLL_INTERVAL = 2


def resolve_relay_paths(
    relay_root: Path | str | None = None,
) -> tuple[Path, Path, Path]:
    """Resolve relay root, inbox, and outbox paths.

    If relay_root is provided, use it. Otherwise use the auto-detected default.
    Returns (root, inbox, outbox).
    """
    if relay_root is not None:
        root = Path(relay_root)
    else:
        root = RELAY_ROOT
    return root, root / "inbox", root / "outbox"


def write_request_to_relay(
    request: dict[str, Any],
    relay_inbox: Path = RELAY_INBOX_DEFAULT,
    dry_run: bool = False,
) -> Path:
    """Write an action request JSON to the relay inbox.

    In dry_run mode, the request is written but marked as dry_run
    so the relay can skip execution.
    """
    _log(f"write_request_to_relay: inbox={relay_inbox} dry_run={dry_run}")
    relay_inbox.mkdir(parents=True, exist_ok=True)

    if dry_run:
        request = {**request, "dry_run": True}

    request_id = request.get("request_id", "unknown")
    filename = f"{request_id}.json"
    path = relay_inbox / filename
    _log(f"  writing: {path}")

    with open(path, "w") as f:
        json.dump(request, f, indent=2)

    exists = path.exists()
    size = path.stat().st_size if exists else 0
    _log(f"  written: exists={exists} size={size}B")
    return path


def read_result_from_relay(
    request_id: str,
    relay_outbox: Path = RELAY_OUTBOX_DEFAULT,
    timeout_seconds: int = RELAY_TIMEOUT_SECONDS,
    poll_interval: int = RELAY_POLL_INTERVAL,
) -> dict[str, Any] | None:
    """Poll the relay outbox for a result matching the request_id.

    Returns None if the result is not found within the timeout.
    """
    result_filename = f"{request_id}_result.json"
    result_path = relay_outbox / result_filename
    deadline = time.time() + timeout_seconds
    _log(f"read_result_from_relay: watching {result_path} timeout={timeout_seconds}s")

    poll_count = 0
    while time.time() < deadline:
        if result_path.exists():
            _log(f"  result found: {result_path}")
            try:
                with open(result_path, encoding="utf-8-sig") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                _log(f"  parse error: {e}")
        poll_count += 1
        if poll_count % 5 == 0:
            _log(f"  polling... ({poll_count * poll_interval}s elapsed)")
        time.sleep(poll_interval)

    _log(f"  timeout after {timeout_seconds}s")
    return None


def check_relay_available(
    relay_inbox: Path = RELAY_INBOX_DEFAULT,
    relay_outbox: Path = RELAY_OUTBOX_DEFAULT,
) -> dict[str, Any]:
    """Check if the relay directories exist and are writable."""
    _log(f"check_relay_available: inbox={relay_inbox} outbox={relay_outbox}")
    inbox_exists = relay_inbox.exists()
    outbox_exists = relay_outbox.exists()

    inbox_writable = False
    if inbox_exists:
        try:
            test_file = relay_inbox / ".relay_test"
            test_file.write_text("test")
            test_file.unlink()
            inbox_writable = True
        except OSError:
            pass

    result = {
        "relay_inbox_exists": inbox_exists,
        "relay_outbox_exists": outbox_exists,
        "relay_inbox_writable": inbox_writable,
        "relay_available": inbox_exists and outbox_exists and inbox_writable,
        "relay_inbox": str(relay_inbox),
        "relay_outbox": str(relay_outbox),
        "is_windows_relay_environment": _is_windows_relay_environment(),
    }
    _log(
        f"  available={result['relay_available']} "
        f"inbox_exists={inbox_exists} outbox_exists={outbox_exists} "
        f"writable={inbox_writable} win_env={result['is_windows_relay_environment']}"
    )
    return result


def send_request_and_wait(
    request: dict[str, Any],
    relay_inbox: Path = RELAY_INBOX_DEFAULT,
    relay_outbox: Path = RELAY_OUTBOX_DEFAULT,
    timeout_seconds: int = RELAY_TIMEOUT_SECONDS,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Write request, then poll for result.

    Returns a summary dict with the result or timeout status.
    """
    _log(f"send_request_and_wait: dry_run={dry_run} inbox={relay_inbox} outbox={relay_outbox}")
    request_path = write_request_to_relay(request, relay_inbox, dry_run=dry_run)
    request_id = request.get("request_id", "unknown")
    _log(f"  request_id={request_id} request_path={request_path}")

    if dry_run:
        _log("  returning dry_run status (file was written, relay should skip execution)")
        return {
            "status": "dry_run",
            "request_id": request_id,
            "request_path": str(request_path),
            "result": None,
            "note": "Dry run — request written but no execution expected",
        }

    _log(f"  polling outbox for result (timeout={timeout_seconds}s)...")
    result = read_result_from_relay(
        request_id,
        relay_outbox,
        timeout_seconds=timeout_seconds,
    )

    if result is None:
        _log("  TIMEOUT — no result received")
        return {
            "status": "timeout",
            "request_id": request_id,
            "request_path": str(request_path),
            "result": None,
            "error": f"No result within {timeout_seconds}s — relay may be unavailable",
        }

    _log(f"  result received: adapter_status={result.get('adapter_status')}")
    return {
        "status": "completed",
        "request_id": request_id,
        "request_path": str(request_path),
        "result": result,
    }


# ── CLI entry point ─────────────────────────────────────────────────────────


def _cli_main() -> None:
    parser = argparse.ArgumentParser(description="Windows Interactive Desktop Relay Client")
    parser.add_argument(
        "--action",
        choices=["PING", "CHECK"],
        default="CHECK",
        help="Action to perform (default: CHECK)",
    )
    parser.add_argument(
        "--relay-root",
        type=str,
        default=None,
        help="Explicit relay root directory (overrides auto-detection)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Write request but mark as dry_run",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=15,
        help="Timeout in seconds for result polling (default: 15)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print detailed debug output",
    )
    args = parser.parse_args()

    root, inbox, outbox = resolve_relay_paths(args.relay_root)

    if args.debug:
        _log(f"relay_root={root}")
        _log(f"inbox={inbox}")
        _log(f"outbox={outbox}")
        _log(f"is_windows_env={_is_windows_relay_environment()}")
        _log(f"action={args.action} dry_run={args.dry_run} timeout={args.timeout}")

    if args.action == "CHECK":
        status = check_relay_available(relay_inbox=inbox, relay_outbox=outbox)
        print(json.dumps(status, indent=2))
        sys.exit(0 if status["relay_available"] else 1)

    if args.action == "PING":
        sys.path.insert(0, "/opt/OS")
        from core.environment_bridge.windows_desktop_request_builder import (
            build_ping_request,
        )

        req = build_ping_request()
        if args.debug:
            _log(f"request_id={req.request_id}")
            expected_result = inbox.parent / "outbox" / f"{req.request_id}_result.json"
            _log(f"expected_result_path={expected_result}")

        result = send_request_and_wait(
            req.to_dict(),
            relay_inbox=inbox,
            relay_outbox=outbox,
            timeout_seconds=args.timeout,
            dry_run=args.dry_run,
        )
        print(json.dumps(result, indent=2, default=str))
        sys.exit(0 if result["status"] in ("completed", "dry_run") else 1)


if __name__ == "__main__":
    _cli_main()
