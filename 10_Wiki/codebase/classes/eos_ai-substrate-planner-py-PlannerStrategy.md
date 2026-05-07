---
type: codebase-class
file: eos_ai/substrate/planner.py
line: 227
generated: 2026-05-07
---

# PlannerStrategy

**File:** [[eos_ai-substrate-planner-py]] | **Line:** 227

DecisionStrategy implementation that drives intents through plans.

Evaluation flow:
1. Read active intents from state (sorted by priority).
2. For the highest-priority active intent, derive its plan.
...

## Methods

- [[eos_ai-substrate-planner-py-PlannerStrategy-name]]`() → str` — 
- [[eos_ai-substrate-planner-py-PlannerStrategy-evaluate]]`(state) → DecisionOutput | None` — Evaluate active intents and return next planned action.
- [[eos_ai-substrate-planner-py-PlannerStrategy-_build_step_output]]`(intent, plan, step, state_hash) → DecisionOutput` — Build DecisionOutput for emitting a plan step.
- [[eos_ai-substrate-planner-py-PlannerStrategy-_build_completion_output]]`(intent, plan, state_hash) → DecisionOutput` — Build DecisionOutput to mark an intent as completed.
