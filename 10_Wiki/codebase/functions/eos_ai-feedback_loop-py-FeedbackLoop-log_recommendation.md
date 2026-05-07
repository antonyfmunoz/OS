---
type: codebase-function
file: eos_ai/feedback_loop.py
line: 48
generated: 2026-05-07
---

# FeedbackLoop.log_recommendation

**File:** [[eos_ai-feedback_loop-py]] | **Line:** 48
**Signature:** `log_recommendation(content, venture_id, context) → str`

**Class:** [[eos_ai-feedback_loop-py-FeedbackLoop]]

Log actionable DEX recommendation to Neon.
Filters out agent data dumps, stage checks, and research outputs.
Returns recommendation ID, or '' if filtered out.

## Calls

- [[eos_ai-feedback_loop-py-FeedbackLoop-_is_actionable_advice]]
