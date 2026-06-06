# Phase 14.11D — Presence Activation + Voice/Text Command E2E Slice

## Implementation Report

**Date:** 2026-06-05
**Phase:** 14.11D
**Status:** PARTIAL GO
**Verdict:** All substrate, transport, and cockpit components implemented and tested. Voice/STT is environment-dependent (PARTIAL GO per spec). No capabilities faked.

---

## What Was Built

### A. ActivationSignal Contract (`substrate/workstation/activation.py`)

Typed activation event model covering 8 activation sources:
- `manual_cockpit_open` — AVAILABLE
- `hotkey` — AVAILABLE (requires Electron or DISPLAY)
- `typed_command` — AVAILABLE
- `push_to_talk_voice` — environment-dependent (groq SDK + GROQ_API_KEY → available; faster_whisper → degraded; neither → unavailable)
- `discord_remote_command` — AVAILABLE when DISCORD_TOKEN set, DEGRADED otherwise
- `wake_word_unavailable` — NOT_IMPLEMENTED (requires trained model)
- `clap_unavailable` — NOT_IMPLEMENTED (requires trained model)
- `mobile_remote_command_unavailable` — NOT_IMPLEMENTED (use Discord mobile)

Key models: `ActivationSource` (enum, 8 values), `ActivationCapabilityStatus` (enum, 4 values), `ActivationSignal` (dataclass, 13 fields with auto-generated ID/timestamp/node/device), `PresenceCapability`, `PresenceSession`, `get_activation_capabilities()`.

Runtime capability detection: `_detect_stt_status()` and `_detect_stt_blocker()` probe for groq SDK and faster_whisper at import time. No capabilities are faked.

### B. Presence API (`transports/api/cockpit_presence_routes.py`)

