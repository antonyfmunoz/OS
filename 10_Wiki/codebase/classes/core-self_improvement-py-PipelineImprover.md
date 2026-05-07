---
type: codebase-class
file: core/self_improvement.py
line: 263
generated: 2026-05-07
---

# PipelineImprover

**File:** [[core-self_improvement-py]] | **Line:** 263

Self-improvement interface for the Execution Pipeline.

Analyses pipeline execution logs to identify failure patterns,
slow steps, and primitive-level bottlenecks.

## Inherits From

- [[core-self_improvement-py-SelfImprovingComponent]]

## Methods

- [[core-self_improvement-py-PipelineImprover-__init__]]`() → None` — 
- [[core-self_improvement-py-PipelineImprover-metrics]]`() → dict[str, Any]` — Pipeline metrics from action log.
- [[core-self_improvement-py-PipelineImprover-evaluate]]`() → dict[str, Any]` — Diagnose pipeline health.
- [[core-self_improvement-py-PipelineImprover-propose_improvements]]`() → list[TransformationResult]` — Propose primitive-level improvements based on pipeline failures.
- [[core-self_improvement-py-PipelineImprover-apply_improvements]]`(proposals) → dict[str, Any]` — Log pipeline improvement proposals.
