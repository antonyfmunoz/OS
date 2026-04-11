---
type: codebase-function
file: core/tool_mastery_author_agent/draft.py
line: 403
generated: 2026-04-11
---

# render_skill_body

**File:** [[core-tool_mastery_author_agent-draft-py]] | **Line:** 403
**Signature:** `render_skill_body(tool_slug, display_name, drafts) → str`

Render the body (after frontmatter) for a freshly scaffolded SKILL.md.

Only used when reconcile.py decides to populate a scaffold's
SKILL.md body from scratch. Existing high-quality SKILL.md files
are preserved — see reconcile.should_populate_skill_md.
