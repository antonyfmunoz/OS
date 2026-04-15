---
type: codebase-file
path: core/orchestrator/steps.py
module: core.orchestrator.steps
lines: 211
size: 6437
generated: 2026-04-12
---

# core/orchestrator/steps.py

Reusable orchestrator step helpers.

The three Phase-3/4/5 `_cp.py` wrappers (morning_prep, nightly_consolidation,
weekly_review) share a near-identical shape:

...

**Lines:** 211 | **Size:** 6,437 bytes

## Depends On

- [[core-action_system-control_plane-py]]

## Used By

- [[scripts-scheduled-morning_prep_cp-py]]
- [[scripts-scheduled-nightly_consolidation_cp-py]]
- [[scripts-scheduled-weekly_review_cp-py]]

## Contains

- **class** [[core-orchestrator-steps-py-ScriptWorkflowSpec]] — 0 methods
- **fn** [[core-orchestrator-steps-py-run_script_workflow]]`(spec) → int`
- **fn** [[core-orchestrator-steps-py-script_step]]`() → ActionStep`
- **fn** [[core-orchestrator-steps-py-api_step]]`() → ActionStep`

## Import Statements

```python
from __future__ import annotations
import json
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from core.action_system.control_plane import log_decision
from core.action_system.control_plane import run_action
from pipeline import ActionStep
```
