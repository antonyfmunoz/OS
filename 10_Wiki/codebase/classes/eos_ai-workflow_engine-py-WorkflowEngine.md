---
type: codebase-class
file: eos_ai/workflow_engine.py
line: 617
generated: 2026-05-07
---

# WorkflowEngine

**File:** [[eos_ai-workflow_engine-py]] | **Line:** 617

Manages workflow execution, state persistence, and step routing.

Usage:
    we = WorkflowEngine(ctx)
    state = we.start_workflow('lead_qualification', inputs={'lead_path': '...'})
...

## Methods

- [[eos_ai-workflow_engine-py-WorkflowEngine-__init__]]`(ctx) → None` — 
- [[eos_ai-workflow_engine-py-WorkflowEngine-start_workflow]]`(workflow_name, inputs) → WorkflowState` — Initialize and persist a new workflow execution state.
- [[eos_ai-workflow_engine-py-WorkflowEngine-get_current_step]]`(state) → WorkflowStep | None` — Return the current step definition, or None if workflow is complete.
- [[eos_ai-workflow_engine-py-WorkflowEngine-advance]]`(state, outputs, success) → WorkflowStep | None` — Record step completion and advance to next step.
- [[eos_ai-workflow_engine-py-WorkflowEngine-get_step_prompt]]`(state) → str` — Return a prompt string for the current step, including available outputs.
- [[eos_ai-workflow_engine-py-WorkflowEngine-list_workflows]]`() → list[str]` — Return all available workflow names.
- [[eos_ai-workflow_engine-py-WorkflowEngine-get_workflow_steps]]`(workflow_name) → list[WorkflowStep]` — Return all steps for a given workflow.
- [[eos_ai-workflow_engine-py-WorkflowEngine-_save_state]]`(state) → None` — Persist workflow state to disk.
- [[eos_ai-workflow_engine-py-WorkflowEngine-load_state]]`(workflow_id) → WorkflowState | None` — Load a workflow state from disk by ID.
