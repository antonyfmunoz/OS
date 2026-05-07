---
type: codebase-file
path: core/tool_mastery_author_agent/models.py
module: core.tool_mastery_author_agent.models
lines: 141
size: 4874
generated: 2026-05-07
---

# core/tool_mastery_author_agent/models.py

Data types for the Tool Mastery Author Agent.

All JSON-serialisable via asdict() so runs can be persisted alongside
the research run directory.

**Lines:** 141 | **Size:** 4,874 bytes

## Used By

- [[scripts-tool_mastery_author-py]]

## Contains

- **class** [[core-tool_mastery_author_agent-models-py-AuthorStatus]] — 0 methods
- **class** [[core-tool_mastery_author_agent-models-py-AuthorRequest]] — 1 methods
- **class** [[core-tool_mastery_author_agent-models-py-SectionDraft]] — 1 methods
- **class** [[core-tool_mastery_author_agent-models-py-AuthoredProvenance]] — 1 methods
- **class** [[core-tool_mastery_author_agent-models-py-AuthorResult]] — 1 methods

## Import Statements

```python
from __future__ import annotations
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any
```
