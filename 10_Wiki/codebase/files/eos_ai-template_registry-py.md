---
type: codebase-file
path: eos_ai/template_registry.py
module: eos_ai.template_registry
lines: 598
size: 22755
tags: [entry-point]
generated: 2026-05-07
---

# eos_ai/template_registry.py

> **ENTRY POINT** — Contains `if __name__` or server start.

TemplateRegistry — formal template schema for the Meta Harness.

Templates are composable blueprints made of ontological primitives.
Each template defines typed slots that must be filled at instantiation.

...

**Lines:** 598 | **Size:** 22,755 bytes

## Used By

- [[eos_ai-company_instantiator-py]]

## Contains

- **class** [[eos_ai-template_registry-py-TemplateSlot]] — 0 methods
- **class** [[eos_ai-template_registry-py-Template]] — 0 methods
- **class** [[eos_ai-template_registry-py-TemplateInstance]] — 0 methods
- **class** [[eos_ai-template_registry-py-TemplateRegistry]] — 6 methods
- **fn** [[eos_ai-template_registry-py-_common_business_slots]]`() → list[TemplateSlot]`

## Import Statements

```python
import os
import sys
import uuid as _uuid
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from typing import Any
```
