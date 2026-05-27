#!/usr/bin/env bash
# credential_coordinator.sh — single source of truth for CC credential management
#
# Responsibilities:
# 1. Watches master credentials for changes (token refresh by any session)
# 2. Distributes refreshed credentials to all isolated session dirs
# 3. Uses flock to serialize writes — prevents race conditions
# 4. Logs all credential events with process attribution
# 5. Alerts on auth degradation
#
# Runs in tmux session "auth_monitor"

set -uo pipefail

MASTER_CRED="/root/.claude/.credentials.json"
SESSIONS_BASE="/root/.claude_sessions"
SESSION_NAMES=("builder" "product" "adhoc")
LOCK_FILE="/tmp/cc_credential.lock"
LOG_FILE="${UMH_ROOT:-/opt/OS}/logs/cc_credential_coordinator.log"
DISCORD_WEBHOOK_ENV="${UMH_ROOT:-/opt/OS}/services/.env"
BACKUP_DIR="/root/.claude/.credentials_backups"

mkdir -p "$BACKUP_DIR" "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

send_discord_alert() {
    local msg="$1"
    local webhook
    webhook=$(grep DISCORD_BRIEF_WEBHOOK "$DISCORD_WEBHOOK_ENV" 2>/dev/null | cut -d= -f2-)
    if [[ -n "$webhook" ]]; then
        curl -s -H "Content-Type: application/json" \
            -d "{\"content\":\"🔴 **CC Credential Coordinator**\\n$msg\"}" \
            "$webhook" > /dev/null 2>&1
    fi
}

md5_of() {
    if [[ -f "$1" ]]; then
        md5sum "$1" | awk '{print $1}'
    else
        echo "MISSING"
    fi
}

