---
type: codebase-function
file: eos_ai/substrate/storage.py
line: 177
generated: 2026-04-12
---

# get_storage

**File:** [[eos_ai-substrate-storage-py]] | **Line:** 177
**Signature:** `get_storage(prefer) → SubstrateStorage`

Return a process-wide storage singleton.

prefer:
  "auto" (default) — try Neon, fall back to JSON
  "json"           — always JSON file
...

## Calls

- [[eos_ai-substrate-storage-py-_log]]

## Called By

- [[eos_ai-substrate-control_bridge-py-_load_state]]
- [[eos_ai-substrate-control_bridge-py-_save_state]]
- [[eos_ai-substrate-local_listener-py-TriggerHistory-__init__]]
- [[eos_ai-substrate-wake_producer-py-WakeProducerHistory-__init__]]
