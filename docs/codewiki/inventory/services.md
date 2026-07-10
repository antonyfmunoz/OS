---
type: codewiki-inventory
dir: services
source_sha: 70deadbac8667755a38ac49595afd09afc209c2f
---

# `services/` — File Inventory

**Files:** 43 regular + 0 symlinks · **Bytes:** 726,549

[Narrative page](../dirs/services.md)


## services/ (root)

| Path | Lines | Purpose |
|---|---|---|
| `services/.env` | 68 | — |
| `services/.env.tpl` | 65 | UMH secrets — resolved from 1Password at runtime |
| `services/CLAUDE.md` | 33 | services — Legacy Entrypoints (being migrated) |
| `services/LOCAL_BRIDGE_SETUP.md` | 161 | Local Bridge Setup — Windows WSL |
| `services/bridge_health.py` | 316 | bridge_health.py — VPS-side watchdog for the Windows bridge. |
| `services/browser_adapter.py` | 98 | browser_adapter.py — Camoufox browser wrapper for anti-detect automation. |
| `services/browser_relay.py` | 583 | Browser relay — streams headless Chromium viewports to cockpit viewers. |
| `services/calls_log.json` | 1 | — |
| `services/cc_webhook_receiver.py` | 391 | CC Reply Webhook Receiver — receives POSTs from the CC Stop hook and |
| `services/cost_log.json` | 180 | — |
| `services/cost_tracker.py` | 414 | — |
| `services/discord_bot.py` | 1,915 | EntrepreneurOS Discord Bot — DEX conversational layer. |
| `services/discord_bot_commands.py` | 3,113 | Discord bot commands — extracted from discord_bot.py. |
| `services/discord_message_handlers.py` | 1,367 | Discord message handlers — extracted from discord_bot.py. |
| `services/export_bridge_handler.py` | 294 | export_bridge_handler.py — Windows-side handler for fire_export bridge messages. |
| `services/export_profiles.yaml` | 34 | auth_mode values: magic_link, password_totp, password_email_code, verification_code, oauth_google, oauth_apple |
| `services/goal_api.py` | 194 | Goal API — REST endpoints for goal selection + focus management. |
| `services/hashtag_config.json` | 88 | — |
| `services/heartbeat.py` | 113 | EOS Heartbeat Service |
| `services/higgsfield_webhook.py` | 131 | Higgsfield Cloud API webhook receiver. |
| `services/icp_scorer.py` | 603 | — |
| `services/instagram_session.json` | 1 | — |
| `services/kpi_history.json` | 12 | — |
| `services/kpi_tracker.py` | 411 | — |
| `services/local_bridge_client.py` | 172 | Local Bridge Client — forwards Discord messages to Antony's local machine. |
| `services/local_bridge_send_to_discord.sh` | 110 | Stop hook for LOCAL CC sessions (Windows WSL) — reads last assistant message |
| `services/local_bridge_server.py` | 250 | Local Bridge Server — runs on Antony's Windows machine (WSL2). |
| `services/magic_link_handler.py` | 358 | magic_link_handler.py — Bridge endpoint for intercepting auth emails. |
| `services/magic_link_server.py` | 59 | magic_link_server.py — Standalone VPS server for magic-link email interception. |
| `services/mesh.env.tpl` | 6 | Secret Reference Manifest — umh-mesh.service (least-privilege). |
| `services/oauth_device_flow.py` | 304 | oauth_device_flow.py — Headless OAuth re-auth via Tailscale-routed callback. |
| `services/opener_stats.json` | 9 | — |
| `services/operator_api.py` | 809 | UMH Operator Workstation API — FastAPI backend for the operator UI. |
| `services/overnight_scrape.py` | 252 | — |
| `services/requirements.txt` | 26 | Python pip dependencies |
| `services/revenue_log.json` | 1 | — |
| `services/scraped_posts.json` | 489 | — |
| `services/setup_scheduler.bat` | 6 | Windows batch script — setup scheduler |
| `services/tier_3_fallback.py` | 28 | Tier 3 fallback — stub for future UI-TARS / computer-use integration. |
| `services/trigger_export.py` | 128 | trigger_export.py — VPS-side trigger for browser exports on Windows. |

## services/auth_flows/ (3 files)

| Path | Lines | Purpose |
|---|---|---|
| `services/auth_flows/__init__.py` | 0 | package marker (empty) |
| `services/auth_flows/chatgpt.py` | 456 | Scripted login for chatgpt.com — email-based auth flow. |
| `services/auth_flows/claude.py` | 210 | Scripted login for claude.ai — email magic-link flow. |
