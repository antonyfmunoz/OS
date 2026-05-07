---
type: codebase-file
path: eos_ai/substrate/gui_backend_healthcheck.py
module: eos_ai.substrate.gui_backend_healthcheck
lines: 247
size: 9026
generated: 2026-05-07
---

# eos_ai/substrate/gui_backend_healthcheck.py

GUI computer-use backend healthcheck for Phase 94D.5.

Generates safe healthcheck commands and parses reported capability.
Does NOT execute any commands, move mouse, click, type, or open browser.

...

**Lines:** 247 | **Size:** 9,026 bytes

## Contains

- **class** [[eos_ai-substrate-gui_backend_healthcheck-py-BackendStatus]] — 0 methods
- **class** [[eos_ai-substrate-gui_backend_healthcheck-py-BackendCandidate]] — 0 methods
- **class** [[eos_ai-substrate-gui_backend_healthcheck-py-BackendCheck]] — 1 methods
- **class** [[eos_ai-substrate-gui_backend_healthcheck-py-GUIHealthcheckReport]] — 2 methods
- **fn** [[eos_ai-substrate-gui_backend_healthcheck-py-_now_iso]]`() → str`
- **fn** [[eos_ai-substrate-gui_backend_healthcheck-py-generate_healthcheck_commands]]`() → list[BackendCheck]`
- **fn** [[eos_ai-substrate-gui_backend_healthcheck-py-build_healthcheck_report_from_results]]`(results, node_id) → GUIHealthcheckReport`
- **fn** [[eos_ai-substrate-gui_backend_healthcheck-py-build_gui_missing_approval_request]]`(work_order_id, report) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
import json
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from enum import Enum
from typing import Any
```
