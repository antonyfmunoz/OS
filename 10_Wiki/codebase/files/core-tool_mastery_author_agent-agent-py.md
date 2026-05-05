---
type: codebase-file
path: core/tool_mastery_author_agent/agent.py
module: core.tool_mastery_author_agent.agent
lines: 189
size: 6593
generated: 2026-04-12
---

# core/tool_mastery_author_agent/agent.py

Author Agent orchestrator.

Loader → mapping → drafting → reconcile → verify → final state.

Public entry: ``author(request) -> AuthorResult``.

**Lines:** 189 | **Size:** 6,593 bytes

## Used By

- [[scripts-tool_mastery_author-py]]

## Contains

- **fn** [[core-tool_mastery_author_agent-agent-py-_iso_now]]`() → str`
- **fn** [[core-tool_mastery_author_agent-agent-py-_display_name]]`(slug) → str`
- **fn** [[core-tool_mastery_author_agent-agent-py-author]]`(request) → AuthorResult`
- **fn** [[core-tool_mastery_author_agent-agent-py-_write_provenance]]`(result, run_dir, tool_slug, drafts, preserved) → None`

## Import Statements

```python
from __future__ import annotations
import json
from datetime import datetime
from datetime import timezone
from pathlib import Path
from draft import build_drafts
from draft import render_best_practices
from draft import render_skill_body
from loader import load_artifact
from mapping import map_sections
from models import AuthoredProvenance
from models import AuthorRequest
from models import AuthorResult
from models import AuthorStatus
from reconcile import plan_reconciliation
from reconcile import replace_body_preserving_frontmatter
from reconcile import run_scaffold
from verify import verify_skill
```
