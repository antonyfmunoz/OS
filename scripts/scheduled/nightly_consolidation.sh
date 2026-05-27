#!/usr/bin/env bash
# ─── Nightly Memory Consolidation ─────────────────────────────────────────────
#
# Runs the memory pipeline: summarize conversations → promote to wiki.
# Scheduled via cron. Uses flock to prevent overlapping runs.
#
# Usage:
#   bash scripts/scheduled/nightly_consolidation.sh           # normal run
#   bash scripts/scheduled/nightly_consolidation.sh --dry-run  # preview only
#
# To disable: comment out the cron line or remove the script.
# Logs: /opt/OS/logs/nightly_consolidation.log
# Lock: /tmp/eos_nightly_consolidation.lock (auto-released on exit/crash)
# ──────────────────────────────────────────────────────────────────────────────

set -euo pipefail

LOCK_FILE="/tmp/eos_nightly_consolidation.lock"
LOG_FILE="${UMH_ROOT:-/opt/OS}/logs/nightly_consolidation.log"
SCRIPT="${UMH_ROOT:-/opt/OS}/scripts/nightly_consolidation.py"

# Pass through args (e.g. --dry-run)
ARGS="${*}"

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")"

# flock --nonblock: if another instance is running, exit immediately
exec 200>"$LOCK_FILE"
if ! flock --nonblock 200; then
    echo "[$(date -Iseconds)] SKIP: another consolidation is already running" >> "$LOG_FILE"
    exit 0
fi

echo "[$(date -Iseconds)] START: nightly consolidation ${ARGS}" >> "$LOG_FILE"

cd ${UMH_ROOT:-/opt/OS}

# Substrate: start close_day ritual (additive, failures non-fatal).
RITUAL_ID="$(python3 -m runtime.substrate.ritual_runner close_day start 2>>"$LOG_FILE" || true)"
echo "[$(date -Iseconds)] close_day ritual_id=${RITUAL_ID:-none}" >> "$LOG_FILE"

# Provider health gate — consolidation requires LLMs for summarization
if ! python3 -c "
import sys; import os; sys.path.insert(0, os.environ.get('UMH_ROOT') or '/opt/OS')
from dotenv import load_dotenv; load_dotenv(os.path.join(os.environ.get('UMH_ROOT', '/opt/OS'), 'services/.env'))
from runtime.provider_health import check_all
sys.exit(0 if check_all().any_healthy else 1)
" 2>/dev/null; then
  echo "[$(date -Iseconds)] SKIP nightly_consolidation: no healthy LLM provider" >> "$LOG_FILE"
  exit 0
fi

python3 "$SCRIPT" $ARGS >> "$LOG_FILE" 2>&1
EXIT_CODE=$?

echo "[$(date -Iseconds)] END: exit code ${EXIT_CODE}" >> "$LOG_FILE"

# Substrate: finish close_day ritual (additive, failures non-fatal).
if [ -n "${RITUAL_ID:-}" ]; then
  if [ "$EXIT_CODE" -eq 0 ]; then
    python3 -m runtime.substrate.ritual_runner close_day finish "$RITUAL_ID" 2>>"$LOG_FILE" || true
  else
    python3 -c "
import sys; import os; sys.path.insert(0, os.environ.get('UMH_ROOT') or '/opt/OS')
from runtime.substrate.ritual_runner import fail_ritual
fail_ritual('$RITUAL_ID', 'nightly_consolidation exit=$EXIT_CODE')
" 2>>"$LOG_FILE" || true
  fi
fi

echo "---" >> "$LOG_FILE"

exit $EXIT_CODE
