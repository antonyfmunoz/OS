# UMH secrets — resolved from 1Password at runtime
# This file is safe to commit. It contains vault references, not actual values.
#
# Usage:
#   op inject -i services/.env.tpl -o services/.env
#   op run --env-file=services/.env.tpl -- <command>

# ── AI / LLM Provider Keys ──────────────────────────────────────────────────
ANTHROPIC_API_KEY=op://${UMH_OP_VAULT}/AI-Anthropic/api_key
OPENAI_API_KEY=op://${UMH_OP_VAULT}/AI-OpenAI/api_key
GEMINI_API_KEY=op://${UMH_OP_VAULT}/AI-Gemini/api_key
GROQ_API_KEY=op://${UMH_OP_VAULT}/AI-Groq/api_key
PERPLEXITY_API_KEY=op://${UMH_OP_VAULT}/AI-Perplexity/api_key

# ── Database ─────────────────────────────────────────────────────────────────
DATABASE_URL=op://${UMH_OP_VAULT}/Database-Neon/url
EOS_DATABASE_URL=op://${UMH_OP_VAULT}/Development/DATABASE_URL

# ── Mesh (node dispatch) ─────────────────────────────────────────────────────
# Relay auth for the node-mesh HTTP relay (fail-closed when unset) and the
# shared verdict-signing secret (Beast node validates with its own copy).
UMH_MESH_RELAY_SECRET=op://${UMH_OP_VAULT}/Mesh-Relay-Secret/password
UMH_MESH_VERDICT_SECRET=op://${UMH_OP_VAULT}/Mesh-Verdict-Secret/password

# ── Discord ──────────────────────────────────────────────────────────────────
DISCORD_BOT_TOKEN=op://${UMH_OP_VAULT}/Discord-Bot/token
DISCORD_BRIEF_WEBHOOK=op://${UMH_OP_VAULT}/Discord-Bot/brief_webhook
DISCORD_OUTREACH_WEBHOOK=op://${UMH_OP_VAULT}/Discord-Bot/outreach_webhook
DISCORD_FOUNDERS_OFFICE=op://${UMH_OP_VAULT}/Discord-Bot/founders_office_channel
FOUNDER_DISCORD_ID=op://${UMH_OP_VAULT}/Discord-Bot/founder_discord_id

# ── Telegram ─────────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN=op://${UMH_OP_VAULT}/Telegram-Bot/token

# ── Notion ───────────────────────────────────────────────────────────────────
NOTION_API_KEY=op://${UMH_OP_VAULT}/Notion-Integration/api_key

# ── Third-Party APIs ────────────────────────────────────────────────────────
APIFY_API_TOKEN=op://${UMH_OP_VAULT}/Apify/api_token
APIFY_PROXY_PASSWORD=op://${UMH_OP_VAULT}/Apify/proxy_password
CALENDLY_SIGNING_KEY=op://${UMH_OP_VAULT}/Calendly/signing_key
STITCH_API_KEY=op://${UMH_OP_VAULT}/Stitch/api_key
HIGGSFIELD_API_KEY=op://${UMH_OP_VAULT}/Higgsfield/api_key
HIGGSFIELD_API_KEY_SECRET=op://${UMH_OP_VAULT}/Higgsfield/api_key_secret

# ── Instagram ────────────────────────────────────────────────────────────────
INSTAGRAM_PASSWORD=op://${UMH_OP_VAULT}/Instagram/password

# ── UMH Operator Auth ───────────────────────────────────────────────────────
UMH_OPERATOR_API_KEY=op://${UMH_OP_VAULT}/UMH-Operator/api_key
UMH_OPERATOR_TOKEN=op://${UMH_OP_VAULT}/UMH-Operator/operator_token
UMH_WS_TOKEN=op://${UMH_OP_VAULT}/UMH-Operator/ws_token

# ── LiveKit (Voice Rooms) ──────────────────────────────────────────────────
LIVEKIT_API_KEY=op://${UMH_OP_VAULT}/LiveKit/api_key
LIVEKIT_API_SECRET=op://${UMH_OP_VAULT}/LiveKit/api_secret
LIVEKIT_WS_URL=op://${UMH_OP_VAULT}/LiveKit/ws_url
COCKPIT_DOMAIN=universalmetaharness.tech

# ── Cockpit Auth (Clerk JWT) ───────────────────────────────────────────────
CLERK_JWKS_URL=op://${UMH_OP_VAULT}/Clerk/jwks_url
ALLOWED_CLERK_USER_IDS=op://${UMH_OP_VAULT}/Clerk/allowed_user_ids

# ── Beast SSH (browser verification) ──────────────────────────────────────
UMH_BEAST_SSH=op://${UMH_OP_VAULT}/Beast SSH/connection-string
