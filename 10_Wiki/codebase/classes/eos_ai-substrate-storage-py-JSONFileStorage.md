---
type: codebase-class
file: eos_ai/substrate/storage.py
line: 52
generated: 2026-04-11
---

# JSONFileStorage

**File:** [[eos_ai-substrate-storage-py]] | **Line:** 52

Thread-safe JSON file KV store. All values must be JSON-serializable.

File layout: {"<key>": <value>, ...}
Writes are atomic via os.replace on a tempfile sibling.

## Methods

- [[eos_ai-substrate-storage-py-JSONFileStorage-__init__]]`(path) → None` — 
- [[eos_ai-substrate-storage-py-JSONFileStorage-_read_all]]`() → dict` — 
- [[eos_ai-substrate-storage-py-JSONFileStorage-_write_all]]`(data) → None` — 
- [[eos_ai-substrate-storage-py-JSONFileStorage-get]]`(key, default) → Any` — 
- [[eos_ai-substrate-storage-py-JSONFileStorage-put]]`(key, value) → None` — 
- [[eos_ai-substrate-storage-py-JSONFileStorage-all_keys]]`() → list[str]` — 
