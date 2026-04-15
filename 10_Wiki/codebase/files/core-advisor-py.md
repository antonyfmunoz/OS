---
type: codebase-file
path: core/advisor.py
module: core.advisor
lines: 864
size: 28478
generated: 2026-04-12
---

# core/advisor.py

advisor.py — Conditional intelligence layer for the EOS AI OS.

The Advisor Strategy introduces two model roles:

  Executor  — fast/cheap model, default for all operations
...

**Lines:** 864 | **Size:** 28,478 bytes

## Depends On

- [[core-capability-py]]

## Contains

- **class** [[core-advisor-py-AdvisorDecision]] — 0 methods
- **class** [[core-advisor-py-AdvisorResult]] — 2 methods
- **class** [[core-advisor-py-EscalationReason]] — 0 methods
- **class** [[core-advisor-py-EscalationConfig]] — 0 methods
- **class** [[core-advisor-py-_RateLimiter]] — 3 methods
- **fn** [[core-advisor-py-_check_workflow_budget]]`(workflow_id, config) → bool`
- **fn** [[core-advisor-py-_increment_workflow_count]]`(workflow_id) → None`
- **fn** [[core-advisor-py-reset_workflow_count]]`(workflow_id) → None`
- **fn** [[core-advisor-py-needs_advisor]]`(result, context, metadata) → tuple[bool, str]`
- **fn** [[core-advisor-py-call_advisor]]`(task, executor_output, context, metadata) → AdvisorResult`
- **fn** [[core-advisor-py-run_with_advisor]]`(task, context, metadata) → dict[str, Any]`
- **fn** [[core-advisor-py-_build_advisor_prompt]]`(task, executor_output, context, metadata, escalation_reason) → str`
- **fn** [[core-advisor-py-_parse_advisor_response]]`(raw, provider, latency_ms, escalation_reason) → AdvisorResult`
- **fn** [[core-advisor-py-_extract_output_text]]`(result) → str`
- **fn** [[core-advisor-py-_log_advisor_call]]`(task, escalation_reason, result, workflow_id) → None`
- **fn** [[core-advisor-py-advisor_stats]]`(limit) → dict[str, Any]`
- **fn** [[core-advisor-py-recent_advisor_calls]]`(n) → list[dict[str, Any]]`

## Import Statements

```python
from __future__ import annotations
import json
import sys
import threading
import time
import uuid
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
from core.capability import RiskTier
from core.capability import coerce_risk
```
