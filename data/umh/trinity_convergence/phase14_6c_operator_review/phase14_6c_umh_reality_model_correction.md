---
phase: "14.6C"
status: "DRAFT"
operator_approved: false
allows_implementation: false
date: "2026-06-04"
provenance: "OPERATOR_CORRECTION"
---

# Phase 14.6C: UMH Reality Model Correction -- P0 Operator Clarification

This document captures and formalizes a P0 operator correction to the UMH
product identity, architecture framing, and Stage 1 scope definition.

**This is an OPERATOR CLARIFICATION, not silently approved canon.**
Nothing in this document authorizes implementation. It captures the
operator's words, traces their impact across existing artifacts, and
presents ratification decisions for explicit operator approval.

---

## Classification

- **Type:** OPERATOR_CLARIFICATION
- **Priority:** P0 (gates all implementation)
- **Source:** Operator directive, 2026-06-04
- **Status:** Captured as DRAFT. NOT silently ratified. Requires explicit operator review and ratification.
- **Blocks:** All Cockpit implementation, all UMH reality-engine phases, all Stage 1 organism definitions

---

## The Correction

### 1. Current Canon State (14.6B-UMH)

The 14.6B UMH canon -- across 22 artifacts in `data/umh/trinity_convergence/phase14_6b_umh/` --
describes UMH using these identities:

| Artifact | Exact Language Used |
|----------|-------------------|
| `umh_lossless_product_canon.md` (line 8) | "private universal intelligence substrate, orchestration kernel, governed execution control plane, and operator/Jarvis system" |
| `umh_projection_ecosystem_doctrine.md` (line 11) | "private universal intelligence substrate, orchestration kernel, governed execution control plane, and operator/Jarvis system that powers, integrates with, and coordinates the Trinity ecosystem" |
| `umh_full_end_state_canon.md` (line 8) | "a private Jarvis system -- a fully autonomous intelligence substrate that governs the founder's entire operational surface" |
| `umh_cockpit_jarvis_doctrine.md` (line 12) | "the private operator/Jarvis interface into UMH" |
| `umh_code_resolved_substrate_canon.md` (line 8) | "`substrate/` is the innermost UMH layer" (architectural framing, no identity statement) |
| `umh_workstation_jarvis_experience_canon.md` (line 9) | "a universal intelligence substrate that the operator can command across all domains, devices, and contexts" |
| `umh_naming_canonicalization.md` (line 11) | "Universal Meta Harness" (naming only, no identity definition) |

**Summary of current framing:**
UMH is described as an **operational tooling system** -- infrastructure that routes
signals, governs execution, coordinates projections, and provides a Jarvis-like
operator interface. The language is consistently about **orchestration**, **governance**,
**execution**, and **substrate infrastructure**. The world model subsystem
(`umh_world_model_memory_architecture.md`) is described in operational terms:
"Maintains the system's understanding of external reality. Represents entities,
relationships, and state as perceived through signals." This frames the world model
as a software feature of the execution system, not as the core identity of UMH itself.

---

### 2. Operator's Intended State

**Verbatim operator directive (2026-06-04):**

> The UMH reality model is intended to approximate reality as closely and
> isomorphically as possible. It is not merely an operational tooling model
> or business/software model. It must ultimately model physical, digital,
> cognitive, biological, social, economic, symbolic, operational, software,
> memory, source-truth, and OS-level reality as corresponding layers of
> one reality model.

**What this means:**

UMH is not an orchestration kernel that happens to have a world model.
UMH is a **reality-approximation engine** -- a system whose core purpose is
to build and maintain an isomorphic model of reality across all domains,
and whose orchestration, governance, and execution capabilities exist
*in service of* keeping that reality model accurate and actionable.

The relationship is inverted from the current canon:

| Current Canon | Operator's Intent |
|--------------|-------------------|
| UMH = orchestration system that has a world model | UMH = reality model that has orchestration capabilities |
| World model is a subsystem of the execution engine | Execution engine is a subsystem that acts on the reality model |
| Cockpit displays operational state | Cockpit renders and navigates reality layers |
| Signals are inputs to the governance pipeline | Signals are reality-model observations from the world |
| Memory stores interaction history | Memory is one layer of the reality model (what was known, when, confidence, decay) |
| Governance gates execution risk | Governance protects the integrity of the reality model |

---

### 3. Reality Layers (Operator-Specified)

The operator explicitly named 12 reality layers that UMH must ultimately model
as "corresponding layers of one reality model":

