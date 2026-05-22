---
type: synthesis
created: 2026-05-21
sources:
  - "data/drive_doc_ingestion_tab_aware/UMH_11p36P6T.json"
  - "ARCHITECTURE.md"
  - "PHILOSOPHY.md"
---

# UMH Unified System Synthesis

Synthesized from the 8-tab UMH Google Drive canonical document
(file `11p36P6TMvTnnz2KdQ2wYd3cDKfjHtCvVKp2_XEkuvz8`, 13,949 words)
cross-referenced with ARCHITECTURE.md and the live codebase as of 2026-05-21.

---

## 1. What UMH Is

A self-recursive, governed, leverage-maximizing intelligence operating system
that models reality, models the user, models itself, and continuously compounds
human capability through the highest-leverage use of tools, resources, models,
systems, people, environments, and feedback.

UMH is **not** an AI agent system. It is the substrate that *harnesses*
agents, models, tools, adapters, and environments under a single
[[execution-spine]], governed by a single [[control-plane]].

The human is limited by time, attention, energy, knowledge, execution
bottlenecks, and working memory. UMH compensates for those limits by
providing externalized cognition, memory, execution, and recursive
improvement.

---

## 2. Foundational Thesis

> Reality can be decomposed into primitives, governed by laws,
> modeled as state, and transformed through action.

### 2.1 Ontology Primitives (10)

| Primitive | Role |
|-----------|------|
| State | Current snapshot of any entity |
| Change | Delta between states |
| Constraint | Boundary on what is possible |
| Resource | Input consumed by action |
| Time | Temporal ordering and dependency |
| Signal | Incoming information from any source |
| Feedback | Outcome observation fed back into the system |
| Goal | Desired future state |
| Action | Transformation applied to state |
| Outcome | Result of action meeting reality |

### 2.2 Governing Laws (11)

Causality, feedback, compounding, entropy, emergence, equilibrium,
constraints, resource scarcity, tradeoffs, temporal dependency, leverage.

These laws are domain-agnostic. Domain-specific instantiations
(business laws, software laws, human performance laws) live in a
future **Domain Law Registry** (Phase 91).

---

## 3. Canonical Architecture (6 Tiers)

From the locked end-state spec (Tab 4, v2.0):

### Tier 0 — Ontology + Primitives
Primitives, laws, relationships, validity matrix.
Everything in UMH decomposes to these.

### Tier 1 — Control Plane
The nervous system. **Nothing executes without passing through it.**
Single authority over: identity, context, governance, memory,
registry, composition, execution routing, trace, feedback, learning.

Hard invariant: the control plane is the *only* path to execution.
No adapter, agent, or interface may bypass it.

### Tier 2 — Execution Spine
Single governed execution pathway:
signal → primitive interpretation → world/user/system model →
memory recall → leverage selection → composition → governance →
tool/model/environment routing → execution → trace → feedback →
recursive improvement.

Every execution produces: a trace, an outcome, a feedback record,
a memory candidate, and capability/adapter reliability data.

### Tier 3 — Adapter Layer
Connections to external systems. Adapters are interchangeable and
governed. Categories:
- API adapters (structured, precise)
- Computer-use adapters (universal digital hands/eyes)
- Model adapters (cognitive capability)
- Human adapters (biological/social capability)
- Filesystem, browser, OS, device adapters
- MCP servers, workflow engines

Doctrine: **leverage-first**, not API-first or computer-use-first.
The system chooses the best interface based on cost, latency, precision,
risk, reliability, availability, reversibility, observability,
governance requirement, task type, and long-term compounding value.

### Tier 4 — World Model
Three sub-models:
- **User model** — cognition, preferences, constraints, goals, energy,
  attention, patterns, identity
- **System model** — UMH's own state, capabilities, reliability,
  adapter health, resource budgets
- **Environment model** — external reality: businesses, markets,
  relationships, tools, physical/digital state

State representation + lawful state-transition logic.
Enables simulation: current state + possible action + constraints +
domain laws + uncertainty → projected future state.

### Tier 5 — Intelligence Layer
- Deliberation Council (model-agnostic multi-perspective reasoning)
- Causal Attribution
- Simulation Interface
- Predictive Planning
- Multi-Step Planning
- Self-Recursion Engine

The Deliberation Council is the executive function: strategist, skeptic,
completeness auditor, risk auditor, domain specialist, implementation
engineer, synthesis judge. Advisory only — cannot execute or bypass governance.

---

## 4. The 24 Subsystems

From Tab 1 (system definition) with protocol contracts from Tab 2:

