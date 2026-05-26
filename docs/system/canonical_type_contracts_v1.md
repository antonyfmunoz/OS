# Canonical Type Contracts — v1

**Established:** 2026-05-25 (Coherence Convergence Phase 2)
**Authority:** This document is the single reference for which types
constitute the substrate's contract layer. All downstream phases
must speak these types at package boundaries.

---

## Contract Registry

All canonical types live in `substrate/types.py` unless noted otherwise.
Every type is a Pydantic BaseModel with validation constraints.

### Signal Layer

| Contract | Location | Purpose |
|----------|----------|---------|
| **SignalEnvelope** | `substrate/types.py:48` | Application-layer signal arriving at the system boundary |
| **SignalEnvelope** (integration) | `substrate/sockets/envelopes.py:14` | Wire-protocol envelope for integration boundary (frozen) |

Two SignalEnvelope types exist intentionally:
- `types.py` version: mutable, signal-scoped, carries user/org/venture context
- `sockets/envelopes.py` version: immutable (frozen=True), integration-scoped, carries integration_id + payload

Signal sources (Discord, API, cron, mesh) create the `types.py` version.
Integration adapters receive the `sockets/envelopes.py` version.

### Intelligence Layer

| Contract | Location | Purpose |
|----------|----------|---------|
| **Intent** | `substrate/types.py:751` | Structured intent after classification (action + target + confidence) |
| **Interpretation** | `substrate/types.py:760` | Full interpretation with intents, entities, sentiment, urgency |

CognitiveLoop currently uses string-based deterministic intent detection
(regex patterns in `detect_intent_and_inject`). The `Intent` Pydantic
model is the structured target for Phase 3 wiring.

### Execution Layer

| Contract | Location | Purpose |
|----------|----------|---------|
| **ExecutionContext** | `substrate/types.py:123` | Assembled context for spine execution (identity + memories + goals) |
| **ExecutionResult** | `substrate/types.py:350` | Complete result of processing a signal through the spine |
| **ExecutionEnvelope** | `execution_contracts_v1.py:380` | Complete proof-chain package for orchestrator (dataclass) |

ExecutionResult vs ExecutionEnvelope:
- `ExecutionResult`: output contract — what the spine produces after processing
- `ExecutionEnvelope`: internal contract — proof chain assembled during pipeline execution

A second `ExecutionResult` (dataclass) exists in `execution_loop.py:48` for
goal-level execution tracking. Code aliases as `CanonicalExecutionResult`.

### Governance Layer

| Contract | Location | Purpose |
|----------|----------|---------|
| **GovernanceVerdict** | `substrate/types.py:267` | Full verdict with risk class, decision, rationale, conditions |
| **GovernanceVerdict** (enum) | `execution_contracts_v1.py:85` | Pipeline-scoped enum (APPROVED/DENIED/REQUIRES_APPROVAL/STRUCTURALLY_FORBIDDEN) |

The canonical GovernanceVerdict (Pydantic) carries full provenance.
The pipeline enum is a simplified decision token. Code aliases as
`CanonicalGovernanceVerdict` where both are in scope.

Decision flow:
```
Structural Deny → Risk Classification → Permission Tier
→ Autonomy Level → Environment Policy → Approval Requirement → Audit Proof
```

### Memory Layer

| Contract | Location | Purpose |
|----------|----------|---------|
| **MemoryEntry** | `substrate/types.py:97` | Canonical memory record (type + content + confidence + tags) |
| **MemoryEntry** (store) | `canonical_memory_store_v1.py:63` | Store-scoped entry with full provenance lineage (dataclass) |
| **MemoryCandidate** | `substrate/types.py:784` | Candidate for promotion into canonical memory |

Two MemoryEntry definitions are intentional:
- `types.py` version: generic, signal-scoped, used by consumers
- `canonical_memory_store_v1.py` version: extends with audit trail
  (memory_id hash, promotion_receipt_id, lineage dict)

### Observability Layer

| Contract | Location | Purpose |
|----------|----------|---------|
| **TraceRecord** | `substrate/types.py:431` | Complete execution trace from signal intake to outcome |
| **TraceEvent** | `substrate/types.py:420` | Single event within a trace |
| **TraceEventType** | `substrate/types.py:398` | Enum of trace event categories |

`Trace = TraceRecord` alias at line 460 for protocol-layer convenience.
Traces are append-only. `add_event()` is the only mutation path.
`complete()` is terminal.

### World Model Layer

| Contract | Location | Purpose |
|----------|----------|---------|
| **WorldModelUpdate** | `substrate/types.py` | Discrete change to the substrate's understanding of reality |
| **WorldModelUpdateType** | `substrate/types.py` | Enum: pattern discovered/invalidated, relationship changed, confidence adjusted, constraint activated/lifted |
| **EnvironmentSnapshot** | `substrate/types.py:719` | Point-in-time view of operating environment |
| **PrimitiveObservation** | `substrate/types.py:578` | Single ontological observation |

WorldModelUpdate captures what changed and why. EnvironmentSnapshot
captures what IS right now. PrimitiveObservation captures what was
observed from a source document.

### Adapter Layer

| Contract | Location | Purpose |
|----------|----------|---------|
| **CapabilityHandler** | `substrate/sockets/protocols.py:77` | Protocol — adapter must describe + handle capabilities |
| **SignalEmitter** | `substrate/sockets/protocols.py:62` | Protocol — adapter can emit signals |
| **OutcomeReceiver** | `substrate/sockets/protocols.py:96` | Protocol — adapter receives execution outcomes |
| **ViewSubscriber** | `substrate/sockets/protocols.py:115` | Protocol — adapter subscribes to view frames |
| **IntegrationManifest** | `substrate/sockets/registry.py:31` | Bundle of protocol implementations for one integration |

No unified "AdapterContract" class. Adapters satisfy Protocols
structurally (Hard Invariant 8). `IntegrationManifest` bundles
the protocol implementations an integration provides.

### Projection Layer

| Contract | Location | Purpose |
|----------|----------|---------|
| **ProjectionContract** | `substrate/types.py` | Declaration a projection provides to register with the substrate |

Every application projection (EOS, CreatorOS, LyfeOS) produces a
ProjectionContract declaring its identity, domains, entity types,
and required adapters.

### Node Mesh Layer

| Contract | Location | Purpose |
|----------|----------|---------|
| **NodeCapability** | `substrate/integrations/node_mesh/types.py:12` | Capability declaration for a mesh node |
| **ConnectedNode** | `substrate/integrations/node_mesh/types.py:20` | Full node state with capabilities + heartbeat |

Re-exported through `transports/node_mesh/registry.py` for
transport-layer consumption.

---

## Dependency Direction

```
projections → transports → adapters → substrate
```

substrate is innermost. It never reaches outward.
All types in this document live in substrate/ or its sockets layer.
Downstream packages import these types — never the reverse.

## Multi-Scope Pattern

Five contracts have intentional duplicates across scope boundaries:
1. SignalEnvelope (application vs integration)
2. GovernanceVerdict (Pydantic vs Enum)
3. ExecutionResult (signal-scoped vs goal-scoped)
4. MemoryEntry (generic vs store-provenance)
5. ExecutionEnvelope (proof chain — distinct from SignalEnvelope)

Where both versions are in scope, code aliases with `Canonical` prefix.
This is by design — different lifecycle stages require different contracts.

## Adding New Contracts

1. Add Pydantic BaseModel to `substrate/types.py`
2. Add entry to this document
3. Verify import: `python3 -c "from substrate.types import NewType"`
4. Update `substrate/__init__.py` exports if public API
