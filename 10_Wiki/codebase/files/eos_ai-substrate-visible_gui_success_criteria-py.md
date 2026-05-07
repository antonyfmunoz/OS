---
type: codebase-file
path: eos_ai/substrate/visible_gui_success_criteria.py
module: eos_ai.substrate.visible_gui_success_criteria
lines: 200
size: 6686
generated: 2026-05-07
---

# eos_ai/substrate/visible_gui_success_criteria.py

Visible GUI success criteria for Phase 94D.7S.

Defines what constitutes a successful visible GUI action.
Command exit code 0 alone is NOT sufficient for visible GUI success.

...

**Lines:** 200 | **Size:** 6,686 bytes

## Used By

- [[eos_ai-substrate-interactive_gui_worker_contracts-py]]
- [[eos_ai-substrate-interactive_shell_executor-py]]

## Contains

- **class** [[eos_ai-substrate-visible_gui_success_criteria-py-VisibleGuiStatus]] — 0 methods
- **class** [[eos_ai-substrate-visible_gui_success_criteria-py-LaunchContext]] — 0 methods
- **fn** [[eos_ai-substrate-visible_gui_success_criteria-py-is_context_reliable_for_gui]]`(context) → bool`
- **fn** [[eos_ai-substrate-visible_gui_success_criteria-py-classify_ssh_launch_context]]`() → str`
- **fn** [[eos_ai-substrate-visible_gui_success_criteria-py-is_exit_code_sufficient_for_visible_success]]`() → bool`
- **fn** [[eos_ai-substrate-visible_gui_success_criteria-py-build_action_attempted_status]]`(action, backend, command_exit_code, launch_context, chrome_path) → dict[str, Any]`
- **fn** [[eos_ai-substrate-visible_gui_success_criteria-py-build_waiting_for_confirmation_message]]`(work_order_id, action, target_account) → dict[str, Any]`
- **fn** [[eos_ai-substrate-visible_gui_success_criteria-py-evaluate_founder_confirmation]]`(confirmation) → dict[str, Any]`
- **fn** [[eos_ai-substrate-visible_gui_success_criteria-py-demote_ssh_launch_to_attempted]]`(previous_result) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
from typing import Any
```
