---
type: codebase-file
path: eos_ai/feedback_loop.py
module: eos_ai.feedback_loop
lines: 468
size: 16041
generated: 2026-04-12
---

# eos_ai/feedback_loop.py

FeedbackLoop — closes the loop between DEX recommendations and real outcomes.

Every piece of advice DEX gives is logged. When the founder reports back
what happened, the outcome is captured and tied to the recommendation.
Over time this builds a signal of what actually works vs. what doesn't.
...

**Lines:** 468 | **Size:** 16,041 bytes

## Contains

- **class** [[eos_ai-feedback_loop-py-OutcomeType]] — 0 methods
- **class** [[eos_ai-feedback_loop-py-Recommendation]] — 0 methods
- **class** [[eos_ai-feedback_loop-py-FeedbackLoop]] — 10 methods

## Import Statements

```python
import json
import uuid
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from enum import Enum
```
