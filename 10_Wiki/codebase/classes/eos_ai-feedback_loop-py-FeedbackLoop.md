---
type: codebase-class
file: eos_ai/feedback_loop.py
line: 44
generated: 2026-04-11
---

# FeedbackLoop

**File:** [[eos_ai-feedback_loop-py]] | **Line:** 44

*No docstring.*

## Methods

- [[eos_ai-feedback_loop-py-FeedbackLoop-__init__]]`(ctx)` — 
- [[eos_ai-feedback_loop-py-FeedbackLoop-log_recommendation]]`(content, venture_id, context) → str` — Log actionable DEX recommendation to Neon.
- [[eos_ai-feedback_loop-py-FeedbackLoop-_is_actionable_advice]]`(content, context) → bool` — Returns True only if this is specific actionable advice to the founder.
- [[eos_ai-feedback_loop-py-FeedbackLoop-log_outcome]]`(text, venture_id) → bool` — Detect outcome signals in founder's text and update
- [[eos_ai-feedback_loop-py-FeedbackLoop-_classify_outcome_semantic]]`(text) → str` — LLM classifier for outcome detection.
- [[eos_ai-feedback_loop-py-FeedbackLoop-_classify_outcome_keywords]]`(text) → str` — Keyword fallback for outcome classification.
- [[eos_ai-feedback_loop-py-FeedbackLoop-_get_pending_recs]]`() → list[dict]` — Get pending recommendations from Neon.
- [[eos_ai-feedback_loop-py-FeedbackLoop-_update_recommendation]]`(event_id, outcome, note) → bool` — Update a recommendation's outcome in Neon.
- [[eos_ai-feedback_loop-py-FeedbackLoop-get_recommendation_stats]]`() → dict` — Return outcome distribution across all logged recommendations.
- [[eos_ai-feedback_loop-py-FeedbackLoop-check_and_close_observable_signals]]`() → int` — Check each pending recommendation against observable DB signals.
