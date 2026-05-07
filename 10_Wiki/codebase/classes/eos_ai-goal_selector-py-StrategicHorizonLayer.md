---
type: codebase-class
file: eos_ai/goal_selector.py
line: 401
generated: 2026-05-07
---

# StrategicHorizonLayer

**File:** [[eos_ai-goal_selector-py]] | **Line:** 401

Multi-timescale scoring: evaluates goals across short/medium/long horizons.

Replaces single-decay performance adjustment with a weighted blend of
three decay windows. Adds a stability bonus for goals that perform
consistently across all horizons, making them harder to displace.

## Methods

- [[eos_ai-goal_selector-py-StrategicHorizonLayer-__init__]]`(horizon_weights, stability_threshold, stability_max, performance_weight)` — 
- [[eos_ai-goal_selector-py-StrategicHorizonLayer-compute_horizon_adjustment]]`(goal) → float` — Compute multi-horizon performance adjustment for a single goal.
- [[eos_ai-goal_selector-py-StrategicHorizonLayer-_compute_stability_bonus]]`(composites) → float` — Bonus for consistent cross-horizon performance.
- [[eos_ai-goal_selector-py-StrategicHorizonLayer-build_explanation]]`(goal) → list[str]` — Generate explanation entries for multi-horizon scoring.
- [[eos_ai-goal_selector-py-StrategicHorizonLayer-explain_goal]]`(goal) → dict` — Structured explainability for horizon layer.
