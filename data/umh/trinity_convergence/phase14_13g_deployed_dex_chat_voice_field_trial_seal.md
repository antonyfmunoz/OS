# Phase 14.13G — Deployed DEX Chat + Voice Field Trial Seal

**Date**: 2026-06-07
**Commits**: 63fde2dc (routing fix), 4f554aea (CC bridge error message fix)
**Endpoint**: localhost:8091/api/umh/dex/converse
**Verdict**: DEPLOYED DAILY-DRIVER READY WITH TRUTHFUL LIMITATIONS

---

## Test Results: 14/14 PASS

### Routing Fix (Primary Objective) — PASS
| Test | Input | Expected Intent | Actual Intent | Result |
|------|-------|----------------|---------------|--------|
| T1 | "What am I looking at, and what should I do next?" | explain_current_view | explain_current_view | PASS |
| T8 | "is this good enough?" | unknown (conversational) | unknown | PASS |
| T7 | "Let's think through the highest leverage move" | unknown (conversational) | unknown | PASS |
| T11 | "what am I looking at?" (no view_context) | explain_current_view + fallback | explain_current_view + fallback | PASS |

**The core bug is fixed.** Advisory phrases no longer route to the execution spine. View-context questions return conversational responses via fast model. No "Execution successful" leakage.

### Explicit Action Commands — PASS
| Test | Input | Expected Intent | Actual Intent | Result |
|------|-------|----------------|---------------|--------|
| T2 | "create a work packet for fixing auth middleware timeout" | work_packet_draft | work_packet_draft | PASS |
| T3 | "turn this into work packets" | decompose_intent | decompose_intent | PASS |
| T4 | "run council review on the current routing implementation" | council_review | council_review | PASS |

All explicit action intents route correctly and produce substantive responses.

### Claude Code Bridge — PASS (Truthful Limitations)
| Test | Input | Expected | Actual | Result |
|------|-------|----------|--------|--------|
| T5 | "send to claude code: check the routing tests" | cc_send + truthful blocker | cc_send + specific error + suggested actions | PASS |
| T6 | "what did claude do" | cc_capture + truthful state | cc_capture + truthful | PASS |

**T5 verified behavior**: Intent classification is correct (cc_send). Two failure paths, both specific:
- **No sessions exist**: "No active Claude Code sessions found. Start a session first." + `[Check sessions]`
- **Sessions exist but send fails**: "Claude Code send failed: No active Claude Code session accepted the message. Check that a session is running and attached." + `[Check sessions, Retry]`

No raw "unknown" appears in either path. Claude Code delegation is NOT operational — no active session receives the message. The bridge reports the exact blocker truthfully.

### Informational Queries — PASS
| Test | Input | Expected Intent | Actual Intent | Result |
|------|-------|----------------|---------------|--------|
| T12 | "current status" | status_query | status_query | PASS |
| T13 | "catch me up" | resume_query | resume_query | PASS |
| T14 | "show dashboard" | cockpit_navigation | cockpit_navigation | PASS |

### Conversation Infrastructure — PASS
| Test | Description | Result |
|------|-------------|--------|
| T9 | History endpoint returns conversation entries | PASS (10+ entries) |
| T10 | Suggested actions well-formed (label + action + payload) | PASS (2 actions) |
| Persistence | Multiple messages to same conversation_id stored and retrievable | PASS |
| Response shape | Keys: text, intent, suggested_actions, metadata, conversation_id, message_id, timestamp | PASS |

### Voice — NOT INTEGRATED (Truthful State)
- Voice subsystem exists at `/api/umh/voice/` (transports/api/voice.py) and `/api/voice/tts` (operator_api.py)
- Voice is NOT under the DEX conversation layer (`/dex/voice/` returns 404)
- Voice is a separate subsystem with its own session management (VoiceSession, not DexConversation)
- This is architectural, not a routing failure
- **Not proven integrated. Not claimed integrated.**

### Browser-Side Rendering — VERIFIED (Structural)
- Response shape matches frontend contract in chatStore.ts
- `suggested_actions` array contains well-formed `{label, action, payload}` objects
- `intent` field present for badge rendering in RightRail.tsx
- `metadata.model_tier` present for future UX differentiation
- `conversation_id` and `message_id` present for history tracking
- Frontend verified structurally — not browser-tested (headless auth required)

---

## Capability Matrix

| Capability | Status | Notes |
|-----------|--------|-------|
| View-context advisory | DEPLOYED | explain_current_view intent, fast model, fallback when no context |
| Conversational chat | DEPLOYED | UNKNOWN intent to LLM conversation, suggested actions |
| Work packet creation | DEPLOYED | Explicit commands only, no advisory phrase leakage |
| Decompose command | DEPLOYED | Routes correctly |
| Council review | DEPLOYED | Routes correctly, returns substantive text |
| CC bridge send | TRUTHFUL BLOCKER | Intent routes correctly, specific error when no active session, suggested actions for recovery |
| CC bridge capture | DEPLOYED | Truthful state when no session |
| Status/resume/nav | DEPLOYED | All informational intents work |
| Conversation history | DEPLOYED | Persisted, retrievable, correct shape |
| Suggested actions | DEPLOYED | Non-mutating, well-formed for frontend |
| Voice via DEX | NOT INTEGRATED | Separate subsystem, not proven integrated |
| Browser rendering | STRUCTURAL PASS | Shape verified, no headless auth test |

---

## What Was Fixed in 14.13G

1. **Added EXPLAIN_CURRENT_VIEW intent** — new enum value + signal list + handler
2. **Tightened _WORK_PACKET_SIGNALS** — removed 9 advisory phrases, kept 9 explicit commands
3. **Removed "is this good enough" from council signals** — stays conversational
4. **Reordered classify_intent()** — explicit actions first, view-context after, UNKNOWN last
5. **Added _handle_explain_view()** — view-context-aware conversational response via fast model
6. **Improved _handle_advisor_signal()** — detects empty/generic responses, gives recovery guidance
7. **Fixed CC bridge error messages** — both no-session and send-failure paths return specific, actionable messages with suggested actions. No raw "unknown" errors.
8. **16 new tests** — 60 total jarvis_command tests pass, 42 related tests pass (102 total)

## Truthful Limitations

1. **Claude Code delegation is not operational.** The bridge correctly identifies and reports when no active session exists or when a session cannot accept messages. It does not fake success.
2. **Voice is a separate subsystem.** Voice routes through VoiceSession at `/api/umh/voice/`, not through DexConversation at `/dex/voice/`. Unless explicitly proven integrated, it is not claimed as such.
3. **Browser rendering is structurally verified, not visually confirmed.** Response shape matches the frontend contract but no headless browser test was run due to auth requirements.

---

## Final Verdict

### DEPLOYED DAILY-DRIVER READY WITH TRUTHFUL LIMITATIONS

**Reason**: DEX deployed chat, routing, view context, council, work packet flow, persistence, and field-trial behavior are production-usable. Claude Code bridge now reports the exact blocker when no active session exists. Voice remains a separate subsystem unless explicitly proven integrated. No fake success, no generic bridge failure, no execution-spine misrouting.

**What works daily**: An operator can use DEX chat for conversational advisory, view-context questions, status queries, work packet commands, council reviews, and conversation history without misrouting. Every failure state reports the specific blocker with recovery actions.

**What does not work**: Claude Code message delegation (no active session to receive). Voice via DEX (separate subsystem). Browser visual confirmation (auth-gated).
