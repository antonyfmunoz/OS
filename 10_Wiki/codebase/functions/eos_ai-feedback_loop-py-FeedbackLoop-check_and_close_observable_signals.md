---
type: codebase-function
file: eos_ai/feedback_loop.py
line: 358
generated: 2026-05-07
---

# FeedbackLoop.check_and_close_observable_signals

**File:** [[eos_ai-feedback_loop-py]] | **Line:** 358
**Signature:** `check_and_close_observable_signals() → int`

**Class:** [[eos_ai-feedback_loop-py-FeedbackLoop]]

Check each pending recommendation against observable DB signals.
Auto-closes when signal is found. Expires after 14 days as inconclusive.
Returns number of recommendations closed.

Observable signals:
...

## Calls

- [[eos_ai-feedback_loop-py-FeedbackLoop-_get_pending_recs]]
