---
type: codebase-file
path: eos_ai/person_recognition.py
module: eos_ai.person_recognition
lines: 614
size: 24177
generated: 2026-04-11
---

# eos_ai/person_recognition.py

Person Recognition — central module for identifying known people
across all channels: email, Discord, Calendly, Calendar.

The Martell Rule: never auto-respond to a recognized person with
a template. Route to ANTONY immediately. Flag it.

**Lines:** 614 | **Size:** 24,177 bytes

## Contains

- **class** [[eos_ai-person_recognition-py-HumanIntelligenceProfile]] — 0 methods
- **fn** [[eos_ai-person_recognition-py-create_lead_file]]`(name, email, company, source, venture, notes) → str`
- **fn** [[eos_ai-person_recognition-py-recognize_person]]`(name, email, ctx) → dict`
- **fn** [[eos_ai-person_recognition-py-format_person_context]]`(recognition, name) → str`
- **fn** [[eos_ai-person_recognition-py-build_intelligence_profile]]`(name, email, company, ctx) → HumanIntelligenceProfile`
- **fn** [[eos_ai-person_recognition-py-format_intelligence_profile]]`(profile) → str`
- **fn** [[eos_ai-person_recognition-py-score_relationship_health]]`(name, email, ctx) → dict`

## Import Statements

```python
import os
import json
import logging
from datetime import datetime
from datetime import timedelta
from zoneinfo import ZoneInfo
from dataclasses import dataclass
from dataclasses import field
from typing import Optional
```
