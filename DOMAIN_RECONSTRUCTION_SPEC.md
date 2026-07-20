# UMH Domain Reconstruction Specification

**Version: 0.3.0**
**State: DRAFT**
**Parent authority: EPISTEMOLOGY.md**
**Relationship to PLATFORM_SPEC.md: additive — no amendment**

This document specifies UMH's federated domain-reconstruction system and the v1
Grounded Self-Model slice. It is governed by EPISTEMOLOGY.md and does not restate
it. It is additive to PLATFORM_SPEC.md v1.0.0 (FROZEN): it introduces no new
required field on any frozen contract, changes no frozen signature, and adds no
new canonical mutation, event domain, or persistence path. In PLATFORM_SPEC's
versioning vocabulary (§Versioning Policy), every integration point named here is
either a MINOR additive extension through a published Extension Point (§13) or a
non-executing contract awaiting its own future RFC. Promotion of this spec past
DRAFT follows PLATFORM_SPEC.md's Breaking Change Process.

Normative language uses **MUST / SHOULD / MAY** (RFC 2119 sense). Sections marked
**Normative** state binding requirements; sections marked **Commentary** are
explanatory and bind nothing.

## Conformance summary

| Concern | v1 posture | Binding |
|---|---|---|
| Ontology layer of this spec | L4 semantic-grounding over L1 reality + L2 metamodel | `.claude/rules/ontology-layers.md` |
| New contracts | implemented in v1 — `substrate/understanding/reconstruction/` (run-scoped instance artifacts only) | new-in-v1 |
| Reality persistence | **none new** — read-through only | `substrate/reality_model/` unchanged |
| Mutation routing | **untouched** — `UMH_CANONICAL_RUNTIME_ROUTING` not read or set | `substrate/organism/canonical_runtime.py` |
| Self-model replacement | **none** — `SelfModel` / `RealityIntelligenceEngine` not replaced | additive |
| Evidence standard | facet vector, never a single tier | §4.7 |
| Final status vocabulary | OPERATIONAL / PARTIALLY_OPERATIONAL / INSUFFICIENT_EVIDENCE / FAILED | §4.12 |

---

## 4.1 Purpose and non-goals

**Commentary.** EPISTEMOLOGY.md establishes that reality is the singular source of
knowledge, that every observation is evidence, every model a hypothesis, and every
outcome updates the organism's approximation of reality (EPISTEMOLOGY.md, Part I —
"Reality as Source", "The Governing Law"). It also establishes the acquisition
pipeline (Reality → Observe → Extract Evidence → Decompose → … → Verify → Refine →
Reality) and the one canonical spine every surface must enter. This specification
does not restate those; it specifies the **subsystem that turns a bounded slice of
reality into an evidence-grounded, provenance-carrying, falsifiable model** — the
concrete machinery behind "Approximate reality" (EPISTEMOLOGY.md Part I, function
2) and "Continuous Refinement" (Part III).

Domain Reconstruction is a **federation** of cooperating parts, not a monolith:

1. **Universal Reality Kernel** — a fixed 20-concept grammar every reconstruction
   specializes but never replaces (§4.4).
2. **Evidence & Provenance Fabric** — for every derived assertion, which source,
   which activity, which code/model version, when, and what later contested it
   (§4.5).
3. **Claim & Belief Ledger** — the append-preserving record separating what a
   source *claims* from what UMH *believes* and why (§4.3, §4.6).
4. **Temporal Entity-Event representations** — bitemporal (valid time vs record
   time) entities and events (§4.6).
5. **Mechanism representations** — causal statements classified by typed
   evidence basis, never promoted by repetition (§4.9).
6. **Partitioned domain models** — separate-but-linked legal / operational /
   software / runtime / participant-native views of the same reality (§4.8).
7. **Domain Reconstruction Orchestrator** — the iterative, backtracking contract
   that drives a reconstruction from intent to versioned artifact (§4.11).
8. **Evaluation & Falsification** — five evaluation classes and a closed set of
   permitted final statuses (§4.12).
9. **Governed future-improvement contracts** — the adapter points through which
   later, separately-RFC'd packets extend this subsystem (§4.14).

**Normative — v1 non-goals.** v1 MUST NOT attempt, claim, or be represented as
providing:

- a universal ontology of all domains;
- reconstruction of arbitrary external domains (v1 reconstructs UMH's own
  self-model; see §4.14);
- simulation of reconstructed models (simulation stays in
  `substrate/reality_model/simulation.py`, out of scope here);
