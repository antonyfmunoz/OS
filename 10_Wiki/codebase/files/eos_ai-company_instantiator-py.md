---
type: codebase-file
path: eos_ai/company_instantiator.py
module: eos_ai.company_instantiator
lines: 304
size: 11447
tags: [entry-point]
generated: 2026-05-07
---

# eos_ai/company_instantiator.py

> **ENTRY POINT** — Contains `if __name__` or server start.

CompanyInstantiator — instantiate the 6 Munoz Conglomerate companies
as formal template instances with offer ladder rows in Neon.

**Lines:** 304 | **Size:** 11,447 bytes

## Depends On

- [[eos_ai-db-py]]
- [[eos_ai-template_registry-py]]

## Contains

- **class** [[eos_ai-company_instantiator-py-CompanyInstantiator]] — 5 methods

## Import Statements

```python
import sys
import os
from eos_ai.template_registry import TemplateRegistry
from eos_ai.template_registry import TemplateInstance
from eos_ai.db import get_conn
```
