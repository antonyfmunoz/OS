# UMH Universal Capability Pipeline

**Phase:** 14.6B-UMH
**Status:** DRAFT -- awaiting operator ratification
**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

This document formalizes the core capability pipeline available to Cockpit and projections.

---

## Pipeline Stages

### 1. Intake
**What:** Signal enters the system
**Code:** substrate/sockets/signal_socket.py, transports/discord/signal_factory.py, transports/api/signal_factory.py
**Type:** SignalEnvelope (id, source, urgency, modality, content, user/org/venture IDs, authority_tier, attachments, metadata)
**Sources:** Discord message, API request, scheduled trigger, internal event, adapter output, node mesh, organism

### 2. Ingestion
**What:** Raw input is perceived and normalized
**Code:** substrate/understanding/perception/orchestrator.py (1,157 lines), substrate/execution/ingestion/
**Process:** Multimodal resolution (voice->text via Whisper, image->text, document parsing)
**Fallback:** Raw text pass-through if perception fails

### 3. Signal Classification
**What:** Determine intent and urgency
**Code:** substrate/execution/spine.py (_INTENT_PATTERNS -- 7 regex patterns), substrate/control_plane/runtime/gateway.py (classify_intent -- 12 categories)
**Intents:** schedule, send, status, analysis, question, command, greeting + ai_naming, memory_query, approval, automation, rename
**Deterministic-first:** Regex patterns before any LLM call

### 4. Decomposition
**What:** Break complex input into primitive observations
**Code:** substrate/understanding/ontology/primitive_decomposition_v1.py, adapters/adapter_engine/substrate_decomposer_v1.py
**Output:** PrimitiveObservation (primitive_type, label, description, evidence, relationships)
**Primitive types:** STATE, CHANGE, CONSTRAINT, RESOURCE, SIGNAL, ACTION, OUTCOME, FEEDBACK, GOAL, TIME

### 5. Context Assembly
**What:** Build execution context from identity, memory, conversation history, business context
**Code:** substrate/control_plane/context/ (ConcreteContextAssembler), substrate/control_plane/runtime/cognitive_loop.py (ContextBuilder)
**Layers:** Identity -> semantic memory -> conversation history -> domain knowledge -> behavioral principles -> business instance -> ambient reality -> primitives -> persona -> agent hierarchy
**Output:** ExecutionContext (identity, conversation_history, session_id)

### 6. Memory Recall
**What:** Search for relevant prior context
**Code:** substrate/state/memory/memory.py (ConversationMemory.recall(), AgentMemory), substrate/state/memory/contracts/canonical_memory_store_v1.py
**Methods:** Neon-backed recall with relevance scoring, canonical memory store query-back
**Fallback:** Empty context if memory unavailable

### 7. Data Boundary Check
**What:** Verify data access permissions
**Code:** substrate/governance/policy/confidentiality.py, substrate/state/permissions/
**Status:** PARTIAL -- confidentiality classification exists but projection-level data boundary enforcement not fully implemented
**GAP:** No automated cross-projection data access control

### 8. Governance / Risk Classification
**What:** Classify risk and determine execution authority
**Code:** substrate/governance/risk_classes.py (8 ActionRiskCategory -> 5 RiskClass), substrate/control_plane/governance.py (ConcreteGovernanceEngine)
**Risk categories:** READ_ONLY->NEGLIGIBLE, SAFE_WRITE->LOW, REVERSIBLE_WRITE->MEDIUM, IRREVERSIBLE_WRITE->HIGH, EXTERNAL_COMMUNICATION->HIGH, FINANCIAL->CRITICAL, SECURITY_SENSITIVE->CRITICAL, PHYSICAL_WORLD->CRITICAL
**Blocking:** IRREVERSIBLE_WRITE, EXTERNAL_COMMUNICATION, FINANCIAL, SECURITY_SENSITIVE, PHYSICAL_WORLD require approval
**Simulation:** SimulationReality dry-run for HIGH/CRITICAL
**Deliberation:** DeliberationCouncil multi-perspective review for HIGH/CRITICAL

### 9. Planning
**What:** Generate execution plan
**Code:** substrate/control_plane/goals/ (GoalSelector), substrate/execution/spine.py (compose stage)
**Process:** Intent-aware prompt composition with full context injection
**Deterministic:** Template responses available for every intent type

### 10. Capability Routing
**What:** Find capable adapters and tools
**Code:** substrate/execution/runtime/capability_router.py (28 Capability enum values), substrate/types.py (ComponentType.ADAPTER)
**Capabilities:** GENERAL_RESPONSE through COORDINATE (28 total)
**Registry:** ConcreteComponentRegistry with component lookup by type

### 11. Model Routing
**What:** Select LLM provider for execution
**Code:** adapters/models/model_router.py (call_with_fallback), adapters/models/cc_sdk.py, adapters/models/agent_runtime.py
**Chain:** CLAUDE_CLI -> CC_SDK -> GEMINI -> GROQ -> ANTHROPIC -> PERPLEXITY -> OLLAMA -> CODEX -> HERMES -> OPENCODE
**Fast path:** Separate priority chain for fast tasks (conversation, score, classify, summarize)
**Quality escalation:** Below 0.40 threshold -> escalate to cc_sdk
**Circuit breaker:** Exponential backoff (30s base, 300s cap)
**Deterministic fallback:** Intent-aware heuristic responses if all providers fail

