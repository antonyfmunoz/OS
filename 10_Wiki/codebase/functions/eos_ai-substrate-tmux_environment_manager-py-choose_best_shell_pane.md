---
type: codebase-function
file: eos_ai/substrate/tmux_environment_manager.py
line: 132
generated: 2026-05-07
---

# choose_best_shell_pane

**File:** [[eos_ai-substrate-tmux_environment_manager-py]] | **Line:** 132
**Signature:** `choose_best_shell_pane(panes) → TmuxPane | None`

Choose the best shell pane for command dispatch.

Prefers:
1. Panes with 'gui' or 'shell' in session name
2. Regular shell panes
...

## Calls

- [[eos_ai-substrate-tmux_environment_manager-py-is_shell_pane]]
