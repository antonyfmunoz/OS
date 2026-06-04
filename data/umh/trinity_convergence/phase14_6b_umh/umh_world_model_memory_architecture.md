# UMH Reality Model and Memory Architecture

Phase: 14.6B-UMH (revised 14.6D)
Status: DRAFT
Generated: 2026-06-03

**Reality Model Context (DEC-146C-001):** UMH's core functional purpose is to build, maintain, and act through a reality-isomorphic approximation of reality across 12 layers: physical, digital, cognitive, biological, social, economic, symbolic, operational, software, memory, source-truth, and OS-level. The world model and memory subsystems documented here are the implementation of UMH's reality model -- the central organizing model through which UMH understands intent, state, constraints, resources, possible actions, consequences, and feedback.

**Indivisible Stage 1 (DEC-146C-003):** Memory is one of the four indivisible Stage 1 organism components (Reality Model + Cockpit + Memory + Governed Execution Loop). Memory without execution is passive storage. Memory feeds the reality model; the reality model feeds execution; execution outcomes update memory.

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

## Reality Model Subsystem

### World Model (Reality Model Core)

`substrate/understanding/world_model/world_model.py` -- Maintains UMH's reality-isomorphic approximation of reality (DEC-146C-001). Represents entities, relationships, and state across the 12 reality layers as perceived through signals, observations, and execution outcomes. This is the core of UMH's identity -- not merely operational tooling, but the central organizing model of reality.

### World Pulse

`substrate/understanding/world_pulse/world_pulse.py` -- Continuous heartbeat of world state changes. Detects and propagates state transitions through the understanding layer.

### Reality Model Tiers

Three-tier reality model in `substrate/reality_model/`:

| File | Class | Purpose |
|------|-------|---------|
| `canonical.py` | `CanonicalRealityModel` | Source truth -- what the system knows with certainty about reality. The canonical 12-layer reality model (DEC-146C-001). |
| `instance.py` | `InstanceRealityModel` | Instance reality model -- carries the same isomorphic ambition but from the perspective/context of a specific instantiated user, company, product, environment, or incarnation (DEC-146C-001). Runtime-loaded. |
| `simulation.py` | `SimulationReality` | Dry-run execution sandbox. Enables simulation without production side effects. Used by governance for risk evaluation before actuation. Implements part of the materialization principle (DEC-146C-002) -- simulates paths from intent to outcome. |

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
