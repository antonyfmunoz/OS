#!/usr/bin/env python3
"""
Stop hook: POST last assistant message to the CC webhook receiver.

Mirrors local_bridge_send_to_discord.sh behavior for VPS sessions.
The webhook receiver maps session_name → Discord channel and delivers.

Input (stdin JSON): Claude Code stop hook payload
Output: exits 0 always — never blocks the stop hook chain.
"""

import json
import os
import subprocess
import sys
import urllib.request

WEBHOOK_URL = os.getenv("EOS_VPS_WEBHOOK_URL", "http://127.0.0.1:8765/cc-reply")
MIN_TEXT_LENGTH = 10


def _read_payload() -> dict:
    try:
        return json.load(sys.stdin)
    except Exception:
        return {}


def _get_session_name() -> str:
    name = os.getenv("SESSION_NAME", "")
    if name:
        return name
    try:
        result = subprocess.run(
            ["tmux", "display-message", "-p", "#S"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    return "dex_main"


def _extract_from_payload(payload: dict) -> str:
    text = payload.get("last_assistant_message", "")
    if isinstance(text, str) and text.strip():
        return text.strip()
    return ""


def _extract_from_transcript(path: str) -> str:
    if not path or not os.path.isfile(path):
        return ""
    try:
        with open(path) as f:
            lines = f.readlines()
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if record.get("type") != "assistant":
                continue
            msg = record.get("message", {})
            if msg.get("stop_reason") != "end_turn":
                continue
            parts = []
            for block in msg.get("content", []):
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(block["text"])
            if parts:
                return "\n".join(parts).strip()
    except Exception:
        pass
    return ""


def main() -> None:
    payload = _read_payload()

    text = _extract_from_payload(payload)
    if not text:
        text = _extract_from_transcript(payload.get("transcript_path", ""))
    if not text or len(text) < MIN_TEXT_LENGTH:
        sys.exit(0)

    session_name = _get_session_name()

    body = json.dumps(
        {
            "session_name": session_name,
            "text": text,
            "source": "vps_stop_hook",
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        WEBHOOK_URL,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass

    sys.exit(0)


if __name__ == "__main__":
    main()
