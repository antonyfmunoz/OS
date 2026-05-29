"""Report dispatcher — sends task completion reports to Discord + cockpit chat.

The organism calls dispatch_report() after any task completion. Reports flow to:
  1. Discord Founders Office channel (as file attachment + summary)
  2. Cockpit chat (as system message visible in ChatDrawer)
  3. Organism store (persisted in messages.jsonl for history)

This is a substrate module. It uses abstract ports (channel_port) for Discord
and writes directly to OrganismStore for cockpit chat. No transport imports.
"""

from __future__ import annotations

import io
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from substrate.sockets.notification import push_chat
from substrate.state.business.business_instance import get_ai_name

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")


@dataclass
class Report:
    title: str
    summary: str
    body: str
    file_path: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


@dataclass
class DispatchResult:
    discord_sent: bool = False
    cockpit_sent: bool = False
    store_saved: bool = False
    errors: list[str] = field(default_factory=list)

    @property
    def all_succeeded(self) -> bool:
        return self.discord_sent and self.cockpit_sent and self.store_saved

    def to_dict(self) -> dict[str, Any]:
        return {
            "discord_sent": self.discord_sent,
            "cockpit_sent": self.cockpit_sent,
            "store_saved": self.store_saved,
            "errors": self.errors,
            "all_succeeded": self.all_succeeded,
        }


class ReportDispatcher:
    """Dispatches reports to Discord and cockpit chat."""

    def __init__(
        self,
        store_dir: str | Path = "data/umh/organism",
        discord_token: str | None = None,
        discord_channel_id: str | None = None,
    ) -> None:
        self._store_dir = Path(store_dir)
        self._store_dir.mkdir(parents=True, exist_ok=True)
        self._messages_path = self._store_dir / "messages.jsonl"
        self._reports_path = self._store_dir / "reports.jsonl"
        self._reports_path.parent.mkdir(parents=True, exist_ok=True)

        self._discord_token = discord_token or self._load_env("DISCORD_BOT_TOKEN")
        self._discord_channel_id = discord_channel_id or self._load_env("DISCORD_FOUNDERS_OFFICE")

    @staticmethod
    def _load_env(key: str) -> str:
        val = os.environ.get(key, "")
        if val:
            return val
        env_path = os.path.join(_REPO_ROOT, "services", ".env")
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith(f"{key}="):
                        return line.split("=", 1)[1].strip()
        return ""

    def dispatch_report(self, report: Report) -> DispatchResult:
        """Send report to all channels. Returns per-channel success status."""
        result = DispatchResult()

        result.store_saved = self._save_to_store(report)
        result.cockpit_sent = self._send_to_cockpit(report)
        discord_ok, discord_err = self._send_to_discord(report)
        result.discord_sent = discord_ok
        if discord_err:
            result.errors.append(discord_err)

        level = logging.INFO if result.all_succeeded else logging.WARNING
        logger.log(
            level,
            "Report dispatched: discord=%s cockpit=%s store=%s title='%s'",
            result.discord_sent, result.cockpit_sent, result.store_saved, report.title,
        )
        return result

    def _save_to_store(self, report: Report) -> bool:
        try:
            record = {
                "id": str(uuid4()),
                "type": "report",
                "title": report.title,
                "summary": report.summary,
                "file_path": report.file_path,
                "metadata": report.metadata,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            with open(self._reports_path, "a") as f:
                f.write(json.dumps(record, default=str, separators=(",", ":")) + "\n")
            return True
        except Exception as e:
            logger.error("Failed to save report to store: %s", e)
            return False

    def _send_to_cockpit(self, report: Report) -> bool:
        """Write an AI message to messages.jsonl so the cockpit chat picks it up."""
        try:
            ai_name = get_ai_name().lower() or "system"
            msg = {
                "id": str(uuid4()),
                "sender": ai_name,
                "recipient": "operator",
                "intent": "report",
                "payload": {
                    "title": report.title,
                    "summary": report.summary,
                    "file_path": report.file_path,
                    "metadata": report.metadata,
                    "source": "cockpit_dex_channel",
                },
                "conversation_id": str(uuid4()),
                "parent_message_id": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            with open(self._messages_path, "a") as f:
                f.write(json.dumps(msg, default=str, separators=(",", ":")) + "\n")
            try:
                push_chat(msg)
            except Exception as ws_exc:
                logger.debug("WS push for report failed (non-fatal): %s", ws_exc)
            return True
        except Exception as e:
            logger.error("Failed to send report to cockpit: %s", e)
            return False

    def _send_to_discord(self, report: Report) -> tuple[bool, str]:
        """Send report to Discord as file attachment + summary message."""
        if not self._discord_token or not self._discord_channel_id:
            return False, "Discord credentials not configured"

        try:
            import requests
            url = f"https://discord.com/api/v10/channels/{self._discord_channel_id}/messages"
            headers = {"Authorization": f"Bot {self._discord_token}"}

            files_dict: dict[str, Any] = {}
            if report.file_path and os.path.exists(report.file_path):
                resolved = os.path.realpath(report.file_path)
                allowed_roots = [
                    os.path.realpath(os.path.join(_REPO_ROOT, "docs")),
                    os.path.realpath(os.path.join(_REPO_ROOT, "data")),
                ]
                if not any(resolved.startswith(root + os.sep) for root in allowed_roots):
                    return False, f"file_path outside allowed directories: {resolved}"
                if os.path.islink(report.file_path):
                    return False, "symlinks not allowed for report files"
                filename = os.path.basename(resolved)
                files_dict["files[0]"] = (filename, open(resolved, "rb"), "text/markdown")
            elif report.body:
                safe_title = report.title.replace(" ", "_").replace("/", "_")[:50]
                filename = f"{safe_title}.md"
                files_dict["files[0]"] = (filename, io.BytesIO(report.body.encode()), "text/markdown")

            content = report.summary[:2000]
            resp = requests.post(url, headers=headers, data={"content": content}, files=files_dict, timeout=10)

            if resp.status_code in (200, 201):
                return True, ""
            return False, f"Discord API returned {resp.status_code}: {resp.text[:200]}"

        except Exception as e:
            return False, f"Discord send failed: {e}"

    def list_reports(self, limit: int = 20) -> list[dict[str, Any]]:
        """List recent reports from store."""
        if not self._reports_path.exists():
            return []
        entries: list[dict[str, Any]] = []
        with open(self._reports_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
        return entries[-limit:]