- automatic causal discovery (mechanisms are proposed, ranked, and evidenced —
  never auto-inferred as established; §4.9);
- autonomous promotion of a model to canonical status;
- autonomous modification of code;
- any **new** canonical reality persistence path (v1 reads through existing
  reality-model surfaces; §4.14);
- multi-agent consensus treated as truth (§4.13);
- exhaustive parsing of generated data, logs, or vendored dependencies
  (adaptive granularity governs coverage; §4.10).

---

## 4.2 Four model classes

**Normative.** Every reconstructed record belongs to exactly one of four model
classes. The classes have **distinct semantics** but **share stable identifiers**,
so the same real entity may be described in more than one class without collision.

| Class | Answers | Semantics |
|---|---|---|
| **Descriptive** | *What is / what exists* | Observed structure and state |
| **Epistemic** | *What is claimed / believed and how strongly* | Claims, beliefs, contradictions, confidence |
| **Mechanistic** | *Why / how one thing affects another* | Causal statements with an evidence basis |
| **Predictive-control** | *What will happen / what to do* | Forecasts, scenarios, plans, proofs |

**Normative.** No record MAY silently change model class. A change of class is a
new record that supersedes the old one through the provenance chain (§4.5), never
an in-place mutation of the same record's class field.

**Normative — home map.** Each class maps to an existing UMH home; v1 adds a
ledger and a typed causal-basis classification but no new persistence store:

| Class | UMH home(s) | Status |
|---|---|---|
| Descriptive | `substrate/reality_model/` (`CanonicalRealityModel`, `InstanceRealityModel`) + `substrate/organism/reality_graph.py` (`RealityGraph`) | existing |
| Epistemic | `substrate/organism/contradiction_engine.py` (`ContradictionEngine`, `ContradictionReport`) + the new reconstruction ledger (§4.3) | existing + new-in-v1 |
| Mechanistic | `CausalSupportRecord` typed basis classes (new, §4.9) over `RelationshipType` / `CausalRole` in `substrate/types.py` | new-in-v1 over existing |
| Predictive-control | `substrate/intelligence/runtime.py` (`Prediction`, `IntelligenceRuntime`) + `substrate/organism/prediction_portfolio_runtime.py` (`PredictionPortfolioRuntime`) + `substrate/organism/scenario_intelligence_engine.py` (`ScenarioIntelligenceEngine`) + `substrate/organism/proof_runtime.py` (`ProofRuntime`) | existing |

**Commentary.** This four-way split is why reconstruction can hold "the vendor's
website claims the service is live" (epistemic) and "no process was observed
answering on the port" (descriptive) at the same time without contradiction — the
contradiction is then a *first-class epistemic record* produced by the
`ContradictionEngine`, not a bug.

---

## 4.3 Ratified semantics

**Normative.** The following terms have fixed meaning in this spec. Where a UMH
type already realizes a term, reconstruction MUST bind to it rather than define a
parallel type (Type Coherence Law, `.claude/rules/type-coherence.md`). New v1
contracts live in a single new module,
`substrate/understanding/reconstruction/contracts.py`, and are wired ONLY by the
v1 Grounded Self-Model builder (run-scoped instance artifacts; no canonical
write path).

