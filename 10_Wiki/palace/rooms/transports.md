---
type: palace-room
room_id: transports
wing: services
generated: 2026-04-11
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
| 1 | [[services-discord_bot-py]] | 21 | `critical` `entry` | EntrepreneurOS Discord Bot — DEX conversational layer. |
| 2 | [[services-telegram_control-py]] | 10 | `critical` |  |
| 3 | [[services-dm_monitor-py]] | 7 | `entry` |  |
| 4 | [[services-apify_scraper-py]] | 5 | `entry` |  |
| 5 | [[services-icp_scorer-py]] | 5 | `entry` |  |
| 6 | [[services-calendly_webhook-py]] | 4 | `entry` |  |
| 7 | [[services-higgsfield_webhook-py]] | 4 | `entry` | Higgsfield Cloud API webhook receiver. |
| 8 | [[services-heartbeat-py]] | 3 | `entry` | EOS Heartbeat Service |
| 9 | [[services-kpi_tracker-py]] | 3 | `entry` |  |
| 10 | [[services-overnight_scrape-py]] | 3 | `entry` |  |
| 11 | [[services-cost_tracker-py]] | 0 | — |  |
| 12 | [[services-handlers-cc_command_handler-py]] | 0 | — | Inline command handlers for Discord on_message. |
| 13 | [[services-handlers-intent_handler-py]] | 0 | — | Intent classification and gateway routing. |
| 14 | [[services-handlers-pipeline_handler-py]] | 0 | — | Pipeline update detection and Notion stage updates. |
| 15 | [[services-handlers-voice_handler-py]] | 0 | — | Voice handler — skeleton module. |

## Traversal

- Back to wing → [[services-wing|services wing]]
- Up to palace → [[../index|Memory Palace index]]
- Retrieval rules → [[../../retrieval_rules|retrieval_rules.md]]

## Raw Paths

```
  services/discord_bot.py
  services/telegram_control.py
  services/dm_monitor.py
  services/apify_scraper.py
  services/icp_scorer.py
  services/calendly_webhook.py
  services/higgsfield_webhook.py
  services/heartbeat.py
  services/kpi_tracker.py
  services/overnight_scrape.py
  services/cost_tracker.py
  services/handlers/cc_command_handler.py
  services/handlers/intent_handler.py
  services/handlers/pipeline_handler.py
  services/handlers/voice_handler.py
```
