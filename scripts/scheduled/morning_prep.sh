#!/bin/bash
# EOS Morning Prep — runs 5:30am via cron
# Verifies system is ready before Antony's day starts

set -euo pipefail

LOG="/opt/OS/logs/morning_$(date +%Y%m%d).log"
echo "=== EOS Morning Prep: $(date) ===" >> "$LOG"

cd /opt/OS

claude -p --allowedTools "Bash Read Glob Grep" \
  --add-dir /opt/OS \
  --max-budget-usd 0.30 \
  "Read /opt/OS/.claude/CLAUDE.md.

Run EOS morning preparation. Fix anything broken. Report final status.

Step 1 — Container check:
  docker ps --format '{{.Names}}: {{.Status}}'
  Any container not Up → docker compose restart [service], wait 10s, check again.

Step 2 — API key check:
  python3 -c \"
import os; from pathlib import Path
from dotenv import load_dotenv
load_dotenv('/opt/OS/eos_ai/.env')
key = os.getenv('ANTHROPIC_API_KEY','')
print('Anthropic key:', 'set' if key else 'MISSING')
\"

Step 3 — Neon connection check:
  python3 -c \"
import sys; sys.path.insert(0,'/opt/OS')
from eos_ai.db import get_conn
from eos_ai.context import load_context_from_env
ctx = load_context_from_env()
with get_conn(ctx.org_id) as cur:
  cur.execute('SELECT 1')
  print('Neon: connected')
\"

Step 4 — GWS auth check:
  python3 -c \"
import sys; sys.path.insert(0,'/opt/OS')
from eos_ai.gws_connector import GWSConnector
from eos_ai.context import load_context_from_env
ctx = load_context_from_env()
gws = GWSConnector(ctx)
status = gws.check_auth()
print('GWS:', status)
\" 2>/dev/null || echo 'GWS: check skipped'

Step 5 — Final status:
  Print one line: 'SYSTEM READY' or list each issue." >> "$LOG" 2>&1

echo "=== Done: $(date) ===" >> "$LOG"
