---
type: codebase-file
path: core/self_improvement.py
module: core.self_improvement
lines: 482
size: 16782
generated: 2026-05-07
---

# core/self_improvement.py

Self-Improvement Interface — recursive system evolution.

Every major subsystem exposes four methods:
    metrics()              — current performance data
    evaluate()             — diagnosis of strengths/weaknesses
...

**Lines:** 482 | **Size:** 16,782 bytes

## Depends On

- [[core-primitives-py]]
- [[core-transformer-py]]

## Contains

- **class** [[core-self_improvement-py-SelfImprovingComponent]] — 4 methods
- **class** [[core-self_improvement-py-ImprovementRecord]] — 1 methods
- **class** [[core-self_improvement-py-CompositionImprover]] — 5 methods
- **class** [[core-self_improvement-py-PipelineImprover]] — 5 methods
- **class** [[core-self_improvement-py-RouterImprover]] — 5 methods
- **fn** [[core-self_improvement-py-_log_improvement]]`(record) → None`
- **fn** [[core-self_improvement-py-load_improvement_history]]`(component, limit) → list[dict[str, Any]]`
- **fn** [[core-self_improvement-py-run_improvement_cycle]]`(components) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
import json
import time
from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Any
from core.primitives import PrimitiveTag
from core.transformer import TransformationResult
from core.transformer import transform
```
