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
LOG_FILE="/opt/OS/logs/nightly_consolidation.log"
SCRIPT="/opt/OS/scripts/nightly_consolidation.py"

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

cd /opt/OS
python3 "$SCRIPT" $ARGS >> "$LOG_FILE" 2>&1
EXIT_CODE=$?

echo "[$(date -Iseconds)] END: exit code ${EXIT_CODE}" >> "$LOG_FILE"
echo "---" >> "$LOG_FILE"

exit $EXIT_CODE
