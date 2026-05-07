---
type: codebase-function
file: core/execution_bridge.py
line: 661
generated: 2026-05-07
---

# execute_with_routing

**File:** [[core-execution_bridge-py]] | **Line:** 661
**Signature:** `execute_with_routing(structure, constraints, extra_context) → RoutedLearningResult`

End-to-end: compose → match capabilities → route → execute → learn.

This is the full intelligence-allocator flow:
    intent
    → compose (existing)
...

## Calls

- [[core-composer-py-ComposedStructure-to_dict]]
- [[core-execution_bridge-py-FullRealityLoopResult-to_dict]]
- [[core-execution_bridge-py-LearningResult-to_dict]]
- [[core-execution_bridge-py-RealityLoopResult-to_dict]]
- [[core-execution_bridge-py-RoutedLearningResult-to_dict]]
- [[core-orchestrator-pipeline-py-PipelineResult-to_dict]]

## Called By

- [[core-execution_bridge-py-execute_with_full_reality_loop]]
- [[core-execution_bridge-py-execute_with_reality_loop]]
