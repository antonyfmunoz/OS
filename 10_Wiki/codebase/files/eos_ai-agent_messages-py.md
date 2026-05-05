---
type: codebase-file
path: eos_ai/agent_messages.py
module: eos_ai.agent_messages
lines: 141
size: 4848
generated: 2026-04-12
---

# eos_ai/agent_messages.py

AgentMessageBus — inter-agent communication layer.

Agents send typed messages to each other via Neon events.
Messages are directional (upward/downward/lateral) and typed
(task/report/alert/query/result).
...

**Lines:** 141 | **Size:** 4,848 bytes

## Depends On

- [[eos_ai-context-py]]

## Contains

- **class** [[eos_ai-agent_messages-py-MessageDirection]] — 0 methods
- **class** [[eos_ai-agent_messages-py-MessageType]] — 0 methods
- **class** [[eos_ai-agent_messages-py-AgentMessage]] — 0 methods
- **class** [[eos_ai-agent_messages-py-AgentMessageBus]] — 4 methods

## Import Statements

```python
import json
import uuid
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from enum import Enum
from eos_ai.context import EOSContext
```
