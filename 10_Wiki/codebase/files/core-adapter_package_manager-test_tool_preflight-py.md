---
type: codebase-file
path: core/adapter_package_manager/test_tool_preflight.py
module: core.adapter_package_manager.test_tool_preflight
lines: 249
size: 8850
generated: 2026-05-07
---

# core/adapter_package_manager/test_tool_preflight.py

Test Tool Preflight for UMH task execution.

Before a test or ingestion run, UMH must inventory the tools, access
paths, and runtimes required and verify execution readiness for each.

...

**Lines:** 249 | **Size:** 8,850 bytes

## Contains

- **class** [[core-adapter_package_manager-test_tool_preflight-py-TestToolPreflightStatus]] — 0 methods
- **class** [[core-adapter_package_manager-test_tool_preflight-py-TestToolRequirement]] — 1 methods
- **class** [[core-adapter_package_manager-test_tool_preflight-py-TestToolPreflightReport]] — 1 methods
- **fn** [[core-adapter_package_manager-test_tool_preflight-py-detect_required_tools_for_task]]`(task_summary) → list[TestToolRequirement]`
- **fn** [[core-adapter_package_manager-test_tool_preflight-py-build_w0_001_required_tool_inventory]]`() → list[TestToolRequirement]`
- **fn** [[core-adapter_package_manager-test_tool_preflight-py-run_test_tool_preflight]]`(task_summary, package_lookup) → TestToolPreflightReport`
- **fn** [[core-adapter_package_manager-test_tool_preflight-py-preflight_blocks_execution]]`(report) → bool`
- **fn** [[core-adapter_package_manager-test_tool_preflight-py-summarize_test_tool_preflight]]`(report) → str`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any
from maturity_enforcement import AdapterExecutionMaturityStatus
from maturity_enforcement import AdapterExecutionReadinessDecision
from maturity_enforcement import AdapterPackageSnapshot
from maturity_enforcement import evaluate_adapter_package_execution_readiness
```
