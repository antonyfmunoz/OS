---
type: codebase-function
file: core/execution_bridge.py
line: 812
generated: 2026-05-07
---

# execute_with_reality_loop

**File:** [[core-execution_bridge-py]] | **Line:** 812
**Signature:** `execute_with_reality_loop(structure, constraints, extra_context) → RealityLoopResult`

Full closed-loop: intent → compose → route → execute → ingest reality
→ evaluate objective → transform → re-run if below threshold → store memory.

This replaces the synthetic learning loop with a REAL loop that:
1. Executes the pipeline via execute_with_routing()
...

## Calls

- [[core-composer-py-ComposedStructure-to_dict]]
- [[core-execution_bridge-py-FullRealityLoopResult-to_dict]]
- [[core-execution_bridge-py-LearningResult-to_dict]]
- [[core-execution_bridge-py-RealityLoopResult-to_dict]]
- [[core-execution_bridge-py-RoutedLearningResult-to_dict]]
- [[core-execution_bridge-py-execute_with_routing]]
- [[core-orchestrator-pipeline-py-PipelineResult-to_dict]]
