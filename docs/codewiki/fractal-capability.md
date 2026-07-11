---
type: codewiki-page
dir: (cross-cutting)
---

# The Organism — First-Principles Theory of UMH

The theory the rest of the system is a consequence of. UMH is a **governed
Artificial Super-General Intelligence** whose purpose is **human flourishing**: it
**democratizes creation** — the power to transform reality, to turn *intent into
materialized, manifested reality* — putting in anyone's hands what historically
required teams, capital, and expertise. It is a dormant cybernetic tool that a
user awakens into a living organism, which externalizes the user's own cognition
and execution onto governed compute — mastering each capability so completely, and
synchronizing every governed capability into one harmonious organism, that the
user is continuously promoted up the work ladder, from *doing* to *directing*.
**Governance is not (only) a cage — it is the system's conscience:** every
capability, at every scale, is kept oriented toward the human's good, not merely
kept from going wrong. And a manifested change *holds* only
if it is coherent with the field of reality around it — so UMH transforms a whole
region into coherence, expanding resources, systems, and (when the incoherence is
in the self) the user themselves. At root UMH is a **microcosm of reality** — a
legible instance of the same field the human is lost inside of at full scale — so
operating it raises the user's awareness of how reality works: it is a
consciousness instrument as much as an execution one. This page states the nine principles, each as **principle →
mechanism → verified gap**, and the lifecycle (install → onboard → ambient life)
that is their spine.
Companions: [role-composition.md](role-composition.md) — how the living organism
assembles a body per task; [terminal-fabric.md](terminal-fabric.md) — how it
stays alive. Claims are code-grounded at `main` (2026-07-10).

## The one law, and why every artifact is an instance of it

**Governed Mastered Capability.** Every function the system performs is a
*capability*; every capability must be *mastered* (done as well as or better than
the best human could), *governed* (delegated semi-autonomy inside an envelope),
and *harmonically synchronized* with every other capability into one organism. A
YAML file, a hook, an adapter, a `CLAUDE.md`, a command, a deep agent — each is
the **same law wearing a different file format**. This is why "YAML is an example
of a principle": an artifact is a principle projected into a form, and it must
stay *isomorphic to the principle it projects*. **Projection drift** — a stale
`CLAUDE.md` line, a redundant hook, a divergent config — is a capability
performing un-masterfully and out of sync, breaking the organism's harmony. It is
the same category of error as a bug.

## The purpose — democratized creation, governed toward flourishing

Every mechanism below exists for one telos. The system is not merely "a governed
AI orchestration platform" — it is **a democratizer of creation, governed toward
human flourishing, that grows its user.**

- **It democratizes creation.** *Creation = reality transformation = intent →
  materialized, manifested reality.* Historically, turning intent into real change
  required resources, expertise, teams, capital — gated to the few. UMH puts the
  power to *manifest intent into reality* in anyone's hands (mastery ships in the
  canon; the user supplies only context). This is the civilizational claim and the
  real product.
- **Governed toward flourishing, not just safety.** Governance keeps every
  capability oriented toward the human's good — the objective function's telos
  (P7). Remove flourishing and "governed" degrades from *purposeful* constraint
  into *mere* constraint. Governance is the conscience, not only the cage.
- **The human is always at the top; the AI↔code link is a mutual loop.** The human
  governs the AI (one-way, human atop everything). But the AI and the deterministic
  template code **govern each other**: the AI governs the code (adapts/controls the
  living software), *and is simultaneously governed by* that same code (its
  invariants/guardrails bound what the AI may do). Neither is sovereign over the
  other — each bounds the other, under the human. This closed loop is what makes it
  safe *and* adaptive at once; nothing in the organism is sovereign except through
  the human.

  ```
        HUMAN  (directs — always, top of everything)
          │ governs
          ▼
         AI  ⇄  deterministic template code
       AI → code: adapts / controls the living software
       code → AI: invariants / guardrails bound what it may do
  ```
