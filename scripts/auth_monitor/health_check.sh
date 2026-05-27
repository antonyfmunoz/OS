#!/usr/bin/env bash
# health_check.sh — runs every 5 minutes, validates CC auth state
# Now checks master + all isolated session credential files
# Log: ${UMH_ROOT:-/opt/OS}/logs/cc_auth_health.log
# Cron: */5 * * * * bash ${UMH_ROOT:-/opt/OS}/scripts/auth_monitor/health_check.sh

MASTER_CRED="$HOME/.claude/.credentials.json"
SESSIONS_BASE="$HOME/.claude_sessions"
SESSION_NAMES=("builder" "product" "adhoc")
LOG_FILE="${UMH_ROOT:-/opt/OS}/logs/cc_auth_health.log"
BACKUP_DIR="$HOME/.claude/.credentials_backups"
DISCORD_WEBHOOK_ENV="${UMH_ROOT:-/opt/OS}/services/.env"

mkdir -p "$BACKUP_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

send_discord_alert() {
    local msg="$1"
    local webhook
    webhook=$(grep DISCORD_BRIEF_WEBHOOK "$DISCORD_WEBHOOK_ENV" 2>/dev/null | cut -d= -f2-)
    if [[ -n "$webhook" ]]; then
        curl -s -H "Content-Type: application/json" \
            -d "{\"content\":\"🔴 **CC Auth Health**\\n$msg\"}" \
            "$webhook" > /dev/null 2>&1
    fi
}

