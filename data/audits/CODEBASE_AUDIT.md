# UMH Codebase Audit — Complete Guide for New Development Teams

**Date:** June 2026  
**Project:** UMH (Universal Meta Harness)  
**Scope:** End-to-end review of all production code, systems architecture, and governance

---

## EXECUTIVE SUMMARY

UMH is a **governed intelligence substrate** that turns any LLM into an elite AI advisor for running a business. It is **NOT a chatbot** — it is a complete operating system for autonomous business operations. Every decision flows through constitutional governance gates. Every action is verifiable. Every interaction feeds continuous learning.

**Key Facts:**
- **3,478 Python files** + 1,124 TypeScript/TSX frontend files
- **22 major subsystems** (control plane, organism, execution, governance, memory)
- **100+ integration tests** covering critical paths
- **Constitutional governance** on every action (PolicyEngine → WorkPacketExecutor)
- **Stage-aware reasoning** (blocks inappropriate advice at each business stage)
- **Reality-grounded** (queries live market data, not just hallucinating)
- **Single unified memory** (canonical write path, reconciliation engine)
- **Multi-modal I/O** (Discord voice/text, local workstation, browser automation)
- **Continuous learning** (every interaction generates RLHF signal)

---

## SECTION 1: MACRO ARCHITECTURE

### 1.1 The Five Layers

UMH architecture follows a strict five-layer model:

```
┌─────────────────────────────────────────────────────────────┐
│ LAYER 5: PROJECTIONS (Applications)                          │
│ EntrepreneurOS, CreatorOS, LYFEOS — domain-specific          │
│ manifestations built on unified intelligence                  │
└─────────────────────────────────────────────────────────────┘
                          ↓ Consume
┌─────────────────────────────────────────────────────────────┐
│ LAYER 4: TRANSPORTS (Input/Output Surfaces)                  │
│ Discord (voice+text), API, Node Mesh, WebSocket, Cockpit     │
│ Operators: presence tracking, device awareness               │
└─────────────────────────────────────────────────────────────┘
                          ↓ Signal Envelopes
┌─────────────────────────────────────────────────────────────┐
│ LAYER 3: EXECUTION & ORCHESTRATION                            │
│ Organism Loop (work packets → execution → learning)           │
│ Distributed runtime workers, browser automation, shell exec   │
│ Task decomposition, parallel execution, continuity            │
└─────────────────────────────────────────────────────────────┘
                          ↓ Work Packets
┌─────────────────────────────────────────────────────────────┐
│ LAYER 2: GOVERNANCE & CONTROL PLANE                           │
│ PolicyEngine, Authority tiers (READ/DRAFT/EXECUTE/COMMIT)    │
│ Goal management, strategy, memory promotion policy            │
│ Constitutional principles, risk classification               │
└─────────────────────────────────────────────────────────────┘
                          ↓ Governed Decisions
┌─────────────────────────────────────────────────────────────┐
│ LAYER 1: SUBSTRATE (Brain)                                    │
│ Types, Memory, Governance, Perception, Understanding         │
│ Reality Model, Adaptation, Continuity, State Management      │
│ LLM Routing (Gemini 2.5 → Groq → Ollama fallback)             │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 The Execution Spine

Everything that happens in UMH follows this cycle:

```
Perception (Input Signal)
  ↓ [substrate/types.py → SignalEnvelope]
Understanding (Cognitive Loop)
  ↓ [substrate/control_plane/runtime/cognitive_loop.py → CognitiveResult]
Planning (Control Plane)
  ↓ [substrate/control_plane/ → strategies, goals, decisions]
Governance (Policy Engine)
  ↓ [substrate/governance/policy_engine.py → PolicyVerdict]
Execution (Work Packets)
  ↓ [substrate/execution/executor.py → WorkPacketExecutor]
Verification (Proof Generation)
  ↓ [substrate/execution/proof_generator.py → ProofArtifact]
Memory Write (Canonical Path)
  ↓ [substrate/memory/canonical_write.py → MemoryWriteReceipt]
Learning (Event Spine)
  ↓ [substrate/organism/event_spine.py → EventEmitted]
