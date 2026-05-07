---
type: codebase-file
path: eos_ai/substrate/tmux_environment_manager.py
module: eos_ai.substrate.tmux_environment_manager
lines: 206
size: 6115
generated: 2026-05-07
---

# eos_ai/substrate/tmux_environment_manager.py

Tmux environment manager for Phase 94D.8.

Manages tmux sessions/panes as environments within the UMH organism.
Provides pane discovery, classification, selection, and command dispatch.

...

**Lines:** 206 | **Size:** 6,115 bytes

## Depends On

- [[eos_ai-substrate-environment_contracts-py]]

## Contains

- **class** [[eos_ai-substrate-tmux_environment_manager-py-TmuxPane]] — 1 methods
- **fn** [[eos_ai-substrate-tmux_environment_manager-py-parse_tmux_list_panes_output]]`(output) → list[TmuxPane]`
- **fn** [[eos_ai-substrate-tmux_environment_manager-py-classify_tmux_pane]]`(pane) → str`
- **fn** [[eos_ai-substrate-tmux_environment_manager-py-is_shell_pane]]`(pane) → bool`
- **fn** [[eos_ai-substrate-tmux_environment_manager-py-is_busy_pane]]`(pane) → bool`
- **fn** [[eos_ai-substrate-tmux_environment_manager-py-choose_best_shell_pane]]`(panes) → TmuxPane | None`
- **fn** [[eos_ai-substrate-tmux_environment_manager-py-build_tmux_list_panes_command]]`() → str`
- **fn** [[eos_ai-substrate-tmux_environment_manager-py-build_tmux_send_keys_command]]`(target, command) → str`
- **fn** [[eos_ai-substrate-tmux_environment_manager-py-build_tmux_new_shell_session_command]]`(session_name) → str`
- **fn** [[eos_ai-substrate-tmux_environment_manager-py-build_tmux_capture_pane_command]]`(target) → str`
- **fn** [[eos_ai-substrate-tmux_environment_manager-py-panes_to_environment_profiles]]`(panes, node_id) → list[EnvironmentProfile]`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from eos_ai.substrate.environment_contracts import EnvironmentBinding
from eos_ai.substrate.environment_contracts import EnvironmentCapability
from eos_ai.substrate.environment_contracts import EnvironmentProfile
from eos_ai.substrate.environment_contracts import EnvironmentType
from eos_ai.substrate.environment_contracts import build_environment_from_tmux_pane
```