| # | Layer | What It Models | Current Canon Coverage |
|---|-------|---------------|----------------------|
| 1 | **Physical** | Locations, objects, environments, hardware, devices | Partial: device graph in `umh_workstation_jarvis_experience_canon.md` covers hardware nodes; no physical-world modeling beyond infrastructure |
| 2 | **Digital** | Files, data, APIs, services, state, code, deployments | Strong: substrate code extensively tracks digital reality (codebase graph, API endpoints, service state) |
| 3 | **Cognitive** | Knowledge, beliefs, mental models, decisions, reasoning | Partial: memory subsystem stores facts/beliefs/decisions; no explicit cognitive-state modeling |
| 4 | **Biological** | Health, energy, circadian rhythm, physical state | None: no biological-reality modeling in any 14.6B artifact |
| 5 | **Social** | Relationships, networks, reputation, influence, community | Minimal: CRM/contact data in EOS projection; no social-graph modeling at substrate level |
| 6 | **Economic** | Capital, transactions, assets, liabilities, markets, revenue | Partial: EOS projection handles business transactions; organism has "execution economics"; no comprehensive economic-reality model |
| 7 | **Symbolic** | Brands, meaning, narrative, identity, culture, aesthetics | Minimal: brand identity exists in docs/brand-identity.md; not modeled as a reality layer |
| 8 | **Operational** | Tasks, workflows, processes, systems, cadence | Strong: execution spine, work packets, governance lifecycle, autonomous cadence -- this is what the current canon focuses on |
| 9 | **Software** | Codebase state, architecture, dependencies, deployments | Strong: codebase graph, dependency direction, pre-commit gates, type coherence |
| 10 | **Memory** | What was known, when, confidence level, decay over time | Partial: ConversationMemory and AgentMemory exist; MemoryType enum covers fact/belief/decision/observation; no explicit temporal-confidence-decay modeling |
| 11 | **Source-truth** | Which documents/sources are authoritative, provenance chains | Partial: source truth vs production truth distinction exists in governance lifecycle; no comprehensive source-truth registry |
| 12 | **OS-level** | The meta-layer governing all other layers -- UMH itself as a self-aware system | Partial: organism self-build routes exist; self_model.py exists; no explicit meta-reality-layer framing |

**Key observation:** The current canon covers layers 2, 8, and 9 (digital,
operational, software) in depth. Layers 1, 3, 4, 5, 6, 7 are absent or
minimal. Layers 10, 11, 12 have partial implementations but are framed
as subsystem features rather than reality layers.

---

### 4. Instance Reality Models

**Verbatim operator directive (2026-06-04):**

> The instance reality model carries the same isomorphic ambition, but from
> the perspective/context of a specific instantiated user, company, product,
> environment, or incarnation.

**What this means:**

The universal reality model defines the structure (all 12 layers, their
relationships, their ontology). An instance reality model is a specific
instantiation -- one user's, one company's, one product's view of reality
through that same 12-layer structure.

| Instance Type | What It Contains | Example |
|--------------|-----------------|---------|
| **User instance** | One person's reality across all 12 layers | Antony's physical location, digital accounts, cognitive state, biological rhythms, social network, economic position, brand identity, operational tasks, software projects, accumulated memory, trusted sources, and meta-awareness |
| **Company instance** | One company's reality across applicable layers | Lyfe Institute's digital presence, social reach, economic state (revenue, expenses, runway), brand positioning, operational workflows, software products, institutional memory |
| **Product instance** | One product's reality across applicable layers | Initiate Arena's digital architecture, user base (social), revenue metrics (economic), brand perception (symbolic), feature backlog (operational), codebase state (software) |
| **Environment instance** | One deployment's reality across applicable layers | VPS node's physical hardware, digital services, operational health, software state, memory of past incidents |

**Relationship to existing Instance Context Law:**

The Instance Context Law (`scripts/check_instance_leak.py`) already enforces
that substrate code must not contain instance-specific values. The instance
reality model extends this principle: the *structure* of reality modeling is
universal (substrate), but the *content* is always instance-specific (loaded
at runtime from BIS, env vars, or persistent storage).

---

### 5. The Indivisible Stage 1 Organism

**Verbatim operator directive (2026-06-04):**

> Stage 1 must not be split into separate sequential stages of harness,
> Cockpit, and reality model. Stage 1 is one minimum viable UMH organism:
> Reality Model + Cockpit + Memory + Governed Execution Loop.
>
> The harness cannot function as intended without the reality model and
> Cockpit. Cockpit without a reality model is only a dashboard. A reality
> model without Cockpit is inaccessible to the operator.

**Why the current sequential framing is wrong:**

The 14.6B artifacts implicitly assume a build sequence:

1. Build the substrate (execution engine, governance, memory) -- *done*
2. Build the cockpit (panels, voice, command palette) -- *partially done*
3. Build the world model (reality understanding) -- *future phase*

The operator's correction states these are not sequential. They are
**one indivisible organism** that must reach minimum viability simultaneously.

