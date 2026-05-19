#!/usr/bin/env bash
# Launch UMH backend API on port 8093.
#
# Usage:
#   ./launch_backend.sh          # foreground
#   ./launch_backend.sh --bg     # background (detached)
#
# Requires: uvicorn, fastapi, pydantic (all in requirements.txt)
# The umh_mvp package must be on PYTHONPATH (repo root handles this).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${SCRIPT_DIR}/../../.."
PORT="${JARVIS_BACKEND_PORT:-8093}"
HOST="${JARVIS_BACKEND_HOST:-0.0.0.0}"

cd "$REPO_ROOT"

# Check if port is already in use
if ss -tlnp 2>/dev/null | grep -q ":${PORT} "; then
    echo "Port ${PORT} is already in use."
    echo "To restart: kill the existing process first, then re-run."
    ss -tlnp | grep ":${PORT} "
    exit 1
fi

# Verify imports before launching
python3 -c "
import sys
sys.path.insert(0, '.')
from umh_mvp.api.app import app
print('Import check passed — app ready')
" || { echo "Import check failed"; exit 1; }

echo "Starting UMH backend on ${HOST}:${PORT}..."

if [[ "${1:-}" == "--bg" ]]; then
    nohup python3 -m uvicorn umh_mvp.api.app:app \
        --host "$HOST" --port "$PORT" --reload \
        > /opt/OS/logs/umh_backend.log 2>&1 &
    echo "PID: $!"
    echo "Log: /opt/OS/logs/umh_backend.log"
else
    exec python3 -m uvicorn umh_mvp.api.app:app \
        --host "$HOST" --port "$PORT" --reload
fi
