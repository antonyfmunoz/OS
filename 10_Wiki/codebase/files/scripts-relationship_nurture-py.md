---
type: codebase-file
path: scripts/relationship_nurture.py
module: scripts.relationship_nurture
lines: 128
size: 4024
tags: [entry-point]
generated: 2026-04-12
---

# scripts/relationship_nurture.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Relationship nurturing — checks for contacts not heard from in 30+ days
and surfaces them. Runs weekly on Mondays at 7am PDT.

**Lines:** 128 | **Size:** 4,024 bytes

## Contains

- **fn** [[scripts-relationship_nurture-py-check_relationships]]`()`

## Import Statements

```python
import os
import sys
import asyncio
import discord
from datetime import datetime
from datetime import timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
```
