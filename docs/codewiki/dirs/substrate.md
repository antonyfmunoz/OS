---
type: codewiki-dir
dir: substrate
---

# `substrate/` — the universal UMH platform core

**1,009 files · 12,452,560 bytes · [Full file inventory](../inventory/substrate.md)**

## Purpose
`substrate/` is the Universal Meta Harness itself: the domain-agnostic platform
every projection (EOS, CreatorOS, LyfeOS) is built on. It owns the type system,
the governance and risk model, the execution pipeline, the state stores, the
organism runtime, and the abstract ports through which the outside world reaches
it. Nothing in here knows what "venture" or "ICP" means — those are projection
vocabulary. Substrate defines the *rules of worlds*, never the contents of one
world. If a class, string, or field would differ for a different UMH user, it
does not belong here (see the Instance Context and Ontology Layer laws below).

## How it fits
Substrate is the **bottom** of the four-layer dependency stack
(`projections/ → transports/ → adapters/ → substrate/`). Everything imports
downward into it; it imports **nothing upward or sideways**. This is mechanically
enforced: `scripts/check_dependency_direction.py` blocks any
`from transports`, `from services`, `from projections/saas`, or even
`from adapters` inside `substrate/`. When substrate needs something from a higher
layer, it declares an **abstract port** in `substrate/sockets/` and the outer
layer registers a concrete implementation at runtime — this is the
dependency-inversion seam that keeps the core reusable. Reference:
`.claude/rules/architecture-layers.md` and the projection-boundary,
instance-context, and ontology-layer laws in `.claude/rules/`.

The four ontology layers (`.claude/rules/ontology-layers.md`) also live mostly
here: **L1** external operational reality (`substrate/reality_model/`), **L2**
the universal metamodel / primitives (`substrate/types.py`,
`substrate/ontology/`), **L4** semantic grounding / domain bridges
(`substrate/understanding/domains/`). Only **L3** projection domain models live
outside, in `projections/`. L2 must never import L3 or business state; Gate 13
(`scripts/check_ontology_homes.py`) freezes the set of ontology homes.

## Structure

