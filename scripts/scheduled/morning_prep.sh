#!/bin/bash
# EOS Morning Prep — runs 5:30am via cron
# Verifies system is ready before Antony's day starts

set -euo pipefail

LOG="${UMH_ROOT:-/opt/OS}/logs/morning_$(date +%Y%m%d).log"
echo "=== EOS Morning Prep: $(date) ===" >> "$LOG"

cd ${UMH_ROOT:-/opt/OS}

# Substrate: start open_day ritual (additive, failures non-fatal).
RITUAL_ID="$(python3 -m runtime.substrate.ritual_runner open_day start 2>>"$LOG" || true)"
echo "[$(date -Iseconds)] open_day ritual_id=${RITUAL_ID:-none}" >> "$LOG"

# Provider health gate — skip if no LLM provider is reachable
if ! python3 -c "
import sys; import os; sys.path.insert(0, os.environ.get('UMH_ROOT') or '/opt/OS')
from dotenv import load_dotenv; load_dotenv(os.path.join(os.environ.get('UMH_ROOT', '/opt/OS'), 'services/.env'))
from runtime.provider_health import check_all
sys.exit(0 if check_all().any_healthy else 1)
" 2>/dev/null; then
  echo "[$(date -Iseconds)] SKIP morning_prep: no healthy LLM provider" >> "$LOG"
  exit 0
fi

claude -p --allowedTools "Bash Read Glob Grep" \
  --add-dir ${UMH_ROOT:-/opt/OS} \
  --max-budget-usd 0.30 \
  "Read ${UMH_ROOT:-/opt/OS}/.claude/CLAUDE.md.

Run EOS morning preparation. Fix anything broken. Report final status.

Step 1 — Container check:
  docker ps --format '{{.Names}}: {{.Status}}'
  Any container not Up → docker compose restart [service], wait 10s, check again.

Step 2 — API key check:
  python3 -c \"
import os; from pathlib import Path
from dotenv import load_dotenv
load_dotenv(os.path.join(os.environ.get('UMH_ROOT', '/opt/OS'), 'services/.env'))
key = os.getenv('ANTHROPIC_API_KEY','')
print('Anthropic key:', 'set' if key else 'MISSING')
\"

Step 3 — Neon connection check:
  python3 -c \"
import sys; import os; sys.path.insert(0, os.environ.get('UMH_ROOT') or '/opt/OS')
from runtime.db import get_conn
from runtime.context import load_context_from_env
ctx = load_context_from_env()
with get_conn(ctx.org_id) as cur:
  cur.execute('SELECT 1')
  print('Neon: connected')
\"

Step 4 — GWS auth check:
  python3 -c \"
import sys; import os; sys.path.insert(0, os.environ.get('UMH_ROOT') or '/opt/OS')
from runtime.gws_connector import GWSConnector
gws = GWSConnector()
status = 'ok' if gws else 'unavailable'
print('GWS:', status)
\" 2>/dev/null || echo 'GWS: check skipped'

Step 5 — Final status:
  Print one line: 'SYSTEM READY' or list each issue." >> "$LOG" 2>&1

echo "=== Done: $(date) ===" >> "$LOG"

# Substrate: finish open_day ritual (additive, failures non-fatal).
if [ -n "${RITUAL_ID:-}" ]; then
  python3 -m runtime.substrate.ritual_runner open_day finish "$RITUAL_ID" 2>>"$LOG" || true
fi
