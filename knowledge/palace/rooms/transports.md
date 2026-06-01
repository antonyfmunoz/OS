---
type: palace-room
room_id: transports
wing: services
generated: 2026-05-31
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
| 3 | [[services-icp_scorer-py]] | 5 | `entry` |  |
| 4 | [[services-discord_bot_commands-py]] | 4 | — | Discord bot commands — extracted from discord_bot.py. |
| 5 | [[services-goal_api-py]] | 4 | `entry` | Goal API — REST endpoints for goal selection + focus management. |
| 6 | [[services-higgsfield_webhook-py]] | 4 | `entry` | Higgsfield Cloud API webhook receiver. |
| 7 | [[services-magic_link_server-py]] | 4 | `entry` | magic_link_server.py — Standalone VPS server for magic-link email interception. |
| 8 | [[services-operator_api-py]] | 4 | `entry` | UMH Operator Workstation API — FastAPI backend for the operator UI. |
| 9 | [[services-bridge_health-py]] | 3 | `entry` | bridge_health.py — VPS-side watchdog for the Windows bridge. |
| 10 | [[services-heartbeat-py]] | 3 | `entry` | EOS Heartbeat Service |
| 11 | [[services-kpi_tracker-py]] | 3 | `entry` |  |
| 12 | [[services-local_bridge_server-py]] | 3 | `entry` | Local Bridge Server — runs on Antony's Windows machine (WSL2). |
| 13 | [[services-oauth_device_flow-py]] | 3 | `entry` | oauth_device_flow.py — Headless OAuth re-auth via Tailscale-routed callback. |
| 14 | [[services-overnight_scrape-py]] | 3 | `entry` |  |
| 15 | [[services-trigger_export-py]] | 3 | `entry` | trigger_export.py — VPS-side trigger for browser exports on Windows. |

## Traversal

- Back to wing → [[services-wing|services wing]]
- Up to palace → [[../index|Memory Palace index]]
- Retrieval rules → [[../../retrieval_rules|retrieval_rules.md]]

## Raw Paths

```
  services/discord_bot.py
  services/discord_message_handlers.py
  services/icp_scorer.py
  services/discord_bot_commands.py
  services/goal_api.py
  services/higgsfield_webhook.py
  services/magic_link_server.py
  services/operator_api.py
  services/bridge_health.py
  services/heartbeat.py
  services/kpi_tracker.py
  services/local_bridge_server.py
  services/oauth_device_flow.py
  services/overnight_scrape.py
  services/trigger_export.py
```
