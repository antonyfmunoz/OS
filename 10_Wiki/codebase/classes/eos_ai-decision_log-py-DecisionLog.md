---
type: codebase-class
file: eos_ai/decision_log.py
line: 57
generated: 2026-04-12
---

# DecisionLog

**File:** [[eos_ai-decision_log-py]] | **Line:** 57

*No docstring.*

## Methods

- [[eos_ai-decision_log-py-DecisionLog-__init__]]`(ctx)` — 
- [[eos_ai-decision_log-py-DecisionLog-detect_decision]]`(text, venture_id) → bool` — Return True if the text contains decision language.
- [[eos_ai-decision_log-py-DecisionLog-log_decision]]`(description, rationale, venture_id, decided_by, impact, tags) → str` — Persist a decision to Neon. Returns short decision_id.
- [[eos_ai-decision_log-py-DecisionLog-log_from_message]]`(text, venture_id) → str | None` — Auto-extract and log a decision from a founder message.
- [[eos_ai-decision_log-py-DecisionLog-get_recent_decisions]]`(venture_id, limit) → list[dict]` — Retrieve recent decisions from Neon, optionally filtered by venture.
- [[eos_ai-decision_log-py-DecisionLog-format_for_context]]`(decisions) → str` — Format recent decisions for injection into cognitive loop.
