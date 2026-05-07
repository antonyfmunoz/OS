---
type: codebase-function
file: core/dynamics.py
line: 60
generated: 2026-05-07
---

# FeedbackDynamics.project_score

**File:** [[core-dynamics-py]] | **Line:** 60
**Signature:** `project_score(immediate_score, elapsed_steps, historical_trajectory) → DelayedScore`

**Class:** [[core-dynamics-py-FeedbackDynamics]]

Project what the score will be once feedback fully matures.

Args:
    immediate_score:       Score measured right now.
    elapsed_steps:         How many steps since the run executed.
...

## Calls

- [[core-dynamics-py-FeedbackDynamics-_compute_confidence]]
- [[core-dynamics-py-FeedbackDynamics-_compute_trend]]
