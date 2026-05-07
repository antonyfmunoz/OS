---
type: codebase-function
file: eos_ai/substrate/nodes.py
line: 173
generated: 2026-05-07
---

# NodeRegistry.purge_stale

**File:** [[eos_ai-substrate-nodes-py]] | **Line:** 173
**Signature:** `purge_stale() → list[str]`

**Class:** [[eos_ai-substrate-nodes-py-NodeRegistry]]

Remove nodes whose last_seen is older than max_age_hours.

Protects well-known nodes (vps-primary, antony-workstation) from
purge.  Returns list of removed node_ids.

## Calls

- [[eos_ai-substrate-nodes-py-NodeRegistry-_flush]]
