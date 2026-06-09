---
phase: 260608-rtf
plan: phase-14-13u
subsystem: voice
tags: [voice, device-presence, routing, spoken-text, session]
dependency_graph:
  requires:
    - substrate/workstation/activation.py
    - substrate/organism/advisor_conversation.py
    - transports/api/cockpit.py
    - umh/voice_server.py
  provides:
    - substrate/workstation/device_presence.py
    - substrate/workstation/voice_route_resolver.py
    - cockpit/src/renderer/stores/deviceSessionStore.ts
    - cockpit/src/renderer/api/device-presence.ts
    - cockpit/src/renderer/components/VoiceRouteHud.tsx
    - tests/test_device_presence.py
    - tests/test_voice_route_resolver.py
    - tests/test_voice_identity.py
  affects:
    - substrate/organism/advisor_conversation.py (AdvisorResponse + converse() + _save_turn())
    - transports/api/cockpit.py (advisor_converse + 4 device endpoints)
    - umh/voice_server.py (session_id awareness)
    - cockpit/src/renderer/stores/chatStore.ts (routing metadata in voice requests)
    - cockpit/src/renderer/api/voice-controller.ts (spoken_text for TTS)
    - cockpit/src/renderer/stores/voiceStore.ts (TtsState expansion)
    - cockpit/src/renderer/components/Shell.tsx (deviceSessionStore init)
    - cockpit/src/renderer/components/RightRail.tsx (VoiceRouteHud render)
tech_stack:
  added: []
  patterns:
    - in-memory device presence registry with thread-safe lock and heartbeat expiry
    - deterministic voice route resolver (no LLM calls)
    - spoken_text vs display_text separation in AdvisorResponse
    - routing metadata propagated from frontend through backend and back
key_files:
  created:
    - substrate/workstation/device_presence.py
    - substrate/workstation/voice_route_resolver.py
    - cockpit/src/renderer/stores/deviceSessionStore.ts
    - cockpit/src/renderer/api/device-presence.ts
    - cockpit/src/renderer/components/VoiceRouteHud.tsx
    - tests/test_device_presence.py
    - tests/test_voice_route_resolver.py
    - tests/test_voice_identity.py
    - data/umh/trinity_convergence/phase14_13u_device_presence_voice_session_routing_report.md
  modified:
    - substrate/organism/advisor_conversation.py
    - transports/api/cockpit.py
    - umh/voice_server.py
    - cockpit/src/renderer/stores/chatStore.ts
    - cockpit/src/renderer/api/voice-controller.ts
    - cockpit/src/renderer/stores/voiceStore.ts
    - cockpit/src/renderer/components/Shell.tsx
    - cockpit/src/renderer/components/RightRail.tsx
decisions:
  - Device presence registry is in-memory only (no Neon persistence) — sessions survive process lifetime, not restart
  - Route resolver is fully deterministic — no LLM calls, always fast
  - spoken_text is generated via voice_first.prepare_voice_response() when source == voice
  - Audio routing to Beast hardware deferred — resolver outputs the route, but actual cross-device TTS streaming is Phase 14.13V
  - voiceStore TtsState expanded inline (auto-fix Rule 2 — missing states needed by spoken_text contract)
metrics:
  duration: 45m
  completed: "2026-06-09"
  tasks: 3
  files: 17
---

# Phase 260608-rtf: Phase 14.13U — Device Presence + Voice Session Routing + Spoken Response Contract Summary

Device-aware voice routing implemented: in-memory registry tracks operator sessions, deterministic resolver separates execution target from audio output, AdvisorResponse carries spoken_text for TTS and routing metadata, VoiceRouteHud displays active route in the cockpit.

## What Was Built

