---
type: codebase-file
path: eos_ai/substrate/result_store.py
module: eos_ai.substrate.result_store
lines: 246
size: 8813
generated: 2026-04-11
---

# eos_ai/substrate/result_store.py

ResultStore — durable index of ingested ActionResults.

Sits between the station drainer (producer) and ritual reconciliation /
operator inspection (consumers).

...

**Lines:** 246 | **Size:** 8,813 bytes

## Used By

- [[eos_ai-substrate-result_query-py]]
- [[eos_ai-substrate-ritual_reconciler-py]]
- [[eos_ai-substrate-station_drainer-py]]
- [[eos_ai-substrate-station_readiness-py]]
- [[scripts-substrate_durable_result_smoke_test-py]]
- [[scripts-substrate_result_loop_smoke_test-py]]
- [[scripts-substrate_voice_eos_responder_smoke_test-py]]
- [[scripts-substrate_voice_session_smoke_test-py]]

## Contains

- **class** [[eos_ai-substrate-result_store-py-IngestedResult]] — 3 methods
- **class** [[eos_ai-substrate-result_store-py-ResultStore]] — 14 methods
- **fn** [[eos_ai-substrate-result_store-py-_log]]`(msg) → None`
- **fn** [[eos_ai-substrate-result_store-py-_utcnow]]`() → str`
- **fn** [[eos_ai-substrate-result_store-py-get_result_store]]`() → ResultStore`
- **fn** [[eos_ai-substrate-result_store-py-reset_result_store_for_tests]]`() → None`

## Import Statements

```python
from __future__ import annotations
import sys
import threading
from dataclasses import dataclass
from dataclasses import field
from dataclasses import asdict
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from typing import Any
from typing import Optional
```
