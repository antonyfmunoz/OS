---
type: codebase-function
file: core/tool_mastery_manager/discovery.py
line: 142
generated: 2026-04-12
---

# discover_claude_json

**File:** [[core-tool_mastery_manager-discovery-py]] | **Line:** 142
**Signature:** `discover_claude_json(path) → list[ToolRef]`

Source (iv): MCP servers declared in ~/.claude.json.

Reads both the top-level `mcpServers` block AND the union of
per-project `mcpServers` blocks. MCP server names may contain
hyphens and mixed case; we normalise to snake_case the same way as
...

## Calls

- [[core-tool_mastery_manager-discovery-py-_title_case]]
- [[core-tool_mastery_manager-discovery-py-normalise_slug]]

## Called By

- [[core-tool_mastery_manager-discovery-py-discover_all]]
