# Canonical Runtime Contract

**Version:** 1.0
**Date:** 2026-05-27
**Status:** Design lock — defines target architecture for convergence

---

## Target Pipeline

```
Transport/Input
  → SignalEnvelope
  → Substrate ingress (ConcreteSignalRouter.route)
  → GovernanceKernel (classify + authority + policy)
  → ContextBuilder (conversation memory + semantic recall + BIS)
  → ExecutionSpine (perceive → understand → plan → execute → verify → reflect → learn → store)
  → Adapter/Node/Model/HumanApproval
  → Trace/Feedback/MemoryPromotion
  → Response
```

## Contract Definitions

### SignalEnvelope
**Existing:** `substrate/types.py` — `SignalEnvelope` Pydantic model
**Fields:** signal_id, source, content, user_id, timestamp, metadata, risk_class, intent
**Status:** COMPLETE — used by ConcreteSignalRouter and ConcreteExecutionSpine

### Intent
**Existing:** `substrate/types.py` — `Intent` Pydantic model
**Fields:** intent_type, confidence, parameters
**Status:** COMPLETE — populated by regex classification in spine

### ExecutionContext
**Existing:** `substrate/types.py` — `ExecutionContext` Pydantic model
**Fields:** signal_id, identity, conversation_history, relevant_memories, business_context, goals, metadata
**Status:** COMPLETE — assembled by ConcreteContextAssembler

### GovernanceVerdict
**Existing:** `substrate/types.py` — `GovernanceVerdict` Pydantic model
**Fields:** risk_class, authority_level, approved, requires_human, reason, conditions
**Status:** COMPLETE — produced by ConcreteGovernanceEngine.classify()

### ExecutionEnvelope
**Existing:** `substrate/types.py` — `ExecutionEnvelope` Pydantic model
**Fields:** signal, context, verdict, adapter_name, execution_params
**Status:** COMPLETE — used by spine

### ExecutionResult
**Existing:** `substrate/types.py` — `ExecutionResult` Pydantic model
**Fields:** signal_id, content, provider, quality_score, trace_id, metadata
**Status:** COMPLETE — returned by spine.execute()

### TraceRecord
**Existing:** `substrate/types.py` — `TraceRecord` Pydantic model + `substrate/execution/trace.py`
**Fields:** trace_id, signal_id, events, start_time, end_time, provider, quality_score
**Status:** COMPLETE — used by ConcreteExecutionSpine and trace recorder. NOT used by gateway/cognitive_loop (gap).

### MemoryEntry
**Existing:** `substrate/types.py` — `MemoryEntry` Pydantic model
**Fields:** id, memory_type, content, authority_tier, confidence, metadata, created_at
**Status:** COMPLETE

### WorldModelUpdate
**Existing:** `substrate/understanding/world_model/world_model.py` — `WorldModelEntry`
**Status:** EXISTS but not a formal contract. Uses WorldModelEntry dataclass.
**Action needed:** Align WorldModelEntry with substrate/types.py pattern

### AdapterContract
**Existing:** Implicit in adapters/adapter_engine/. No formal Protocol.
**Status:** MISSING as formal contract
**Action needed:** Define Protocol in substrate/sockets/ for adapter registration

### NodeCapability
**Existing:** `transports/node_mesh/registry.py` — `NodeCapability` dataclass
**Status:** COMPLETE but not in substrate/types.py
**Action needed:** Promote to substrate/types.py or substrate/sockets/

### ProjectionContract
**Existing:** `substrate/integrations/product_connections.py` — `IntegrationManifest`
**Status:** EXISTS via IntegrationManifest and IntegrationRegistry
**Action needed:** Formalize as a documented contract

### HumanApprovalRequest
**Existing:** `substrate/governance/policy/authority_engine.py` — approval queue methods
**Status:** EXISTS implicitly (queue_for_approval, approve, reject, get_pending)
**Action needed:** Extract as formal type in substrate/types.py

### RuntimeEvent
**Existing:** `substrate/types.py` — `RuntimeEvent` if present, or `TraceEventType` enum
**Status:** Partial — events are logged to Neon `events` table by gateway
**Action needed:** Formalize event schema

## Type System Location

All canonical types live in `substrate/types.py`. This is the single source of truth.
Types that exist only in domain modules should be promoted here when they become cross-cutting.

## Contract Gaps

1. **Tracing not in production hot path** — gateway/cognitive_loop don't use TraceRecord
2. **AdapterContract missing** — no formal Protocol for adapters
3. **WorldModelUpdate informal** — WorldModelEntry is a dataclass, not Pydantic
4. **HumanApprovalRequest implicit** — exists in AuthorityEngine methods, not as a type
5. **RuntimeEvent informal** — logged to events table but no formal schema
