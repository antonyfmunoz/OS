"""WSL-side relay client for the Windows Interactive Desktop Adapter.

Writes action request JSON to the relay inbox and reads result JSON
from the relay outbox. The relay inbox/outbox are shared directories
accessible from both WSL and Windows.

This module runs on the WSL/tmux side. It never executes GUI actions
itself — it delegates to the Windows-native relay.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RELAY_INBOX_DEFAULT = Path.home() / "eos_relay" / "inbox"
RELAY_OUTBOX_DEFAULT = Path.home() / "eos_relay" / "outbox"

RELAY_TIMEOUT_SECONDS = 120
RELAY_POLL_INTERVAL = 2


def write_request_to_relay(
    request: dict[str, Any],
    relay_inbox: Path = RELAY_INBOX_DEFAULT,
    dry_run: bool = False,
) -> Path:
    """Write an action request JSON to the relay inbox.

    In dry_run mode, the request is written but marked as dry_run
    so the relay can skip execution.
    """
    relay_inbox.mkdir(parents=True, exist_ok=True)

    if dry_run:
        request = {**request, "dry_run": True}

    request_id = request.get("request_id", "unknown")
    filename = f"{request_id}.json"
    path = relay_inbox / filename

    with open(path, "w") as f:
        json.dump(request, f, indent=2)

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

    while time.time() < deadline:
        if result_path.exists():
            try:
                with open(result_path) as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        time.sleep(poll_interval)

    return None


def check_relay_available(
    relay_inbox: Path = RELAY_INBOX_DEFAULT,
    relay_outbox: Path = RELAY_OUTBOX_DEFAULT,
) -> dict[str, Any]:
    """Check if the relay directories exist and are writable."""
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

    return {
        "relay_inbox_exists": inbox_exists,
        "relay_outbox_exists": outbox_exists,
        "relay_inbox_writable": inbox_writable,
        "relay_available": inbox_exists and outbox_exists and inbox_writable,
        "relay_inbox": str(relay_inbox),
        "relay_outbox": str(relay_outbox),
    }


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
    request_path = write_request_to_relay(request, relay_inbox, dry_run=dry_run)
    request_id = request.get("request_id", "unknown")

    if dry_run:
        return {
            "status": "dry_run",
            "request_id": request_id,
            "request_path": str(request_path),
            "result": None,
            "note": "Dry run — request written but no execution expected",
        }

    result = read_result_from_relay(
        request_id,
        relay_outbox,
        timeout_seconds=timeout_seconds,
    )

    if result is None:
        return {
            "status": "timeout",
            "request_id": request_id,
            "request_path": str(request_path),
            "result": None,
            "error": f"No result within {timeout_seconds}s — relay may be unavailable",
        }

    return {
        "status": "completed",
        "request_id": request_id,
        "request_path": str(request_path),
        "result": result,
    }
