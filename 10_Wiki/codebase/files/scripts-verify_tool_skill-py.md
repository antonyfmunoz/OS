---
type: codebase-file
path: scripts/verify_tool_skill.py
module: scripts.verify_tool_skill
lines: 189
size: 6116
tags: [entry-point]
generated: 2026-04-12
---

# scripts/verify_tool_skill.py

> **ENTRY POINT** — Contains `if __name__` or server start.

verify_tool_skill.py — Tool Mastery Engine verifier / linter.

Replaces the brittle ad-hoc regex checks from the in-skill verification
block with a real YAML-aware linter.

...

**Lines:** 189 | **Size:** 6,116 bytes

## Depends On

- [[scripts-_tme_common-py]]

## Used By

- [[core-tool_mastery_manager-coverage-py]]

## Contains

- **class** [[scripts-verify_tool_skill-py-VerifyResult]] — 0 methods
- **fn** [[scripts-verify_tool_skill-py-_check]]`(rec) → VerifyResult`
- **fn** [[scripts-verify_tool_skill-py-_render]]`(results, quiet) → None`
- **fn** [[scripts-verify_tool_skill-py-_render_json]]`(results) → None`
- **fn** [[scripts-verify_tool_skill-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import argparse
import json
import re
import sys
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from scripts._tme_common import MIN_BP_CHARS
from scripts._tme_common import MIN_SKILL_CHARS
from scripts._tme_common import REQUIRED_BP_SECTIONS
from scripts._tme_common import REQUIRED_SKILL_SECTIONS
from scripts._tme_common import SkillRecord
from scripts._tme_common import all_skill_slugs
from scripts._tme_common import load_skill
from scripts._tme_common import section_present
```
