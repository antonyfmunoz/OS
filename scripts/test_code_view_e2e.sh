#!/usr/bin/env bash
# E2E test for operator-ui Code View backend
# Starts the server, exercises /api/code endpoints, verifies responses.
#
# Usage: bash scripts/test_code_view_e2e.sh
# Exit 0 = all pass, non-zero = failure

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
UI_DIR="$ROOT_DIR/operator-ui"
PORT=${TEST_PORT:-8092}
SERVER_PID=""
PASS=0
FAIL=0

cleanup() {
  if [[ -n "$SERVER_PID" ]]; then
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

echo "=== Operator UI Code View E2E Test ==="
echo ""

# ── Start server ──────────────────────────────────────────────────────────────
echo "[1/5] Starting backend server..."
cd "$UI_DIR"
APP_ROOT="$ROOT_DIR" PORT=$PORT npx tsx src/server/index.ts &
SERVER_PID=$!

# Wait for server to be ready
for i in $(seq 1 20); do
  if curl -sf "http://localhost:$PORT/api/health" >/dev/null 2>&1; then
    echo "       Server ready (attempt $i)"
    break
  fi
  if [[ $i -eq 20 ]]; then
    echo "FAIL: Server did not start within 10s"
    exit 1
  fi
  sleep 0.5
done

# ── Test: Health ──────────────────────────────────────────────────────────────
echo "[2/5] Testing /api/health..."
HEALTH=$(curl -sf "http://localhost:$PORT/api/health")
if echo "$HEALTH" | grep -q '"status":"ok"'; then
  echo "       PASS: health endpoint"
  PASS=$((PASS + 1))
else
  echo "       FAIL: health returned: $HEALTH"
  FAIL=$((FAIL + 1))
fi

# ── Test: Read ────────────────────────────────────────────────────────────────
echo "[3/5] Testing /api/code/read (reading package.json)..."
READ_RESULT=$(curl -sf -X POST "http://localhost:$PORT/api/code/read" \
  -H "Content-Type: application/json" \
  -d '{"path":"operator-ui/package.json"}')

if echo "$READ_RESULT" | grep -q 'operator-ui'; then
  echo "       PASS: read returned file content"
  PASS=$((PASS + 1))
else
  echo "       FAIL: read returned: $READ_RESULT"
  FAIL=$((FAIL + 1))
fi

# ── Test: Execute ─────────────────────────────────────────────────────────────
echo "[4/5] Testing /api/code/execute (echo hello)..."
EXEC_RESULT=$(curl -sf -X POST "http://localhost:$PORT/api/code/execute" \
  -H "Content-Type: application/json" \
  -d '{"command":"echo hello"}')

if echo "$EXEC_RESULT" | grep -q 'hello'; then
  echo "       PASS: execute returned hello"
  PASS=$((PASS + 1))
else
  echo "       FAIL: execute returned: $EXEC_RESULT"
  FAIL=$((FAIL + 1))
fi

# ── Test: List ────────────────────────────────────────────────────────────────
echo "[5/5] Testing /api/code/list (listing root)..."
LIST_RESULT=$(curl -sf -X POST "http://localhost:$PORT/api/code/list" \
  -H "Content-Type: application/json" \
  -d '{"path":"."}')

if echo "$LIST_RESULT" | grep -q '"entries"'; then
  echo "       PASS: list returned entries"
  PASS=$((PASS + 1))
else
  echo "       FAIL: list returned: $LIST_RESULT"
  FAIL=$((FAIL + 1))
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="

if [[ $FAIL -gt 0 ]]; then
  exit 1
fi
exit 0
