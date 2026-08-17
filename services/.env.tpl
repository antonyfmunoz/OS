# UMH secrets — resolved from 1Password at runtime
# This file is safe to commit. It contains vault references, not actual values.
#
# Usage:
#   op inject -i services/.env.tpl -o services/.env
#   op run --env-file=services/.env.tpl -- <command>

# ── AI / LLM Provider Keys ──────────────────────────────────────────────────
ANTHROPIC_API_KEY=op://UMH-Production/AI-Anthropic/api_key
OPENAI_API_KEY=op://UMH-Production/AI-OpenAI/api_key
GEMINI_API_KEY=op://UMH-Production/AI-Gemini/api_key
GROQ_API_KEY=op://UMH-Production/AI-Groq/api_key
PERPLEXITY_API_KEY=op://UMH-Production/AI-Perplexity/api_key

# ── Database ─────────────────────────────────────────────────────────────────
DATABASE_URL=op://UMH-Production/Database-Neon/url
EOS_DATABASE_URL=op://EntrepreneurOS/Development/DATABASE_URL

# ── Mesh (node dispatch) ─────────────────────────────────────────────────────
# Relay auth for the node-mesh HTTP relay (fail-closed when unset) and the
# shared verdict-signing secret (Beast node validates with its own copy).
UMH_MESH_RELAY_SECRET=op://UMH-Production/Mesh-Relay-Secret/password
UMH_MESH_VERDICT_SECRET=op://UMH-Production/Mesh-Verdict-Secret/password

# ── Discord ──────────────────────────────────────────────────────────────────
DISCORD_BOT_TOKEN=op://UMH-Production/Discord-Bot/token
DISCORD_BRIEF_WEBHOOK=op://UMH-Production/Discord-Bot/brief_webhook
DISCORD_OUTREACH_WEBHOOK=op://UMH-Production/Discord-Bot/outreach_webhook
DISCORD_FOUNDERS_OFFICE=op://UMH-Production/Discord-Bot/founders_office_channel
FOUNDER_DISCORD_ID=op://UMH-Production/Discord-Bot/founder_discord_id

# ── Telegram ─────────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN=op://UMH-Production/Telegram-Bot/token

# ── Notion ───────────────────────────────────────────────────────────────────
NOTION_API_KEY=op://UMH-Production/Notion-Integration/api_key

# ── Third-Party APIs ────────────────────────────────────────────────────────
APIFY_API_TOKEN=op://UMH-Production/Apify/api_token
APIFY_PROXY_PASSWORD=op://UMH-Production/Apify/proxy_password
CALENDLY_SIGNING_KEY=op://UMH-Production/Calendly/signing_key
STITCH_API_KEY=op://UMH-Production/Stitch/api_key
HIGGSFIELD_API_KEY=op://UMH-Production/Higgsfield/api_key
HIGGSFIELD_API_KEY_SECRET=op://UMH-Production/Higgsfield/api_key_secret

# ── Instagram ────────────────────────────────────────────────────────────────
INSTAGRAM_PASSWORD=op://UMH-Production/Instagram/password

# ── UMH Operator Auth ───────────────────────────────────────────────────────
UMH_OPERATOR_API_KEY=op://UMH-Production/UMH-Operator/api_key
UMH_OPERATOR_TOKEN=op://UMH-Production/UMH-Operator/operator_token
UMH_WS_TOKEN=op://UMH-Production/UMH-Operator/ws_token

# ── LiveKit (Voice Rooms) ──────────────────────────────────────────────────
LIVEKIT_API_KEY=op://UMH-Production/LiveKit/api_key
LIVEKIT_API_SECRET=op://UMH-Production/LiveKit/api_secret
LIVEKIT_WS_URL=ws://157.173.212.126:7880
COCKPIT_DOMAIN=universalmetaharness.tech

# ── Cockpit Auth (Clerk JWT) ───────────────────────────────────────────────
CLERK_JWKS_URL=https://obliging-donkey-31.clerk.accounts.dev/.well-known/jwks.json
ALLOWED_CLERK_USER_IDS=user_3EHDsQSiGJUVF5FdLVkGflrwFlu

# ── Beast SSH (browser verification) ──────────────────────────────────────
UMH_BEAST_SSH=op://UMH-Production/Beast SSH/connection-string

# WP-P0-004: bearer token for the CC webhook receiver (fail-closed if unset)
CC_WEBHOOK_TOKEN=op://UMH-Production/CC-Webhook/token
