---
type: codebase-function
file: core/execution_bridge.py
line: 468
generated: 2026-05-07
---

# execute_composed

**File:** [[core-execution_bridge-py]] | **Line:** 468
**Signature:** `execute_composed(structure, extra_context) → PipelineResult`

End-to-end: compose → build pipeline → execute.

Injects primitive trace and composition metadata into the pipeline
context so every action carries its ontological lineage.

## Calls

- [[core-composer-py-ComposedStructure-to_dict]]
- [[core-execution_bridge-py-FullRealityLoopResult-to_dict]]
- [[core-execution_bridge-py-LearningResult-to_dict]]
- [[core-execution_bridge-py-RealityLoopResult-to_dict]]
- [[core-execution_bridge-py-RoutedLearningResult-to_dict]]
- [[core-execution_bridge-py-build_pipeline]]
- [[core-orchestrator-pipeline-py-PipelineResult-to_dict]]
- [[core-orchestrator-pipeline-py-run_pipeline]]

## Called By

- [[core-execution_bridge-py-execute_with_learning]]