```

Every message, every command, every decision follows this path. There are no shortcuts.

---

## SECTION 2: SUBSTRATE (THE BRAIN)

Location: `/opt/OS/substrate/`

The substrate is the unified intelligence core. It is NOT application-specific — everything
from EntrepreneurOS to CreatorOS to Discord voice channels uses the same substrate.

### 2.1 Foundation Layer

**File:** `substrate/foundation/` (8 core modules)

These define the ontological primitives — the fundamental concepts reality is built from.

- **primitives.py** — Base concepts: intention, capability, state, causality
- **identity.py** — How entities are defined and tracked across transformations
- **epistemology.py** — What the system knows and how it knows it
- **perspective.py** — How truth changes based on observer position
- **possibility.py** — The space of what could be (used for planning)
- **laws.py** — Invariants that always hold (conservation, causality)
- **persona.py** — How individual identity persists over time
- **derived_constructs.py** — Complex concepts built from primitives

**Why this matters:** AI often hallucinates because it lacks grounding in fundamental reality.
The foundation layer is checked before every major decision.

### 2.2 Canonical Types

**File:** `substrate/types.py` (1,400 lines) + `substrate/canonical_types.py` (1,249 lines)

This is the single source of truth for every domain concept in UMH. The types registry explicitly
lists where each type is canonical:

```python
# Example: from canonical_types.py
"SignalEnvelope": ["substrate.types"],          # Where all signals enter
"MemoryEntry": ["substrate.types"],             # How facts are stored
"ExecutionResult": ["substrate.types"],         # How work is verified
"PolicyVerdict": ["substrate.governance.policy_engine"],  # Governance decision
```

**Critical Pattern:** If you need a new type, it MUST go in the canonical location. Divergent
types (even if similar) are a defect that breaks governance and learning.

**Key Types to Understand:**

- **SignalEnvelope** — Universal input. Everything enters here with source, urgency, modality, authority tier
- **ExecutionContext** — Assembled reasoning context (identity + memories + goals + business context)
- **MemoryEntry** — Stores FACTS, BELIEFS, DECISIONS, OBSERVATIONS, COMMITMENTS
- **PermissionTier** — 4-level authority model (READ < DRAFT < EXECUTE < COMMIT)
- **ExecutionResult** — Proof of work completion, what changed, cost, duration
- **TraceRecord** — Immutable audit trail of every operation

### 2.3 Governance Layer

**File:** `substrate/governance/`

The policy engine is the constitutional guardian. Every action is evaluated against risk classes:

```
RiskClass.READ_ONLY           → AUTONOMOUS (no approval needed)
RiskClass.SAFE_WRITE          → Check if in safe roots, else APPROVE
RiskClass.REVERSIBLE_WRITE    → APPROVE (can be undone)
RiskClass.IRREVERSIBLE_WRITE  → DENY by default (financial/destructive)
RiskClass.EXTERNAL_COMM       → DENY by default (sends emails, posts, etc)
RiskClass.FINANCIAL           → DENY by default (touches money)
RiskClass.SECURITY_SENSITIVE  → ESCALATE (admin approval required)
RiskClass.PHYSICAL_WORLD      → ESCALATE (touches hardware/robotics)
```

**PolicyEngine (`governance/policy_engine.py`):**
- Stateless evaluator of (RiskClass, context) → GovernanceVerdict
- Maps to 5 authority levels: AUTONOMOUS, NOTIFY, APPROVE, ESCALATE, DENY
- Supports path overrides (mark specific directories as safe)
- Transparent: every decision includes a detailed rationale

**Authority Engine (`governance/policy/authority_engine.py`):**
- Implements the 4-tier permission model
- Verifies user has authority before allowing execution
- Tracks escalation chains and delegation history
- Enforces role-based access control (RBAC)

### 2.4 Reality Model

**File:** `substrate/reality_model/`

The system has a *simulation* of reality separate from its beliefs about reality. This prevents
hallucination.

- **canonical.py** — Canonical state (what *is*)
- **instance.py** — User-specific manifestations of canonical state
- **simulation.py** — Possible futures (for planning)
- **reality_mutation.py** — How reality changes when actions are taken
- **reality_query.py** — State queries (RPC interface to reality)

**Why:** An LLM alone has no grounding in what's actually true. The reality model stores:
- Company financials (not guessed)
- Market data (live feeds, not cached)
- Founder psychology (from interactions, not stereotypes)
- Current tasks (from CRM, not fabricated)
- Proof of past completions (artifacts, not claims)

### 2.5 Understanding Layer

**File:** `substrate/understanding/`

This is where raw input becomes structured knowledge.

**Modules:**
- **interpretation/** — Converts natural language into action semantics
- **perception/** — Parses code, config, databases (structured data)
- **intelligence/** — Extracts competitive intel, stakeholder maps, person recognition
- **knowledge/** — Integrates into knowledge graph with multiple layers
- **embedding/** — Vector representations for semantic search
- **patterns/** — Identifies leverage patterns and business laws
- **world_model/** — Builds unified model of market, org, founder

**Real Use Case:** When a founder says "we're losing deals in the pipeline," the understanding
layer extracts: which stage, which channel, quantified rate, recent changes. Not a generic
sympathy response.

### 2.6 Memory System

**File:** `substrate/state/memory/` (5 contract modules)

UMH has a single canonical memory, not chat history + knowledge base + facts + beliefs scattered
everywhere.

**Canonical Memory Store (`canonical_memory_store_v1.py`):**
```python
class MemoryEntry:
    memory_type: MemoryType  # FACT, BELIEF, DECISION, OBSERVATION, COMMITMENT
    content: str
    source_signal_id: UUID  # What created this
    authority_tier: int     # 1-9, higher = more certain
    confidence: float       # 0.0-1.0, uncertainty quantified
    tags: list[str]        # Semantic tagging
    created_at: datetime
