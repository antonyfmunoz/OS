---
type: codebase-function
file: eos_ai/feedback_loop.py
line: 146
generated: 2026-04-12
---

# FeedbackLoop.log_outcome

**File:** [[eos_ai-feedback_loop-py]] | **Line:** 146
**Signature:** `log_outcome(text, venture_id) → bool`

**Class:** [[eos_ai-feedback_loop-py-FeedbackLoop]]

Detect outcome signals in founder's text and update
the most recent pending recommendation.
Keywords first (fast, free), LLM only if ambiguous.

## Calls

- [[eos_ai-feedback_loop-py-FeedbackLoop-_classify_outcome_keywords]]
- [[eos_ai-feedback_loop-py-FeedbackLoop-_classify_outcome_semantic]]
- [[eos_ai-feedback_loop-py-FeedbackLoop-_get_pending_recs]]
- [[eos_ai-feedback_loop-py-FeedbackLoop-_update_recommendation]]
