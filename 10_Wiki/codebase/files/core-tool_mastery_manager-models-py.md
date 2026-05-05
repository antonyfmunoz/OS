---
type: codebase-file
path: core/tool_mastery_manager/models.py
module: core.tool_mastery_manager.models
lines: 122
size: 4162
generated: 2026-04-12
---

# core/tool_mastery_manager/models.py

Data types for the Tool Mastery Manager.

Kept deliberately small. Everything is JSON-serialisable so coverage
reports and ensure results can be written to disk as backlog artifacts
without custom encoders.

**Lines:** 122 | **Size:** 4,162 bytes

## Used By

- [[scripts-tool_mastery_manager-py]]

## Contains

- **class** [[core-tool_mastery_manager-models-py-CoverageStatus]] — 1 methods
- **class** [[core-tool_mastery_manager-models-py-DiscoverySource]] — 0 methods
- **class** [[core-tool_mastery_manager-models-py-ToolRef]] — 1 methods
- **class** [[core-tool_mastery_manager-models-py-CoverageReport]] — 1 methods
- **class** [[core-tool_mastery_manager-models-py-ManagerPlan]] — 1 methods
- **class** [[core-tool_mastery_manager-models-py-EnsureResult]] — 1 methods

## Import Statements

```python
from __future__ import annotations
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any
```
