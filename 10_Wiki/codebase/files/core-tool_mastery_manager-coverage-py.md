---
type: codebase-file
path: core/tool_mastery_manager/coverage.py
module: core.tool_mastery_manager.coverage
lines: 120
size: 4254
generated: 2026-04-12
---

# core/tool_mastery_manager/coverage.py

Unified coverage evaluator for the Tool Mastery Manager.

This is the composition layer. It calls existing TME utilities and
collapses their per-concern verdicts into a single CoverageStatus per
tool. No verification or staleness logic is duplicated here — if the
...

**Lines:** 120 | **Size:** 4,254 bytes

## Depends On

- [[scripts-_tme_common-py]]
- [[scripts-check_skill_staleness-py]]
- [[scripts-verify_tool_skill-py]]

## Used By

- [[scripts-tool_mastery_manager-py]]
- [[scripts-tool_mastery_research_dispatcher-py]]

## Contains

- **fn** [[core-tool_mastery_manager-coverage-py-evaluate_coverage]]`(slug) → CoverageReport`
- **fn** [[core-tool_mastery_manager-coverage-py-evaluate_many]]`(slugs) → list[CoverageReport]`

## Import Statements

```python
from __future__ import annotations
import sys
from datetime import date
from scripts._tme_common import load_skill
from scripts.check_skill_staleness import _assess
from scripts.verify_tool_skill import _check
from models import CoverageReport
from models import CoverageStatus
from paths import SKILLS_TOOLS_DIR
```
