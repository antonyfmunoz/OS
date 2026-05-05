---
type: codebase-file
path: eos_ai/substrate/stt_producer.py
module: eos_ai.substrate.stt_producer
lines: 1147
size: 42041
generated: 2026-04-12
---

# eos_ai/substrate/stt_producer.py

STT producer — bounded local speech-to-text capture layer.

Purpose
-------
This module is the first REAL local mic/STT producer for the substrate.
...

**Lines:** 1147 | **Size:** 42,041 bytes

## Used By

- [[scripts-substrate_ptt_binding_smoke_test-py]]
- [[scripts-substrate_stt_producer_smoke_test-py]]
- [[scripts-substrate_transport_report_smoke_test-py]]

## Contains

- **class** [[eos_ai-substrate-stt_producer-py-SttCaptureSource]] — 0 methods
- **class** [[eos_ai-substrate-stt_producer-py-SttCaptureStatus]] — 0 methods
- **class** [[eos_ai-substrate-stt_producer-py-SttWorkstationReadiness]] — 0 methods
- **class** [[eos_ai-substrate-stt_producer-py-SttCaptureEvent]] — 2 methods
- **class** [[eos_ai-substrate-stt_producer-py-SttRuntimeCapability]] — 1 methods
- **class** [[eos_ai-substrate-stt_producer-py-SttCaptureHistory]] — 6 methods
- **class** [[eos_ai-substrate-stt_producer-py-LocalSttRuntime]] — 6 methods
- **fn** [[eos_ai-substrate-stt_producer-py-_env_flag]]`(name, default) → bool`
- **fn** [[eos_ai-substrate-stt_producer-py-_env_str]]`(name, default) → Optional[str]`
- **fn** [[eos_ai-substrate-stt_producer-py-_env_float]]`(name, default) → float`
- **fn** [[eos_ai-substrate-stt_producer-py-_env_int]]`(name, default) → int`
- **fn** [[eos_ai-substrate-stt_producer-py-_log]]`(msg) → None`
- **fn** [[eos_ai-substrate-stt_producer-py-_utcnow_iso]]`() → str`
- **fn** [[eos_ai-substrate-stt_producer-py-_new_id]]`(prefix) → str`
- **fn** [[eos_ai-substrate-stt_producer-py-_probe_capability]]`() → SttRuntimeCapability`
- **fn** [[eos_ai-substrate-stt_producer-py-_detect_environment]]`() → str`
- **fn** [[eos_ai-substrate-stt_producer-py-_enumerate_input_devices]]`() → list[dict[str, Any]]`
- **fn** [[eos_ai-substrate-stt_producer-py-_validate_audio_quality]]`(audio) → tuple[bool, Optional[str], dict[str, Any]]`
- **fn** [[eos_ai-substrate-stt_producer-py-stt_workstation_readiness]]`() → dict[str, Any]`
- **fn** [[eos_ai-substrate-stt_producer-py-stt_runtime_status]]`() → dict[str, Any]`
- **fn** [[eos_ai-substrate-stt_producer-py-get_stt_capture_history]]`() → SttCaptureHistory`
- **fn** [[eos_ai-substrate-stt_producer-py-reset_stt_capture_history_for_tests]]`() → None`
- **fn** [[eos_ai-substrate-stt_producer-py-get_local_stt_runtime]]`() → LocalSttRuntime`
- **fn** [[eos_ai-substrate-stt_producer-py-reset_local_stt_runtime_for_tests]]`() → None`
- **fn** [[eos_ai-substrate-stt_producer-py-stt_capture_snapshot]]`(node_id) → dict[str, Any]`
- **fn** [[eos_ai-substrate-stt_producer-py-recent_stt_captures]]`(limit, node_id) → list[dict[str, Any]]`

## Import Statements

```python
from __future__ import annotations
import os
import sys
import threading
import time
import uuid
import wave
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from enum import Enum
from pathlib import Path
from typing import Any
from typing import Optional
```
