---
type: codebase-function
file: eos_ai/substrate/windows_desktop_relay_client.py
line: 115
generated: 2026-05-07
---

# resolve_relay_paths

**File:** [[eos_ai-substrate-windows_desktop_relay_client-py]] | **Line:** 115
**Signature:** `resolve_relay_paths(relay_root) → tuple[Path, Path, Path]`

Resolve relay root, inbox, and outbox paths.

If relay_root is provided, use it. Otherwise use the auto-detected default.
Returns (root, inbox, outbox).

## Called By

- [[eos_ai-substrate-windows_desktop_relay_client-py-_cli_main]]
