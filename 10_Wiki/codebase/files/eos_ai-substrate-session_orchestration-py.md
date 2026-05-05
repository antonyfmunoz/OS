---
type: codebase-file
path: eos_ai/substrate/session_orchestration.py
module: eos_ai.substrate.session_orchestration
lines: 418
size: 13214
tags: [entry-point]
generated: 2026-04-12
---

# eos_ai/substrate/session_orchestration.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Session Orchestration Layer v1 — registry, health, recovery, reporting.

Bounded orchestration that knows which sessions should exist, whether they
are healthy, and how to explicitly recover them. No background processes, no autonomous
supervision, no hot-path imports.

**Lines:** 418 | **Size:** 13,214 bytes

## Used By

- [[scripts-substrate_session_orchestration_smoke_test-py]]

## Contains

- **class** [[eos_ai-substrate-session_orchestration-py-ExpectedSession]] — 0 methods
- **class** [[eos_ai-substrate-session_orchestration-py-SessionHealth]] — 0 methods
- **fn** [[eos_ai-substrate-session_orchestration-py-_now_iso]]`() → str`
- **fn** [[eos_ai-substrate-session_orchestration-py-_log]]`(msg) → None`
- **fn** [[eos_ai-substrate-session_orchestration-py-expected_sessions]]`() → list[ExpectedSession]`
- **fn** [[eos_ai-substrate-session_orchestration-py-actual_sessions]]`(target) → list[dict[str, Any]]`
- **fn** [[eos_ai-substrate-session_orchestration-py-session_health]]`(target, session_name) → dict[str, Any]`
- **fn** [[eos_ai-substrate-session_orchestration-py-session_readiness_report]]`() → dict[str, Any]`
- **fn** [[eos_ai-substrate-session_orchestration-py-ensure_expected_sessions]]`() → dict[str, Any]`
- **fn** [[eos_ai-substrate-session_orchestration-py-recover_session]]`(target, session_name) → dict[str, Any]`
- **fn** [[eos_ai-substrate-session_orchestration-py-reconcile_sessions]]`() → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
import datetime
import os
import sys
from dataclasses import asdict
from dataclasses import dataclass
from enum import Enum
from typing import Any
```
