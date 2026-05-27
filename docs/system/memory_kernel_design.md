# Memory Kernel Design

**Version:** 1.0
**Date:** 2026-05-27
**Status:** Design document — unification plan for memory convergence

---

## Current State

20+ memory-related components across 4 directories:

### Primary Storage (substrate/state/memory/)
| Component | Type | Backend | Production? |
|-----------|------|---------|-------------|
| AgentMemory | Episodic (interaction log) | Neon PostgreSQL | YES |
| ConversationMemory | Verbatim conversation store | Neon PostgreSQL | YES |
| CanonicalMemoryStore | Promoted canonical memories | JSONL files | No (reconciliation only) |
| ReconciliationEngine | Dedup/strengthen/conflict | JSONL receipts | No |
| MemoryConflictGovernance | Conflict resolution | JSONL | No |
| MemoryIdentity | Identity fingerprints | JSONL | No |

### Memory Lifecycle (substrate/memory/)
| Component | Type | Backend | Production? |
|-----------|------|---------|-------------|
| MemoryCandidateGenerator | Candidate staging | JSONL | No |
| MemoryPromoter | Promotion gate (3-layer dedup) | JSON | No |
| AutoReconciler | Bridge to canonical store | Delegates | No |
| ClaudeMemoryBridge | CC session → substrate sync | File + hash | No |
| MemoryWatcher | Filesystem watcher daemon | Watchdog | No |

### World/Reality Models
| Component | Type | Backend | Production? |
|-----------|------|---------|-------------|
| WorldModel | Two-layer world model | Key-value store | Partial |
| CanonicalRealityModel | Graph-based reality | JSON | No (spine future) |
| InstanceRealityModel | Temporal observations | JSONL | No |
| SimulationReality | Hypothesis testing | Ephemeral clones | Partial (spine) |

### Intelligence
| Component | Type | Backend | Production? |
|-----------|------|---------|-------------|
| IntelligenceRuntime | Pattern/decision learning | JSON | Partial (cognitive loop) |
| EmbeddingEngine | 3-tier embedding | Neon (384-dim vectors) | YES |
| Embedder | Lightweight singleton | In-memory | YES |
| EmbeddingStore | Neon write API | Neon PostgreSQL | YES |

### Protocol/Wrapper
| Component | Type | Production? |
|-----------|------|-------------|
| ConcreteMemorySystem | Facade over AgentMemory + ConversationMemory | YES (bugs fixed this session) |
| MemoryScopeContracts | Policy: what can be promoted to global canon | N/A (contract only) |

---

## Target: Unified MemoryKernel

The MemoryKernel organizes all memory as strata — distinct layers that serve
different temporal and semantic purposes. Each stratum has a clear read/write
API and a defined lifecycle.