# Distribute master credentials to all session dirs (under flock)
distribute_credentials() {
    local reason="$1"
    (
        flock -w 10 200 || { log "ERROR: Could not acquire lock for distribution"; return 1; }

        local master_hash
        master_hash=$(md5_of "$MASTER_CRED")

        if [[ "$master_hash" == "MISSING" ]]; then
            log "CRITICAL: Master credentials missing during distribution"
            send_discord_alert "Master credentials missing — cannot distribute"
            return 1
        fi

        # Validate master credentials before distributing
        local valid
        valid=$(python3 -c "
import json, sys
from datetime import datetime, timezone
try:
    with open('$MASTER_CRED') as f:
        data = json.load(f)
    oauth = data.get('claudeAiOauth', {})
    if not oauth.get('accessToken'):
        print('NO_TOKEN')
        sys.exit(1)
    expires = oauth.get('expiresAt', 0)
    if isinstance(expires, (int, float)):
        exp_dt = datetime.fromtimestamp(expires / 1000, tz=timezone.utc)
    else:
        exp_dt = datetime.fromisoformat(str(expires).replace('Z', '+00:00'))
    remaining = (exp_dt - datetime.now(timezone.utc)).total_seconds()
    if remaining < 0:
        print(f'EXPIRED:{int(remaining)}s')
        sys.exit(1)
    print(f'VALID:{int(remaining)}s')
except Exception as e:
    print(f'ERROR:{e}')
    sys.exit(1)
" 2>&1)

        if [[ $? -ne 0 ]]; then
            log "WARNING: Master credentials invalid ($valid) — skipping distribution"
            return 1
        fi

        local distributed=0
        for session in "${SESSION_NAMES[@]}"; do
            local session_cred="$SESSIONS_BASE/$session/.credentials.json"
            local session_dir="$SESSIONS_BASE/$session"

            if [[ ! -d "$session_dir" ]]; then
                continue
            fi

            local session_hash
            session_hash=$(md5_of "$session_cred")

            if [[ "$session_hash" != "$master_hash" ]]; then
                cp "$MASTER_CRED" "$session_cred"
                chmod 600 "$session_cred"
                log "  Distributed to $session (was: ${session_hash:0:8}, now: ${master_hash:0:8})"
                distributed=$((distributed + 1))
            fi
        done

        if [[ $distributed -gt 0 ]]; then
            log "DISTRIBUTED ($reason): $distributed sessions updated | master=$valid"
        fi

        # Backup
        cp "$MASTER_CRED" "$BACKUP_DIR/credentials_$(date +%Y%m%d_%H%M%S).json"
        chmod 600 "$BACKUP_DIR"/credentials_*.json 2>/dev/null
        # Keep last 288 backups (24h of 5-min intervals)
        ls -t "$BACKUP_DIR"/*.json 2>/dev/null | tail -n +289 | xargs rm -f 2>/dev/null

    ) 200>"$LOCK_FILE"
}

# Collect credentials from session dirs back to master
# (in case a session refreshed its own token)
collect_from_sessions() {
    (
        flock -w 10 200 || { log "ERROR: Could not acquire lock for collection"; return 1; }

        local master_hash
        master_hash=$(md5_of "$MASTER_CRED")
        local master_expiry=0

        # Get master token expiry
        if [[ -f "$MASTER_CRED" ]]; then
            master_expiry=$(python3 -c "
import json
with open('$MASTER_CRED') as f:
    data = json.load(f)
print(data.get('claudeAiOauth', {}).get('expiresAt', 0))
" 2>/dev/null || echo 0)
        fi

        # Check each session for a newer token
        for session in "${SESSION_NAMES[@]}"; do
            local session_cred="$SESSIONS_BASE/$session/.credentials.json"
            [[ ! -f "$session_cred" ]] && continue

            local session_hash
            session_hash=$(md5_of "$session_cred")
            [[ "$session_hash" == "$master_hash" ]] && continue

            # Session has different credentials — check if newer
            local session_expiry
            session_expiry=$(python3 -c "
import json
with open('$session_cred') as f:
    data = json.load(f)
print(data.get('claudeAiOauth', {}).get('expiresAt', 0))
" 2>/dev/null || echo 0)

            if [[ "$session_expiry" -gt "$master_expiry" ]]; then
                log "COLLECTED: Session '$session' has newer token (expiry $session_expiry > $master_expiry)"
                cp "$session_cred" "$MASTER_CRED"
                chmod 600 "$MASTER_CRED"
                master_hash="$session_hash"
                master_expiry="$session_expiry"
                # Distribute the newer token to all other sessions
                distribute_credentials "collected from $session"
            fi
        done

    ) 200>"$LOCK_FILE"
}

# ── Main loop ──────────────────────────────────────────────────────

log "=== Credential coordinator started ==="
log "Master: $MASTER_CRED"
log "Sessions: ${SESSION_NAMES[*]}"
log "Lock: $LOCK_FILE"
log "PID: $$"

# Initial distribution
distribute_credentials "startup"

PREV_MASTER_HASH=$(md5_of "$MASTER_CRED")

# Watch master credentials for changes + periodic session collection
# inotifywait watches for immediate changes; timeout handles periodic checks
while true; do
    # Watch for changes to master credentials (30s timeout for periodic work)
    CHANGE=$(inotifywait -t 30 -e modify,create,delete,move_self,attrib \
        --format '%T %e' --timefmt '%Y-%m-%d %H:%M:%S' \
        "$(dirname "$MASTER_CRED")" 2>/dev/null | grep -i "credentials" | head -1 || true)

    if [[ -n "$CHANGE" ]]; then
        NEW_HASH=$(md5_of "$MASTER_CRED")
        if [[ "$NEW_HASH" != "$PREV_MASTER_HASH" ]]; then
            log "MASTER CHANGED: $CHANGE | hash: ${PREV_MASTER_HASH:0:8} → ${NEW_HASH:0:8}"

            # Log which process might have done it
            CC_PROCS=$(pgrep -af "claude" 2>/dev/null | grep -v grep | head -5)
            log "  Active CC processes:"
            echo "$CC_PROCS" | while read -r proc; do
                log "    $proc"
            done

            distribute_credentials "master file changed"
            PREV_MASTER_HASH="$NEW_HASH"
        fi
    fi

    # Periodic: collect newer tokens from sessions
    collect_from_sessions

    # Periodic: check for session credential drift
    for session in "${SESSION_NAMES[@]}"; do
        local_cred="$SESSIONS_BASE/$session/.credentials.json"
        [[ ! -f "$local_cred" ]] && continue

        local_hash=$(md5_of "$local_cred")
        master_hash=$(md5_of "$MASTER_CRED")

        if [[ "$local_hash" != "$master_hash" ]]; then
            local_expiry=$(python3 -c "
import json
with open('$local_cred') as f: data = json.load(f)
print(data.get('claudeAiOauth', {}).get('expiresAt', 0))
" 2>/dev/null || echo 0)
            master_expiry=$(python3 -c "
import json
with open('$MASTER_CRED') as f: data = json.load(f)
print(data.get('claudeAiOauth', {}).get('expiresAt', 0))
" 2>/dev/null || echo 0)

            if [[ "$local_expiry" -gt "$master_expiry" ]]; then
                log "DRIFT: Session '$session' has newer token — collecting"
                collect_from_sessions
            else
                log "DRIFT: Session '$session' has older token — redistributing"
                distribute_credentials "drift correction for $session"
            fi
        fi
    done
done