| Term | Meaning | Binding | Module | Status |
|---|---|---|---|---|
| reality | the external operational world (L1) | `CanonicalRealityModel` / `InstanceRealityModel` | `substrate/reality_model/canonical.py`, `instance.py` | existing |
| artifact | a produced/observed thing carrying content | `RealityEntity` | `substrate/organism/reality_graph.py` | existing |
| source | where an observation came from | `SourceRecord` | `substrate/understanding/reconstruction/contracts.py` | new-in-v1 (implemented) |
| observation | a recorded perception of reality at a time | `ObservationRecord` (new) / `InstanceObservation` (existing store) | `.../reconstruction/contracts.py`; `substrate/reality_model/instance.py` | new-in-v1 + existing |
| claim | an assertion *made by a source*, not yet believed | `ClaimLedgerEntry` | `.../reconstruction/contracts.py` | new-in-v1 (implemented) |
| evidence | an observation supporting an assertion | `RealityEvidence` | `substrate/reality_model/reality_query.py` | existing |
| counterevidence | an observation contradicting an assertion | `Contradiction` | `substrate/organism/contradiction_engine.py` | existing |
| belief | UMH's own graded assertion, derived from evidence | `DerivedBelief` | `.../reconstruction/contracts.py` | new-in-v1 (implemented) |
| model | a coherent set of records describing a domain slice | `CanonicalPattern` / `WorldModelEntry` | `substrate/reality_model/canonical.py`; `substrate/understanding/world_model/world_model.py` | existing |
| hypothesis | a model held as provisional | `LearnedPattern` | `substrate/intelligence/runtime.py` | existing |
| mechanism | a causal relation with an evidence basis | `CausalSupportRecord` over `RelationshipType`/`CausalRole` | `.../reconstruction/contracts.py`; `substrate/types.py` | new-in-v1 over existing |
| prediction | a forecast of a future outcome | `Prediction` | `substrate/intelligence/runtime.py` | existing |
| goal | a desired outcome state | `PrimitiveType.GOAL` | `substrate/types.py` | existing |
| plan | an ordered set of actions toward a goal | `FutureScenario` (planning view) | `substrate/organism/scenario_intelligence_engine.py` | existing |
| action | a governed operation | `ActionEnvelope` | `substrate/organism/action_envelope.py` (PLATFORM_SPEC §2) | existing |
| outcome | the result of an action | `PrimitiveType.OUTCOME`; `ProofEvidence` | `substrate/types.py`; `substrate/organism/proof_runtime.py` | existing |
| trace | the recorded path of an execution | `TraceEvent` | `substrate/types.py` (`substrate/execution/trace.py` persists) | existing |
| proof | evidence that an outcome occurred | `ProofPackage` | `substrate/organism/proof_runtime.py` | existing |

Additional new-in-v1 contract records (all in
`substrate/understanding/reconstruction/contracts.py`, implemented in v1): `SourceRecord`,
`ObservationRecord`, `ClaimLedgerEntry`, `DerivedBelief`, `IdentityResolution`,
`CausalSupportRecord`, `ActivityRecord`.

**Commentary — naming.** `contradiction_engine.py` already defines `Claim` and
`Observation` dataclasses for its own contradiction detection. The reconstruction
records are deliberately named `ClaimLedgerEntry` and `ObservationRecord` so no new
homonym enters `canonical_types.py` and the type-divergence gate
(`scripts/check_type_divergence.py`) stays green.

**Normative — the load-bearing invariant.**

> A desired state, a design proposal, a roadmap item, or a documented claim MUST
> NOT be stored as an observation that the thing exists.

A roadmap sentence is a `ClaimLedgerEntry` with source = the roadmap document. A
running process answering a health check is an `ObservationRecord`. A `DerivedBelief`
that "the service is operational" MUST cite observations, not claims, as its
supporting evidence. Violating this is the single failure mode this spec exists to
prevent: intent laundered into fact.

## 4.4 Universal Reality Kernel

**Normative.** The kernel is a fixed grammar of 20 concepts. Every reconstructed
domain model **specializes** the kernel and MUST NOT replace it. The concepts are
**not** forced into one Python module — each binds to wherever UMH already realizes
it. A domain model adds specializations (subtypes, fields, constraints) under a
kernel concept; it never introduces a 21st top-level concept without an amendment
to this section.

| # | Kernel concept | UMH binding | Canonical module | v1 conformance |
|---|---|---|---|---|
| 1 | Entity | `RealityEntity`; `OntologicalCategory.ENTITY` | `substrate/organism/reality_graph.py`; `substrate/types.py` | existing |
| 2 | Event | `TraceEvent`; `OntologicalCategory.EVENT` | `substrate/types.py` | existing |
| 3 | State | `PrimitiveType.STATE` | `substrate/types.py` | existing |
| 4 | Process | `OntologicalCategory.PROCESS` | `substrate/types.py` | existing |
| 5 | Agent | `RealityEntityType` (agent kinds); identity model | `substrate/organism/reality_graph.py`; PLATFORM_SPEC §19 | existing |
| 6 | Resource | `PrimitiveType.RESOURCE` | `substrate/types.py` | existing |
| 7 | Capability | `WorldCapability`; Capability Model | `substrate/organism/world_model.py`; PLATFORM_SPEC §20 | existing |
| 8 | Relation | `RelationshipType`; `RealityRelation` | `substrate/types.py`; `substrate/organism/reality_graph.py` | existing |
| 9 | Observation | `ObservationRecord` (new); `InstanceObservation` | `.../reconstruction/contracts.py`; `substrate/reality_model/instance.py` | new-in-v1 + existing |
| 10 | Claim | `ClaimLedgerEntry` (new) | `.../reconstruction/contracts.py` | new-in-v1 |
| 11 | Source | `SourceRecord` (new) | `.../reconstruction/contracts.py` | new-in-v1 |
| 12 | Evidence | `RealityEvidence`; `WorldEvidence` | `substrate/reality_model/reality_query.py`; `substrate/organism/world_model.py` | existing |
| 13 | Mechanism | `CausalSupportRecord` (new) over `CausalRole` | `.../reconstruction/contracts.py`; `substrate/types.py` | new-in-v1 over existing |
| 14 | Action | `ActionEnvelope`; `PrimitiveType.ACTION` | `substrate/organism/action_envelope.py`; `substrate/types.py` | existing |
| 15 | Outcome | `PrimitiveType.OUTCOME`; `ProofEvidence` | `substrate/types.py`; `substrate/organism/proof_runtime.py` | existing |
| 16 | Constraint | `PrimitiveType.CONSTRAINT` | `substrate/types.py` | existing |
| 17 | Rule | governance laws; `GovernanceVerdict` | `substrate/types.py` (`substrate/control_plane/governance.py`) | existing |
| 18 | Risk | `RiskClass`; risk fields on `ActionEnvelope` | `substrate/types.py`; `substrate/organism/action_envelope.py` | existing |
| 19 | Time | `TemporalMode`; `PrimitiveType.TIME` | `substrate/types.py` | existing |
| 20 | Location | `RealityEntity` properties (node/host); node identity | `substrate/organism/reality_graph.py`; `infra/device_registry.json` | existing |