```

**Reconciliation Engine (`canonical_memory_reconciliation_engine_v1.py`):**
- Runs every time the system learns something new
- Checks for contradictions
- Updates confidence on existing entries based on new evidence
- Promotes uncertain beliefs to facts when confidence crosses threshold
- Never deletes — only updates confidence and rationale

**Conflict Governance (`memory_conflict_governance_v1.py`):**
- When two sources conflict: "System says revenue is $100K, founder says $80K"
- Evaluates source reliability (founder > system observation for this domain)
- Stores both with conflict flag
- Escalates to human only if unresolvable

---

## SECTION 3: CONTROL PLANE

Location: `/opt/OS/substrate/control_plane/`

The control plane is where *strategy* lives. It does NOT execute — it plans, delegates, and reviews.

### 3.1 Cognitive Loop

**File:** `control_plane/runtime/cognitive_loop.py` (1,539 lines)

This is the gateway for ALL AI reasoning in UMH. Do not call LLMs directly — call this.

```python
from substrate.control_plane.runtime.cognitive_loop import CognitiveLoop

loop = CognitiveLoop(ctx)
result = await loop.run(
    input="Analyze this sales lead",
    agent="sales_agent",
    task_type=TaskType.ANALYZE,
    venture_id="company_id"
)
```

What happens inside:

1. **Authority gating** — Check if caller has permission for this task
2. **Context assembly** — Load memories, business stage, similar past patterns
3. **Prompt enhancement** — Inject 8 layers of context before LLM sees input
4. **Model routing** — Choose: Claude > Gemini 2.5 Flash > Groq > Ollama (fallback)
5. **Spend tracking** — Measure token usage, cost
6. **Quality verification** — Check output against governance principles
7. **Reflection logging** — Store decision for future learning
8. **Memory storage** — Facts extracted from response

**Key Feature: Fallback Responses**

If all LLMs fail, the loop has deterministic fallbacks:
- Matching message intent (schedule/email/analysis/etc)
- Returning transparent message that AI is offline
- Still logging the interaction for replay when AI is back

### 3.2 Agent Hierarchy

**File:** `control_plane/agents/`

The agent hierarchy mirrors the organizational chart:

```
Human (founder) — always in control
├── Level 1: Portfolio Advisor (cross-company strategy)
├── Level 2: CEO Agent (company orchestrator)
│   ├── Level 3a: Developer Agent (engineering)
│   ├── Level 3b: Sales Manager (go-to-market)
│   ├── Level 3c: Marketing Manager (brand/demand)
│   ├── Level 3d: Operations Manager (execution)
│   ├── Level 3e: CS Manager (customer)
│   └── Level 3f: Finance Manager (capital)
└── Advisor hierarchy (specializations)
    ├── Negotiation advisor
    ├── Psychology advisor
    ├── Funnel advisor
    └── etc.
