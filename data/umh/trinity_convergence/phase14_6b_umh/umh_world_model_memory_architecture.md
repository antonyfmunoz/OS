# UMH World Model and Memory Architecture

Phase: 14.6B-UMH
Status: DRAFT
Generated: 2026-06-03

---

## Memory Subsystem

### Core Classes

Two memory classes in `substrate/state/memory/memory.py` (1,039 lines):

- **ConversationMemory** -- Interaction-level memory. Logs leads, outcomes, orphaned replies, events. Provides `semantic_search()` via EmbeddingEngine. Neon-backed persistence. 20+ methods including `log()`, `log_outcome()`, `log_event()`, `get_recent()`, `embed_and_store()`, `semantic_search()`, `reply_rate_by_skill()`.

- **AgentMemory** -- Session-scoped agent memory. Methods: `store()`, `get_session()`, `get_recent()`, `get_by_position()`, `search()`, `get_session_summary()`, `format_session_for_prompt()`. Context-aware initialization via `ctx` parameter.

### MemoryType Enum

Defined in `substrate/types.py` (line 86):

| Value | Key |
|-------|-----|
| `fact` | FACT |
| `belief` | BELIEF |
| `decision` | DECISION |
| `observation` | OBSERVATION |
| `commitment` | COMMITMENT |
| `feedback` | FEEDBACK |
| `relationship` | RELATIONSHIP |
| `domain_projection` | DOMAIN_PROJECTION |

Each memory entry is a `MemoryEntry` Pydantic model with `id`, `memory_type`, `content`, `source_signal_id`, typed fields.

### Canonical Memory Store

`substrate/state/memory/contracts/canonical_memory_store_v1.py` (289 lines) -- Contract for persistent memory storage. Defines the interface that Neon-backed implementations fulfill.

### Memory Promoter

`substrate/memory/promoter.py` (254 lines) -- `MemoryPromoter` class. Promotes observations and signals into persistent memory entries based on salience, relevance, and governance rules. Works alongside:

- `substrate/memory/auto_reconciler.py` -- Automated reconciliation of memory conflicts
- `substrate/memory/candidate_generator.py` -- Generates promotion candidates
- `substrate/memory/watcher.py` -- Watches for promotable signals
- `substrate/memory/claude_bridge.py` -- Bridge for Claude-based memory operations

### Memory Recall

Semantic search via `ConversationMemory.semantic_search()` backed by EmbeddingEngine. Searches stored embeddings in Neon for contextually relevant memory retrieval.

---

## World Model Subsystem

### World Model

`substrate/understanding/world_model/world_model.py` -- Maintains the system's understanding of external reality. Represents entities, relationships, and state as perceived through signals.

### World Pulse

`substrate/understanding/world_pulse/world_pulse.py` -- Continuous heartbeat of world state changes. Detects and propagates state transitions through the understanding layer.

### Reality Model

Three-tier reality model in `substrate/reality_model/`:

| File | Class | Purpose |
|------|-------|---------|
| `canonical.py` | `CanonicalRealityModel` | Source truth -- what the system knows with certainty |
| `instance.py` | `InstanceRealityModel` | Runtime-loaded instance-specific reality (BIS values, env config) |
| `simulation.py` | `SimulationReality` | Dry-run execution sandbox. Enables simulation without production side effects. Used by governance for risk evaluation before actuation. |

### SimulationReality

`SimulationReality` provides an isolated execution context where:
- Work packets can be evaluated without production mutation
- Risk classification can be tested against simulated state
- Governance approval workflows can be previewed
- Cadence dry-run operates within this boundary

---

## Architecture Integration

```
MemoryType (substrate/types.py)
    |
    v
ConversationMemory / AgentMemory (substrate/state/memory/memory.py)
    |                                    |
    v                                    v
CanonicalMemoryStore (contracts/)    EmbeddingEngine (semantic search)
    |                                    |
    v                                    v
Neon PostgreSQL                      Vector similarity recall
    
MemoryPromoter (substrate/memory/promoter.py)
    |
    v
CandidateGenerator -> AutoReconciler -> Watcher
    
WorldModel + WorldPulse (substrate/understanding/)
    |
    v
RealityModel: Canonical / Instance / Simulation (substrate/reality_model/)
```

### Neon Persistence

All memory persistence routes through Neon PostgreSQL. ConversationMemory writes interaction records, embeddings, and event logs. AgentMemory stores session-scoped context. The canonical memory store contract defines the persistence interface.

### Deterministic-First Compliance

Memory recall uses deterministic embedding similarity search as the spine. LLM-enhanced interpretation of recalled memories is optional -- the system returns usable results even when all LLM providers are down.