| Subdir | Files | Role |
|---|---|---|
| `foundation/` | 4 | Bedrock: `identity.py`, `laws.py`, `perspective.py` — the non-negotiable invariants and self-identity of the substrate. |
| `ontology/` | 8 | **L2 metamodel** — `laws.py`, `primitives.py`, `relationships.py`. Universal primitive definitions. Must not import business state or projections. |
| `contracts/` | 12 | Protocol/ABC surface: `agent_types.py` (TaskType, ModelProvider), `execution_protocol.py`, `governance_protocol.py`, `adapter_contracts.py` — the typed interfaces other layers implement. |
| `control_plane/` | 77 | **Orchestration brain** — 17 subpackages (actions, agents, context, coordination, delegation, events, goals, identity, invariants, onboarding, orchestrator, proactive, router, runtime, scheduling, signals, strategy). Signal lifecycle, goal decomposition, delegation, scheduling. |
| `execution/` | 176 | **The doing layer** — `spine.py` (8-stage LLM/cognitive pipeline), `cpu_gate.py` (CPU choke point), `trace.py`, `feedback.py`, plus subpackages runtime/, workers/, voice/, media/, ingestion/, adapters/, actuation/, intent/, loop/, bridge/, agents/, logs/. |
| `governance/` | 20 | Deterministic risk + authority: `risk_classes.py`, `authority.py`, `policy_engine.py`, `security.py`. Classifies every mutation before it runs. |
| `state/` | 66 | **19 sub-stores** — business, config, context, finance, lifecycle, logs, memory, metrics, permissions, preferences, profiles, providers, registries, session, storage, stores, tenancy, work. All durable state, tenant-scoped. |
| `memory/` | 7 | Long-term memory reconciliation: `canonical_write.py`, `auto_reconciler.py`, `candidate_generator.py`, `promoter.py`, `watcher.py`, `claude_bridge.py`. |
| `understanding/` | 55 | **14 subpackages** — perception, interpretation, deliberation, knowledge, embedding, patterns, reality, research, signals, world_model, world_pulse, intelligence, ontology (shim), **domains/ (L4 bridges)**. Turns raw input into structured meaning. |
| `reality_model/` | 8 | **L1 external reality** — `canonical.py`, `instance.py`, `canonical_reality_write.py`, `reality_query.py`, `reality_mutation.py`, `simulation.py`, `reality_intelligence.py`. The org's model of the real world. |
| `intelligence/` | 4 | Model-facing learning: `runtime.py`, `training_extractor.py`, `finetune_harness.py`. |
| `composition/` | 46 | Tool Mastery Engine authoring: `knowledge_gap_trigger.py` + `mastery/` (research → author → reconcile skill files). Detects capability gaps and composes new mastery. |
| `templates/` | 3 | `reality_template.py`, `registry.py` — parameterized templates (f(invariants, parameters, context)). |
| `integrations/` | 5 | External wiring: `product_connections.py`, `bridge.py`, `cors.py`, `health.py`. |
| `sockets/` | 26 | **Abstract ports — the dependency-inversion seam.** intelligence_port, channel_port, projection_port, approval_port, browser_port, mesh_dispatch_port, notification_engine, and the socket registry. |
| `operator/` | 19 | Operator-facing runtime: `intent_router.py`, `intent_runtime.py`, `continuity_engine.py`, `operator_attention_engine.py`, `device_continuity.py`. |
| `workstation/` | 57 | Governed operator workstation: activation, agent workforce runtime, ambient wake, app resolver, attention aggregation — the MVP surface. |
| `meta_ide/` | 18 | Engineering self-improvement: `engineering_planner.py`, `engineering_execution.py`, `browser_evidence_collector.py`, `browser_verification_gate.py`. |
| `observability/` | 5 | `trace_store.py`, `error_recorder.py`, `outcome_classifier.py`, `jsonl_rotation.py`. |
| `organism/` | 389 | The living runtime — canonical mutation spine, daemon, workcells, event spine, reality graph. **Its own page:** [substrate-organism.md](./substrate-organism.md). |

`organism/` is by far the largest subsystem (389 of the 1,009 files) and hosts
the **canonical operation runtime** — `substrate/organism/canonical_runtime.py`
declares the single legal mutation path (`governed_mutation → MutationRouter →
GovernedExecutionSpine`), distinct from `execution/spine.py`'s cognitive
pipeline. Full treatment lives on its dedicated page.

## Key components
Read these first — they are the highest-centrality nodes in the fresh graph:

- **`substrate/types.py`** (1,553 lines) — the single domain type system:
  `SignalEnvelope`, `RiskClass`, `Modality`, `ExecutionContext`,
  `ExecutionResult`, and 30+ Pydantic models. **85 files import it** — the most
  depended-on file in the entire codebase. This is L2 metamodel; every field
  here must be projection-agnostic.
- **`substrate/canonical_types.py`** (1,532 lines) — the Canonical Type Registry,
  ~1,157 registered type entries (the "~1040 registered types" referenced in
  CLAUDE.md). Before defining any new Enum/BaseModel/@dataclass, check here and
  import rather than redefine (Type Coherence Law, Gate via
  `scripts/check_type_divergence.py`).
- **`substrate/execution/spine.py`** — the **8-stage cognitive pipeline**:
  interpret → recall → lookup → compose → route → execute → trace → feedback,
  with a Stage 0 governance gate, Stage 0b simulation dry-run, and Stage 0c
  deliberation council for high-risk signals (`spine.py:172`+). Deterministic-
  first: every LLM call has a heuristic fallback so output is produced even when
  all providers are down. NOT the mutation runtime — that is
  `organism/canonical_runtime.py`.
- **`substrate/execution/cpu_gate.py`** (64 dependents) — the single CPU choke
  point. `cpu_gate_check(caller)`, `gated_subprocess_run(...)`,
  `gated_popen(...)`. Raw `subprocess.*` is forbidden in substrate/adapters/
  transports/services and blocked by pre-commit Gate 5. Innermost layer of the
  6-layer CPU defense stack (CPU Gate Law, CLAUDE.md).