**Commentary.** The kernel is why a reconstruction of "UMH's own runtime" and a
future reconstruction of "an external sales domain" would share a spine: both are
Entities related by Relations, asserted through Claims from Sources, believed on
Evidence, moved by Actions producing Outcomes under Constraints, Rules, and Risk,
across Time and Location. Only the specializations differ.

---

## 4.5 Provenance

**Normative.** The Evidence & Provenance Fabric aligns conceptually with W3C PROV.
No RDF or OWL implementation is required or permitted in v1 — the repo does not
require a triplestore, and adding one would violate the additive posture.

| PROV concept | Reconstruction realization |
|---|---|
| **Entity** (PROV) | a source artifact or a derived assertion — `SourceRecord`, `ObservationRecord`, `DerivedBelief` |
| **Activity** | acquisition / extraction / transformation / evaluation — `ActivityRecord` |
| **Agent** (PROV) | human / model / script / service / institution that ran the activity |

**Normative.** Every derived assertion (`ObservationRecord`, `DerivedBelief`,
`CausalSupportRecord`, `IdentityResolution`) MUST be able to answer:

1. **which source** it came from (`SourceRecord` reference);
2. **which activity** produced it (`ActivityRecord`: acquisition, extraction,
   transformation, or evaluation);
3. **which code/model version** ran that activity (git SHA and/or model id);
4. **when** (valid time and record time, §4.6);
5. **what later evidence** contested or superseded it (supersession link).

An assertion that cannot answer (1)–(4) MUST NOT be stored as belief; it may be
stored as an unattributed claim awaiting a source, but never promoted.

**Commentary.** This mirrors PLATFORM_SPEC §17 (State Model) — Desired/Observed/
Actual/Verified are distinguished there; provenance is how reconstruction keeps
those distinct at the record level rather than the system level.

---

## 4.6 Temporal semantics

**Normative.** Reconstruction is **bitemporal**. Every temporal record carries:

- **valid_time** — when the fact was true in reality;
- **record_time** — when UMH recorded it.

Valid time MAY be an instant, an interval, open-ended (still true / not yet ended),
or **unknown** (recorded as such, never guessed). Record history is
**append-preserving** (MUST): a correction adds a new record and supersedes the
prior one; it never overwrites it. This aligns with PLATFORM_SPEC §17/§18
(Historical state is immutable and append-only) and binds to the existing
append-only `InstanceRealityModel` store and the append-only `ExecutionJournal`.

**Commentary.** Bitemporality is what lets reconstruction say "we believed X from
record_time T1 to T2, and X was valid in reality from V1 to V2" — the two axes
diverge whenever UMH learns late, and the divergence is itself evidence about
observation latency.

---

## 4.7 Evidence facets and implementation maturity

**Normative.** Implementation maturity is described by **12 facets**, which are
**NOT exclusive tiers**. A component does not "reach tier 7"; it accumulates a
**maturity vector** derived from facet-bearing observations. The facets:

`declared`, `specified`, `source_present`, `importable`, `unit_tested`,
`integration_tested`, `deployment_configured`, `deployed`, `running`, `reachable`,
`live_path`, `outcome_verified`.

