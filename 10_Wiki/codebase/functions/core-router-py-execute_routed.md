---
type: codebase-function
file: core/router.py
line: 227
generated: 2026-05-07
---

# execute_routed

**File:** [[core-router-py]] | **Line:** 227
**Signature:** `execute_routed(plan, extra_context) → RoutedExecutionResult`

Execute a routed plan, tracking which capability handles each step.

Injects routing metadata into the pipeline context so every action
knows which capability was selected and why.  After execution,
performance records are updated for adaptive learning.

## Calls

- [[core-capabilities-py-Capability-to_dict]]
- [[core-capabilities-py-PerformanceRecord-to_dict]]
- [[core-capabilities-py-record_outcome]]
- [[core-composer-py-ComposedStructure-to_dict]]
- [[core-matcher-py-CapabilityScore-to_dict]]
- [[core-matcher-py-CapabilitySelection-to_dict]]
- [[core-orchestrator-pipeline-py-PipelineResult-to_dict]]
- [[core-orchestrator-pipeline-py-run_pipeline]]
- [[core-router-py-ExecutionPlan-to_dict]]
- [[core-router-py-RoutedExecutionResult-to_dict]]
- [[core-router-py-RoutedStep-to_dict]]
