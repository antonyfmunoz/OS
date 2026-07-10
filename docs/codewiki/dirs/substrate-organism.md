---
type: codewiki-dir
dir: substrate/organism
---

# `substrate/organism/` — the self-operating agent core

**389 `.py` files (275 at the top level + 114 across `audits/`, `benchmarks/`, `executors/`, `self_use/`, `tests/`) · ~153,800 lines · ~5.8 MB · [Full file inventory](../inventory/substrate.md)**

Counts measured directly in the live tree: `find substrate/organism -name '*.py' -not -path '*__pycache__*' | wc -l` → 389 (275 with `-maxdepth 1`). This subtree is the single largest subsystem of `substrate/`, which the [census](../inventory/_census.md) records at 1,009 code files overall.

## Purpose

`substrate/organism/` is the part of UMH that lets the system operate *itself* — schedule work, allocate it to agent workcells, execute state mutations under governance, observe the outcome, and learn. Where `substrate/execution/` provides the LLM/cognitive pipeline and `substrate/control_plane/` provides signal routing and risk classification, `organism/` is the runtime loop that turns operator intent into governed changes to reality (filesystem, containers, processes, network, persisted state) and keeps a self-model of what it did.

The name is literal: this directory treats the running system as one organism with a lifecycle daemon, homeostasis regulation, a self-model, an event spine, and a learning loop. Everything here is **deterministic-first** — the daemon, routers, registries, and self-model extraction all run without an LLM; LLM calls are a cognitive enhancement layered on top, never a dependency.

## How it fits

This is a sub-package of `substrate/` — the universal, projection-agnostic platform layer. See [`substrate/`](./substrate.md) for the parent directory and the dependency-direction law. Per the [Architecture Layer Law](../../../.claude/rules/architecture-layers.md), `organism/` sits at the bottom of the stack: `projections/ → transports/ → adapters/ → substrate/`. It may be imported by anything above it but imports **only** downward and sideways within `substrate/` (e.g. `substrate.governance`, `substrate.execution`, `substrate.reality_model`). It must never import from `transports/` or `services/`; when it needs an I/O surface it uses an abstract port in `substrate/sockets/`.

Concretely, `canonical_runtime.py` documents this discipline: it "never imports transports/ or services/ … the concrete router/spine are obtained from the running daemon at call time." Organism modules are the workhorses invoked by the Discord bot, the cockpit HTTP API, and EOS workflows — but always through governed entry points, not by transports reaching into execution logic.

## Structure

| Subdir | `.py` | Role |
|---|---|---|
| *(top level)* | 275 | Daemon, runtimes, registries, advisors, action system, self-model, learning loop — the operating core |
| `audits/` | 7 | Self-audit probes: `organism_awareness.py`, `operational_awareness.py`, `model_correspondence.py`, `context_capacity.py`, `empire_readiness.py`, `source_truth.py` — the organism checking whether its own state matches reality |
| `benchmarks/` | 26 | Scored capability benchmarks (`autonomous_execution.py`, `governance_quality.py`, `reality_correspondence.py`, `compounding_proof.py`, `harness_superiority.py`, …) plus scorers (`composite_scorer.py`, `harness_scorer.py`) |
| `executors/` | 5 | Concrete execution mechanics: `agent_executor.py`, `workstation_executor.py`, `approval_intercept.py`, `execution_telemetry.py` |
| `self_use/` | 7 | The organism using itself on itself: `certification_report.py`, `gap_ledger.py`, `meta_ide_audit.py`, `projection_delta.py`, `task_catalog.py`, `task_taxonomy.py` |
| `tests/` | 69 | Subsystem tests — the largest test cluster in `substrate/` |

## Key components

**The canonical operation runtime — the most load-bearing fact in the system.**
`canonical_runtime.py` (WP-P1-001) *declares* that there is exactly **one** path from operator intent to a governed state mutation:

```
governed_mutation  →  MutationRouter  →  GovernedExecutionSpine
```

