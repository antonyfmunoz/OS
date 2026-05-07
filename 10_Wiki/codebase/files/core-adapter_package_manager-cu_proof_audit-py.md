---
type: codebase-file
path: core/adapter_package_manager/cu_proof_audit.py
module: core.adapter_package_manager.cu_proof_audit
lines: 312
size: 11743
generated: 2026-05-07
---

# core/adapter_package_manager/cu_proof_audit.py

CU Proof Audit.

Audits the evidence chain behind Computer Use maturity claims.
Static contract tests alone cannot establish 100% maturity —
auditable proof of actual GUI execution is required.
...

**Lines:** 312 | **Size:** 11,743 bytes

## Contains

- **class** [[core-adapter_package_manager-cu_proof_audit-py-CUProofQualityStatus]] — 0 methods
- **class** [[core-adapter_package_manager-cu_proof_audit-py-CUProofAuditResult]] — 1 methods
- **fn** [[core-adapter_package_manager-cu_proof_audit-py-_check_evidence_file]]`(path, base_dir) → bool`
- **fn** [[core-adapter_package_manager-cu_proof_audit-py-_load_cu_inventory]]`(path, base_dir) → dict[str, Any] | None`
- **fn** [[core-adapter_package_manager-cu_proof_audit-py-audit_w_gdrive_cu_001_proof]]`(evidence_paths, base_dir) → CUProofAuditResult`
- **fn** [[core-adapter_package_manager-cu_proof_audit-py-evidence_supports_100_percent_maturity]]`(result) → bool`
- **fn** [[core-adapter_package_manager-cu_proof_audit-py-cu_proof_requires_downgrade]]`(result) → bool`
- **fn** [[core-adapter_package_manager-cu_proof_audit-py-cu_proof_requires_founder_confirmation]]`(result) → bool`
- **fn** [[core-adapter_package_manager-cu_proof_audit-py-build_cu_proof_audit_report]]`(result) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any
import json
import os
```
