# UMH Execution Boundary Model

**Phase:** 14.6B-UMH (revised 14.6D) | **Status:** DRAFT -- awaiting operator ratification | **Provenance:** CODE_RESOLVED_CURRENT_TRUTH + DEC-146C-002/003 ratification

**Materialization Principle (DEC-146C-002):** If a human can imagine an outcome, UMH should attempt to simulate the path from imagination to materialization. Missing knowledge, resources, tools, capital, information, skill, access, or time does not invalidate the intent -- it creates typed gaps and acquisition paths: research loops, resource acquisition loops, experiment loops, work packets, delegation paths, agent paths, financing paths, and time-bound execution paths. UMH does not treat missing capability as terminal failure. It classifies the gap, identifies what must be acquired or learned, generates the highest-leverage path, and governs execution. If an outcome violates physical reality, law, safety, ethics, or non-negotiable constraints, UMH states the boundary clearly and proposes the nearest lawful/safe/materializable alternative.

**Indivisible Stage 1 (DEC-146C-003):** Governed execution is one of the four indivisible Stage 1 organism components. Execution without memory, governance, and reality model state is unsafe and incoherent.

---

## Three Execution Paths

The codebase contains three distinct execution paths. Only Path 1 is production.

### Path 1: Gateway -> CognitiveLoop -> AgentRuntime (PRODUCTION)
**Flow:** Discord message -> services/discord_bot.py -> Gateway.handle() -> CognitiveLoop.run() -> AgentRuntime.run() -> model_router.call_with_fallback()
**Status:** PRODUCTION -- the only path used by the running os-discord service
**Governance:** Gateway approval logic (always/never approve based on action flags)
**Memory:** CognitiveLoop writes conversation + interaction memory
**Tracing:** CognitiveLoop creates interaction_id, logs to Neon
**Quality:** CognitiveLoop quality loop with max_iterations
**Context:** 8-injection ContextBuilder (identity, memory, domain, behavioral, business, ambient, primitive, persona)

### Path 2: Substrate.execute() -> SignalRouter -> ExecutionSpine (V2)
**Flow:** Substrate.execute(signal) -> ConcreteSignalRouter.route() -> ConcreteExecutionSpine.execute()
**Status:** IMPLEMENTED but NOT in production path
**Governance:** ConcreteGovernanceEngine.classify() -> GovernanceVerdict -> spine gate
**Memory:** Spine writes ConversationMemory + AgentMemory
**Tracing:** TraceRecord with 18 event types, Neon persistence
**Quality:** No quality loop (single-pass)
**Context:** Identity + Context + Governance resolution in router
**Additional:** Simulation dry-run + Deliberation council for HIGH/CRITICAL
**Evidence:** Substrate class is instantiated but not called from discord_bot.py's message handling

### Path 3: Organism WorkPackets (GOVERNED)
**Flow:** Organism work queue -> WorkPacketEngine -> GovernedExecutionSpine -> execution
**Status:** PARTIAL -- work packet engine exists, not primary path
**Governance:** SpineGuard pre-validation + autonomous action gateway
**Memory:** Work packet outcome tracking
**Tracing:** Organism event spine
**Evidence:** 30 cockpit_spine_router endpoints serve work packet management

## Unification Assessment

The three paths have DIFFERENT:
- Governance implementations (Gateway approval vs GovernanceVerdict vs SpineGuard)
- Memory write patterns (CognitiveLoop vs spine vs organism)
- Tracing mechanisms (Neon interaction_id vs TraceRecord vs organism events)
- Quality assurance (quality loop vs single-pass vs work packet verification)

### OPEN QUESTION -- Operator Decision Required
Should these paths be unified into a single execution flow? Options:
1. Keep Path 1 as production, evolve Path 2 as the target architecture, deprecate Path 3's independent execution
2. Merge governance/memory/tracing into a shared substrate layer used by all three paths
3. Designate Path 1 for real-time conversational, Path 2 for programmatic/API, Path 3 for batch/autonomous

## Execution Safety Boundaries

### Materialization Principle Integration (DEC-146C-002)

UMH must distinguish between gap states and true blockers:

| Gap Type | Response | Example |
|----------|----------|---------|
| IMPOSSIBLE | State boundary, propose nearest alternative | Violates physical law |
| ILLEGAL | State boundary, propose lawful alternative | Violates law |
| UNSAFE | State boundary, propose safe alternative | Violates safety/ethics |
| UNAVAILABLE | Generate acquisition path | Tool/resource not currently accessible |
| UNDER_RESOURCED | Generate resource acquisition loop | Insufficient capital/compute/people |
| UNPROVEN | Generate experiment loop | Untested approach |
| NOT_YET_ACQUIRED | Generate research/skill acquisition path | Missing knowledge/skill/access |
| TIME_BOUND | Generate time-bound execution path | Insufficient time in current window |

"Impossible" must not be used as lazy failure language. Each gap generates a typed path, not a dead end.

### What CAN execute automatically
- READ_ONLY operations (memory queries, status checks, analytics, reality-model queries)
- SAFE_WRITE operations (internal logging, memory updates, reality-model observation recording)
- REVERSIBLE_WRITE operations when autonomy level permits
- Deterministic fallback responses (always -- no LLM required)
- Gap classification and acquisition path generation (typed gap → typed path)

### What REQUIRES approval
- IRREVERSIBLE_WRITE (data deletion, schema changes)
- EXTERNAL_COMMUNICATION (emails, DMs, social posts, API calls to third parties)
- FINANCIAL (payments, billing, subscriptions)
- SECURITY_SENSITIVE (auth changes, permission modifications)
- PHYSICAL_WORLD (device control, infrastructure changes)
- Reality-model mutation of source-truth layer (promotes observation to canonical)

### What is ALWAYS blocked
- FORBIDDEN risk class actions
- Actions exceeding autonomy level threshold
- Actions failing simulation dry-run
- Actions rejected by deliberation council
- Outcomes violating physical reality, law, safety, ethics, or non-negotiable constraints (DEC-146C-002)

## Docker Service Execution Context

| Service | What It Executes | Authority |
|---------|-----------------|-----------|
| os-discord | Path 1 (Gateway -> CognitiveLoop). All AI conversations via Discord. | Bot-level: EXECUTE tier, operator approval for HIGH+ |
| os-operator | Cockpit API. Operator commands, approval CRUD, organism control. | Operator-level: COMMIT tier, rate-limited mutations |
| os-webhook | Calendly webhook receiver. Event ingestion only. | Transport-level: READ tier |
| os-scraper | Instagram overnight scraping. Scheduled batch job. | Batch-level: READ tier, no restart |

## Resource Limits (docker-compose.yml)

| Service | Memory | CPU |
|---------|--------|-----|
| os-discord | 1G | 0.5 |
| os-operator | 512M | 0.5 |
| os-scraper | 256M | 0.5 |
| os-webhook | 128M | 0.25 |

## Execution Verification Gaps

1. SimulationReality: Code exists but runtime behavior unverified -- does it actually block in production?
2. DeliberationCouncil: Code exists but runtime behavior unverified -- are all perspectives evaluated?
3. Quality loop in CognitiveLoop: max_iterations logic unverified -- does iteration improve output?
4. Circuit breaker in model_router: Exponential backoff logic unverified -- does it recover correctly?
5. Deterministic fallback: 7 intent patterns with template responses -- are they sufficient?
6. Memory write: Both paths write to Neon -- are writes atomic and consistent?

All marked: RUNTIME VERIFICATION REQUIRED
