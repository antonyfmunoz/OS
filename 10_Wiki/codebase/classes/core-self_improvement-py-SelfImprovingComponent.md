---
type: codebase-class
file: core/self_improvement.py
line: 42
generated: 2026-05-07
---

# SelfImprovingComponent

**File:** [[core-self_improvement-py]] | **Line:** 42

Protocol that every improvable subsystem must implement.

The four methods form a closed loop:
    metrics → evaluate → propose → apply → metrics (improved)

## Inherits From

- `ABC`

## Inherited By

- [[core-self_improvement-py-CompositionImprover]]
- [[core-self_improvement-py-PipelineImprover]]
- [[core-self_improvement-py-RouterImprover]]

## Methods

- [[core-self_improvement-py-SelfImprovingComponent-metrics]]`() → dict[str, Any]` — Return current performance metrics.
- [[core-self_improvement-py-SelfImprovingComponent-evaluate]]`() → dict[str, Any]` — Diagnose current state — what's working, what isn't.
- [[core-self_improvement-py-SelfImprovingComponent-propose_improvements]]`() → list[TransformationResult]` — Return ranked list of improvement proposals.
- [[core-self_improvement-py-SelfImprovingComponent-apply_improvements]]`(proposals) → dict[str, Any]` — Apply the top proposal(s). Returns summary of changes.