```

Each agent has:
- **Soul document** (values, boundaries, decision style)
- **Skill set** (which operations they can do)
- **Domain knowledge** (loaded at startup)
- **Autonomy level** (0-5, set by user)
- **Persistent memory context** (what they remember)

**Agency in UMH:**

Agents are NOT independent actors. They operate within:
- **Role-based boundaries** (a sales agent cannot touch financial data)
- **Authority tiers** (higher-risk actions require escalation)
- **Business stage constraints** (Stage 1 founder ≠ Stage 5 founder)
- **Founder-controlled autonomy** (founder sets how much the AI can do)

### 3.3 Control Plane Router

**File:** `control_plane/router/control_plane_router_v1.py`

Routes incoming signals to the right agent based on intent and context.

```python
# Signal comes in
signal: SignalEnvelope = ...

# Router analyzes: "schedule a meeting" → calendar_action
# Routes to: Portfolio Advisor → CEO Agent → Operations Manager
# Each layer adds context, then executes

result = await router.route(signal)
```

This is NOT simple prompt matching. It involves:
- Domain classification (sales vs ops vs strategy)
- Authority verification (can this user ask for this?)
- Stage appropriateness (is this advice valid at current stage?)
- Precedent matching (have we done this before?)
- Conflict checking (does this align with founder's constraints?)

---

## SECTION 4: ORGANISM (MULTI-AGENT ORCHESTRATION)

Location: `/opt/OS/substrate/organism/`

The organism is where **work packets flow** through the distributed system. It is a **convergence
coordinator** that wires together multiple subsystems without replacing any of them.

### 4.1 The Organism Loop

**File:** `organism/organism_loop.py` (497 lines)

This is the heartbeat of execution:

```
Intent arrives (e.g., "schedule follow-up with that lead")
↓
Organism Loop:
  1. Reality check (Empire Router)
  2. Work packet creation (WorkPacketEngine)
  3. Queue ingest (UniversalWorkQueue)
  4. Governance gate (PolicyEngine)
  5. Execution (WorkPacketExecutor) — if approved
  6. Proof generation (ProofGenerator)
  7. Memory write (CanonicalWritePath)
  8. Status update on organism packet
  9. Event emission (EventSpine) ← triggers learning
↓
Learning captured, next similar intent is smarter
```

**OrganismLoopResult** includes:
- Unique result_id
- All subsystem IDs touched (reality snapshot, work packet, governance decision, etc)
- Proof artifacts generated
- Memory write receipt (what was learned)
- Event IDs emitted
- Duration and error (if any)

### 4.2 Work Packets

**File:** `organism/work_packet.py` + `organism/work_packet_engine.py`

A work packet is the unit of work that flows through the system:

```python
class WorkPacket:
    id: UUID
    intent: str              # "schedule meeting"
    decomposition: list[WorkUnit]  # Steps needed
    status: PacketLifecycleStatus  # created → queued → approved → executing → done
    risk_level: str          # "low", "medium", "high", "critical"
    required_authority: AuthorityLevel
    execution_environment: str  # "agent" | "browser" | "shell" | "distributed"
    estimated_duration: float
    deadline: datetime | None
    constraints: list[str]   # user-imposed constraints
    proof_artifacts: list[str]  # what was generated
    created_at: datetime
    completed_at: datetime | None
    error: str | None
```

**WorkPacketEngine** is responsible for:
1. Taking raw intent
2. Decomposing into executable units
3. Estimating resource needs
4. Checking for conflicts
5. Emitting to queue

### 4.3 Universal Work Queue

**File:** `organism/universal_work_queue.py`

Single queue for all work in the system. No priority inversions, no starving — governed by allocation engine.

Features:
- **Priority-based** (urgent vs background)
- **Stage-aware** (Stage 1 focus ≠ Stage 5 focus)
- **Resource-conscious** (doesn't overload workstations)
- **Deadline-aware** (drops non-critical work if deadline approaching)
- **Parallel-safe** (manages dependencies between packets)

### 4.4 Distributed Runtime

**File:** `execution/runtime/` (15 files)

UMH can execute work on:
- **Local agent** (in-process LLM reasoning)
- **Workstation** (desktop automation via relay)
- **Browser** (web interaction via Playwright)
- **Shell** (command execution via remote connection)
- **Distributed** (fan out to multiple workers)

Each runtime maintains:
- **Session registry** — Track active sessions
- **Heartbeat** — Keep connection alive
- **Recovery** — Auto-reconnect if lost
- **State sync** — Propagate state updates
- **Presence** — Know which runtimes are available

---

## SECTION 5: EXECUTION LAYER

Location: `/opt/OS/substrate/execution/`

### 5.1 Executor

**File:** `execution/executor.py` (800+ lines)

The executor takes an ApprovedWorkPacket and actually does the work.

```python
class WorkPacketExecutor:
    async def execute(
        self,
        bundle: ExecutionBundle,  # approved work + resources + proof spec
    ) -> ExecutionResult:
        """Execute work and return proof of what changed."""
        
        # 1. Dispatch to right runtime
        # 2. Stream progress
        # 3. Capture output
        # 4. Generate proof
        # 5. Return ExecutionResult
