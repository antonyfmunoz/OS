#!/usr/bin/env bash
# cc_keepalive.sh — prevents OAuth token expiry during idle sessions
# Runs every 6 hours via cron. Sends a lightweight no-op to active
# CC tmux sessions to trigger token refresh before the 8h TTL expires.

LOG="/opt/OS/logs/cc_keepalive.log"
SESSIONS=("dex_builder_main" "dex_product_main")

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG"; }

for SESSION in "${SESSIONS[@]}"; do
    if ! tmux has-session -t "$SESSION" 2>/dev/null; then
        log "SKIP $SESSION — session does not exist"
        continue
    fi

    PANE_OUTPUT=$(tmux capture-pane -t "$SESSION" -p 2>/dev/null | tail -3)
    
    if echo "$PANE_OUTPUT" | grep -q "⏺\|Thinking\|Running\|Working"; then
        log "SKIP $SESSION — CC is actively working, will retry next cycle"
        continue
    fi

    tmux send-keys -t "$SESSION" "" ""
    log "OK $SESSION — keepalive sent"
done