| # | Subsystem | Protocol Contract |
|---|-----------|-------------------|
| 1 | Identity | Resolve identity context for every execution |
| 2 | Context | Load and maintain execution context |
| 3 | Memory | Store, retrieve, and rank memories by relevance |
| 4 | Governance | Classify risk, enforce approval, block violations |
| 5 | Execution Spine | Route every action through single governed path |
| 6 | Trace | Record every action with provenance |
| 7 | Feedback | Capture outcome observation per execution |
| 8 | Learning | Propose improvements from feedback patterns |
| 9 | Registry | Register and discover all components |
| 10 | Template | Provide instantiable reusable structure |
| 11 | Library | Store and retrieve reusable knowledge/patterns |
| 12 | Composition | Assemble executable systems from components |
| 13 | Completeness | Validate all required elements are present |
| 14 | Quality | Score output against benchmarks |
| 15 | World Model | Maintain current state of user/system/environment |
| 16 | Simulation | Project future states before execution |
| 17 | Ontology | Decompose reality into typed primitives |
| 18 | Law Kernel | Apply domain laws to state transitions |
| 19 | Adapter | Connect to external systems under governance |
| 20 | Storage | Persist data with discipline and retention rules |
| 21 | Workstation | Manage session continuity and user presence |
| 22 | Self-Recursion | Apply UMH's own loop to itself |
| 23 | Resource Allocation | Budget compute, attention, model calls |
| 24 | Homeostasis | Detect instability, self-regulate |

---

## 5. Hard Invariants

From Tab 1 (locked):

1. **Control Plane Exclusivity** — every execution routes through governance
2. **Single Execution Spine** — no parallel ungoverned paths
3. **Governance Before Execution** — risk classification before any action
4. **Trace Everything** — every execution produces an auditable trace
5. **Memory Discipline** — structured storage with authority tiers, no hallucinated facts
6. **Registry as Truth** — if it's not registered, it doesn't exist to the system
7. **Template Over Rebuild** — never reconstruct what can be composed from structure
8. **Feedback Closes Loops** — every outcome feeds back into learning
9. **Self-Recursion is Bounded** — detect → propose → simulate → sandbox → test → compare → approve → deploy → trace → monitor

---

## 6. Template & Composition System

Templates are not prompts. A template is:
- Immutable primitives (input, processing, output, feedback,
  constraint check, failure handler, quality benchmark,
  governance gate, trace event, memory update)
- Customizable slots (goal, domain, tools, environment,
  constraints, timeline, budget, risk tolerance, output format,
  success metric, approval level)
- Validation rules, feedback loops, governance requirements

Composition pipeline:
intent binding → world-state grounding → memory recall →
domain mapping → registry lookup → library retrieval →
template selection → slot filling → capability selection →
adapter/environment matching → constraint binding →
completeness validation → quality validation →
governance classification → execution plan generation.

---

## 7. The Human Model

UMH mirrors human cognitive architecture in software:

| Human | UMH Equivalent |
|-------|----------------|
| Cognition | Reasoning / world model |
| Memory | Memory system |
| Nervous system | Control plane |
| Hands/fingers | Adapters / computer-use / API |
| Senses | Perception layer |
| Habits | Workflows / templates |
| Learning | Feedback loops |
| Executive control | Governance |
| Self-reflection | Self-recursion |

---

## 8. Leverage Doctrine

Leverage is a core law, not a productivity tip.
A leverage point is where small input produces disproportionately large output.

UMH continuously searches for leverage across: human, code, content,
capital, systems, templates, AI/models, network, attention, data,
memory, distribution, environment.

The system asks: what should the human do personally? What should be
automated? Delegated? Templated? Routed to a model? Routed to a
specialist? Routed to a workflow? Ignored? Delayed? Simulated first?
Turned into a reusable asset?

The user becomes the orchestrator of capability.
UMH becomes the leverage system.

---

## 9. Magnitude Scale (Product Arc)

| Magnitude | Description |
|-----------|-------------|
| 1 | Personal AI harness — governed adapter execution |
| 2 | Persistent workstation / Jarvis — session continuity, context |
| 3 | Leverage engine — identifies highest-leverage path |
| 4 | System composer — builds workflows, businesses, systems from templates |
| 5 | World model runtime — models all domains of reality |
| 6 | Simulation & strategy engine — tests actions before execution |
| 7 | Organism runtime — self-regulating with internal signaling |
| 8 | Self-recursive AI OS — improves its own architecture |
| 9 | Proprietary intelligence platform — traces become training data |
| 10 | Human capability infrastructure — democratized leverage |

---

## 10. Roadmap (108 Phases, 8 Stages)

### Stage 1 — MVP Foundation (Phases 76-78)
Adapter pack, workstation state, trace→outcome→memory loop.

### Stage 2 — Operational Harness (Phases 79-82)
Observability, registry unification, storage discipline, legacy deprecation.

### Stage 3 — Composition Core (Phases 83-87)
Template system, library system, composition engine,
completeness engine, quality engine.

### Stage 4 — World Model (Phases 88-91)
World model core, user+environment model, update loop, temporal model.

### Stage 5 — Intelligence Maturity (Phases 92-95)
Causal attribution, simulation, predictive planning, multi-step planning.

### Stage 6 — Organism Runtime (Phases 96-100)
Workstation modes, presence system, internal signaling,
resource allocation, homeostasis.

### Stage 7 — Frontier AI OS (Phases 101-105)
Model registry, external agent harnessing, embodied perception,
world model simulation, proprietary intelligence path.

### Stage 8 — Distribution (Phases 106-108)
Installer/updater, onboarding/first boot, security hardening.

