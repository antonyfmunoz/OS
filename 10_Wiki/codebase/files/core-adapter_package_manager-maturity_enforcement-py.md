---
type: codebase-file
path: core/adapter_package_manager/maturity_enforcement.py
module: core.adapter_package_manager.maturity_enforcement
lines: 301
size: 11349
generated: 2026-05-07
---

# core/adapter_package_manager/maturity_enforcement.py

Adapter Package Maturity Enforcement.

Selected-tool / access-path 100% maturity gate. No external tool,
SaaS, API, CLI, MCP server, browser tool, computer-use path, file
parser, runtime, or environment may be used by UMH unless the
...

**Lines:** 301 | **Size:** 11,349 bytes

## Contains

- **class** [[core-adapter_package_manager-maturity_enforcement-py-AdapterExecutionMaturityStatus]] — 0 methods
- **class** [[core-adapter_package_manager-maturity_enforcement-py-AdapterExecutionReadinessDecision]] — 1 methods
- **class** [[core-adapter_package_manager-maturity_enforcement-py-AdapterPackageSnapshot]] — 0 methods
- **fn** [[core-adapter_package_manager-maturity_enforcement-py-selected_access_path_is_complete]]`(path_status) → bool`
- **fn** [[core-adapter_package_manager-maturity_enforcement-py-adapter_package_has_required_components]]`(snap) → bool`
- **fn** [[core-adapter_package_manager-maturity_enforcement-py-known_gaps_affect_capability]]`(snap, capability) → bool`
- **fn** [[core-adapter_package_manager-maturity_enforcement-py-evaluate_adapter_package_execution_readiness]]`(snap, capability, access_path_id) → AdapterExecutionReadinessDecision`
- **fn** [[core-adapter_package_manager-maturity_enforcement-py-_count_passed_checks]]`(snap, capability) → int`
- **fn** [[core-adapter_package_manager-maturity_enforcement-py-adapter_execution_blocks]]`(decision) → bool`
- **fn** [[core-adapter_package_manager-maturity_enforcement-py-require_100_percent_maturity]]`(decision) → bool`
- **fn** [[core-adapter_package_manager-maturity_enforcement-py-build_adapter_execution_readiness_report]]`(decisions) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any
```
