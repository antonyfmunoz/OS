---
type: codebase-function
file: eos_ai/substrate/tmux_environment_manager.py
line: 69
generated: 2026-05-07
---

# parse_tmux_list_panes_output

**File:** [[eos_ai-substrate-tmux_environment_manager-py]] | **Line:** 69
**Signature:** `parse_tmux_list_panes_output(output) → list[TmuxPane]`

Parse output from tmux list-panes -a with custom format.

Expected format per line:
session_name:window_index.pane_index | cmd=command | path=/some/path
