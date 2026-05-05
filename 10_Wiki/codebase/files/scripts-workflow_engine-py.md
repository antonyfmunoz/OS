---
type: codebase-file
path: scripts/workflow_engine.py
module: scripts.workflow_engine
lines: 1177
size: 46115
tags: [entry-point]
generated: 2026-04-12
---

# scripts/workflow_engine.py

> **ENTRY POINT** — Contains `if __name__` or server start.

WorkflowEngine — goal-driven, graph-aware, agent-executed workflows.

Built on top of the existing EOS cognition + execution stack. This engine does
NOT replace:
  - eos_ai/workflow_engine.py (skill-sequence + AgentWorkflow/Run model)
...

**Lines:** 1177 | **Size:** 46,115 bytes

## Depends On

- [[core-environment-py]]

## Used By

- [[scripts-orchestrator-py]]
- [[scripts-sandbox_safety_verifier-py]]
- [[scripts-sandbox_smoke_test-py]]

## Contains

- **class** [[scripts-workflow_engine-py-StepType]] — 0 methods
- **class** [[scripts-workflow_engine-py-StepStatus]] — 0 methods
- **class** [[scripts-workflow_engine-py-WorkflowStatus]] — 0 methods
- **class** [[scripts-workflow_engine-py-Step]] — 1 methods
- **class** [[scripts-workflow_engine-py-Workflow]] — 2 methods
- **class** [[scripts-workflow_engine-py-Agent]] — 1 methods
- **class** [[scripts-workflow_engine-py-AgentRegistry]] — 5 methods
- **class** [[scripts-workflow_engine-py-Verifier]] — 3 methods
- **class** [[scripts-workflow_engine-py-StepExecutor]] — 12 methods
- **class** [[scripts-workflow_engine-py-WorkflowEngine]] — 8 methods
- **fn** [[scripts-workflow_engine-py-topological_order]]`(steps) → list[str]`
- **fn** [[scripts-workflow_engine-py-_routing_output]]`(result) → str`
- **fn** [[scripts-workflow_engine-py-_routing_provider]]`(result) → str`
- **fn** [[scripts-workflow_engine-py-_new_id]]`(prefix) → str`
- **fn** [[scripts-workflow_engine-py-build_research_workflow]]`(goal) → Workflow`
- **fn** [[scripts-workflow_engine-py-build_content_workflow]]`(goal) → Workflow`
- **fn** [[scripts-workflow_engine-py-build_refactor_workflow]]`(goal, target_file) → Workflow`
- **fn** [[scripts-workflow_engine-py-main]]`(argv) → int`

## Import Statements

```python
from __future__ import annotations
import argparse
import json
import sys
import time
import traceback
import uuid
from collections import defaultdict
from collections import deque
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from enum import Enum
from pathlib import Path
from typing import Any
from typing import Callable
from core.environment import Environment
```
