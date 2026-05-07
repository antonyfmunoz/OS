---
type: codebase-file
path: eos_ai/substrate/advisor_bridge_transport.py
module: eos_ai.substrate.advisor_bridge_transport
lines: 264
size: 8192
generated: 2026-05-07
---

# eos_ai/substrate/advisor_bridge_transport.py

Advisor bridge transport for Phase 94D.5.

Transport-aware helpers that bind the abstract advisor relay contracts
to the founder's current topology: VPS orchestrator ↔ local PC worker
via Tailscale + HTTP bridge + SSH + file-based inbox/outbox.
...

**Lines:** 264 | **Size:** 8,192 bytes

## Depends On

- [[eos_ai-substrate-message_bus_contracts-py]]

## Contains

- **class** [[eos_ai-substrate-advisor_bridge_transport-py-AdvisorMessageFile]] — 5 methods
- **fn** [[eos_ai-substrate-advisor_bridge_transport-py-_now_iso]]`() → str`
- **fn** [[eos_ai-substrate-advisor_bridge_transport-py-_new_id]]`() → str`
- **fn** [[eos_ai-substrate-advisor_bridge_transport-py-build_local_inbox_path]]`(session_name) → str`
- **fn** [[eos_ai-substrate-advisor_bridge_transport-py-build_local_outbox_path]]`(work_order_id) → str`
- **fn** [[eos_ai-substrate-advisor_bridge_transport-py-build_advisor_message_dir]]`() → str`
- **fn** [[eos_ai-substrate-advisor_bridge_transport-py-create_worker_approval_request_file]]`(work_order_id, action, target, description, risk_level, worker_id, backend) → AdvisorMessageFile`
- **fn** [[eos_ai-substrate-advisor_bridge_transport-py-create_advisor_response_file]]`(approval_request_id, decision, work_order_id, reason, correlation_id) → AdvisorMessageFile`
- **fn** [[eos_ai-substrate-advisor_bridge_transport-py-build_forward_to_local_payload]]`(message_file, session_name) → dict[str, Any]`
- **fn** [[eos_ai-substrate-advisor_bridge_transport-py-build_poll_local_outbox_command]]`(work_order_id, outbox_dir) → str`
- **fn** [[eos_ai-substrate-advisor_bridge_transport-py-build_read_local_outbox_file_command]]`(filepath) → str`
- **fn** [[eos_ai-substrate-advisor_bridge_transport-py-build_write_local_inbox_command]]`(content, inbox_path) → str`
- **fn** [[eos_ai-substrate-advisor_bridge_transport-py-build_ssh_health_command]]`() → str`
- **fn** [[eos_ai-substrate-advisor_bridge_transport-py-build_bridge_health_command]]`() → str`
- **fn** [[eos_ai-substrate-advisor_bridge_transport-py-build_bridge_status_command]]`() → str`
- **fn** [[eos_ai-substrate-advisor_bridge_transport-py-build_mkdir_local_dirs_command]]`() → str`

## Import Statements

```python
from __future__ import annotations
import json
import uuid
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Any
from eos_ai.substrate.message_bus_contracts import MessageEnvelope
from eos_ai.substrate.message_bus_contracts import MessagePriority
from eos_ai.substrate.message_bus_contracts import MessageType
```
