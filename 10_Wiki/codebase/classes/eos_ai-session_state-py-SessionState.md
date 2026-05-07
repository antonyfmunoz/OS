---
type: codebase-class
file: eos_ai/session_state.py
line: 8
generated: 2026-05-07
---

# SessionState

**File:** [[eos_ai-session_state-py]] | **Line:** 8

*No docstring.*

## Methods

- [[eos_ai-session_state-py-SessionState-set_ambient]]`(state) → None` — Store a fresh reality snapshot as ambient state.
- [[eos_ai-session_state-py-SessionState-get_ambient]]`() → dict` — Return the current ambient state. Empty dict if never set.
- [[eos_ai-session_state-py-SessionState-save]]`(phase, last_completed, in_progress, files_modified, next_steps, context) → dict` — 
- [[eos_ai-session_state-py-SessionState-load]]`() → dict | None` — 
- [[eos_ai-session_state-py-SessionState-get_resume_context]]`() → str` — 
- [[eos_ai-session_state-py-SessionState-clear]]`()` — 
- [[eos_ai-session_state-py-SessionState-update_progress]]`(last_completed, in_progress)` — Load current state, update only last_completed and in_progress, preserve all oth
