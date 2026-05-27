# Current Runtime Paths

**Date:** 2026-05-27
**Source:** Code trace analysis of all 5 execution paths

---

## Path A: Gateway (PRIMARY PRODUCTION)

**File:** `substrate/control_plane/runtime/gateway.py`
**Class:** `EntrepreneurOSGateway` (singleton via `get_gateway()`)

| Dimension | Detail |
|-----------|--------|
| Caller | `services/discord_bot.py` (line 199), overnight_scrape, email_gps, orchestrator |
| Entry | `handle(request)` — sync |
| Governance | Approval gate (`_requires_approval`), QualityTransformationGate (output) |
| Memory | ConversationMemory, KnowledgeIntegrator, AccountabilityEngine, DecisionLog |
| Tracing | Events table (NOT trace.py) |
| Model routing | Via CognitiveLoop → AgentRuntime → model_router.call_with_fallback |
| Production | **YES — handles all Discord messages** |
| Convergence target | Migrate to use ConcreteExecutionSpine internally |

### Flow
```
handle(request)
  → validate
  → approval gate (external actions: DMs, payments, deletes)
  → route: automation / email / agent_task / event / status / brief
  → _route_agent_task()
    → CognitiveLoop(ctx).run()
    → store conversation memory
    → quality gate output
  → response
```

---

## Path B: CognitiveLoop (INNER PRODUCTION)

**File:** `substrate/control_plane/runtime/cognitive_loop.py`
**Class:** `CognitiveLoop` (instantiated per-request)

| Dimension | Detail |
|-----------|--------|
| Caller | Gateway._route_agent_task(), strategy_engine, coordination_engine, research_engine |
| Entry | `run(input, agent, task_type, venture_id, ...)` — sync |
| Governance | AuthorityEngine.check_can_execute() with approval queuing |
| Memory | AgentMemory, ContextBuilder (semantic + conversation), MemoryPromoter, IntelligenceRuntime |
| Tracing | Internal reflection logging (NOT trace.py) |
| Model routing | AgentRuntime.run() → model_router.call_with_fallback() |
| Production | **YES — always entered through Gateway** |
| Convergence target | Extract stages into ExecutionSpine protocol |

### 8-Stage Cycle
```
PERCEIVE → multimodal input + context build
UNDERSTAND → pattern matching, memory query-back, philosophy lenses
PLAN → AuthorityEngine check
EXECUTE → AgentRuntime.run()
VERIFY → quality loop (up to 3 iterations)
REFLECT → extract learnings
LEARN → log to Neon, knowledge integration, intelligence runtime
STORE → handled by AgentRuntime
```

---

## Path C: ConcreteExecutionSpine (CANONICAL FUTURE)

**File:** `substrate/execution/spine.py`
**Class:** `ConcreteExecutionSpine` (implements `ExecutionSpine` Protocol)

| Dimension | Detail |
|-----------|--------|
| Caller | Substrate.__init__() → ConcreteSignalRouter.route() |
| Entry | `async execute(signal, context, verdict)` — async |
| Governance | GovernanceVerdict (pre-classified) + SimulationReality + DeliberationCouncil |
| Memory | ConversationMemory + AgentMemory (mandatory writes) |
| Tracing | **YES — TraceRecord with proper events** |
| Model routing | model_router.call_with_fallback via asyncio.to_thread |
| Production | Loaded by operator.py but not deployed |
| Convergence target | **This IS the target** |

### 8 Async Stages
```
0a. Governance gate (verdict check)
0b. SimulationReality (HIGH/CRITICAL dry-run)
0c. DeliberationCouncil (HIGH/CRITICAL advisory)
1. Interpret (regex intent classification)
2. Recall (memory search)
3. Lookup (adapter registry)
4. Compose (build prompt)
5. Route+Execute (call_with_fallback)
6. Trace recording
7. Feedback + knowledge gap + mandatory memory writes
```

---

## Path D: ExecutionPipeline (MOST COMPLETE, NOT DEPLOYED)

**File:** `substrate/execution/pipeline.py`
**Class:** `ExecutionPipeline`

| Dimension | Detail |
|-----------|--------|
| Caller | transports/api/app.py, organism/daemon.py, organism/worker_cell.py |
| Entry | `submit_signal(content, source, risk_class, adapter_name, ...)` — sync |
| Governance | PolicyEngine + MasteryGate + DeliberationCouncil + CompletenessEngine (5 gates) |
| Memory | MemoryCandidateGenerator → MemoryPromoter → AutoReconciler (full lifecycle) |
| Tracing | **YES — Trace events + TraceStore (JSONL)** |
| Model routing | Via WorkPacketExecutor (indirect) |
| Production | **NO — transports/api/app.py is not deployed** |
| Convergence target | Merge best ideas into ConcreteExecutionSpine |

### Full Pipeline
```
Signal creation → Protocol trace
→ UnderstandingBridge (interpret, decompose, domain, laws, reality)
→ MasteryGate check
→ DeliberationCouncil (high-risk)
→ PolicyEngine governance
→ WorkPacket → WorkPacketExecutor.execute()
→ Proof generation
→ OutcomeClassifier
→ IntelligenceRuntime learning
→ TraceStore
→ MemoryCandidateGenerator → MemoryPromoter → AutoReconciler
→ Reality Model update
→ HomeostasisEngine
→ CompletenessEngine
```

---

## Path E: Legacy Runtime ExecutionSpine (OPERATOR API)

**File:** `substrate/execution/runtime/execution_spine.py`
**Class:** `ExecutionSpine` (explicitly marked "legacy" in docstring)

| Dimension | Detail |
|-----------|--------|
| Caller | services/operator_api.py (line 84) |
| Entry | `run(message, unified_context, agent_type, ...)` — sync |
| Governance | AuthorityEngine.check_can_execute() |
| Memory | ConversationMemory + AgentMemory (mandatory writes) |
| Tracing | **NO** — only stdout timing |
| Model routing | model_router.call_with_fallback() direct |
| Production | **YES — os-operator container on port 8091** |
| Convergence target | Migrate callers to ConcreteExecutionSpine (Path C) |

### Linear 5-Step
```
1. Authority validation
2. LLM call via call_with_fallback
3. Deterministic fallback if all fail
4. Mandatory memory writes
5. Session persistence to SubstrateStorage
```

---

## Convergence Plan

### Phase 1 (safe): Wire tracing into Path A/B
Gateway and CognitiveLoop should create TraceRecords for observability.

### Phase 2 (medium): Migrate Path E → Path C
Replace legacy ExecutionSpine in operator_api with ConcreteExecutionSpine.
This gives the operator API proper tracing and governance verdicts.

### Phase 3 (medium): Absorb Path D innovations into Path C
Bring MemoryCandidateGenerator, UnderstandingBridge, CompletenessEngine
from ExecutionPipeline into ConcreteExecutionSpine.

### Phase 4 (high): Migrate Path A/B → Path C
Refactor Gateway to create SignalEnvelopes and route through
ConcreteSignalRouter → ConcreteExecutionSpine, replacing the
direct CognitiveLoop instantiation.

### Phase 5 (decommission): Remove Paths D and E
Once Path C handles all traffic, remove ExecutionPipeline and
legacy ExecutionSpine.