It holds no execution logic itself — it is a declaration plus one deterministic routing flag. `canonical_runtime_name()` returns the string `"governed_mutation -> MutationRouter -> GovernedExecutionSpine"` so tests, docs, and adapters all reference one source of truth. `canonical_runtime_routing_enabled()` is a pure env lookup (`UMH_CANONICAL_RUNTIME_ROUTING`, truthy = `1/true/yes/on`) — **off by default**, so deploying the packet is a no-op until the flag is set, and rollback is "unset the flag" with no code revert. The rival runtimes are explicitly *adapters*, not second choke points: `command_runtime.py`, `governed_work_runtime.py`, and `organism_loop.py` are its three dependents (`query_graph.py dependents substrate/organism/canonical_runtime.py`) — when routing is enabled each submits its mutation step into this one path instead of executing independently. This is the guarantee behind the permanent constraint "all state changes through `governed_mutation()`."

**The mutation gateway.** `governed_spine.py` is the concrete `GovernedExecutionSpine` — "THE single mutation gateway in the organism. EVERY mutation to reality MUST flow through this spine." Subsystems become proposal generators that emit `ActionEnvelope`s (`action_envelope.py`, 21 in-edges — highly central); only the spine executes them. It enforces the execution-mode governance check, validates against the `MutationRegistry` (`mutation_registry.py`, 20 in-edges), gates approvals, dispatches, retries, rolls back, verifies, records to the journal, and emits events.

**The lifecycle daemon.** `daemon.py` (`query_graph.py centrality`: 9 in / 55 out — the widest fan-out in the subtree) owns the full subsystem graph: `RuntimeGraph → RuntimeSupervisor → OrganismCoordinator → Advisor`, with `HomeostasisEngine` feeding self-regulation and `WorkcellDaemon` processing persistent inboxes. It is tmux-safe, restart-safe, crash-safe, and supervisor-managed.

**The event spine.** `event_spine.py` (41 in-edges — the single most-depended-on file here) is the organism-level, in-memory, append-only, thread-safe event transport that connects Advisor, Coordinator, RuntimeGraph, Supervisor, and HomeostasisEngine into one observable flow, with domain-filtered subscriptions and replay for late-joining observers (e.g. cockpit).

**The advisor system.** `advisor.py` (13 out-edges), `advisor_hierarchy.py`, `advisor_conversation.py` (2,065 lines — the largest file here), and `advisor_reconciliation.py` implement the strategic-reasoning layer. Parallel advisor branches must **reconverge** before a workcell completes.

**The action system.** `action_catalog.py` is a data-driven registry — actions are data (`ActionDefinition`: command template, risk level, preconditions, parameter schema), so adding one is registering a definition, not writing Python. `action_bridge.py` composes catalog + observation + execution to translate an operator request into `WorkPacket → ExecutionCoordinator → WorkstationExecutor` with no new execution path. `next_action_engine.py`, `autonomous_action_gateway.py`, and `action_voice_contract.py` round out intent→action routing.

**Workcells (agent employees).** `workcell.py` is the planning/delegation model (a bounded unit spawned from a WorkPacket, recursively subdividable); `workcell_protocol.py` is the low-level inbox/outbox execution cell; `workcell_daemon.py` runs persistent inbox processing. The four canonical roles are seeded on disk — `advisor`, `executor`, `researcher`, `reviewer` (see `data/umh/organism/workcells/*/heartbeat.json`).

**The self-model.** `world_model.py` is the organism knowing *itself* — which subsystems exist, their `EntityStatus` (operational/degraded/partial/dormant/missing/unknown), the evidence for that state, known gaps, and uncertainties. Extraction is fully deterministic. Per the [Ontology Layer Law](../../../.claude/rules/ontology-layers.md) this is a distinct concern from `substrate/understanding/world_model/` (domain knowledge) and must not be merged with it.

**Reality graph.** `reality_graph.py` is the canonical cross-domain operator-world graph. It *composes and reflects* — it never mutates canonical reality directly; any write routes through `CanonicalRealityWritePath` (in `substrate/reality_model/`). It reflects mutations after they happen, never initiating them.

**Execution-policy registry.** `domain_registry.py` defines first-class WorkPacket domains — each with `allowed_actions`, `ProofRequirement`s, default agent types, `approval_gates`, and a default risk class. Per the Ontology Layer Law this is an *execution-policy* registry (what actions/proofs/approvals a domain permits), **not** an ontology/domain-model registry and not the L4 `BridgeRegistry`.

