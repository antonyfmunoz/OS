---
type: codebase-file
path: eos_ai/substrate/visible_google_doc_reader.py
module: eos_ai.substrate.visible_google_doc_reader
lines: 359
size: 10822
generated: 2026-05-07
---

# eos_ai/substrate/visible_google_doc_reader.py

Visible Google Doc reader for W0-001R computer-use fallback test.

Reads a Google Doc through the visible Chrome UI using only:
- Windows UI Automation / accessibility tree
- Mouse / keyboard / scrolling
...

**Lines:** 359 | **Size:** 10,822 bytes

## Contains

- **class** [[eos_ai-substrate-visible_google_doc_reader-py-DocReadMethod]] — 0 methods
- **class** [[eos_ai-substrate-visible_google_doc_reader-py-DocReadStatus]] — 0 methods
- **class** [[eos_ai-substrate-visible_google_doc_reader-py-DocTabCURead]] — 1 methods
- **class** [[eos_ai-substrate-visible_google_doc_reader-py-DocCUReadResult]] — 1 methods
- **fn** [[eos_ai-substrate-visible_google_doc_reader-py-validate_doc_read_scope]]`(url) → list[str]`
- **fn** [[eos_ai-substrate-visible_google_doc_reader-py-build_doc_open_command]]`(file_id, chrome_path, profile_directory) → str`
- **fn** [[eos_ai-substrate-visible_google_doc_reader-py-build_doc_tab_detection_script]]`() → str`
- **fn** [[eos_ai-substrate-visible_google_doc_reader-py-build_doc_scroll_read_script]]`(max_scrolls) → str`
- **fn** [[eos_ai-substrate-visible_google_doc_reader-py-parse_doc_cu_output]]`(raw_output) → DocCUReadResult`
- **fn** [[eos_ai-substrate-visible_google_doc_reader-py-build_cu_vs_api_coverage]]`(cu_word_count, api_word_count, cu_tabs_read, api_total_tabs) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
import re
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any
```
