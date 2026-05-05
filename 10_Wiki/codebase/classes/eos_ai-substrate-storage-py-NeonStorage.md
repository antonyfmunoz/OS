---
type: codebase-class
file: eos_ai/substrate/storage.py
line: 109
generated: 2026-04-12
---

# NeonStorage

**File:** [[eos_ai-substrate-storage-py]] | **Line:** 109

Neon-backed KV using the existing RLS-scoped get_conn() pattern.

The table is created on first successful connect. On ANY failure, the
wrapping get_storage() call falls back to JSONFileStorage. This avoids
a hard dependency on DB health during a session start.
...

## Methods

- [[eos_ai-substrate-storage-py-NeonStorage-__init__]]`() → None` — 
- [[eos_ai-substrate-storage-py-NeonStorage-_ensure_table]]`() → None` — 
- [[eos_ai-substrate-storage-py-NeonStorage-get]]`(key, default) → Any` — 
- [[eos_ai-substrate-storage-py-NeonStorage-put]]`(key, value) → None` — 
- [[eos_ai-substrate-storage-py-NeonStorage-all_keys]]`() → list[str]` — 
