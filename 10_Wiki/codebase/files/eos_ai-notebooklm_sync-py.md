---
type: codebase-file
path: eos_ai/notebooklm_sync.py
module: eos_ai.notebooklm_sync
lines: 314
size: 11501
generated: 2026-04-11
---

# eos_ai/notebooklm_sync.py

NotebookLMSync — bidirectional sync between Neon and NotebookLM.

Data flows:
  Neon → NotebookLM: pipeline data, world pulse reports, founder profile docs
  NotebookLM → Neon: query results stored as notebooklm_insight events for DEX
...

**Lines:** 314 | **Size:** 11,501 bytes

## Depends On

- [[eos_ai-context-py]]

## Contains

- **class** [[eos_ai-notebooklm_sync-py-NotebookConfig]] — 0 methods
- **class** [[eos_ai-notebooklm_sync-py-NotebookLMSync]] — 9 methods

## Import Statements

```python
import json
import os
import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from pathlib import Path
from eos_ai.context import EOSContext
```