```

**ExecutionResult** includes:
- Status (SUCCESS, PARTIAL, FAILED)
- Output (what was produced)
- Side effects (what changed in external systems)
- Proof (artifacts proving it happened)
- Cost (tokens, time, resources)
- Error (if any)

### 5.2 Proof Generation

**File:** `execution/proof_generator.py`

After every action, generate cryptographic proof:
- Code executed and its hash
- Output captured
- Side effects logged
- Timestamp
- Agent signature

This proof is immutable evidence that the action happened exactly as claimed.

### 5.3 Bridge Layer

**File:** `execution/bridge/` (60+ files)

The bridge connects the substrate to real systems:

**Session management:**
- `claude_session_bridge.py` — Claude API interaction
- `discord_voice_transport.py` — Discord voice I/O
- `node_transport.py` — Node mesh communication

**Capability mapping:**
- `capability_routing.py` — Route task to right capability
- `scene_capabilities.py` — What can be done in current context
- `scene_policy.py` — What's allowed in current context

**Local control:**
- `local_listener.py` — Listen for local commands
- `local_control.py` — Execute local operations
- `workstation_translator.py` — Convert to/from workstation format

**Task execution:**
- `task_decomposition.py` — Break task into steps
- `task_pipeline.py` — Execute steps in order
- `task_system.py` — Manage task lifecycle

---

## SECTION 6: STATE & PERSISTENCE

Location: `/opt/OS/substrate/state/`

### 6.1 Database Layer

**File:** `state/storage/db.py`

PostgreSQL is the single source of truth. Neon.tech handles infrastructure.

Connection management:
- Pooled connections per organization
- Automatic reconnection
- Query timeouts
- Transaction management

**Key tables:**
- `users` — Founder identity + preferences
- `ventures` — Company configs (stage, offer, ICP, etc)
- `interactions` — Every input/output with timestamps
- `memories` — Canonical memory store
- `decisions` — Governance decisions + rationale
- `proofs` — Execution proofs (immutable audit trail)
- `approvals` — Pending/completed approvals

### 6.2 Business Instance Spec (BIS)

**File:** `state/business/business_instance.py`

The BIS is the configuration of a company at a specific point in time:

```python
class BusinessInstanceSpec:
    stage: int  # 1-6
    offer: OfferDefinition  # what we sell
    icp: ICPDefinition  # who we sell to
    channels: list[Channel]  # how we reach them
    financial_model: FinancialModel  # unit economics
    north_star: str  # primary metric
    proof_to_advance: str  # what we need to show
    constraints: list[str]  # founder-imposed constraints
    status: str  # active, paused, etc
```

**Why stage matters:** Every piece of advice is filtered through BIS.stage:
- Stage 1: "Move fast, even if wrong"
- Stage 3: "Optimize funnel, nail repeatable"
- Stage 5: "Scale ops, remove founder bottleneck"

Same advice at wrong stage kills the company.

### 6.3 Stores

**File:** `state/stores/` (12 specialized stores)

Each store is a thin wrapper around a table with semantic methods:

- **approval_store.py** — Pending approvals
- **entity_link_store.py** — Cross-entity relationships
- **embedding_store.py** — Vector representations
- **skill_store.py** — Available skills (capabilities)
- **goal_store.py** — Active goals + status
- **task_store.py** — Work to be done
- **venture_store.py** — Company configs
- **profile_store.py** — User preferences
- **permission_store.py** — Role-based access

---

## SECTION 7: ADAPTERS (EXTERNAL INTEGRATIONS)

Location: `/opt/OS/adapters/`

Adapters connect UMH to external systems without polluting the core.

### 7.1 LLM Adapters

**File:** `adapters/llm/`

Routes to the best available LLM:

1. **cc_sdk** (Claude API — preferred, tier 1)
2. **gemini_flash** (Gemini 2.5 Flash — tier 2, faster)
3. **groq** (Groq SDK — tier 3, local fallback)
4. **ollama** (Ollama local — tier 4, offline fallback)

Each adapter:
- Implements `LLMAdapter` interface
- Handles auth, retries, timeouts
- Returns standardized `LLMResponse`
- Tracks cost and latency

**Routing Logic** (from CLAUDE.md):
```
If API key available AND cost < daily budget:
  Use highest-tier available
