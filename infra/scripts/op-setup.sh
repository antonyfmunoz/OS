#!/usr/bin/env bash
# op-setup.sh — Populate 1Password vault from current .env files
#
# Run this ONCE after 1Password Business account + service account are created.
# Reads secrets from existing .env files and creates 1Password items.
#
# Prerequisites:
#   1. 1Password CLI installed: apt install 1password-cli
#   2. Service account created in 1Password web UI
#   3. OP_SERVICE_ACCOUNT_TOKEN exported in shell
#   4. Original .env files still present (not yet deleted)
#
# Usage: bash infra/scripts/op-setup.sh
set -euo pipefail

UMH_ROOT="${UMH_ROOT:-/opt/OS}"
VAULT="${UMH_OP_VAULT:-UMH-Production}"

if ! command -v op &>/dev/null; then
    echo "ERROR: 1Password CLI not installed."
    echo "Install: https://developer.1password.com/docs/cli/get-started/"
    exit 1
fi

if ! op whoami &>/dev/null; then
    echo "ERROR: Not authenticated to 1Password."
    echo "Set OP_SERVICE_ACCOUNT_TOKEN or run 'op signin'."
    exit 1
fi

# Source the main .env to get current secret values
set -a
source "$UMH_ROOT/services/.env"
set +a

# Source umh.env for ANTHROPIC_API_KEY (has the actual key, services/.env may be empty)
ANTHROPIC_KEY_FROM_UMH=$(grep "^ANTHROPIC_API_KEY=" "$UMH_ROOT/infra/docker/umh.env" | cut -d= -f2-)
if [ -n "$ANTHROPIC_KEY_FROM_UMH" ]; then
    ANTHROPIC_API_KEY="$ANTHROPIC_KEY_FROM_UMH"
fi

# Claude OAuth token
CLAUDE_OAUTH=$(grep "^export CLAUDE_CODE_OAUTH_TOKEN=" "$UMH_ROOT/.env.sessions" 2>/dev/null | sed 's/^export //' | cut -d= -f2- || echo "")

# UMH operator keys (from services/.env)
# Already sourced above

echo "Creating vault '$VAULT'..."
op vault create "$VAULT" --description "UMH/EntrepreneurOS production secrets" 2>/dev/null || echo "Vault already exists"

echo ""
echo "Creating items..."

create_item() {
    local title="$1"
    shift
    echo "  Creating: $title"
    op item create --vault "$VAULT" --category "API Credential" --title "$title" "$@" 2>/dev/null || \
        echo "    (already exists or failed — check manually)"
}

create_item "AI-Anthropic" \
    "api_key=$ANTHROPIC_API_KEY"

create_item "AI-OpenAI" \
    "api_key=$OPENAI_API_KEY"

create_item "AI-Gemini" \
    "api_key=$GEMINI_API_KEY"

create_item "AI-Groq" \
    "api_key=$GROQ_API_KEY"

create_item "AI-Perplexity" \
    "api_key=$PERPLEXITY_API_KEY"

create_item "Database-Neon" \
    "url=$DATABASE_URL"

create_item "Discord-Bot" \
    "token=$DISCORD_BOT_TOKEN" \
    "brief_webhook=$DISCORD_BRIEF_WEBHOOK" \
    "outreach_webhook=$DISCORD_OUTREACH_WEBHOOK"

create_item "Telegram-Bot" \
    "token=$TELEGRAM_BOT_TOKEN"

create_item "Notion-Integration" \
    "api_key=$NOTION_API_KEY"

create_item "Apify" \
    "api_token=$APIFY_API_TOKEN" \
    "proxy_password=$APIFY_PROXY_PASSWORD"

create_item "Calendly" \
    "signing_key=$CALENDLY_SIGNING_KEY"

create_item "Stitch" \
    "api_key=$STITCH_API_KEY"

create_item "Higgsfield" \
    "api_key=$HIGGSFIELD_API_KEY" \
    "api_key_secret=$HIGGSFIELD_API_KEY_SECRET"

op item create --vault "$VAULT" --category "Login" --title "Instagram" \
    "username=$INSTAGRAM_USERNAME" \
    "password=$INSTAGRAM_PASSWORD" 2>/dev/null || \
    echo "  Instagram: already exists or failed"

if [ -n "$CLAUDE_OAUTH" ]; then
    create_item "Claude-Code-OAuth" \
        "oauth_token=$CLAUDE_OAUTH"
fi

create_item "UMH-Operator" \
    "api_key=$UMH_OPERATOR_API_KEY" \
    "operator_token=$UMH_OPERATOR_TOKEN" \
    "ws_token=$UMH_WS_TOKEN"

# Tailscale authkey — check fly.toml or prompt
echo ""
echo "NOTE: Tailscale authkey must be added manually:"
echo "  op item create --vault '$VAULT' --category 'API Credential' --title 'Tailscale-Cockpit' 'authkey=YOUR_KEY'"

echo ""
echo "=== Setup complete ==="
echo ""
echo "Verify with:"
echo "  op read 'op://$VAULT/AI-Anthropic/api_key'"
echo "  op read 'op://$VAULT/Database-Neon/url'"
echo "  op read 'op://$VAULT/Discord-Bot/token'"
echo ""
echo "Next steps:"
echo "  1. Verify all 17 items in 1Password web UI"
echo "  2. Test: bash infra/scripts/dc-up.sh"
echo "  3. After 48h of clean operation, shred .env files"
