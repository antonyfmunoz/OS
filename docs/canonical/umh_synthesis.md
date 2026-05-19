# Universal Meta Harness — Canonical Synthesis

**Source:** Google Doc `UMH` (id `11p36P6TMvTnnz2KdQ2wYd3cDKfjHtCvVKp2_XEkuvz8`), 12 tabs, 226KB, last modified 2026-05-10.
**Method:** Full read of every tab, cross-reference against OST leverage doctrine, ground every architectural claim against the current `/opt/OS` stack and protected core files.
**Status:** Synthesized canonical reference. Supersedes the fragmented multi-tab artifact for reasoning purposes; the source doc remains the historical record.

-----

## 0. Document Status & Methodology

### 0.1 What the source actually is

The UMH doc evolved across many sessions. It contains **12 numbered tabs (1 missing from the export, 2–13 present)** and roughly 15,866 lines of prose, spec, and roadmap. The tabs were written at different times for different abstraction levels, so the artifact has:

- visionary tabs (6, 11) — strategic and philosophical
- architectural specs (3, 4, 9) — three successive lockable versions, each more refined
- protocol packs (2) — formal contracts
- roadmaps (5, 7) — sequencing and release
- strategic positioning (8) — EntrepreneurOS as the commercial wedge
- meta-recognition (12) — diagnosis of the drift itself
- existing synthesis attempt (13) — partial coherent merger

Tab 12 explicitly names the problem: **knowledgebase entropy + state ambiguity + layer collapse + specification drift**. This synthesis is the response. It does not invent new framing — it canonicalizes, deduplicates, and grounds.

### 0.2 The drift this synthesis resolves

The most material conflicts and evolutions across the tabs:

1. **Name** — the doc consistently uses **Universal Meta Harness**. The connected leverage skill calls it Universal Model Harness. The doc wins; the skill is out of date. This synthesis uses Meta.
1. **Invariant count** — Tab 10 lists 7 invariants, Tab 3 lists 8, Tab 4 lists 10 (adds Reality Mimicry + Intelligence Subordinate to Control), Tab 9 lists 12 (adds External Boundary Law, Action/Execution Separation, Mastery Law). The Tab 9 superset is correct.
1. **Roadmap numbering** — Tab 5 phases 76–108. Tab 6 renumbers them 80–110 with a Deliberation Council and Leverage Taxonomy track inserted. The phase numbers are bookkeeping; the *sequencing* is what matters. This synthesis presents the canonical stage order, not the numeric labels.
1. **Architecture depth** — Tab 4 lists 35 modules as a flat tree. Tab 9 collapses this into **10 macro-layers** with subsystems nested inside. The 10-layer model is correct; the flat tree is the implementation projection.
1. **Adapter contract** — Tab 4 says adapters `execute()`. Tab 9 corrects this: adapters `translate_request` / `normalize_result` / `observe_state` but **do not execute**. Workers execute. The corrected contract is canonical.
1. **MVP boundary** — Tab 5 puts Workstation in Stage 1. Tab 9's MVP section says workstation needs only minimal state. The minimal-state version is what Phase 76–78 should ship.

Each of these is flagged inline below at the relevant section.

### 0.3 Status labels used in this synthesis

Per Tab 12's canonicalization protocol, every claim below carries one of these labels where ambiguity exists:

- `CANONICAL` — invariant law or definition; should not change
- `ACTIVE` — currently being built
- `PROVEN` — running in the current `/opt/OS` deployment
- `PARTIAL` — partially proven, gaps named
- `PLANNED` — sequenced for a future phase
- `SPECULATIVE` — end-state vision, not active build
- `DEPRECATED` — superseded by a later tab; preserved only as history

-----

# PART I — FOUNDATION

## 1. Thesis

UMH is a **governed, stateful, reality-modeling intelligence operating system** that:

- perceives multimodal signals
- decomposes them into ontological primitives
- maintains source-attributed user/world/environment/system state
- composes complete executable systems from reusable primitives, templates, registries, libraries, capabilities, and policies
- verifies mastery before execution
- governs every action through one control plane
- routes execution through a single execution spine across explicit environments
- connects to all external reality only through adapter boundaries
- validates proof
- learns from outcomes through bounded feedback
- self-regulates over time
- compounds human capability across devices, tools, models, systems, people, and environments

Compressed: **UMH is the governed control plane for externalized cognition, mastered action, cross-environment execution, and recursive human capability compounding.**

The key technical insight from Tab 10 — and the line that constrains the entire build — is:

> The universal harness is NOT universal execution. It is universal orchestration + protocol standardization.

UMH does not perform work. UMH coordinates the systems that perform work. Confusing the two is the failure mode that produces a "second execution loop" inside the harness and collapses the architecture.

## 2. Prime Directive

**Minimize human friction while maximizing human capability under real-world constraints.** `CANONICAL`

A subsystem is valid only if it improves one or more of:

capability gain, friction reduction, execution reliability, safety, state continuity, learning over time, cross-environment leverage, human leverage, system leverage, memory leverage, decision quality

without violating any system law.

UMH is not optimized for novelty, complexity, or aesthetic architecture. It is optimized for **governed leverage**.

## 3. Identity — UMH Is and Is Not

### 3.1 UMH IS `CANONICAL`

A single coherent system that is simultaneously:

control plane · world-model engine · second-brain memory system · registry system · library system · template system · capability router · composition engine · governed execution runtime · environment router · adapter-boundary framework · workstation/Jarvis layer · cross-device cognition layer · organism-style self-regulating runtime · AI OS foundation

These are not separate products. They are facets of one runtime.

### 3.2 UMH IS NOT `CANONICAL`

a chatbot · a UI · a model wrapper · a tool wrapper · a workflow builder · a SaaS product · a single agent · a prompt library · a loose automation stack

The interface is not the system. The model is not the system. The tools are not the system. The system is the **governed intelligence runtime that coordinates all of them**.

## 4. Core Architectural Thesis

Ten first principles. Every design decision must be checkable against these:

1. Reality can be modeled as state.
1. State changes through action.
1. Action is constrained by resources, time, context, environment, and governance.
1. Human intent is a signal, not the whole truth.
1. External systems must be translated into internal contracts.
1. Execution must be governed before it is performed.
1. Every outcome must produce traceable evidence.
1. Every useful outcome should improve future execution.
1. The user's capability compounds when work becomes reusable structure.
1. The system must preserve continuity across sessions, devices, environments, and time.

-----

# PART II — THE INVARIANT LAWS

These are non-negotiable. Any violation = architectural failure. The list below is the superset across Tabs 3, 4, and 9. `CANONICAL`

## 5. The Twelve Laws

### 5.1 Control Plane Exclusivity

All signals, decisions, actions, memory writes, adapter interactions, environment interactions, worker directives, and execution requests must pass through the Control Plane. No subsystem may independently execute. No interface may directly call external systems. No model may directly act. No adapter may bypass the execution spine.

### 5.2 Single Execution Spine

There is **one** canonical runtime path. Parallel work is allowed only as controlled divergence from the spine. All parallel branches must reconverge before decisions, memory writes, or execution. The full spine is in §7.

### 5.3 Governance Before Execution

No execution occurs without governance. Every proposed action must be classified by authority, risk, data sensitivity, environment, capability, reversibility, cost, confidence, ambiguity, legal/safety constraints, and approval requirement. Governance returns one of: `autonomous` / `notify` / `approve` / `escalate` / `deny`. **No governance decision means no execution.**

### 5.4 Typed Contracts Only

All inter-module communication uses explicit schemas. Forbidden: implicit prompt-string contracts, hidden dictionaries, untyped side channels, undocumented payloads, silent mutation, magic state. Required: typed protocols (Pydantic v2 or equivalent), validated structures, versioned schemas, traceable inputs/outputs, contract tests.

### 5.5 Memory Discipline

All durable state writes go through the Memory/Storage subsystem. No module writes long-term state directly. Every memory write must include source, timestamp, confidence, scope, reason, promotion status, links/evidence. **Trace is not memory.** Trace is the execution record; Memory receives governed memory *candidates* derived from traces, outcomes, feedback, or explicit user instruction.

### 5.6 Environment Explicitness

Every executable action must declare target environment, required capabilities, required adapters, required worker/runtime, permissions, constraints, authority requirement, expected output, failure modes, and proof requirements. No environment declaration means no execution.

### 5.7 Trace Completeness

Every execution must produce an inspectable trace containing input, interpretation, world context, memory context, composition, governance, work packet, execution, adapter boundary, environment, result, proof, outcome, feedback, memory-update decision, and timestamps. If the system cannot explain what happened, the run is incomplete.

### 5.8 Deterministic Core

Core system logic must be deterministic, explainable, bounded, testable, auditable. Adaptive intelligence may recommend, score, enrich, simulate, and learn — but it cannot bypass deterministic control, governance, execution, or memory discipline. **Intelligence is subordinate to control.**

### 5.9 External Boundary Law `CANONICAL` (Tab 9, supersedes earlier "Adapter Isolation")

No external system — tool, SaaS, model, runtime, environment, human approval process, data source, filesystem, browser, OS, or physical actor — may be accessed directly. Every external interaction passes through an **adapter boundary**. Adapters do not independently execute. Execution is performed only by the governed Action System through the Execution Spine, using an approved worker/runtime in an explicit environment. Every external interaction must declare adapter boundary, capability contract, environment, worker/runtime, governance policy, mastery requirements, work packet, proof requirements, and trace path.

### 5.10 Action / Execution Separation Law `CANONICAL` (Tab 9)

These are eight distinct entities. Conflating any two is an architectural error:

- **Action** — intended state transformation
- **Capability** — abstract ability required to perform or support that transformation
- **Adapter** — connection and translation boundary to an external system
- **Environment** — where execution occurs
- **Worker Runtime** — process/session/node that performs execution
- **Actuation** — low-level effect-producing operation
- **Work Packet** — governed executable instruction
- **Proof Artifact** — evidence that the action happened correctly

Adapters translate. Workers execute. Actuators affect. Proof validates. Trace records.

### 5.11 Mastery Law `CANONICAL` (Tab 9, new in PRD v3.0)

UMH must not execute an action merely because it has access to a tool, model, environment, runtime, human, data source, or adapter. Before execution, UMH must possess or acquire sufficient **scoped, versioned, testable, fresh, proof-backed** competence in:

action being attempted · domain context · external system · adapter boundary · execution environment · data being handled · model or worker performing the task · human approval path · governance constraints · success criteria · proof requirements

Mastery is not infinite knowledge. It is *context-specific competence* sufficient for the declared capability, risk level, environment, and constraints.

