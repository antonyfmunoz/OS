---
type: codebase-file
path: eos_ai/substrate/local_gui_control_contracts.py
module: eos_ai.substrate.local_gui_control_contracts
lines: 246
size: 7762
generated: 2026-05-07
---

# eos_ai/substrate/local_gui_control_contracts.py

Local GUI control contracts for Phase 95.0.

Defines the abstraction layer for computer-use-only operations:
observation methods, action types, and policies for interacting
with visible desktop UI elements.
...

**Lines:** 246 | **Size:** 7,762 bytes

## Used By

- [[eos_ai-substrate-drive_ui_inventory_comparator-py]]
- [[eos_ai-substrate-visible_drive_ui_inventory-py]]

## Contains

- **class** [[eos_ai-substrate-local_gui_control_contracts-py-GUIObservationMethod]] — 0 methods
- **class** [[eos_ai-substrate-local_gui_control_contracts-py-GUIActionType]] — 0 methods
- **class** [[eos_ai-substrate-local_gui_control_contracts-py-GUIControlStatus]] — 0 methods
- **class** [[eos_ai-substrate-local_gui_control_contracts-py-GUIObservationPolicy]] — 2 methods
- **class** [[eos_ai-substrate-local_gui_control_contracts-py-GUIAction]] — 1 methods
- **class** [[eos_ai-substrate-local_gui_control_contracts-py-GUIObservationResult]] — 1 methods
- **class** [[eos_ai-substrate-local_gui_control_contracts-py-GUIInventoryItem]] — 1 methods
- **fn** [[eos_ai-substrate-local_gui_control_contracts-py-_now_iso]]`() → str`
- **fn** [[eos_ai-substrate-local_gui_control_contracts-py-is_observation_target_blocked]]`(target) → bool`
- **fn** [[eos_ai-substrate-local_gui_control_contracts-py-is_observation_target_allowed]]`(target) → bool`
- **fn** [[eos_ai-substrate-local_gui_control_contracts-py-classify_gui_control_availability]]`(has_ui_automation, has_accessibility, has_screen_capture, has_ocr) → tuple[GUIControlStatus, GUIObservationMethod | None]`
- **fn** [[eos_ai-substrate-local_gui_control_contracts-py-build_gui_backend_missing_report]]`(checked_methods) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from enum import Enum
from typing import Any
```