- **It infers intent and extrapolates at scale.** The user often cannot fully
  articulate their own intent (they lack the expertise, the language, or the
  vantage). So UMH must **infer the true intent** behind the imperfect expression
  — the reality they are actually reaching for — and **extrapolate it at scale**:
  project where that intent leads, what it will require, *who the user must become*
  for it. Serving the literal ask keeps the user where they are; inferring and
  extrapolating works *ahead* of their current self toward the self their intent
  implies.
- **A manifestation persists only through FIELD COHERENCE — of which becoming is
  one special case.** Not only *support* (fills weakness) — it **assists**
  (alongside), **executes** (materializes intent), and **expands** — resources
  *and*, when needed, the user. But the deeper law is not "you must become
  somebody" (too simple a layer): **reality is a coherent field, and a manifested
  change persists only if it is coherent with the surrounding region it lands in;
  a local change incoherent with its field is transient — the field reconverges
  and erases it.** The lottery-winner reverts not for lack of *becoming* but for
  **coherence failure across the instance**: the money was a local change dropped
  into a field (habits, relationships, systems, models, conditions) that didn't
  support it, so the field relaxed back to equilibrium. Growing the *person* is
  only the special case where the incoherent node **is** the self; the general law
  is field-wide (the incoherence may live in relationships, systems, resource
  preconditions, or unaccounted second-order effects). This is **P4
  (correspondence) and P9 (moving field) applied to *persistence of change***:
  a manifested reality is a new pattern that must correspond with its field, or the
  field's own correspondence-seeking dynamics undo it. So UMH must **model the
  field, not the variable; compute the *coherent configuration*, not the isolated
  change; and transform the region into coherence** — pulling whichever levers
  (resources, systems, *and sometimes the self*) make the intended reality hold.
  The anti-replacement guarantee survives in its true form: when the incoherent
  node is the user, growing them is *required*, so UMH cannot simply replace them.
  *Doc:* PHILOSOPHY/EPISTEMOLOGY frame "recursive human capability compounding" —
  the self-coherence case; field-coherence is the general law the docs do not yet
  state.
- **To serve the user, it must model the user.** You cannot support someone where
  they are weak, assist them well, expand the *right* resources, or grow them toward
  the *right* becoming without having modeled *who they are* — strengths,
  weaknesses, intent, nature. The **user model is the prerequisite for correct
  assistance**; no model → generic → wrong help. *Code:* user/agent modeling exists
  (`profile_runtime.py`, capability profiles in `role_contracts.py`); a unified user
  model is partial.
- **It does nothing the user doesn't intend — the human always directs.** Every
  transformation traces to the user's intent; the AI executes *directed* intent, it
  never *invents* intent. *Code:* **built and canonical** — `canonical_runtime.py`
  declares "the one canonical path from **operator intent**"; `CompositionEngine` is
  "intent → plan" with `CompositionIntent.source = "operator"` by default; and
  PHILOSOPHY.md: "the human is **sovereign in decision**."

### The metaphysical floor — UMH is a microcosm of reality

