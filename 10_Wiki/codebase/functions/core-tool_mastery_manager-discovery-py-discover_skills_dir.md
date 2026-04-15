---
type: codebase-function
file: core/tool_mastery_manager/discovery.py
line: 43
generated: 2026-04-12
---

# discover_skills_dir

**File:** [[core-tool_mastery_manager-discovery-py]] | **Line:** 43
**Signature:** `discover_skills_dir(tools_dir) → list[ToolRef]`

Source (i): every directory under skills/tools/ that has a SKILL.md.

This is not "tools we know about" in an abstract sense — it is the
concrete set of tools that already have *some* coverage (valid or
not). The coverage evaluator decides READY vs INVALID.

## Calls

- [[core-tool_mastery_manager-discovery-py-_title_case]]

## Called By

- [[core-tool_mastery_manager-discovery-py-discover_all]]
