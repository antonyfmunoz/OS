# Interface Projection Contract v1

**Date**: 2026-05-04
**Phase**: 94D.3 — Central Advisor Session + Interface-Agnostic Communication Bus Correction v1

---

## 1. What an Interface Projection Is

An interface projection is a UI/channel-specific representation of the same central advisor session. It is a window into the session, not a separate session.

Every projection renders the same underlying session state through interface-appropriate affordances. A Discord embed with buttons, a CLI text prompt, and a voice utterance can all represent the same approval request.

---

## 2. Interface Projection Contract

Every interface projection must declare:

```
InterfaceProjection:
  interface_id:         str            — unique identifier (e.g., "cli_vps_main")
  interface_type:       InterfaceType  — CLI, DISCORD, TELEGRAM, MOBILE, WORKSTATION, VOICE, BROWSER_OVERLAY, WEB_DASHBOARD
  capabilities:         set[str]       — what this interface can do
  limitations:          list[str]      — what this interface cannot do
  input_modalities:     list[str]      — text, command, button, tap, voice, gesture, hotkey
  output_modalities:    list[str]      — text, embed, notification, audio, panel, overlay
  authentication:       str            — how the founder is authenticated on this interface
  supported_msg_types:  set[str]       — which MessageType values this interface can render
  approval_support:     ApprovalMode   — TEXT_PROMPT, BUTTON, INLINE_KEYBOARD, MODAL, VOICE_CONFIRM, NONE
  file_support:         bool           — can send/receive files
  evidence_support:     bool           — can display screenshots, exports
  realtime_support:     bool           — supports streaming/live updates
  fallback_behavior:    str            — what to do when this interface can't handle a message type
  connected:            bool           — currently active
  last_activity:        str            — ISO 8601 timestamp
```

---

## 3. Interface Type Enum

```
InterfaceType:
  CLI                — terminal-based (VPS tmux, Termius, local shell)
  DISCORD            — Discord channel/DM
  TELEGRAM           — Telegram chat
  MOBILE_APP         — native mobile application
  WORKSTATION_UI     — desktop application (Jarvis UI, Electron, etc.)
  VOICE              — audio-only (microphone + speaker)
  BROWSER_OVERLAY    — in-browser overlay/extension
  WEB_DASHBOARD      — web application
```

---

## 4. Approval Mode Enum

```
ApprovalMode:
  TEXT_PROMPT         — "Type APPROVE or DENY"
  BUTTON              — clickable buttons (Discord, web)
  INLINE_KEYBOARD     — inline buttons (Telegram)
  MODAL               — dialog box (desktop, mobile)
  VOICE_CONFIRM       — "Say yes or no"
  NONE                — this interface cannot handle approvals (read-only)
```

---

## 5. Interface Declarations

### CLI (VPS / Termius / Local Shell)

```
interface_id:       "cli_vps_main"
interface_type:     CLI
capabilities:       {text_input, text_output, command_input, file_path_reference, log_streaming}
limitations:        ["no buttons", "no rich media inline", "no push notifications"]
input_modalities:   [text, command]
output_modalities:  [text]
authentication:     SSH key / session token
supported_msg_types: ALL
approval_support:   TEXT_PROMPT
file_support:       true (via path reference, scp)
evidence_support:   false (text description only, paths to files)
realtime_support:   true (streaming output)
fallback_behavior:  "render as plain text"
```

### Discord

```
interface_id:       "discord_eos_channel"
interface_type:     DISCORD
capabilities:       {text_input, text_output, button_input, embed_output, file_upload, file_download, reaction_input}
limitations:        ["2000 char message limit", "no terminal streaming", "async delivery"]
input_modalities:   [text, button, reaction]
output_modalities:  [text, embed, button, file]
authentication:     Discord user ID (FOUNDER_DISCORD_ID)
supported_msg_types: ALL except HEARTBEAT
approval_support:   BUTTON
file_support:       true
evidence_support:   true (image embeds, file attachments)
realtime_support:   true (websocket)
fallback_behavior:  "queue and deliver on next interaction"
```

### Telegram

```
interface_id:       "telegram_founder"
interface_type:     TELEGRAM
capabilities:       {text_input, text_output, inline_button_input, file_upload, file_download}
limitations:        ["4096 char limit", "no rich embeds", "inline keyboards only"]
input_modalities:   [text, command, inline_button]
output_modalities:  [text, inline_keyboard, file]
authentication:     Telegram user ID
supported_msg_types: ALL except HEARTBEAT
approval_support:   INLINE_KEYBOARD
file_support:       true
evidence_support:   true (image messages)
realtime_support:   true (webhook)
fallback_behavior:  "queue and deliver on next message"
```