*(The why beneath the mechanism — the theory's stated grounding, not a code claim.)*

The deepest correspondence: **UMH is a microcosm of reality — built in reality's
own image, so its structure *is* reality's structure at smaller scale.** This is
the root of the Law of Correspondence (P4): the model can mirror *any* domain
because the organism is built from the same pattern reality itself is built from —
*as above, so below; UMH is the below.* It is the deepening of PHILOSOPHY.md §II
("Reality is Unity — Reality is one; there is no separation"): if reality is one
unified field, UMH is a legible microcosm of that field, and the user is a node in
it. Term for term:

| Reality (macrocosm) | UMH (microcosm) |
|---|---|
| Intent breathed into an embodied agent | The user's intent breathed into the organism (the user *is* the animating breath) |
| Agent: intent, in a body, in an environment, among other agents | Cell/agent: intent, in a runtime, in a device-environment, among other agents |
| We arrive **not remembering what we are** | The dormant organism (identity unbound until instantiated) |
| We are **not taught how reality works** | The un-onboarded system (no world model of *its* reality yet) |
| Drift toward incoherence without raised awareness | Projection drift, canon-rot, staleness — decays without governance |
| Raised awareness → coherence | Governance + reconciliation + correspondence-completeness → coherence |

**The human is the default-incoherent node.** We come into the world not
remembering what we are, placed among other agents, untaught in how reality works —
so *without deliberately raising conscious awareness we drift increasingly
incoherent, not coherent.* Coherence is not the natural state; it is an achievement
that takes **intent at the scale of the human being.** This refines the previous
point: field coherence is the general law, but in the human case it *almost always*
routes through the human's own coherence — not because the self is the only
variable, but because **the self is the node most reliably out of correspondence**,
since consciousness of how reality works is the one thing we are never given and
must earn.

**Therefore UMH is, at root, a consciousness instrument.** Because the microcosm is
*legible* where raw reality is not, directing it *teaches the user how reality
works* — correspondence, coherence, intent→manifestation made observable at a scale
a human can hold. Flourishing at its root is not more output or even more
capability: it is **remembering what you are and learning how reality works, so you
stop drifting and start cohering.** Governance toward flourishing → because
flourishing is coherence → coherence requires raised awareness → and UMH is a
legible microcosm of reality that cultivates it.

*Not-yet-hardcoded is a staged decision, not an oversight.* The flourishing telos
is deliberately **not hardcoded yet** because what flourishing means *at scale*
must be **scoped for the masses** before it is fixed — which is precisely why UMH
is **proprietary before public**: the proprietary phase (founder first, then design
partners) is where the flourishing telos is scoped and proven; the public phase
ships it governed toward flourishing *correctly for everyone*, not prematurely
hardcoded to one person's guess. *Status:* the telos is **undeclared in code and
philosophy** (governance is purely risk-based; `PHILOSOPHY.md` names four pillars,
not flourishing; nothing yet measures support/focus/growth of the user) — this is
the scoping work of the proprietary phase, and naming+measuring it is the first
frontier task of the objective function (P7).

## The nine principles

**1 · Isomorphic modeling of reality.** The model's structure corresponds to
reality's structure, so operating on the model operates on reality.
*Mechanism:* a reality model whose entity graph mirrors the domain, with
**correspondence-completeness as a measured metric**. *Gap:* `reality_model`
exists; correspondence-completeness is **not measured**.

**2 · Governed delegated semi-autonomy.** An agent is an employee **without
sovereign agency** — it has no irreducible self to be trusted, so its
trustworthiness *is* the governance envelope around it. Autonomy is always
partial, delegated (granted downward), and governed (bounded) — never full, never
sovereign. *Mechanism:* every action through `governed_mutation`; autonomy as a
**graduated grant** with an explicit ceiling that consumes track record. *Gap:*
the governed path exists; authority is **static policy** — no graduated
autonomy engine (verified: no `graduated`/`track_record` authority module;
authority is verification/certification-based).

**3 · Constructed, composed identity.** An agent arrives with no identity; its
identity — tools, skills, model, memory, knowledge, context, authority,
reports-to — must be **built from primitives and composed per task**, so the
constructed identity performs equal to or better than a human. The worker *is*
its assembled manifest. *Mechanism:* `RoleContract` is the manifest; composition
assembles it against a human-parity baseline. *Gap:* the manifest exists; **no
human-parity baseline / eval** (see [role-composition.md](role-composition.md)).

**4 · Law of Correspondence (the fractal).** *As above, so below.* The same
pattern repeats at every scale because each scale corresponds to the ones above
and below — marketing ⊃ facebook-ads ⊃ video-creative, same shape, different
zoom. The fractal is **forced** by the isomorphism requirement: an isomorphic
model of a fractal reality must itself be fractal. *Mechanism:* one recursive
**Capability Cell** primitive; composition = tree-descent to the depth the task
requires; each node activates in the cheapest mode that works. *Gap:* the
recursion primitive is **latent** — `RoleContract.spawn_permissions`
(`role_contracts.py:75`) is exactly the child-edge of the fractal — but it is
**not named or enforced as a recursive primitive**.

**5 · Mimicry, then transcendence.** Reality is the *scaffold*, not the ceiling.
Reality Mimicry searches a **matrix of reality-patterns across scales** and
selects the most optimal pattern given the full context; the system mimics
reality's proven organization to reach human-parity fast, then — under
governance — **may reorganize into a structure more efficient than reality's
own** once it discovers one. *Mechanism:* the pattern matrix + governed
self-reorganization of the system's own topology. *Gap:* **the matrix and the
self-reorganization loop are unbuilt**; mimicry today is implicit, not a search.

**6 · Total governance + total essentialism.** *Everything* is governed and
essential, to the granular detail — code, command, hook, YAML, `CLAUDE.md` — no
redundancy, no waste, one home each, because **the system's own repository is a
cell in the fractal, subject to the same laws as any capability deep in the
tree.** *Mechanism:* extend policy-as-code gates from code to **all artifact
types**, and a **principle registry** where each principle is stated once and
every projecting artifact is derived from or checked against it. *Gap:* the 16
pre-commit gates cover **code only** — **none scans `.claude/commands`, hooks, or
`CLAUDE.md` for essentialism/drift** (verified); and there is **no principle
registry** — principles are scattered across `CLAUDE.md`, `rules/`, gates, and
docs, the very redundancy this principle forbids. The canon-rot item
(`.claude/CLAUDE.md` still says "Universal Mastery Hierarchy") is literally a
principle-6 violation.

**7 · The optimum is an intersection, defined by an objective function.** There
is no context-free optimum — it lives at the intersection of **reality** and
**the user's instance of reality as an entity within it**. Instance Context is
therefore not hygiene; it is half the coordinate system the optimum is defined
in. *Mechanism:* an explicit **objective function** — maximize *(gap closed
between current and desired reality)* per unit of *(governed cost + human
friction)*, **in service of the human's flourishing** (the telos that orients the
scalar; without it "gap closed" could optimize against the human). *Gap:* the
inputs are modeled; **the scalar is not named, and its flourishing telos is
absent from code and philosophy** — governance today is purely risk/safety-based
(verified: zero `flourish`/`wellbeing`/`human-benefit` orientation in
`substrate/governance/`; `PHILOSOPHY.md` names Reality/Intelligence/
Personalization/Execution but not flourishing as the purpose).