| Component | Alone | With Reality Model + Cockpit |
|-----------|-------|------------------------------|
| **Harness (substrate)** | Routes signals without understanding what they mean. Executes tasks without modeling the reality they affect. Governs actions without knowing the full state of reality being acted upon. | Routes signals with reality-layer context. Executes tasks that update the reality model. Governs actions based on reality-state awareness. |
| **Cockpit** | Displays operational metrics and execution traces. A dashboard. Shows what happened, not what reality looks like. | Renders reality layers. Operator navigates physical, digital, cognitive, economic reality. Not a dashboard -- a reality interface. |
| **Reality Model** | Accumulates observations with no way for the operator to see, navigate, correct, or direct them. An invisible internal model. | Visible through Cockpit. Correctable by operator. Feeds execution decisions. Receives execution results. A living, observable model. |
| **Memory** | Stores interaction history as flat records. | One layer of the reality model -- tracks what was known, when, at what confidence, with what decay. Memory IS reality layer 10. |

**Minimum Viable Organism (Stage 1):**

All four components must reach minimum viability together. The acceptance
criteria for Stage 1 are:

1. Reality Model can represent at least 3-4 reality layers with real data
2. Cockpit can render those reality layers and allow operator navigation
3. Memory functions as a reality layer (temporal, confidence-weighted)
4. Governed Execution Loop can act on reality model state and update it
5. Signals entering UMH update the reality model, not just trigger execution
6. Operator can observe reality state through Cockpit, not just execution state

---

### 6. The Materialization Principle

**Verbatim operator directive (2026-06-04):**

> Materialization Principle: If a human can imagine an outcome, UMH should
> attempt to simulate the path from imagination to materialization. Lack of
> current knowledge, resources, tools, capital, or information does not
> invalidate the intent; it creates acquisition loops, research loops,
> experiment loops, work packets, and time-bound execution paths.

**What this means for UMH architecture:**

The current execution model treats "blockers" as terminal states. An agent
encounters a missing resource, capability, or piece of information, and the
task either fails or gets deferred with a static note.

Under the Materialization Principle, there are no blockers -- only **gaps
in the reality model** that create **typed execution paths**:

| Gap Type | Current Behavior | Materialization Behavior |
|----------|-----------------|------------------------|
| Missing knowledge | Task fails or defers | Creates a **research loop**: web search, document ingestion, expert query, experiment design |
| Missing resource | Task blocks | Creates a **resource acquisition path**: identify resource, find source, create procurement work packet |
| Missing tool | Task cannot execute | Creates a **tool acquisition path**: research tool, evaluate options, install/configure, verify |
| Missing capital | Task is out of scope | Creates a **funding path**: estimate cost, identify funding sources, create financial plan work packet |
| Missing information | Agent asks operator | Creates an **information acquisition loop**: identify what's needed, determine best source, create intake work packet |
| Missing time | Task overflows schedule | Creates a **scheduling path**: estimate duration, find time slots, create prioritization decision |
| Missing skill | Task quality is low | Creates a **learning loop**: identify skill gap, find training resources, create practice work packets |

**Integration with execution model:**

The `umh_execution_boundary_model.md` defines three execution paths (Gateway,
Substrate.execute, Organism WorkPackets). Under the Materialization Principle,
all three paths must be able to:

1. Detect when a gap prevents completion
2. Classify the gap type (knowledge, resource, tool, capital, information, time, skill)
3. Generate an appropriate typed execution path (loop or work packet)
4. Track the path in the reality model
5. Resume the original task when the gap is closed

This is not a new execution path -- it is a behavioral extension of all
existing paths.

---

## Affected 14.6B Artifacts (17 Files)

### Directly Affected (Require Content Revision)

Each artifact below is listed with its exact current framing and the specific
correction required. File paths are relative to
`data/umh/trinity_convergence/phase14_6b_umh/`.

---

#### 1. umh_lossless_product_canon.md

**Current framing (line 8):**
"Universal Meta Harness (UMH) is the private universal intelligence substrate,
orchestration kernel, governed execution control plane, and operator/Jarvis system."

**Required correction:**
UMH identity must be reframed as a reality-approximation engine. The substrate,
orchestration, governance, and execution capabilities are *mechanisms that serve*
the reality model, not the identity itself. The product canon must define UMH
as "a private universal reality-approximation engine that builds and maintains
an isomorphic model of reality across physical, digital, cognitive, biological,
social, economic, symbolic, operational, software, memory, source-truth, and
OS-level layers." Orchestration, governance, and execution are capabilities
of the engine, not the engine's identity.

**Severity:** CRITICAL -- this is the root identity document. All other artifacts
derive their framing from this one.

---

#### 2. umh_projection_ecosystem_doctrine.md

**Current framing (line 11):**
"UMH (Universal Meta Harness) is the private universal intelligence substrate,
orchestration kernel, governed execution control plane, and operator/Jarvis
system that powers, integrates with, and coordinates the Trinity ecosystem."

