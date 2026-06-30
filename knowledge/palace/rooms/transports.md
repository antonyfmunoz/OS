---
type: palace-room
room_id: transports
wing: services
generated: 2026-06-29
---

# Room — Transports

**Wing:** [[services-wing|services]]  
**Palace:** [[../index|EOS Memory Palace]]

## Purpose

Discord, Telegram, webhooks — how EOS reaches the founder.

## Core Loci

Top-ranked files by dependency centrality, criticality, and entry status.
These are the files you most often need; open them before grepping.

| # | Locus | Score | Flags | One-liner |
|---|-------|-------|-------|-----------|
| 1 | [[services-discord_bot-py]] | 29 | `critical` `entry` | EntrepreneurOS Discord Bot — DEX conversational layer. |
| 2 | [[services-discord_message_handlers-py]] | 8 | — | Discord message handlers — extracted from discord_bot.py. |
| 3 | [[services-discord_bot_commands-py]] | 5 | — | Discord bot commands — extracted from discord_bot.py. |
| 4 | [[services-icp_scorer-py]] | 5 | `entry` |  |
| 5 | [[services-operator_api-py]] | 5 | `entry` | UMH Operator Workstation API — FastAPI backend for the operator UI. |
| 6 | [[services-bridge_health-py]] | 4 | `entry` | bridge_health.py — VPS-side watchdog for the Windows bridge. |
| 7 | [[services-goal_api-py]] | 4 | `entry` | Goal API — REST endpoints for goal selection + focus management. |
| 8 | [[services-higgsfield_webhook-py]] | 4 | `entry` | Higgsfield Cloud API webhook receiver. |
| 9 | [[services-local_bridge_server-py]] | 4 | `entry` | Local Bridge Server — runs on Antony's Windows machine (WSL2). |
| 10 | [[services-magic_link_server-py]] | 4 | `entry` | magic_link_server.py — Standalone VPS server for magic-link email interception. |
| 11 | [[services-overnight_scrape-py]] | 4 | `entry` |  |
| 12 | [[services-browser_relay-py]] | 3 | `entry` | Browser relay — streams headless Chromium viewports to cockpit viewers. |
| 13 | [[services-heartbeat-py]] | 3 | `entry` | EOS Heartbeat Service |
| 14 | [[services-kpi_tracker-py]] | 3 | `entry` |  |
| 15 | [[services-oauth_device_flow-py]] | 3 | `entry` | oauth_device_flow.py — Headless OAuth re-auth via Tailscale-routed callback. |

## Traversal

- Back to wing → [[services-wing|services wing]]
- Up to palace → [[../index|Memory Palace index]]
- Retrieval rules → [[../../retrieval_rules|retrieval_rules.md]]

## Raw Paths

```
  services/discord_bot.py
  services/discord_message_handlers.py
  services/discord_bot_commands.py
  services/icp_scorer.py
  services/operator_api.py
  services/bridge_health.py
  services/goal_api.py
  services/higgsfield_webhook.py
  services/local_bridge_server.py
  services/magic_link_server.py
  services/overnight_scrape.py
  services/browser_relay.py
  services/heartbeat.py
  services/kpi_tracker.py
  services/oauth_device_flow.py
```
