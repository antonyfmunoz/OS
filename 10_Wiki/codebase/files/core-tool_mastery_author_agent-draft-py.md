---
type: codebase-file
path: core/tool_mastery_author_agent/draft.py
module: core.tool_mastery_author_agent.draft
lines: 452
size: 16332
generated: 2026-05-07
---

# core/tool_mastery_author_agent/draft.py

Draft authored section content from SectionEvidence.

Phase 6 — Author Intelligence. Takes the evidence output of mapping.py
and renders it as markdown. Pattern-priority: structured signals (install
commands, setup flows, JSON schema fields, workflow sequences) are
...

**Lines:** 452 | **Size:** 16,332 bytes

## Used By

- [[scripts-measure_phase8_batch-py]]

## Contains

- **fn** [[core-tool_mastery_author_agent-draft-py-_label_for]]`(kind) → str`
- **fn** [[core-tool_mastery_author_agent-draft-py-_render_ordered_list]]`(excerpt) → list[str]`
- **fn** [[core-tool_mastery_author_agent-draft-py-_render_pattern]]`(pattern) → list[str]`
- **fn** [[core-tool_mastery_author_agent-draft-py-_render_prose_excerpt]]`(excerpt, index) → list[str]`
- **fn** [[core-tool_mastery_author_agent-draft-py-_looks_marketing]]`(text) → bool`
- **fn** [[core-tool_mastery_author_agent-draft-py-_render_sourced_content]]`(ev) → tuple[str, str, int]`
- **fn** [[core-tool_mastery_author_agent-draft-py-_render_uncovered_content]]`(ev) → str`
- **fn** [[core-tool_mastery_author_agent-draft-py-_has_usable_evidence]]`(ev) → bool`
- **fn** [[core-tool_mastery_author_agent-draft-py-build_drafts]]`(evidence) → list[SectionDraft]`
- **fn** [[core-tool_mastery_author_agent-draft-py-render_best_practices]]`(tool_slug, display_name, drafts, generated_at) → str`
- **fn** [[core-tool_mastery_author_agent-draft-py-_status_badge]]`(draft) → str`
- **fn** [[core-tool_mastery_author_agent-draft-py-render_skill_body]]`(tool_slug, display_name, drafts) → str`

## Import Statements

```python
from __future__ import annotations
from mapping import SectionEvidence
from mapping import TME_SECTIONS
from models import SectionDraft
```
