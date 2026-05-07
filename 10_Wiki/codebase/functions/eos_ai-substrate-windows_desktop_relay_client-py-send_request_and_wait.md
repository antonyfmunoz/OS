---
type: codebase-function
file: eos_ai/substrate/windows_desktop_relay_client.py
line: 229
generated: 2026-05-07
---

# send_request_and_wait

**File:** [[eos_ai-substrate-windows_desktop_relay_client-py]] | **Line:** 229
**Signature:** `send_request_and_wait(request, relay_inbox, relay_outbox, timeout_seconds, dry_run) → dict[str, Any]`

Write request, then poll for result.

Returns a summary dict with the result or timeout status.

## Calls

- [[eos_ai-substrate-windows_desktop_relay_client-py-_log]]
- [[eos_ai-substrate-windows_desktop_relay_client-py-read_result_from_relay]]
- [[eos_ai-substrate-windows_desktop_relay_client-py-write_request_to_relay]]

## Called By

- [[eos_ai-substrate-windows_desktop_relay_client-py-_cli_main]]
