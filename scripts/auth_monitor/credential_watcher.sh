#!/usr/bin/env bash
# credential_watcher.sh — watches ~/.claude/.credentials.json for any change
# Logs: ${UMH_ROOT:-/opt/OS}/logs/cc_credential_watch.log
# Run in tmux session "auth_monitor"

CRED_FILE="$HOME/.claude/.credentials.json"
LOG_FILE="${UMH_ROOT:-/opt/OS}/logs/cc_credential_watch.log"
DISCORD_WEBHOOK_ENV="${UMH_ROOT:-/opt/OS}/services/.env"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

send_discord_alert() {
    local msg="$1"
    local webhook
    webhook=$(grep DISCORD_BRIEF_WEBHOOK "$DISCORD_WEBHOOK_ENV" 2>/dev/null | cut -d= -f2-)
    if [[ -n "$webhook" ]]; then
        curl -s -H "Content-Type: application/json" \
            -d "{\"content\":\"🔴 **CC Auth Alert**\\n$msg\"}" \
            "$webhook" > /dev/null 2>&1
    fi
}

# Snapshot current state for diffing
snapshot_creds() {
    if [[ -f "$CRED_FILE" ]]; then
        md5sum "$CRED_FILE" | awk '{print $1}'
    else
        echo "MISSING"
    fi
}

log "=== Credential watcher started ==="
log "Monitoring: $CRED_FILE"
log "PID: $$"
log "Initial hash: $(snapshot_creds)"
log "Initial perms: $(stat -c '%a %U:%G' "$CRED_FILE" 2>/dev/null || echo 'FILE MISSING')"
log "Initial size: $(stat -c '%s' "$CRED_FILE" 2>/dev/null || echo '0') bytes"

PREV_HASH=$(snapshot_creds)

# Watch the parent directory — catches delete+recreate
inotifywait -m -e modify,delete,create,attrib,move_self,delete_self \
    --format '%T %e %f' --timefmt '%Y-%m-%d %H:%M:%S' \
    "$(dirname "$CRED_FILE")" 2>&1 | while read -r timestamp event filename; do

    # Only care about the credentials file
    [[ "$filename" != ".credentials.json" ]] && continue

    NEW_HASH=$(snapshot_creds)
    PROCS=$(pgrep -af "claude" 2>/dev/null | grep -v grep | head -10)

    detail="Event: $event | Hash: $PREV_HASH → $NEW_HASH"
    detail="$detail | Size: $(stat -c '%s' "$CRED_FILE" 2>/dev/null || echo 'GONE') bytes"
    detail="$detail | Perms: $(stat -c '%a' "$CRED_FILE" 2>/dev/null || echo 'GONE')"

    log "CHANGE DETECTED at $timestamp"
    log "  $detail"
    log "  Active claude processes:"
    echo "$PROCS" | while read -r proc; do
        log "    $proc"
    done

    # Try to identify which process touched it via /proc
    # Look for recent writers in the last 2 seconds
    for pid in $(pgrep -f "claude"); do
        if [[ -d "/proc/$pid/fd" ]]; then
            fd_target=$(readlink /proc/$pid/fd/* 2>/dev/null | grep credentials)
            if [[ -n "$fd_target" ]]; then
                log "  PID $pid has open fd to credentials: $fd_target"
            fi
        fi
    done

    case "$event" in
        *DELETE*|*MOVED_FROM*)
            alert="Credentials file DELETED at $timestamp"
            log "  CRITICAL: $alert"
            send_discord_alert "$alert\\nProcesses: $(echo "$PROCS" | head -3)"
            ;;
        *CREATE*)
            alert="Credentials file RECREATED at $timestamp (hash: $NEW_HASH)"
            log "  WARNING: $alert"
            send_discord_alert "$alert"
            ;;
        *MODIFY*)
            if [[ "$PREV_HASH" != "$NEW_HASH" ]]; then
                log "  Content changed (token refresh or corruption)"
                if [[ "$NEW_HASH" == "MISSING" ]] || [[ $(stat -c '%s' "$CRED_FILE" 2>/dev/null) -lt 100 ]]; then
                    alert="Credentials file is EMPTY or MISSING after modify at $timestamp"
                    log "  CRITICAL: $alert"
                    send_discord_alert "$alert"
                fi
            else
                log "  Touch only (no content change)"
            fi
            ;;
        *ATTRIB*)
            log "  Permission/attribute change"
            ;;
    esac

    PREV_HASH="$NEW_HASH"
done
