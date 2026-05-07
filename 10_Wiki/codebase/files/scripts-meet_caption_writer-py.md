---
type: codebase-file
path: scripts/meet_caption_writer.py
module: scripts.meet_caption_writer
lines: 66
size: 2157
tags: [entry-point]
generated: 2026-05-07
---

# scripts/meet_caption_writer.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Operator CLI to append Meet captions to the JSONL bridge.

Usage:
    meet_caption_writer.py --meeting-code CODE [--speaker NAME] [--ts TS]         [--stdin] [TEXT ...]

...

**Lines:** 66 | **Size:** 2,157 bytes

## Depends On

- [[eos_ai-substrate-meet_caption_bridge-py]]

## Contains

- **fn** [[scripts-meet_caption_writer-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import argparse
import json
import sys
from eos_ai.substrate.meet_caption_bridge import CaptionWriter
```
