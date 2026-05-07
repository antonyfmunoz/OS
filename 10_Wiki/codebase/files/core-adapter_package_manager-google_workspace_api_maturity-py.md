---
type: codebase-file
path: core/adapter_package_manager/google_workspace_api_maturity.py
module: core.adapter_package_manager.google_workspace_api_maturity
lines: 223
size: 7602
generated: 2026-05-07
---

# core/adapter_package_manager/google_workspace_api_maturity.py

Maturity Gate for W-GWS-API-001.

Evaluates whether the API tab-aware adapter path is 100% mature.
Uses existing maturity enforcement and full-path maturity helpers.

...

**Lines:** 223 | **Size:** 7,602 bytes

## Contains

- **class** [[core-adapter_package_manager-google_workspace_api_maturity-py-W_GWS_API_001_MaturityCheck]] — 1 methods
- **class** [[core-adapter_package_manager-google_workspace_api_maturity-py-W_GWS_API_001_MaturityDecision]] — 1 methods
- **fn** [[core-adapter_package_manager-google_workspace_api_maturity-py-evaluate_w_gws_api_001_maturity]]`(has_tool_mastery_pack, has_contract_mapping, has_governance, has_tests, has_auth, first_tab_only_allowed, has_w0_001_coverage_contract) → W_GWS_API_001_MaturityDecision`
- **fn** [[core-adapter_package_manager-google_workspace_api_maturity-py-w_gws_api_001_is_100_percent_mature]]`() → bool`
- **fn** [[core-adapter_package_manager-google_workspace_api_maturity-py-build_w_gws_api_001_maturity_decision]]`() → W_GWS_API_001_MaturityDecision`
- **fn** [[core-adapter_package_manager-google_workspace_api_maturity-py-build_w_gws_api_001_gap_report]]`() → dict[str, Any]`
- **fn** [[core-adapter_package_manager-google_workspace_api_maturity-py-google_workspace_package_is_fully_mature_with_cu_partial]]`() → bool`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from google_workspace_api_adapter_path import W_GWS_API_001_PATH_ID
from google_workspace_api_adapter_path import build_google_workspace_api_tab_aware_path
from google_workspace_api_contract_mapping import api_mapping_rejects_first_tab_only
from google_workspace_api_contract_mapping import api_mapping_requires_child_tabs_recursion
from google_workspace_api_contract_mapping import api_mapping_requires_document_tabs_traversal
from google_workspace_api_contract_mapping import api_mapping_requires_include_tabs_content
from google_workspace_api_contract_mapping import build_w_gws_api_001_contract_mapping
from google_workspace_api_governance import build_w_gws_api_001_governance_policy
from google_workspace_api_governance import governance_blocks_credential_capture
from google_workspace_api_governance import governance_blocks_mutation
from google_workspace_api_governance import governance_is_read_only
from full_path_maturity import AdapterPathSnapshot
from full_path_maturity import PathDeclarationStatus
from full_path_maturity import evaluate_full_adapter_package_maturity
from full_path_maturity import evaluate_path_maturity
```
