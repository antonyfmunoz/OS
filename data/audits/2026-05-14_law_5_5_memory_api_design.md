# Law 5.5 Memory API Extension — Design Brief
# Date: 2026-05-14
# Purpose: Phase A scoping for Row 88 runtime layer migration
# Status: TIER 3 COMPLETE — 14 stores, ~50 sites adopted, 0 regressions

---

## Problem

52 of 92 reachable runtime/ modules contain direct SQL (INSERT INTO,
UPDATE SET, DELETE FROM). Law 5.5 requires all database writes to go
through the canonical memory API (`state/memory/memory.py` →
`AgentMemory`). These modules cannot be migrated to §24 homes while
carrying raw SQL — it would spread the violation across the tree.

## Current State of memory.py

`state/memory/memory.py` — 1,006 lines, 2 classes:

### AgentMemory (write API)

| Method | Table | Pattern | Notes |
|--------|-------|---------|-------|
| `log()` | interactions | INSERT | Full interaction record with embedding |
| `log_lead_scored()` | outcomes | INSERT | Lead scoring outcome |
| `log_outcome()` | outcomes | INSERT | Generic outcome linked to interaction |
| `log_standalone_outcome()` | outcomes | INSERT | Outcome without parent interaction |
| `log_orphaned_reply()` | interactions + events | INSERT | Orphaned reply with event |
| `log_event()` | events | INSERT | Generic event (org_id, event_type, payload) |
| `embed_and_store()` | embeddings | INSERT | Vector embedding storage |

### AgentMemory (read API)

| Method | Table | Notes |
|--------|-------|-------|
| `get_interaction_for_lead()` | interactions | By username |
| `get_recent()` | interactions | Paginated |
| `get_outcomes_for()` | outcomes | By interaction_id |
| `get_orphaned_replies()` | interactions | Filtered |
| `semantic_search()` | embeddings | Vector similarity |
| `reply_rate_by_skill()` | outcomes | Aggregation |

### ConversationMemory

Separate class for Discord conversation storage. Not relevant to
Law 5.5 — it already owns its own table cleanly.

---

## SQL Pattern Audit — What the 52 Modules Do

### Category 1: Events table INSERT (33 modules, 46 sites)

The dominant pattern. 33 modules write to the `events` table with
variations of:

```sql
INSERT INTO events (org_id, event_type, payload_json, handled_by)
VALUES (%s, %s, %s, %s)
```

**AgentMemory.log_event() already covers this exactly.** The method
exists, is tested, and 5 modules already use it. The remaining 33
are doing the same operation with raw SQL.

Adoption status:
- **Already using log_event()**: error_handler, coordination_engine,
  knowledge_integrator, meetings (partial)
- **Need to adopt log_event()**: 33 modules (see classification audit)
- **Minor variations**: some pass 3 columns (no handled_by), some
  include extra columns (id, created_at). log_event() handles the
  4-column standard. The 3-column variant needs a default handled_by
  or an optional parameter.

**Estimated API change**: Add `handled_by: str = "runtime"` parameter
to `log_event()` if not already present. ~2 lines changed.

**Estimated downstream changes**: 46 sites across 33 modules —
mechanical replacement:
```python
# Before
with get_conn() as cur:
    cur.execute("INSERT INTO events ...", (...))
# After
from state.memory.memory import AgentMemory
AgentMemory().log_event(org_id, event_type, payload)
```

### Category 2: Events table UPDATE (4 sites in 3 modules)

3 modules update existing event records:

| Module | Pattern | Purpose |
|--------|---------|---------|
| accountability | `UPDATE events SET payload_json = %s WHERE id = %s` | Amend event payload |
| feedback_loop | `UPDATE events SET payload_json = %s WHERE id = %s` (×2) | Amend event payload |
| delegation_tracker | Unclear — needs inspection | |

**New method needed**: `update_event(event_id, payload)` — targeted
payload update by event ID.

**Estimated API change**: ~15 lines (method + SQL + validation).

### Category 3: Domain-specific table writes (19 modules, ~50 sites)

These modules write to tables that AgentMemory doesn't own:

| Table | Operations | Modules | Sites |
|-------|-----------|---------|-------|
| goals | INSERT + UPDATE | goal_selector | 4 |
| goal_outcomes | INSERT | goal_selector | 1 |
| skills | INSERT + UPDATE | claude_skill_registry, knowledge_domains, research_engine, skill_improvement, skill_registry_v2 | 6 |
| ventures | INSERT + UPDATE | business_instance, company_instantiator | 3 |
| model_preferences | INSERT + UPDATE | model_preferences | 6 |
| approvals | INSERT | evolution_engine | 2 |
| agents | INSERT | self_awareness | 2 |
| human_profiles | INSERT | human_intelligence | 1 |
| user_profiles | INSERT | user_model | 1 |
| user_intelligence_profiles | INSERT + UPDATE | os_trinity | 2 |
| cross_product_permissions | INSERT + UPDATE | os_trinity | 2 |
| product_connections | INSERT + UPDATE | os_trinity | 2 |
| tasks | INSERT + UPDATE | coordination_engine, notion_sync | 2 |
| interactions | INSERT | knowledge_integrator | 1 |
| context_compactions | INSERT | context_compaction | 1 |
| embeddings | INSERT + DELETE | embedding_engine | 2 |
| email_folders | INSERT + UPDATE | email_gps | 2 |
| higgsfield_jobs | INSERT + UPDATE | higgsfield_client | 2 |
| outcomes | INSERT | execution_engine | 1 |
| clients | INSERT + UPDATE + DELETE | transaction_workflow | 4 |
| transactions | INSERT + UPDATE | transaction_workflow | 3 |
| fulfillment_events | INSERT | transaction_workflow | 1 |
| offers | INSERT | company_instantiator | 1 |
| entity_links | INSERT | knowledge_graph | 1 |