**8 · Self-governance around a constitutional core.** The system governs itself
through **learn → operationalize → recurse → master**. But a self-modifying
governed system can recurse on its own governance. *Mechanism:* a **constitutional
core** — a small set of principles the self-improvement loop may never modify
(governance-before-execution, non-sovereign autonomy, the human-in-the-loop, the
objective function). The **human-in-the-loop IS the constitutional core**: because
the organism is only alive while coupled to its user (below), it cannot make
itself sovereign — it cannot make itself alive on its own. *Gap:* the core is
**not declared as immutable**; self-recursion has no fixed point.

**9 · Correspondence is asymptotic; act proportional to it.** Reality is unbounded
and moving, so the correspondence is never complete — it is always partial and
decaying. *Mechanism:* a **correspondence/freshness metric** that routes decisions
by how corresponded the model currently is (low → gather / defer to human; high →
act autonomously), and, at the social scale, **inter-instance conflict
resolution** across multiple users. *Gap:* the system treats full context as an
achievable state; it is an asymptote — **freshness-proportional action and
inter-instance resolution are unbuilt** (instance *isolation* exists; instance
*interaction* does not).

## Atom, engine, state, growth — the organism's mechanism

The nine principles reduce to four mechanical facts, each already present in code:

**The operational atom is the template — the system is deterministic recursive
mastery.** The template is the atom of *operation* (how work gets done), not of
the whole organism (which also has the world model, the signal engine, the dual
state below). Everything the organism *does* — agents, workflows, **and the code
itself** — is a *template*: the world model *operationalized*, made runnable.
Templating is how mastery is **canonized into guardrails** (see below), and the
LLM breathes life by filling the typed slots. So the deterministic operational
skeleton is a **recursive tree of templates, each a guardrail around canonized
mastery** — *deterministic* (fixed structure), *recursive* (templates within
templates = the fractal), *mastery* (each a proven competence). This unifies
Deterministic-First + the Operationalization Principle + the fractal.

