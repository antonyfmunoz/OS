---
type: codebase-file
path: eos_ai/substrate/ptt_binding.py
module: eos_ai.substrate.ptt_binding
lines: 382
size: 14718
generated: 2026-05-07
---

# eos_ai/substrate/ptt_binding.py

Workstation push-to-talk (PTT) binding + REAL_READY proof path.

Purpose
-------
This module is a thin, bounded orchestrator on top of the existing STT
...

**Lines:** 382 | **Size:** 14,718 bytes

## Used By

- [[scripts-substrate_ptt_binding_smoke_test-py]]
- [[scripts-substrate_transport_report_smoke_test-py]]

## Contains

- **class** [[eos_ai-substrate-ptt_binding-py-RealCaptureValidation]] — 1 methods
- **class** [[eos_ai-substrate-ptt_binding-py-_ValidationHistory]] — 4 methods
- **fn** [[eos_ai-substrate-ptt_binding-py-_log]]`(msg) → None`
- **fn** [[eos_ai-substrate-ptt_binding-py-_utcnow_iso]]`() → str`
- **fn** [[eos_ai-substrate-ptt_binding-py-_new_id]]`(prefix) → str`
- **fn** [[eos_ai-substrate-ptt_binding-py-get_validation_history]]`() → _ValidationHistory`
- **fn** [[eos_ai-substrate-ptt_binding-py-reset_validation_history_for_tests]]`() → None`
- **fn** [[eos_ai-substrate-ptt_binding-py-_safe_readiness]]`() → dict[str, Any]`
- **fn** [[eos_ai-substrate-ptt_binding-py-_pick_device]]`(readiness, explicit_device) → Optional[int]`
- **fn** [[eos_ai-substrate-ptt_binding-py-validate_real_capture]]`(node_id) → dict[str, Any]`
- **fn** [[eos_ai-substrate-ptt_binding-py-real_capture_report]]`(node_id) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
import sys
import threading
import uuid
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from typing import Any
from typing import Optional
```
