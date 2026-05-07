---
type: codebase-file
path: core/wiki_navigation.py
module: core.wiki_navigation
lines: 326
size: 12644
generated: 2026-05-07
---

# core/wiki_navigation.py

Wiki Navigation Layer — bridges graph nodes and Obsidian wiki pages.

Provides:
    WikiIndex       — deterministic mapping between graph nodes and wiki pages
    enrich_candidates(candidates, wiki_index) -> candidates with wiki metadata
...

**Lines:** 326 | **Size:** 12,644 bytes

## Contains

- **class** [[core-wiki_navigation-py-WikiIndex]] — 9 methods
- **fn** [[core-wiki_navigation-py-enrich_candidates]]`(candidates, wiki_index) → list[dict]`
- **fn** [[core-wiki_navigation-py-wiki_traverse]]`(candidates, wiki_index, max_expansions) → list[str]`
- **fn** [[core-wiki_navigation-py-wiki_rerank_bonus]]`(candidate) → float`

## Import Statements

```python
import re
import sys
from pathlib import Path
```
