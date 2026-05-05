#!/bin/bash
# Start UMH with UI
# Usage: ./scripts/run_ui.sh [port]

PORT=${1:-8000}
echo "Starting UMH Control Plane + UI on port $PORT"
echo "UI: http://localhost:$PORT/ui/"
echo "API: http://localhost:$PORT/"
echo ""

cd /opt/OS
python3 -m uvicorn umh.control.api:app --host 127.0.0.1 --port $PORT --reload