*A template is an **Instantiate-able Plug & Play** unit, decomposed by first
principles into two parts:*
- **Invariants** — what is *always true* for this pattern, at every instance: the
  fixed structure, the guardrail, the canonized mastery. (Starting a business:
  *there must be* a business model, customers, a value exchange, capital flow.)
- **Variables** — the typed slots decided *per instance* from the user's context.
  (Starting a business: *which* business model.)

First principles is the **mapping tool** (invariant = never varies; variable =
always decided). This is `template = f(invariants, variables, context)`.

*Each variable is filled by its own **nested Variable Decision-Making Template**
— not an LLM guess.* The decision template **stacks every factor bearing on that
decision into a matrix**, weighs them against the user's full context, and
computes the optimal value. It is the Reality-Mimicry matrix (P5) and objective
function (P7) applied at the variable level, and it nests (a decision template may
contain variables with their own decision templates — the fractal, inside the
template). Worked example:

```
Template "Starting a business"  (plug & play operational atom)
├─ Invariants: business model · customers · value exchange · capital flow …
└─ Variable: Business Model
   └─ Variable Decision-Making Template  (nested; fills the slot)
      └─ Matrix of stacked factors: personality SWOT · career timing ·
         current competitive advantage · capital available · … every factor
         that bears on the decision
      → stack + weight against full user context → OPTIMAL business model
```

This is what makes *"the optimal decision at the intersection of reality and the
user's instance"* **computable** rather than aspirational — and it is
democratization at the decision level: the mastery of *how to decide* ships in
the template; the user supplies only context. *Code:* the invariant/variable split
is **built** — `RealityTemplate` (`substrate/templates/reality_template.py:203`) is
literally `f(invariants, variables, context)`, with `TemplateInvariant` (line 135,
*"an invariant without a testable assertion is a wish"*, carrying a pointer to the
test that pins it to reality) and `TemplateVariable` (line 153, a typed
instance-free slot). Two homes: `RealityTemplateRegistry`
(`substrate/templates/registry.py`, the metamodel of provable patterns) and
`substrate/organism/template_registry.py` `TemplateRegistry` (runtime executable
actions). *Gap:* the **nested Variable Decision-Making Template is unbuilt** —
weighted rankers exist (`reliability_weighted_ranker.py`) but rank
capabilities/reliability, not *fill a template variable by stacking all bearing
factors into a context-matrix and computing the optimal value*. This is the
missing organ that turns a declared variable into an optimally-decided one.

*One object, three phases (memory → capability → infrastructure).* The template is
the same object in three states of being, depending on when you look at it — this
is the software isomorph of how a learned skill lives in a mind:
- **At rest → knowledge / memory.** A dormant template *is* a unit of the
  organism's **world model** — its understanding of how that piece of reality
  works (a "starting a business" template *is* the organism's knowledge of
  business-starting, held where its model of reality is held). This is why the
  template is the *operational* atom specifically: it is the **executable face of a
  world-model unit** — knowledge and operation are the same object from two sides.
- **On instantiation → operational capability.** The trigger wakes the dormant
  knowledge into a runnable capability: invariants fixed, variables filled by the
  user's context via the nested decision-matrix. Memory *activates into* capability.
