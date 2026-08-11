---
type: codewiki-page
dir: (cross-cutting)
---

# Role + Composition — The Employee Model (What Runs, and How It's Assembled)

The organizing model behind UMH's workforce: **the same agent-orchestration
pattern Anthropic uses (agent = tools + skills + memory + context + model +
responsibilities + reports-to + tasks + reports), applied to UMH, with the
Role as the primitive that keeps only what's essential.** Given a task, the
right adapters + Roles are assembled (solo or teamed), models and tools chosen,
and a **Workflow** strings them into a sequence or loop to collaborate. This
page is grounded in code read at `main` (2026-07-10); every claim is
file:line-cited. Companion: [terminal-fabric.md](terminal-fabric.md) — *how*
those agents run and survive overnight. This page is the *what* and the *how
assembled*.

## The mapping (employee → Anthropic term → UMH primitive that already exists)

| Employee concept | Claude Code / Anthropic term | UMH primitive | Home |
|---|---|---|---|
| The employee | Agent / subagent | **Role** (`RoleContract`) | `substrate/organism/role_contracts.py:66` |
| What they can do | Tools | Adapters + Capabilities | `adapters/`, `capability_router.py` |
| Learned competence | Skills | Tool Mastery skills | `skills/` |
| What they remember | Memory | memory types + continuity | `substrate/organism/` |
| What they know | Knowledge | graph / palace | `knowledge/`, `data/codebase_pages/` |
| What's in front of them | Context | SubstrateContext (BIS at runtime) | `substrate/state/context/` |
| Which brain | Model | `model_router.call_with_fallback` | `adapters/models/` |
| Their job | Responsibilities | `owned_work_types` / `owned_domains` | `role_contracts.py:70-71` |
| Chain of command | Reports-to | `escalation_rules` + hierarchy | `role_contracts.py:79` |
| Who they can hire | Sub-agent spawn | `spawn_permissions` | `role_contracts.py:75` |
| A unit of work | Task | WorkPacket | `nodes/environments/work_packet.py` |
| Status up | Report | `report_dispatcher` | `substrate/organism/report_dispatcher.py` |
| Stringing it together | Workflow (sequence/loop) | Composition → Plan → Execution | see below |

## The three organs already in code (this is the correction)

A prior verdict called this "the composition gap — `substrate/templates/` is 3
files." That looked in the wrong directory. The real machinery lives in
`substrate/organism/`, is richer than claimed, and — crucially — is **LIVE, not
dormant**:

**Organ 1 — Role primitive.** `RoleContract`
(`substrate/organism/role_contracts.py:66`) is the employee, already built:
`allowed_tools`, `capability_profile` (→ `CapabilityProfile`,
`role_contracts.py:26` — carries `capabilities`, `reliability_by_capability`,
successful/failed outcomes, `average_confidence`: a **per-role trust ledger**),
`owned_work_types`, `owned_domains`, `knowledge_access_policy`,
`spawn_permissions`, `approval_requirements`, `escalation_rules`,
`validation_responsibilities`, `reconvergence_responsibilities`,
`reliability_score`, `version`, `status`.

**Organ 2 — Composition engine.** `CompositionEngine.compose()`
(`substrate/organism/composition_engine.py:319`) — its docstring is almost the
operator's own sentence: *"Intent + Context + Constraints → Available
capabilities → Dependencies → Risks → Executable plan… NOT freeform LLM
planning. It composes from observed reality."* Produces a `CompositionPlan` of
`CompositionStep`s. **LIVE** — production callers:
`autonomous_improvement_lane.py:726,811`, `trial_runner.py:572`, and HTTP
surfaces `cockpit_spine_router.py:702`, `organism_bridge.py:748,769`.

**Organ 3 — Plan executor.** `PlanExecutionAdapter`
(`substrate/organism/plan_execution_adapter.py:319`) converts a
`CompositionPlan` → `ExecutablePlan` (`convert_plan`, line 342) of
`ExecutableStep`s with a dependency DAG (`ready_steps()`, line 183) and executes
each through a governed-mutation envelope (`_build_envelope`, line 383), with an
`OutcomeLearningLoop` hook (line 327).

