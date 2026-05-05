---
type: codebase-function
file: core/tool_mastery_author_agent/draft.py
line: 283
generated: 2026-04-12
---

# build_drafts

**File:** [[core-tool_mastery_author_agent-draft-py]] | **Line:** 283
**Signature:** `build_drafts(evidence) → list[SectionDraft]`

Convert every piece of evidence into a SectionDraft.

Phase 6 honest-fallback rule: a section with zero patterns AND no
non-marketing prose remains uncovered even if ``ev.sourced`` is
True. We do not force completion.

## Calls

- [[core-tool_mastery_author_agent-draft-py-_has_usable_evidence]]
- [[core-tool_mastery_author_agent-draft-py-_looks_marketing]]
- [[core-tool_mastery_author_agent-draft-py-_render_sourced_content]]
- [[core-tool_mastery_author_agent-draft-py-_render_uncovered_content]]

## Called By

- [[scripts-measure_phase8_batch-py-measure_tool]]
