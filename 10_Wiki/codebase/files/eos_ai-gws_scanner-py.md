---
type: codebase-file
path: eos_ai/gws_scanner.py
module: eos_ai.gws_scanner
lines: 700
size: 27421
generated: 2026-04-11
---

# eos_ai/gws_scanner.py

GWSDocumentScanner — reads Google Docs the founder owns,
extracts business context, and ingests it into EOS knowledge layers.

DEX knows everything written about the businesses.

...

**Lines:** 700 | **Size:** 27,421 bytes

## Depends On

- [[eos_ai-context-py]]

## Contains

- **class** [[eos_ai-gws_scanner-py-GWSDocument]] — 0 methods
- **class** [[eos_ai-gws_scanner-py-GWSDocumentScanner]] — 13 methods

## Import Statements

```python
import json
import re
import subprocess
import time
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from pathlib import Path
from eos_ai.context import EOSContext
```
