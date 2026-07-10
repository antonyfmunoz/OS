#!/usr/bin/env bash
# rotate_secrets.sh — automated 30-day secret rotation
#
# Auto-rotates self-generated secrets (UMH operator tokens).
# Flags provider-managed secrets for manual rotation.
# Sends rotation report to Discord Founders Office.
#
# Usage: op run --env-file=services/.env.tpl -- bash scripts/rotate_secrets.sh
# Cron:  0 5 1 * * (1st of month, 5am)
set -euo pipefail

UMH_ROOT="${UMH_ROOT:-/opt/OS}"
VAULT="${UMH_OP_VAULT:-UMH-Production}"
LOG="$UMH_ROOT/logs/secret_rotation.log"
ROTATED=0
FAILED=0
MANUAL_NEEDED=()

log() { echo "[$(date -Iseconds)] $*" | tee -a "$LOG"; }

rotate_umh_operator() {
    local new_api_key new_operator_token new_ws_token
    new_api_key=$(openssl rand -base64 32 | tr -d '=/+')
    new_operator_token=$(openssl rand -base64 32 | tr -d '=/+')
    new_ws_token=$(openssl rand -base64 24 | tr -d '=/+')

    if op item edit "$VAULT/UMH-Operator" \
        "api_key=$new_api_key" \
        "operator_token=$new_operator_token" \
        "ws_token=$new_ws_token" &>/dev/null; then
        log "UMH-Operator: rotated successfully"
        ((ROTATED++))
    else
        log "ERROR: UMH-Operator rotation failed"
        ((FAILED++))
    fi
}

flag_manual_rotations() {
    MANUAL_NEEDED+=(
        "AI-Anthropic: regenerate in Anthropic Console"
        "AI-OpenAI: regenerate in OpenAI dashboard"
        "AI-Gemini: regenerate in Google Cloud Console"
        "AI-Groq: regenerate in Groq dashboard"
        "AI-Perplexity: regenerate in Perplexity dashboard"
        "Database-Neon: rotate password via Neon dashboard or API"
        "Discord-Bot: regenerate token in Developer Portal"
        "Telegram-Bot: /revoke + /token via BotFather"
        "Notion-Integration: regenerate in integration settings"
        "Apify: regenerate token in Apify console"
        "Instagram: change password in account settings"
        "Calendly: regenerate PAT in Calendly settings"
        "Stitch: regenerate in Stitch dashboard"
        "Higgsfield: regenerate in Higgsfield dashboard"
    )
}

log "=== Secret rotation cycle started ==="

rotate_umh_operator
flag_manual_rotations

log "Redeploying containers with new secrets..."
bash "$UMH_ROOT/infra/scripts/dc-up.sh"
sleep 10

HEALTH_OK=true
if curl -sf http://localhost:8091/health > /dev/null 2>&1; then
    log "Operator API: healthy"
else
    log "ERROR: Operator API unhealthy after rotation"
    HEALTH_OK=false
fi

if curl -sf http://localhost:8080/health > /dev/null 2>&1; then
    log "Webhook: healthy"
else
    log "ERROR: Webhook unhealthy after rotation"
    HEALTH_OK=false
fi

MANUAL_LIST=""
for item in "${MANUAL_NEEDED[@]}"; do
    log "  MANUAL: $item"
    MANUAL_LIST="$MANUAL_LIST\n- $item"
done

log "Rotation complete. Auto-rotated: $ROTATED. Failed: $FAILED. Manual needed: ${#MANUAL_NEEDED[@]}"

cd "$UMH_ROOT"
python3 -c "
import sys
sys.path.insert(0, '$UMH_ROOT')
try:
    from transports.channels.channel import send_to_discord
    send_to_discord('founders_office',
        '**Monthly Secret Rotation Report**\n'
        'Auto-rotated: $ROTATED | Failed: $FAILED\n'
        'Health check: $( [ \"$HEALTH_OK\" = true ] && echo PASS || echo FAIL )\n'
        'Manual rotation needed: ${#MANUAL_NEEDED[@]}\n'
        '$MANUAL_LIST\n'
        'Check logs/secret_rotation.log for details')
except Exception as e:
    print(f'Discord notification failed: {e}', file=sys.stderr)
" 2>/dev/null || true

log "=== Cycle complete ==="
