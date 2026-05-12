#!/usr/bin/env bash
set -euo pipefail

# Relay End-to-End Verification Script
# Prerequisites: WSL environment, Windows relay running, Tailscale up
# Usage: ./scripts/verify_relay_end_to_end.sh
# Exit: 0 = PASS, 1 = FAIL

REPO_ROOT="${UMH_ROOT:-/opt/OS}"
PROOF_DIR="$REPO_ROOT/data/runtime/workstation_relay/proofs"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H%M%SZ")
PROOF_FILE="$PROOF_DIR/${TIMESTAMP}_ping.json"

fail() { echo "FAIL: $1"; exit 1; }
pass() { echo "PASS: $1"; exit 0; }

echo "=== Relay E2E Verification — $TIMESTAMP ==="

# Step 1: Detect WSL
if [ ! -d "/mnt/c" ]; then
    fail "Not running under WSL (/mnt/c not found). This script requires WSL."
fi
echo "[1/5] WSL detected"

# Step 2: Resolve Windows relay root
RELAY_ROOT=$(python3 -c "
import sys; sys.path.insert(0, '$REPO_ROOT')
from runtime.transport.windows_desktop_relay_client import _default_relay_root
print(_default_relay_root())
" 2>/dev/null) || fail "Could not resolve relay root via Python module"

if [ ! -d "$RELAY_ROOT" ]; then
    fail "Relay root does not exist: $RELAY_ROOT"
fi
echo "[2/5] Relay root: $RELAY_ROOT"

# Step 3: Check heartbeat freshness
HEARTBEAT="$RELAY_ROOT/heartbeats/windows_relay_heartbeat.json"
if [ ! -f "$HEARTBEAT" ]; then
    fail "No heartbeat file at $HEARTBEAT — is the Windows relay running?"
fi

HEARTBEAT_AGE=$(python3 -c "
import os, time
age = time.time() - os.path.getmtime('$HEARTBEAT')
print(int(age))
" 2>/dev/null) || fail "Could not read heartbeat mtime"

if [ "$HEARTBEAT_AGE" -gt 60 ]; then
    fail "Heartbeat stale (${HEARTBEAT_AGE}s old, max 60s). Windows relay may not be running."
fi
echo "[3/5] Heartbeat fresh (${HEARTBEAT_AGE}s old)"

# Step 4: Send dry-run PING via relay client
REQUEST_ID="PING-E2E-${TIMESTAMP}"
echo "[4/5] Sending dry-run PING (request_id=$REQUEST_ID)..."

SEND_RESULT=$(python3 -c "
import sys, json; sys.path.insert(0, '$REPO_ROOT')
from runtime.transport.windows_desktop_relay_client import write_request_to_relay, resolve_relay_paths
root, inbox, outbox = resolve_relay_paths('$RELAY_ROOT')
req = {
    'request_id': '$REQUEST_ID',
    'action': 'PING',
    'payload': {'source': 'verify_relay_end_to_end.sh', 'timestamp': '$TIMESTAMP'},
}
path = write_request_to_relay(req, relay_inbox=inbox, dry_run=True)
print(json.dumps({'written': str(path), 'exists': path.exists()}))
" 2>&1) || fail "Failed to write PING request: $SEND_RESULT"

echo "  Request written: $SEND_RESULT"

# Step 5: Poll outbox for result (30s timeout)
echo "[5/5] Polling outbox for result (30s timeout)..."

POLL_RESULT=$(python3 -c "
import sys, json; sys.path.insert(0, '$REPO_ROOT')
from runtime.transport.windows_desktop_relay_client import read_result_from_relay, resolve_relay_paths
root, inbox, outbox = resolve_relay_paths('$RELAY_ROOT')
result = read_result_from_relay('$REQUEST_ID', relay_outbox=outbox, timeout_seconds=30, poll_interval=2)
if result is None:
    print(json.dumps({'status': 'timeout'}))
else:
    print(json.dumps(result))
" 2>&1) || fail "Polling error: $POLL_RESULT"

STATUS=$(echo "$POLL_RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status','unknown'))" 2>/dev/null || echo "parse_error")

# Write proof artifact
mkdir -p "$PROOF_DIR"
python3 -c "
import json
proof = {
    'timestamp': '$TIMESTAMP',
    'request_id': '$REQUEST_ID',
    'relay_root': '$RELAY_ROOT',
    'heartbeat_age_seconds': $HEARTBEAT_AGE,
    'poll_result_status': '$STATUS',
    'poll_result_raw': $POLL_RESULT,
}
with open('$PROOF_FILE', 'w') as f:
    json.dump(proof, f, indent=2)
print('Proof written: $PROOF_FILE')
"

if [ "$STATUS" = "timeout" ]; then
    echo "  Result: timeout (relay did not process within 30s)"
    echo "  Proof: $PROOF_FILE"
    fail "Relay did not respond within 30s. Check Windows relay process."
fi

echo "  Result: $STATUS"
echo "  Proof: $PROOF_FILE"
pass "Relay processed PING and returned result (status=$STATUS)"