### Final End-State Gate
UMH reaches the locked end state when it can:
install on a new device, create/load a user instance, initialize workstation,
perceive multimodal signals, decompose into primitives, update world models,
retrieve memory, select templates/libraries/registries/capabilities,
compose executable systems, validate completeness and quality,
govern every action, execute through adapters, observe outcomes,
trace everything, learn safely, self-regulate, continue across devices,
harness external frontier systems, produce proprietary training data,
evolve toward proprietary intelligence.

---

## 11. Release Strategy

Authority-gated, not time-gated:

| Stage | Duration | Scope |
|-------|----------|-------|
| Founder dogfooding | 2-4 weeks | Full internal use, no public |
| Trusted alpha | 4-8 weeks | 3-10 users, read-only + safe local |
| Private beta | 8-12 weeks | 10-30 users, controlled execution |
| Public beta | 3-6 months | Narrow product, approval-required |
| Full launch | 6-12 months | Stable spine, docs, support, pricing |

First public release: **UMH Operator Console / AI Command Center Beta**
— governed execution, traces, memory, registry, approval-based actions.

Hold back: full autonomous execution, self-modification, open computer-use,
financial actions, destructive operations.

---

## 12. Strategic Context

### The Three-Layer Stack
1. **UMH** = intelligence and execution substrate
2. **EntrepreneurOS** = first monetizable operating product
3. **Munoz Holdings** = portfolio/capital/infrastructure compounding vehicle

### The Flywheel
Build/acquire business → install EntrepreneurOS/UMH → capture data →
improve workflows → increase margin/revenue → convert improvements
into templates → add to libraries → improve UMH → make next business
easier to optimize → increase portfolio cash flow → fund infrastructure.

### Eight Moat Layers
1. Software (UMH/EOS architecture)
2. Data (operational traces across real companies)
3. Workflow (proprietary templates/playbooks)
4. Distribution (personal brand + CreatorOS)
5. Network (operators, creators, vendors, investors)
6. Infrastructure (fulfillment, manufacturing, real estate)
7. Capital (cash flow from portfolio)
8. Trust (governance, auditability, safety)

### Ecosystem
- EntrepreneurOS for business execution
- CreatorOS for distribution
- LyfeOS for human performance
- Lyfe Institute for education/coaching
- Empyrean Studio for creative production
- Lyfe Spectrum for culture/physical brand
- UMH powers all of them

---

## 13. Current Codebase State vs. Spec

### Built and Operational
- [[execution-spine]] — `runtime/cognitive_loop.py` (8-stage loop)
- Governance — `runtime/authority_engine.py` (4 risk classes)
- Memory — `runtime/memory.py` (AgentMemory + ConversationMemory, Neon)
- Model routing — `runtime/model_router.py` (multi-model, vision-capable)
- Ingestion pipeline — `runtime/ingestion/` (perceive→interpret→decompose→bridge→map→persist→query_back)
- Ontology primitives — `runtime/primitives.py` (10 primitives)
- Authority tiers — `runtime/ingestion/authority_tier.py` (T1-T9)
- Domain bridge — `runtime/domain_bridge/business.py` (business domain V1)
- Transport — `services/discord_bot.py` (primary), `services/operator_api.py` (cockpit)
- Cockpit — `apps/cockpit/` (React, voice + vision)
- Session state — `runtime/session_state.py`
- Work state / pressure — `runtime/work_state.py`

### Partially Built
- Orchestration — `control_plane/orchestrator/` (scheduler, events, queues)
- Registry — multiple registries exist but not unified
- Trace — exists within cognitive loop, not standalone subsystem
- Template system — skills serve as proto-templates, no formal Template subsystem
- Composition — manual, no formal Composition Engine

### Not Yet Built (per spec)
- Deliberation Council
- Leverage / Resource / Tool Taxonomy
- Formal Template System (immutable primitives + customizable slots)
- Library System
- Composition Engine
- Completeness Engine
- Quality Engine
- Domain Law Registry
- World Model (user, system, environment sub-models)
- Simulation Interface
- Causal Attribution
- Predictive / Multi-Step Planning
- Workstation Modes / Presence System
- Internal Signaling (organism runtime)
- Resource / Attention Allocation
- Homeostasis / Self-Regulation
- Self-Recursion Engine
- Distribution / Installer / Onboarding
- Security Hardening

### Execution Rule
Before every phase: Does it strengthen the canonical system? Preserve the
spine? Avoid redundancy? Map to the locked spec? Move MVP or end-state
forward? If yes, build. If no, reject.

---

## 14. The Compounding Principle

Every useful execution should produce more than an output.
It should produce assets: trace, outcome, feedback record, memory candidate,
capability score, adapter reliability data, template performance data,
workflow pattern, user preference, domain insight, reusable process,
reduced future friction.

The system compounds because it converts work into structure.
The user compounds because the system converts intent into reusable leverage.

This is the difference between UMH and every other AI system:
most systems are `model → tool → result`.
UMH is `signal → interpretation → model → memory → leverage → composition →
governance → routing → execution → trace → feedback → recursive improvement`.

That is a different category.
