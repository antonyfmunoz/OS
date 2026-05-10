#!/usr/bin/env bash
# session_resurrector.sh — checks CC session health in tmux, alerts if dead
# Does NOT auto-restart CC (requires interactive auth) — alerts operator instead
# Run: */5 * * * * bash ${UMH_ROOT:-/opt/OS}/scripts/auth_monitor/session_resurrector.sh

LOG_FILE="${UMH_ROOT:-/opt/OS}/logs/cc_session_health.log"
DISCORD_WEBHOOK_ENV="${UMH_ROOT:-/opt/OS}/eos_ai/.env"

WATCHED_SESSIONS=("dex_builder_main" "dex_product_main")

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

send_discord_alert() {
    local msg="$1"
    local webhook
    webhook=$(grep DISCORD_BRIEF_WEBHOOK "$DISCORD_WEBHOOK_ENV" 2>/dev/null | cut -d= -f2-)
    if [[ -n "$webhook" ]]; then
        curl -s -H "Content-Type: application/json" \
            -d "{\"content\":\"🟡 **CC Session Alert**\\n$msg\"}" \
            "$webhook" > /dev/null 2>&1
    fi
}

for session in "${WATCHED_SESSIONS[@]}"; do
    # Check if tmux session exists
    if ! tmux has-session -t "$session" 2>/dev/null; then
        log "MISSING — tmux session '$session' does not exist"
        send_discord_alert "tmux session \`$session\` is gone"
        continue
    fi

    # Capture last line of the pane to detect CC state
    PANE_OUTPUT=$(tmux capture-pane -t "$session" -p 2>/dev/null | tail -5)

    # Check for common logout/error patterns
    if echo "$PANE_OUTPUT" | grep -qi "not authenticated\|session expired\|login required\|auth.*error\|ECONNREFUSED\|unauthorized"; then
        log "AUTH_FAILED — session '$session' shows auth error"
        send_discord_alert "Session \`$session\` shows auth failure:\\n\`\`\`$(echo "$PANE_OUTPUT" | tail -3)\`\`\`"
    elif echo "$PANE_OUTPUT" | grep -qi "exited\|terminated\|command not found"; then
        log "EXITED — CC process in '$session' has exited"
        send_discord_alert "CC process in \`$session\` has exited"
    else
        # Check if CC process is actually running in this session
        SESSION_PID=$(tmux list-panes -t "$session" -F '#{pane_pid}' 2>/dev/null | head -1)
        if [[ -n "$SESSION_PID" ]]; then
            # Check if claude is a child of this pane's shell
            CC_RUNNING=$(pgrep -P "$SESSION_PID" -af "claude" 2>/dev/null | head -1)
            if [[ -z "$CC_RUNNING" ]]; then
                # Check grandchildren too
                for child in $(pgrep -P "$SESSION_PID" 2>/dev/null); do
                    CC_RUNNING=$(pgrep -P "$child" -af "claude" 2>/dev/null | head -1)
                    [[ -n "$CC_RUNNING" ]] && break
                done
            fi
            if [[ -n "$CC_RUNNING" ]]; then
                log "OK — session '$session' has CC running ($(echo "$CC_RUNNING" | awk '{print $1}'))"
            else
                log "NO_CC — session '$session' exists but no CC process found"
                send_discord_alert "tmux session \`$session\` alive but CC not running"
            fi
        fi
    fi
done
