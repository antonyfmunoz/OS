---
type: codebase-class
file: eos_ai/substrate/voice_session.py
line: 467
generated: 2026-04-12
---

# VoiceSessionRuntime

**File:** [[eos_ai-substrate-voice_session-py]] | **Line:** 467

Bounded, deterministic voice session runtime.

All public methods are best-effort: they never raise into the caller.
On failure they mark the session ERROR with a reason and persist it,
matching the local_listener emit() pattern.

## Methods

- [[eos_ai-substrate-voice_session-py-VoiceSessionRuntime-__init__]]`(store) → None` — 
- [[eos_ai-substrate-voice_session-py-VoiceSessionRuntime-start_session]]`(node_id, role_slug) → VoiceSession` — Start a new voice session targeting `node_id` with `role_slug`.
- [[eos_ai-substrate-voice_session-py-VoiceSessionRuntime-end_session]]`(session_id) → Optional[VoiceSession]` — 
- [[eos_ai-substrate-voice_session-py-VoiceSessionRuntime-submit_utterance]]`(session_id, text) → Optional[VoiceSession]` — Submit a bounded utterance to the active session.
- [[eos_ai-substrate-voice_session-py-VoiceSessionRuntime-switch_role]]`(session_id, new_role_slug) → Optional[VoiceSession]` — 
- [[eos_ai-substrate-voice_session-py-VoiceSessionRuntime-_resolve_role]]`(role_slug) → Optional[AgentRole]` — 
