---
type: codebase-file
path: eos_ai/setup_wizard.py
module: eos_ai.setup_wizard
lines: 167
size: 5659
tags: [entry-point]
generated: 2026-04-12
---

# eos_ai/setup_wizard.py

> **ENTRY POINT** — Contains `if __name__` or server start.

SetupWizard — onboarding flow for new EOS users.

Collects founder and venture info, creates a BusinessInstance,
and generates a personalised EA soul doc from the master template.

...

**Lines:** 167 | **Size:** 5,659 bytes

## Contains

- **fn** [[eos_ai-setup_wizard-py-generate_ea_soul_doc]]`(ai_name, founder_name, north_star, current_stage, offer_name, primary_channel) → str`
- **fn** [[eos_ai-setup_wizard-py-run_setup]]`() → None`

## Import Statements

```python
from __future__ import annotations
import sys
import os
from pathlib import Path
```
