---
type: codebase-file
path: eos_ai/substrate/interactive_gui_worker_contracts.py
module: eos_ai.substrate.interactive_gui_worker_contracts
lines: 196
size: 7406
generated: 2026-05-07
---

# eos_ai/substrate/interactive_gui_worker_contracts.py

Interactive GUI worker contracts for Phase 94D.7S.

Defines the contract between VPS advisor and the local interactive GUI worker
that runs in the founder's active Windows desktop session.

...

**Lines:** 196 | **Size:** 7,406 bytes

## Depends On

- [[eos_ai-substrate-visible_gui_success_criteria-py]]

## Contains

- **fn** [[eos_ai-substrate-interactive_gui_worker_contracts-py-build_interactive_chrome_launch_command]]`(url, chrome_path) → str`
- **fn** [[eos_ai-substrate-interactive_gui_worker_contracts-py-build_interactive_launch_intent]]`(work_order_id, target_account) → dict[str, Any]`
- **fn** [[eos_ai-substrate-interactive_gui_worker_contracts-py-build_action_attempted_outbox]]`(work_order_id, command_exit_code, launch_context, chrome_path) → dict[str, Any]`
- **fn** [[eos_ai-substrate-interactive_gui_worker_contracts-py-build_visible_confirmed_outbox]]`(work_order_id, confirmation) → dict[str, Any]`
- **fn** [[eos_ai-substrate-interactive_gui_worker_contracts-py-get_recommended_mvp_path]]`() → dict[str, Any]`
- **fn** [[eos_ai-substrate-interactive_gui_worker_contracts-py-classify_current_ssh_path]]`() → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
from typing import Any
from eos_ai.substrate.visible_gui_success_criteria import LaunchContext
from eos_ai.substrate.visible_gui_success_criteria import VisibleGuiStatus
```
