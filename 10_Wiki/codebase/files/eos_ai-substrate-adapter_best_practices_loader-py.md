---
type: codebase-file
path: eos_ai/substrate/adapter_best_practices_loader.py
module: eos_ai.substrate.adapter_best_practices_loader
lines: 228
size: 7148
generated: 2026-05-07
---

# eos_ai/substrate/adapter_best_practices_loader.py

Tool Mastery Pack loader for Phase 96.5.

Tool Mastery is an internal layer of the Adapter Engine.
This module loads and parses skill files to build Tool Mastery Packs.

...

**Lines:** 228 | **Size:** 7,148 bytes

## Contains

- **class** [[eos_ai-substrate-adapter_best_practices_loader-py-AdapterBestPracticesPolicy]] — 1 methods
- **class** [[eos_ai-substrate-adapter_best_practices_loader-py-MergedAdapterPolicy]] — 1 methods
- **fn** [[eos_ai-substrate-adapter_best_practices_loader-py-locate_claude_code_best_practices_skill]]`(search_roots) → str | None`
- **fn** [[eos_ai-substrate-adapter_best_practices_loader-py-load_best_practices_skill]]`(path) → str`
- **fn** [[eos_ai-substrate-adapter_best_practices_loader-py-extract_adapter_relevant_rules]]`(skill_text) → list[str]`
- **fn** [[eos_ai-substrate-adapter_best_practices_loader-py-build_adapter_policy_from_skill]]`(skill_text) → AdapterBestPracticesPolicy`
- **fn** [[eos_ai-substrate-adapter_best_practices_loader-py-build_tool_mastery_pack_from_skill]]`(adapter_id, tool_name, skill_path) → Any`
- **fn** [[eos_ai-substrate-adapter_best_practices_loader-py-merge_skill_policy_with_adapter_quality_gate]]`(skill_policy, default_rules) → MergedAdapterPolicy`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Any
```
