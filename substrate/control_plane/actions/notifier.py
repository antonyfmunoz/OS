"""Notifier foundation for deferred actions.

Two implementations ship in v2:

- FileNotifier  — always-on, writes an append-only JSONL queue that
                  any future consumer (Discord bot, Telegram worker,
                  web dashboard) can tail or drain.
- DiscordNotifier — best-effort POST to DISCORD_APPROVAL_WEBHOOK_URL
                    if set; silently skips if missing. Non-blocking
                    and never raises.

Both implement the same `notify(action)` signature so `run_action` can
take any Notifier without knowing which concrete one it has.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Protocol

from .actions import Action
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"


NOTIFICATION_QUEUE = f"{_ROOT}/logs/deferred/notifications.jsonl"


class Notifier(Protocol):
    def notify(self, action: Action) -> dict: ...


class FileNotifier:
    """Append deferred-action notifications to a JSONL queue file.

    This is the always-on sink. Future Discord/Telegram workers can
    drain it without needing to hook into the Control Plane directly.
    """

    def __init__(self, path: str = NOTIFICATION_QUEUE) -> None:
        self.path = path

    def notify(self, action: Action) -> dict:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        record = {
            "notified_at": datetime.now(timezone.utc).isoformat(),
            "channel": "file",
            "action_id": action.id,
            "type": action.type,
            "description": action.description,
            "risk_level": action.risk_level,
            "source_agent": action.source_agent,
            "approve_cmd": (f"python3 /opt/OS/scripts/deferred.py approve {action.id}"),
        }
        with open(self.path, "a") as f:
            f.write(json.dumps(record, default=str) + "\n")
        return {"ok": True, "channel": "file", "path": self.path}


class DiscordNotifier:
    """Best-effort Discord webhook notifier.

    Reads DISCORD_APPROVAL_WEBHOOK_URL from the environment. If unset or
    the POST fails, returns {"ok": False, "reason": ...} but never raises.
    Wrap alongside a FileNotifier in a MultiNotifier for durability.
    """

    def __init__(self, webhook_url: str | None = None) -> None:
        self.webhook_url = webhook_url or os.getenv("DISCORD_APPROVAL_WEBHOOK_URL")

    def notify(self, action: Action) -> dict:
        if not self.webhook_url:
            return {"ok": False, "reason": "no webhook url configured"}
        try:
            import urllib.request

            payload = {
                "content": (
                    f"**Control Plane — approval required**\n"
                    f"`{action.risk_level.upper()}` {action.type} "
                    f"from `{action.source_agent}`\n"
                    f"> {action.description}\n"
                    f"Approve: `python3 /opt/OS/scripts/deferred.py approve {action.id}`"
                )
            }
            data = json.dumps(payload).encode()
            req = urllib.request.Request(
                self.webhook_url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as r:
                return {"ok": 200 <= r.status < 300, "status": r.status}
        except Exception as e:
            return {"ok": False, "reason": f"{type(e).__name__}: {e}"}


class MultiNotifier:
    """Fan out to multiple notifiers. First-failure is captured but not raised."""

    def __init__(self, notifiers: list[Notifier]) -> None:
        self.notifiers = list(notifiers)

    def notify(self, action: Action) -> dict:
        results = []
        for n in self.notifiers:
            results.append({"impl": type(n).__name__, "result": n.notify(action)})
        return {"ok": all(r["result"].get("ok") for r in results), "results": results}


def default_notifier() -> Notifier:
    """Return the default notifier stack: File always, Discord if configured.

    This is what run_action uses when no notifier is passed explicitly.
    """
    stack: list[Notifier] = [FileNotifier()]
    if os.getenv("DISCORD_APPROVAL_WEBHOOK_URL"):
        stack.append(DiscordNotifier())
    return MultiNotifier(stack)
