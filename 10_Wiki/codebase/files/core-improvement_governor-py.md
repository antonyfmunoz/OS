---
type: codebase-file
path: core/improvement_governor.py
module: core.improvement_governor
lines: 328
size: 12035
generated: 2026-05-07
---

# core/improvement_governor.py

Improvement Governor — controlled self-modification with audit trail.

Allows system components to PROPOSE improvements without silent mutation.
Changes are classified by risk and only low-risk changes auto-apply.
Medium/high-risk changes are logged as proposals for human review.
...

**Lines:** 328 | **Size:** 12,035 bytes

## Contains

- **class** [[core-improvement_governor-py-ImprovementProposal]] — 1 methods
- **class** [[core-improvement_governor-py-Governor]] — 13 methods
- **fn** [[core-improvement_governor-py-get_governor]]`() → Governor`

## Import Statements

```python
from __future__ import annotations
import json
import time
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Any
from typing import Literal
```
