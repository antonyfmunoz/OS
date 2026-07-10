---
type: codewiki-page
dir: (cross-cutting)
---

# The Canonical Registry — Every Element of UMH, One Home Each

The essentialist master taxonomy: every law, layer, loop, registry, role, mode,
and enumeration from the UMH Master Document (14 tabs) and the Jarvis Master
Handoff, **deduplicated to exactly one canonical entry with one assigned home**.
Operating model this registry serves: *the deterministic skeleton owns all
structure, definitions, and governance; LLM intelligence breathes life into it
by traversing the code and executing within the guardrails.* No element may
exist twice; no element may exist without a home (No Inferior Duplication
Principle + Ontology Home Law, Gate 13).

Status labels per Tab 12 document governance: **ENFORCED** (gate/code),
**BUILT** (exists in code), **PARTIAL**, **DESIGNED** (doc only), **FUTURE**.

## 1. Identity (one definition, locked)

UMH = Universal **Meta Harness** (never "Mastery Hierarchy" —
`substrate/organism/system_identity.py` bans it; `.claude/CLAUDE.md` line 3
still carries the banned form — open canon-rot fix). Canonical definition:
*"The governed control plane for externalized cognition, mastered action,
cross-environment execution, and recursive human capability compounding."*
Shortest: infrastructure for turning intent into governed, reusable,
compounding capability. Prime Directive: **minimize human friction while
maximizing human capability under real-world constraints.** Governing purpose
(EPISTEMOLOGY.md): **maximize justified capability.** DEX = operator-facing AI
identity (internal: Advisor). Jarvis = the operator-experience north star, not
a product.

## 2. The Laws (deduplicated constitution — 22, each with its home)

| # | Law | Home / enforcement | Status |
|---|---|---|---|
| 1 | Control Plane Exclusivity — nothing executes outside the plane | canonical_runtime.py + governed_mutation (transports/api/governed.py) | BUILT |
| 2 | Single Execution Spine — one path signal→learn; branches reconverge | GovernedExecutionSpine; PLATFORM_SPEC frozen | BUILT |
| 3 | Governance Before Execution — verdicts: autonomous/notify/approve/escalate/deny | governance.py RiskClass + authority_engine.py | BUILT |
| 4 | Typed Contracts Only | canonical_types.py (~1,157 types) + Gate: check_type_divergence.py | ENFORCED |
| 5 | Adapter Isolation / External Boundary — adapters translate, never execute | adapters/ base-adapter permission enforcement | BUILT |
| 6 | Action/Execution Separation — adapter≠worker≠actuator≠proof | worker_runtime_contracts.py; WorkPacket contract | BUILT |
| 7 | Memory Discipline — trace is not memory; governed candidates only | substrate/memory/canonical_write.py | BUILT |
| 8 | Environment Explicitness — no declaration, no execution | nodes/environments/ binding contracts + validators | BUILT |
| 9 | Trace Completeness — unexplainable run = incomplete run | substrate/execution/trace.py | BUILT |
| 10 | Deterministic Core — intelligence recommends, never controls | Deterministic-First (CLAUDE.md) + grounding firewall | ENFORCED |
| 11 | Mastery Law — scoped, versioned, testable competence before execution | TME + mastery_gate.py + skills/tools (97 skills) | BUILT |
| 12 | No Hidden Self-Modification — safe recursion: detect→propose→simulate→sandbox→test→compare→approve→deploy→trace→monitor | doctrine; no self-mod pipeline exists yet | DESIGNED |
| 13 | Observed Reality > Declared Intent (anti-hallucination invariant) | Grounding Law: grounded_handlers.py, test_grounding_firewall.py | ENFORCED |
| 14 | Reality Mimicry Is Native (organisms/cells/markets as patterns when technically apt) | organism/ subsystem naming + design | BUILT |
| 15 | Canonical vs Instance Separation | Gate: check_instance_leak.py; instance.json/BIS | ENFORCED |
| 16 | Projection Boundary — projections never own intelligence | Gate: check_projection_leak.py | ENFORCED |
| 17 | Architecture Layer Law — one-way downward imports | Gate: check_dependency_direction.py (also bans substrate→adapters) | ENFORCED |
| 18 | Ontology Layer/Home Law — L1–L4 separation; frozen home set | Gates: check_ontology_layers.py + check_ontology_homes.py (13) | ENFORCED |
| 19 | CPU Gate Law — 6-layer defense; never saturate a host | cpu_gate.py + Gate 5 | ENFORCED |
| 20 | Credential Injection Law — 1Password op run; never plaintext | Gate: check_credential_injection.py + credential_gate.py | ENFORCED |
| 21 | Provider Role Law — purpose-based routing, no generic equivalence | model_router purpose/role routing | BUILT |
| 22 | **No Inferior Duplication / Essentialism** — every subsystem/tool/model must have a unique reason to exist; one concept, one home | LEGACY_DUPLICATES ledgers (shrink-only) + Gate 13 + this registry | PARTIAL |

