---
type: codebase-file
path: scripts/sync_skills_to_neon.py
module: scripts.sync_skills_to_neon
lines: 156
size: 5065
tags: [entry-point]
generated: 2026-04-12
---

# scripts/sync_skills_to_neon.py

> **ENTRY POINT** — Contains `if __name__` or server start.

sync_skills_to_neon.py — Canonical Tool Mastery Engine → Neon sync.

Scans /opt/OS/skills/tools/, extracts metadata + full SKILL.md content,
upserts rows into the `skills` table under the active org_id.

...

**Lines:** 156 | **Size:** 5,065 bytes

## Depends On

- [[eos_ai-context-py]]
- [[eos_ai-db-py]]
- [[scripts-_tme_common-py]]

## Contains

- **fn** [[scripts-sync_skills_to_neon-py-_raw_text]]`(rec) → str`
- **fn** [[scripts-sync_skills_to_neon-py-_fetch_existing]]`(cur, org_id, name) → tuple[str, str, int] | None`
- **fn** [[scripts-sync_skills_to_neon-py-_sync_one]]`(cur, org_id, rec, dry_run) → str`
- **fn** [[scripts-sync_skills_to_neon-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import argparse
import sys
import uuid
from pathlib import Path
from scripts._tme_common import SkillRecord
from scripts._tme_common import all_skill_slugs
from scripts._tme_common import eprint
from scripts._tme_common import load_skill
from eos_ai.context import load_context_from_env
from eos_ai.db import get_conn
```
