---
type: codebase-file
path: core/tool_mastery_author_agent/reconcile.py
module: core.tool_mastery_author_agent.reconcile
lines: 172
size: 5601
generated: 2026-04-12
---

# core/tool_mastery_author_agent/reconcile.py

Reconcile drafts with existing on-disk skill files.

Policy: never destructively overwrite human-authored content unless
``force_rewrite=True``. We detect whether an existing file is a
fresh scaffold (all placeholders) or real human work, and behave
...

**Lines:** 172 | **Size:** 5,601 bytes

## Contains

- **class** [[core-tool_mastery_author_agent-reconcile-py-ReconcilePlan]] — 0 methods
- **fn** [[core-tool_mastery_author_agent-reconcile-py-_looks_like_scaffold]]`(bp_text) → bool`
- **fn** [[core-tool_mastery_author_agent-reconcile-py-plan_reconciliation]]`(tool_slug) → ReconcilePlan`
- **fn** [[core-tool_mastery_author_agent-reconcile-py-run_scaffold]]`(tool_slug) → tuple[bool, str]`
- **fn** [[core-tool_mastery_author_agent-reconcile-py-replace_body_preserving_frontmatter]]`(path, new_body) → None`

## Import Statements

```python
from __future__ import annotations
import subprocess
from dataclasses import dataclass
from pathlib import Path
from paths import SCAFFOLD_SCRIPT
from paths import SKILLS_TOOLS_DIR
```
