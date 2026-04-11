---
type: codebase-file
path: scripts/substrate_voice_eos_responder_smoke_test.py
module: scripts.substrate_voice_eos_responder_smoke_test
lines: 328
size: 13040
tags: [entry-point]
generated: 2026-04-11
---

# scripts/substrate_voice_eos_responder_smoke_test.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Voice → EOS responder smoke test.

Proves the bounded EOS-backed voice responder integration end-to-end:
  1. Backward compat: with NO EOS responder installed, the substrate stub
     still works exactly as before.
...

**Lines:** 328 | **Size:** 13,040 bytes

## Depends On

- [[eos_ai-substrate-result_store-py]]
- [[eos_ai-substrate-station_bus-py]]
- [[eos_ai-substrate-station_daemon-py]]
- [[eos_ai-substrate-voice_eos_responder-py]]
- [[eos_ai-substrate-voice_session-py]]

## Contains

- **class** [[scripts-substrate_voice_eos_responder_smoke_test-py-_MockRoutingResult]] — 1 methods
- **class** [[scripts-substrate_voice_eos_responder_smoke_test-py-_MockRouter]] — 2 methods
- **fn** [[scripts-substrate_voice_eos_responder_smoke_test-py-_header]]`(msg) → None`
- **fn** [[scripts-substrate_voice_eos_responder_smoke_test-py-_install_mock_router]]`(mock) → None`
- **fn** [[scripts-substrate_voice_eos_responder_smoke_test-py-_restore_real_router]]`() → None`
- **fn** [[scripts-substrate_voice_eos_responder_smoke_test-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import sys
from eos_ai.substrate.result_store import get_result_store
from eos_ai.substrate.result_store import reset_result_store_for_tests
from eos_ai.substrate.station_bus import get_station_bus
from eos_ai.substrate.station_daemon import StationDaemon
from eos_ai.substrate.voice_eos_responder import EOS_VOICE_ROLES
from eos_ai.substrate.voice_eos_responder import install_default_eos_voice_responder
from eos_ai.substrate.voice_eos_responder import is_eos_voice_responder_installed
from eos_ai.substrate.voice_eos_responder import uninstall_eos_voice_responder
from eos_ai.substrate.voice_session import VoiceSessionRuntime
from eos_ai.substrate.voice_session import VoiceSessionStatus
from eos_ai.substrate.voice_session import VoiceTurnSource
from eos_ai.substrate.voice_session import get_voice_session_store
from eos_ai.substrate.voice_session import reset_voice_session_store_for_tests
from eos_ai.substrate.voice_session import voice_session_report
```
