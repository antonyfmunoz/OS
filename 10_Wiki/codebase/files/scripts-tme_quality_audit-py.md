---
type: codebase-file
path: scripts/tme_quality_audit.py
module: scripts.tme_quality_audit
lines: 246
size: 8303
tags: [entry-point]
generated: 2026-05-07
---

# scripts/tme_quality_audit.py

> **ENTRY POINT** — Contains `if __name__` or server start.

TME Quality Audit — checks content depth, not just structure.

Validates that tool skills meet creator-level quality standards:
- Frontmatter completeness (10 required fields)
- Section presence (19 sections in best_practices.md)
...

**Lines:** 246 | **Size:** 8,303 bytes

## Depends On

- [[scripts-_tme_common-py]]

## Contains

- **fn** [[scripts-tme_quality_audit-py-audit_skill]]`(slug) → dict`
- **fn** [[scripts-tme_quality_audit-py-main]]`() → int`

## Import Statements

```python
import os
import re
import sys
import json
import argparse
from scripts._tme_common import load_all_skills
from scripts._tme_common import load_skill
from scripts._tme_common import all_skill_slugs
from scripts._tme_common import section_present
from scripts._tme_common import REQUIRED_BP_SECTIONS
```