The example from Tab 9 makes this concrete:

- **Bad** mastery declaration: "Master Google Workspace."
- **Good**: "Master Google Docs tab-aware extraction for W0-001 under read-only OAuth/API constraints, with `includeTabsContent=true`, child tab recursion, source provenance, and coverage validation."

The eleven mastery categories: Tool, Action, Domain, Environment, Data, Model, Adapter Boundary, Human Approval, Governance, Context, Physical-World.

### 5.12 Reality Mimicry Is Native (not decorative)

UMH may model system structure after effective real-world patterns when technically useful. The pattern must fit the technical problem; biology is not always the right metaphor.

- organisms → self-regulation and homeostasis
- cells → isolated worker units
- nervous systems → control and signal routing
- immune systems → anomaly/safety detection
- ecosystems → resource allocation
- markets → weighted decision signals
- physics → constraints, entropy, causality
- games → feedback, progression, state transition
- software systems → typed contracts, modularity, tests

-----

# PART III — ONTOLOGY

UMH's internal language of reality. Every interpreted signal, concept, goal, action, outcome, template, capability, and world-model update must map to ontological primitives. `CANONICAL`

## 6. Primitives, Concepts, Laws

### 6.1 Core Primitives (10)

state · change · constraint · resource · time · signal · feedback · goal · action · outcome

### 6.2 Additional System Concepts (16)

entity · relationship · environment · capability · authority · risk · uncertainty · memory · identity · pattern · policy · plan · composition · execution · trace · proof · adapter · worker · actuation

### 6.3 Governing Laws (13)

causality · feedback · compounding · entropy · emergence · constraints · equilibrium · temporal dependency · resource scarcity · tradeoffs · local/global optimization · polarity/tension · system boundary effects

### 6.4 Primitive Mapping Contract

```python
class PrimitiveMapping(BaseModel):
    source_id: str
    source_type: str
    primitives: list[Primitive]
    relationships: list[Relationship]
    constraints: list[Constraint]
    confidence: float
    evidence: list[EvidenceRef]
```

-----

# PART IV — THE CANONICAL RUNTIME SPINE

The one and only authorized path from signal to learning. `CANONICAL` Drawn from Tab 9 §7 (the most refined form). 27 steps:

```
Signal
  → Control Plane Intake
  → Perception
  → Interpretation
  → Decomposition
  → Ontology Mapping
  → Domain Mapping
  → World Model / Memory / Profile Retrieval
  → Breadth Expansion
  → Completeness Detection
  → Registry / Library / Template Lookup
  → Capability Selection
  → Adapter / Environment Matching
  → Composition
  → Planning
  → Mastery Check
  → Quality Check
  → Governance Decision
  → Work Packet Creation
  → Worker Routing
  → Adapter-Bound External Interaction
  → Actuation
  → Result Collection
  → Proof Validation
  → Trace Persistence
  → Outcome Evaluation
  → Learning Proposal
  → Memory / World Model / Profile Update
  → Self-Regulation
```

No module may create a shortcut around this spine. Parallel divergence is allowed for worker cells, but all branches reconverge before memory writes or learning updates.

-----

# PART V — THE TEN MACRO-LAYERS

Tab 9's first-principles essentialist architecture. Every subsystem belongs to exactly one of these layers. No orphan systems. No side-door execution. No feature without architectural placement. `CANONICAL`

```
Universal Meta Harness
├─ 1. Interface Layer
├─ 2. Control Plane
├─ 3. Understanding Layer
├─ 4. State Layer
├─ 5. Composition Layer
├─ 6. Governance Layer
├─ 7. Execution Plane
├─ 8. Adapter Boundary Layer
├─ 9. Observability + Proof Layer
└─ 10. Learning + Self-Regulation Layer
```

## 7. Layer 1 — Interface Layer

Receives user/system input, displays approved system state. **The interface is not the system.** It is the user's cockpit into UMH.

**Surfaces:** CLI · API · desktop app · mobile app · voice interface · Discord/Slack/Telegram control · browser dashboard · workstation command center · presence surfaces · notifications · approval surfaces.

**May:** capture intent, display state, display traces, display approvals, display active tasks, display summaries, route signals into Control Plane.

**May not:** execute actions, call adapters directly, write memory directly, bypass governance, invent state, mutate traces, directly access external systems.

### 7.1 Workstation / Jarvis Surface

The persistent user-facing operational embodiment. Maintains devices, environments, modes, boot sequences, active state, active tasks, active traces, pending approvals, preferred execution nodes, continuity state.

**Continuity behavior (non-optional):**

```
user leaves
  → system continues permitted work
  → traces outcomes
  → updates state through governed paths
  → user returns
  → system summarizes what happened
  → user resumes with context
```

**Modes** (canonical set): Command Center · Developer · Research · Outreach · Content · Overnight · Maintenance · Simulation · Emergency · Workstation.

### 7.2 UI Doctrine (from Tab 6 §13)

- Full-screen Command Center
- Expanded floating overlay
- Minimized 6-line animated voice-wave (the smallest visible embodiment of UMH)
- Ghost/hidden mode
- Voice interface
- Mobile companion (degrades to widgets/Live Activities/App Intents/Shortcuts on iOS, since iOS cannot support a true global overlay)
- CLI/API/developer console

## 8. Layer 2 — Control Plane

Owns the canonical runtime flow. Enforces system invariants. Authority layer. Everything reports to it. Nothing bypasses it.

**Components:** runtime · router · orchestrator · event bus · protocol enforcement · invariant checks · system lifecycle · authority routing · execution routing.

**Contract:**

```python
class ControlPlaneEvent(BaseModel):
    event_id: str
    source: str
    event_type: str
    payload: dict
    schema_version: str
    user_instance_id: str
    session_id: str
    environment_id: str
    timestamp: int
    authority_context: AuthorityContext
    trace_id: str
```

**Technical reality check:** the Control Plane should be implemented as a deterministic Python service first, not an LLM agent. The LLM can interpret, plan, summarize, classify, or propose. The control plane *decides* what can move forward.

## 9. Layer 3 — Understanding Layer

Converts raw signals into structured meaning.

### 9.1 Perception

Inputs: text · voice · audio · video · screen state · webcam · sensors · file events · system events · browser events · API events · execution results · behavioral patterns · device state · environment state · human feedback.

**MVP perception** (Tab 4 §7): text input · CLI/API input · execution result input · trace event input · system event input · workstation session state input.

Output:

```python
class Signal(BaseModel):
    signal_id: str
    modality: SignalModality
    source: str
    content: Any
    context: dict
    timestamp: int
    environment: EnvironmentRef | None
    confidence: float
    metadata: dict
```

### 9.2 Interpretation

Extracts meaning from signals. Does not just process text — extracts signal from every word, omission, context, timing, pattern, and behavior.

**Extracted dimensions:** meaning · intent · ambiguity · urgency · risk · constraints · domain · goal · emotional tone · communication style · vocabulary level · mental model indicators · avoidance patterns · focus areas · authority expectation · missing context · desired outcome.

Output:

```python
class InterpretedSignal(BaseModel):
    signal_id: str
    intent_candidates: list[IntentCandidate]
    extracted_entities: list[Entity]
    extracted_constraints: list[Constraint]
    inferred_goals: list[Goal]
    ambiguity_score: float
    risk_score: float
    confidence: float
    explanation: str
```

### 9.3 Decomposition

**Mandatory pipeline:**

```
tokens → grammar → semantics → concepts → entities
  → primitives → relationships → constraints → context → intent
```

**Promotion rule:** Not every word becomes memory. A concept is promoted only if it is reusable, decision-relevant, identity-relevant, domain-relevant, world-model-relevant, policy-relevant, or explicitly requested by user.

### 9.4 Ontology — see Part III

### 9.5 Domain System

Domains organize reality into operational areas for breadth-first reasoning. Canonical domains (Tab 4 §10): personal_life · health · fitness · relationships · business · operations · sales · marketing · finance · legal · software · research · content · creator · education · fashion/product · workstation · device · environment · communication · automation · investment · household · travel · security · governance.

```python
class DomainMap(BaseModel):
    domain_id: str
    name: str
    subdomains: list[str]
    common_entities: list[EntityType]
    common_workflows: list[WorkflowRef]
    common_constraints: list[Constraint]
    required_slots: list[SlotSpec]
    failure_modes: list[FailureMode]
    benchmarks: list[Benchmark]
    templates: list[TemplateRef]
    capabilities: list[CapabilityRef]
    domain_laws: list[DomainLaw]  # added in Tab 9
```

**Domain Law Registry** (Tab 6 §10): business laws (cash flow, supply/demand, incentives, margins, bottlenecks, trust, distribution, competition) · human performance laws (energy, attention, habit, emotion, cognitive load, identity, motivation, recovery) · software laws (state, dependencies, latency, interfaces, security, complexity, versioning, failure modes) · finance · content/distribution · operations · relationships · learning · health · markets · governance. These are what makes the world model simulate-able later.

### 9.6 Breadth → Depth Reasoning

UMH expands context breadth-first, then deepens selectively.

1. identify all relevant domains
1. identify entities/processes/resources
1. detect required slots
1. detect omissions
1. score importance/uncertainty/impact
1. deepen high-value areas
1. compose plan/system

**Canonical example** (Tab 4 §11): "Build a CRM for construction" expands breadth to include lead capture · estimating · contracts · projects · crew scheduling · materials · invoicing · collections · customer communication · reporting · feedback · compliance — before depth-narrowing to whichever components matter most for the current goal.

## 10. Layer 4 — State Layer

Maintains working and persistent representations of reality.

### 10.1 World Model

The explicit structured representation of user/world/environment/system state. **Graph-based, time-aware, uncertainty-aware, source-attributed, updateable, queryable.**

```python
class WorldState(BaseModel):
    entities: list[Entity]
    relationships: list[Relationship]
    state_values: dict
    temporal_state: TemporalState
    uncertainty: UncertaintyModel
    active_goals: list[Goal]
    active_tasks: list[Task]
    constraints: list[Constraint]
    environments: list[EnvironmentRef]
    resources: list[Resource]
    capabilities: list[CapabilityRef]
    risks: list[Risk]

class Entity(BaseModel):
    entity_id: str
    type: str
    name: str
    attributes: dict
    relationships: list[RelationshipRef]
    state: dict
    confidence: float
    source: str
    timestamp: int

class Fact(BaseModel):
    value: Any
    confidence: float
    source: str
    timestamp: int
    scope: str
    expiry: int | None
    evidence: list[EvidenceRef]
```

