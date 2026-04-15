---
type: codebase-file
path: scripts/substrate_discord_mode_routing_smoke_test.py
module: scripts.substrate_discord_mode_routing_smoke_test
lines: 542
size: 18101
tags: [entry-point]
generated: 2026-04-12
---

# scripts/substrate_discord_mode_routing_smoke_test.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Discord Channel Mode Routing v1 — smoke test.

Proves that:
  1.  Channel → mode classification is deterministic and exact-match only.
  2.  Mode → session mapping returns the right target/session per mode.
...

**Lines:** 542 | **Size:** 18,101 bytes

## Contains

- **fn** [[scripts-substrate_discord_mode_routing_smoke_test-py-check]]`(name, cond, detail) → None`
- **fn** [[scripts-substrate_discord_mode_routing_smoke_test-py-_header]]`(msg) → None`
- **fn** [[scripts-substrate_discord_mode_routing_smoke_test-py-_reset_env]]`() → None`
- **fn** [[scripts-substrate_discord_mode_routing_smoke_test-py-test_classification]]`() → None`
- **fn** [[scripts-substrate_discord_mode_routing_smoke_test-py-test_session_mapping]]`() → None`
- **fn** [[scripts-substrate_discord_mode_routing_smoke_test-py-test_thread_local_context]]`() → None`
- **fn** [[scripts-substrate_discord_mode_routing_smoke_test-py-test_hotpath_clean]]`() → None`
- **fn** [[scripts-substrate_discord_mode_routing_smoke_test-py-test_end_to_end_router_override]]`() → None`
- **fn** [[scripts-substrate_discord_mode_routing_smoke_test-py-test_ingest_adds_mode_metadata]]`() → None`
- **fn** [[scripts-substrate_discord_mode_routing_smoke_test-py-test_tts_footer_untouched]]`() → None`
- **fn** [[scripts-substrate_discord_mode_routing_smoke_test-py-test_shared_router_tripwire]]`() → None`
- **fn** [[scripts-substrate_discord_mode_routing_smoke_test-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import os
import sys
```
