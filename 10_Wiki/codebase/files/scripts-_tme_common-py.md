---
type: codebase-file
path: scripts/_tme_common.py
module: scripts._tme_common
lines: 230
size: 6707
generated: 2026-04-11
---

# scripts/_tme_common.py

Shared helpers for Tool Mastery Engine system scripts.

One place for:
- Skill directory discovery
- Robust YAML frontmatter parsing (no fragile regex)
...

**Lines:** 230 | **Size:** 6,707 bytes

## Used By

- [[core-tool_mastery_manager-coverage-py]]
- [[scripts-build_skill_graph-py]]
- [[scripts-check_skill_staleness-py]]
- [[scripts-query_skills-py]]
- [[scripts-sync_skills_to_neon-py]]
- [[scripts-verify_tool_skill-py]]

## Contains

- **class** [[scripts-_tme_common-py-SkillRecord]] — 7 methods
- **fn** [[scripts-_tme_common-py-_split_frontmatter]]`(text) → tuple[dict[str, Any], str, str | None]`
- **fn** [[scripts-_tme_common-py-load_skill]]`(slug, tools_dir) → SkillRecord`
- **fn** [[scripts-_tme_common-py-all_skill_slugs]]`(tools_dir) → list[str]`
- **fn** [[scripts-_tme_common-py-load_all_skills]]`(tools_dir) → list[SkillRecord]`
- **fn** [[scripts-_tme_common-py-section_present]]`(body, heading) → bool`
- **fn** [[scripts-_tme_common-py-days_since]]`(d, today) → int`
- **fn** [[scripts-_tme_common-py-freshness_window]]`(speed) → int`
- **fn** [[scripts-_tme_common-py-eprint]]`() → None`

## Import Statements

```python
from __future__ import annotations
import sys
from dataclasses import dataclass
from dataclasses import field
from datetime import date
from datetime import datetime
from pathlib import Path
from typing import Any
import yaml
```
