---
type: codebase-function
file: core/action_system/tme.py
line: 57
generated: 2026-05-07
---

# ensure_tool_mastery

**File:** [[core-action_system-tme-py]] | **Line:** 57
**Signature:** `ensure_tool_mastery(tool) → dict[str, Any]`

Active mastery assurance for a tool.

Delegates to `core.tool_mastery_manager.ensure_mastery`. Import is
deferred to call time so module-load remains side-effect-free and
circular imports are impossible (the Manager itself depends on
...
