---
type: codebase-function
file: eos_ai/substrate/windows_desktop_relay_client.py
line: 130
generated: 2026-05-07
---

# write_request_to_relay

**File:** [[eos_ai-substrate-windows_desktop_relay_client-py]] | **Line:** 130
**Signature:** `write_request_to_relay(request, relay_inbox, dry_run) → Path`

Write an action request JSON to the relay inbox.

In dry_run mode, the request is written but marked as dry_run
so the relay can skip execution.

## Calls

- [[eos_ai-substrate-windows_desktop_relay_client-py-_log]]

## Called By

- [[eos_ai-substrate-windows_desktop_relay_client-py-send_request_and_wait]]
