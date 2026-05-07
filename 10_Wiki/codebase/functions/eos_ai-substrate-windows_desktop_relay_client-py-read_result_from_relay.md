---
type: codebase-function
file: eos_ai/substrate/windows_desktop_relay_client.py
line: 160
generated: 2026-05-07
---

# read_result_from_relay

**File:** [[eos_ai-substrate-windows_desktop_relay_client-py]] | **Line:** 160
**Signature:** `read_result_from_relay(request_id, relay_outbox, timeout_seconds, poll_interval) → dict[str, Any] | None`

Poll the relay outbox for a result matching the request_id.

Returns None if the result is not found within the timeout.

## Calls

- [[eos_ai-substrate-windows_desktop_relay_client-py-_log]]

## Called By

- [[eos_ai-substrate-windows_desktop_relay_client-py-send_request_and_wait]]
