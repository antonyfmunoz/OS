---
type: codebase-function
file: core/tool_mastery_author_agent/reconcile.py
line: 148
generated: 2026-04-11
---

# replace_body_preserving_frontmatter

**File:** [[core-tool_mastery_author_agent-reconcile-py]] | **Line:** 148
**Signature:** `replace_body_preserving_frontmatter(path, new_body) → None`

Overwrite the body of a markdown file while keeping its YAML frontmatter.

Used to rewrite a scaffolded SKILL.md without touching the
frontmatter that the research agent's handoff just updated
(source_url, last_researched).
