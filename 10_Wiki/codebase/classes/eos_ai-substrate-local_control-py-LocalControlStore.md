---
type: codebase-class
file: eos_ai/substrate/local_control.py
line: 183
generated: 2026-05-07
---

# LocalControlStore

**File:** [[eos_ai-substrate-local_control-py]] | **Line:** 183

Persistent store for local control requests and mode state.

Singleton via ``default()`` classmethod. Backed by substrate.storage
so data survives across process boundaries.

## Methods

- [[eos_ai-substrate-local_control-py-LocalControlStore-__init__]]`() → None` — 
- [[eos_ai-substrate-local_control-py-LocalControlStore-_load]]`() → None` — 
- [[eos_ai-substrate-local_control-py-LocalControlStore-_flush]]`() → None` — Persist current state to storage. Caller holds the lock.
- [[eos_ai-substrate-local_control-py-LocalControlStore-_flush_mode]]`() → None` — Persist mode to storage. Caller holds the lock.
- [[eos_ai-substrate-local_control-py-LocalControlStore-_prune]]`() → None` — Drop oldest completed requests when over _MAX_REQUESTS. Caller holds lock.
- [[eos_ai-substrate-local_control-py-LocalControlStore-get]]`(request_id) → Optional[LocalControlRequest]` — Retrieve a single request by ID.
- [[eos_ai-substrate-local_control-py-LocalControlStore-put]]`(request) → None` — Persist a request (insert or update), pruning if over cap.
- [[eos_ai-substrate-local_control-py-LocalControlStore-all]]`() → list[LocalControlRequest]` — All requests sorted by created_at descending.
- [[eos_ai-substrate-local_control-py-LocalControlStore-by_status]]`(status) → list[LocalControlRequest]` — Filter requests by status, sorted by created_at descending.
- [[eos_ai-substrate-local_control-py-LocalControlStore-pending]]`() → list[LocalControlRequest]` — Convenience: all PENDING requests.
- [[eos_ai-substrate-local_control-py-LocalControlStore-get_mode]]`() → LocalControlMode` — Return the current control mode (reads from loaded state).
- [[eos_ai-substrate-local_control-py-LocalControlStore-set_mode]]`(mode) → None` — Set the control mode and persist.
- [[eos_ai-substrate-local_control-py-LocalControlStore-default]]`() → LocalControlStore` — Return the process-wide singleton, creating on first call.
- [[eos_ai-substrate-local_control-py-LocalControlStore-reset_default_for_tests]]`() → None` — Drop the singleton. Next ``default()`` rehydrates from storage.
