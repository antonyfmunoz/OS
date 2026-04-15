---
type: codebase-class
file: eos_ai/workflow_engine.py
line: 773
generated: 2026-04-12
---

# AgentWorkflowEngine

**File:** [[eos_ai-workflow_engine-py]] | **Line:** 773

Dynamic workflow engine — creates and runs agent-task workflows at runtime.
Human steps pause execution. Agent steps run via TaskExecutor.
All state persisted to Neon events table.

Usage:
...

## Methods

- [[eos_ai-workflow_engine-py-AgentWorkflowEngine-__init__]]`(ctx) → None` — 
- [[eos_ai-workflow_engine-py-AgentWorkflowEngine-create_workflow]]`(name, venture_id, trigger, steps) → AgentWorkflow` — 
- [[eos_ai-workflow_engine-py-AgentWorkflowEngine-run]]`(workflow, context) → WorkflowRun` — 
- [[eos_ai-workflow_engine-py-AgentWorkflowEngine-get_workflow_for_trigger]]`(trigger, venture_id) → Optional[dict]` — Return the most recent active workflow matching this trigger.
- [[eos_ai-workflow_engine-py-AgentWorkflowEngine-_save_workflow]]`(workflow) → None` — 
- [[eos_ai-workflow_engine-py-AgentWorkflowEngine-_save_run]]`(run) → None` — 
