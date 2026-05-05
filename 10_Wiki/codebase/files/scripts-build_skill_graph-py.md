---
type: codebase-file
path: scripts/build_skill_graph.py
module: scripts.build_skill_graph
lines: 217
size: 7118
tags: [entry-point]
generated: 2026-04-12
---

# scripts/build_skill_graph.py

> **ENTRY POINT** — Contains `if __name__` or server start.

build_skill_graph.py — Tool Mastery Engine skill dependency graph.

Builds a cross-reference graph between tool skills by scanning each
skill's SKILL.md + references/best_practices.md for mentions of
*other* tool slugs. Mentions come from:
...

**Lines:** 217 | **Size:** 7,118 bytes

## Depends On

- [[scripts-_tme_common-py]]

## Contains

- **fn** [[scripts-build_skill_graph-py-_tokens_for]]`(rec) → set[str]`
- **fn** [[scripts-build_skill_graph-py-_find_refs]]`(source, all_tokens) → set[str]`
- **fn** [[scripts-build_skill_graph-py-build_graph]]`(skills) → dict`
- **fn** [[scripts-build_skill_graph-py-render_markdown]]`(graph) → str`
- **fn** [[scripts-build_skill_graph-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from scripts._tme_common import SkillRecord
from scripts._tme_common import all_skill_slugs
from scripts._tme_common import load_all_skills
from scripts._tme_common import load_skill
```