**Required correction:**
Same identity correction as artifact 1. Additionally, the doctrine's description
of what UMH IS (lines 25-29: "The private universal substrate that powers all
projections / The governed execution control plane / The operator/Jarvis system /
The shared capability pipeline owner / The cross-system coordination brain")
must be reframed. Projections are not just "domain-specific views of the substrate"
-- they are domain-specific instantiations of the reality model. EOS is not merely
"a view into UMH" but "an instance reality model for business operations."

**Severity:** HIGH -- governs how all projections relate to UMH.

---

#### 3. umh_full_end_state_canon.md

**Current framing (line 8):**
"UMH at end-state is a private Jarvis system -- a fully autonomous intelligence
substrate that governs the founder's entire operational surface across business,
creative, and personal domains."

**Required correction:**
End state must reflect the isomorphic reality ambition. UMH at end-state is not
merely "governing the operational surface" -- it is maintaining a comprehensive,
continuously-updated model of reality across all 12 layers. The "Autonomous
Operation" section (lines 34-37) describes overnight execution and morning
summaries -- these must be reframed as the execution loop maintaining and
updating the reality model, not just executing operational tasks. The
"Intelligence End-State" section (lines 39-44) must include reality-model
reasoning -- the ability to infer across reality layers, not just route
intelligence calls.

**Severity:** CRITICAL -- defines what UMH is building toward.

---

#### 4. umh_cockpit_jarvis_doctrine.md

**Current framing (line 12):**
"Cockpit IS the private universal control surface that allows Antony (the
operator) to: [19 operational capabilities listed]"

**Required correction:**
The 19 capabilities (lines 23-41) are framed as operational inspection and
control -- observe ecosystem, command UMH, inspect agents, inspect work packets,
approve/deny, pause/resume, route tasks, inspect files, inspect tmux, inspect
infrastructure, inspect projections, inspect model routing, manage workflows,
trigger work, supervise execution, use voice/text, operate across devices, use
as Jarvis. These must be reframed around reality-model interaction: observe
reality state across layers, navigate reality layers, correct reality model
entries, direct reality-model updates, approve reality-affecting actions.
Cockpit is part of the indivisible Stage 1 organism, not a separate component
to be built after the substrate.

**Severity:** CRITICAL -- Cockpit identity is central to Stage 1 definition.

---

#### 5. umh_cockpit_buildable_readiness_detail.md

**Current framing:**
25 readiness criteria organized into Command Layer (1-6), Execution Layer (7-9),
Observability Layer (10-18), and more. All criteria assume a sequential build
where readiness is assessed per-component.

**Required correction:**
Readiness criteria must be reorganized around the indivisible Stage 1 organism.
Instead of "Is the command layer ready? Is the execution layer ready?" the
criteria must be "Can the organism render reality state through Cockpit, accept
operator corrections, execute reality-affecting actions, and update the reality
model?" The voice/text intake criterion (1) is not just "can the operator give
commands" but "can the operator interact with the reality model through natural
language." The work packet visibility criterion (8) is not just "can the operator
see work packets" but "can the operator see how work packets relate to reality-model
gaps and materialization paths."

**Severity:** HIGH -- defines what "ready" means for Stage 1.

---

#### 6. umh_cockpit_readiness_buildable_criteria.md

**Current framing:**
25 criteria with classification (IMPLEMENTED, PARTIALLY_IMPLEMENTED, SCAFFOLD,
DOCS_ONLY, MISSING). Framed as dashboard readiness.

**Required correction:**
Same structural issue as artifact 5. Classifications must account for
reality-model integration. An endpoint that is "IMPLEMENTED" for operational
display may be "PARTIALLY_IMPLEMENTED" or "SCAFFOLD" for reality-layer
rendering. The criteria need an additional dimension: does this criterion
satisfy its role in the indivisible Stage 1 organism, or only its role as
a standalone dashboard feature?

**Severity:** HIGH -- paired with artifact 5, defines readiness.

---

#### 7. umh_cockpit_readiness_gap_matrix.md

**Current framing:**
15 criteria with status (IMPLEMENTED/PARTIAL/STUB/NOT_IMPLEMENTED). Summary:
6 implemented, 7 partial, 1 stub, 1 not implemented. Critical gaps identified
as execution control, degraded mode, voice E2E.

**Required correction:**
The gap matrix must be reframed around reality-model interface requirements.
Current gaps are framed as "execution control is not wired" and "no degraded
mode UI." The deeper gap -- which the matrix does not surface -- is that **none
of the 15 criteria assess whether the Cockpit can render, navigate, or correct
the reality model**. This is not a gap in the existing matrix; it is a missing
dimension. The matrix needs new criteria for reality-layer rendering,
reality-model navigation, reality-model correction by operator, and
materialization-path visibility.

**Severity:** HIGH -- gap analysis drives implementation priorities.

---

#### 8. umh_cockpit_screen_panel_inventory.json

**Current framing:**
27 panels designed for operational display -- dashboard, agents, organism,
execution, infrastructure, knowledge, approvals, analytics.

