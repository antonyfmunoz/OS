---
type: codebase-file
path: eos_ai/substrate/environment_contracts.py
module: eos_ai.substrate.environment_contracts
lines: 138
size: 4393
generated: 2026-05-07
---

# eos_ai/substrate/environment_contracts.py

Environment contracts for Phase 94D.8.

Defines the environment model: nodes contain environments, environments
host workers, workers execute capabilities.

...

**Lines:** 138 | **Size:** 4,393 bytes

## Used By

- [[eos_ai-substrate-tmux_environment_manager-py]]

## Contains

- **class** [[eos_ai-substrate-environment_contracts-py-EnvironmentType]] — 0 methods
- **class** [[eos_ai-substrate-environment_contracts-py-EnvironmentCapability]] — 0 methods
- **class** [[eos_ai-substrate-environment_contracts-py-EnvironmentBinding]] — 0 methods
- **class** [[eos_ai-substrate-environment_contracts-py-EnvironmentProfile]] — 1 methods
- **fn** [[eos_ai-substrate-environment_contracts-py-is_ssh_service_gui_safe]]`() → bool`
- **fn** [[eos_ai-substrate-environment_contracts-py-is_interactive_session_gui_safe]]`(confirmed) → bool`
- **fn** [[eos_ai-substrate-environment_contracts-py-gui_success_requires_confirmation]]`() → bool`
- **fn** [[eos_ai-substrate-environment_contracts-py-build_environment_from_tmux_pane]]`(session_name, window_index, pane_index, current_command, current_path, node_id) → EnvironmentProfile`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any
```