- **`substrate/self_model.py`** (478 lines) — the substrate's awareness of its
  own structure and state.
- **`substrate/governance/risk_classes.py`** (20 dependents) — deterministic
  risk classification (LOW/MEDIUM/HIGH/CRITICAL) that gates every mutation.
- **`substrate/state/context/context.py`** (33 dependents) &
  **`substrate/state/storage/db.py`** (33 dependents) — runtime context load
  (org/venture IDs from BIS) and the Neon persistence client.
- **`substrate/sockets/`** — `intelligence_port.call_with_fallback` (keyword-only
  — pass `prompt=...`), `envelopes.py` (19 dependents), and the port registry.
  This is the ONLY sanctioned way substrate reaches transports/adapters.

## Data & state
- **Neon Postgres** — via `substrate/state/storage/db.py`; traces, feedback,
  outcomes, tenant/org/venture state.
- **JSONL stores under `data/umh/`** — organism events, execution journal,
  outcome learning, reality model instance, work packets, workcell heartbeats
  (rotated by `observability/jsonl_rotation.py`).
- **Runtime instance values** — org/user IDs from BIS via
  `state/context/context.py`; AI name from `get_ai_name()`; device identity from
  `infra/device_registry.json`. Never hardcoded (Instance Context Law).
- **Env** — `UMH_ROOT` (default `/opt/OS`), `UMH_ORG_ID`/`UMH_USER_ID` (with EOS
  fallback), model-router provider keys resolved through 1Password at deploy.

## Gotchas
- **Never import upward.** `substrate/` importing from `transports/`, `services/`,
  `projections/`, or even `adapters/` is blocked by
  `scripts/check_dependency_direction.py`. Use a `sockets/` port instead.
- **`spine.py` vs `canonical_runtime.py`.** Two different runtimes. `spine.py`
  (execution/) is the LLM 8-stage cognitive pipeline; the canonical *mutation*
  runtime is `organism/canonical_runtime.py` (`governed_mutation → MutationRouter
  → GovernedExecutionSpine`). Do not conflate them — see the Component status
  taxonomy in `.claude/CLAUDE.md`.
- **No new type systems.** Homonyms and parallel enums cost a full reconvergence
  audit. Check `canonical_types.py` first; legacy duplicates live in a
  shrink-only ledger (`data/audits/2026-07-04_type_divergence_ledger.md`).
- **No instance leaks.** No founder/company/product/device literals in
  `substrate/` — pre-commit `check_instance_leak.py` scans all layers.
- **L2 purity.** `substrate/ontology/` and `substrate/types.py` must not carry
  projection vocabulary (venture/offer/ICP/revenue) or import
  `state/business/` — Gate 13 + `check_ontology_layers.py` enforce this; existing
  contamination is frozen shrink-only.
- **Same-name, different concern.** `organism/world_model.py` (organism
  self-model) ≠ `understanding/world_model/` (domain world model);
  `organism/domain_registry.py` (execution-policy) ≠ the L4 `BridgeRegistry`.
  Don't merge them.
- **`intelligence_port.call_with_fallback` is keyword-only** — passing `prompt`
  positionally broke every chat reply (2026-07-08).
- **Python 3.11 in Docker** — no 3.12+ syntax (e.g. backslash in f-string
  expressions); services run 3.11.
- **No Python file over 3,000 lines.** `types.py` (1,553) and
  `canonical_types.py` (1,532) are the largest here and stay under the cap.

## See also
- [substrate-organism.md](./substrate-organism.md) — the 389-file organism runtime
- [../architecture.md](../architecture.md) — the four-layer dependency stack
- [../data-flow.md](../data-flow.md) — how signals move through the spine
- [adapters.md](./adapters.md) · [transports.md](./transports.md) · [projections.md](./projections.md) — the layers above substrate
- [../conventions.md](../conventions.md) — type coherence, instance context, and layer laws
