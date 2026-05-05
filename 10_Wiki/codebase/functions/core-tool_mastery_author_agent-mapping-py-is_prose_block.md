---
type: codebase-function
file: core/tool_mastery_author_agent/mapping.py
line: 279
generated: 2026-04-12
---

# is_prose_block

**File:** [[core-tool_mastery_author_agent-mapping-py]] | **Line:** 279
**Signature:** `is_prose_block(text) → bool`

Heuristic: does this chunk look like human-readable prose?

The goal is to reject code, JSON blobs, config snippets, nav-menu
spam, and feature-flag arrays. False negatives are acceptable — we
would rather mark a section uncovered than source it from garbage.

## Called By

- [[core-tool_mastery_author_agent-mapping-py-_excerpt_from_block]]
- [[core-tool_mastery_author_agent-mapping-py-_split_prose_blocks]]