### Mobile App

```
interface_id:       "mobile_eos"
interface_type:     MOBILE_APP
capabilities:       {text_input, text_output, tap_input, push_notification, voice_input, voice_output}
limitations:        ["small screen", "intermittent connectivity"]
input_modalities:   [text, tap, voice]
output_modalities:  [text, notification, audio]
authentication:     App-level auth (biometric + token)
supported_msg_types: ALL
approval_support:   MODAL
file_support:       true (with size constraints)
evidence_support:   true
realtime_support:   true (websocket + push)
fallback_behavior:  "push notification with summary, full content on open"
```

### Workstation UI (Jarvis)

```
interface_id:       "workstation_jarvis"
interface_type:     WORKSTATION_UI
capabilities:       {text_input, text_output, voice_input, voice_output, panel_output, live_state, computer_use_observation, hotkey_input}
limitations:        ["local PC only", "requires desktop application running"]
input_modalities:   [text, hotkey, voice, gesture]
output_modalities:  [text, panel, audio, video_feed, overlay]
authentication:     Local OS session + Tailscale identity
supported_msg_types: ALL
approval_support:   MODAL
file_support:       true
evidence_support:   true (live screen observation)
realtime_support:   true (local process)
fallback_behavior:  "spoken summary if panels unavailable"
```

### Voice

```
interface_id:       "voice_eos"
interface_type:     VOICE
capabilities:       {voice_input, voice_output, spoken_command}
limitations:        ["no visual output", "no file transfer", "latency on STT/TTS"]
input_modalities:   [voice]
output_modalities:  [audio]
authentication:     Voice recognition / session context
supported_msg_types: {INTENT, COMMAND, APPROVAL_RESPONSE, CLARIFICATION_RESPONSE, STOP, PAUSE, RESUME, ADVISORY, QUESTION, APPROVAL_REQUEST, STATUS_SUMMARY, RISK_WARNING}
approval_support:   VOICE_CONFIRM
file_support:       false
evidence_support:   false (verbal description only)
realtime_support:   true (streaming)
fallback_behavior:  "speak summary, defer file/evidence to visual interface"
```

### Browser Overlay

```
interface_id:       "browser_overlay"
interface_type:     BROWSER_OVERLAY
capabilities:       {text_input, text_output, click_input, overlay_output, context_observation}
limitations:        ["browser-dependent", "limited screen space", "may conflict with target page"]
input_modalities:   [text, click]
output_modalities:  [overlay, notification]
authentication:     Browser extension token
supported_msg_types: {APPROVAL_REQUEST, APPROVAL_RESPONSE, STATUS_SUMMARY, STOP, PAUSE}
approval_support:   BUTTON
file_support:       false
evidence_support:   true (can capture current page)
realtime_support:   true (extension messaging)
fallback_behavior:  "minimize overlay, queue messages"
```

### Web Dashboard

```
interface_id:       "web_dashboard"
interface_type:     WEB_DASHBOARD
capabilities:       {text_input, text_output, form_input, chart_output, table_output, file_upload, file_download}
limitations:        ["requires browser", "session timeout"]
input_modalities:   [text, click, form]
output_modalities:  [text, table, chart, form, file]
authentication:     Web session token
supported_msg_types: ALL
approval_support:   BUTTON
file_support:       true
evidence_support:   true
realtime_support:   true (websocket)
fallback_behavior:  "refresh on reconnect, show queued messages"
```

---

## 6. Capability Requirements by Message Type

| Message Type | Minimum Interface Capability |
|-------------|------------------------------|
| INTENT | text_input |
| COMMAND | text_input OR command_input |
| APPROVAL_REQUEST | text_output + any approval_support except NONE |
| APPROVAL_RESPONSE | text_input OR button_input OR voice_input |
| STATUS_SUMMARY | text_output |
| EVIDENCE_AVAILABLE | file_support OR evidence_support (degrades to text description) |
| STOP / PAUSE / RESUME | text_input OR command_input OR voice_input |
| RISK_WARNING | text_output (URGENT priority → push if available) |

---

## 7. Fallback Chain

When the target interface cannot handle a message type:

1. Try to render in degraded form (e.g., evidence → text description)
2. If degraded rendering is impossible, route to next active interface
3. If no active interface can handle it, queue with notification on all interfaces: "Pending message requires [capability] — switch to an interface that supports it"
4. Never silently drop a message
