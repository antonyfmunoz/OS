---
type: codebase-function
file: core/tool_mastery_author_agent/draft.py
line: 328
generated: 2026-05-07
---

# render_best_practices

**File:** [[core-tool_mastery_author_agent-draft-py]] | **Line:** 328
**Signature:** `render_best_practices(tool_slug, display_name, drafts, generated_at) → str`

Render a complete best_practices.md from drafts.

The output satisfies the verifier's 19-section requirement by
always emitting all TME_SECTIONS as H2 headings in canonical
order. Uncovered sections contain honest placeholders, not
...

## Calls

- [[core-tool_mastery_author_agent-draft-py-_status_badge]]