**Required correction:**
Panels are organized around operational concerns (execution traces, agent state,
approval workflows). Under the reality-model framing, panels should be organized
around reality layers -- or at minimum, each panel should declare which reality
layer(s) it surfaces. The infrastructure panel surfaces physical + digital reality.
The execution panel surfaces operational reality. The analytics panel surfaces
economic reality. The knowledge panel surfaces cognitive + memory reality. This
mapping must be made explicit, and gaps must be identified (no panel covers
biological, social, or symbolic reality layers).

**Severity:** MEDIUM -- panel inventory is an implementation detail, but drives
Cockpit UX architecture.

---

#### 9. umh_world_model_memory_architecture.md

**Current framing (line 59):**
World model "maintains the system's understanding of external reality. Represents
entities, relationships, and state as perceived through signals."

**Required correction:**
This artifact is the closest to the operator's intent but still frames the world
model as a subsystem of the execution engine ("as perceived through signals" --
signals are the input mechanism, not the purpose). The world model must be
reframed as the **core of UMH** -- the reality model that all other subsystems
serve. Memory is not a separate subsystem that coexists with the world model;
memory IS reality layer 10 (what was known, when, at what confidence, with
what decay). The MemoryType enum (FACT, BELIEF, DECISION, OBSERVATION,
COMMITMENT, FEEDBACK, RELATIONSHIP, DOMAIN_PROJECTION) maps naturally to
reality-model concepts but is currently framed as interaction data, not
reality-layer state.

**Severity:** CRITICAL -- this artifact becomes the seed of the reality-model
architecture.

---

#### 10. umh_execution_boundary_model.md

**Current framing:**
Three execution paths (Gateway, Substrate.execute, Organism WorkPackets) with
different governance, memory, and tracing implementations. Framed entirely around
task execution boundaries and safety classifications.

**Required correction:**
Execution boundaries must account for the Materialization Principle. The current
"What CAN execute automatically" section (lines 56-59) classifies by operation
type (READ_ONLY, SAFE_WRITE, REVERSIBLE_WRITE). Under the Materialization
Principle, execution also generates **new execution paths** when gaps are detected.
The boundary model must define governance for gap-generated execution paths:
When a task encounters missing knowledge, who approves the research loop? When
missing capital is detected, what risk class applies to the funding acquisition
path? The unification question (lines 41-52) remains valid but gains a new
dimension: all three paths must be able to detect gaps and generate
materialization paths.

**Severity:** HIGH -- execution model is foundational to how UMH acts on
the reality model.

---

#### 11. umh_governance_approval_lifecycle.md

**Current framing:**
Permission tiers (READ/DRAFT/EXECUTE/COMMIT), risk classes (NEGLIGIBLE through
FORBIDDEN), action risk categories (READ_ONLY through PHYSICAL_WORLD).

**Required correction:**
Governance must cover reality-model mutation. Currently, governance gates
*actions* (sending messages, making payments, deploying code). Under the
reality-model framing, governance must also gate *reality-model updates* --
when the system updates its model of economic reality (e.g., records a
transaction), when it updates social reality (e.g., modifies a relationship
record), when it updates cognitive reality (e.g., promotes a belief to a fact).
Some reality-model mutations are higher risk than others: correcting the
economic layer (capital amounts) is higher risk than updating the digital layer
(file state). The governance lifecycle must define risk classification for
reality-model mutations, not just action execution.

**Severity:** HIGH -- governance integrity is non-negotiable for a system
that models reality.

---

#### 12. umh_code_resolved_substrate_canon.md

**Current framing:**
Detailed code inventory of substrate/ organized by package (types, control plane,
execution, organism). Framed as infrastructure documentation.

**Required correction:**
The substrate canon must acknowledge that the code infrastructure serves a
reality-approximation purpose, not just an orchestration purpose. The organism
package (201 files, 70,126 lines) is described as "implementing the self-organizing
execution economy" -- under the reality-model framing, the organism is also the
self-organizing reality-maintenance system. The world model code (currently in
`substrate/understanding/world_model/`) must be elevated from "a subsystem under
understanding/" to "the core component that all other subsystems serve."

**Severity:** MEDIUM -- code documentation, but shapes how developers understand
the architecture.

---

#### 13. umh_workstation_jarvis_experience_canon.md

**Current framing (line 9):**
"UMH is Antony's private Jarvis-like operator system. It is not merely a developer
tool or a business dashboard -- it is a universal intelligence substrate that the
operator can command across all domains, devices, and contexts."

**Required correction:**
The Jarvis experience must interface the reality model, not just operational state.
Currently the experience modes (Cockpit UI, Discord Voice/Text, CLI, Mobile SSH)
are framed as different ways to access operational capabilities. Under the
reality-model framing, each mode provides a different lens onto the same reality
model: Cockpit provides the richest visual rendering, Discord provides
conversational reality-model interaction, CLI provides programmatic access,
Mobile provides ambient awareness. The device graph (VPS, Beast, iPhone, iPad)
is not just "nodes that run services" -- each device IS a node in the physical
reality layer of the instance reality model.

**Severity:** MEDIUM -- experience design, but shapes operator expectations.

---

