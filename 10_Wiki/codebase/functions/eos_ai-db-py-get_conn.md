---
type: codebase-function
file: eos_ai/db.py
line: 64
generated: 2026-04-11
---

# get_conn

**File:** [[eos_ai-db-py]] | **Line:** 64
**Signature:** `get_conn(org_id) → Generator`

Open a Neon connection inside a transaction with RLS enabled for org_id.

Every transaction begins with SET LOCAL app.current_org_id so the
PostgreSQL RLS firewall scopes all queries to the correct tenant.

...

## Calls

- [[eos_ai-db-py-_load_caches]]

## Called By

- [[core-execution_contract-py-_resolve_session]]
- [[eos_ai-authority_engine-py-AuthorityEngine-_load_org_autonomy]]
- [[eos_ai-authority_engine-py-AuthorityEngine-approve]]
- [[eos_ai-authority_engine-py-AuthorityEngine-get_autonomy_level]]
- [[eos_ai-authority_engine-py-AuthorityEngine-get_pending]]
- [[eos_ai-authority_engine-py-AuthorityEngine-queue_for_approval]]
- [[eos_ai-authority_engine-py-AuthorityEngine-reject]]
- [[eos_ai-context_compaction-py-ContextCompactor-_ensure_table]]
- [[eos_ai-context_compaction-py-ContextCompactor-compact]]
- [[eos_ai-context_compaction-py-ContextCompactor-get_lineage]]
- [[eos_ai-coordination_engine-py-CoordinationEngine-_ensure_table]]
- [[eos_ai-coordination_engine-py-CoordinationEngine-assign_task]]
- [[eos_ai-coordination_engine-py-CoordinationEngine-complete_task]]
- [[eos_ai-coordination_engine-py-CoordinationEngine-get_task_queue]]
- [[eos_ai-event_bus-py-EventBus-_log_event]]
- [[eos_ai-evolution_engine-py-EvolutionEngine-analyze_system_performance]]
- [[eos_ai-evolution_engine-py-EvolutionEngine-detect_new_agent_patterns]]
- [[eos_ai-evolution_engine-py-EvolutionEngine-propose_new_agent]]
- [[eos_ai-evolution_engine-py-EvolutionEngine-propose_workflow_improvement]]
- [[eos_ai-evolution_engine-py-EvolutionEngine-run_weekly_evolution_cycle]]

## Decorators

- `@contextmanager`
