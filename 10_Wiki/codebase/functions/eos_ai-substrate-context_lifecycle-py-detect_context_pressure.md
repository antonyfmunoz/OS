---
type: codebase-function
file: eos_ai/substrate/context_lifecycle.py
line: 105
generated: 2026-05-07
---

# detect_context_pressure

**File:** [[eos_ai-substrate-context_lifecycle-py]] | **Line:** 105
**Signature:** `detect_context_pressure(session_name) → dict[str, Any]`

Detect context pressure using multiple signals.

Returns a dict with pressure_score, pressure_level, should_clear,
individual signal contributions, threshold, and lifecycle_version.

## Calls

- [[eos_ai-substrate-context_lifecycle-py-_guard_enabled]]
- [[eos_ai-substrate-context_lifecycle-py-_has_degradation_markers]]
- [[eos_ai-substrate-context_lifecycle-py-_pressure_threshold]]

## Called By

- [[eos_ai-substrate-context_lifecycle-py-maybe_clear_and_restore]]
- [[eos_ai-substrate-discord_text_transport-py-maybe_mirror_discord_text_message]]