**Tracks:** user · devices · environments · goals · constraints · projects · tasks · relationships · workflows · tools · capabilities · execution history · interaction history.

**Technical reality:** start with Postgres + JSONB + pgvector. Do not start with Neo4j unless graph traversal becomes the actual bottleneck. The graph model is *logical*, not necessarily a graph database.

### 10.2 Memory System

Memory externalizes cognition and preserves continuity. Memory is **typed, governed, temporal, source-attributed** — not just vector search.

**14 memory types** (Tab 4 §14): working · episodic · semantic · canonical · instance · behavioral · procedural · trace-derived · profile · environment · goal · world-state · pattern · policy.

```python
class MemoryRecord(BaseModel):
    memory_id: str
    type: MemoryType
    content: Any
    source: str
    confidence: float
    timestamp: int
    scope: str
    tags: list[str]
    links: list[MemoryRef]
    expiry: int | None
    promotion_status: PromotionStatus
    reason: str
```

### 10.3 Trace vs Memory (`CANONICAL` — Tab 9 §12.4)

This distinction is permanent and load-bearing:

- **Trace** = complete execution record
- **Memory Candidate** = selected learning-worthy information
- **Memory** = approved persisted knowledge
- **Canonical Memory** = promoted general knowledge
- **Instance Memory** = user/account-specific state

Correct flow:

```
Execution → Trace → Outcome → Learning Proposal
  → Memory Candidate → Review/Promotion → Memory / World Model Update
```

### 10.4 Profiles

Profiles are **compiled views** of memory and world state relevant to an entity. They are not memory themselves and should be regenerated from evidence, not manually trusted forever.

**Types:** user · contact · client · entity · device · environment · workstation · agent · capability · adapter · model · worker.

**Contents:** identity · behavior · preferences · communication style · goals · risks · permissions · relationships · history · patterns · trust/confidence · context boundaries.

## 11. Layer 5 — Composition Layer

Turns intent + state into complete executable systems. This is the layer that contains the most distinct subsystems, each with a specific role.

### 11.1 Registries

Canonical discovery indexes for selectable components. Answer: *what exists? what can be used? what version? under what constraints? at what cost/reliability/authority?*

**17 registry types:** capability · adapter · backend · environment · worker · template · workflow · agent · model · tool · policy · memory · prompt · schema · evaluation · domain · workstation_mode · boot_sequence.

```python
class RegistryItem(BaseModel):
    id: str
    name: str
    type: str
    version: str
    inputs: dict
    outputs: dict
    constraints: list[Constraint]
    environment: EnvironmentRef | None
    cost: CostModel
    latency: LatencyModel
    reliability: float
    authority_required: AuthorityLevel
    dependencies: list[str]
    owner: str
    status: ItemStatus
    metadata: dict
```

**Rules:** no hardcoded capability lookup, no backend lookup outside registry, version everything, support deprecation, support fallback, queryable by composition engine, observable via trace.

### 11.2 Libraries

Reusable knowledge, patterns, frameworks, playbooks, examples, maps, reasoning structures.

**15 library types:** domain · system · pattern · primitive · workflow · decision · governance · adapter · benchmark · prompt · playbook · ontology · quality · failure_mode · mastery.

### 11.3 Templates

**Templates are not prompts.** A template is a typed, instantiable blueprint:

```
immutable primitives
  + customizable primitive slots
  + validation rules
  + feedback loop
  + governance requirements
  + quality criteria
  + memory update rules
```

**Immutable primitives** (structural elements that should not change per user): input slot · processing step · output slot · feedback loop · constraint check · failure handler · quality benchmark · governance gate · trace event · memory update.

**Customizable slots** (filled by user context): user goal · domain · target environment · tools · constraints · tone · budget · timeline · risk tolerance · approval level · desired output format · success metric.

```python
class Template(BaseModel):
    id: str
    name: str
    domain: str
    purpose: str
    immutable_primitives: list[ImmutablePrimitive]
    customizable_slots: list[Slot]
    required_slots: list[Slot]
    optional_slots: list[Slot]
    inputs: dict
    outputs: dict
    constraints: list[Constraint]
    default_steps: list[Step]
    feedback_loop: FeedbackLoopSpec
    failure_modes: list[FailureMode]
    governance_requirements: GovernanceSpec
    quality_benchmarks: list[Benchmark]
    compatible_capabilities: list[CapabilityRef]
    compatible_adapters: list[AdapterRef]
    memory_update_rules: list[MemoryUpdateRule]
```

**Lifecycle:** select → bind user/world context → fill slots → validate required → run completeness engine → attach capabilities/adapters/environments → generate executable composition → govern → execute → observe feedback → update template performance stats.

### 11.4 Capabilities

A capability is an **abstract ability**. Not a tool, not an adapter, not an execution.

```python
class Capability(BaseModel):
    capability_id: str
    name: str
    inputs: dict
    outputs: dict
    cost: CostModel
    latency: LatencyModel
    reliability: float
    required_environment: list[EnvironmentType]
    required_adapter: list[AdapterRef]
    required_worker: list[WorkerType]
    authority_required: AuthorityLevel
    constraints: list[Constraint]
    failure_modes: list[FailureMode]
    observability: ObservabilitySpec
    proof_requirements: list[ProofRequirement]
```

**Types:** llm_reasoning · code_editing · shell_command · browser_action · api_operation · file_operation · workflow_execution · memory_query · world_model_update · notification · calendar_action · email_action · device_control · simulation · robotic_action · human_approval_request · computer_use_operation.

**Rule:** the composition engine selects capabilities. Execution does not hardcode them.

### 11.5 The Registry/Library/Template/Memory Distinction `CANONICAL`

```
Registry = what exists and can be selected (executable/selectable inventory)
Library  = reusable knowledge and frameworks
Template = instantiable structured blueprint
Memory   = learned/source-attributed state
Profile  = structured model of an entity
Capability = abstract ability
Adapter  = external connection/translation boundary
```

This distinction is permanent. Without it the system becomes a pile of templates instead of a runtime.

### 11.6 Composition Engine

Transforms structured intent and world context into executable compositions.

**15-step composition standard:** intent binding → world-state grounding → memory recall → domain mapping → registry lookup → library retrieval → template selection → slot filling → capability selection → adapter/environment matching → mastery requirement detection → constraint binding → completeness validation → quality validation → governance classification → execution plan generation.

```python
class ExecutableComposition(BaseModel):
    composition_id: str
    goal: str
    selected_template: TemplateRef
    filled_slots: dict
    selected_capabilities: list[CapabilityRef]
    required_adapters: list[AdapterRef]
    required_environments: list[EnvironmentRef]
    required_workers: list[WorkerRef]
    steps: list[Step]
    dependencies: list[Dependency]
    constraints: list[Constraint]
    failure_modes: list[FailureMode]
    feedback_loop: FeedbackLoopSpec
    governance_requirements: GovernanceSpec
    mastery_requirements: list[MasteryRequirement]
    quality_criteria: list[QualityCriterion]
    memory_update_rules: list[MemoryUpdateRule]
```

**Invalid composition conditions:** missing input path · output path · feedback path · governance path · failure handling · environment declaration · capability mapping · adapter boundary · traceability · proof requirements.

### 11.7 Planning

Transforms compositions into ordered execution strategies.

**Plan types:** single-step · multi-step · DAG · contingency · simulation-informed · receding horizon · parallel worker · human-approval.

### 11.8 Completeness Engine

Prevents partial systems. Every plan/workflow/template/composition/automation/advisory response must satisfy 13 required slots:

input · processing · output · feedback · constraints · failure handling · optimization loop · governance requirement · execution environment · observability · memory/update path · quality benchmark · proof requirement

**Rule:** Incomplete executable systems cannot proceed to execution. Incomplete advisory outputs must explicitly disclose missing slots.

### 11.9 Quality / Excellence Engine

Ensures outputs and plans meet the highest feasible standard under constraints.

**The rule (Tab 4 §24):** UMH should not produce the first acceptable answer. It should produce the best feasible output under the user's constraints. Quality is *not* infinite perfectionism — it is bounded by time, cost, risk, available data, user preference, environment limitations, authority level.

For code tasks specifically, the quality gate enforces: lint/test pass · small diff · no core-file mutation without approval · executable proof · trace.

### 11.10 Universal Mastery / Competence Layer `CANONICAL` (Tab 9 — new)

Before UMH executes, verify that the system has sufficient scoped, versioned, testable, fresh, proof-backed competence to perform the action correctly under the current context and constraints. See Law 5.11.

The current implementation slice is the **Tool Mastery Engine**, focused on whichever external system is being added (Google Workspace adapters for the W0-001 validation test, etc.).

```python
class MasteryRequirement(BaseModel):
    mastery_id: str
    category: MasteryCategory
    target: str
    capability_scope: list[str]
    risk_level: RiskLevel
    required_freshness: timedelta
    required_tests: list[TestRef]
    required_proof: list[ProofRequirement]
    current_status: MasteryStatus
    gaps: list[MasteryGap]
```

## 12. Layer 6 — Governance Layer

Controls authority, risk, permissions, policy, escalation, safety. Security is **nested under** governance. Governance decides what is allowed; security enforces protection.

```python
class GovernancePolicy(BaseModel):
    authority_level: AuthorityLevel
    risk_model: RiskModel
    constraints: list[Constraint]
    permissions: list[Permission]
    escalation_rules: list[EscalationRule]
    approval_requirements: list[ApprovalRequirement]
    environment_limits: list[EnvironmentLimit]
```

**Authority levels:** autonomous · notify · approve · escalate · deny.

**Risk classes for this stack specifically:** read-only · reversible write · irreversible write · financial · security-sensitive · identity/reputation-sensitive · destructive local-device action · external communication · legal/compliance · physical-world actuation.

**Dangerous categories that always require strict approval and rollback:** deleting/uninstalling files/apps/processes · device optimization/overclocking · browser account actions · sending DMs/emails · financial transactions · production code deployment · manufacturing actuators.

## 13. Layer 7 — Execution Plane

Performs approved work through the single execution spine. Owns actions, work packets, queues, DAGs, workers, runtimes, environments, actuation, retries, timeouts, idempotency, result collection.

### 13.1 Action System

```python
class ActionContract(BaseModel):
    action_id: str
    action_type: str
    intended_state_change: StateTransition
    required_capabilities: list[CapabilityRef]
    required_adapters: list[AdapterRef]
    required_environments: list[EnvironmentRef]
    required_workers: list[WorkerRef]
    required_mastery: list[MasteryRequirement]
    governance_policy: GovernancePolicyRef
    risk_level: RiskLevel
    authority_required: AuthorityLevel
    success_criteria: list[SuccessCriterion]
    failure_modes: list[FailureMode]
    proof_requirements: list[ProofRequirement]
    idempotency_key: str
```

