---
type: codebase-file
path: core/tool_mastery_author_agent/verify.py
module: core.tool_mastery_author_agent.verify
lines: 77
size: 2339
generated: 2026-04-12
---

# core/tool_mastery_author_agent/verify.py

Run verify_tool_skill.py against an authored tool.

We shell out to the canonical verifier rather than reimplementing
its logic. The Author Agent's output is NEVER trusted on its own
word — the verifier is the ground truth for READY status.

**Lines:** 77 | **Size:** 2,339 bytes

## Contains

- **class** [[core-tool_mastery_author_agent-verify-py-VerifyReport]] — 0 methods
- **fn** [[core-tool_mastery_author_agent-verify-py-verify_skill]]`(tool_slug) → VerifyReport`

## Import Statements

```python
from __future__ import annotations
import json
import subprocess
from dataclasses import dataclass
from dataclasses import field
from paths import VERIFY_SCRIPT
```
