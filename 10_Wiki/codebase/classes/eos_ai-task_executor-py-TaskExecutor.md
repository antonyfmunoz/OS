---
type: codebase-class
file: eos_ai/task_executor.py
line: 62
generated: 2026-05-07
---

# TaskExecutor

**File:** [[eos_ai-task_executor-py]] | **Line:** 62

Maps task types to handlers and executes them.
High-risk tasks are blocked for approval rather than executed.

## Methods

- [[eos_ai-task_executor-py-TaskExecutor-__init__]]`(ctx) → None` — 
- [[eos_ai-task_executor-py-TaskExecutor-execute]]`(task) → AgentTask` — 
- [[eos_ai-task_executor-py-TaskExecutor-_handle_research]]`(task) → AgentTask` — 
- [[eos_ai-task_executor-py-TaskExecutor-_handle_draft]]`(task) → AgentTask` — 
- [[eos_ai-task_executor-py-TaskExecutor-_handle_analyze]]`(task) → AgentTask` — 
- [[eos_ai-task_executor-py-TaskExecutor-_handle_pipeline]]`(task) → AgentTask` — 
- [[eos_ai-task_executor-py-TaskExecutor-_handle_brief]]`(task) → AgentTask` — 
- [[eos_ai-task_executor-py-TaskExecutor-_handle_search]]`(task) → AgentTask` — 
- [[eos_ai-task_executor-py-TaskExecutor-_handle_log_lead]]`(task) → AgentTask` — 
- [[eos_ai-task_executor-py-TaskExecutor-_handle_send_dm]]`(task) → AgentTask` — 
- [[eos_ai-task_executor-py-TaskExecutor-_queue_for_approval]]`(task) → None` — 
- [[eos_ai-task_executor-py-TaskExecutor-_save_task]]`(task) → None` — 