So intent → composed plan → governed execution **exists and runs today**. The
skeleton composes; governance guards; outcomes are recorded.

## The real gap — four missing bindings (not a missing architecture)

The three organs aren't threaded into the *employee* model. Precisely:

1. **Role ↔ model is unbound.** `RoleContract` has **no model field** (verified:
   zero `model`/`opus`/`provider` references in `role_contracts.py`). Model
   choice happens separately in `model_router` by `agent_type`/`TaskType`. The
   operator's "models used [per role]" isn't expressed on the Role.
   → Add `preferred_model` / routing-hint to `RoleContract`; `model_router`
   honors it.

2. **Composition ↔ Role is unbound.** `CompositionStep` carries no `role_id`
   (verified: no role binding in `composition_engine.py`). Composition selects
   *capabilities from the world model*, not *Roles (employees)*.
   → `CompositionStep` gains `role_id`; `CompositionEngine` selects Roles whose
   `capability_profile` matches the step — and the `reliability_by_capability`
   ledger already there is exactly the signal for *which* employee to pick.

3. **Step ↔ agent execution is unbound.** `PlanExecutionAdapter` runs steps as
   governed **actions**, not as **agents** that reason, use their bound
   tools/skills/model/memory, and hand output to the next step.
   → Execute each role-bound step as a live agent; output feeds the next =
   **workflow sequence**; independent steps run parallel = **team**; a step that
   re-queues itself = **loop**. This is the operator's "workflow strings agents
   together in a sequence or loop."

4. **The loop ↔ persistent supervisor is unbound.** Composition→execution fires
   **on-demand** (improvement lane, trial runner, HTTP), never under a
   service-hosted 24/7 supervisor. This is the [terminal-fabric.md](terminal-fabric.md)
   half — without it, the workforce still stops at night.

## Teaming (assemble N Roles for one task)

Both councils exist — `substrate/organism/council.py` and
`substrate/understanding/deliberation/council.py` (a canon-rot duplicate flagged
in [vision-alignment.md](vision-alignment.md)) — providing multi-perspective
panels. What's absent is the composition-time decision *"this task needs Role A
+ Role B teamed vs Role A solo,"* driven by the task and the roles'
`capability_profile`s. Teaming = a `CompositionStep` (or step group) that binds
**more than one** `role_id` and runs them parallel with a reconvergence step
(the `reconvergence_responsibilities` field on `RoleContract` already names who
owns the merge).

## Essentialism, mechanically enforced

The operator's "keep only what's essential" is not a style guideline here — the
**Role manifest is the essentialism boundary made mechanical.** A Role declares
its exact `allowed_tools` + capability set + knowledge policy + (proposed) model;
composition may bind *only* what a Role declares. No redundant capability, one
home each, and the LLM "breathes life into it by traversing the code within the
guardrails" (the operating model in
[canonical-registry.md](canonical-registry.md)). Binding #1–#3 above turn the
Role from a character sheet into the enforced unit of composition.

## Build order (bindings, in dependency order)

WP-RC-001 Role↔model field + router honor · WP-RC-002 `role_id` on
`CompositionStep` + Role selection by `capability_profile` · WP-RC-003 role-bound
step execution as live agent (sequence) · WP-RC-004 teamed steps (parallel +
reconvergence) · WP-RC-005 loop steps (re-queue) · WP-RC-006 host the
composition→execution loop under the persistent supervisor
([terminal-fabric.md](terminal-fabric.md) Tier A). Each ships behind the
existing governed path — no new runtime, four bindings on organs that already
run.

## See also

[fractal-capability.md](fractal-capability.md) · [terminal-fabric.md](terminal-fabric.md) ·
[vision-alignment.md](vision-alignment.md) · [canonical-registry.md](canonical-registry.md) ·
[build-doctrine.md](build-doctrine.md) · [architecture.md](architecture.md)
