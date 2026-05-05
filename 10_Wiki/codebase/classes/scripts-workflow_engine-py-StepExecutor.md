---
type: codebase-class
file: scripts/workflow_engine.py
line: 414
generated: 2026-04-12
---

# StepExecutor

**File:** [[scripts-workflow_engine-py]] | **Line:** 414

Dispatches a Step to its concrete side-effect, using agent constraints.

Real integration points:
  - RESEARCH → model_router.call_with_fallback (+ optional graph query)
  - WRITE    → model_router.call_with_fallback
...

## Methods

- [[scripts-workflow_engine-py-StepExecutor-__init__]]`(registry) → None` — 
- [[scripts-workflow_engine-py-StepExecutor-_router_call]]`() → Callable[..., Any]` — 
- [[scripts-workflow_engine-py-StepExecutor-_graph_search]]`(term) → list[str]` — 
- [[scripts-workflow_engine-py-StepExecutor-_actions]]`() → Any` — 
- [[scripts-workflow_engine-py-StepExecutor-run]]`(step, context) → dict` — 
- [[scripts-workflow_engine-py-StepExecutor-_should_use_advisor]]`(step) → bool` — Check if this step has any advisor flags set.
- [[scripts-workflow_engine-py-StepExecutor-_apply_advisor]]`(step, task, executor_result, context) → dict[str, Any]` — Run the advisor pipeline on an executor result.
- [[scripts-workflow_engine-py-StepExecutor-_run_research]]`(agent, step, prompt) → dict` — 
- [[scripts-workflow_engine-py-StepExecutor-_run_write]]`(agent, step, prompt) → dict` — 
- [[scripts-workflow_engine-py-StepExecutor-_run_decision]]`(agent, step, prompt) → dict` — 
- [[scripts-workflow_engine-py-StepExecutor-_run_execute]]`(agent, step, context) → dict` — 
- [[scripts-workflow_engine-py-StepExecutor-_expand_prompt]]`(tmpl, context) → str` — Replace {step_id.key} tokens with upstream step outputs.