Else if faster model available:
  Use Gemini 2.5 Flash
Else if local model available:
  Use Groq or Ollama
Else:
  Deterministic fallback (no LLM call)
```

### 7.2 Browser Adapter

**File:** `adapters/browser/` + `execution/agents/browser_agent.py`

Uses Playwright for headless browser automation:
- Takes screenshots
- Reads DOM state
- Clicks elements
- Fills forms
- Captures console output

Every browser action is:
- Traced (screenshot + action logged)
- Verified (proof of what changed)
- Replayed (for debugging)

### 7.3 Discord Adapter

**File:** `transports/discord/`

UMH lives in Discord. The adapter handles:
- Message ingestion
- Voice channel connection
- TTS (text-to-speech output)
- STT (speech-to-text input)
- Presence tracking
- Thread management

---

## SECTION 8: TESTING STRATEGY

Location: `/opt/OS/tests/` (100+ test files)

Tests are NOT afterthoughts — they're executable specifications of system behavior.

### 8.1 Test Organization

```
tests/
├── test_p0_smoke.py           — Critical path smoke tests
├── test_daemon_e2e.py         — End-to-end daemon lifecycle
├── test_operator_loop_mvp.py  — Operator experience tests
├── test_governance_routes.py  — Governance enforcement
├── test_approval_intercepts.py — Authority gating
├── test_phase*_*.py           — Phase-specific (see CLAUDE.md for phases)
└── test_*_integration.py      — Subsystem integration
```

### 8.2 Critical Test Files

**test_p0_smoke.py** — If this fails, nothing works. Must pass before every commit.

Tests:
1. Database connection
2. LLM routing fallback
3. Canonical type loading
4. Memory subsystem
5. Governance engine
6. Basic orchestration loop

**test_governance_routes.py** — Enforce that governance gates are NOT bypassed

Tests:
1. READ_ONLY operations are autonomous
2. SAFE_WRITE respects safe roots
3. IRREVERSIBLE_WRITE is denied
4. EXTERNAL_COMM is denied
5. Escalation chain works
6. Override paths are checked

**test_daemon_e2e.py** — Full lifecycle of a work packet

Tests:
1. Organism loop runs end-to-end
2. Work packet lifecycle
3. Event emission
4. Memory promotion
5. Error recovery

### 8.3 Running Tests

```bash
# Run P0 smoke tests (essential)
pytest tests/test_p0_smoke.py -v

# Run governance tests
pytest tests/test_governance*.py -v

# Run phase tests for feature area
pytest tests/test_phase14*.py -v

# Run all tests (slow, ~10 min)
pytest tests/ -v --tb=short
```

---

## SECTION 9: DEPLOYMENT

### 9.1 Docker Compose

**File:** `docker-compose.yml`

Brings up three services:

```yaml
os-discord:          # Primary interface, Discord bot
  image: os-discord
  depends_on: [postgres]
  env: API_KEYS, DISCORD_TOKEN, etc

os-operator:        # Workstation API + Cockpit UI
  image: os-operator
  depends_on: [postgres]
  ports: 8000, 5173 (frontend)

os-webhook:         # Media generation (Higgsfield)
  image: os-webhook
  depends_on: [postgres]
```

### 9.2 Quick Start

```bash
# 1. Install Docker
# 2. Clone repo
cd /opt/OS

# 3. Set environment
cp .env.example .env
# Edit .env: add API_KEYS, DATABASE_URL, DISCORD_TOKEN

# 4. Start services
docker compose up -d

