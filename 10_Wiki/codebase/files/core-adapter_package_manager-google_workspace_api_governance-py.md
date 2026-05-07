---
type: codebase-file
path: core/adapter_package_manager/google_workspace_api_governance.py
module: core.adapter_package_manager.google_workspace_api_governance
lines: 119
size: 3429
generated: 2026-05-07
---

# core/adapter_package_manager/google_workspace_api_governance.py

Governance Policy for W-GWS-API-001.

Defines what is allowed and blocked for the API tab-aware extraction
path. Read-only by default; no mutation, no credential capture.

...

**Lines:** 119 | **Size:** 3,429 bytes

## Contains

- **class** [[core-adapter_package_manager-google_workspace_api_governance-py-GovernancePolicy]] — 1 methods
- **fn** [[core-adapter_package_manager-google_workspace_api_governance-py-build_w_gws_api_001_governance_policy]]`() → GovernancePolicy`
- **fn** [[core-adapter_package_manager-google_workspace_api_governance-py-governance_is_read_only]]`(policy) → bool`
- **fn** [[core-adapter_package_manager-google_workspace_api_governance-py-governance_blocks_mutation]]`(policy) → bool`
- **fn** [[core-adapter_package_manager-google_workspace_api_governance-py-governance_blocks_credential_capture]]`(policy) → bool`
- **fn** [[core-adapter_package_manager-google_workspace_api_governance-py-governance_blocks_permission_changes]]`(policy) → bool`
- **fn** [[core-adapter_package_manager-google_workspace_api_governance-py-governance_blocks_memory_promotion]]`(policy) → bool`
- **fn** [[core-adapter_package_manager-google_workspace_api_governance-py-governance_requires_export_approval]]`(policy) → bool`
- **fn** [[core-adapter_package_manager-google_workspace_api_governance-py-governance_preserves_instance_scope]]`(policy) → bool`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from typing import Any
```
