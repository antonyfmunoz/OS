#!/usr/bin/env python3
"""discord_approval_worker.py — tail notifications.jsonl, post to Discord.

The Control Plane's `FileNotifier` writes every deferred-action
announcement to an append-only JSONL queue at
`/opt/OS/logs/deferred/notifications.jsonl`. This worker is the
integration seam between that queue and any external approval channel
(currently Discord).

Design notes:

- **Decoupled from the Control Plane**. This worker never imports
  `core.action_system`. It only reads the JSONL and the deferred
  directory (to skip already-approved/dropped actions). That means
  the Control Plane's execution path is never blocked on notification
  delivery — if this worker is down, actions still defer cleanly.

- **Offset-based tailing**. We track the last processed byte offset in
  `/opt/OS/logs/deferred/.worker_offset` so restarts don't re-notify
  old events. The offset is written *after* a successful POST (or after
  the line is skipped as stale), so a crash mid-POST is at-most-once
  lossy — not at-least-once spammy.

- **Best-effort POST**. If Discord returns non-2xx or the webhook is
  missing, the line is logged to stderr and the offset still advances.
  The on-disk deferred queue remains the source of truth; Discord is
  advisory.

Configuration:

    DISCORD_APPROVAL_WEBHOOK_URL   — webhook URL (required)
    DISCORD_APPROVAL_POLL_SECONDS  — poll interval for --loop mode (default 15)

Usage:

    # Drain once (cron-friendly):
    python3 /opt/OS/scripts/workers/discord_approval_worker.py --once

    # Tail forever (systemd / tmux):
    python3 /opt/OS/scripts/workers/discord_approval_worker.py --loop

    # Reset offset (re-process entire queue):
    python3 /opt/OS/scripts/workers/discord_approval_worker.py --reset --once
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone

NOTIFICATION_QUEUE = "/opt/OS/logs/deferred/notifications.jsonl"
DEFERRED_DIR = "/opt/OS/logs/deferred"
OFFSET_FILE = "/opt/OS/logs/deferred/.worker_offset"

DEFAULT_POLL_SECONDS = 15


def _read_offset() -> int:
    try:
        with open(OFFSET_FILE) as f:
            return int(f.read().strip() or "0")
    except (FileNotFoundError, ValueError):
        return 0


def _write_offset(offset: int) -> None:
    os.makedirs(os.path.dirname(OFFSET_FILE), exist_ok=True)
    with open(OFFSET_FILE, "w") as f:
        f.write(str(offset))


def _is_still_deferred(action_id: str) -> bool:
    """Check whether the action file still exists on disk.

    If an operator already approved or dropped it before the worker
    ran, we don't want to notify about it.
    """
    if not action_id:
        return False
    return os.path.isfile(os.path.join(DEFERRED_DIR, f"{action_id}.json"))


def _format_discord_payload(record: dict) -> dict:
    return {
        "content": (
            f"**Control Plane — approval required**\n"
            f"`{(record.get('risk_level') or '?').upper()}` "
            f"{record.get('type', '?')} from `{record.get('source_agent', '?')}`\n"
            f"> {record.get('description', '(no description)')}\n"
            f"Approve: `{record.get('approve_cmd', '')}`\n"
            f"_notified_at: {record.get('notified_at', '')}_"
        )
    }


def _post_to_discord(
    webhook_url: str, payload: dict, timeout: int = 5
) -> tuple[bool, str]:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        webhook_url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return (200 <= r.status < 300), f"status={r.status}"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def _log(msg: str) -> None:
    print(f"[{datetime.now(timezone.utc).isoformat()}] {msg}", file=sys.stderr)


def drain_once(webhook_url: str | None, *, dry_run: bool = False) -> dict:
    """Process any un-notified entries in notifications.jsonl.

    Returns a summary dict: {"read": N, "posted": N, "skipped": N, "failed": N}.
    """
    stats = {
        "read": 0,
        "posted": 0,
        "skipped_stale": 0,
        "skipped_no_webhook": 0,
        "failed": 0,
    }

    if not os.path.isfile(NOTIFICATION_QUEUE):
        return stats

    offset = _read_offset()
    with open(NOTIFICATION_QUEUE, "rb") as f:
        f.seek(offset)
        while True:
            line_start = f.tell()
            line = f.readline()
            if not line:
                break
            stats["read"] += 1
            try:
                record = json.loads(line.decode("utf-8"))
            except json.JSONDecodeError:
                _log(f"skip malformed line at offset {line_start}")
                continue

            action_id = record.get("action_id") or ""
            if not _is_still_deferred(action_id):
                stats["skipped_stale"] += 1
                continue

            if dry_run:
                _log(f"DRY {action_id} {record.get('description', '')}")
                stats["posted"] += 1
                continue

            if not webhook_url:
                stats["skipped_no_webhook"] += 1
                # Do not advance offset in this case: if the webhook
                # comes online later we want to replay these lines.
                return stats

            ok, detail = _post_to_discord(webhook_url, _format_discord_payload(record))
            if ok:
                stats["posted"] += 1
            else:
                stats["failed"] += 1
                _log(f"POST failed for {action_id}: {detail}")

        final_offset = f.tell()

    _write_offset(final_offset)
    return stats


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--once", action="store_true", help="Drain the queue once and exit"
    )
    mode.add_argument(
        "--loop", action="store_true", help="Drain forever on a poll interval"
    )
    p.add_argument(
        "--dry-run", action="store_true", help="Do not POST; print what would be sent"
    )
    p.add_argument(
        "--reset", action="store_true", help="Reset offset to 0 before draining"
    )
    p.add_argument(
        "--poll-seconds",
        type=int,
        default=int(os.getenv("DISCORD_APPROVAL_POLL_SECONDS", DEFAULT_POLL_SECONDS)),
    )
    args = p.parse_args()

    webhook_url = os.getenv("DISCORD_APPROVAL_WEBHOOK_URL")
    if args.reset:
        _write_offset(0)
        _log("offset reset to 0")

    if not webhook_url and not args.dry_run:
        _log(
            "WARNING: DISCORD_APPROVAL_WEBHOOK_URL not set. Worker is "
            "operationally ready but will not POST. Use --dry-run for a no-op drain."
        )

    if args.once:
        stats = drain_once(webhook_url, dry_run=args.dry_run)
        print(json.dumps(stats, indent=2))
        return 0

    # --loop
    _log(f"loop mode poll={args.poll_seconds}s queue={NOTIFICATION_QUEUE}")
    while True:
        try:
            stats = drain_once(webhook_url, dry_run=args.dry_run)
            if stats["read"]:
                _log(f"drain: {stats}")
        except Exception as e:  # pragma: no cover - defensive
            _log(f"drain error: {type(e).__name__}: {e}")
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    sys.exit(main())
