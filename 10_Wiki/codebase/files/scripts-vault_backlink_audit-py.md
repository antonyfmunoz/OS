---
type: codebase-file
path: scripts/vault_backlink_audit.py
module: scripts.vault_backlink_audit
lines: 275
size: 9411
tags: [entry-point]
generated: 2026-05-07
---

# scripts/vault_backlink_audit.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Vault Backlink Health + Retrieval Signal Report

Surfaces backlinking opportunities and retrieval-quality signals
across 10_Wiki/ and vault/.

...

**Lines:** 275 | **Size:** 9,411 bytes

## Contains

- **fn** [[scripts-vault_backlink_audit-py-extract_wikilinks]]`(content) → set[str]`
- **fn** [[scripts-vault_backlink_audit-py-find_scannable_files]]`() → list[Path]`
- **fn** [[scripts-vault_backlink_audit-py-run_health_check]]`(show_retrieval) → None`
- **fn** [[scripts-vault_backlink_audit-py-run_retrieval_signals]]`(wiki_slugs, incoming, outgoing) → None`
- **fn** [[scripts-vault_backlink_audit-py-main]]`() → None`

## Import Statements

```python
import argparse
import json
import sys
import re
from pathlib import Path
from datetime import datetime
from datetime import timezone
```
