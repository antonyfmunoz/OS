---
type: codebase-file
path: core/environment_bridge/bootstrap_plan.py
module: core.environment_bridge.bootstrap_plan
lines: 231
size: 8383
generated: 2026-05-07
---

# core/environment_bridge/bootstrap_plan.py

Bootstrap plan for the Environment Bridge.

Generates step-by-step bootstrap plans for one-time local worker
setup. After initial bootstrap, the worker runs autonomously.

...

**Lines:** 231 | **Size:** 8,383 bytes

## Contains

- **class** [[core-environment_bridge-bootstrap_plan-py-BootstrapStepStatus]] — 0 methods
- **class** [[core-environment_bridge-bootstrap_plan-py-BootstrapStep]] — 1 methods
- **class** [[core-environment_bridge-bootstrap_plan-py-BootstrapPlan]] — 1 methods
- **fn** [[core-environment_bridge-bootstrap_plan-py-build_local_worker_bootstrap_plan]]`() → BootstrapPlan`
- **fn** [[core-environment_bridge-bootstrap_plan-py-build_windows_task_scheduler_bootstrap_plan]]`() → BootstrapPlan`
- **fn** [[core-environment_bridge-bootstrap_plan-py-build_tmux_local_worker_bootstrap_plan]]`() → BootstrapPlan`
- **fn** [[core-environment_bridge-bootstrap_plan-py-bootstrap_plan_requires_manual_once]]`(plan) → bool`
- **fn** [[core-environment_bridge-bootstrap_plan-py-summarize_bootstrap_plan]]`(plan) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any
```
