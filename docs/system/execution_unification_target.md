# Execution Unification Target — P5 Reference

Produced from 2026-05-27 exhaustive audit. This documents the current execution
paths and the target unified architecture. No code changes — reference only.

## Current State: Three Parallel Execution Paths

### Path 1: CognitiveLoop (PRIMARY — what runs today)

```
EntrepreneurOSGateway.handle(request: dict)
  → CognitiveLoop.run()
    1. PERCEIVE:    MultimodalInput resolution (audio/video/document → text)
    2. UNDERSTAND:  ContextBuilder assembly (knowledge, memory, philosophy, patterns)
    3. PLAN:        AuthorityEngine.check_can_execute() — approval gating
    4. EXECUTE:     AgentRuntime.run() → model_router.call_with_fallback()
    5. VERIFY:      Quality loop (up to 3 iterations, GENERATE tasks only)
    6. REFLECT:     Extract learnings
    7. LEARN:       AgentMemory.log + KnowledgeIntegrator + IntelligenceRuntime
    8. STORE:       Memory writes
  → CognitiveResult
```

Files:
- substrate/control_plane/runtime/gateway.py (2,063 lines)
- substrate/control_plane/runtime/cognitive_loop.py (1,448 lines)

### Path 2: SubstrateGateway (BRIDGE — thin wrapper)

```
SubstrateGateway.handle(signal: SignalEnvelope)
  → Convert envelope to dict
  → Delegate to EntrepreneurOSGateway.handle()
  → Convert response to ExecutionResult
```

File: substrate/control_plane/runtime/substrate_gateway.py

### Path 3: SignalRouter (FUTURE — protocol only)

```
ConcreteSignalRouter.route(signal: SignalEnvelope)
  → IdentityResolver.resolve(signal)
  → ContextAssembler.assemble(signal, identity)
  → GovernanceEngine.classify(signal, context) → verdict
  → ExecutionSpine.execute(signal, context, verdict)
  → ExecutionResult with trace
```

Files:
- substrate/control_plane/router/__init__.py (protocol)
- substrate/execution/spine.py (protocol)
- substrate/execution/runtime/execution_spine.py (legacy sync impl)

## Divergence Points

| Component     | CognitiveLoop Path          | Substrate/Router Path        |
|---------------|----------------------------|------------------------------|
| Entry format  | dict                       | SignalEnvelope               |
| Context       | ContextBuilder             | ContextAssembler (protocol)  |
| Governance    | AuthorityEngine            | GovernanceEngine             |
| Memory        | AgentMemory + CanonicalStore | MemorySystem protocol       |
| Execution     | AgentRuntime → model_router | ExecutionSpine (protocol)   |
| Trace         | error_recorder + footer    | TraceRecord (protocol)       |
| Fallback      | _deterministic_cognitive_response() | _deterministic_response() |

## Target: Unified Execution Path

```
Interface (Discord / Cockpit / API / Node Mesh)
  → SignalEnvelope (canonical input format)
  → Substrate.execute()
    → GovernanceKernel (merged AuthorityEngine + GovernanceEngine)
    → Memory/WorldModel (unified CanonicalMemoryStore + AgentMemory)
    → ExecutionSpine (8-stage pipeline, async)
      1. PERCEIVE
      2. UNDERSTAND
      3. PLAN (governance gate)
      4. EXECUTE (via Adapter/Node/Human Approval)
      5. VERIFY
      6. REFLECT
      7. LEARN
      8. STORE
    → Trace/Feedback (unified observability)
  → ExecutionResult
```

## Constraint: Don't Break DEX

The Discord bot (os-discord) runs production today through Path 1.
Unification must be incremental — each step must keep DEX functional.

## Implementation Order (when P5 begins)

1. Make Gateway accept SignalEnvelope alongside dict (dual input)
2. Merge AuthorityEngine + GovernanceEngine → single GovernanceKernel
3. Unify memory into one MemorySystem interface
4. Wire ExecutionSpine as async, delegate to CognitiveLoop stages
5. Remove SubstrateGateway bridge (replaced by unified path)
6. Wire node mesh + workstation + cockpit into the same spine
