---
type: codebase-function
file: eos_ai/primitives.py
line: 882
generated: 2026-04-11
---

# ContextualReasoningEngine.evaluate_principle

**File:** [[eos_ai-primitives-py]] | **Line:** 882
**Signature:** `evaluate_principle(advice, context) → dict`

**Class:** [[eos_ai-primitives-py-ContextualReasoningEngine]]

Evaluate whether a piece of advice applies at the current stage.

Pre-checks PRIMITIVE_LIBRARY for a structural match before
falling through to keyword-based not_yet matching.

...
