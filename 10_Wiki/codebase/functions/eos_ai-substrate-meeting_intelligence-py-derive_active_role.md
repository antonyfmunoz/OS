---
type: codebase-function
file: eos_ai/substrate/meeting_intelligence.py
line: 1221
generated: 2026-04-12
---

# derive_active_role

**File:** [[eos_ai-substrate-meeting_intelligence-py]] | **Line:** 1221
**Signature:** `derive_active_role(node_id) → Optional[str]`

Best-effort: derive the currently speaking role from the active voice
session, if one is attached to the node. Always safe; returns None on
any failure so the caller can fall back to role-agnostic phrasing.

## Calls

- [[eos_ai-substrate-meeting_intelligence-py-_normalize_role]]

## Called By

- [[eos_ai-substrate-meeting_intelligence-py-maybe_emit_intervention]]
