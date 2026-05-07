---
type: palace-room
room_id: transports
wing: services
generated: 2026-05-07
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
| 1 | [[services-discord_bot-py]] | 13 | `critical` `entry` |  |
| 2 | [[services-telegram_control-py]] | 10 | `critical` |  |
| 3 | [[services-apify_scraper-py]] | 5 | `entry` |  |
| 4 | [[services-icp_scorer-py]] | 5 | `entry` |  |
| 5 | [[services-calendly_webhook-py]] | 4 | `entry` |  |
| 6 | [[services-goal_api-py]] | 4 | `entry` | Goal API — REST endpoints for goal selection + focus management. |
| 7 | [[services-higgsfield_webhook-py]] | 4 | `entry` | Higgsfield Cloud API webhook receiver. |
| 8 | [[services-dm_monitor-py]] | 3 | `entry` |  |
| 9 | [[services-heartbeat-py]] | 3 | `entry` | EOS Heartbeat Service |
| 10 | [[services-kpi_tracker-py]] | 3 | `entry` |  |
| 11 | [[services-local_bridge_server-py]] | 3 | `entry` | Local Bridge Server — runs on Antony's Windows machine (WSL2). |
| 12 | [[services-overnight_scrape-py]] | 3 | `entry` |  |
| 13 | [[services-cc_webhook_receiver-py]] | 0 | — | CC Reply Webhook Receiver — receives POSTs from the CC Stop hook and |
| 14 | [[services-cost_tracker-py]] | 0 | — |  |
| 15 | [[services-handlers-cc_command_handler-py]] | 0 | — | Inline command handlers for Discord on_message. |

## Traversal

- Back to wing → [[services-wing|services wing]]
- Up to palace → [[../index|Memory Palace index]]
- Retrieval rules → [[../../retrieval_rules|retrieval_rules.md]]

## Raw Paths

```
  services/discord_bot.py
  services/telegram_control.py
  services/apify_scraper.py
  services/icp_scorer.py
  services/calendly_webhook.py
  services/goal_api.py
  services/higgsfield_webhook.py
  services/dm_monitor.py
  services/heartbeat.py
  services/kpi_tracker.py
  services/local_bridge_server.py
  services/overnight_scrape.py
  services/cc_webhook_receiver.py
  services/cost_tracker.py
  services/handlers/cc_command_handler.py
```
