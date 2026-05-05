---
type: codebase-file
path: eos_ai/substrate/meeting_transport.py
module: eos_ai.substrate.meeting_transport
lines: 1012
size: 38606
generated: 2026-04-12
---

# eos_ai/substrate/meeting_transport.py

Meeting voice transport — bounded adapter onto the existing voice substrate.

Purpose
-------
This is the FIRST meeting voice transport adapter. It exists so that
...

**Lines:** 1012 | **Size:** 38,606 bytes

## Depends On

- [[eos_ai-substrate-meeting_sources-py]]

## Used By

- [[scripts-substrate_google_meet_smoke_test-py]]
- [[scripts-substrate_meeting_attachment_smoke_test-py]]
- [[scripts-substrate_meeting_transport_smoke_test-py]]

## Contains

- **class** [[eos_ai-substrate-meeting_transport-py-MeetingTransportEvent]] — 1 methods
- **class** [[eos_ai-substrate-meeting_transport-py-_MeetingTransportHistory]] — 4 methods
- **class** [[eos_ai-substrate-meeting_transport-py-MeetingTransport]] — 17 methods
- **fn** [[eos_ai-substrate-meeting_transport-py-_log]]`(msg) → None`
- **fn** [[eos_ai-substrate-meeting_transport-py-_utcnow_iso]]`() → str`
- **fn** [[eos_ai-substrate-meeting_transport-py-_probe_meeting_capability]]`() → dict[str, Any]`
- **fn** [[eos_ai-substrate-meeting_transport-py-_normalize_platform]]`(platform) → str`
- **fn** [[eos_ai-substrate-meeting_transport-py-get_meeting_transport_history]]`() → _MeetingTransportHistory`
- **fn** [[eos_ai-substrate-meeting_transport-py-reset_meeting_transport_history_for_tests]]`() → None`
- **fn** [[eos_ai-substrate-meeting_transport-py-_build_node_id]]`(platform, meeting_id) → str`
- **fn** [[eos_ai-substrate-meeting_transport-py-get_default_meeting_transport]]`() → MeetingTransport`
- **fn** [[eos_ai-substrate-meeting_transport-py-reset_default_meeting_transports_for_tests]]`() → None`
- **fn** [[eos_ai-substrate-meeting_transport-py-_env_hook_enabled]]`() → bool`
- **fn** [[eos_ai-substrate-meeting_transport-py-_playback_env_enabled]]`() → bool`
- **fn** [[eos_ai-substrate-meeting_transport-py-maybe_mirror_meeting_utterance]]`(text) → Optional[dict[str, Any]]`

## Import Statements

```python
from __future__ import annotations
import os
import sys
import threading
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from typing import Any
from typing import Optional
from eos_ai.substrate.meeting_sources import is_meeting_source
```
