---
type: codebase-file
path: eos_ai/substrate/interactive_shell_executor.py
module: eos_ai.substrate.interactive_shell_executor
lines: 193
size: 6445
generated: 2026-05-07
---

# eos_ai/substrate/interactive_shell_executor.py

Interactive shell executor for Phase 94D.8.

Routes approved actions through an interactive tmux shell environment
on the local PC. Dispatches commands via tmux send-keys so they
execute within the user's interactive session.
...

**Lines:** 193 | **Size:** 6,445 bytes

## Depends On

- [[eos_ai-substrate-visible_gui_success_criteria-py]]

## Contains

- **fn** [[eos_ai-substrate-interactive_shell_executor-py-build_open_drive_in_chrome_script]]`() → str`
- **fn** [[eos_ai-substrate-interactive_shell_executor-py-build_send_open_drive_to_tmux_command]]`(tmux_target) → str`
- **fn** [[eos_ai-substrate-interactive_shell_executor-py-build_founder_confirmation_prompt]]`() → dict[str, Any]`
- **fn** [[eos_ai-substrate-interactive_shell_executor-py-classify_visual_confirmation_response]]`(response) → dict[str, Any]`
- **fn** [[eos_ai-substrate-interactive_shell_executor-py-visible_success_requires_confirmation]]`() → bool`
- **fn** [[eos_ai-substrate-interactive_shell_executor-py-build_next_gate_message]]`(confirmation, work_order_id, target_account) → dict[str, Any] | None`

## Import Statements

```python
from __future__ import annotations
from typing import Any
from eos_ai.substrate.visible_gui_success_criteria import VisibleGuiStatus
```