### 13.2 Work Packet

The governed executable instruction passed to a worker/runtime.

```python
class WorkPacket(BaseModel):
    packet_id: str
    work_order_id: str
    title: str
    description: str
    action_type: str
    target_environment: EnvironmentRef
    required_adapter_packages: list[AdapterPackageRef]
    required_tool_or_mastery_packs: list[MasteryRef]
    risk_level: RiskLevel
    approval_status: ApprovalStatus
    founder_confirmation_required: bool
    allowed_actions: list[str]
    blocked_actions: list[str]
    expected_outputs: list[OutputSpec]
    proof_requirements: list[ProofRequirement]
    timeout_seconds: int
    created_at: int
    expires_at: int
    status: PacketStatus
    trace_id: str
    notes: str
```

**Rules:**

- No high-risk packet executes without approval.
- No local GUI packet executes unless target environment includes the correct local GUI/browser environment.
- No packet executes without `blocked_actions` and `proof_requirements`.

### 13.3 Worker Runtime

The process/session/node that performs execution.

**Examples in this stack:** VPS worker · local WSL worker · local Windows GUI worker · tmux session · container worker · browser worker · API worker · model worker · human operator · future robot/device worker.

**Worker cells may:** execute bounded tasks · report result · write proof artifacts · terminate.

**Worker cells may not:** bypass governance · write memory directly · execute outside environment constraints · persist unauthorized state · call external systems without adapter boundary.

The **advisor/control cell** (Tab 4 §26) may persist across cycles. Worker cells are disposable.

### 13.4 Environment System

```python
class Environment(BaseModel):
    environment_id: str
    type: EnvironmentType
    capabilities: list[CapabilityRef]
    constraints: list[Constraint]
    resources: ResourceModel
    permissions: list[Permission]
    network_state: NetworkState
    availability: float
    reliability: float
```

**Hybrid execution requirements** for this stack:

- **VPS** as persistent advisor/control node (`/opt/OS`, srv1500858, Ubuntu 24.04)
- **Local machine** as local/GUI/high-compute worker (Windows + WSL)
- **Mobile** as command interface (iPhone via Tailscale + Termius)
- **Cloud** as scalable fallback
- **Sandbox/container** as isolated execution cell
- **Offline mode** where possible

### 13.5 Actuation

The low-level effect-producing operation. Types: OS control · browser automation · API operation · file operation · workflow execution · device control · notification · robotic/physical action · human approval request.

**Correct separation:** Adapter translates. Worker executes. Actuator affects. Proof validates.

## 14. Layer 8 — Adapter Boundary Layer

Connects UMH to external reality. Adapters translate external systems into UMH-readable contracts and translate UMH work intent into formats required by external systems. **Adapters do not independently execute.**

### 14.1 Corrected Adapter Contract `CANONICAL` (Tab 9 §16.2, supersedes Tab 4)

```python
class Adapter(Protocol):
    def connect(self) -> Connection: ...
    def validate_connection(self) -> ValidationResult: ...
    def describe_capabilities(self) -> list[Capability]: ...
    def translate_request(self, work_packet: WorkPacket) -> ExternalRequest: ...
    def validate_operation(self, request: ExternalRequest) -> ValidationResult: ...
    def normalize_result(self, raw: ExternalResponse) -> NormalizedResult: ...
    def observe_state(self) -> StateSnapshot: ...
    def disconnect(self) -> None: ...
```

The earlier `execute()` method (Tab 4 §20) is **deprecated**. If an engineering implementation needs `execute_adapter_operation()`, that method belongs to the governed Execution Plane and invokes adapter-bound operations under authority.

### 14.2 Adapter Categories (15)

Tool · SaaS · API · CLI · MCP · Environment · Runtime · Model · Human Approval · Data Source · Filesystem · Database · Browser · Computer Use · Physical-World.

### 14.3 Adapter Package & Adapter Family

```python
class AdapterPackage(BaseModel):
    package_id: str
    name: str
    external_system: str
    category: AdapterCategory
    capabilities: list[CapabilityRef]
    access_paths: list[AccessPath]
    governance_policy: GovernancePolicyRef
    mastery_requirements: list[MasteryRequirement]
    supported_environments: list[EnvironmentType]
    proof_requirements: list[ProofRequirement]
    maturity_status: MaturityStatus
    version: str
```

An **Adapter Family** is a suite-level grouping of related service adapter packages:

```
Google Workspace Adapter Family
├─ Google Workspace Core
├─ Google Drive Adapter Package
├─ Google Docs Adapter Package
├─ Gmail Adapter Package
├─ Google Sheets Adapter Package
├─ Google Slides Adapter Package
└─ Google Calendar Adapter Package
```

The family coordinates shared identity, auth, governance, rate limits, and ecosystem-level doctrine.

### 14.4 Access Path

The specific method used through an adapter. Examples: API · SDK · CLI · MCP · Computer Use · browser extension · local export/archive · local sync · file parser · human operator.

### 14.5 The Full Separation Worked Example

The canonical example from Tab 9 §16.7:

```
Capability:    tab_aware_document_extraction
Adapter:       Google Docs Adapter
Access Paths:  Google Docs API, Google Docs Computer Use,
               Google Docs MCP, Google Docs export parser
Environment:   VPS for API, Local Windows GUI for Computer Use
Worker:        API worker or local GUI worker
```

This decomposition is what makes the system swappable across access paths without rewriting capability or composition logic.

### 14.6 The Leverage Doctrine Applied to Adapter Choice

When harvesting from any external stack, classify the stack by abstraction layer **before** evaluating. The general rule (from `leverage-principle/SKILL.md`):

- **Layer 1 — Model.** Stateless vision-language model that takes goals + screenshots and emits actions. Consume directly. *(Anthropic computer-use, OpenAI CUA, UI-TARS model.)*
- **Layer 2 — Agent runtime.** Stateful, opinionated agent with its own loop. Harvest plumbing, not the loop. *(browser-use, Skyvern, UI-TARS Desktop, Agent TARS.)*
- **Layer 3 — Primitive.** Raw I/O drivers. Vendor in directly. *(Playwright, PyAutoGUI, AppleScript, PowerShell relay.)*

UMH already owns the cognitive loop. Adopting a Layer 2 runtime wholesale produces two competing loops and collapses the architecture. Wrap Layer 1 and Layer 3 behind UMH's adapter contracts. Layer 2 is for harvesting patterns, not for adopting cognition.

## 15. Layer 9 — Observability + Proof Layer

Observability makes every decision and action inspectable. Proof validates that the action actually happened correctly.

### 15.1 Trace

```python
class Trace(BaseModel):
    trace_id: str
    user_id: str
    input: Signal
    interpretation: InterpretedSignal
    world_context: WorldStateSnapshot
    memory_context: list[MemoryRecord]
    composition: ExecutableComposition
    governance: GovernanceDecision
    work_packet: WorkPacket
    adapter_boundary: AdapterRef
    environment: EnvironmentRef
    execution: ExecutionResult
    result: Any
    proof: ProofArtifact
    outcome: Outcome
    feedback: FeedbackEvent | None
    timestamps: TimestampSet
```

### 15.2 Proof

Evidence appropriate to the action, risk, and environment.

```python
class ProofArtifact(BaseModel):
    proof_id: str
    action_id: str
    packet_id: str
    environment_id: str
    worker_id: str
    evidence_type: EvidenceType
    evidence_summary: str
    source: str
    timestamp: int
    governance_compliance: bool
    no_secret_confirmed: bool
    no_mutation_confirmed: bool
    parity_result: ParityResult | None
    founder_confirmation_status: ConfirmationStatus
    confidence: float
```

### 15.3 Trace vs Proof vs Outcome vs Feedback vs Audit `CANONICAL`

- **Trace** = what happened
- **Proof** = evidence it happened correctly
- **Outcome** = whether it achieved the goal
- **Feedback** = signal used for improvement
- **Audit** = compliance record

### 15.4 Evidence Standard

Claims require evidence appropriate to their risk and environment. A unit test can prove a contract. A local GUI Computer Use claim requires proof from the actual local GUI environment. **This prevents false maturity** — the failure mode where the system claims a capability is mature because the API path works, while the CU path has never been validated end-to-end.

## 16. Layer 10 — Learning + Self-Regulation

### 16.1 Learning Loop

```
Outcome → Feedback → Pattern → Compression → Proposal
       → Evaluation → Governance → Update
```

**Learning types:** local feedback · strategy feedback · pattern confidence · temporal decay · weight evolution · regime learning · cross-dimension interaction · policy learning · world-model update · profile update · template performance update · capability reliability update · adapter reliability update · mastery update.

**Rule:** learning must be bounded, explainable, and governed. **No hidden self-modification.**

### 16.2 Organism Layer

UMH regulates itself like a coherent adaptive system. **Tab 13's grounding correction is important:** this should not become biological-metaphor bloat. "Organism" technically means:

- health checks · resource monitoring · queue backpressure · anomaly detection · degraded mode · module heartbeat · task prioritization · budget control · compute allocation · memory compaction · retry suppression · stuck-loop detection

**Internal signaling:**

```python
class InternalSignal(BaseModel):
    source_module: str
    signal_type: SignalType
    severity: Severity
    payload: dict
    timestamp: int
    recommended_action: str | None
```

**Operating cycles:** day · night · advisor · worker · review · maintenance.

### 16.3 Self-Improvement Rule

The bounded self-recursion loop:

```
detect issue → propose improvement → simulate/evaluate
  → sandbox → test → compare before/after
  → request approval if needed → deploy → trace → monitor
```

### 16.4 Advisor Cell and Deliberation Council (Tab 6 §8)

For high-importance reasoning, the advisor cell uses a model-agnostic **Deliberation Council**:

- primary strategist
- skeptic / red-team critic
- completeness auditor
- risk/governance auditor
- domain specialist
- implementation engineer
- synthesis judge

Purpose: reduce hallucination, single-model bias, missing assumptions, incomplete decomposition, bad composition, overweighting recent context, weak risk assessment, low-quality execution plans.

Belongs in: advisor strategy · decomposition · composition · completeness · quality · governance review · world-model simulation · self-recursive improvement proposals.

**The council remains advisory.** It cannot execute. It cannot bypass governance. It produces structured deliberation artifacts.

-----

# PART VI — TERMINOLOGY LOCK

`CANONICAL` (Tab 9 §28). Use these definitions permanently. Conflating any pair is an architectural error.

