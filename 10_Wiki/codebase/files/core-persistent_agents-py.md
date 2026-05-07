---
type: codebase-file
path: core/persistent_agents.py
module: core.persistent_agents
lines: 566
size: 20664
generated: 2026-05-07
---

# core/persistent_agents.py

persistent_agents.py — Long-running stateful agents in the EOS OS.

A persistent agent is NOT a thread. It is a state-carrying object whose
`tick()` method is called on a schedule by the orchestrator. State is
written to disk (data/agent_state/<name>.json) after every tick so restarts
...

**Lines:** 566 | **Size:** 20,664 bytes

## Depends On

- [[core-agent_harness-py]]

## Used By

- [[core-control_plane-py]]

## Contains

- **class** [[core-persistent_agents-py-TickResult]] — 1 methods
- **class** [[core-persistent_agents-py-PersistentAgent]] — 7 methods
- **class** [[core-persistent_agents-py-ObserverAgent]] — 2 methods
- **class** [[core-persistent_agents-py-HealerAgent]] — 1 methods
- **class** [[core-persistent_agents-py-LibrarianAgent]] — 1 methods
- **fn** [[core-persistent_agents-py-_tail_jsonl]]`(path, lines) → list[dict[str, Any]]`
- **fn** [[core-persistent_agents-py-default_agents]]`() → list[PersistentAgent]`
- **fn** [[core-persistent_agents-py-_emit_agent_log]]`(agent, result) → None`

## Import Statements

```python
from __future__ import annotations
import json
import sys
import time
from abc import ABC
from abc import abstractmethod
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from pathlib import Path
from typing import Any
from core.agent_harness import AgentHarness
from core.agent_harness import default_harness
```
