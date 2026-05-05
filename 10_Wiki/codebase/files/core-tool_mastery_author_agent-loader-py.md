---
type: codebase-file
path: core/tool_mastery_author_agent/loader.py
module: core.tool_mastery_author_agent.loader
lines: 219
size: 7867
generated: 2026-04-12
---

# core/tool_mastery_author_agent/loader.py

Research artifact loader.

Reads a research_artifact.json + its on-disk raw captures into
normalised in-memory structures the mapper can reason about.

...

**Lines:** 219 | **Size:** 7,867 bytes

## Used By

- [[scripts-measure_phase8_batch-py]]

## Contains

- **class** [[core-tool_mastery_author_agent-loader-py-RawCapture]] — 0 methods
- **class** [[core-tool_mastery_author_agent-loader-py-LoadedArtifact]] — 2 methods
- **fn** [[core-tool_mastery_author_agent-loader-py-sanitize_text]]`(text) → str`
- **fn** [[core-tool_mastery_author_agent-loader-py-_symbol_density]]`(s) → float`
- **fn** [[core-tool_mastery_author_agent-loader-py-_read_text_safely]]`(path, max_bytes) → tuple[str, str | None]`
- **fn** [[core-tool_mastery_author_agent-loader-py-load_artifact]]`(artifact_path) → LoadedArtifact`

## Import Statements

```python
from __future__ import annotations
import json
import re
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Any
```
