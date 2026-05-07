---
type: codebase-file
path: scripts/substrate_session_orchestration_smoke_test.py
module: scripts.substrate_session_orchestration_smoke_test
lines: 369
size: 11241
tags: [entry-point]
generated: 2026-05-07
---

# scripts/substrate_session_orchestration_smoke_test.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Session Orchestration Smoke Tests.

**Lines:** 369 | **Size:** 11,241 bytes

## Depends On

- [[eos_ai-substrate-session_orchestration-py]]

## Contains

- **fn** [[scripts-substrate_session_orchestration_smoke_test-py-check]]`(name, cond, detail) → None`
- **fn** [[scripts-substrate_session_orchestration_smoke_test-py-test_registry]]`() → int`
- **fn** [[scripts-substrate_session_orchestration_smoke_test-py-test_health]]`() → int`
- **fn** [[scripts-substrate_session_orchestration_smoke_test-py-test_recovery]]`() → int`
- **fn** [[scripts-substrate_session_orchestration_smoke_test-py-test_reconciliation]]`() → int`
- **fn** [[scripts-substrate_session_orchestration_smoke_test-py-test_architecture]]`() → int`
- **fn** [[scripts-substrate_session_orchestration_smoke_test-py-test_integration_guard]]`() → int`

## Import Statements

```python
from __future__ import annotations
import ast
import sys
from eos_ai.substrate.session_orchestration import LAYER_NAME
from eos_ai.substrate.session_orchestration import LAYER_VERSION
from eos_ai.substrate.session_orchestration import ExpectedSession
from eos_ai.substrate.session_orchestration import SessionHealth
from eos_ai.substrate.session_orchestration import actual_sessions
from eos_ai.substrate.session_orchestration import ensure_expected_sessions
from eos_ai.substrate.session_orchestration import expected_sessions
from eos_ai.substrate.session_orchestration import reconcile_sessions
from eos_ai.substrate.session_orchestration import recover_session
from eos_ai.substrate.session_orchestration import session_health
from eos_ai.substrate.session_orchestration import session_readiness_report
```