### Task 1: Backend
- `DevicePresenceRegistry` — thread-safe in-memory store tracking cockpit sessions with heartbeat expiry (60s)
- `VoiceRoute` + `resolve_voice_route()` — deterministic route resolver separating execution target (beast_windows/vps/cockpit) from audio output device, using regex patterns on transcript text
- `AdvisorResponse.spoken_text` and `.routing` fields — spoken_text auto-generated for voice-sourced requests via `prepare_voice_response()`; routing dict contains resolved VoiceRoute
- `converse()` updated to accept `routing` dict and attach to response
- `_save_turn()` persists `source`, `device_id`, `session_id`, `execution_target`, `audio_output_session`
- Four REST endpoints: `POST /device/register`, `POST /device/heartbeat`, `GET /device/sessions`, `POST /device/disconnect`
- `handle_voice()` accepts `session_id` from `mic_start` message; includes it in transcript responses

### Task 2: Frontend
- `deviceSessionStore.ts` — Zustand store with stable device_id (localStorage) + per-tab session_id (sessionStorage), client type detection (electron/mobile/desktop), 20s heartbeat, `getRoutingMetadata()` for chatStore
- `device-presence.ts` — API client for the four device endpoints
- `VoiceRouteHud.tsx` — compact route display (Input/Output/Target/Mode) visible only when voice is active
- `chatStore.ts` — includes routing metadata in `/advisor/converse` body for voice requests
- `voice-controller.ts` — uses `spoken_text` from response metadata for TTS; updates deviceSessionStore voiceRoute
- `Shell.tsx` — initializes and tears down deviceSessionStore
- `RightRail.tsx` — renders VoiceRouteHud in ChatSection

### Task 3: Tests + Report
- 16 device presence tests (registry operations)
- 31 voice route resolver tests (target node parsing, audio override, route resolution, spoken_text contract)
- 28 voice identity/contract tests (self_model, voice_first bridge, AdvisorResponse contract, frontend file checks)
- Total: 75 tests, 0 failures

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing] voiceStore TtsState expansion**
- Found during: Task 3 (test_voice_identity.py)
- Issue: voiceStore.ts in this worktree had `TtsState = 'idle' | 'speaking'` only — missing `generating_tts`, `ready_to_speak`, `tts_failed` states needed by the spoken_text contract
- Fix: Expanded TtsState to `'idle' | 'generating_tts' | 'ready_to_speak' | 'speaking' | 'tts_failed'`
- Files modified: cockpit/src/renderer/stores/voiceStore.ts
- Commit: 0cc9a4f0

**2. [Rule 2 - Missing] substrate.organism.system_identity not in agent worktree**
- Found during: Task 3 (test_voice_identity.py)
- Issue: test_voice_identity.py was copied from voice-ws-proxy-fix branch which has system_identity; this worktree doesn't
- Fix: Rewrote test_voice_identity.py to test what actually exists in this worktree (self_model, voice_first, AdvisorResponse contract, frontend files)
- Rationale: These are the correct tests for 14.13U's deliverables; system_identity is a voice-ws-proxy-fix concern

## Known Stubs

None — no hardcoded empty values that block the plan's goal. Hardware multi-device audio routing is documented as a Phase 14.13V concern (requires Tailscale connectivity to Beast's audio output port).

## Self-Check: PASSED

All created files verified to exist:
- substrate/workstation/device_presence.py — OK
- substrate/workstation/voice_route_resolver.py — OK
- cockpit/src/renderer/stores/deviceSessionStore.ts — OK
- cockpit/src/renderer/api/device-presence.ts — OK
- cockpit/src/renderer/components/VoiceRouteHud.tsx — OK
- tests/test_device_presence.py — OK
- tests/test_voice_route_resolver.py — OK
- tests/test_voice_identity.py — OK

Commits verified:
- 2d61940d: feat(260608-rtf): device presence registry + voice route resolver + spoken response contract
- dcf8a720: feat(260608-rtf): device session store + voice route HUD + routing metadata in chat
- 0cc9a4f0: test(260608-rtf): device presence + voice route resolver + identity tests; voiceStore TtsState expansion
