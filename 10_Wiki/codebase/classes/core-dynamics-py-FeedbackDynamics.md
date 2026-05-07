---
type: codebase-class
file: core/dynamics.py
line: 43
generated: 2026-05-07
---

# FeedbackDynamics

**File:** [[core-dynamics-py]] | **Line:** 43

Models how feedback evolves over time.

Args:
    lag_steps:          How many evaluation cycles before full impact is visible.
    decay_rate:         How fast signal strength decays per step (0.0 = no decay).
...

## Methods

- [[core-dynamics-py-FeedbackDynamics-project_score]]`(immediate_score, elapsed_steps, historical_trajectory) → DelayedScore` — Project what the score will be once feedback fully matures.
- [[core-dynamics-py-FeedbackDynamics-should_wait]]`(elapsed_steps) → bool` — True if the run hasn't matured yet and shouldn't be judged.
- [[core-dynamics-py-FeedbackDynamics-apply_compounding]]`(base_score, steps) → float` — Apply compounding effect over N steps.
- [[core-dynamics-py-FeedbackDynamics-apply_decay]]`(score, steps) → float` — Apply decay over N steps.
- [[core-dynamics-py-FeedbackDynamics-apply_saturation]]`(score) → float` — Apply diminishing returns above saturation threshold.
- [[core-dynamics-py-FeedbackDynamics-_compute_trend]]`(trajectory) → float` — Simple linear trend from trajectory (slope of last N points).
- [[core-dynamics-py-FeedbackDynamics-_compute_confidence]]`(elapsed, trajectory_len, matured) → float` — Confidence in the projected score.
- [[core-dynamics-py-FeedbackDynamics-to_dict]]`() → dict[str, Any]` — 

## Decorators

- `@dataclass`
