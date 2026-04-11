---
type: codebase-function
file: scripts/substrate_discord_mode_routing_smoke_test.py
line: 492
generated: 2026-04-11
---

# test_shared_router_tripwire

**File:** [[scripts-substrate_discord_mode_routing_smoke_test-py]] | **Line:** 492
**Signature:** `test_shared_router_tripwire() → None`

Tripwire: neither mode should bypass the broader router.

We assert the mode router module does not import or call
respond_via_claude_session directly — the ONLY path to claude_cli
is through eos_ai.model_router.call_with_fallback.

## Calls

- [[scripts-substrate_discord_mode_routing_smoke_test-py-_header]]
- [[scripts-substrate_discord_mode_routing_smoke_test-py-check]]

## Called By

- [[scripts-substrate_discord_mode_routing_smoke_test-py-main]]