4 endpoints on `presence_router` (prefix `/api/umh`):

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/presence/activate` | POST | Create ActivationSignal + PresenceSession |
| `/presence/current` | GET | Current presence state without activation |
| `/presence/command` | POST | Classify text → intent → route command |
| `/presence/capabilities` | GET | All 8 capability statuses + STT/TTS summary |

Helpers: `_load_continuity_state()`, `_load_resume_summary()`, `_load_pending_approvals()`, `_log_presence_event()`, `_check_tts_available()`, `_build_status_response()`, `_build_resume_response()`, `_build_approval_response()`.

Router mounted in cockpit.py via `_mount_presence_router()` — delegation only, no route bodies in cockpit.py. cockpit.py: 2691 lines (under 3000 limit).

### C. Deterministic Command Router (`substrate/workstation/jarvis_command.py`)

7 command intents classified via keyword matching (no LLM dependency):

| Intent | Signal Count | Governance |
|--------|-------------|------------|
| `status_query` | 16 phrases | INFORMATIONAL |
| `resume_query` | 13 phrases | INFORMATIONAL |
| `approval_query` | 10 phrases | INFORMATIONAL |
| `mode_switch` | 22 phrases | INFORMATIONAL |
| `work_packet_draft` | 14 phrases | REQUIRES_GOVERNANCE |
| `cockpit_navigation` | 34 nav keywords | INFORMATIONAL |
| `unknown` | fallback | INFORMATIONAL |

Classification priority: resume → approval → status → mode → work_packet → navigation → unknown.

`resolve_navigation_target()` maps 34 keywords to panel IDs.
`resolve_mode_target()` extracts target mode from text.
`governance_requirement()` gates only `work_packet_draft` as REQUIRES_GOVERNANCE.

### D. Cockpit UI

**HudBar.tsx:** Added STT/TTS status dots polling `/api/umh/presence/capabilities` every 15s. Shows green dot when available, red when unavailable.

**CommandPalette.tsx:** Extended command palette with Jarvis command handler. When no built-in commands match and query > 2 chars, Enter key routes to `POST /api/umh/presence/command`. Handles `panel_target` (setPanel), `mode_target` (setMode), and `response_text` display. "Ask Jarvis: ..." button for explicit invocation.

**index.ts (Electron main):** Registered `Ctrl+Alt+J` global shortcut via `globalShortcut.register()`. Shows/focuses window + sends `activation:hotkey` IPC event. Graceful degradation: logs warning if registration fails. Cleanup via `globalShortcut.unregisterAll()` in before-quit handler.

### E. Trace/Resume Integration

Presence events logged to `data/umh/workstation_state/presence_events.jsonl`:
- Activation events: `{event, activation_id, source, session_id, continuity_state, timestamp}`
- Command events: `{event, command_id, intent, governance, source, text, timestamp}`

Activation → command chains create traceable sequences for resume/debug.

### F. cockpit.py Mount

13-line `_mount_presence_router()` stub added after workspace router. Import + configure + include_router. No route bodies in cockpit.py.

---

## Test Coverage

| Test File | Tests | Coverage Area |
|-----------|-------|---------------|
| `test_phase14_11d_activation_signal.py` | 25 | ActivationSource, ActivationSignal, PresenceCapability, PresenceSession, capability detection |
| `test_phase14_11d_jarvis_command.py` | 43 | classify_intent (20), resolve_navigation_target (6), resolve_mode_target (7), governance_requirement (7), JarvisCommandResult (3) |
| `test_phase14_11d_presence_endpoints.py` | 22 | activate (5), current (3), capabilities (3), command (10), detect_env (1) |
| `test_phase14_11d_voice_integration.py` | 25 | voice routing (6), STT (3), TTS (3), Discord alignment (4), trace/resume (3), hotkey (2), manual (1), governance (3) |
| **Total** | **115** | |

All 115 tests pass clean.

---

## Hard Boundaries Verification

| # | Boundary | Status |
|---|----------|--------|
| 1 | No EOS/CreatorOS/LyfeOS/projection names in substrate/ | PASS — no projection references |
| 2 | No full ambient voice | PASS — push-to-talk only |
| 3 | No wake word/clap training | PASS — both report NOT_IMPLEMENTED |
| 4 | No fake capabilities | PASS — runtime detection, truthful unavailable |
| 5 | No route bodies in cockpit.py | PASS — delegation only |
| 6 | No ExecutionAuthorityEngine bypass | PASS — work_packet_draft → REQUIRES_GOVERNANCE |
| 7 | No runtime daemon data committed | PASS |
| 8 | No dist-web/Playwright/audio committed | PASS |
| 9 | cockpit.py < 3000 lines | PASS — 2691 lines |
| 10 | substrate/ never imports transports/ | PASS |
| 11 | Type coherence — no parallel types | PASS — new types in substrate/workstation/ |
| 12 | Deterministic-first | PASS — keyword classification, no LLM |
| 13 | Python 3.11 compatible | PASS — no 3.12+ syntax |
| 14 | No hardcoded instance context in substrate/ | PASS |
| 15 | No modification of governance gate config | PASS |

---

## Architecture

```
substrate/workstation/activation.py    → ActivationSignal, PresenceSession, capability detection
substrate/workstation/jarvis_command.py → deterministic command classifier, governance routing
transports/api/cockpit_presence_routes.py → 4 API endpoints, presence event logging
transports/api/cockpit.py              → _mount_presence_router() delegation stub
cockpit/src/main/index.ts              → Ctrl+Alt+J global shortcut
cockpit/src/renderer/components/HudBar.tsx → STT/TTS status dots
cockpit/src/renderer/components/CommandPalette.tsx → Jarvis command handler
```

Dependency direction: cockpit UI → transports/api → substrate/workstation (correct, downward only).

---

## Partial GO Rationale

STT capability is environment-dependent:
- **VPS:** groq SDK installed + GROQ_API_KEY set → STT available
- **Beast:** faster_whisper available → STT degraded
- **Minimal env:** neither → STT unavailable (truthfully reported)

TTS capability depends on Beast Kokoro reachability:
- **With Tailscale:** Kokoro at 100.74.199.102:8880 → TTS available
- **Without:** TTS unavailable (truthfully reported)

No capability is faked. All unavailable states are reported with specific blocker messages.

---

## Files Changed

| File | Action | Lines |
|------|--------|-------|
| `substrate/workstation/activation.py` | NEW | 215 |
| `substrate/workstation/jarvis_command.py` | NEW | 282 |
| `transports/api/cockpit_presence_routes.py` | NEW | 372 |
| `transports/api/cockpit.py` | MODIFIED | +13 (mount stub) |
| `cockpit/src/main/index.ts` | MODIFIED | +25 (globalShortcut) |
| `cockpit/src/renderer/components/HudBar.tsx` | MODIFIED | +15 (STT/TTS dots) |
| `cockpit/src/renderer/components/CommandPalette.tsx` | MODIFIED | +35 (Jarvis handler) |
| `tests/test_phase14_11d_activation_signal.py` | NEW | 25 tests |
| `tests/test_phase14_11d_jarvis_command.py` | NEW | 43 tests |
| `tests/test_phase14_11d_presence_endpoints.py` | NEW | 22 tests |
| `tests/test_phase14_11d_voice_integration.py` | NEW | 25 tests |
| Implementation report | NEW | this file |

---

## Commit History

1. `feat(14.11D): ActivationSignal contract + presence endpoints + tests`
2. `feat(14.11D): deterministic Jarvis command router + governance + tests`
3. `test(14.11D): voice/STT/TTS integration + trace/resume + tests`
4. `feat(14.11D): cockpit presence UI — hotkey, STT/TTS dots, Jarvis command palette`
5. `feat(14.11D): mount presence router in cockpit.py — delegation only`
6. `docs(14.11D): implementation report — presence activation + voice/text command E2E`