check_credential_file() {
    local cred_file="$1"
    local label="$2"
    local status="OK"
    local details=""

    # Check 1: File exists
    if [[ ! -f "$cred_file" ]]; then
        log "CRITICAL [$label] — credentials MISSING"
        send_discord_alert "[$label] credentials.json MISSING"
        # Auto-restore for master only
        if [[ "$cred_file" == "$MASTER_CRED" ]]; then
            local latest_backup
            latest_backup=$(ls -t "$BACKUP_DIR"/*.json 2>/dev/null | head -1)
            if [[ -n "$latest_backup" ]]; then
                cp "$latest_backup" "$cred_file"
                chmod 600 "$cred_file"
                log "AUTO-RESTORED [$label] from $latest_backup"
                send_discord_alert "[$label] auto-restored from backup"
            fi
        fi
        return 1
    fi

    # Check 2: Non-empty
    local file_size
    file_size=$(stat -c '%s' "$cred_file" 2>/dev/null)
    if [[ "$file_size" -lt 100 ]]; then
        log "CRITICAL [$label] — nearly empty ($file_size bytes)"
        send_discord_alert "[$label] credentials nearly empty ($file_size bytes)"
        return 1
    fi

    # Check 3: Valid JSON with OAuth block + token
    local oauth_check
    oauth_check=$(python3 -c "
import json, sys
try:
    with open('$cred_file') as f:
        data = json.load(f)
    oauth = data.get('claudeAiOauth', {})
    if not oauth:
        print('MISSING_OAUTH'); sys.exit(1)
    if not oauth.get('accessToken'):
        print('MISSING_TOKEN'); sys.exit(1)
    print('VALID')
except json.JSONDecodeError:
    print('CORRUPT_JSON'); sys.exit(1)
except Exception as e:
    print(f'ERROR:{e}'); sys.exit(1)
" 2>&1)

    if [[ "$oauth_check" != "VALID" ]]; then
        log "CRITICAL [$label] — OAuth: $oauth_check"
        send_discord_alert "[$label] OAuth validation failed: $oauth_check"
        return 1
    fi

    # Check 4: OAuth refresh capability
    # Access token expiry is NORMAL with OAuth — CC auto-refreshes via refreshToken.
    # Only alert if refreshToken is missing (actual auth failure) or subscription invalid.
    local auth_check
    auth_check=$(python3 -c "
import json, sys
from datetime import datetime, timezone
with open('$cred_file') as f:
    data = json.load(f)
oauth = data.get('claudeAiOauth', {})
refresh = oauth.get('refreshToken', '')
sub_type = oauth.get('subscriptionType', '')
expires = oauth.get('expiresAt', 0)

# Critical: no refresh token means auth cannot renew
if not refresh:
    print('NO_REFRESH_TOKEN'); sys.exit(1)

# Warning: unexpected subscription type
if sub_type and sub_type != 'max':
    print(f'SUB_TYPE:{sub_type}')

# Informational: access token age (not a failure)
if expires:
    if isinstance(expires, (int, float)):
        exp_dt = datetime.fromtimestamp(expires / 1000, tz=timezone.utc)
    else:
        exp_dt = datetime.fromisoformat(str(expires).replace('Z', '+00:00'))
    remaining = exp_dt - datetime.now(timezone.utc)
    hours = remaining.total_seconds() / 3600
    if hours < 0:
        print(f'OK:refresh_active(access_expired_{-hours:.1f}h_ago)')
    else:
        print(f'OK:access_valid({hours:.1f}h_remaining)')
else:
    print('OK:refresh_active(no_expiry_field)')
" 2>&1)

    local auth_status=$?
    if [[ $auth_status -ne 0 ]]; then
        log "CRITICAL [$label] — Auth: $auth_check"
        send_discord_alert "[$label] OAuth refresh BROKEN: $auth_check — CC cannot renew auth"
        return 1
    fi

    # Check 5: Permissions
    local perms
    perms=$(stat -c '%a' "$cred_file" 2>/dev/null)
    if [[ "$perms" != "600" ]]; then
        chmod 600 "$cred_file"
        log "FIXED [$label] — permissions $perms → 600"
    fi

    # Check 6: Is this a symlink? (isolation violation)
    if [[ -L "$cred_file" && "$cred_file" != "$MASTER_CRED" ]]; then
        log "WARNING [$label] — credentials is a SYMLINK (isolation broken)"
        status="WARNING"
    fi

    log "$status [$label] — size=${file_size}B perms=$perms auth=$auth_check"
    return 0
}

# ── Check master ──
check_credential_file "$MASTER_CRED" "master"
MASTER_OK=$?

# ── Check each session ──
for session in "${SESSION_NAMES[@]}"; do
    session_cred="$SESSIONS_BASE/$session/.credentials.json"
    if [[ -d "$SESSIONS_BASE/$session" ]]; then
        check_credential_file "$session_cred" "session:$session"
    fi
done

# ── Cross-session drift check ──
if [[ $MASTER_OK -eq 0 ]]; then
    master_hash=$(md5sum "$MASTER_CRED" | awk '{print $1}')
    for session in "${SESSION_NAMES[@]}"; do
        session_cred="$SESSIONS_BASE/$session/.credentials.json"
        [[ ! -f "$session_cred" ]] && continue
        session_hash=$(md5sum "$session_cred" | awk '{print $1}')
        if [[ "$session_hash" != "$master_hash" ]]; then
            log "DRIFT [session:$session] — hash differs from master (coordinator should fix)"
        fi
    done
fi

# ── Process count ──
CC_COUNT=$(pgrep -c -f "claude" 2>/dev/null || echo 0)
CC_PIDS=$(pgrep -af "claude" 2>/dev/null | grep -v grep | awk '{print $1}' | tr '\n' ',')
log "PROCESSES — count=$CC_COUNT pids=[$CC_PIDS]"

# ── Backup master if healthy ──
if [[ $MASTER_OK -eq 0 ]]; then
    backup_file="$BACKUP_DIR/credentials_$(date +%Y%m%d_%H%M).json"
    cp "$MASTER_CRED" "$backup_file"
    chmod 600 "$backup_file"
    ls -t "$BACKUP_DIR"/*.json 2>/dev/null | tail -n +289 | xargs rm -f 2>/dev/null
fi

exit 0
