---
type: codebase-file
path: eos_ai/substrate/workflow_execution.py
module: eos_ai.substrate.workflow_execution
lines: 362
size: 12063
generated: 2026-05-07
---

# eos_ai/substrate/workflow_execution.py

Workflow Execution Layer v1.1 — bounded, deterministic workflow handlers.

Purpose
-------
Executes classified workflow requests through explicit, bounded handlers.
...

**Lines:** 362 | **Size:** 12,063 bytes

## Depends On

- [[eos_ai-substrate-workflow_delegation-py]]

## Contains

- **fn** [[eos_ai-substrate-workflow_execution-py-_handle_builder_dev]]`(text, mode, target, session_name, metadata) → dict[str, Any]`
- **fn** [[eos_ai-substrate-workflow_execution-py-_handle_product_runtime]]`(text, mode, target, session_name, metadata) → dict[str, Any]`
- **fn** [[eos_ai-substrate-workflow_execution-py-_content_ops_prefix]]`(mode) → str`
- **fn** [[eos_ai-substrate-workflow_execution-py-_handle_content_ops]]`(text, mode, target, session_name, metadata) → dict[str, Any]`
- **fn** [[eos_ai-substrate-workflow_execution-py-_analysis_prefix]]`(mode) → str`
- **fn** [[eos_ai-substrate-workflow_execution-py-_handle_analysis]]`(text, mode, target, session_name, metadata) → dict[str, Any]`
- **fn** [[eos_ai-substrate-workflow_execution-py-_handle_system_ops]]`(text, mode, target, session_name, metadata) → dict[str, Any]`
- **fn** [[eos_ai-substrate-workflow_execution-py-_resolve_handler]]`(workflow_kind) → tuple[Callable[..., dict[str, Any]] | None, str]`
- **fn** [[eos_ai-substrate-workflow_execution-py-execute_workflow_if_allowed]]`(text, mode) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
from typing import Any
from typing import Callable
from eos_ai.substrate.workflow_delegation import KIND_ANALYSIS
from eos_ai.substrate.workflow_delegation import KIND_BUILDER_DEV
from eos_ai.substrate.workflow_delegation import KIND_CONTENT_OPS
from eos_ai.substrate.workflow_delegation import KIND_PRODUCT_RUNTIME
from eos_ai.substrate.workflow_delegation import KIND_SYSTEM_OPS
```
