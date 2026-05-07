---
type: codebase-file
path: eos_ai/substrate/nodes.py
module: eos_ai.substrate.nodes
lines: 242
size: 8795
generated: 2026-05-07
---

# eos_ai/substrate/nodes.py

Node abstraction — execution targets beyond "the VPS".

Today EOS implicitly assumes all work happens on the VPS. This module
introduces a typed `Node` model and an in-memory `NodeRegistry` so future
routing code can reason about *where* work runs (VPS, local station, future
...

**Lines:** 242 | **Size:** 8,795 bytes

## Used By

- [[eos_ai-substrate-execution_router-py]]
- [[eos_ai-substrate-local_listener-py]]
- [[eos_ai-substrate-ritual_body-py]]
- [[eos_ai-substrate-ritual_inference-py]]
- [[eos_ai-substrate-station_daemon-py]]
- [[eos_ai-substrate-station_readiness-py]]
- [[eos_ai-substrate-voice_session-py]]
- [[scripts-substrate_local_listener_smoke_test-py]]
- [[scripts-substrate_ptt_binding_smoke_test-py]]
- [[scripts-substrate_smoke_test-py]]
- [[scripts-substrate_transport_report_smoke_test-py]]
- [[scripts-substrate_voice_session_smoke_test-py]]

## Contains

- **class** [[eos_ai-substrate-nodes-py-NodeType]] — 0 methods
- **class** [[eos_ai-substrate-nodes-py-NodeRole]] — 0 methods
- **class** [[eos_ai-substrate-nodes-py-NodeStatus]] — 0 methods
- **class** [[eos_ai-substrate-nodes-py-Node]] — 2 methods
- **class** [[eos_ai-substrate-nodes-py-NodeRegistry]] — 13 methods

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from enum import Enum
from typing import Optional
```