|Term               |Definition                                                                                                                    |
|-------------------|------------------------------------------------------------------------------------------------------------------------------|
|**Signal**         |Raw or structured input from user, system, environment, model, file, API, sensor, worker, or event stream.                    |
|**Interpretation** |Extraction of meaning, intent, ambiguity, risk, domain, constraints, desired outcome from a signal.                           |
|**Decomposition**  |Breaking meaning into concepts, entities, primitives, relationships, constraints, context.                                    |
|**Ontology**       |Internal primitive language UMH uses to model reality.                                                                        |
|**Domain**         |Operational area of reality with entities, workflows, constraints, failure modes, benchmarks, and laws.                       |
|**World Model**    |Structured representation of user/world/environment/system state.                                                             |
|**Memory**         |Durable, typed, source-attributed state used for continuity and learning.                                                     |
|**Profile**        |Structured compiled model of an entity.                                                                                       |
|**Registry**       |Queryable index of selectable system components.                                                                              |
|**Library**        |Reusable knowledge, patterns, playbooks, maps, frameworks, examples, doctrine.                                                |
|**Template**       |Typed, instantiable blueprint for composing systems.                                                                          |
|**Capability**     |An abstract ability UMH can select.                                                                                           |
|**Adapter**        |Connection and translation boundary to an external system.                                                                    |
|**Adapter Family** |Suite-level grouping of related adapter packages.                                                                             |
|**Access Path**    |Specific method used through an adapter (API, SDK, CLI, MCP, Computer Use, …).                                                |
|**Environment**    |Where execution occurs.                                                                                                       |
|**Action**         |A proposed state transformation.                                                                                              |
|**Work Packet**    |Governed instruction passed to an execution runtime.                                                                          |
|**Execution Spine**|The only authorized path from plan to result.                                                                                 |
|**Worker Runtime** |Process/session/node that performs execution.                                                                                 |
|**Actuation**      |Low-level effect-producing operation.                                                                                         |
|**Governance**     |Authority, risk, policy, approval, constraint enforcement.                                                                    |
|**Mastery**        |Scoped, versioned, testable competence required before execution.                                                             |
|**Proof**          |Evidence that the action happened correctly.                                                                                  |
|**Trace**          |Full inspectable record of input, decision, execution, result, outcome, and learning.                                         |
|**Learning**       |Governed update process from outcome to improved memory, policy, world model, template, adapter, capability, or mastery state.|

-----

# PART VII — STRATEGIC STACK & PRODUCT RELATIONSHIP

Tab 8 + Tab 12's classification establishes the product hierarchy. The platforms are **not** the substrate.

```
OST (Operating System Technologies) — HoldCo
└── UMH: intelligence + execution substrate
    ├── EntrepreneurOS: business operations interface
    ├── CreatorOS:      audience/content/commerce interface
    ├── LYFEOS:         personal life interface
    ├── InvestorOS:     capital allocation interface (future)
    └── Workstation/Jarvis: embodied operator interface
```

## 17. The Four Strict Layers (Tab 12 §4)

The doc is emphatic that layer collapse is the primary source of architectural drift. Enforce these boundaries:

### A. Substrate — UMH

perception · decomposition · memory · world model · planning · composition · execution · governance · learning. **This is the universal harness itself.**

### B. Execution Infrastructure

VPS · workstation · relay · queues · orchestration · adapters · action system · scheduling · runtime. **Generic execution machinery.**

### C. Platform Surfaces

LYFEOS · EntrepreneurOS · CreatorOS · InvestorOS. **These are projections/interfaces, not substrate.** They translate user intent into UMH signals, provide domain-specific views, expose workflows and dashboards, display results, collect feedback, enforce domain-specific permissions. They do not own memory, governance, capability registry, execution spine, adapter contracts, or learning loops.

### D. Domain Systems

CRM · content engine · health system · sales workflows · finance systems · onboarding systems. **Composed systems**, not core architecture.

## 18. The Refined Strategic Thesis (Tab 8)

The commercial wedge is **EntrepreneurOS powered by UMH** as the internal operating system for acquiring, building, optimizing, and compounding companies — then releasing a constrained public version after the internal engine proves measurable operational lift.

This is the grounded version of "AI-Native BlackRock":

> An AI-native operating holdco that uses proprietary intelligence infrastructure to build, acquire, optimize, and compound cash-flowing assets.

The flywheel:

```
Build/Acquire business
  → Install EntrepreneurOS/UMH
  → Capture data
  → Improve workflows
  → Increase margin/revenue
  → Convert improvements into templates
  → Add templates to libraries
  → Improve UMH
  → Make next business easier to optimize
  → Increase portfolio cash flow
  → Fund infrastructure
  → Increase moat
```

## 19. The Eight-Layer Moat

The competitive position is composed of eight stacked moats, not one:

1. **Software moat** — UMH/EOS architecture
1. **Data moat** — operational traces/outcomes across real companies
1. **Workflow moat** — proprietary templates/playbooks
1. **Distribution moat** — personal brand + CreatorOS
1. **Network moat** — operators, creators, vendors, investors
1. **Infrastructure moat** — fulfillment/manufacturing/real estate
1. **Capital moat** — cash flow from portfolio
1. **Trust moat** — governance/auditability/safety

Most competitors will have one or two. The aim is all eight.

## 20. Correct Sequencing (Tab 8 §"The Correct Order")

1. Software intelligence layer
1. Business workflow proof
1. Distribution engine
1. Cash-flowing operating companies
1. Public EntrepreneurOS
1. Acquisition/roll-up playbook
1. Real estate support layer
1. Manufacturing/fulfillment where demand justifies it
1. AI OS / proprietary runtime
1. Full infrastructure empire

-----

# PART VIII — ROADMAP

## 21. Current State `PROVEN`

After Phase 75B, UMH has the MVP spine:

```
Input → Control Plane → Identity → Governance Gate → Backend Registry
      → Canonical Execution Engine → Trace Store → Result
```

That means UMH is no longer just an intelligence kernel. It is now a **governed execution harness**. But it is not fully "usable" until three things ship:

1. real adapters
1. minimal workstation continuity
1. trace → memory/outcome loop

The MVP completion gate (Tab 5):

```
User enters task
→ UMH loads identity
→ workstation context loads
→ control plane interprets task
→ composition creates directive
→ governance evaluates
→ adapter executes (via worker)
→ trace persists
→ outcome classified
→ memory updates
→ user can resume later
```

## 22. The Eight Stages

The phase-number tension between Tab 5 (76–108) and Tab 6 (80–110) is bookkeeping. The **stages** below are canonical.

### Stage 1 — Finish the MVP `ACTIVE`

**Goal:** Turn the governed harness from "runnable" into "actually useful."

- **Phase 76** — MVP Adapter Pack + Real Execution Loop. CLI · filesystem · HTTP/API · browser (or simulated browser) adapters. Acceptance: a real governed task executes end-to-end through the spine with trace.
- **Phase 77** — MVP Workstation State. `WorkstationProfile` · `DeviceRegistry` · `EnvironmentRegistry` · `ActiveMode` · `SessionState` · `TraceResumeSummary` · `PendingApprovalView` · `ExecutionPreference`. MVP modes: Command Center · Developer · Research · Maintenance. Acceptance: UMH answers who/what/where/recent/pending/next.
- **Phase 78** — Trace → Outcome → Memory Loop. `TraceAnalyzer` · `OutcomeClassifier` · `OutcomeMemoryBridge` · `TraceMemoryWriter` · `ExecutionFeedbackRecord`. Acceptance: every execution produces trace → outcome → memory record → feedback signal.

### Stage 2 — Make MVP Operational `PLANNED`

- **Phase 79** — Observability + Trace Query System
- **Phase 80** — Registry Unification (no more hardcoded lookups)
- **Phase 81** — Storage + Memory Discipline Enforcement
- **Phase 82** — Legacy Runtime Deprecation Plan Execution

### Stage 3 — Composition, Templates, Libraries, Registries `PLANNED`

- **Phase 83** — Template System v1
- **Phase 84** — Library System v1
- **Phase 85** — Composition Engine v1 (the 15-step standard)
- **Phase 86** — Completeness Engine v1
- **Phase 87** — Quality / Excellence Engine v1

### Stage 4 — Explicit World Model `PLANNED`

- **Phase 88** — World Model Core (`WorldState` · `Entity` · `Relationship` · `Fact` · `StateValue` · `TemporalState` · `UncertaintyModel`)
- **Phase 89** — User + Environment Model Integration
- **Phase 90** — World Model Update Loop
- **Phase 91** — Temporal World Model

### Stage 5 — Learning, Causality, Simulation `PLANNED`

- **Phase 92** — Causal Attribution v1
- **Phase 93** — Simulation Interface v1
- **Phase 94** — Predictive Planning v1
- **Phase 95** — Multi-Step Planning Engine

### Stage 6 — Workstation, Presence, Organism Runtime `PLANNED`

- **Phase 96** — Workstation Modes v2
- **Phase 97** — Presence System v1
- **Phase 98** — Organism Internal Signaling
- **Phase 99** — Resource / Attention Allocation
- **Phase 100** — Self-Regulation / Homeostasis

### Stage 7 — Frontier AI OS Path `SPECULATIVE`

- **Phase 101** — Model Registry + Multi-Model Routing
- **Phase 102** — MCP / External Agent Harnessing
- **Phase 103** — Embodied / Perception Expansion
- **Phase 104** — Advanced Simulation + World Model Coupling
- **Phase 105** — Proprietary Intelligence Path (training data pipeline, fine-tune interface, self-hosted runtime)

### Stage 8 — Distribution, Installability, Productization `PLANNED` (can run in parallel earlier)

- **Phase 106** — Distribution Layer (installer, updater, package manager, platform detector, dependency resolver)
- **Phase 107** — Onboarding / First Boot
- **Phase 108** — Security Hardening (secret manager, permission scopes, sandbox policies, audit export, rollback, least-privilege adapter permissions)

## 23. Stage-Gate Execution Rule

Before every phase, ask:

1. Does this strengthen the canonical system?
1. Does it preserve the spine?
1. Does it avoid redundancy?
1. Does it map to the locked spec?
1. Does it move MVP or end-state forward?

If yes → build. If no → reject.

-----

# PART IX — RELEASE PATH (Tab 7)

The release standard is **gate-based, not time-based**, scaled to the authority level UMH is allowed to exercise.

