---
type: codebase-file
path: eos_ai/workflow_engine.py
module: eos_ai.workflow_engine
lines: 1013
size: 39463
generated: 2026-05-07
---

# eos_ai/workflow_engine.py

WorkflowEngine — manages multi-step workflow execution and state tracking.

Two layers:

1. Skill-based workflows (WORKFLOWS dict + WorkflowEngine)
...

**Lines:** 1013 | **Size:** 39,463 bytes

## Depends On

- [[eos_ai-context-py]]

## Used By

- [[scripts-force_execution_loop-py]]

## Contains

- **class** [[eos_ai-workflow_engine-py-WorkflowStatus]] — 0 methods
- **class** [[eos_ai-workflow_engine-py-StepOwner]] — 0 methods
- **class** [[eos_ai-workflow_engine-py-AgentWorkflowStep]] — 0 methods
- **class** [[eos_ai-workflow_engine-py-AgentWorkflow]] — 0 methods
- **class** [[eos_ai-workflow_engine-py-WorkflowRun]] — 0 methods
- **class** [[eos_ai-workflow_engine-py-WorkflowStep]] — 0 methods
- **class** [[eos_ai-workflow_engine-py-WorkflowState]] — 2 methods
- **class** [[eos_ai-workflow_engine-py-WorkflowEngine]] — 9 methods
- **class** [[eos_ai-workflow_engine-py-AgentWorkflowEngine]] — 6 methods
- **fn** [[eos_ai-workflow_engine-py-_get_venture]]`(venture_id) → dict`
- **fn** [[eos_ai-workflow_engine-py-dm_to_close_template]]`(venture_id) → tuple[str, list[WorkflowStep]]`
- **fn** [[eos_ai-workflow_engine-py-weekly_rhythm_template]]`(venture_id) → tuple[str, list[WorkflowStep]]`
- **fn** [[eos_ai-workflow_engine-py-b2b_to_retainer_template]]`(venture_id) → tuple[str, list[WorkflowStep]]`
- **fn** [[eos_ai-workflow_engine-py-content_system_template]]`(venture_id) → tuple[str, list[WorkflowStep]]`
- **fn** [[eos_ai-workflow_engine-py-register_venture_workflows]]`(venture_id) → list[str]`
- **fn** [[eos_ai-workflow_engine-py-register_all_venture_workflows]]`() → list[str]`

## Import Statements

```python
from __future__ import annotations
import json
import uuid as _uuid_mod
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from enum import Enum
from pathlib import Path
from typing import Any
from typing import Callable
from typing import Optional
from eos_ai.context import EOSContext
```
