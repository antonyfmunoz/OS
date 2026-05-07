---
type: codebase-file
path: core/agent_harness.py
module: core.agent_harness
lines: 741
size: 25852
generated: 2026-05-07
---

# core/agent_harness.py

agent_harness.py — Unified execution surface for every agent in EOS.

Every agent call flows through AgentHarness. The harness owns:

  * Tools         → scripts.action_system.ActionSystem
...

**Lines:** 741 | **Size:** 25,852 bytes

## Depends On

- [[core-capability-py]]

## Used By

- [[core-persistent_agents-py]]

## Contains

- **class** [[core-agent_harness-py-HarnessResult]] — 1 methods
- **class** [[core-agent_harness-py-AgentHarness]] — 15 methods
- **fn** [[core-agent_harness-py-default_harness]]`() → AgentHarness`
- **fn** [[core-agent_harness-py-_routing_output]]`(result) → str`
- **fn** [[core-agent_harness-py-_routing_provider]]`(result) → str`
- **fn** [[core-agent_harness-py-_json_safe]]`(v) → bool`

## Import Statements

```python
from __future__ import annotations
import json
import sys
import threading
import time
import uuid
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Any
from typing import Callable
from core.capability import CapabilityEnforcer
from core.capability import CapabilityProfile
from core.capability import OperationKind
from core.capability import RiskTier
from core.capability import DEFAULT_PROFILES
from core.capability import get_profile
from core.capability import operation_for_action_type
```
