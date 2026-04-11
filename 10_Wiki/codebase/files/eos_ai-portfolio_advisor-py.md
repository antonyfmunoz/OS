---
type: codebase-file
path: eos_ai/portfolio_advisor.py
module: eos_ai.portfolio_advisor
lines: 788
size: 30909
generated: 2026-04-11
---

# eos_ai/portfolio_advisor.py

Portfolio Advisor — board-level intelligence across all companies in the portfolio.

Reasons across Lyfe Institute, Empyrean Creative, and any future org under
the portfolio. Advises on capital allocation, cross-company patterns, and
north star trajectory. Does not execute. Thinks in quarters, not days.
...

**Lines:** 788 | **Size:** 30,909 bytes

## Depends On

- [[eos_ai-agent_runtime-py]]
- [[eos_ai-context-py]]
- [[eos_ai-db-py]]

## Contains

- **class** [[eos_ai-portfolio_advisor-py-VentureHealth]] — 0 methods
- **class** [[eos_ai-portfolio_advisor-py-PortfolioAdvisor]] — 15 methods

## Import Statements

```python
import json
import os
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from pathlib import Path
from typing import Optional
from eos_ai.context import EOSContext
from eos_ai.context import load_context_from_env
from eos_ai.db import get_conn
from eos_ai.agent_runtime import AgentRuntime
from eos_ai.agent_runtime import TaskType
```
