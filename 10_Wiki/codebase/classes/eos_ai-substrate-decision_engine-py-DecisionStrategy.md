---
type: codebase-class
file: eos_ai/substrate/decision_engine.py
line: 101
generated: 2026-05-07
---

# DecisionStrategy

**File:** [[eos_ai-substrate-decision_engine-py]] | **Line:** 101

Interface for pluggable decision strategies.

Strategies are pure functions from state → optional DecisionOutput.
Returning None means "no action to take."

## Inherits From

- `Protocol`

## Methods

- [[eos_ai-substrate-decision_engine-py-DecisionStrategy-name]]`() → str` — Strategy identifier for logging and tracing.
- [[eos_ai-substrate-decision_engine-py-DecisionStrategy-evaluate]]`(state) → DecisionOutput | None` — Evaluate the current state and return a decision, or None.
