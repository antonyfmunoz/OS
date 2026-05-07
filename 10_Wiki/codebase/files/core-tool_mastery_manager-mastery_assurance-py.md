---
type: codebase-file
path: core/tool_mastery_manager/mastery_assurance.py
module: core.tool_mastery_manager.mastery_assurance
lines: 266
size: 8762
generated: 2026-05-07
---

# core/tool_mastery_manager/mastery_assurance.py

Mastery Assurance Gate for the Tool Mastery Engine.

No worker may execute with an external tool unless TME has assured
a complete, fresh, up-to-date mastery pack for that tool, or the
founder explicitly waives the requirement.
...

**Lines:** 266 | **Size:** 8,762 bytes

## Contains

- **class** [[core-tool_mastery_manager-mastery_assurance-py-MasteryAssuranceStatus]] — 0 methods
- **class** [[core-tool_mastery_manager-mastery_assurance-py-RecommendedFlow]] — 0 methods
- **class** [[core-tool_mastery_manager-mastery_assurance-py-MasteryAssuranceDecision]] — 1 methods
- **fn** [[core-tool_mastery_manager-mastery_assurance-py-normalize_tool_name]]`(tool_name) → str`
- **fn** [[core-tool_mastery_manager-mastery_assurance-py-determine_staleness_threshold]]`(speed_category) → int`
- **fn** [[core-tool_mastery_manager-mastery_assurance-py-evaluate_pack_freshness]]`(last_researched, speed_category, current_date) → str`
- **fn** [[core-tool_mastery_manager-mastery_assurance-py-evaluate_pack_quality]]`(pack_text, tier) → str`
- **fn** [[core-tool_mastery_manager-mastery_assurance-py-evaluate_pack_completeness]]`(pack_text) → str`
- **fn** [[core-tool_mastery_manager-mastery_assurance-py-determine_required_tme_flow]]`(pack_exists, freshness, completeness, quality) → RecommendedFlow`
- **fn** [[core-tool_mastery_manager-mastery_assurance-py-ensure_mastery_before_execution]]`(tool_name, pack_exists, pack_text, last_researched, speed_category, tier, founder_waiver, current_date) → MasteryAssuranceDecision`
- **fn** [[core-tool_mastery_manager-mastery_assurance-py-mastery_assurance_blocks_execution]]`(decision) → bool`

## Import Statements

```python
from __future__ import annotations
import re
from dataclasses import dataclass
from dataclasses import field
from datetime import date
from datetime import timedelta
from enum import Enum
from typing import Any
```
