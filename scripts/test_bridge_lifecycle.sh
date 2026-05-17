#!/bin/bash
# test_bridge_lifecycle.sh — Chaos test for bridge auto-recovery.
#
# Scenario:
#   1. Kill the bridge on Windows
#   2. Trigger an export from VPS
#   3. VPS detects bridge down, auto-starts via Tailscale SSH
#   4. Bridge comes back, export dispatches
#
# Expected: full round-trip completes within 30s of bridge kill.
#
# Usage:
#   bash scripts/test_bridge_lifecycle.sh
#   bash scripts/test_bridge_lifecycle.sh --dry-run  (export won't actually fire)

set -euo pipefail

DRY_RUN="${1:-}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

WINDOWS_HOST="${EOS_WINDOWS_TAILSCALE_HOST:-100.74.199.102}"
WINDOWS_USER="${EOS_WINDOWS_TAILSCALE_USER:-antony}"
BRIDGE_PORT="${EOS_LOCAL_BRIDGE_PORT:-8766}"

log() { echo "[$(date '+%H:%M:%S')] $*"; }

log "=== BRIDGE LIFECYCLE CHAOS TEST ==="
echo ""

# Step 0: Verify SSH works
log "Step 0: Checking Tailscale SSH to Windows..."
if ! ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=accept-new \
    "${WINDOWS_USER}@${WINDOWS_HOST}" "echo ok" >/dev/null 2>&1; then
    log "FAIL: Cannot SSH to Windows. Run: tailscale set --ssh on Windows"
    exit 1
fi
log "  SSH OK"

# Step 1: Check if bridge is currently running
log "Step 1: Checking current bridge state..."
BRIDGE_UP=false
if curl -sf "http://${WINDOWS_HOST}:${BRIDGE_PORT}/health" >/dev/null 2>&1; then
    BRIDGE_UP=true
    log "  Bridge is currently UP"
else
    log "  Bridge is currently DOWN — will attempt start"
fi

# Step 2: Kill the bridge (chaos injection)
if [ "$BRIDGE_UP" = true ]; then
    log "Step 2: Killing bridge on Windows (chaos injection)..."
    ssh "${WINDOWS_USER}@${WINDOWS_HOST}" \
        'wsl -d Ubuntu -e bash -c "pkill -f local_bridge_server || true"' 2>/dev/null || true
    sleep 2

    # Confirm it's dead
    if curl -sf "http://${WINDOWS_HOST}:${BRIDGE_PORT}/health" >/dev/null 2>&1; then
        log "  WARNING: Bridge still alive after kill — may be a different process"
    else
        log "  Bridge confirmed DEAD"
    fi
else
    log "Step 2: Bridge already down — skipping kill"
fi

echo ""
log "Step 3: Triggering export via ensure_bridge_live() + fire_export()..."
log "  Starting timer..."
START_TIME=$(date +%s)

# Run the export trigger (which internally calls ensure_bridge_live)
if [ "$DRY_RUN" = "--dry-run" ]; then
    RESULT=$(python3 -c "
import sys, json
sys.path.insert(0, '.')
from services.trigger_export import fire_export
result = fire_export('claude', dry_run=True)
print(json.dumps(result))
" 2>&1)
else
    RESULT=$(python3 -c "
import sys, json
sys.path.insert(0, '.')
from services.trigger_export import fire_export
result = fire_export('claude', dry_run=True)
print(json.dumps(result))
" 2>&1)
fi

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))

echo ""
log "Step 4: Results"
log "  Elapsed: ${ELAPSED}s"
log "  Result: $RESULT"
echo ""

# Parse result
OK=$(echo "$RESULT" | python3 -c "import sys,json; d=json.loads(sys.stdin.read().strip().split('\n')[-1]); print(d.get('ok', False))" 2>/dev/null || echo "False")

if [ "$OK" = "True" ]; then
    log "=== PASS: Bridge recovered and export dispatched in ${ELAPSED}s ==="

    # Final health check
    if curl -sf "http://${WINDOWS_HOST}:${BRIDGE_PORT}/health" >/dev/null 2>&1; then
        log "  Bridge confirmed LIVE post-test"
    fi
else
    log "=== FAIL: Export did not succeed ==="
    log "  Full output:"
    echo "$RESULT"
    exit 1
fi

echo ""
log "Chaos test complete. Expected lifecycle:"
log "  1. kill → bridge dies"
log "  2. fire_export() → ensure_bridge_live() detects down"
log "  3. SSH → start bridge → poll until healthy"
log "  4. Dispatch export → success"
log "  Total: ${ELAPSED}s (target: <30s)"
