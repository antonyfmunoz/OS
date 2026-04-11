---
type: palace-room
room_id: substrate
wing: eos_ai
generated: 2026-04-11
---

# Room — Substrate Layer

**Wing:** [[eos_ai-wing|eos_ai]]  
**Palace:** [[../index|EOS Memory Palace]]

## Purpose

Voice/meeting/operator pipeline — station daemon + transports.

## Core Loci

Top-ranked files by dependency centrality, criticality, and entry status.
These are the files you most often need; open them before grepping.

| # | Locus | Score | Flags | One-liner |
|---|-------|-------|-------|-----------|
| 1 | [[eos_ai-substrate-station_daemon-py]] | 45 | `entry` | StationDaemon — minimal local node execution loop. |
| 2 | [[eos_ai-substrate-station_bus-py]] | 44 | — | StationBus — MVP transport between EOS and local Station Daemons. |
| 3 | [[eos_ai-substrate-voice_session-py]] | 41 | — | Voice session — bounded live voice-presence layer for the substrate. |
| 4 | [[eos_ai-substrate-local_listener-py]] | 24 | — | Local listener — bounded wake/activation layer for the substrate. |
| 5 | [[eos_ai-substrate-nodes-py]] | 22 | — | Node abstraction — execution targets beyond "the VPS". |
| 6 | [[eos_ai-substrate-ritual_body-py]] | 21 | — | Ritual body — tiny executable layer for open_day / close_day. |
| 7 | [[eos_ai-substrate-audio_loop-py]] | 20 | — | Audio loop — bounded local interaction-window model. |
| 8 | [[eos_ai-substrate-actions-py]] | 18 | — | SafeAction schema — structured intents for future local execution. |
| 9 | [[eos_ai-substrate-result_query-py]] | 17 | — | Result query helpers — tiny operator-facing view over the ResultStore. |
| 10 | [[eos_ai-substrate-result_store-py]] | 16 | — | ResultStore — durable index of ingested ActionResults. |
| 11 | [[eos_ai-substrate-rituals-py]] | 16 | — | Ritual workflow scaffold — open_day / close_day. |
| 12 | [[eos_ai-substrate-ritual_runner-py]] | 15 | `entry` | Ritual runner — shell-callable entry points for open_day / close_day. |
| 13 | [[eos_ai-substrate-discord_text_transport-py]] | 13 | — | Discord text transport — Pseudo-Live Voice Loop v1. |
| 14 | [[eos_ai-substrate-station_drainer-py]] | 13 | — | Station drainer — EOS-side ingestion seam for inbox messages. |
| 15 | [[eos_ai-substrate-wake_producer-py]] | 13 | — | Wake producer — bounded wake-word / clap activation layer for the substrate. |

## Traversal

- Back to wing → [[eos_ai-wing|eos_ai wing]]
- Up to palace → [[../index|Memory Palace index]]
- Retrieval rules → [[../../retrieval_rules|retrieval_rules.md]]

## Raw Paths

```
  eos_ai/substrate/station_daemon.py
  eos_ai/substrate/station_bus.py
  eos_ai/substrate/voice_session.py
  eos_ai/substrate/local_listener.py
  eos_ai/substrate/nodes.py
  eos_ai/substrate/ritual_body.py
  eos_ai/substrate/audio_loop.py
  eos_ai/substrate/actions.py
  eos_ai/substrate/result_query.py
  eos_ai/substrate/result_store.py
  eos_ai/substrate/rituals.py
  eos_ai/substrate/ritual_runner.py
  eos_ai/substrate/discord_text_transport.py
  eos_ai/substrate/station_drainer.py
  eos_ai/substrate/wake_producer.py
```
