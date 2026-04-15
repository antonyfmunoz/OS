---
type: codebase-class
file: eos_ai/primitives.py
line: 838
generated: 2026-04-12
---

# ContextualReasoningEngine

**File:** [[eos_ai-primitives-py]] | **Line:** 838

Evaluates whether advice in a generated response is appropriate for the
current business stage. Used by CognitiveLoop GENERATE filter (step 5b).

Premature advice is flagged with a stage-appropriate correction prepended
to the response — the system corrects itself before the founder sees it.

## Methods

- [[eos_ai-primitives-py-ContextualReasoningEngine-__init__]]`(ctx)` — 
- [[eos_ai-primitives-py-ContextualReasoningEngine-get_current_context]]`(venture_id) → dict` — 
- [[eos_ai-primitives-py-ContextualReasoningEngine-evaluate_principle]]`(advice, context) → dict` — Evaluate whether a piece of advice applies at the current stage.
