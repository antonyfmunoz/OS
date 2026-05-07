---
type: codebase-file
path: scripts/check_skill_staleness.py
module: scripts.check_skill_staleness
lines: 170
size: 5580
tags: [entry-point]
generated: 2026-05-07
---

# scripts/check_skill_staleness.py

> **ENTRY POINT** — Contains `if __name__` or server start.

check_skill_staleness.py — Tool Mastery Engine staleness audit.

Compares each skill's `last_researched` date against the freshness
window for its `speed_category` (fast=30d, medium=60d, stable=90d).
Reports STALE, NEAR_STALE (>= 80% of window), MISSING_DATE, or FRESH.
...

**Lines:** 170 | **Size:** 5,580 bytes

## Depends On

- [[scripts-_tme_common-py]]

## Used By

- [[core-tool_mastery_manager-coverage-py]]
- [[scripts-query_skills-py]]

## Contains

- **class** [[scripts-check_skill_staleness-py-StalenessRow]] — 1 methods
- **fn** [[scripts-check_skill_staleness-py-_assess]]`(rec, today) → StalenessRow`
- **fn** [[scripts-check_skill_staleness-py-_render_text]]`(rows) → None`
- **fn** [[scripts-check_skill_staleness-py-_render_markdown]]`(rows, today) → None`
- **fn** [[scripts-check_skill_staleness-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import argparse
import json
import sys
from dataclasses import dataclass
from datetime import date
from scripts._tme_common import NEAR_STALE_FRACTION
from scripts._tme_common import SkillRecord
from scripts._tme_common import all_skill_slugs
from scripts._tme_common import days_since
from scripts._tme_common import freshness_window
from scripts._tme_common import load_skill
```
