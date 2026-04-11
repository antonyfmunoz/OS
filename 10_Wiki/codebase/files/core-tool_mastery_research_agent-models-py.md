---
type: codebase-file
path: core/tool_mastery_research_agent/models.py
module: core.tool_mastery_research_agent.models
lines: 210
size: 6934
generated: 2026-04-11
---

# core/tool_mastery_research_agent/models.py

Data types for the Tool Mastery Research Agent.

Everything here is JSON-serialisable (str/int/float/bool/list/dict) via
dataclasses.asdict() so that research runs can be persisted to disk
without custom encoders, matching the Manager convention.

**Lines:** 210 | **Size:** 6,934 bytes

## Contains

- **class** [[core-tool_mastery_research_agent-models-py-ResearchMode]] — 0 methods
- **class** [[core-tool_mastery_research_agent-models-py-ResearchStatus]] — 0 methods
- **class** [[core-tool_mastery_research_agent-models-py-SourceTier]] — 0 methods
- **class** [[core-tool_mastery_research_agent-models-py-FetchStatus]] — 0 methods
- **class** [[core-tool_mastery_research_agent-models-py-ResearchRequest]] — 1 methods
- **class** [[core-tool_mastery_research_agent-models-py-SourceRef]] — 1 methods
- **class** [[core-tool_mastery_research_agent-models-py-SourcePlan]] — 2 methods
- **class** [[core-tool_mastery_research_agent-models-py-FetchedSource]] — 1 methods
- **class** [[core-tool_mastery_research_agent-models-py-ResearchArtifact]] — 1 methods
- **class** [[core-tool_mastery_research_agent-models-py-ResearchResult]] — 1 methods

## Import Statements

```python
from __future__ import annotations
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any
```
