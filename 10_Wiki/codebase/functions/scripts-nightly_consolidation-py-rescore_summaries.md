---
type: codebase-function
file: scripts/nightly_consolidation.py
line: 167
generated: 2026-04-11
---

# rescore_summaries

**File:** [[scripts-nightly_consolidation-py]] | **Line:** 167
**Signature:** `rescore_summaries(dry_run) → dict`

Rescore all existing summaries with current salience weights.

Useful after tuning weights — updates frontmatter in place.

## Calls

- [[scripts-nightly_consolidation-py-_dump_frontmatter]]
- [[scripts-nightly_consolidation-py-_parse_frontmatter]]

## Called By

- [[scripts-nightly_consolidation-py-main]]
