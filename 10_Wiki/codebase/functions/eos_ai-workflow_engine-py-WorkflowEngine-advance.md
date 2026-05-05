---
type: codebase-function
file: eos_ai/workflow_engine.py
line: 668
generated: 2026-04-12
---

# WorkflowEngine.advance

**File:** [[eos_ai-workflow_engine-py]] | **Line:** 668
**Signature:** `advance(state, outputs, success) → WorkflowStep | None`

**Class:** [[eos_ai-workflow_engine-py-WorkflowEngine]]

Record step completion and advance to next step.

Args:
    state:   Current workflow state (mutated in place).
    outputs: Outputs produced by the completed step.
...

## Calls

- [[eos_ai-workflow_engine-py-WorkflowEngine-_save_state]]
