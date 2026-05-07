---
type: codebase-class
file: core/self_improvement.py
line: 132
generated: 2026-05-07
---

# CompositionImprover

**File:** [[core-self_improvement-py]] | **Line:** 132

Self-improvement interface for the Composition Engine.

Analyses composition patterns across historical pipeline results
to identify which domain types produce the best primitive coverage
and which consistently miss important primitives.

## Inherits From

- [[core-self_improvement-py-SelfImprovingComponent]]

## Methods

- [[core-self_improvement-py-CompositionImprover-__init__]]`() → None` — 
- [[core-self_improvement-py-CompositionImprover-metrics]]`() → dict[str, Any]` — Composition metrics: coverage by domain type, common gaps.
- [[core-self_improvement-py-CompositionImprover-evaluate]]`() → dict[str, Any]` — Identify domain types with low coverage or missing critical primitives.
- [[core-self_improvement-py-CompositionImprover-propose_improvements]]`() → list[TransformationResult]` — Propose transformations for each domain type that has gaps.
- [[core-self_improvement-py-CompositionImprover-apply_improvements]]`(proposals) → dict[str, Any]` — Log proposed improvements.
