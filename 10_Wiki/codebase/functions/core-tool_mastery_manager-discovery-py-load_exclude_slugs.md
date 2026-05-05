---
type: codebase-function
file: core/tool_mastery_manager/discovery.py
line: 226
generated: 2026-04-12
---

# load_exclude_slugs

**File:** [[core-tool_mastery_manager-discovery-py]] | **Line:** 226
**Signature:** `load_exclude_slugs(path) → dict[str, str]`

Load the exclusion list from config/tool_mastery_exclude.yaml.

Returns a dict mapping normalised slug -> reason string. Reasons are
retained so the Manager can log *why* a slug was excluded when it
filters discovery output.
...

## Calls

- [[core-tool_mastery_manager-discovery-py-normalise_slug]]

## Called By

- [[core-tool_mastery_manager-discovery-py-discover_all]]