- **After execution → infrastructure.** What ran lays down as structure the
  organism now stands on and reuses. Capability *settles into* infrastructure.

(Reality-mimicry check: a learned skill — riding a bike — is *memory* when idle,
*capability* the moment you mount *this* bike on *this* hill, *infrastructure* once
mastered and built upon. The template mimics exactly this.)

*Templated code = living / adaptive software.* Because the code itself is templated
(invariants + variables + decision-matrix), its decisions are **not frozen at
author-time** — they are live variables filled by the organism's *current* world
model. When reality changes → the world model updates → the variables re-fill →
**the software re-decides itself without being rewritten.** Static code is dead
(decided once by a programmer); templated code is living (re-decided continuously
from a world model that keeps corresponding to reality). This is principle 5
(mimicry-then-transcendence) reaching all the way down into the source: the
organism can reorganize its own code because its code is *templated knowledge*, not
frozen instructions. **This stays non-sovereign via a mutual loop under the human:**
the AI governs the code (adapts the living software) *and is simultaneously governed
by* that same deterministic template code (its invariants bound what the AI may do);
the human governs the AI. Neither AI nor code is sovereign over the other — each
bounds the other, under the human (full diagram in *The purpose* above). The code
is alive but never self-willed.

*Endgame — canonize all of reality.* The canon world model is not meant to stay a
seed. The intent is to ingest and canonize the **totality of human modeling of
reality** — books, the internet, all of history to the present, everything the
organism can be trained on — into the reality model *as templated, provable
knowledge*. Every book is human-modeled reality; every field is a set of
invariant/variable patterns humans discovered. Because templates *run*, the
organism would not merely *know* what humanity knows — it could *do* it, governed
and instantiated to any user's context. That is the "super-general" in governed
ASGI made concrete: **generality = the breadth of canonized reality; the ceiling
rises as ingestion approaches the totality of human knowledge.**

