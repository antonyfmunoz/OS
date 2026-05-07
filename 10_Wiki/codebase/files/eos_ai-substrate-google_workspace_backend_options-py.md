---
type: codebase-file
path: eos_ai/substrate/google_workspace_backend_options.py
module: eos_ai.substrate.google_workspace_backend_options
lines: 281
size: 9689
generated: 2026-05-07
---

# eos_ai/substrate/google_workspace_backend_options.py

Google Workspace backend/access-path options matrix for Phase 96.3 + 96.6.

Enumerates all candidate access paths for Google Drive/Docs
ingestion with their current status, independence level, requirements,
and Tool Mastery status.
...

**Lines:** 281 | **Size:** 9,689 bytes

## Depends On

- [[eos_ai-substrate-backend_registry_contracts-py]]

## Contains

- **class** [[eos_ai-substrate-google_workspace_backend_options-py-GoogleWorkspaceBackendOption]] — 1 methods
- **fn** [[eos_ai-substrate-google_workspace_backend_options-py-build_google_workspace_backend_options]]`() → list[GoogleWorkspaceBackendOption]`
- **fn** [[eos_ai-substrate-google_workspace_backend_options-py-get_complete_backends]]`() → list[GoogleWorkspaceBackendOption]`
- **fn** [[eos_ai-substrate-google_workspace_backend_options-py-get_candidate_backends]]`() → list[GoogleWorkspaceBackendOption]`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from eos_ai.substrate.backend_registry_contracts import BackendCategory
from eos_ai.substrate.backend_registry_contracts import BackendImplementationType
from eos_ai.substrate.backend_registry_contracts import BackendProfile
from eos_ai.substrate.backend_registry_contracts import BackendStatus
```
