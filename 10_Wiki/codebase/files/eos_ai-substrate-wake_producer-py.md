---
type: codebase-file
path: eos_ai/substrate/wake_producer.py
module: eos_ai.substrate.wake_producer
lines: 491
size: 18416
generated: 2026-05-07
---

# eos_ai/substrate/wake_producer.py

Wake producer — bounded wake-word / clap activation layer for the substrate.

Purpose
-------
Sits one level above `local_listener` and `voice_session`. A wake producer
...

**Lines:** 491 | **Size:** 18,416 bytes

## Depends On

- [[eos_ai-substrate-local_listener-py]]
- [[eos_ai-substrate-storage-py]]
- [[eos_ai-substrate-voice_session-py]]

## Used By

- [[scripts-substrate_audio_loop_smoke_test-py]]
- [[scripts-substrate_operator_state_smoke_test-py]]
- [[scripts-substrate_stt_producer_smoke_test-py]]
- [[scripts-substrate_wake_producer_cli-py]]
- [[scripts-substrate_wake_producer_smoke_test-py]]

## Contains

- **class** [[eos_ai-substrate-wake_producer-py-WakeProducerKind]] — 0 methods
- **class** [[eos_ai-substrate-wake_producer-py-WakeProducerEvent]] — 1 methods
- **class** [[eos_ai-substrate-wake_producer-py-WakeProducerHistory]] — 6 methods
- **class** [[eos_ai-substrate-wake_producer-py-WakeProducerRuntime]] — 7 methods
- **fn** [[eos_ai-substrate-wake_producer-py-_log]]`(msg) → None`
- **fn** [[eos_ai-substrate-wake_producer-py-_utcnow]]`() → str`
- **fn** [[eos_ai-substrate-wake_producer-py-_new_id]]`(prefix) → str`
- **fn** [[eos_ai-substrate-wake_producer-py-resolve_role_hint]]`(phrase) → Optional[str]`
- **fn** [[eos_ai-substrate-wake_producer-py-get_wake_producer_history]]`() → WakeProducerHistory`
- **fn** [[eos_ai-substrate-wake_producer-py-get_wake_producer_runtime]]`() → WakeProducerRuntime`
- **fn** [[eos_ai-substrate-wake_producer-py-reset_wake_producer_runtime_for_tests]]`() → None`

## Import Statements

```python
from __future__ import annotations
import sys
import uuid
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from enum import Enum
from threading import RLock
from typing import Any
from typing import Optional
from eos_ai.substrate.local_listener import LocalListener
from eos_ai.substrate.local_listener import LocalTrigger
from eos_ai.substrate.local_listener import TriggerKind
from eos_ai.substrate.local_listener import TriggerStatus
from eos_ai.substrate.storage import get_storage
from eos_ai.substrate.voice_session import VoiceSession
from eos_ai.substrate.voice_session import VoiceSessionRuntime
from eos_ai.substrate.voice_session import VoiceSessionStatus
from eos_ai.substrate.voice_session import VoiceTurn
from eos_ai.substrate.voice_session import VoiceTurnSource
from eos_ai.substrate.voice_session import get_voice_session_store
```
