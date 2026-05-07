---
type: codebase-class
file: eos_ai/substrate/task_pipeline.py
line: 78
generated: 2026-05-07
---

# PipelineAgentRole

**File:** [[eos_ai-substrate-task_pipeline-py]] | **Line:** 78

Lightweight routing tag for pipeline steps.

Distinct from substrate.roles.AgentRole which is a rich dataclass
with scopes and handoff targets for live orchestration. This enum
is metadata for deterministic routing within pipelines.

## Inherits From

- `str`
- `Enum`
