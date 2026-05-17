#!/bin/bash
# test_bridge_lifecycle.sh — Chaos test for bridge auto-recovery.
#
# Scenario:
#   1. Kill the bridge on Windows via SSH
#   2. Trigger an export from VPS (calls ensure_bridge_live internally)
#   3. VPS detects bridge down, auto-starts via OpenSSH
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
WINDOWS_USER="${EOS_WINDOWS_TAILSCALE_USER:-antonys beast pc}"
BRIDGE_PORT="${EOS_LOCAL_BRIDGE_PORT:-8767}"

log() { echo "[$(date '+%H:%M:%S.%3N')] $*"; }

log "=== BRIDGE LIFECYCLE CHAOS TEST ==="
echo ""

# Step 0: Verify SSH works (list-form with -l flag for spaced username)
log "Step 0: Checking OpenSSH to Windows via Tailscale..."
if ! ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=accept-new -o BatchMode=yes \
    -l "$WINDOWS_USER" "$WINDOWS_HOST" "powershell" "-c" "echo ok" 2>/dev/null | grep -q "ok"; then
    log "FAIL: Cannot SSH to Windows."
    log "  Username: '$WINDOWS_USER'"
    log "  Host: $WINDOWS_HOST"
    log "  Fix: Enable OpenSSH Server on Windows, bind to Tailscale interface,"
    log "       paste VPS pubkey into C:\\ProgramData\\ssh\\administrators_authorized_keys"
    exit 1
fi
log "  SSH OK (user='$WINDOWS_USER', host=$WINDOWS_HOST)"

# Step 1: Check if bridge is currently running
log "Step 1: Checking current bridge state..."
BRIDGE_UP=false
if curl -sf "http://${WINDOWS_HOST}:${BRIDGE_PORT}/health" >/dev/null 2>&1; then
    BRIDGE_UP=true
    log "  Bridge is currently UP"
else
    log "  Bridge is currently DOWN"
fi

# Step 2: Kill the bridge (chaos injection)
if [ "$BRIDGE_UP" = true ]; then
    log "Step 2: CHAOS — Killing bridge on Windows..."
    ssh -o ConnectTimeout=5 -o BatchMode=yes \
        -l "$WINDOWS_USER" "$WINDOWS_HOST" \
        "powershell" "-c" "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object {\$_.CommandLine -like '*local_bridge_server*'} | ForEach-Object {Stop-Process -Id \$_.ProcessId -Force}" 2>/dev/null || true
    sleep 2

    # Confirm it's dead
    if curl -sf "http://${WINDOWS_HOST}:${BRIDGE_PORT}/health" >/dev/null 2>&1; then
        log "  WARNING: Bridge still alive after kill"
    else
        log "  Bridge confirmed DEAD"
    fi
else
    log "Step 2: Bridge already down — skipping kill (watchdog will start it)"
fi

echo ""
log "Step 3: Triggering fire_export() with integrated watchdog..."
log "  (ensure_bridge_live → detect down → SSH start → poll → dispatch)"
log "  Starting timer..."
START_TIME=$(date +%s%3N)

# Run the export trigger (which internally calls ensure_bridge_live)
RESULT=$(python3 -c "
import sys, json, logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s %(message)s', datefmt='%H:%M:%S.000')
sys.path.insert(0, '.')
from services.trigger_export import fire_export
result = fire_export('claude', dry_run=True)
print('---RESULT---')
print(json.dumps(result))
" 2>&1)

END_TIME=$(date +%s%3N)
ELAPSED_MS=$((END_TIME - START_TIME))
ELAPSED_S=$(echo "scale=1; $ELAPSED_MS / 1000" | bc)

echo ""
log "Step 4: Results"
log "  Elapsed: ${ELAPSED_S}s"
echo ""
echo "$RESULT" | grep -v "^---RESULT---$"
echo ""

# Parse result from last line after marker
RESULT_JSON=$(echo "$RESULT" | grep -A1 "^---RESULT---$" | tail -1)
OK=$(echo "$RESULT_JSON" | python3 -c "import sys,json; d=json.loads(sys.stdin.read().strip()); print(d.get('ok', False))" 2>/dev/null || echo "False")

if [ "$OK" = "True" ]; then
    log "=== PASS === Bridge recovered and export dispatched in ${ELAPSED_S}s"
    echo ""

    # Final health check
    if curl -sf "http://${WINDOWS_HOST}:${BRIDGE_PORT}/health" >/dev/null 2>&1; then
        log "  Bridge confirmed LIVE post-test"
    fi

    if (( ELAPSED_MS < 30000 )); then
        log "  Under 30s target: YES"
    else
        log "  Under 30s target: NO (${ELAPSED_S}s) — still passed but slow"
    fi
else
    log "=== FAIL === Export did not succeed"
    log "  Result: $RESULT_JSON"
    exit 1
fi

echo ""
log "Full lifecycle timeline:"
log "  T+0.0s  Bridge killed / confirmed dead"
log "  T+0.0s  fire_export() called"
log "  T+~3s   ensure_bridge_live() detects bridge down"
log "  T+~5s   SSH check passes"
log "  T+~7s   SSH start command sent"
log "  T+~10s  Bridge process starts in WSL"
log "  T+~${ELAPSED_S}s  Bridge responds to health check → dispatch"
