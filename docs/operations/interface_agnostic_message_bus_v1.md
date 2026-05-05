# Interface-Agnostic Message Bus v1

**Date**: 2026-05-04
**Phase**: 94D.3 — Central Advisor Session + Interface-Agnostic Communication Bus Correction v1

---

## 1. Principle

Every message in EOS flows through one bus. The bus does not know or care which interface originated the message. A command typed in a CLI terminal, a button press in Discord, a voice utterance transcribed on the workstation, and a tap in a mobile app all normalize into the same message envelope.

The founder should be able to start a conversation in one interface and continue it in another without losing context, pending approvals, or session state.

---

## 2. Message Envelope

Every message on the bus uses this envelope:

```
MessageEnvelope:
  message_id:        str           — UUID, unique per message
  session_id:        str           — advisor session this belongs to
  conversation_id:   str | None    — thread/conversation within session
  source_interface:  str           — which interface originated this (cli, discord, telegram, voice, etc.)
  target:            str           — routing target (advisor, node:<id>, interface:<id>, broadcast)
  sender:            str           — who sent it (founder, advisor, node:<id>, system)
  recipient:         str           — intended recipient
  message_type:      str           — enum value from MessageType
  payload:           dict          — type-specific content
  priority:          str           — LOW, NORMAL, HIGH, URGENT
  requires_response: bool          — does this need a reply?
  approval_required: bool          — is this an approval gate?
  timestamp:         str           — ISO 8601 UTC
  correlation_id:    str | None    — links related messages (e.g., request → response)
  parent_message_id: str | None    — for threaded replies
  work_order_id:     str | None    — if this relates to a specific work order
  node_id:           str | None    — if this originates from or targets a specific node
  status:            str           — PENDING, DELIVERED, ACKNOWLEDGED, PROCESSED, FAILED
  audit_tags:        list[str]     — governance/compliance tags
```

---

## 3. Supported Interfaces

| Interface ID | Type | Input | Output | Real-time | Approval Support |
|-------------|------|-------|--------|-----------|-----------------|
| `cli_vps` | CLI | text, commands | text, logs | yes (stream) | text prompt y/n |
| `cli_termius` | CLI | text, commands | text, logs | yes (stream) | text prompt y/n |
| `discord` | Chat | text, buttons, files | text, embeds, buttons, files | yes (websocket) | button/reaction |
| `telegram` | Chat | text, commands | text, inline buttons | yes (webhook) | inline keyboard |
| `mobile_app` | Native | text, tap, voice | text, push notification, UI | yes (websocket) | native dialog |
| `workstation_ui` | Desktop | text, hotkey, mouse, voice | panels, state, video feed | yes (local) | modal dialog |
| `voice` | Audio | speech (STT) | speech (TTS) | yes (stream) | spoken confirm |
| `browser_overlay` | Web | text, click | overlay panels, notifications | yes (websocket) | inline prompt |
| `web_dashboard` | Web | text, click | charts, tables, forms | yes (polling/ws) | form submit |

---

## 4. Interface Normalization

Every interface adapter converts native input to a `MessageEnvelope` and converts `MessageEnvelope` output to native display.

```
[CLI input]        → cli_adapter.normalize()       → MessageEnvelope
[Discord message]  → discord_adapter.normalize()   → MessageEnvelope
[Voice transcript] → voice_adapter.normalize()     → MessageEnvelope
[Mobile tap]       → mobile_adapter.normalize()    → MessageEnvelope

MessageEnvelope    → cli_adapter.render()           → [terminal text]
MessageEnvelope    → discord_adapter.render()       → [embed + buttons]
MessageEnvelope    → voice_adapter.render()         → [TTS utterance]
MessageEnvelope    → mobile_adapter.render()        → [push notification]
```

---

## 5. Bus Routing

```
MessageEnvelope arrives
  → Bus validates envelope (required fields, known type)
  → Bus resolves target:
      "advisor"          → central advisor session
      "node:<node_id>"   → execution node (via bridge, station bus, or SSH)
      "interface:<id>"   → specific interface projection
      "broadcast"        → all connected interfaces
      "founder"          → active interface(s) with highest priority
  → Bus delivers to target
  → Bus updates envelope status (DELIVERED, ACKNOWLEDGED)
  → Bus logs to audit trail
```

---

## 6. Transport Layer (How Messages Move)

The bus is transport-agnostic. It delegates delivery to available transports:

| Route | Transport | Mechanism |
|-------|-----------|-----------|
| VPS ↔ Advisor | In-process | Direct function call (same process) |
| VPS → Local PC | HTTP bridge | `forward_to_local()` via Tailscale |
| VPS → Local PC | SSH | `ssh → wsl → tmux send-keys` |
| VPS → Local PC | Station bus | File-based JSON (outbox/inbox) |
| Local PC → VPS | HTTP POST | `/cc-reply` or `/work-order-result` |
| VPS → Discord | py-cord | Discord API via bot |
| VPS → Telegram | python-telegram-bot | Telegram API |
| VPS → Mobile | Push notification | FCM/APNs (future) |
| VPS → Voice | TTS engine | Via voice_engine.py |
| Voice → VPS | STT engine | Via voice_engine.py |

The bus selects transport based on target and availability. If primary transport fails, it falls back to the next available.

---

## 7. Continuity Protocol

When the founder switches interfaces:

1. New interface sends `SWITCH_INTERFACE` message
2. Bus registers new interface as active
3. Bus sends buffered pending messages (approvals, questions, status) to new interface
4. Old interface remains registered (can still receive, lower priority)
5. Session state is NOT reset — conversation continues

When all interfaces disconnect:

1. Messages queue in the advisor session
2. When any interface reconnects, queued messages are delivered
3. No messages are lost
4. Work orders continue executing (approvals queue until founder reconnects)

---

## 8. Priority System

| Priority | Delivery | Use Case |
|----------|----------|----------|
| URGENT | Immediate push to all active interfaces | Safety violation, credential exposure, wrong account |
| HIGH | Immediate push to primary active interface | Approval request, error, blocked |
| NORMAL | Standard delivery | Status update, result, advisory |
| LOW | Queue, deliver on next interaction | Heartbeat, non-critical audit event |

---

## 9. Relationship to Existing Systems

| Existing System | Role in New Architecture |
|----------------|------------------------|
| `local_bridge_client.py` | Transport adapter for VPS→local delivery |
| `local_bridge_server.py` | Transport adapter for receiving on local |
| `station_bus.py` | Alternative transport adapter (file-based) |
| `discord_bot.py` | Interface adapter for Discord projection |
| `cc_webhook_receiver.py` | Transport adapter for receiving results on VPS |
| `session_discord_bridge.py` | Existing approval relay — becomes one adapter |

None of these are replaced. They become adapters that plug into the bus. The bus sits above them as the routing and normalization layer.

---

## 10. What This Changes About WO-001

Before (broken):
```
Work order → local terminal → local worker asks for approval in terminal
→ Founder must be typing in local terminal to approve
→ Single interface lock-in
```

After (corrected):
```
Work order → local worker → APPROVAL_NEEDED message → message bus
→ Bus routes to advisor session
→ Advisor routes to founder's active interface (CLI, Discord, phone, voice)
→ Founder responds APPROVE from any interface
→ Bus routes APPROVAL_RESPONSE back to local worker
→ Local worker continues
```

The founder can be on the VPS CLI, on Discord, or on the phone. The local worker never needs to know which interface the founder is using.
