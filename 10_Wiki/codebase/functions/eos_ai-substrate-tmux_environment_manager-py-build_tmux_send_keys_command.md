---
type: codebase-function
file: eos_ai/substrate/tmux_environment_manager.py
line: 162
generated: 2026-05-07
---

# build_tmux_send_keys_command

**File:** [[eos_ai-substrate-tmux_environment_manager-py]] | **Line:** 162
**Signature:** `build_tmux_send_keys_command(target, command) → str`

Build the SSH command to send keys into a specific tmux pane.

target: session:window.pane format (e.g., 'my_session:0.0')
command: the shell command to execute
