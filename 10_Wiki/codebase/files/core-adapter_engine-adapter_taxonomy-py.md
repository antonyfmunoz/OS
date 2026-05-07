---
type: codebase-file
path: core/adapter_engine/adapter_taxonomy.py
module: core.adapter_engine.adapter_taxonomy
lines: 131
size: 4289
generated: 2026-05-07
---

# core/adapter_engine/adapter_taxonomy.py

Adapter taxonomy for the UMH Adapter Engine.

Classifies adapter categories and external system types. Every
external system requires an adapter boundary. Every adapter category
has governance, proof, and optionally Tool Mastery requirements.
...

**Lines:** 131 | **Size:** 4,289 bytes

## Contains

- **class** [[core-adapter_engine-adapter_taxonomy-py-AdapterCategory]] — 0 methods
- **class** [[core-adapter_engine-adapter_taxonomy-py-ExternalSystemType]] — 0 methods
- **fn** [[core-adapter_engine-adapter_taxonomy-py-adapter_category_requires_boundary]]`(category) → bool`
- **fn** [[core-adapter_engine-adapter_taxonomy-py-external_system_requires_adapter]]`(system_type) → bool`
- **fn** [[core-adapter_engine-adapter_taxonomy-py-adapter_category_requires_tool_mastery]]`(category) → bool`
- **fn** [[core-adapter_engine-adapter_taxonomy-py-adapter_category_requires_governance]]`(category) → bool`
- **fn** [[core-adapter_engine-adapter_taxonomy-py-adapter_category_requires_proof]]`(category) → bool`
- **fn** [[core-adapter_engine-adapter_taxonomy-py-list_all_adapter_categories]]`() → list[AdapterCategory]`
- **fn** [[core-adapter_engine-adapter_taxonomy-py-list_all_external_system_types]]`() → list[ExternalSystemType]`
- **fn** [[core-adapter_engine-adapter_taxonomy-py-adapter_category_is_execution_environment]]`(category) → bool`
- **fn** [[core-adapter_engine-adapter_taxonomy-py-adapter_category_is_human_path]]`(category) → bool`
- **fn** [[core-adapter_engine-adapter_taxonomy-py-classify_external_system]]`(system_type) → AdapterCategory`

## Import Statements

```python
from __future__ import annotations
from enum import Enum
```