Each facet is set only by an `ObservationRecord` whose activity actually
established it (e.g. `running` requires an observation of a live process, never a
config file that *would* start one). Facets are independent: a component MAY be
`deployment_configured` without being `running`, and `source_present` without being
`importable`.

**Normative worked example.**

> A service `os-widget` has: a paragraph in a roadmap (`declared`), a spec section
> (`specified`), a Python module on disk (`source_present`), and a Docker service
> block with env and ports (`deployment_configured`). No observation has recorded a
> process answering on its port. Its maturity vector is
> `{declared, specified, source_present, deployment_configured}` and explicitly
> **not** `{running, reachable, live_path, outcome_verified}`. A reconstruction
> that reports `os-widget` as "operational" is FAILED (§4.12): it asserted an
> outcome facet no observation supports. The correct report is
> PARTIALLY_OPERATIONAL with the missing facets named.

This is the §4.3 invariant applied to maturity: configuration is a claim about
intent; running is an observation of reality.

---

## 4.8 Ontology pluralism and identity

**Normative.** A single real entity MAY have multiple **separate-but-linked**
representations: legal, operational, software, runtime, and participant-native. A
reconstruction MUST NOT collapse these by default; it links them and records why.

Identity decisions produce one of four verdicts, each evidence-backed and
supersedable (`IdentityResolution`, new-in-v1):

- **merge** — two representations are the same entity;
- **link** — related but distinct;
- **remain_separate** — deliberately not merged;
- **unresolved** — insufficient evidence to decide.

**Normative.** Every identity verdict MUST cite the evidence behind it and MUST be
supersedable by later evidence (§4.5, §4.6). An `unresolved` verdict is a valid,
first-class state — it MUST NOT be silently coerced to `merge` to make a model look
complete.

**Commentary.** This binds to `RealityGraph`'s entity/relation model: links are
`RealityRelation`s; a `merge` verdict is the reconstruction-level decision that two
`RealityEntity` ids denote one thing, recorded with its evidence rather than
performed destructively.

---

## 4.9 Mechanisms and causality

**Normative.** Causal support is classified into **seven TYPED evidence
classes**. The classes are distinct KINDS of evidence, **not a globally ordinal
ladder**:

- **reported causal statement** — a source asserts X causes Y;
- **hypothesized mechanism** — a plausible pathway is proposed;
- **temporal association** — X precedes Y repeatedly;
- **statistical estimate** — measured association with magnitude;
- **quasi-experimental** — natural experiment / discontinuity;
- **experimental** — controlled intervention;
- **formal dependency** — a provable structural dependency (e.g. import graph,
   type dependency).

A `formal` basis proves a formal relation *within a system* (authoritative for
an import edge) but is not globally "stronger" than experimental evidence, and
experimental evidence can be internally weak. Validity is therefore modeled
**per dimension** on each record — internal validity, external validity,
reproducibility, formal soundness — each recorded only when actually assessed,
never guessed.

Each mechanism record (`CausalSupportRecord`, new-in-v1) annotates an existing
`RelationshipType` (`CAUSES`, `ENABLES`, `CONSTRAINS`, …) / `CausalRole`
(`CAUSE`/`EFFECT`/`CONDITION`/…) edge from `substrate/types.py` with its basis
class, its assessed validity dimensions, and the evidence for them.

**Normative.** Textual repetition NEVER changes a basis class. Ten sources
reporting "X causes Y" remain a *reported causal statement* with ten citations —
they do not become an established causal relation. Reclassification requires
evidence of the target class's kind. This is the causal form of the §4.3
invariant.

**Commentary.** Formal dependency is the one class reconstruction can often
attain directly and cheaply for software domains — an import edge is a provable
dependency — which is why the v1 self-model slice (§4.14) leans on it.

---

## 4.10 Adaptive granularity

**Normative.** Reconstruction expands detail where decision value is high and stops
where it is not. Expand a region when any of these is high: **decision
sensitivity**, **uncertainty**, **contradiction density**, **failure cost**,
**dependency centrality**, or **security impact**. Stop expanding when the expected
decision value of further detail no longer justifies its acquisition cost.

**Normative.** Every deliberately **omitted region MUST be recorded** — as a
bounded gap with the reason it was not expanded (`WorldGap` binding,
`substrate/organism/world_model.py`). Silent omission is prohibited: a model that
stopped at a boundary must say so, so the boundary is visible to the next
reconstruction and to evaluation (§4.12).

**Commentary.** This is the operational answer to EPISTEMOLOGY.md's "Why This Is
Not Omniscience": reconstruction is disciplined approximation, and the discipline
is that its own blind spots are first-class records, not absences.

