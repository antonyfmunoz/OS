---
type: codebase-file
path: core/tool_mastery_research_agent/handoff.py
module: core.tool_mastery_research_agent.handoff
lines: 124
size: 3756
generated: 2026-04-11
---

# core/tool_mastery_research_agent/handoff.py

Safe metadata handoff for the Tool Mastery Research Agent.

The only thing this module is allowed to mutate is existing SKILL.md
frontmatter fields that can be derived unambiguously from the research
run:
...

**Lines:** 124 | **Size:** 3,756 bytes

## Contains

- **fn** [[core-tool_mastery_research_agent-handoff-py-_top_source_url]]`(artifact) → str | None`
- **fn** [[core-tool_mastery_research_agent-handoff-py-_update_frontmatter_field]]`(text, key, value) → tuple[str, bool]`
- **fn** [[core-tool_mastery_research_agent-handoff-py-apply_safe_metadata]]`(tool_slug, artifact) → dict[str, object]`

## Import Statements

```python
from __future__ import annotations
from datetime import datetime
from datetime import timezone
from pathlib import Path
from models import FetchedSource
from models import FetchStatus
from models import ResearchArtifact
from paths import SKILLS_TOOLS_DIR
```
