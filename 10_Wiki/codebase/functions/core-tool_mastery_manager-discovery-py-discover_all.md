---
type: codebase-function
file: core/tool_mastery_manager/discovery.py
line: 304
generated: 2026-04-11
---

# discover_all

**File:** [[core-tool_mastery_manager-discovery-py]] | **Line:** 304
**Signature:** `discover_all() → list[ToolRef]`

Run every enabled discovery source and return a merged ToolRef list.

When `apply_exclusions=True` (default), slugs declared in
`config/tool_mastery_exclude.yaml` are filtered out after the merge.
This is how the Manager suppresses ghost MCP entries (uninstalled
...

## Calls

- [[core-tool_mastery_manager-discovery-py-_apply_exclusions]]
- [[core-tool_mastery_manager-discovery-py-_merge]]
- [[core-tool_mastery_manager-discovery-py-discover_claude_json]]
- [[core-tool_mastery_manager-discovery-py-discover_explicit]]
- [[core-tool_mastery_manager-discovery-py-discover_seed_list]]
- [[core-tool_mastery_manager-discovery-py-discover_skills_dir]]
- [[core-tool_mastery_manager-discovery-py-load_exclude_slugs]]
