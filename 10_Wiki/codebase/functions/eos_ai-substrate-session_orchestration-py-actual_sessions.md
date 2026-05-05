---
type: codebase-function
file: eos_ai/substrate/session_orchestration.py
line: 99
generated: 2026-04-12
---

# actual_sessions

**File:** [[eos_ai-substrate-session_orchestration-py]] | **Line:** 99
**Signature:** `actual_sessions(target) → list[dict[str, Any]]`

List actual ``dex_*`` tmux sessions via claude_session_bridge.

Returns the ``sessions`` list from ``list_sessions`` (only dex-prefixed
sessions). On import or call failure returns an empty list.

## Calls

- [[eos_ai-substrate-session_orchestration-py-_log]]

## Called By

- [[eos_ai-substrate-session_orchestration-py-reconcile_sessions]]
- [[scripts-substrate_session_orchestration_smoke_test-py-test_registry]]
