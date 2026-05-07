---
type: codebase-class
file: core/self_improvement.py
line: 387
generated: 2026-05-07
---

# RouterImprover

**File:** [[core-self_improvement-py]] | **Line:** 387

Self-improvement interface for intent routing.

Analyses how well the intent → domain resolution performs by
checking for misrouted intents (based on execution feedback).

## Inherits From

- [[core-self_improvement-py-SelfImprovingComponent]]

## Methods

- [[core-self_improvement-py-RouterImprover-__init__]]`() → None` — 
- [[core-self_improvement-py-RouterImprover-metrics]]`() → dict[str, Any]` — Router metrics from improvement history.
- [[core-self_improvement-py-RouterImprover-evaluate]]`() → dict[str, Any]` — Evaluate router health — requires feedback data to be meaningful.
- [[core-self_improvement-py-RouterImprover-propose_improvements]]`() → list[TransformationResult]` — No automatic proposals for router — requires human judgment.
- [[core-self_improvement-py-RouterImprover-apply_improvements]]`(proposals) → dict[str, Any]` — Router improvements require code changes — always advisory.