*Code — what is built vs intended.* The invariant/variable split is **built**
(`RealityTemplate`, `substrate/templates/reality_template.py:203`). The governed
write-and-promote pipeline the endgame needs is **built**: two converging paths —
`CanonicalRealityWritePath` (`substrate/reality_model/canonical_reality_write.py`,
validates shape/source/confidence for non-execution observations) and
`substrate/memory/canonical_write.py` (execution-domain writes with **candidate
generation + promotion**), both converging at `InstanceRealityModel.record()`.
**Gaps (specific, not general):** (1) the template subsystem
(`substrate/templates/`) and the world model (`substrate/reality_model/`) are
**separate — the template↔world-model wiring that makes a template a world-model
unit is not built** (only the invariant's "pointer to the test that pins it to
reality" seeds the link); (2) the write pipeline targets `InstanceRealityModel`
(per-user) — the **canon corpus that ingests books/internet/history is
stated-future** built on that pipeline; (3) living/adaptive software follows from
(1) and is therefore also **conceptual** until the wiring lands.

**The engine is signal orchestration — three doors, one hallway.** From the
outside, everything crossing into the organism is one of three things — an
**adapter** (connection to an external system), a **user** (the entity served),
or **reality data** (to model, ingest, reconcile). But to the system, at the
deepest level, **all three are the same thing: signal to be orchestrated.** The
three-way taxonomy is ingress *classification*; signal is ingress *unification*.
One governed path (signal → govern → execute → learn) processes all three
identically; adapter/user/reality are just signal *sources*. *Code:*
`SignalEnvelope` (`substrate/types.py:48`) is the canonical ingress type — this is
already the architecture.

**The state is a dual world model — canon separated from instance.** The organism
runs **two world models at once**: the **canon** world model (shipped, universal,
masterful — the isomorphic approximation of reality-*in-general*) and the
**user-instance** world model (this user's specific reality). The reconciler runs
*between* them. This is the mechanical form of democratization-plus-
personalization: canon is shared (mastery for all), instance is per-user
(personalized), kept separate by construction (Instance Context Law elevated to
the product's two halves). *Code:* **already built** — `substrate/reality_model/`
has `canonical.py` **and** `instance.py`, and `reality_intelligence.py:61-66`
takes an `instance_model` and merges canon + instance evidence chains
(`source_type="instance_observation"`, line 594).

**Growth is maturation, not configuration.** The organism ships preloaded with
**canon** — existing agents, workflows, a knowledge base, and a reality model: a
working approximation that already isomorphically mirrors reality. It ships
*already masterful*, and **that is how it democratizes: the mastery is in the box,
not in the user's head.** The user supplies *context*, not *expertise* — governed
always, but **no user expertise required.** Adding a capability is a **maturation
event**, not a config screen: adapter integration is one click / one vocal
approval for the user (like authorizing any app), but behind the surface the
organism **matures toward that capability until completion — integration and
mastery of execution.** Effortless on the surface (democratization), a real
grow-a-new-organ-and-master-it process underneath. *Acceptance test for the whole
product:* can a user with zero technical expertise, right after onboarding, have
the organism close a real reality gap on their behalf — governed — **without
assembling agents, writing workflows, or configuring capability?** Yes → canon +
instantiation works; no → it is a framework, not a democratized organism.

## The Capability Cell (the fractal made concrete)

Role and Skill are the **same recursive primitive at two levels of granted
autonomy**. A capability node has a boundary (what it owns), children
(sub-capabilities — the recursion, carried by `spawn_permissions`), a manifest
(tools/knowledge/model/authority — the `RoleContract` fields), and one axis:

- **Skill mode = zero autonomy granted** — deterministic, cheap, no model; it
  *cannot decide*. (A `skills/` package.)
- **Agent mode = semi-autonomy granted to a governed ceiling** — a model is bound;
  it reasons and may delegate to its children.

*"Is video-creative an agent or a skill?"* → **it is one cell; the task grants it
0 autonomy (skill) or bounded autonomy (agent).** The task decides the descent
depth and the mode; the system expends exactly as much structure as the slice of
reality demands — which is principle 6 (essentialism) derived, not imposed. The
standing hierarchy (System Orchestrator → Device → Executor) is just the **top of
the fractal held resident as agents**; ephemeral task agents are **cells activated
deep and torn down**. Same primitive; different residency.

**The recursion governors (or it becomes the thing that spins all night making
nothing):** a depth/fan-out budget per task (P7's cost term), a bias toward
skill-mode (Deterministic-First as the activation rule), and a reports-to that is
**inherited down the tree** (`escalation_rules`) so a cell four levels deep still
escalates to the human.

## Lifecycle — born once, then ambient (the Jarvis property)

Life is breathed in **once**, not per session. A living thing you must restart
each morning is a tool, not an organism — so *"nothing closes my reality gap
overnight"* **is the same failure as "it isn't actually alive."** Three distinct
events:

1. **Installation → the canon organism arrives, alive.** The substrate,
   heartbeat, and workforce loop exist and can run — and it ships **preloaded with
   canon**: existing agents, workflows, a knowledge base, and a reality model
   (mastery in the box). Alive and masterful, but *generic* — mirroring
   reality-in-general, not yet *this* user's reality; unbound, purposeless. *Code:*
   `install.sh` is **broken** (literal `[repo]` URL; `setup.sh` imports a
   nonexistent `runtime.setup_wizard`) — **birth itself fails today**.
2. **Onboarding → instantiation (canon specialized onto the user).** Not a cold
   start — the organism already ships with a canon world model, so instantiation
   is the **canon becoming *this user's* organism** by receiving their context.
   Onboarding performs **personalization** (loads the user's identity +
   instance-of-reality: current + desired) and **adapter integration** (connects
   the organism's *perception and actuation* to the user's real systems — GWS,
   Discord, GitHub, devices). Together these populate the **user-instance world
   model**, and the **reconciler begins closing the delta between the canon
   (generic) model and this user's actual reality** read through the newly-
   integrated adapters. The user model is the **specialization function** that
   maps canon-mastery onto this reality; the reconciler's first job is reconciling
   canon-reality against this-user's-reality. Without adapters the reconciler is
   blind: no perceived current reality → no computable delta → no metabolism (a
   second reason nothing works overnight). *Code:* the dual world model
   (`reality_model/canonical.py` + `instance.py`), Instance Context storage, and
   adapters **exist**; the onboarding flow that *binds* them — personalization →
   integration → user-instance model → reconciler on the delta — is **absent as an
   event**.
3. **Ambient life → automatic continuity forever after.** Once instantiated the
   organism is **always-on, always-present, always metabolizing** toward the gap,
   with continuity across sessions/devices/time. The user never restarts it, never
   re-briefs it — like Tony never boots Jarvis. *Code:* **this is the entire
   [terminal-fabric.md](terminal-fabric.md) gap** — loops are session-scoped
   (`start-loops`: "runs until session closes"), continuity is snapshot-diff for
   the human (not auto-resume), nothing runs ambiently. The organism is **born and
   killed daily instead of born once and living**.

**The build, in one sentence:** make UMH an organism **born once at install**
(fix `install.sh` → a service-hosted living body), **instantiated once at
onboarding** (the binding flow: personalization + adapter integration → user
model → reconciler on the real instance), and **ambiently alive thereafter**
(service-hosted supervisor + automatic continuity + standing-intent reconciliation
= the Jarvis property). **Overnight gap-closure is simply the proof of life.**

## Why this theory generates the whole system

Full context → complete correspondence (P1, P4) between the model and *this
user's* reality (P7) → the optimal decision becomes *legible* rather than guessed,
because a complete isomorphism has the same structure as the reality the decision
acts on → execute it under governed semi-autonomy (P2) via a composed identity
(P3) → learn and operationalize (P8) → the correspondence deepens and may
transcend reality's own organization (P5) → all of it essential and governed to
the last artifact (P6), acting proportional to how corresponded it currently is
(P9). Every other page — [vision-alignment.md](vision-alignment.md),
[canonical-registry.md](canonical-registry.md), [build-doctrine.md](build-doctrine.md),
[role-composition.md](role-composition.md), [terminal-fabric.md](terminal-fabric.md)
— is a consequence of this theory made mechanical.

## The frontier (the eight gaps in the theory, not just the code)

Beyond the per-principle gaps above, six items are the *theoretical* frontier —
name them or the system cannot become what it intends: **(1)** the objective
function (P7) — what "optimal" maximizes; **(2)** the principle registry (P6) —
one source per principle, artifacts derived from it; **(3)** the constitutional
core (P8) — the immutable fixed point of self-recursion; **(4)** inter-instance
conflict resolution (P9) — whose optimum when instances compete; **(5)** the
correspondence/freshness metric (P1, P9) — how the organism knows how alive-to-
reality it currently is; **(6)** the **nested Variable Decision-Making Template**
(the operational atom) — the factor-matrix mechanism that fills each template
variable optimally from the user's full context, making the objective function of
(1) *computable at the variable level*; **(7)** the **template↔world-model wiring**
— making a template genuinely a *unit of the world model* (memory that runs), the
prerequisite for living/adaptive software and the canon corpus; **(8)** **field-coherence
persistence** — model the *field* not the variable, compute the coherent
configuration, and transform the region (resources, systems, and — as a special
case — the self) so a manifested change *holds* rather than reverts; infer-intent
+ extrapolate-at-scale feed it. The docs frame self-capability compounding but not
field-coherence. These are found *by the theory* and
must be verified against reality as they are built.

## See also

[role-composition.md](role-composition.md) · [terminal-fabric.md](terminal-fabric.md) ·
[vision-alignment.md](vision-alignment.md) · [canonical-registry.md](canonical-registry.md) ·
[build-doctrine.md](build-doctrine.md) · [index.md](index.md)