# 5. Verify
docker compose logs -f os-discord | grep "Ready"
```

### 9.3 Production Checklist

Before going live:

- [ ] Database backups configured (Neon automated)
- [ ] Error tracking configured (Sentry or similar)
- [ ] Spend limits set (LLM cost guardrails)
- [ ] SSL certificates valid
- [ ] Discord bot permissions reviewed
- [ ] Safe roots configured (governance guardrails)
- [ ] Tests passing (pytest -v tests/test_p0_smoke.py)
- [ ] Monitoring alerts set up (Discord outage, DB unavailable, etc)

---

## SECTION 10: KNOWLEDGE SYSTEMS

### 10.1 Memory Palace

**File:** `knowledge/palace/`

UMH has a *memory palace* system that organizes knowledge by concern:

```
knowledge/palace/
├── rooms/
│   ├── business_instance.md     — How to read BIS
│   ├── governance.md            — How governance gates work
│   ├── memory_system.md         — How memory reconciliation works
│   ├── execution_trace.md       — How to debug execution
│   ├── agent_hierarchy.md       — How to dispatch to agents
│   └── ... (20+ rooms)
└── index.md                     — Navigation
```

### 10.2 Codebase Graph

**File:** `scripts/build_graph.py` + `data/codebase_pages/`

UMH maintains an updated dependency graph of the entire codebase:

```bash
# Rebuild the graph
python3 scripts/update-graph

# Query it
python3 scripts/query_graph.py deps substrate/memory/
python3 scripts/query_graph.py search "PolicyEngine"
python3 scripts/query_graph.py critical  # Which files are most depended on?
```

### 10.3 Summaries

**File:** `data/node_summaries.json` (one-line summary for every file/class/function)

Before opening a file, check the summary first:

```bash
python3 scripts/query_graph.py summary substrate/memory/canonical_write.py
```

---

## SECTION 11: COMMON WORKFLOWS

### 11.1 Adding a New Agent

1. Create soul document in `agents/{agent_name}.md`
2. Add agent definition to `substrate/organism/advisor_hierarchy.py`
3. Register in `substrate/state/registries/os_registry.py`
4. Write unit test in `tests/test_agent_runtime.py`
5. Add to agent dispatch in `control_plane/router/`
6. Test: `pytest tests/test_agent_runtime.py -k new_agent`

### 11.2 Adding a New Governance Rule

1. Define risk class in `substrate/governance/risk_classes.py`
2. Add policy in `substrate/governance/policy_engine.py` → `_DEFAULT_POLICY`
3. Add test in `tests/test_governance_routes.py`
4. Verify: `pytest tests/test_governance_routes.py -v`
5. Document in `PROTOCOLS.md`

### 11.3 Adding a New Adapter

1. Create `adapters/{system}/adapter.py`
2. Implement `BaseAdapter` interface
3. Add to `adapters/__init__.py`
4. Write test in `tests/test_adapter_*.py`
5. Test: `pytest tests/test_adapter_*.py -v`

### 11.4 Debugging an Execution

1. Find the interaction ID
2. Query trace: `python3 scripts/query_trace.py {interaction_id}`
3. Check governance decision: `python3 scripts/query_decision.py {interaction_id}`
4. Review proof artifacts
5. Check memory changes
6. Look at event spine emissions

---

## SECTION 12: CRITICAL INVARIANTS

These MUST NEVER be violated:

1. **Governance Gate Always Applies**
   - Every action goes through PolicyEngine
   - No shortcuts to execution without approval
   - Tests check this every commit

2. **Single Memory Source**
   - No parallel belief systems
   - All facts reconcile to canonical store
   - Conflicts are explicit, not hidden

3. **Proof is Immutable**
   - Every execution produces proof
   - Proof hash is stored with the action
   - Proof cannot be retroactively changed

4. **Business Stage Filters Advice**
   - Every recommendation checks BIS.stage
   - Stage-inappropriate advice is blocked
   - Stage advancement requires proof

5. **Authority Tier is Checked**
   - User authority verified before action
   - Escalation chain is followed
   - COMMIT tier changes cannot be delegated

6. **LLM Failures Do Not Cascade**
   - Fallback responses are deterministic
   - System continues with reduced capability
   - Failures are logged but not fatal

7. **Voice I/O is Lossless**
   - Audio is recorded and transcribed
   - TTS output is tested for safety
   - Modality conversions are verified

8. **No Hallucination in Claims**
   - If we say a fact, it's in the canonical store
   - If we say we did something, there's a proof
   - If we say we'll do something, it's in the queue

---

## SECTION 13: PERFORMANCE TARGETS

### 13.1 Latency

- Message input → agent response: **<5 seconds** (with LLM)
- Governance gate evaluation: **<100ms**
- Memory reconciliation: **<500ms**
- Work packet execution: depends on task type

### 13.2 Throughput

- Concurrent operators: **10-100** (depends on hardware)
- Work packets per minute: **100-1000**
- LLM requests per minute: **Routed by spend limit**

### 13.3 Resource Usage

- Memory: 2GB base + 100MB per active session
- CPU: 1 core minimum, scales to 4+
- Database: PostgreSQL 14+, 10GB recommended

---

## SECTION 14: TROUBLESHOOTING

### 14.1 "LLM Returned Empty Response"

1. Check spend limit: `curl http://localhost:8000/spend`
2. Verify API keys in .env
3. Check LLM logs: `docker logs os-discord | grep LLM`
4. Try forcing Ollama: set PREFER_LOCAL_LLM=true