---

## Proposed API Extension Strategy

### Tier 1: Adopt existing (0 API changes, 46 downstream sites)

`log_event()` already handles the events INSERT pattern. 33 modules
just need to import and call it instead of raw SQL.

If `handled_by` parameter is missing, add it as optional with a
default. This is the single highest-ROI change.

### Tier 2: Small extensions (2 new methods, ~30 lines)

| Method | Table | Signature | Sites covered |
|--------|-------|-----------|---------------|
| `update_event()` | events | `(event_id: str, payload: dict) -> None` | 4 |
| `upsert_embedding()` | embeddings | `(text: str, embedding: list, metadata: dict) -> str` | 2 + 1 DELETE |

### Tier 3: Domain store classes (new files, not memory.py changes)

The remaining ~50 sites write to domain-specific tables (goals, skills,
ventures, agents, etc.). These should NOT be added to AgentMemory —
they're separate domain concerns.

Recommended pattern: one store class per domain table, following the
same `get_conn()` + RLS pattern that AgentMemory uses.

| Store Class | Table(s) | Location | Modules served |
|-------------|----------|----------|---------------|
| GoalStore | goals, goal_outcomes | state/goals/ | goal_selector |
| SkillStore | skills | state/registries/ | claude_skill_registry, knowledge_domains, research_engine, skill_improvement, skill_registry_v2 |
| VentureStore | ventures | state/business/ | business_instance, company_instantiator |
| PreferenceStore | model_preferences | state/preferences/ | model_preferences |
| ApprovalStore | approvals | state/governance/ | evolution_engine |
| AgentStore | agents | state/registries/ | self_awareness |
| ProfileStore | human_profiles, user_profiles, user_intelligence_profiles | state/profiles/ | human_intelligence, user_model, os_trinity |
| PermissionStore | cross_product_permissions, product_connections | state/permissions/ | os_trinity |
| TaskStore | tasks | state/tasks/ | coordination_engine, notion_sync |
| ContextCompactionStore | context_compactions | state/context/ | context_compaction |
| EmailStore | email_folders | state/email/ | email_gps |
| HiggsFieldStore | higgsfield_jobs | adapters/higgsfield/ | higgsfield_client |
| TransactionStore | clients, transactions, fulfillment_events, offers | state/finance/ | transaction_workflow, company_instantiator |
| EntityStore | entity_links | state/knowledge/ | knowledge_graph |

**14 store classes**, each ~30-60 lines. Total: ~500-800 lines of new code.

---

## Risk Surface Analysis

### Does this touch §29 Do-Not-Touch Core?

**No.** The §29 spine modules are:
- cognitive_loop.py (control_plane/runtime/)
- model_router.py (execution/runtime/)
- agent_runtime.py (execution/runtime/)
- execution_spine.py (execution/runtime/)
- db.py (state/storage/)
- memory.py (state/memory/)

The extension is **additive to memory.py** (Tier 1-2: ~30 lines added,
0 existing lines modified). Tier 3 store classes are new files entirely.

`db.py` and `get_conn()` are consumed but not modified.

### What could break?

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| AgentMemory constructor change | None — methods are stateless class methods using module-level ORG_ID | No constructor change needed |
| get_conn() behavior change | None — purely additive | Store classes use same pattern |
| RLS policy violation | Low — all stores use get_conn() which sets RLS | Test each store's write path |
| Transaction isolation | Low — each write is atomic within get_conn() context | Same as current raw SQL |
| Import cycle | Medium — store classes in state/ importing from state/storage/db | Use same import pattern as memory.py |

---

## Scope Estimate

### Phase A-1: Tier 1 adoption (log_event)
- memory.py changes: ~5 lines (add handled_by parameter if needed)
- Downstream: 33 modules, 46 sites — mechanical replacement
- Estimated effort: 1 session
- Risk: LOW

### Phase A-2: Tier 2 methods (update_event, upsert_embedding)
- memory.py changes: ~30 lines
- Downstream: 4 modules, 7 sites
- Estimated effort: same session as A-1
- Risk: LOW

### Phase A-3: Tier 3 domain stores (new files)
- New files: ~14 store classes, ~500-800 lines total
- Downstream: 19 modules, ~50 sites
- Estimated effort: 2-3 sessions (design + implement + verify)
- Risk: MEDIUM (new abstractions, need tests)

### Total Phase A
- ~50 lines added to memory.py
- ~14 new store class files (~600 LOC)
- ~52 modules updated (~100 SQL sites replaced)
- Estimated: 3-4 sessions

---

## Execution Order Recommendation

1. **A-1**: Extend log_event() + adopt across 33 modules (biggest bang)
2. **A-2**: Add update_event() + upsert_embedding() (small, same session)
3. **A-3**: Build domain stores one at a time, starting with highest
   caller-count domains:
   - SkillStore (5 modules)
   - GoalStore (1 module but 5 sites)
   - PreferenceStore (1 module but 6 sites)
   - VentureStore (2 modules)
   - ProfileStore (3 modules)
   - TransactionStore (2 modules) — 0 callers, likely archive
   - Remaining 8 stores

4. After A-1 through A-3: all 52 Law 5.5 modules are clean →
   Phase B (context.py) + Phase C (full migration) can proceed.

---

## Modules Already Law-5.5 Clean (for reference)

40 modules have zero direct SQL. Of these:
- 23 are fully free (migratable now — see classification audit)
- 17 depend on context.py (Phase B prerequisite)

The 15 unreachable modules (Row 89) are archive candidates regardless
of their Law 5.5 status.
