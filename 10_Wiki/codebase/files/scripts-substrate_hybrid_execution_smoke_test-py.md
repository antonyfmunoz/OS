---
type: codebase-file
path: scripts/substrate_hybrid_execution_smoke_test.py
module: scripts.substrate_hybrid_execution_smoke_test
lines: 686
size: 25307
tags: [entry-point]
generated: 2026-04-11
---

# scripts/substrate_hybrid_execution_smoke_test.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Hybrid Execution Target Policy v1 — smoke test.

Proves that:
  1.  Builder mode default target resolves to **local**.
  2.  Product mode default target resolves to **vps**.
...

**Lines:** 686 | **Size:** 25,307 bytes

## Contains

- **fn** [[scripts-substrate_hybrid_execution_smoke_test-py-check]]`(name, cond, detail) → None`
- **fn** [[scripts-substrate_hybrid_execution_smoke_test-py-_header]]`(msg) → None`
- **fn** [[scripts-substrate_hybrid_execution_smoke_test-py-_reset_env]]`() → None`
- **fn** [[scripts-substrate_hybrid_execution_smoke_test-py-test_target_policy_defaults]]`() → None`
- **fn** [[scripts-substrate_hybrid_execution_smoke_test-py-test_target_policy_env_overrides]]`() → None`
- **fn** [[scripts-substrate_hybrid_execution_smoke_test-py-test_target_policy_invalid_clamps]]`() → None`
- **fn** [[scripts-substrate_hybrid_execution_smoke_test-py-test_target_policy_full_dict]]`() → None`
- **fn** [[scripts-substrate_hybrid_execution_smoke_test-py-test_delegation_off]]`() → None`
- **fn** [[scripts-substrate_hybrid_execution_smoke_test-py-test_delegation_on_no_match]]`() → None`
- **fn** [[scripts-substrate_hybrid_execution_smoke_test-py-test_delegation_on_keyword_match]]`() → None`
- **fn** [[scripts-substrate_hybrid_execution_smoke_test-py-test_delegation_force_local]]`() → None`
- **fn** [[scripts-substrate_hybrid_execution_smoke_test-py-test_mode_preserved_during_delegation]]`() → None`
- **fn** [[scripts-substrate_hybrid_execution_smoke_test-py-test_resolve_mode_session_builder_local]]`() → None`
- **fn** [[scripts-substrate_hybrid_execution_smoke_test-py-test_resolve_mode_session_product_vps]]`() → None`
- **fn** [[scripts-substrate_hybrid_execution_smoke_test-py-test_resolve_mode_session_delegation_carries]]`() → None`
- **fn** [[scripts-substrate_hybrid_execution_smoke_test-py-test_resolve_mode_session_unknown_noop]]`() → None`
- **fn** [[scripts-substrate_hybrid_execution_smoke_test-py-test_resolve_mode_session_env_override]]`() → None`
- **fn** [[scripts-substrate_hybrid_execution_smoke_test-py-test_mode_context_carries_policy_metadata]]`() → None`
- **fn** [[scripts-substrate_hybrid_execution_smoke_test-py-test_mode_context_delegation_metadata]]`() → None`
- **fn** [[scripts-substrate_hybrid_execution_smoke_test-py-test_no_hot_path_imports_target_policy]]`() → None`
- **fn** [[scripts-substrate_hybrid_execution_smoke_test-py-test_no_hot_path_imports_mode_routing]]`() → None`
- **fn** [[scripts-substrate_hybrid_execution_smoke_test-py-test_one_router_invariant]]`() → None`
- **fn** [[scripts-substrate_hybrid_execution_smoke_test-py-test_target_resolution_deterministic]]`() → None`
- **fn** [[scripts-substrate_hybrid_execution_smoke_test-py-test_builder_product_distinct]]`() → None`
- **fn** [[scripts-substrate_hybrid_execution_smoke_test-py-test_session_names_preserved]]`() → None`
- **fn** [[scripts-substrate_hybrid_execution_smoke_test-py-test_per_channel_session_preserved]]`() → None`
- **fn** [[scripts-substrate_hybrid_execution_smoke_test-py-test_pseudo_live_status_reports_policy]]`() → None`
- **fn** [[scripts-substrate_hybrid_execution_smoke_test-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import os
import sys
```