|Stage                            |Duration                               |What ships                                                                                                                                                                            |Authority allowed                |
|---------------------------------|---------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------|
|1. Founder/internal dogfood      |2–4 weeks min                          |Local workstation, CLI/API, Command Center contract views, trace/outcome/feedback, storage/memory discipline, registry, interface state, read-only dashboards, safe governed execution|All — but on the founder only    |
|2. Trusted alpha                 |4–8 weeks                              |Read-only views · task planning · local assistant behavior · controlled CLI · safe file ops in sandbox · basic workflow execution · observability                                     |Reversible only                  |
|3. Private beta / design partners|8–12 weeks                             |Above + selected reversible-write external actions                                                                                                                                    |Reversible + low-risk external   |
|4. Public beta                   |After 3–6 months controlled testing    |Narrowed product: "AI command center for governed local-first execution, memory, workflow orchestration, and operator visibility"                                                     |Approval-gated external actions  |
|5. Full public launch            |After 6–12 months progressive hardening|Stable onboarding/execution/storage/memory/interface/governance/adapter permissions, strong observability, incident handling                                                          |Per per-account governance policy|

**Testing duration scales by authority class:**

- Read-only: 2–6 weeks
- Reversible: 2–3 months
- External actions (send emails, post content, deploy code, modify CRM): 3–6 months minimum with approval gates
- High-risk (payments, financial, legal, deletion, production infra, mass messaging): 6–12+ months with proven safety, auditability, rollback, governance

**Release readiness gate:**

> A non-technical user can install/onboard, connect one or two safe tools, ask UMH to do a useful workflow, see exactly what happened, approve anything risky, recover from errors, and trust that nothing hidden or destructive happened.

-----

# PART X — TECHNICAL IMPLEMENTATION

## 24. Final Canonical Module Tree

Tab 9 §20's structure. Reflects macro-layers, not dozens of equal top-level concepts. `CANONICAL`

```
universal_meta_harness/
  interface/
    cli/  api/  desktop/  mobile/  voice/  presence/  workstation/

  control_plane/
    runtime/  event_bus/  router/  invariants/  protocols/

  understanding/
    perception/  interpretation/  decomposition/  ontology/  domains/

  state/
    world_model/  memory/  profiles/  storage/

  composition/
    registries/  libraries/  templates/  capabilities/
    planning/  completeness/  quality/  mastery/

  governance/
    policy/  risk/  approval/  permissions/  security/

  execution/
    actions/  work_packets/  queue/  dag/
    workers/  environments/  actuation/  runtime/

  adapters/
    adapter_engine/  tool_adapters/  api_adapters/  cli_adapters/
    mcp_adapters/  model_adapters/  environment_adapters/
    data_source_adapters/  human_approval_adapters/
    browser_adapters/  physical_world_adapters/

  observability/
    trace/  proof/  audit/  metrics/  evals/

  learning/
    feedback/  pattern_detection/  update_proposals/
    self_regulation/  organism/

  distribution/
    installer/  updater/  package_manager/  platform_detector/

  onboarding/
    setup_wizard/  device_linking/  permission_config/
    adapter_setup/  first_boot/

  tests/
```

No top-level domain is optional in the final architecture. MVP may implement minimal versions, but the architecture must *reserve* every domain.

## 25. Protocol Pack

The formal contract layer. No subsystem talks to another subsystem directly. All communication flows through typed protocols enforced by the Control Plane.

```
protocols/
  signal.py · interpretation.py · decomposition.py
  ontology.py · domain.py · world.py · memory.py · profile.py
  registry.py · library.py · template.py · capability.py
  composition.py · planning.py · mastery.py
  governance.py · action.py · work_packet.py · execution.py
  adapter.py · environment.py · worker.py · actuation.py
  proof.py · trace.py · outcome.py · feedback.py · learning.py
```

**Implementation:** Pydantic v2 models with versioned schemas. Every protocol has a `schema_version` field; bumping is governed (no silent contract breaks). Contract tests run on every PR.

## 26. Persistence Architecture

Tab 13 §9.1 names this as one of the unlocked decisions. Recommendation grounded in the current `/opt/OS` stack:

- **Postgres (Neon)** for the canonical record. The OS Trinity already runs on Neon DB with a dev/prod branch split. `pgvector` for embeddings.
- **SQLite** only for local-only worker state (tmux session state, transient queues) — never for canonical truth.
- **Obsidian vault** is an *export target*, not a source of truth for execution state. The system writes to Obsidian; the system does not read from Obsidian as ground truth.
- **Event log** — append-only on Postgres, with replay capability. This is what makes the system event-sourced where it matters.
- **Trace retention** — full traces for 90 days; compressed summaries indefinitely. Memory promotion from trace happens through the governed Learning Layer, not by reading raw traces.
- **Backup** — Neon's point-in-time recovery for the canonical record. Off-site backup of memory promotion artifacts.

## 27. Event Model

Tab 13 §9.2. The spine needs explicit events:

```
SignalReceived  →  InterpretationCompleted  →  DecompositionCompleted
  →  WorldUpdated  →  MemoryRetrieved
  →  PlanComposed  →  MasteryChecked  →  QualityChecked
  →  GovernanceEvaluated
  →  WorkPacketCreated  →  ExecutionStarted
  →  AdapterCalled  →  ActuationCompleted
  →  ResultCollected  →  ProofValidated
  →  TracePersisted  →  OutcomeEvaluated
  →  LearningProposed  →  MemoryWritten  →  LearningUpdated
```

Without an event model, the control plane becomes procedural spaghetti.

## 28. Capability Registry Schema

```yaml
id: capability_id
name: human-readable name
description: what this does
inputs_schema: <Pydantic schema ref>
outputs_schema: <Pydantic schema ref>
risk_level: read_only | reversible | irreversible | financial | …
allowed_environments: [vps, local_wsl, local_gui, …]
required_permissions: [list]
adapters: [adapter_ref, adapter_ref, …]   # one capability, many adapter implementations
cost_estimate: {model: per_call_usd, params: …}
latency_estimate: {p50_ms: …, p95_ms: …}
reliability_score: 0.0–1.0
observability_requirements: [trace, proof, metrics]
failure_modes: [list of FailureMode]
mastery_requirements: [list of MasteryRequirement]
```

## 29. The Do-Not-Touch Core

From the leverage doctrine, these files require explicit plan-approval before any modification. Updated to reflect both the existing EOS spine and UMH-mapped equivalents:

- `eos_ai/gateway.py`
- `cognitive_loop.py`
- `model_router.py`
- `agent_runtime.py`
- `primitives.py`
- Future UMH spine equivalents (control_plane runtime, execution spine entry, governance gate, memory storage gateway)

Any change to these requires snapshot, justification, and approval.

## 30. The W0-001 Validation Test `ACTIVE`

W0-001 is the canonical architecture validation. It is *not* "just a Google Docs ingestion test." Tab 9 §24 makes this explicit: it tests Adapter System, External Boundary Law, Environment System, Execution Plane, Computer Use, Governance, Proof, Memory Discipline, Mastery, Data Ingestion — all in one end-to-end run.

**Current declared package set:**

```
W-GWS-CORE-001    — Google Workspace Core Foundation
W-GDRIVE-API-001  — Google Drive API Package
W-GDOCS-API-001   — Google Docs API Package
W-GDRIVE-CU-001   — Google Drive Computer Use Package
W-GDOCS-CU-001    — Google Docs Computer Use Package
```

**Current status:**

- API slice: ready
- Google Workspace Core: ready for W0-001 Drive/Docs scope
- Google Drive API: mature
- Google Docs API: mature
- Google Drive CU: provisional 100 pending founder/local confirmation
- Google Docs CU: partial; blocked by local GUI/foreground/content extraction gaps
- Local Worker Bridge: modeled, pending local bootstrap
- External Boundary Law: should be encoded before bridge checkpoint
- Full W0-001 triple-test: not ready until CU slice and ingestion validation complete

**What it validates end-to-end:** UMH can interpret the goal, identify external systems, route through adapter boundaries, select API and CU access paths, choose correct environments, check mastery, govern execution, generate work packets, route to workers, collect proof, validate coverage, avoid memory pollution, update maturity honestly.

This is the smallest live proof that the architecture works as specified.

## 31. The Immediate Implementation Sequence

From Tab 9 §30. This is the concrete next-10 steps:

1. Encode External Boundary Law with corrected "adapters do not execute" doctrine.
1. Update Phase 96.8A so the VPS/local worker bridge is clearly an Environment Adapter / bridge boundary.
1. Add Universal Mastery / Competence Layer doctrine.
1. Keep existing Tool Mastery Engine as the first implementation category under Universal Mastery.
1. Add mastery requirements to Work Packets, Adapter Packages, Capability Contracts, and Execution Plans.
1. Commit Phase 96.8A + External Boundary Law + Mastery Doctrine as a coherent checkpoint.
1. Bootstrap the local Windows worker bridge.
1. Run W0-001 CU through the local pull worker.
1. Use proof artifacts to update CU maturity.
1. Complete W0-001 ingestion validation.

## 32. Workstation Boot Sequences (worked examples)

### Developer Mode

- open repo · check git status · start tmux sessions · start Claude Code · load recent context · activate task queue · monitor tests

### Research Mode

- open knowledge vault · launch research agent · route sources through tool mastery protocol · write findings to library · summarize into memory

### Command Center

- display tasks · active agents · execution queue · risks/approvals · KPIs

### Overnight Mode

- run safe queued jobs · no destructive actions · summarize by morning · require approval for uncertain tasks

### Maintenance Mode

- health checks across VPS + local · clear stuck queues · compact memory · refresh adapter credentials · rotate logs

### Outreach Mode

- DM/email automation behind approval gates · template-driven only · all sent messages traced and stored

### Content Mode

- Remotion pipeline · CreatorOS routing · approval-gated publish

### Simulation Mode

- world-model queries only · no actuation · no external adapter calls · all-in-sandbox

### Emergency Mode

- read-only · all autonomy revoked · founder-only approval for everything

## 33. Phase Approval Guardrail

`CANONICAL` Tab 9 §27. No phase may be approved unless it answers all 15 questions:

1. Which macro-layer does this strengthen?
1. Which invariant does this preserve?
1. Which typed contract does this introduce or modify?
1. Which part of the single execution spine does it affect?
1. Which external boundary does it create or enforce?
1. Which environment does it touch?
1. Which worker/runtime performs the action?
1. Which adapter translates the external system?
1. Which mastery requirements are needed?
1. Which governance policy applies?
1. Which proof artifact validates completion?
1. Which trace path is created?
1. Which memory/learning path is affected?
1. Does this create redundancy?
1. Does this bypass control, governance, memory, or execution?

If a phase cannot answer these, it should not be built.

-----

# PART XI — CURRENT REALITY / HONEST STATUS