### 12. Tool Routing
**What:** Route to external tools/services when needed
**Code:** adapters/tool_adapters/ (filesystem, git, shell, tmux), adapters/google_workspace/, adapters/calendar/, adapters/notion/, adapters/capabilities/
**Tools:** Google Workspace, Calendar, Notion, GitHub, filesystem, git, shell, tmux, browser exports, Higgsfield, Kokoro TTS, Goose, UI-TARS

### 13. Agent/Workflow Orchestration
**What:** Coordinate multi-step or multi-agent work
**Code:** substrate/organism/ (201 files, 70,126 lines), projections/eos/workflows/, substrate/execution/bridge/
**Orchestration:** Organism coordinator, workcell protocol, autonomous tick, template registry
**Workflows:** OutreachWorkflow, FollowUpWorkflow, ContentCalendarWorkflow (EOS-specific)

### 14. Execution
**What:** Execute the planned action
**Code:** substrate/execution/spine.py (Route+Execute stages), adapters/models/model_router.py (call_with_fallback)
**Principle:** Deterministic result FIRST, then AI enhancement. If AI produces better result, use it. If AI fails, deterministic result already available.
**Simulation:** SimulationReality blocks unsafe actions before execution
**Council:** DeliberationCouncil blocks rejected actions

### 15. Verification
**What:** Verify output quality
**Code:** substrate/governance/quality/quality_gate.py (QualityTransformationGate), substrate/governance/validation/
**Quality lens:** 4-value scoring (completeness, relevance, safety, accuracy)
**Loop:** Up to max_iterations quality improvement cycles (skipped for fast tasks)

### 16. Audit
**What:** Record execution trace
**Code:** substrate/execution/trace.py (ConcreteTraceRecorder), substrate/observability/proof_store.py, substrate/observability/trace_store.py
**Storage:** In-memory + Neon persistence
**Events:** TraceEventType (18 types including SIGNAL_RECEIVED, GOVERNANCE_DECIDED, MEMORY_RECALLED, PLAN_COMPOSED, ADAPTER_CALLED, ADAPTER_RESPONDED, EXECUTION_COMPLETED, ERROR)

### 17. Feedback / Learning
**What:** Capture quality signal for learning loop
**Code:** substrate/execution/feedback.py (ConcreteFeedbackCapture), substrate/composition/knowledge_gap_trigger.py
**Quality map:** SUCCESS=0.8, PARTIAL=0.6, BLOCKED=0.5, FAILURE=0.2, TIMEOUT/REJECTED=0.1
**Gap detection:** KnowledgeGapTrigger detects missing knowledge from execution outcomes

### 18. Memory Write
**What:** Persist conversation and interaction to memory
**Code:** substrate/state/memory/memory.py (ConversationMemory.store(), AgentMemory.log())
**Written:** Both user input and assistant output stored with session, channel, agent metadata
**Canonical:** CanonicalMemoryStore for promoted observations

### 19. Source/Production Truth Update
**What:** Update source truth when applicable
**Code:** substrate/organism/operational_truth.py, substrate/organism/production_truth_delta.py
**Lifecycle:** Raw -> Draft -> Approved -> Production
**Gate:** Operator approval required for production truth promotion

---

## Pipeline Mapping to Use Cases

### Cockpit Command
Example: "Show me the sales pipeline"
Path: Intake(text) -> Classification(status) -> Context(operator identity) -> Governance(READ_ONLY->NEGLIGIBLE) -> Routing(EOS pipeline view) -> Execute(query EOS tables) -> Audit(trace) -> Response

### EOS Business Operation
Example: "Send follow-up to lead who went cold"
Path: Intake(text) -> Classification(send) -> Context(sales context + CRM data) -> Governance(EXTERNAL_COMMUNICATION->HIGH->REQUIRES_APPROVAL) -> Approval Gate -> Routing(email adapter) -> Execute(compose + send) -> Audit(trace) -> Memory(store interaction)

### CreatorOS Analytics Assistant
Example: "Which posts performed best this week?"
Path: Intake(signal from CreatorOS) -> Classification(analysis) -> Context(creator profile + post data) -> Governance(READ_ONLY->NEGLIGIBLE) -> Routing(analytics) -> Execute(query + synthesize) -> Response -> Memory(store insight)

### LyfeOS Onboarding Assistant
Example: "Help me set up my morning ritual"
Path: Intake(signal from LyfeOS) -> Classification(command) -> Context(user profile + quest system) -> Governance(SAFE_WRITE->LOW) -> Routing(quest creator) -> Execute(generate quest structure) -> Audit(trace) -> Memory(store preference)

### Cross-Product Workflow
Example: "Prepare content calendar from top-performing posts for business social"
Path: Intake(cockpit command) -> Classification(command) -> Context(CreatorOS analytics + EOS calendar) -> Governance(REVERSIBLE_WRITE->MEDIUM) -> Data Boundary Check(cross-projection access) -> Routing(content workflow + CreatorOS adapter + EOS adapter) -> Execute(synthesize + create) -> Audit(trace) -> Memory(store result)

### External Tool Workflow
Example: "Schedule meetings with top 5 leads from CRM"
Path: Intake(cockpit command) -> Classification(schedule) -> Context(EOS CRM + Google Calendar) -> Governance(EXTERNAL_COMMUNICATION->HIGH) -> Approval Gate -> Routing(calendar adapter) -> Execute(book 5 meetings) -> Audit(trace) -> Memory(store outcomes)