#### 14. umh_signal_interpretation_decomposition_canon.md

**Current framing:**
Signals enter via SignalEnvelope, get classified by intent, get decomposed into
PrimitiveObservation objects. Framed as an input processing pipeline.

**Required correction:**
Signal interpretation is the **reality-model input layer**. Signals are not
just "inputs to the governance pipeline" -- they are observations about reality
that update the reality model. Intent classification determines which reality
layer(s) a signal affects. Decomposition extracts reality-model updates from
raw input. The PrimitiveType enum (state/change/constraint/resource/signal/
action/outcome/feedback/goal/time) maps naturally to reality-model update types
but is currently framed as execution-pipeline metadata. Under the reality-model
framing, a "state" primitive is a reality-layer state assertion, a "change"
primitive is a reality-model mutation event, a "constraint" is a reality-layer
boundary condition.

**Severity:** HIGH -- signal processing is how the reality model receives
information from the world.

---

#### 15. umh_private_cockpit_vs_public_projection_boundary.md

**Current framing:**
Hard boundary between private Cockpit and public projections. Cockpit =
"private operator command center." Boundary framed around security and
audience separation.

**Required correction:**
The boundary is not just "private UI vs public UI" -- it is "reality-model
access boundary." The Cockpit provides full access to all 12 reality layers
of all instance reality models. Projections provide access to a
domain-specific subset of reality layers through a domain-specific interface.
EOS users see economic + operational + digital reality for their ventures.
CreatorOS users see social + symbolic + digital reality for their content.
The boundary is about **which reality layers are exposed to which audience**,
not just "which UI is public vs private." This reframing makes the boundary
more principled and easier to govern.

**Severity:** MEDIUM -- boundary model, but fundamentally changes how
projections relate to UMH.

---

#### 16. umh_substrate_cockpit_projection_boundary_matrix.md

**Current framing:**
5-layer boundary matrix (Universal Substrate / Cockpit / Projection Runtime /
Projection Product / Cross-Projection). Framed around architectural layers
and their data/capability/auth boundaries.

**Required correction:**
The 5-layer matrix is incomplete without a reality-model layer. Currently,
"Universal Substrate" is described as "the reusable intelligence/control plane"
-- this must become "the universal reality-model engine." The Cockpit layer is
described as "the private operator control surface" -- this must become "the
full reality-model interface." The projection layers are described as
"domain-specific views" -- these must become "domain-specific reality-model
instantiations." The matrix needs a new column: "Reality Model Scope" -- which
reality layers does each architectural layer manage, render, or expose?

**Severity:** MEDIUM -- boundary architecture, shapes all layer interactions.

---

#### 17. umh_naming_canonicalization.md

**Current framing:**
Canonical name = "Universal Meta Harness." Name resolution matrix maps correct
vs stale names. No "reality model" or "reality engine" in naming vocabulary.