---

## 4.11 Orchestrator contract

**Normative.** The Domain Reconstruction Orchestrator has **15 responsibilities**,
executed **iteratively with backtracking** — it is NOT a fixed linear compiler:

1. receive intent;
2. define competency questions (what the model must be able to answer);
3. discover boundaries (what is in and out of scope);
4. plan evidence acquisition;
5. acquire bounded evidence (respecting §4.10 cost limits);
6. propose schema (specializations under the kernel, §4.4);
7. resolve identities (§4.8);
8. extract claims and events (§4.3, §4.6);
9. propose mechanisms (§4.9);
10. identify contradictions (via `ContradictionEngine`);
11. measure coverage (against competency questions and §4.7 facets);
12. evaluate (§4.12);
13. request review where required (§4.13, governance);
14. publish a versioned artifact;
15. schedule refresh.

**Normative.** The orchestrator MUST support backtracking to any earlier
responsibility when later evidence invalidates an earlier decision. **Schema
induction PROPOSES; evidence, competency tests, and domain constraints RATIFY.** A
proposed schema is never authoritative on proposal alone.

**Commentary.** v1 ships the orchestrator as a **contract**, not as an autonomous
loop (§4.14). The 15 responsibilities are the interface a future automation packet
implements; the v1 self-model builder executes a subset of them by hand-wired
composition of existing runtimes.

---

## 4.12 Evaluation

**Normative.** Reconstruction is evaluated across **five classes**:

1. **retrieval** — can the model answer its competency questions from evidence;
2. **structural** — does the model conform to the kernel and its declared schema;
3. **temporal** — are valid/record times coherent and append-preserving;
4. **mechanism-safety** — is no causal claim labeled beyond its evidence basis (§4.9);
5. **decision usefulness** — does the model change a decision it was built to
   inform.

**Normative.** The ONLY permitted final statuses are:

`OPERATIONAL` · `PARTIALLY_OPERATIONAL` · `INSUFFICIENT_EVIDENCE` · `FAILED`.

`COMPLETE` is NEVER a valid status. `N/A` NEVER counts as a pass — a check that
does not apply is recorded as not-applicable and excluded from the denominator, not
scored as green. This binds to PLATFORM_SPEC §16 (Failure Model): a
`VERIFICATION`-class failure maps to `FAILED`; an untested-but-present component
maps to `INSUFFICIENT_EVIDENCE`, never to a pass.

**Commentary.** These four statuses are the reconstruction-level echo of the
Completion Standards enforced repo-wide: "COMPLETE" is banned because it is the word
that has historically laundered unverified state into reported truth.

---

## 4.13 Witness and counsel method

**Normative.** Blind **witnesses** (independent observers asked without shared
framing) and adversarial **counsels** (critics arguing opposing positions) are
**OPTIONAL** acquisition and critique methods. When used:

- blindness **reduces shared framing** but does NOT by itself prove independent
  evidence;
- **independence MUST be measured by source lineage** (do the assertions trace to
  genuinely different `SourceRecord`s), NOT by the count of personas consulted.

Persona multiplication over one source is one source wearing many masks; it MUST
NOT raise confidence.

**Commentary.** The 2026-07-18 territory-map corpus in `data/reports/`
(`2026-07-18_sales-territory-map.md` and its nine siblings) is the prototype of the
method as a *report grammar*: an evidence-quality preamble, FORCED / HIGH /
MODERATE / BET confidence bands, a "mythology graveyard" of definitively-false
claims, explicit deflation corrections, and a ranked list of the map's own
omissions. That grammar is the human-authored ancestor of §4.7 (facet honesty),
§4.9 (basis honesty), §4.10 (recorded omissions), and §4.12 (no false "complete").
In-substrate, the adjudication precedent is `DeliberationCouncil`
(`substrate/understanding/deliberation/council.py`): fixed adversarial roles
(strategist, skeptic, completeness auditor, risk/governance, domain expert,
engineer) producing role opinions and a synthesized verdict — the counsel pattern
already realized as code.

---

## 4.14 Conformance matrix

**Normative — what v1 implements.**

