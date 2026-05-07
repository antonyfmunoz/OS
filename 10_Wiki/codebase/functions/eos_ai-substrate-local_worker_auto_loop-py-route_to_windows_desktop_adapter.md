---
type: codebase-function
file: eos_ai/substrate/local_worker_auto_loop.py
line: 236
generated: 2026-05-07
---

# route_to_windows_desktop_adapter

**File:** [[eos_ai-substrate-local_worker_auto_loop-py]] | **Line:** 236
**Signature:** `route_to_windows_desktop_adapter(packet, dry_run) → dict[str, Any]`

Route a GUI action through the Windows desktop adapter relay.

In dry_run mode (default), the request is written but not executed.
Returns a summary dict.

## Calls

- [[eos_ai-substrate-local_worker_auto_loop-py-check_windows_desktop_adapter_available]]
