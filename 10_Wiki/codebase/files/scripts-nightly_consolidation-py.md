---
type: codebase-file
path: scripts/nightly_consolidation.py
module: scripts.nightly_consolidation
lines: 325
size: 10509
tags: [entry-point]
generated: 2026-04-11
---

# scripts/nightly_consolidation.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Nightly memory consolidation — the "sleep/dream" layer.

Processes accumulated episodic memory into durable knowledge:
1. Find new/unprocessed conversations
2. Generate summaries with salience scoring
...

**Lines:** 325 | **Size:** 10,509 bytes

## Contains

- **fn** [[scripts-nightly_consolidation-py-_parse_frontmatter]]`(text) → tuple[dict, str]`
- **fn** [[scripts-nightly_consolidation-py-_dump_frontmatter]]`(fm, body) → str`
- **fn** [[scripts-nightly_consolidation-py-run_summarization]]`(dry_run) → dict`
- **fn** [[scripts-nightly_consolidation-py-run_promotion]]`(dry_run) → dict`
- **fn** [[scripts-nightly_consolidation-py-rescore_summaries]]`(dry_run) → dict`
- **fn** [[scripts-nightly_consolidation-py-main]]`() → None`

## Import Statements

```python
import sys
import os
import glob
import argparse
import logging
from datetime import datetime
from datetime import timezone
```
