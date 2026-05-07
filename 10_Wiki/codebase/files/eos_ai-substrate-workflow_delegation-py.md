---
type: codebase-file
path: eos_ai/substrate/workflow_delegation.py
module: eos_ai.substrate.workflow_delegation
lines: 474
size: 16700
generated: 2026-05-07
---

# eos_ai/substrate/workflow_delegation.py

Workflow Delegation Layer v1 — deterministic intent classification + policy.

Purpose
-------
Classifies incoming requests into bounded intent classes (conversation,
...

**Lines:** 474 | **Size:** 16,700 bytes

## Used By

- [[eos_ai-substrate-workflow_execution-py]]

## Contains

- **fn** [[eos_ai-substrate-workflow_delegation-py-classify_workflow_intent]]`(text, mode, metadata) → dict[str, Any]`
- **fn** [[eos_ai-substrate-workflow_delegation-py-_result]]`(intent, workflow_kind, reason, confidence) → dict[str, Any]`
- **fn** [[eos_ai-substrate-workflow_delegation-py-_check_extra_keywords]]`(text, mode) → Optional[dict[str, Any]]`
- **fn** [[eos_ai-substrate-workflow_delegation-py-resolve_workflow_policy]]`(mode, intent_result) → dict[str, Any]`
- **fn** [[eos_ai-substrate-workflow_delegation-py-_policy_result]]`() → dict[str, Any]`
- **fn** [[eos_ai-substrate-workflow_delegation-py-enrich_metadata]]`(meta, text, mode) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
import os
import re
from typing import Any
from typing import Optional
```
