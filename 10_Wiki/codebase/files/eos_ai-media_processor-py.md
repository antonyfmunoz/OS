---
type: codebase-file
path: eos_ai/media_processor.py
module: eos_ai.media_processor
lines: 351
size: 12208
generated: 2026-04-12
---

# eos_ai/media_processor.py

MediaProcessor — unified multimodal file handler.

Routes files to the right backend:
  - voice/audio  → faster-whisper (local, always)
  - image        → Gemini 2.0 Flash (requires GEMINI_API_KEY)
...

**Lines:** 351 | **Size:** 12,208 bytes

## Used By

- [[eos_ai-voice_interface-py]]

## Contains

- **class** [[eos_ai-media_processor-py-MediaProcessor]] — 9 methods

## Import Statements

```python
from pathlib import Path
from dotenv import load_dotenv as _load_dotenv
import os
import tempfile
import subprocess
import base64
```
