#!/usr/bin/env bash
# Stop hook for LOCAL CC sessions (Windows WSL) — reads last assistant message
# from CC transcript, POSTs to VPS webhook receiver via Tailscale.
#
# Install on Windows WSL:
#   cp this file to ~/.claude/hooks/send-to-discord.sh
#   Add to ~/.claude/settings.json Stop hooks:
#     {"type": "command", "command": "bash ~/.claude/hooks/send-to-discord.sh", "timeout": 10}

set -euo pipefail

# VPS Tailscale IP — where the Discord webhook receiver runs
VPS_WEBHOOK_URL="${EOS_VPS_WEBHOOK_URL:-http://100.77.233.50:8765/cc-reply}"

# Read stdin (hook input JSON)
INPUT=$(cat)

export TRANSCRIPT_PATH=$(echo "$INPUT" | python3 -c "import sys,json; print(json.loads(sys.stdin.read()).get('transcript_path',''))" 2>/dev/null)

if [ -z "$TRANSCRIPT_PATH" ] || [ ! -f "$TRANSCRIPT_PATH" ]; then
    exit 0
fi

# Determine which tmux session we're in (maps to Discord channel)
export TMUX_SESSION=$(tmux display-message -p '#S' 2>/dev/null || echo "")
if [ -z "$TMUX_SESSION" ]; then
    # Not in tmux — use a default session name
    export TMUX_SESSION="dex_local"
fi

export VPS_WEBHOOK_URL

# Extract last assistant message text from JSONL and POST to VPS webhook
python3 << 'PYEOF'
import json
import sys
import urllib.request
import os

transcript_path = os.environ.get("TRANSCRIPT_PATH", "")
tmux_session = os.environ.get("TMUX_SESSION", "")
vps_url = os.environ.get("VPS_WEBHOOK_URL", "http://100.77.233.50:8765/cc-reply")

if not transcript_path or not tmux_session:
    sys.exit(0)

# Read JSONL backwards to find last assistant message with end_turn
last_text = ""
try:
    with open(transcript_path, "r") as f:
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

        content = msg.get("content", [])
        text_parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text_parts.append(block["text"])

        if text_parts:
            last_text = "\n".join(text_parts).strip()
            break

except Exception:
    sys.exit(0)

if not last_text:
    sys.exit(0)

# POST to VPS webhook receiver via Tailscale
payload = json.dumps({
    "session_name": tmux_session,
    "text": last_text,
}).encode("utf-8")

req = urllib.request.Request(
    vps_url,
    data=payload,
    headers={"Content-Type": "application/json"},
    method="POST",
)

try:
    urllib.request.urlopen(req, timeout=5)
except Exception:
    # VPS might be unreachable — fail silently
    pass
PYEOF
