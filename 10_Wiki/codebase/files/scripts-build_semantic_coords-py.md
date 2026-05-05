---
type: codebase-file
path: scripts/build_semantic_coords.py
module: scripts.build_semantic_coords
lines: 129
size: 4192
tags: [entry-point]
generated: 2026-04-12
---

# scripts/build_semantic_coords.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Build semantic coordinates for all graph nodes.

Usage:
    python3 scripts/build_semantic_coords.py
    python3 scripts/build_semantic_coords.py --rebuild
...

**Lines:** 129 | **Size:** 4,192 bytes

## Contains

- **fn** [[scripts-build_semantic_coords-py-main]]`() → None`
- **fn** [[scripts-build_semantic_coords-py-_print_distribution_stats]]`(graph) → None`

## Import Statements

```python
import argparse
import json
import sys
import time
import numpy as np
```
