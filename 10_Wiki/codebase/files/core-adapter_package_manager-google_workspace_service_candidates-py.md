---
type: codebase-file
path: core/adapter_package_manager/google_workspace_service_candidates.py
module: core.adapter_package_manager.google_workspace_service_candidates
lines: 100
size: 2969
generated: 2026-05-07
---

# core/adapter_package_manager/google_workspace_service_candidates.py

Google Workspace Future Service Package Candidates.

Services that are part of the Google Workspace suite but are NOT
declared for W0-001. They do not block W0-001 and will require
their own Adapter Packages and Tool Mastery Packs when declared.
...

**Lines:** 100 | **Size:** 2,969 bytes

## Contains

- **class** [[core-adapter_package_manager-google_workspace_service_candidates-py-FutureServiceCandidate]] — 1 methods
- **fn** [[core-adapter_package_manager-google_workspace_service_candidates-py-build_google_workspace_future_service_candidates]]`() → list[FutureServiceCandidate]`
- **fn** [[core-adapter_package_manager-google_workspace_service_candidates-py-candidate_is_declared_for_w0_001]]`(candidate) → bool`
- **fn** [[core-adapter_package_manager-google_workspace_service_candidates-py-candidate_blocks_w0_001]]`(candidate) → bool`
- **fn** [[core-adapter_package_manager-google_workspace_service_candidates-py-no_candidate_blocks_w0_001]]`(candidates) → bool`
- **fn** [[core-adapter_package_manager-google_workspace_service_candidates-py-all_candidates_require_own_package]]`(candidates) → bool`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from typing import Any
```