Supporting operational laws (repo-grown, same spirit): Browser Verification
(executor nodes only), Device Naming (registry-driven), Client-Failure
Observability (instrument before second fix), Cockpit Deploy Gate,
Grounding/Type/Plan-Immutability rules — homes in `.claude/rules/*.md`, all ENFORCED.

## 3. Ontology (L2 metamodel — one home: substrate/types.py + substrate/ontology/)

**Primitives (10):** state, change, constraint, resource, time, signal,
feedback, goal, action, outcome. (13 implemented in
substrate/state/business/primitives.py — L3 relocation completed per Gate 13.)
**Laws (13):** causality, feedback, compounding, entropy, emergence,
constraints, equilibrium, temporal dependency, resource scarcity, tradeoffs,
local/global optimization, polarity/tension, boundary effects.
**System concepts (24):** entity, relationship, environment, capability,
authority, risk, uncertainty, memory, identity, pattern, policy, plan,
composition, execution, trace, proof, adapter, worker, actuation, domain,
template, registry, library, profile.

## 4. The Ten Macro-Layers → code homes

1 Interface → cockpit/, transports/ surfaces · 2 Control Plane →
substrate/control_plane/ · 3 Understanding → substrate/understanding/ ·
4 State → substrate/state/ + memory/ + reality_model/ · 5 Composition →
substrate/composition/ + templates/ (**thinnest layer — the composition gap**) ·
6 Governance → substrate/governance/ · 7 Execution Plane →
substrate/execution/ + organism runtime · 8 Adapter Boundary → adapters/ ·
9 Observability+Proof → substrate/observability/ + execution/trace.py ·
10 Learning+Self-Regulation → execution/feedback.py + organism/
(homeostasis = CPU-gate stack). Rule: **no orphan systems, no side-door
execution, no feature without architectural placement** (fail-closed dir
classification in generate_codewiki.py mirrors this).

## 5. The Canonical Spine (28 stages, one path)

Signal → Control-Plane Intake → Perception → Interpretation → Decomposition
(tokens→grammar→semantics→concepts→primitives→relationships→constraints→context)
→ Ontology Mapping → Domain Mapping → World/Memory/Profile Retrieval → Breadth
Expansion → Completeness Detection → Registry/Library/Template Lookup →
Capability Selection → Adapter/Environment Matching → Composition → Planning →
Mastery Check → Quality Check → Governance Decision → WorkPacket Creation →
Worker Routing → Adapter-Bound Interaction → Actuation → Result Collection →
Proof Validation → Trace Persistence → Outcome Evaluation → Learning Proposal
→ Memory/World/Profile Update → Self-Regulation.
Current reality: intake→interpret→govern→execute→trace→outcome runs; stages
9–15 (breadth→composition) are the missing organ; 26–28 record but don't yet
recompound.

## 6. Terminology Lock (26 terms — the system's vocabulary, one meaning each)

