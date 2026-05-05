---
type: codebase-file
path: scripts/inbox_zero_init.py
module: scripts.inbox_zero_init
lines: 403
size: 14783
generated: 2026-04-12
---

# scripts/inbox_zero_init.py

Inbox Zero Initialization — run ONCE on first DEX setup.

Four-phase protocol:
  Phase 1 — AUDIT    Read-only. Map current inbox state.
  Phase 2 — PLAN     Show what will change. Confirm before proceeding.
...

**Lines:** 403 | **Size:** 14,783 bytes

## Depends On

- [[eos_ai-context-py]]
- [[eos_ai-email_gps-py]]
- [[eos_ai-gws_connector-py]]

## Contains

- **fn** [[scripts-inbox_zero_init-py-run_post_init_verification]]`(processed) → str`
- **fn** [[scripts-inbox_zero_init-py-verify_existing_labels]]`() → str`

## Import Statements

```python
import sys
from dotenv import load_dotenv
from collections import Counter
from pathlib import Path
from eos_ai.email_gps import EmailGPS
from eos_ai.email_gps import EmailFolder
from eos_ai.email_gps import ProcessedEmail
from eos_ai.gws_connector import GWSConnector
from eos_ai.context import load_context_from_env
```
