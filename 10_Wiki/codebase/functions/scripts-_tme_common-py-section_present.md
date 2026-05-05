---
type: codebase-function
file: scripts/_tme_common.py
line: 188
generated: 2026-04-12
---

# section_present

**File:** [[scripts-_tme_common-py]] | **Line:** 188
**Signature:** `section_present(body, heading) → bool`

Return True if `body` contains an H2/H3 heading whose visible text
equals `heading`, ignoring:
  - leading `## ` / `### ` depth
  - optional `N.` / `N)` numbering
  - trailing punctuation and any text after the required name
...

## Called By

- [[scripts-verify_tool_skill-py-_check]]