Signal · Interpretation · Decomposition · Ontology · Domain · World Model ·
Memory · Profile · Registry (what exists/selectable) · Library (reusable
knowledge) · Template (typed instantiable blueprint = "compressed
operationalized understanding") · Capability (abstract ability) · Adapter
(translation boundary) · Adapter Family (suite grouping, e.g. GWS) · Access
Path (API/SDK/CLI/MCP/CU/browser/human) · Environment · Action (intended state
transformation) · Work Packet (governed executable instruction) · Execution
Spine · Worker Runtime · Actuation · Governance · Mastery · Proof · Trace ·
Learning. **Distinction that must never collapse:** Registry ≠ Library ≠
Template ≠ Memory ≠ Profile. Composition = the engine that *uses* all five:
intent + world model + constraints + resources + domain map + memory +
registry + library + templates = executable system instance.

## 7. The Enumerations (assigned, exhaustive)

- **Registries (18):** capability, adapter, backend, environment, worker,
  template, workflow, agent, model, tool, policy, memory, prompt, schema,
  evaluation, domain, workstation_mode, boot_sequence. Home:
  substrate/state/registries/ (partial today: skills, others scattered —
  unification = roadmap Phase "Registry Unification").
- **Library types (15):** domain, system, pattern, primitive, workflow,
  decision, governance, adapter, benchmark, prompt, playbook, ontology,
  quality, failure_mode, mastery. Home today: skills/ + knowledge/ (merge
  target).
- **Template anatomy:** 10 immutable primitives (input, processing, output,
  feedback, constraint check, failure handler, quality benchmark, governance
  gate, trace event, memory update) + 12 customizable slots (goal, domain,
  environment, tools, constraints, tone, budget, timeline, risk tolerance,
  approval level, output format, success metric). Kinds (5): structural,
  workflow, UI, code, platform. **Instantiation equation: template + context
  = active executable system.** Home: substrate/templates/ (3 files — to build).
- **Capability types (17):** llm_reasoning, code_editing, shell_command,
  browser_action, api_operation, file_operation, workflow_execution,
  memory_query, world_model_update, notification, calendar_action,
  email_action, device_control, simulation, robotic_action,
  human_approval_request, computer_use_operation. Home: capability_router.py
  (28 job capabilities today).
- **Adapter categories (15):** tool, SaaS, API, CLI, MCP, environment,
  runtime, model, human-approval, data-source, filesystem, database, browser,
  computer-use, physical-world. Contract: connect/validate/describe/translate/
  validate_op/normalize/observe/disconnect.
- **Memory types (14):** working, episodic, semantic, canonical, instance,
  behavioral, procedural, trace-derived, profile, environment, goal,
  world-state, pattern, policy. Flow: Execution→Trace→Outcome→Learning
  Proposal→Memory Candidate→Promotion→Update.
- **Learning types (14):** local feedback, strategy feedback, pattern
  confidence, temporal decay, weight evolution, regime learning,
  cross-dimension interaction, policy, world-model update, profile update,
  template performance, capability reliability, adapter reliability, mastery
  update. (docs/audits phase19–74 reports = the built regime/weight stack.)
- **Mastery categories (11):** tool, action, domain, environment, data, model,
  adapter-boundary, human-approval, governance, context, physical-world.
- **Completeness slots (13):** input, processing, output, feedback,
  constraints, failure handling, optimization loop, governance requirement,
  execution environment, observability, memory path, quality benchmark, proof
  requirement. Home: substrate/governance/validation/completeness_engine.py
  (exists; not yet a mandatory spine stage).
- **Governance verdicts (5):** autonomous, notify, approve, escalate, deny ·
  **Autonomy levels:** 0–5, Finance/Legal never full · **Permission tiers:**
  4 cumulative (READ→…), 52 action types, 3 enforcement layers · **Risk
  classes (10):** read-only, reversible write, irreversible write, financial,
  security-sensitive, identity/reputation, destructive-local, external
  communication, legal/compliance, physical actuation.
- **Environments (11):** local device, mobile, VPS, cloud, browser, sandbox,
  container, simulation, offline, mesh group, physical device. **Worker
  runtimes (10):** VPS worker, local WSL, local Windows GUI, tmux session,
  container, browser, API, model, human operator, robot (future).
  **Actuation types (9):** OS control, browser automation, API op, file op,
  workflow, device control, notification, robotic action, human-approval
  request. **Work lanes (4):** foreground, background browser, background
  shell, native app (Chrome-first policy; Session-0 excluded).
- **Protocol Pack (27 modules):** signal, interpretation, decomposition,
  ontology, domain, world, memory, profile, registry, library, template,
  capability, composition, planning, mastery, governance, action, work_packet,
  execution, adapter, environment, worker, actuation, proof, trace, outcome,
  feedback. **Event model (13):** SignalReceived → … → LearningUpdated.
  Home: substrate/contracts/ + types.py (consolidation target).
- **Deliberation Council roles (7):** primary strategist, skeptic/red-team,
  completeness auditor, risk/governance auditor, domain specialist,
  implementation engineer, synthesis judge — advisory only, never executes.
  Homes today: organism/council.py + understanding/deliberation/council.py
  (**duplicate — must merge to one**).
- **Domains (~26)** with DomainMap contract (entities, workflows, constraints,
  required slots, failure modes, benchmarks, templates, capabilities, domain
  laws) + Domain Law Registry (business laws, human-performance laws, software
  laws…). Home: substrate/understanding/domains/ (L4 bridges exist; law
  registry DESIGNED).
- **Workstation modes (10):** Command Center, Developer, Research, Workstation,
  Outreach, Content, Overnight, Maintenance, Simulation, Emergency · **Boot
  sequences (4 specified):** Developer, Research, Command Center, Overnight ·
  **Profile modes (7, built):** active_day, deep_work, creative_build,
  admin_ops, away, night_cycle, shutdown · **7-Axis Awareness:** WHO=Profile,
  AVAILABLE=Presence, WHERE=Session, WHAT=Command, WHY=Goals/Gap/Projection,
  MEMORY=Continuity, DO=Execution Coordinator · **Voice routing (5 dims):**
  input_device, control_surface, execution_target, audio_output,
  render_surface (BUILT, 14.13U). Never collapse Profile/Mode/Session/Presence.
- **Agent roles:** 11 soul docs (agents/), 4 CC subagents (.claude/agents/),
  4 organism workcells (advisor, executor, researcher, reviewer), advisor
  cell vs disposable worker cells. Character in soul docs; mechanics in code;
  never duplicated (rule: .claude/rules/agents.md).

## 8. The Loops (all named, one meta-loop)

Prompt · Context · Agent · Execution · Governance · Feedback · Learning ·
Operator · **Meta Loop = UMH itself** (contains all lower loops).
Operationalization loop: Learn Once → Understand Deeply → Extract Invariants
→ Template → Capability → Operationalize → Reuse Forever → Improve Forever.
Safe self-recursion loop (10 steps, law 12). Organism cycle: Think → Act →
Observe → Govern → Remember State. Reconciler loop (target): DesiredState −
ObservedState → Gap → WorkPackets → governed execution → repeat.

## 9. Roadmap canon (all sequences, one authority)

Maturity **Tiers 1–6** (MVP→Operational→Learning→World-Model→Organism→AI-OS;
reality today = Tier 2+, Tier 1 frozen as PLATFORM_SPEC v1.0.0). Leverage
doctrine **5 stages**: Orchestration→Optimization→Internalization→Ownership→
Embodiment. **Three Worlds**: information→digital→physical (adapters are the
only thing that changes). **Five Generations**: labor amplification→cognition
amplification (now)→capability compounding→collective→civilizational.
**Product stack order**: personal harness→Workstation/Jarvis→EOS→CreatorOS→
LYFEOS→HoldCo infra→proprietary intelligence→AI-native OS. **Release gates
(Tab 7)**: dogfood→trusted alpha→design partners→public beta→launch; testing
duration scales with authority level (read-only weeks → high-risk 6–12+ mo).
**Moat layers (8)**: software, data, workflow, distribution, network,
infrastructure, capital, trust. **EOS track**: EOS-1 company model … EOS-8
portfolio dashboard. Legacy phase numberings (Tab 5 76–108, Tab 6 76–110,
handoff P1–P17/14.x) are HISTORICAL — superseded by repo P1–P3 + the 7-stage
gap-closure program in [vision-alignment.md](vision-alignment.md).

## 10. Working principles (the culture, deduplicated)

Vertical slices, not capability explosions · Governance first, autonomy second
— never reverse · Observation before optimization · Reality before simulation
· **Convergence before expansion** · Composition, not creation (compose prior
phases, never reimplement) · Fail closed · Never the first acceptable answer
(Excellence Gate) · Test-green ≠ product-green — the bar is live physical
behavior · Wrap now, internalize later (absorb-don't-rebuild) · Leverage-first
tool choice (hammer-vs-wrench) · Best model for the job, subscriptions before
API spend · One-shot exhaustive plans · Essentialism: everything assigned,
nothing duplicated, nothing homeless.

## 11. The operating model (the sentence that governs it all)

**The deterministic skeleton owns all structure** — laws, types, registries,
templates, spine stages, gates, budgets — **and LLM intelligence breathes life
into it by traversing that structure and executing within its guardrails.**
Intelligence proposes; the skeleton disposes. The LLM fills typed slots, never
invents control flow; when every model is down the skeleton still walks
(deterministic fallbacks); when better models arrive the same skeleton runs
faster and deeper (model-agnosticism: intelligence lives above the model).
Enforcement of this model is the sum of laws 1, 2, 10, 13, and 21.

## Redundancy debt (essentialism violations to close — shrink-only)

1. Two councils (organism/ vs understanding/deliberation/) — merge to one.
2. Three knowledge systems (knowledge/ CANON, data/codebase_pages, docs/codewiki)
   — assign non-overlapping jobs explicitly (business wiki / symbol graph /
   current-reality map) or consolidate.
3. Legacy type homonyms — capped in LEGACY_DUPLICATES_META (shrink-only, keep shrinking).
4. skills/ ↔ .agents/skills ↔ .claude/skills symlink trio — by-design single
   source (.agents canonical); document, don't duplicate.
5. Three roadmap numbering schemes — declare HISTORICAL (this registry does).
6. `.claude/CLAUDE.md` banned name expansion — fix.
7. saas/, .claire/, umh/ 3.12 pycache — delete (audit register).

## See also

[vision-alignment.md](vision-alignment.md) · [architecture.md](architecture.md)
· [conventions.md](conventions.md) · [audit-2026-07-10.md](audit-2026-07-10.md)
