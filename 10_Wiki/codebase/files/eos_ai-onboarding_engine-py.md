---
type: codebase-file
path: eos_ai/onboarding_engine.py
module: eos_ai.onboarding_engine
lines: 353
size: 14657
generated: 2026-04-12
---

# eos_ai/onboarding_engine.py

OnboardingEngine — conversational onboarding for new EOS founders.

A new founder runs !onboard in Discord. DEX asks 15 questions across
6 topic areas. When all questions are answered the engine:
  1. Uses the LLM to extract structured business data from free-form answers
...

**Lines:** 353 | **Size:** 14,657 bytes

## Used By

- [[services-discord_bot-py]]

## Contains

- **class** [[eos_ai-onboarding_engine-py-OnboardingStep]] — 0 methods
- **class** [[eos_ai-onboarding_engine-py-OnboardingSession]] — 0 methods
- **class** [[eos_ai-onboarding_engine-py-OnboardingEngine]] — 9 methods

## Import Statements

```python
from __future__ import annotations
import asyncio
import json
import re
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional
```
