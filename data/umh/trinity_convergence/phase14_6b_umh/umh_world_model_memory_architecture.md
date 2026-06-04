# UMH Reality Model and Memory Architecture

Phase: 14.6B-UMH (revised 14.6F)
Status: DRAFT
Generated: 2026-06-03
Revised in Phase 14.6F to align with 18 ratified P0 decisions (2026-06-04).

**Reality Model Context (DEC-146C-001, DEC-146B-UMH-001):** The Universal Meta Harness (UMH) is a reality-isomorphic intelligence harness whose core functional purpose is to build, maintain, and act through an isomorphic approximation of reality across 12 layers: physical, digital, cognitive, biological, social, economic, symbolic, operational, software, memory, source-truth, and OS-level. The world model and memory subsystems documented here ARE the reality model -- the central organizing model through which UMH understands intent, state, constraints, resources, possible actions, consequences, and feedback. This artifact is the closest document to the reality model's architectural intent. Orchestration, governance, execution, memory, adapters, agents, Cockpit, and projections are capabilities/organs serving this reality model.

**Indivisible Stage 1 (DEC-146C-003, RATIFIED 2026-06-04):** Memory is one of the four indivisible Stage 1 organism components (Reality Model + Cockpit + Memory + Governed Execution Loop). Memory without execution is passive storage. Memory feeds the reality model; the reality model feeds execution; execution outcomes update memory. Incremental builds are permitted only if each increment advances the integrated organism across all four components simultaneously.

**Materialization Principle (DEC-146C-002):** The memory and reality model subsystems support the materialization principle -- when UMH encounters a gap between imagined outcome and current state, the reality model classifies the gap type and the memory system tracks acquisition paths (research loops, resource acquisition loops, experiment loops, delegation paths, financing paths). Memory persists not just what is known, but what is not-yet-known and the path to knowing it.

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

`substrate/understanding/world_model/world_model.py` -- Maintains UMH's reality-isomorphic approximation of reality (DEC-146C-001). Represents entities, relationships, and state across the 12 reality layers as perceived through signals, observations, and execution outcomes. This is the core of UMH's identity as a reality-isomorphic intelligence harness (DEC-146B-UMH-001) -- not merely operational tooling, but the central organizing model of reality. The world model is the substrate's primary data structure; all other subsystems exist to perceive into it, reason over it, act from it, and update it.

### World Pulse

`substrate/understanding/world_pulse/world_pulse.py` -- Continuous heartbeat of world state changes. Detects and propagates state transitions through the understanding layer.

### Reality Model Tiers

Three-tier reality model in `substrate/reality_model/`:

| File | Class | Purpose |
|------|-------|---------|
| `canonical.py` | `CanonicalRealityModel` | Source truth -- what the system knows with certainty about reality. The canonical 12-layer reality model (DEC-146C-001). Mutations to canonical state are HIGH/CRITICAL risk governed actions. |
| `instance.py` | `InstanceRealityModel` | Instance reality model -- carries the same isomorphic ambition but from the perspective/context of a specific instantiated user, company, product, environment, or incarnation (DEC-146C-001). Runtime-loaded. Instance values never hardcoded in substrate/. |
| `simulation.py` | `SimulationReality` | Simulation sandbox for the materialization principle (DEC-146C-002). Simulates paths from imagination to materialization. Gap states (unavailable, under-resourced, unproven, not-yet-acquired, time-bound) generate typed acquisition paths; only impossible/illegal/unsafe are true boundaries. |

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

## Isomorphic Reality Model Design Principles (DEC-146C-001)

The world model and memory architecture together implement UMH's isomorphic reality model. Design principles:

1. **Isomorphism over abstraction** -- The model should structurally mirror reality, not abstract it into operational categories. A venture exists in the reality model because it exists in reality, not because UMH needs to "manage" it.
2. **12-layer coverage** -- Every observation enriches at least one reality layer. Observations that do not map to any layer indicate a missing layer or a misclassified signal.
3. **Bidirectional flow** -- Perception updates the model; execution reads from it; outcomes update it again. The cycle is continuous and never terminates.
4. **Gap awareness (DEC-146C-002)** -- The model explicitly represents what is NOT known. Unknown state is typed (unavailable, under-resourced, unproven, not-yet-acquired, time-bound) and generates acquisition paths.
5. **Canonical/instance separation** -- Universal reality model structure lives in substrate/; instance-specific state loads at runtime from BIS/env.
6. **Single execution path (DEC-146B-UMH-003, RATIFIED)** -- All reality-model mutations route through the unified Substrate -> SignalRouter -> Spine execution path.
