---
type: codebase-function
file: core/execution_bridge.py
line: 541
generated: 2026-05-07
---

# execute_with_learning

**File:** [[core-execution_bridge-py]] | **Line:** 541
**Signature:** `execute_with_learning(structure, extra_context) → LearningResult`

Execute with optional feedback → transform → re-execute loop.

This is the extended pipeline flow:
    intent → compose → run_pipeline → evaluate_result
    → transform (if score < threshold) → re-run improved → store trace
...

## Calls

- [[core-composer-py-ComposedStructure-to_dict]]
- [[core-execution_bridge-py-FullRealityLoopResult-to_dict]]
- [[core-execution_bridge-py-LearningResult-to_dict]]
- [[core-execution_bridge-py-RealityLoopResult-to_dict]]
- [[core-execution_bridge-py-RoutedLearningResult-to_dict]]
- [[core-execution_bridge-py-execute_composed]]
- [[core-orchestrator-pipeline-py-PipelineResult-to_dict]]
