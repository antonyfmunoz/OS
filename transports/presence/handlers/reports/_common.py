"""Shared imports and helpers for report handler modules."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

logger = logging.getLogger(__name__)


def _log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"[{ts}] [substrate-handler] {msg}", flush=True)


async def _wait_for_founder_confirmation(message: Any, report_name: str) -> str:
    """Wait for founder YES/NO reply within 60 seconds."""
    await message.channel.send(
        "**Founder confirmation required.**\n"
        f"Approve {report_name} proof escalation?\n"
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
        return response.content.strip().lower()
    except asyncio.TimeoutError:
        await message.channel.send(f"{report_name} confirmation timed out.")
        return "timeout"
    except AttributeError:
        await message.channel.send("Could not access bot for confirmation — skipping.")
        return "timeout"