**The runtime family.** Roughly 60 top-level `*_runtime.py` modules specialize the operating loop by concern — the largest include `executor_runtime.py` (1,513), `profile_runtime.py` (1,490), `workstation_runtime.py` (1,400), `command_runtime.py` (1,395), `continuity_runtime.py` (1,353), and `session_runtime.py` (1,114) — alongside `orchestrator_kernel.py`, `execution_coordinator.py`, and `projection_engine.py`.

**The learning loop.** `outcome_learning.py` (14 in-edges), `outcome_pattern_engine.py`, `outcome_tracking_runtime.py`, `outcome_verification.py`, `execution_journal.py` (14 in-edges), `learning_extraction_runtime.py`, `leverage_engine.py`/`leverage_metrics.py`/`leverage_assimilation.py`, and `autonomous_improvement_lane.py` close the observe→score→learn loop that makes the organism compound with every execution.

## Data & state

Organism state persists under `data/umh/organism/` (JSONL append logs + JSON snapshots):

- `daemon_state.json` — daemon/subsystem snapshot
- `events.jsonl` (+ `events.jsonl.old`) — event spine log
- `execution_journal.jsonl` — every governed mutation recorded by the spine
- `outcome_learning.jsonl`, `learning_signals.jsonl` — the learning loop
- `messages.jsonl`, `reports.jsonl`, `deliverables.jsonl`, `proof_packages.jsonl`
- `qualification_live.jsonl`, `c32_benchmarks.jsonl`, `mesh_metrics.json`
- `workcells/<role>/heartbeat.json` — per-role workcell liveness (`advisor`, `executor`, `researcher`, `reviewer`)
- Sub-stores: `agents/`, `coordinator/`, `leverage/`, `memory/`, `projections/`, `propagation/`, `supervisor/`, `templates/`, `workcell_daemon/`

Path root is resolved at runtime via `UMH_ROOT` (default `/opt/OS`) — never hardcoded. Note the container gotcha: inside Docker `UMH_ROOT=/app`, not `/opt/OS`.

## Gotchas

- **Never introduce a second mutation path.** `governed_spine.py` is *the* gateway and `canonical_runtime.py` declares *the* one runtime. Adding a runtime/spine/approval store that executes mutations outside this chain violates the permanent platform constraint. New runtimes must be adapters that route in, exactly like `command_runtime`, `governed_work_runtime`, and `organism_loop`.
- **Two same-named modules that must never merge** (Ontology Layer Law): `substrate/organism/world_model.py` (organism self-model) is NOT `substrate/understanding/world_model/`; `substrate/organism/domain_registry.py` (execution-policy) is NOT an ontology/domain-model registry and NOT the L4 `BridgeRegistry`. Gate 13 (`scripts/check_ontology_homes.py`) blocks a new ontology/domain-model registry appearing here.
- **`reality_graph.py` reflects, never initiates.** It composes cross-domain relationships and reads state; all reality writes go through `CanonicalRealityWritePath`. Do not add a mutation call to it.
- **Deterministic-first is enforced by design here.** The daemon, routers, registries, and `world_model` extraction run without an LLM. Any LLM call added to this subtree needs a deterministic fallback that produces a usable result (Deterministic-First Principle).
- **Substrate never imports up.** No `import` of `transports/` or `services/` anywhere in this subtree — enforced by `scripts/check_dependency_direction.py`. Use `substrate/sockets/` ports for I/O.
- **File-size ceiling.** `advisor_conversation.py` (2,065 lines), `qualification_harness.py` (1,569), and `executor_runtime.py` (1,513) are the largest files and sit well under the 3,000-line hard cap — but they are the first candidates to split before growing further.
- **Python 3.11 only** for anything that runs in a container (Docker images pin 3.11); no 3.12+ syntax.

## See also

- [`substrate/`](./substrate.md) — parent package and dependency-direction law
- [`services/`](./services.md) — deployment entrypoints that launch the daemon
- [`transports/`](./transports.md) — I/O surfaces (Discord, HTTP API) that invoke organism runtimes through governed entry points
- [`adapters/`](./adapters.md) — model routing the cognitive stages call into
- [Architecture overview](../architecture.md) · [Data & control flow](../data-flow.md)
