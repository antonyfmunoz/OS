---
type: codebase-class
file: eos_ai/substrate/task_system.py
line: 101
generated: 2026-05-07
---

# Task

**File:** [[eos_ai-substrate-task_system-py]] | **Line:** 101

A unit of work tracked by the task system.

## Methods

- [[eos_ai-substrate-task_system-py-Task-new]]`(title) → 'Task'` — Create a new Task with generated ID and current timestamps.
- [[eos_ai-substrate-task_system-py-Task-to_dict]]`() → dict` — Return a JSON-safe dict. Enums serialized as their .value.
- [[eos_ai-substrate-task_system-py-Task-from_dict]]`(d) → 'Task'` — Deserialize from a dict, reconstructing enums with safe defaults.

## Decorators

- `@dataclass`