| Capability | v1 status |
|---|---|
| New contracts (`SourceRecord`, `ObservationRecord`, `ClaimLedgerEntry`, `DerivedBelief`, `IdentityResolution`, `CausalSupportRecord`, `ActivityRecord`) in `substrate/understanding/reconstruction/contracts.py` | **implemented** |
| Evidence & Provenance Fabric (facet vector, §4.7) | **implemented** over existing evidence types |
| Claim & Belief Ledger (§4.3 invariant enforced) | **implemented** |
| Identity resolution verdicts (§4.8) | **implemented** |
| **Grounded Self-Model builder** (v1 slice: reconstructs UMH's own runtime self-model) | **implemented** |
| Evaluation subset (structural + temporal + mechanism-safety; retrieval and decision-usefulness partial) | **implemented (subset)** |
| Verification script for the self-model slice | **implemented** |
| Formal-dependency import evidence + evidence-backed identity verdicts (§4.8/§4.9) | **implemented (v1.1)** |
| Execution-backed test evidence (pytest evidence plugin + two-dimension outcome ingestion + evidence-gated tested-facet derivation, CQ5 partial closure; `unit_tested` unreachable until a `unit` marker is registered — only `integration` is a registered class marker) | **implemented (v1.2)** |

**Normative — what is contract-only in v1** (declared here, RFC'd separately
before any code path):

| Capability | Status |
|---|---|
| Mechanism library beyond `CausalSupportRecord` | contract-only |
| Simulation of reconstructed models | contract-only (stays in `substrate/reality_model/simulation.py`) |
| Orchestrator automation (§4.11 as an autonomous loop) | contract-only |
| Governed future-improvement engine | contract-only |
| External-domain reconstruction | contract-only |
| ContradictionEngine integration (lexical candidate adapter — engine outputs are candidates, never adjudicated contradictions) | contract-only |
| Component-exercise mapping ingestion (coverage dynamic contexts → test-to-component evidence) — without it tested facets derive for NO component, and v1.2 says so (`component_mapping_status`); a test file referencing a module is never proof of correctness | contract-only |
| Canonical-reality write-back from reconstruction | contract-only |
| Agent-runtime projection (Context/Event/Effect, §4.15) | contract-only |
| Durable-execution runtime (§4.15.2) | contract-only |

**Normative — v1 Grounded Self-Model slice.** v1 reconstructs the organism's own
self-model by composing existing runtimes: `SelfModel` and its `CanonicalSelf` /
`InstanceSelf` (`substrate/self_model.py`, structural self-knowledge); `WorldModel`
+ `extract_world_model()` (`substrate/organism/world_model.py`, subsystem
inventory with `WorldEvidence` / `WorldGap`); `ContradictionEngine`
(`substrate/organism/contradiction_engine.py`, epistemic contradictions);
`RealityGraph` (`substrate/organism/reality_graph.py`, entity/relation view);
`RealityIntelligenceEngine` (`substrate/reality_model/reality_intelligence.py`,
evidence retrieval and lineage); and `PredictiveSelfModel`
(`substrate/organism/self_model_predictor.py`, PLATFORM_SPEC §8) for the
predictive-control class. The slice adds the ledger and facet vector on top; it
**replaces none** of these.

**Normative — v1 integration boundaries.**

- **No canonical reality writes.** v1 reads through `CanonicalRealityModel` /
  `InstanceRealityModel` / `RealityIntelligenceEngine`; it invokes no new write
  path. The existing governed write path `CanonicalRealityWritePath`
  (`substrate/reality_model/canonical_reality_write.py`, with its trust gate)
  remains the ONLY way anything reaches canonical reality, and reconstruction does
  not call it in v1.
- **No mutation-routing changes.** v1 registers no `MutationSpec`, changes no
  `governed_mutation()` behavior, and touches no frozen contract in PLATFORM_SPEC
  §1–§2.
- **`UMH_CANONICAL_RUNTIME_ROUTING` untouched.** v1 neither reads nor sets it;
  `canonical_runtime_routing_enabled()` / `canonical_runtime_name()`
  (`substrate/organism/canonical_runtime.py`) behave exactly as before.
- **`SelfModel` and `RealityIntelligenceEngine` not replaced** — composed only.
- **No second event spine and no second approval store.** v1 introduces neither;
  where it needs to announce a reconstruction, it does so through the single
  `EventSpine` (PLATFORM_SPEC §3), and any human-review gate (§4.11 step 13) routes
  through the existing approval path, never a new one.

**Documented adapter points for future integration** (each a published Extension
Point per PLATFORM_SPEC §13, activated only by a later RFC):

- reconstruction → canonical reality: `CanonicalRealityWritePath.apply_mutation()`
  is the future write adapter (trust-gated), never bypassed;
- reconstruction → governed action: `governed_mutation()` (PLATFORM_SPEC §1) for
  any future write side-effect;
- reconstruction → events: `EventSpine.emit()` under an existing `EventDomain`
  (e.g. `MEMORY` / `OBSERVABILITY`);
- orchestrator automation: implements the §4.11 15-responsibility contract behind
  a feature flag, off by default.

---

## 4.15 Agent-runtime interoperability (contract-only)

**Commentary.** A world model becomes operationally valuable only when its state
connects cleanly to durable agent execution. The normative requirements of this
section stand on their own terms: grounded model state → typed context
projection → evidence-backed event → governed effect proposal → outcome →
updated context. (Time-sensitive research context, non-normative: industry
convergence — e.g. Palantir's Agent Stack at DevCon 6, with its context-items /
events / effects grammar, durable orchestration, automatic telemetry, and
evaluation-governed improvement — independently validates this pattern; vendors
validate the pattern, they do not define UMH's law.) UMH does not adopt those
nouns — it already has richer types — but every agent execution and every
reconstruction output MUST be **projectable** into a common runtime grammar so
the self-model never becomes an isolated research artifact consumed by parsing
reports ad hoc. The projection maps into the EXISTING `governed_mutation()` /
GovernedExecutionSpine (approval, verification, rollback, journaling,
idempotency) — never a parallel runtime. Everything in this section is
**contract-only in v1**: no agent engine, orchestrator, or new runtime surface is
built by the v1 packet.

### 4.15.1 The Context–Event–Effect projection

**Normative.** Grounded self-model outputs MUST be projectable into three typed
runtime primitives (bindings, not new classes in v1):

| Primitive | Meaning | UMH binding |
|---|---|---|
| **Context item** | durable, typed, versioned state needed to continue a task | `ClaimLedgerEntry`/`DerivedBelief` + `WorldModelEntry` (`substrate/understanding/world_model/world_model.py`); carries source claim ids + valid_as_of |
| **Event** | an evidence-backed state change or external signal that may require a transition | `ObservationRecord` + `SignalEnvelope`/`TraceEvent` (`substrate/types.py`), announced through the single `EventSpine` (PLATFORM_SPEC §3) |
| **Effect** | a typed, idempotency-keyed request to alter reality | `ActionEnvelope` (`substrate/organism/action_envelope.py`) / `RealityMutation` through `governed_mutation()` — never a new mutation path |

The canonical loop: Context + Event → transition proposal → governance → Effect →
Outcome → updated Context. A projection MUST preserve record ids so any context
item is traceable to its supporting claims and observations.

### 4.15.2 Durable-execution requirements (future phases)

**Normative.** Any future Domain Reconstruction Orchestrator (§4.11 automation)
MUST support: checkpointed state; resumability; deterministic waiting;
externally-triggered continuation; idempotent or duplicate-resistant effects;
bounded retries; human-approval suspension; cancellation; timeout; rollback where
possible; versioned agent logic; automatic telemetry; replayable transition
history. An agent process that dies mid-task MUST rehydrate from persisted state
without repeating completed effects.

### 4.15.3 Automatic observability invariant

**Normative.** Every orchestrator transition MUST automatically produce: context
version before; event consumed; transition selected; tools/models involved;
effects proposed; governance verdict; effects executed; context version after;
evidence and proof; latency/resource use; failure-or-waiting state. Observability
is a structural property of executing through the runtime — agent-authored
logging is supplementary, never authoritative; untraced execution is structurally
impossible. **Trace ≠ Proof ≠ Outcome ≠ Learning**: a trace proves what the
system recorded about execution, never that the external result was correct
(that remains the Proof Contract's job, PLATFORM_SPEC §5).

### 4.15.4 Evaluation-to-improvement boundary

**Normative.** Telemetry and evaluation MAY generate improvement proposals. They
MUST NOT directly modify: constitutional semantics; permissions; security
boundaries; the canonical ontology; production workflows; model promotion state.
All improvement follows branch → isolated evaluation → review → governed
promotion or rollback (the same lifecycle §4.14's adapter points require). A live
system never modifies itself directly.

---

## Change process

**Commentary.** This specification is **DRAFT** at version 0.3.0. Amendments follow
normal PR review. Every capability marked contract-only in §4.14 stays
non-executing until a separately-reviewed, guarded packet wires it, at which
point that packet carries its own tests and gate updates. Promotion of this spec from DRAFT to FROZEN follows
PLATFORM_SPEC.md's process vocabulary: an RFC with justification, a migration plan
for any consumer, a regression qualification pass with all prior suites green, a
version bump, and contract approval from the platform owner. Until then, nothing in
this document may be cited as a frozen platform guarantee.
