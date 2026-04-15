---
type: codebase-file
path: scripts/substrate_workflow_delegation_smoke_test.py
module: scripts.substrate_workflow_delegation_smoke_test
lines: 579
size: 20966
tags: [entry-point]
generated: 2026-04-12
---

# scripts/substrate_workflow_delegation_smoke_test.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Workflow Delegation Layer v1 — smoke test.

Proves that:
  1.  Builder-dev language → classified as workflow/builder_dev.
  2.  Product-runtime language → classified as workflow/product_runtime.
...

**Lines:** 579 | **Size:** 20,966 bytes

## Contains

- **fn** [[scripts-substrate_workflow_delegation_smoke_test-py-check]]`(name, cond, detail) → None`
- **fn** [[scripts-substrate_workflow_delegation_smoke_test-py-_header]]`(msg) → None`
- **fn** [[scripts-substrate_workflow_delegation_smoke_test-py-_reset_env]]`() → None`
- **fn** [[scripts-substrate_workflow_delegation_smoke_test-py-test_builder_dev_classification]]`() → None`
- **fn** [[scripts-substrate_workflow_delegation_smoke_test-py-test_product_runtime_classification]]`() → None`
- **fn** [[scripts-substrate_workflow_delegation_smoke_test-py-test_conversation_classification]]`() → None`
- **fn** [[scripts-substrate_workflow_delegation_smoke_test-py-test_skill_tool_classification]]`() → None`
- **fn** [[scripts-substrate_workflow_delegation_smoke_test-py-test_content_ops_classification]]`() → None`
- **fn** [[scripts-substrate_workflow_delegation_smoke_test-py-test_analysis_classification]]`() → None`
- **fn** [[scripts-substrate_workflow_delegation_smoke_test-py-test_system_ops_classification]]`() → None`
- **fn** [[scripts-substrate_workflow_delegation_smoke_test-py-test_empty_input]]`() → None`
- **fn** [[scripts-substrate_workflow_delegation_smoke_test-py-test_builder_allows_builder_dev]]`() → None`
- **fn** [[scripts-substrate_workflow_delegation_smoke_test-py-test_product_blocks_builder_dev]]`() → None`
- **fn** [[scripts-substrate_workflow_delegation_smoke_test-py-test_product_allows_product_runtime]]`() → None`
- **fn** [[scripts-substrate_workflow_delegation_smoke_test-py-test_unknown_mode_restricts]]`() → None`
- **fn** [[scripts-substrate_workflow_delegation_smoke_test-py-test_conversation_always_allowed]]`() → None`
- **fn** [[scripts-substrate_workflow_delegation_smoke_test-py-test_enrich_metadata]]`() → None`
- **fn** [[scripts-substrate_workflow_delegation_smoke_test-py-test_enrich_preserves_existing]]`() → None`
- **fn** [[scripts-substrate_workflow_delegation_smoke_test-py-test_extra_keywords]]`() → None`
- **fn** [[scripts-substrate_workflow_delegation_smoke_test-py-test_determinism]]`() → None`
- **fn** [[scripts-substrate_workflow_delegation_smoke_test-py-test_policy_dict_shape]]`() → None`
- **fn** [[scripts-substrate_workflow_delegation_smoke_test-py-test_no_hotpath_imports]]`() → None`
- **fn** [[scripts-substrate_workflow_delegation_smoke_test-py-test_no_second_router]]`() → None`
- **fn** [[scripts-substrate_workflow_delegation_smoke_test-py-test_product_local_delegation_coexists_with_workflow]]`() → None`
- **fn** [[scripts-substrate_workflow_delegation_smoke_test-py-test_transport_integration_returns_workflow_fields]]`() → None`
- **fn** [[scripts-substrate_workflow_delegation_smoke_test-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import os
import sys
```