Tab 12 calls this "the MOST important missing section" because without it, hallucination and drift happen *organizationally*. Brutally honest classification:

## 34. Proven `PROVEN`

- Relay transport (Discord bridge to `dex_builder_main`)
- Authority gates (governance pre-execution check)
- WorkPacket validation
- VPS orchestration (`/opt/OS` on `srv1500858`)
- Foreground CU ingestion pipeline (the API slice)
- Phase 75B governed execution spine end-to-end: Input → Control Plane → Identity → Governance → Backend Registry → Canonical Execution Engine → Trace Store → Result
- Salience pipeline for EOS memory (conversation logging, salience scoring, consolidation, promotion thresholds, Neon metadata)
- Tailscale mesh (VPS + Windows + iPhone)
- ttyd / Termius / code-server access paths
- Persistent `claude` tmux session
- Claude Code 1-year OAuth token in `/opt/OS/.env.sessions` with `unset ANTHROPIC_API_KEY` guard + keepalive cron
- Remotion at `/opt/OS/content/remotion`
- Clerk auth flow on `feature/company-system`
- Core user flow: login → portfolio creation → company setup → Command Center
- `saas-dev-skill` extracted into standalone repo, dropped into OSv2 as local dev harness
- UserPromptSubmit hook capture (scripts/user_prompt_capture.py, .claude/settings.json hook configured, 453 conversation files captured)
- Full ingestion system — GenericIngestionOrchestrator + LocalFileSource + GWSSource + BusinessBridge (1,000+ LOC running in production)
- Multi-Model Routing across Claude/GPT/Gemini/local (1,000+ LOC in model_router.py, cc_sdk→Gemini→Groq→Ollama fallback chain)
- Transport §24 migration — 68 modules relocated to `execution/transport/`, 11 PROD callers updated, Docker-tested cold-start, thin shim at old path (2026-05-14)
- Law 5.5 memory API canonical enforcement — 54 raw-SQL sites migrated to AgentMemory/ConversationMemory stores across 3 tiers (2026-05-14)
- Cron operational reliability — 22/24 scripts verified CLEAN, 2 fixed (broken .env paths + moved modules), crontab audited and corrected (2026-05-14)

## 35. Partially Proven `PARTIAL`

- Workstation automation (modes exist conceptually, runtime is partial)
- Google session routing (API path solid, CU path provisional)
- Semantic retrieval tuning (basic recall works, ranking is naive)
- Subprocess lifecycle management (4GB swapfile + management works, but spawning cap is still a manual ceiling)
- Composition Engine — partial implementation; not yet the canonical 15-step engine from §11.6
- World Model — partial implementation; some entity/fact tables exist; not yet the full §10.1 structure
- Law 5.9 adapter contract — 2 of 6 identified adapters refactored to translate_request/normalize_result; 4 classified as INTERNAL_WORKER (out of scope) (2026-05-14)

## 36. Unverified `PARTIAL`

- Founder-confirmed foreground extraction (W-GDOCS-CU-001 still blocked on local GUI gaps)
- Full W0-001 triple-test (API/CU/parity)
- End-to-end RLHF loop (memory writes happen on only 2 of 13 message paths in the EOS gateway — the foundational diagnosis from earlier)

## 37. Not Built `PLANNED` / `SPECULATIVE`

- Unified memory graph (cross-product user identity is in place, but graph traversal is not)
- Autonomous reconciliation
- Workstation UI runtime (Command Center as a real interface, not just a contract)
- Completeness Engine v1
- Quality Engine v1
- Causal Attribution
- Simulation Interface
- Computer Use access path matured to "proven" status anywhere
- Mobile (Appium) control
- Desktop (PyAutoGUI) control beyond Playwright
- Distribution / Installer
- Onboarding wizard
- Security hardening (audit export, rollback, least-privilege adapter permissions)
- Proprietary intelligence runtime (training data pipeline, fine-tune interface)
- Anything in Stage 7

This list prevents architectural delusion. Phases must close gaps in §35–§37, not add new abstractions that depend on unsolved §36 items.

-----

# PART XII — DOCUMENT DRIFT, CONTRADICTIONS, OPEN QUESTIONS

A world-class spec review names what the source got wrong or left ambiguous.

## 38. The "Meta" vs "Model" Name Conflict

The Google Doc consistently uses **Universal Meta Harness**. The leverage skill in `/mnt/skills/user/leverage-principle/SKILL.md` calls it **Universal Model Harness**. The doc is the canonical source — the skill is stale. Recommendation: update the skill (and any user-memory references) to "Meta" so the term means one thing across surfaces.

The semantic difference is meaningful: "Model" implies a wrapper over models; "Meta" implies a layer above every harness-able system including models. The doc's framing is the broader and correct one.

## 39. The Adapter Contract Drift

Tab 4 §20 specifies `execute()`. Tab 9 §16.2 explicitly deprecates that. Any code already written against the Tab 4 contract needs to be migrated to the Tab 9 contract before the External Boundary Law can be honestly claimed as enforced. This is a non-trivial refactor surface — every existing adapter has to be split into translate/validate/normalize/observe, with the actual `execute` logic relocated to the Execution Plane.

## 40. Phase-Number Bookkeeping

Tab 5 uses 76–108. Tab 6 uses 80–110 with a different ordering. Tab 9 §30 lists 10 immediate steps without phase numbers. The stage *order* is consistent across all tabs; the *numbers* are not. Treat phase numbers as a working register, not a permanent identifier. The stage gates in §22 are what matter.

## 41. Composition Complexity Risk

The 15-step composition standard is correct in spec but is a recipe for very long-tail latency if implemented literally for every request. Practical implementation needs to:

- cache common composition results keyed by `(intent_signature, world_state_hash, domain)`
- skip steps where evidence is already in working memory
- short-circuit for high-confidence templated tasks
- still write the full trace as if every step ran

This is not in the doc and should be locked before Phase 85 ships.

## 42. The Two-Loop Problem

The doc warns about adopting Layer 2 agent runtimes wholesale (would create two competing loops). It does *not* explicitly warn about the analogous risk inside the codebase: if Claude Code (or any LLM-driven agent harness) starts owning multi-step decision sequences that should belong to the Composition Engine, the same two-loop failure mode happens internally. Recommendation: Claude Code must be modeled as a **worker/runtime** behind a `claude_code` adapter, not as a peer planner. Its multi-step capability is wrapped, not embraced.

## 43. Memory Promotion Policy Is Underspecified

The doc names the flow: `Trace → Outcome → Learning Proposal → Memory Candidate → Review/Promotion → Memory`. It does not specify:

- the *criteria* for memory candidate selection
- the *review process* (automated heuristic vs. founder approval vs. council deliberation)
- *demotion* rules (when does memory expire or get downgraded?)
- *conflict resolution* when new evidence contradicts existing canonical memory

These need a Memory Governance Policy doc before Phase 81 ships.

## 44. The Substrate / Platform Boundary Is Stated But Not Enforced

Tab 12 §4 says platforms must not own intelligence. Tab 13 §5 reinforces. But the current EntrepreneurOS build on `feature/company-system` is not yet plumbed through a UMH spine — it has its own auth, its own gateway, its own routing. The substrate/platform boundary is currently a *plan*, not an *enforced architecture*. Migrating EOS onto UMH-as-substrate is the largest single piece of architectural work implied by this spec and is not on any phase list.

## 45. The "Operator Helmet" and Form Factors

The leverage skill mentions the Operator Helmet (a personal artifact, not a commercial product). The doc doesn't engage with form factors in much depth. This is fine — it's a long-horizon hardware question — but should be flagged as `SPECULATIVE` and not allowed to influence near-term spec choices.

-----

# PART XIII — FINAL LOCKED DEFINITION & BUILD PRINCIPLE

## 46. Final Locked Definition `CANONICAL`

UMH is a:

> **Governed, stateful, reality-modeling intelligence operating system that externalizes cognition, converts signals into structured primitives, maintains source-attributed user/world/system state, composes complete executable systems from registries, libraries, templates, capabilities, and policies, verifies mastery, governs all action through a control plane, routes execution through a single spine across explicit environments, connects to external reality through adapter boundaries, validates proof, learns from outcomes, self-regulates over time, and compounds human capability across devices, tools, models, systems, people, and environments.**

Compressed:

> **UMH is the governed control plane for externalized cognition, mastered action, cross-environment execution, and recursive human capability compounding.**

## 47. The Compression Every Build Decision Must Obey

`CANONICAL` Tab 9 §31.

```
Adapters connect and translate.
Capabilities define what can be done.
Actions define intended state transformations.
Governance authorizes.
Execution performs.
Workers run.
Environments host.
Actuators affect.
Proof validates.
Trace records.
Learning improves.
Memory preserves.
The Control Plane coordinates everything.
```

## 48. End-State Completion Criteria

UMH is complete when it can:

install on a device · create/load a user instance · initialize workstation · perceive multimodal signals · decompose inputs into primitives · maintain world/user/environment/system models · retrieve memory · select templates/capabilities/adapters/environments · compose complete executable systems · verify mastery · govern execution · route work across environments · execute through workers/runtimes · interact externally through adapter boundaries · observe outcomes · validate proof · trace everything · learn safely · continue across devices and time · self-regulate · integrate frontier AI capabilities · produce proprietary training data · evolve toward proprietary intelligence

-----

## Appendix A — The Civilizational Frame (Tab 11) `SPECULATIVE`

Worth preserving as the long-horizon "why" even though it must not influence near-term architecture decisions. At civilization scale:

> Civilizations scale through increasingly effective orchestration of capability — not through raw intelligence, labor, compute, capital, or resources. Every major civilizational leap (language, writing, currency, legal systems, roads, printing, factories, electricity, computers, internet, cloud, AI) has been fundamentally an orchestration breakthrough.

> What UMH extrapolates toward is persistent governed operational coordination at planetary scale.

> The deepest extrapolation: civilization advances by externalizing and coordinating capability. UMH is an attempt to externalize and govern operational intelligence itself.

This frame is correct as direction but dangerous as near-term build pressure. The leverage doctrine's sequencing rule applies: orchestration → optimization → internalization → ownership → embodiment. Skipping ahead collapses the system. The civilizational frame is the destination, not the next sprint.

-----

## Appendix B — Cross-Reference Index