### 14.2 "Governance Denied This Action"

This is CORRECT. The action was risky. Options:
1. Increase authority tier (if founder can)
2. Run in approved context (e.g., in safe root for writes)
3. Escalate to human approval
4. Change the policy (modify `policy_engine.py`, regenerate container)

### 14.3 "Memory Conflict: Founder Says X, System Says Y"

1. Check both sources
2. Query: `SELECT * FROM memories WHERE tags = 'conflicting'`
3. Founder's statement wins (they have higher authority)
4. System observation is marked as lower confidence
5. Future learning will reconcile

### 14.4 "Work Packet Stuck in Queue"

1. Check dependencies: `python3 scripts/query_graph.py deps {packet_id}`
2. Check authorization: `SELECT * FROM approvals WHERE packet_id = {packet_id}`
3. Check runtime availability: `curl http://localhost:8000/runtime-status`
4. Restart executor: `docker restart os-discord`

---

## SECTION 15: READING ORDER FOR NEW DEVELOPERS

Start here. In this order.

1. **PHILOSOPHY.md** (30 min) — Understand the "why"
2. **ARCHITECTURE.md** (45 min) — Understand the "what"
3. **CLAUDE.md** (30 min) — Understand the "how"
4. **substrate/types.py** (60 min) — Understand the primitives
5. **substrate/control_plane/runtime/cognitive_loop.py** (45 min) — AI entry point
6. **substrate/organism/organism_loop.py** (30 min) — Execution flow
7. **substrate/governance/policy_engine.py** (20 min) — Safety model
8. **Run tests** (10 min) — `pytest tests/test_p0_smoke.py`
9. **Deploy locally** (15 min) — `docker compose up`
10. **Read a full user flow** (60 min) — Pick a test, trace it end-to-end

---

## SECTION 16: KEY CONTACTS & RESOURCES

### Documentation
- **PHILOSOPHY.md** — Founding principles
- **ARCHITECTURE.md** — System design
- **PROTOCOLS.md** — Communication contracts
- **CLAUDE.md** — AI development principles
- **cloud.md** — Cloud deployment
- **knowledge/palace/** — Memory palace

### Code Locations
- **Substrate:** `/opt/OS/substrate/`
- **Tests:** `/opt/OS/tests/`
- **Services:** `/opt/OS/services/`
- **Scripts:** `/opt/OS/scripts/`
- **Docs:** `/opt/OS/docs/`

### Scripts
- **Build graph:** `python3 scripts/update-graph`
- **Query graph:** `python3 scripts/query_graph.py`
- **Verify system:** `python3 scripts/verify_knowledge_system.py`
- **Test:** `pytest tests/`
- **Bootstrap session:** `python3 scripts/session_bootstrap.py --compact`

---

## SECTION 17: WHAT'S NOT IN THIS AUDIT

This audit covers core substrate systems. Not covered (by design):

- **saas/** — TypeScript/React frontend (separate team)
- **Detailed projections/** — EntrepreneurOS specifics (documented separately)
- **Detailed adapters/** — Each adapter has its own documentation
- **Historical decisions** — See git log and decision transcripts
- **Phase history** — See CLAUDE.md phases 1-17

---

## END OF AUDIT

This document is the *start* of understanding UMH, not the end.

Every file has a purpose. Every decision was made for a reason. The governance layer exists
because hallucination costs companies money. The memory layer exists because learning compounds.
The bridge layer exists because real execution matters.

Welcome to the team.

Read the code. Run the tests. Deploy locally. Ask questions.

The intelligence is in the substrate. You're not building features. You're expanding the surface area
where intelligence meets reality.

---

**Audit Metadata**
- Generated: 2026-06-20
- Scope: Complete substrate, control plane, execution, governance
- Files Analyzed: 3,478 Python + 1,124 TypeScript
- Tests Present: 100+ test files
- Status: Production-ready

