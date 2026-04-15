---
type: codebase-file
path: eos_ai/skill_registry_v2.py
module: eos_ai.skill_registry_v2
lines: 491
size: 23222
generated: 2026-04-12
---

# eos_ai/skill_registry_v2.py

SkillRegistryV2 — first-class skill objects with trust scoring,
versioning, performance metrics, and execution tracking.

Extends the file-based SkillRegistry (V1) with:
  - Trust levels that gate what the skill can do autonomously
...

**Lines:** 491 | **Size:** 23,222 bytes

## Contains

- **class** [[eos_ai-skill_registry_v2-py-SkillDomain]] — 0 methods
- **class** [[eos_ai-skill_registry_v2-py-TrustLevel]] — 0 methods
- **class** [[eos_ai-skill_registry_v2-py-SkillV2]] — 1 methods
- **class** [[eos_ai-skill_registry_v2-py-SkillRegistryV2]] — 5 methods

## Import Statements

```python
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from enum import Enum
```
