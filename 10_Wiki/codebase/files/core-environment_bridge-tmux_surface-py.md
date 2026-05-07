---
type: codebase-file
path: core/environment_bridge/tmux_surface.py
module: core.environment_bridge.tmux_surface
lines: 137
size: 3753
generated: 2026-05-07
---

# core/environment_bridge/tmux_surface.py

Tmux execution surface for the Environment Bridge.

Models tmux as a persistent local execution environment. Builds
commands and policies without executing them. Dangerous commands
are blocked at the model layer.
...

**Lines:** 137 | **Size:** 3,753 bytes

## Contains

- **class** [[core-environment_bridge-tmux_surface-py-TmuxSurfaceStatus]] — 0 methods
- **class** [[core-environment_bridge-tmux_surface-py-TmuxSurface]] — 1 methods
- **fn** [[core-environment_bridge-tmux_surface-py-build_tmux_surface]]`(host, session_name, window_name, working_directory, allowed_commands, blocked_commands) → TmuxSurface`
- **fn** [[core-environment_bridge-tmux_surface-py-tmux_command_is_allowed]]`(surface, command) → bool`
- **fn** [[core-environment_bridge-tmux_surface-py-build_tmux_send_command]]`(surface, command) → str`
- **fn** [[core-environment_bridge-tmux_surface-py-tmux_surface_blocks_command]]`(surface, command) → bool`
- **fn** [[core-environment_bridge-tmux_surface-py-summarize_tmux_surface]]`(surface) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any
```
