---
type: codebase-class
file: eos_ai/substrate/live_sessions.py
line: 92
generated: 2026-05-07
---

# LiveSession

**File:** [[eos_ai-substrate-live_sessions-py]] | **Line:** 92

A bounded real-time interaction container.

Tracks one continuous session with agent roles, attached resources,
and lifecycle state. Persisted via LiveSessionStore.

## Methods

- [[eos_ai-substrate-live_sessions-py-LiveSession-new]]`(title, session_type) → 'LiveSession'` — Create a new LiveSession with generated ID and current timestamps.
- [[eos_ai-substrate-live_sessions-py-LiveSession-is_terminal]]`() → bool` — Return True if session is in a terminal state (ENDED or FAILED).
- [[eos_ai-substrate-live_sessions-py-LiveSession-to_dict]]`() → dict` — Return a JSON-safe dict. Enums serialized as their .value.
- [[eos_ai-substrate-live_sessions-py-LiveSession-from_dict]]`(d) → 'LiveSession'` — Deserialize from a dict, reconstructing enums and guarding list fields.

## Decorators

- `@dataclass`