**Required correction:**
The naming canonicalization may need revision once "reality model" becomes a
core concept. Questions for operator ratification:
- Does "Universal Meta Harness" still capture the identity? ("Harness" implies
  tooling; the operator's description is closer to "engine" or "model.")
- Should "reality model" be a formal term in the naming matrix?
- Should "instance reality model" be the canonical term for what projections
  provide, rather than "domain-specific view"?

This is the lowest-severity correction because naming follows identity, and
identity must be ratified first (DEC-146C-001).

**Severity:** LOW -- naming follows identity ratification.

---

### Indirectly Affected Artifacts

These artifacts are not in the 14.6B-UMH set but will need updates if the
reality-model framing is ratified:

| Artifact Set | Why Affected |
|-------------|-------------|
| EOS integration artifacts (`phase14_6b_eos/`) | Reference UMH as "substrate" not "reality engine"; EOS becomes an instance reality model for business operations |
| CreatorOS integration artifacts (`phase14_6b_creatoros/`) | Same as EOS -- CreatorOS becomes an instance reality model for creator operations |
| LyfeOS integration artifacts (`phase14_6b_lyfeos/`) | Same -- LyfeOS becomes an instance reality model for life management |
| UMH open questions document | New decisions needed about reality-model scope, layer priority, Stage 1 minimum |
| ARCHITECTURE.md | Master specification references UMH as orchestration system |
| PHILOSOPHY.md | Philosophy doc may need reality-model alignment |
| CLAUDE.md | Developer agent instructions reference UMH as "substrate" throughout |

---

## What This Correction Blocks

This P0 correction gates the following work items. None may proceed until
the ratification decisions below are resolved.

| # | Blocked Item | Why Blocked |
|---|-------------|-------------|
| 1 | Any Cockpit implementation phase (14.6G or later) | Cockpit design depends on whether it is "an operational dashboard" or "a reality-model interface." These produce fundamentally different UX architecture. |
| 2 | Any UMH reality-engine or world-model build phase | The scope, layer structure, and integration model of the reality engine depend on the ratified identity. |
| 3 | Any Stage 1 organism definition that treats components as sequential | The operator explicitly rejected sequential component delivery. Stage 1 = simultaneous minimum viability of Reality Model + Cockpit + Memory + Governed Execution Loop. |
| 4 | Any projection integration that does not account for reality-model data flow | Projections must be framed as instance reality models, not just "views." Integration architecture changes. |
| 5 | Any execution-model unification (DEC from `umh_execution_boundary_model.md`) | The Materialization Principle adds a new dimension to execution: gap detection and typed path generation. Execution unification must include this. |

---

## Ratification Decisions Required

### DEC-146C-001: UMH Reality Model Identity — OPERATOR-APPROVED WITH MODIFICATION

**Priority:** P0
**Status:** OPERATOR-APPROVED WITH MODIFICATION (2026-06-04)
**Operator Selection:** Option A modified

**Ratified Canon Statement:**

> Universal Meta Harness is the integrated AI-native system/product whose core functional purpose is to build, maintain, and act through a reality-isomorphic approximation of reality. UMH attempts to model reality across physical, digital, cognitive, biological, social, economic, symbolic, operational, software, memory, source-truth, and OS-level layers. Orchestration, governance, execution, memory, adapters, agents, Cockpit, and projections are capabilities/organs serving this reality model; they are not separate identities from UMH. The reality model is not merely operational tooling. It is the central organizing model through which UMH understands intent, state, constraints, resources, possible actions, consequences, and feedback.

**Operator Constraints:**
- Product name remains "Universal Meta Harness." Do not rename to "engine."
- Functional identity: reality-isomorphic intelligence harness / reality-modeling system.
- Naming canonicalization must preserve "Universal Meta Harness" as the only product name.

**Impact (now confirmed):**
- All 17 directly affected artifacts require content revision in Phase 14.6D
- UMH identity across CLAUDE.md, ARCHITECTURE.md, PHILOSOPHY.md must be updated
- All projection integration architectures must be revised
- Cockpit UX architecture changes from "operational dashboard" to "reality-model interface"
- World model subsystem becomes the architectural center, not a subsystem
- Product name "Universal Meta Harness" is retained throughout

---

### DEC-146C-002: Materialization Principle Adoption — OPERATOR-APPROVED WITH MODIFICATION

**Priority:** P0
**Status:** OPERATOR-APPROVED WITH MODIFICATION (2026-06-04)
**Operator Selection:** Option A modified

**Ratified Canon Statement:**

> If a human can imagine an outcome, UMH should attempt to simulate the path from imagination to materialization. Lack of current knowledge, resources, tools, capital, information, skill, access, or time does not invalidate the intent; it creates typed gaps and acquisition paths: research loops, resource acquisition loops, experiment loops, work packets, delegation paths, agent paths, financing paths, and time-bound execution paths. UMH should not treat current missing capability as terminal failure. It should classify the gap, identify what must be acquired or learned, generate the highest-leverage path, and govern execution. If an outcome violates physical reality, law, safety, ethics, or non-negotiable constraints, UMH must state the boundary clearly and propose the nearest lawful/safe/materializable alternative.

**Operator Constraints:**
- This is a core design constraint, not aspirational.
- "Impossible" should not be used as lazy failure language.
- UMH must distinguish impossible, illegal, unsafe, unavailable, under-resourced, unproven, and not-yet-acquired.
- Gap states must generate typed paths, not dead ends.

**Impact (now confirmed):**
- Execution boundary model gains gap-detection and path-generation requirements
- Governance must cover reality-model gap responses, not just action risk
- Every "blocker" in the system becomes a "typed execution path"
- Work packet engine must support materialization-path work packets
- Reality model must track gaps and their resolution paths
- Safety/ethics boundary added: physically impossible, illegal, unsafe, or unethical outcomes are not materialized

---

### DEC-146C-003: Indivisible Stage 1 Definition — OPERATOR-APPROVED

**Priority:** P0
**Status:** OPERATOR-APPROVED (2026-06-04)
**Operator Selection:** Option B (Indivisible target, incremental build)

**Ratified Canon Statement:**

> Stage 1 is one minimum viable UMH organism: Reality Model + Cockpit + Memory + Governed Execution Loop. These components are not separate products or sequential phases. They must reach minimum viability as one integrated system. The harness cannot function as intended without the reality model. Cockpit without a reality model is only a dashboard. A reality model without Cockpit is inaccessible to the operator. Memory without execution is passive storage. Execution without memory, governance, and reality model state is unsafe and incoherent. Incremental builds are allowed only inside the indivisible Stage 1 target: each increment must advance the integrated organism across Reality Model, Cockpit, Memory, and Governed Execution rather than completing one component in isolation and deferring the others.

**Operator Constraints:**
- Reject sequential build framing.
- Accept incremental delivery only if increments advance the integrated organism.
- Stage 1 is not complete until all four components are minimally viable together.
- Do not define Stage 1 as a backend-only substrate.
- Do not define Cockpit as a passive dashboard.
- Do not defer reality model, memory, or governed execution to later phases.
- Do not require commercial-grade completeness before use.

**Operator Clarification — Stage 1 Minimum Viability (2026-06-04):**

"Indivisible Stage 1" does not mean all components are fully built before use. It means the minimum vertical slice must include partially functional Reality Model + Cockpit + Memory + Governed Execution together. The minimum version must provide a usable Jarvis-style operating experience — functional enough for the operator to actually operate through it.

Stage 1 minimum viability acceptance criteria:

1. Operator can use Cockpit/Jarvis as primary interface
2. UMH can capture intent and preserve it in memory/source truth
3. UMH can maintain a usable reality model (work, products, companies, files, artifacts, agents, blockers)
4. UMH can generate work packets from operator intent
5. UMH can route work packets to agents/tools (Claude Code, shell, GitHub, docs, adapters)
6. UMH can govern risky actions through approval gates
7. UMH can verify outputs (tests, audit reports, diffs, review packets)
8. UMH can update memory/reality model after outcomes
9. UMH can work on itself through governed self-improvement work packets
10. UMH can build and improve projection apps from inside the UMH operating loop

The target is a usable, self-improving UMH organism — not a complete system or backend-only substrate.

Projection app minimum viability:
- EOS: usable enough to run company operations
- CreatorOS: usable enough to run content/community/product workflows
- LyfeOS: usable enough to run personal execution/transformation workflows

**Impact (now confirmed):**
- Cannot ship any component independently
- All roadmap sequencing changes -- no "build substrate first, then Cockpit, then reality model"
- Stage 1 acceptance criteria are the 10 items above, verified against operator usability
- Cockpit readiness criteria (artifacts 5, 6, 7) must be rewritten around organism viability
- Incremental builds are allowed but must advance all four components in each increment
- UMH must be self-improving: work on itself through governed work packets
- Projection apps built from inside UMH, not as separate projects

---

## Confirmed Correction Sequence

All three decisions have been ratified by the operator (2026-06-04). The correction sequence is now confirmed:

| Phase | Scope | Deliverable | Status |
|-------|-------|-------------|--------|
| **14.6C** (this document) | Capture, present, and ratify correction | P0 operator clarification + ratification record | **COMPLETE** |
| **14.6D** | Revise 17 directly affected UMH artifacts | Updated artifacts with reality-model framing, new Stage 1 definition, Materialization Principle integration | NEXT |
| **14.6E** | Update EOS/CreatorOS/LyfeOS integration artifacts | Projection artifacts reframed as instance reality models | BLOCKED (awaits 14.6D) |
| **14.6F** | Revised Stage 1 organism definition | Single document defining the minimum viable indivisible organism with acceptance criteria | BLOCKED (awaits 14.6D) |
| **14.6G** | Cockpit implementation (as reality-model interface) | First implementation phase, building against the revised canon | BLOCKED (awaits 14.6D + remaining P0 decisions) |

---

## Audit Trail

| Date | Event | Actor |
|------|-------|-------|
| 2026-06-04 | Operator states reality-model correction | Operator (AFM) |
| 2026-06-04 | Correction captured in this document | Developer Agent |
| 2026-06-04 | Document added to Phase 14.6C operator review packet | Developer Agent |
| 2026-06-04 | Operator ratifies DEC-146C-001 with modification: reality-isomorphic intelligence harness, product name retained as "Universal Meta Harness" | Operator (AFM) |
| 2026-06-04 | Operator ratifies DEC-146C-002 with modification: Materialization Principle as core design constraint, expanded gap taxonomy, safety/ethics boundary | Operator (AFM) |
| 2026-06-04 | Operator ratifies DEC-146C-003 as Option B: indivisible Stage 1 target, incremental builds advancing all four components | Operator (AFM) |
| 2026-06-04 | Operator adds Stage 1 minimum viability clarification: 10 acceptance criteria, projection app viability, self-improvement mandate | Operator (AFM) |
| 2026-06-04 | Ratification decisions and clarifications recorded in this document and decision queue | Developer Agent |
| Pending | 17 affected artifacts revised per ratification decisions (Phase 14.6D) | Developer Agent |

---

## Integrity Statement

This document captures the operator's words as faithfully as possible.
Every quoted passage is verbatim from the operator's 2026-06-04 directive.
Every artifact assessment is grounded in actual file content read from
`data/umh/trinity_convergence/phase14_6b_umh/` with specific line references.
No claim is made from memory; all were verified against source files.

The three ratification decisions (DEC-146C-001, DEC-146C-002, DEC-146C-003)
have been OPERATOR-APPROVED as of 2026-06-04. The ratified canon statements
and operator constraints are recorded above and in the decision queue.

Implementation remains blocked. The ratified decisions unblock Phase 14.6D
(UMH canon artifact revision) but do not authorize Cockpit, reality-engine,
or projection-app implementation. `allows_implementation` remains false.