### Strata Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    QUERY INTERFACE                          │
│  recall(query, strata, scope) → ranked MemoryEntry[]       │
│  context_for_prompt(session_id, channel) → formatted text  │
├─────────────────────────────────────────────────────────────┤
│ Stratum 1: EPISODIC MEMORY                                 │
│   AgentMemory — every interaction logged to Neon            │
│   Retention: permanent                                     │
│   Backend: Neon interactions table                          │
├─────────────────────────────────────────────────────────────┤
│ Stratum 2: CONVERSATION MEMORY                             │
│   ConversationMemory — verbatim message store               │
│   Retention: permanent (per session)                        │
│   Backend: Neon messages table                              │
├─────────────────────────────────────────────────────────────┤
│ Stratum 3: SEMANTIC MEMORY                                 │
│   EmbeddingEngine + EmbeddingStore — vector similarity      │
│   Retention: permanent                                      │
│   Backend: Neon embeddings table (384-dim)                  │
├─────────────────────────────────────────────────────────────┤
│ Stratum 4: CANONICAL MEMORY                                │
│   CanonicalMemoryStore — promoted, reconciled, governed     │
│   Retention: permanent (with confidence decay)              │
│   Backend: JSONL → migrate to Neon                          │
├─────────────────────────────────────────────────────────────┤
│ Stratum 5: BEHAVIORAL MEMORY                               │
│   IntelligenceRuntime — learned patterns + decisions        │
│   Retention: permanent (pattern reinforcement)              │
│   Backend: JSON → migrate to Neon                           │
├─────────────────────────────────────────────────────────────┤
│ Stratum 6: ENTITY MEMORY                                   │
│   WorldModel + RealityModel — entity relationships          │
│   Retention: temporal decay (14-180 day half-life)          │
│   Backend: JSON/JSONL → migrate to Neon                     │
├─────────────────────────────────────────────────────────────┤
│ Stratum 7: RECONCILIATION                                  │
│   ReconciliationEngine — dedup, strengthen, conflict        │
│   Not a store — a pipeline between candidates and canonical │
├─────────────────────────────────────────────────────────────┤
│ Stratum 8: PROMOTION                                       │
│   MemoryCandidateGenerator → MemoryPromoter → AutoReconciler│
│   Pipeline: stage → evaluate → promote → reconcile          │
├─────────────────────────────────────────────────────────────┤
│ Stratum 9: SESSION BRIDGE                                  │
│   ClaudeMemoryBridge + MemoryWatcher                        │
│   Syncs external agent memory into the promotion pipeline   │
├─────────────────────────────────────────────────────────────┤
│ Stratum 10: WORLD MODEL OBSERVATIONS                       │
│   WorldModel.update_from_interaction() — heuristic tagging  │
│   Feeds into entity memory stratum                          │
└─────────────────────────────────────────────────────────────┘
```

---

## Existing System Mapping

| Stratum | Existing Component(s) | Status |
|---------|----------------------|--------|
| Episodic | AgentMemory | COMPLETE — keep as-is |
| Conversation | ConversationMemory | COMPLETE — keep as-is |
| Semantic | EmbeddingEngine + Embedder + EmbeddingStore | COMPLETE — keep as-is |
| Canonical | CanonicalMemoryStore | COMPLETE — migrate backend to Neon |
| Behavioral | IntelligenceRuntime | PARTIAL — needs Neon backend |
| Entity | WorldModel + RealityModel | OVERLAP — unify into single entity model |
| Reconciliation | ReconciliationEngine | COMPLETE — keep as-is |
| Promotion | MemoryCandidateGenerator + MemoryPromoter + AutoReconciler | COMPLETE — keep pipeline |
| Session Bridge | ClaudeMemoryBridge + MemoryWatcher | COMPLETE — keep as-is |
| World Model | WorldModel.update_from_interaction() | PARTIAL — needs formal integration |

---

## Known Bugs (Fixed This Session)

### 1. ConversationMemory init without ctx (FIXED)
**Files affected:**
- `substrate/control_plane/memory.py:42` — ConcreteMemorySystem.__init__()
- `substrate/control_plane/context/__init__.py:69` — fallback import

**Fix:** Made ctx optional in ConcreteMemorySystem, passes it when available.
Added SimpleNamespace(org_id=...) in context/__init__.py fallback.

### 2. ConcreteMemorySystem.store() wrong API (FIXED)
**Problem:** Called `embed_and_store(content=..., memory_type=..., metadata=...)`
but actual signature is `embed_and_store(interaction_id, text)`.
**Fix:** Changed to use `log_event()` which matches the intent.

### 3. ConcreteMemorySystem.log_interaction() wrong API (FIXED)
**Problem:** Called `log(content=..., response=..., provider=...)`
but actual signature expects `(agent_result, venture_id, input_summary, ...)`.
**Fix:** Create SimpleNamespace agent_result and pass correctly.

---

## WorldModel vs RealityModel Overlap

Both implement a two-layer canonical+instance knowledge store with:
- Confidence scoring
- Temporal decay
- Promotion from instance to canonical
- Search/query

**Differences:**
| Aspect | WorldModel | RealityModel |
|--------|-----------|--------------|
| Storage | Key-value store | JSON/JSONL files |
| Schema | WorldModelEntry dataclass | Pydantic models |
| Relationships | None | Entity graph edges |
| Simulation | None | SimulationReality sandbox |
| Governance | None | Governance-gated updates |
| Decay | None built-in | 14-day (instance) / 180-day (canonical) half-life |

**Resolution:** RealityModel is the more complete implementation. WorldModel should
be deprecated and its `update_from_interaction()` logic merged into RealityModel
as a convenience method.

---

## Migration Plan

### Phase 1 (Safe): Fix bugs — DONE this session
- ConversationMemory init
- ConcreteMemorySystem API mismatches

### Phase 2 (Medium): Wire promotion pipeline into cognitive loop
- After every CognitiveLoop.run(), generate memory candidates
- Use existing MemoryCandidateGenerator → MemoryPromoter flow
- This brings the CANONICAL_FUTURE memory lifecycle into production

### Phase 3 (Medium): Unify WorldModel + RealityModel
- Merge WorldModel.update_from_interaction() into RealityModel
- Deprecate WorldModel class
- Update callers (cognitive_loop, pipeline)

### Phase 4 (Medium): Migrate file-based stores to Neon
- CanonicalMemoryStore: JSONL → Neon table
- IntelligenceRuntime: JSON → Neon table
- RealityModel: JSON/JSONL → Neon table
- This eliminates file I/O bottlenecks and enables RLS

### Phase 5 (High): Create unified MemoryKernel API
- Single query interface across all strata
- `kernel.recall(query, strata=[...], scope=...)` → ranked results
- `kernel.context_for_prompt(session_id)` → formatted context string
- Replace ConcreteMemorySystem with MemoryKernel

## Tests Required

- ConversationMemory init: passes with ctx, degrades gracefully without
- AgentMemory.log(): still writes correctly (regression test)
- Promotion pipeline: candidate → promote → reconcile → stored
- Embedding: search returns semantically relevant results
- WorldModel → RealityModel merge: entity relationships preserved
