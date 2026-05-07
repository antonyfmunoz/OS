---
type: codebase-file
path: core/tool_mastery_manager/tool_mastery_resolver.py
module: core.tool_mastery_manager.tool_mastery_resolver
lines: 323
size: 10953
generated: 2026-05-07
---

# core/tool_mastery_manager/tool_mastery_resolver.py

Natural Language Tool Mastery Resolver.

Detects tools, capabilities, and runtimes from natural language text
and resolves the required Tool Mastery Packs. No slash commands needed.

...

**Lines:** 323 | **Size:** 10,953 bytes

## Contains

- **class** [[core-tool_mastery_manager-tool_mastery_resolver-py-ResolvedToolMention]] — 1 methods
- **class** [[core-tool_mastery_manager-tool_mastery_resolver-py-ResolvedCapabilityMention]] — 1 methods
- **class** [[core-tool_mastery_manager-tool_mastery_resolver-py-ResolvedMasteryPack]] — 1 methods
- **class** [[core-tool_mastery_manager-tool_mastery_resolver-py-ToolMasteryResolution]] — 1 methods
- **fn** [[core-tool_mastery_manager-tool_mastery_resolver-py-detect_tool_mentions]]`(text, known_tools) → list[ResolvedToolMention]`
- **fn** [[core-tool_mastery_manager-tool_mastery_resolver-py-detect_capability_mentions]]`(text) → list[ResolvedCapabilityMention]`
- **fn** [[core-tool_mastery_manager-tool_mastery_resolver-py-_detect_runtimes]]`(text) → list[str]`
- **fn** [[core-tool_mastery_manager-tool_mastery_resolver-py-infer_required_mastery_packs]]`(text, known_tools, active_context) → list[ResolvedMasteryPack]`
- **fn** [[core-tool_mastery_manager-tool_mastery_resolver-py-resolve_mastery_for_task]]`(text, known_tools, active_context) → ToolMasteryResolution`
- **fn** [[core-tool_mastery_manager-tool_mastery_resolver-py-should_reuse_active_tool_context]]`(text, active_context) → bool`
- **fn** [[core-tool_mastery_manager-tool_mastery_resolver-py-explain_mastery_resolution]]`(resolution) → str`

## Import Statements

```python
from __future__ import annotations
import re
from dataclasses import dataclass
from dataclasses import field
from typing import Any
```