|Source claim                                                    |Where in this synthesis|Source tab|
|----------------------------------------------------------------|-----------------------|----------|
|Universal harness is orchestration, not execution               |§1, §47                |Tab 10    |
|Hard invariants (7-law version)                                 |§5.1–5.7               |Tab 10    |
|Hard invariants (8-law version)                                 |§5.1–5.8               |Tab 3     |
|Hard invariants (10-law version)                                |§5.1–5.10              |Tab 4     |
|Hard invariants (12-law version)                                |§5.1–5.12              |Tab 9     |
|Protocol Pack                                                   |§25                    |Tab 2     |
|Control plane flow (13-step)                                    |predecessor of §7      |Tab 2     |
|Control plane flow (27-step canonical)                          |§7                     |Tab 9     |
|Canonical lifecycle                                             |§22                    |Tab 4     |
|41-section spec                                                 |distributed Parts II–V |Tab 4     |
|Roadmap stages                                                  |§22                    |Tab 5     |
|Real Core / 10 magnitudes                                       |§1, §46 (compressed)   |Tab 6     |
|Deliberation Council                                            |§16.4                  |Tab 6     |
|Domain Law Registry                                             |§9.5                   |Tab 6     |
|Release path                                                    |Part IX                |Tab 7     |
|EOS-as-wedge                                                    |§18                    |Tab 8     |
|8 moats                                                         |§19                    |Tab 8     |
|PRD v3.0 / 10 macro-layers                                      |Part V                 |Tab 9     |
|Mastery Law                                                     |§5.11                  |Tab 9     |
|External Boundary Law                                           |§5.9                   |Tab 9     |
|Action/Execution Separation                                     |§5.10                  |Tab 9     |
|Terminology lock                                                |Part VI                |Tab 9     |
|W0-001                                                          |§30                    |Tab 9     |
|Phase Approval Guardrail                                        |§33                    |Tab 9     |
|Final Build Principle                                           |§47                    |Tab 9     |
|Civilizational frame                                            |Appendix A             |Tab 11    |
|Canonicalization protocol / status labels                       |§0.3, throughout       |Tab 12    |
|Substrate / Execution Infra / Platform Surfaces / Domain Systems|§17                    |Tab 12    |
|Through-line                                                    |§1, §46                |Tab 12    |
|Synthesis precursor                                             |informed §29, §38–§45  |Tab 13    |

-----

## Appendix C — Audit Corrections Log

### 2026-05-13 — Salience Audit Corrections

Triggered by migration test PROVEN-IN-NAME-ONLY finding.
Full audit: data/audits/2026-05-13_salience_audit.md

- §34: reworded "episodic logging" → "conversation logging"
  (code logs as markdown, not typed EPISODIC entries)
- §35: removed cross-session salience line — verified PROVEN
  (score_cross_session() runs nightly, 150 summaries scored)
- §36: removed nightly consolidation cron line — verified
  PROVEN (cron successful 14 nights, Apr 24 – May 12)
- Architectural note: §24 canonical module tree is
  request-path-centric. Operator tooling / batch / scheduled
  work (scripts/ today, 2,100 LOC of salience pipeline)
  doesn't have a formal §24 layer. This is a real
  architectural gap to address during migration. Salience
  pipeline is one of multiple subsystems that will need a
  home — possibly a new top-level operator_tooling/ or
  batch/, possibly under learning/ or execution/.

### 2026-05-13 — Gap Analysis Reclassifications

Triggered by pre-migration gap analysis.
Full report: data/audits/2026-05-13_gap_analysis.md

Five reclassifications applied:
- §35 → §34: UserPromptSubmit hook capture (verified PROVEN)
- §37 → §34: Full ingestion system (1,000+ LOC, recently built)
- §37 → §34: Multi-Model Routing (1,000+ LOC in production)
- §37 → §35: Composition Engine (partial; not yet canonical 15-step)
- §37 → §35: World Model (partial; not yet full §10.1)

Pattern confirmed: code advances, classification doesn't.
This is the third audit instance of the same failure mode
(after §35 cross-session salience and §36 nightly cron
corrections).

Additional gap analysis findings NOT applied to synthesis
text — documented in the gap analysis report for migration
planning:
- Two-Type-System Problem: 86 Pydantic types in umh/protocols/
  have zero production users; production code grew its own
  @dataclass system. Convergence happens during migration.
- Law 5.5 violations: 46 files doing raw INSERT INTO,
  bypassing the canonical memory path.
- Law 5.9 violations: 5 adapters still use the deprecated
  execute() contract; 0 use translate_request/normalize_result.
- §24 architectural gap: ~52K LOC of operator tooling
  (scripts/) has no formal §24 layer. Salience pipeline is
  one example; likely others.

### 2026-05-14 — Post-Consolidation Reclassifications

Triggered by substrate consolidation arc completion (all substantive
threads closed). Full audit trail: data/audits/2026-05-13_triage_manifest.md

Three promotions to §34 (PROVEN):
- Transport §24 migration: 68 modules at `execution/transport/`, Docker
  cold-start verified, 11 PROD + 45 smoke callers updated
- Law 5.5 memory API adoption: 54 raw-SQL sites → canonical stores
  (3 tiers, net −286 LOC, zero new abstractions)
- Cron operational reliability: 22 scripts verified, 2 fixed, crontab
  corrected (broken paths exposed by audit)

One addition to §35 (PARTIAL):
- Law 5.9 adapter contract: 2 adapters refactored, 4 classified as
  INTERNAL_WORKER (not subject to adapter contract per audit-before-
  refactor principle P2)

Pattern confirmed (4th instance): code advances, classification doesn't.
Status sections require periodic reconciliation with implementation
reality.

### 2026-05-14 — Consolidation Principles

Ten engineering principles discovered during the substrate consolidation
arc (Phase A through Transport §24 migration). Each emerged from a
specific failure or optimization and applies to all future migration,
refactoring, and infrastructure work.

#### P1. Env-var-based roots over \_\_file\_\_-relative paths

Modules using `os.path.dirname(__file__)` to locate sibling files (e.g.,
`.env`) silently break when relocated. Use an env-var anchor (`UMH_ROOT`,
`_REPO_ROOT`) with a sensible `os.getenv(..., '/opt/OS')` default.

*Discovered:* Phase B `context.py` migration + Cron audit
(`nightly_maintenance.sh` hard-coded `/opt/OS/runtime/.env`).
*Why it matters:* Every future §24 migration moves files. Path-relative
code creates invisible breakage at every move.

#### P2. Audit-before-refactor as a hard safety gate

When a refactor scope assumes "N items need X treatment," classify each
item first. The classification frequently surfaces in-scope vs
out-of-scope distinctions that would cause misapplication if skipped.

*Discovered:* Law 5.4 reframe (spine infrastructure types ≠ canonical
protocol types → NO_EQUIVALENT classification) + Law 5.9 ADAPTER vs
INTERNAL_WORKER classification (4 of 6 files were workers, not adapters).
*Why it matters:* Prevents wasted refactoring effort and incorrect
abstraction application.

#### P3. AST-based transitive closure for archive boundary determination

Direct caller analysis (grep on imports) misses dependencies hidden in
`__init__.py` registrations and import-time side effects. Use AST to
compute transitive closure before declaring modules archive-safe.

*Discovered:* Transport orphan archive — caught 53 hidden dependencies
via transitive closure, saving 15 PROD modules from silent breakage.
*Why it matters:* A single missed transitive dependency can break
production after what appeared to be a safe archive operation.

#### P4. Dead-code amplification

Dead code holds dependency edges. Archive dead code FIRST, then re-check
what gates clear automatically. This avoids editing files that are about
to be deleted.

*Discovered:* Cleanup sweep — 15 dead-code archives unblocked the Phase B
`context.py` shim deletion (Thread 5: 7 of its last callers were
dead-code modules).
*Why it matters:* Ordering archive-before-refactor reduces total work and
eliminates throwaway edits.

#### P5. Suppress-and-skip patterns hide regressions

Shell patterns like `|| exit 0` combined with `2>/dev/null` silently mask
failures. A nightly cron job had been silently failing for the entire
post-migration period because the script it called was moved but the
error was swallowed.

*Discovered:* Cron migration audit (`nightly_maintenance.sh` silently
failing; `11pm_email_reviewer` referencing a moved module).
*Why it matters:* Silent failures compound. Audit shell wrappers for
stderr-swallowed exits during any migration.

#### P6. Adoption over creation as highest-ROI principle

When a canonical API already exists, the highest-ROI migration work is
wiring it into the call sites that grew their own duplicates. Tier 1
Law 5.5 closed 46 raw-SQL sites with zero new abstractions, net −286
lines of code.

*Discovered:* Phase A Tier 1 (Law 5.5 memory API adoption).
*Why it matters:* Resist the urge to build new abstractions when the
existing canonical path just needs callers redirected to it.

#### P7. Atomic Postgres patterns beat read-modify-write

`SELECT → mutate-in-Python → UPDATE` is a code smell. Postgres native
operators (`||` for JSONB merge, `ON CONFLICT` for upsert) eliminate
both round-trips and race conditions.

*Discovered:* Phase A Tier 2 (`merge_event_payload` JSONB merge) and
Tier 3 (`knowledge_domains.py` + `research_engine.py` race condition
fixes via `ON CONFLICT`).
*Why it matters:* Every read-modify-write is a latent race condition
under concurrent access.

#### P8. Per-X commits yield to independent-validity

"One commit per store/module" is a default heuristic, not a constraint.
When two stores serve a single caller, combining their commit is correct
because separate commits leave broken intermediate states.

*Discovered:* Phase A Tier 3 (`PermissionStore` + `ProfileStore`
co-committed because `os_trinity.py` called both; splitting would
leave one adopted and one raw-SQL in between commits).
*Why it matters:* The real constraint is "every commit compiles and
passes tests," not "every commit touches exactly one file."

#### P9. Scripts over inline Python in crontab entries

Inline Python one-liners in crontab silently break when their referenced
modules change. Cron entries should reference scripts that can be tested
in isolation and that surface import errors at invocation time.

*Discovered:* Cron migration (11pm email reviewer one-liner referencing
a renamed module — failure swallowed by shell redirect).
*Why it matters:* Testable scripts expose breakage; inline one-liners
bury it in cron's stderr blackhole.

#### P10. Container rebuild simulation vs stale pycache reliance

Running production processes can hold `.pyc` files in memory for modules
whose `.py` source has been deleted. A container rebuild regenerates
pycache from source and exposes the breakage. ALWAYS clear `__pycache__`
and do a fresh-import of production entry points after any migration
affecting production code.

*Discovered:* Transport §24 migration — `discord_bot.py` passed import
checks but Docker restart revealed the pre-existing
`control_plane/runtime/` namespace collision that stale pycache had
been masking.
*Why it matters:* Migration correctness requires testing from cold
state, not warm cache.

-----

*End of canonical synthesis.*
