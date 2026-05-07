---
type: codebase-file
path: core/tool_mastery_manager/active_tool_context.py
module: core.tool_mastery_manager.active_tool_context
lines: 151
size: 5563
generated: 2026-05-07
---

# core/tool_mastery_manager/active_tool_context.py

Active Tool Context for the Tool Mastery Engine.

Tracks active tools, capabilities, mastery packs, runtimes, and
governance constraints for an ongoing task. Persists until the task
changes or a better tool is selected.
...

**Lines:** 151 | **Size:** 5,563 bytes

## Contains

- **class** [[core-tool_mastery_manager-active_tool_context-py-ActiveToolContext]] — 1 methods
- **fn** [[core-tool_mastery_manager-active_tool_context-py-_now_iso]]`() → str`
- **fn** [[core-tool_mastery_manager-active_tool_context-py-create_active_tool_context]]`(task_summary, resolution, task_id) → ActiveToolContext`
- **fn** [[core-tool_mastery_manager-active_tool_context-py-update_active_tool_context]]`(context, new_resolution) → ActiveToolContext`
- **fn** [[core-tool_mastery_manager-active_tool_context-py-should_continue_context]]`(context, new_user_intent) → bool`
- **fn** [[core-tool_mastery_manager-active_tool_context-py-should_switch_context]]`(context, new_resolution) → bool`
- **fn** [[core-tool_mastery_manager-active_tool_context-py-summarize_active_tool_context]]`(context) → str`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from typing import Any
from tool_mastery_resolver import ToolMasteryResolution
from tool_mastery_resolver import detect_tool_mentions
```
