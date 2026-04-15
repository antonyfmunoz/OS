---
type: codebase-file
path: core/tool_mastery_manager/discovery.py
module: core.tool_mastery_manager.discovery
lines: 333
size: 11138
generated: 2026-04-12
---

# core/tool_mastery_manager/discovery.py

Tool discovery for the Tool Mastery Manager.

Four deterministic sources, in priority order:

    (i)   skills_dir   — /opt/OS/skills/tools/ existing slugs
...

**Lines:** 333 | **Size:** 11,138 bytes

## Contains

- **fn** [[core-tool_mastery_manager-discovery-py-normalise_slug]]`(raw) → str`
- **fn** [[core-tool_mastery_manager-discovery-py-_title_case]]`(slug) → str`
- **fn** [[core-tool_mastery_manager-discovery-py-discover_skills_dir]]`(tools_dir) → list[ToolRef]`
- **fn** [[core-tool_mastery_manager-discovery-py-discover_explicit]]`(names) → list[ToolRef]`
- **fn** [[core-tool_mastery_manager-discovery-py-discover_seed_list]]`(path) → list[ToolRef]`
- **fn** [[core-tool_mastery_manager-discovery-py-discover_claude_json]]`(path) → list[ToolRef]`
- **fn** [[core-tool_mastery_manager-discovery-py-_merge]]`(refs_lists) → list[ToolRef]`
- **fn** [[core-tool_mastery_manager-discovery-py-load_exclude_slugs]]`(path) → dict[str, str]`
- **fn** [[core-tool_mastery_manager-discovery-py-_apply_exclusions]]`(refs, exclusions) → list[ToolRef]`
- **fn** [[core-tool_mastery_manager-discovery-py-discover_all]]`() → list[ToolRef]`

## Import Statements

```python
from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Iterable
from models import DiscoverySource
from models import ToolRef
from paths import CLAUDE_JSON
from paths import EXCLUDE_LIST_PATH
from paths import SEED_LIST_PATH
from paths import SKILLS_TOOLS_DIR
```
