---
type: codebase-file
path: scripts/query_skills.py
module: scripts.query_skills
lines: 213
size: 7101
tags: [entry-point]
generated: 2026-04-12
---

# scripts/query_skills.py

> **ENTRY POINT** — Contains `if __name__` or server start.

query_skills.py — Tool Mastery Engine CLI registry.

Practical queries over the tool skill base. Uses the common loader,
the staleness logic, and the dependency graph JSON (if built).

...

**Lines:** 213 | **Size:** 7,101 bytes

## Depends On

- [[scripts-_tme_common-py]]
- [[scripts-check_skill_staleness-py]]

## Contains

- **fn** [[scripts-query_skills-py-_matches]]`(rec, needle) → bool`
- **fn** [[scripts-query_skills-py-cmd_search]]`(args) → int`
- **fn** [[scripts-query_skills-py-cmd_show]]`(args) → int`
- **fn** [[scripts-query_skills-py-_load_graph]]`() → dict | None`
- **fn** [[scripts-query_skills-py-cmd_deps]]`(args) → int`
- **fn** [[scripts-query_skills-py-cmd_stale]]`(args) → int`
- **fn** [[scripts-query_skills-py-cmd_unverified]]`(_) → int`
- **fn** [[scripts-query_skills-py-cmd_domain]]`(args) → int`
- **fn** [[scripts-query_skills-py-cmd_list]]`(_) → int`
- **fn** [[scripts-query_skills-py-cmd_count]]`(_) → int`
- **fn** [[scripts-query_skills-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import argparse
import json
import subprocess
import sys
from datetime import date
from pathlib import Path
from scripts._tme_common import SkillRecord
from scripts._tme_common import all_skill_slugs
from scripts._tme_common import load_all_skills
from scripts._tme_common import load_skill
from scripts.check_skill_staleness import _assess
```
