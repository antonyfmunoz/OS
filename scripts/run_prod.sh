#!/bin/bash
# UMH Production Runner
# Starts API server with worker auto-start, restarts on crash.
#
# Usage:
#   ./scripts/run_prod.sh              # foreground
#   ./scripts/run_prod.sh &            # background
#   tmux new -d -s umh ./scripts/run_prod.sh  # tmux (recommended)

set -euo pipefail

cd ${UMH_ROOT:-/opt/OS}

# Config
PORT="${UMH_API_PORT:-8000}"
HOST="${UMH_API_HOST:-127.0.0.1}"
LOG_DIR="${UMH_LOG_DIR:-${UMH_ROOT:-/opt/OS}/data/logs}"
RESTART_DELAY=3
MAX_RESTARTS=50
RESTART_COUNT=0

# Ensure dirs
mkdir -p "$LOG_DIR"
mkdir -p ${UMH_ROOT:-/opt/OS}/data/runtime

echo "============================================"
echo "UMH Production Server"
echo "============================================"
echo "  API:    http://${HOST}:${PORT}"
echo "  UI:     http://${HOST}:${PORT}/ui/"
echo "  Logs:   ${LOG_DIR}/"
echo "  Worker: auto-start enabled"
echo "============================================"
echo ""

# Export for worker auto-start
export UMH_WORKER_AUTO_START=true

while [ "$RESTART_COUNT" -lt "$MAX_RESTARTS" ]; do
    echo "[$(date -Iseconds)] Starting UMH server (restart #${RESTART_COUNT})..."

    python3 -m uvicorn umh.control.api:app \
        --host "$HOST" \
        --port "$PORT" \
        --log-level info \
        --access-log \
        2>&1 | tee -a "${LOG_DIR}/umh_server.log" || true

    RESTART_COUNT=$((RESTART_COUNT + 1))
    echo "[$(date -Iseconds)] Server exited. Restarting in ${RESTART_DELAY}s... (${RESTART_COUNT}/${MAX_RESTARTS})"
    sleep "$RESTART_DELAY"
done

echo "[$(date -Iseconds)] Max restarts ($MAX_RESTARTS) reached. Exiting."
exit 1
