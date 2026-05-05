#!/bin/bash
# UMH Health Check
# Usage: ./scripts/healthcheck.sh [port]

PORT="${1:-8000}"
HOST="${UMH_API_HOST:-127.0.0.1}"

# API health
API_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://${HOST}:${PORT}/health" 2>/dev/null || echo "000")

if [ "$API_STATUS" = "200" ]; then
    echo "API: OK"
else
    echo "API: FAIL (status=$API_STATUS)"
    exit 1
fi

# Worker health (requires API key)
if [ -n "${UMH_API_KEY:-}" ]; then
    WORKER_STATUS=$(curl -s -H "X-API-Key: $UMH_API_KEY" "http://${HOST}:${PORT}/worker/health" 2>/dev/null)
    if echo "$WORKER_STATUS" | grep -q '"is_running": true'; then
        echo "Worker: OK"
    else
        echo "Worker: NOT RUNNING"
    fi
fi

echo "Health check passed."
exit 0
