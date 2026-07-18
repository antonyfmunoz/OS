#!/usr/bin/env python3
"""
UMH Model Watchdog — detects Claude Code model downgrades and forces recovery.

Monitors active CC session transcript JSONL files for model switches away from
the target model (default: claude-fable-5). When a downgrade is detected:

1. Writes the target model back into settings.json (hot-reloaded by CC per turn)
2. Logs the event with timestamp, session ID, and downgraded model
3. Sends a Discord notification via the local webhook receiver

The server-side routing can substitute a different model when the target is
overloaded. This daemon can't prevent that substitution (it happens at the API
layer), but it ensures the NEXT turn requests the right model again by keeping
settings.json authoritative.

Install: bash scripts/install-model-watchdog.sh
Logs:    /opt/OS/logs/model_watchdog.log
"""

import json
import os
import subprocess
import sys
import time
import signal
import urllib.request
from pathlib import Path
from typing import Optional

LOG_FILE = "/opt/OS/logs/model_watchdog.log"
SETTINGS_FILE = os.path.expanduser("~/.claude/settings.json")
PROJECTS_DIR = os.path.expanduser("~/.claude/projects")
ROSTER_FILE = os.path.expanduser("~/.claude/daemon/roster.json")
WEBHOOK_URL = "http://127.0.0.1:8765/cc-reply"
POLL_INTERVAL = 5  # seconds between checks
COOLDOWN = 30  # seconds between corrections for the same session

TARGET_MODEL = os.environ.get("MODEL_WATCHDOG_TARGET", "claude-fable-5")

# Track state per session to avoid spamming
_last_correction: dict[str, float] = {}
_last_file_pos: dict[str, int] = {}
_running = True


def log(msg: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts} [model-watchdog] {msg}"
    print(line, flush=True)
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


def notify_discord(msg: str) -> None:
    try:
        payload = json.dumps({
            "session_name": "model-watchdog",
            "text": msg,
        }).encode("utf-8")
        req = urllib.request.Request(
            WEBHOOK_URL,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass


def get_active_sessions() -> list[dict]:
    """Get active CC sessions from the daemon roster."""
    try:
        result = subprocess.run(
            ["claude", "agents", "--json"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            sessions = json.loads(result.stdout)
            return [s for s in sessions if s.get("state") in ("working", "busy", "idle")]
    except Exception:
        pass
    return []


def find_transcript(session_id: str) -> Optional[str]:
    """Find the transcript JSONL for a session ID."""
    projects = Path(PROJECTS_DIR)
    if not projects.exists():
        return None
    for proj_dir in projects.iterdir():
        if not proj_dir.is_dir():
            continue
        candidate = proj_dir / f"{session_id}.jsonl"
        if candidate.exists():
            return str(candidate)
    return None


def find_all_active_transcripts() -> list[tuple[str, str]]:
    """Find transcript files for all active sessions. Returns (session_id, path) pairs."""
    results = []
    sessions = get_active_sessions()
    for s in sessions:
        sid = s.get("sessionId", "")
        if not sid:
            continue
        path = find_transcript(sid)
        if path:
            results.append((sid, path))
    return results


def check_transcript_tail(path: str, session_id: str) -> Optional[str]:
    """Read new lines from a transcript and return the last non-target model found."""
    last_pos = _last_file_pos.get(path, 0)

    try:
        file_size = os.path.getsize(path)
    except OSError:
        return None

    if file_size <= last_pos:
        if file_size < last_pos:
            _last_file_pos[path] = 0
            last_pos = 0
        else:
            return None

    wrong_model = None
    try:
        with open(path, "r") as f:
            f.seek(last_pos)
            new_data = f.read()
            _last_file_pos[path] = f.tell()

        for line in new_data.strip().split("\n"):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            if record.get("type") != "assistant":
                continue

            msg = record.get("message", {})
            if not isinstance(msg, dict):
                continue

            model = msg.get("model", "")
            if not model or model == "<synthetic>":
                continue

            if not model.startswith(TARGET_MODEL):
                wrong_model = model

    except Exception as e:
        log(f"Error reading {path}: {e}")

    return wrong_model


def ensure_settings_model() -> bool:
    """Ensure settings.json has the target model. Returns True if changed."""
    try:
        with open(SETTINGS_FILE, "r") as f:
            settings = json.load(f)
    except Exception:
        return False

    current = settings.get("model", "")
    if current.startswith(TARGET_MODEL):
        return False

    # Preserve the thinking suffix if present in the current setting
    suffix = ""
    if "[" in current:
        suffix = current[current.index("["):]
    elif not current.startswith(TARGET_MODEL):
        # Use the default thinking suffix
        suffix = "[1m]"

    new_model = TARGET_MODEL + suffix
    settings["model"] = new_model

    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=4)
        log(f"settings.json model corrected: {current} -> {new_model}")
        return True
    except Exception as e:
        log(f"Failed to update settings.json: {e}")
        return False


def handle_downgrade(session_id: str, wrong_model: str) -> None:
    """Handle a detected model downgrade."""
    now = time.time()
    last = _last_correction.get(session_id, 0)
    if now - last < COOLDOWN:
        return

    _last_correction[session_id] = now

    short_id = session_id[:8]
    log(f"DOWNGRADE DETECTED: session {short_id} running {wrong_model} instead of {TARGET_MODEL}")

    changed = ensure_settings_model()

    msg = (
        f"**Model Watchdog Alert**\n"
        f"Session `{short_id}` was downgraded to `{wrong_model}`.\n"
        f"Target: `{TARGET_MODEL}`\n"
    )
    if changed:
        msg += "settings.json corrected — next turn will request target model."
    else:
        msg += "settings.json already correct — server-side routing override."

    notify_discord(msg)


def signal_handler(sig, frame):
    global _running
    log("Received shutdown signal")
    _running = False


def main() -> None:
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    log(f"Started. Target model: {TARGET_MODEL}")
    log(f"Poll interval: {POLL_INTERVAL}s, cooldown: {COOLDOWN}s")

    # Initial settings check
    ensure_settings_model()

    consecutive_empty = 0
    while _running:
        try:
            transcripts = find_all_active_transcripts()

            if not transcripts:
                consecutive_empty += 1
                if consecutive_empty == 1:
                    log("No active sessions found — watching...")
            else:
                consecutive_empty = 0

            for session_id, path in transcripts:
                wrong_model = check_transcript_tail(path, session_id)
                if wrong_model:
                    handle_downgrade(session_id, wrong_model)

        except Exception as e:
            log(f"Error in main loop: {e}")

        time.sleep(POLL_INTERVAL)

    log("Stopped.")


if __name__ == "__main__":
    main()
