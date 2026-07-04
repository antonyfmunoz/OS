# UMH P1 Spine Migration — WP-P1-001

**Date:** 2026-07-04
**Packet:** WP-P1-001 — establish one canonical governed operation runtime.
**Base:** `origin/main` @ `fc0a96304`. **Branch:** `fix/p1-001-canonical-operation-runtime`.
**Status:** implemented as a draft PR; staged behind a routing flag (off by default). Held for operator approval — not merged.

---

## 1. What this packet declares

The one canonical operation runtime is:

```
governed_mutation → MutationRouter → GovernedExecutionSpine
```

Named once in `substrate/organism/canonical_runtime.py`
(`CANONICAL_OPERATION_RUNTIME`). This ratifies the P0 choke point
(`MutationRouter`/`GovernedExecutionSpine`, fail-closed since WP-P0-001) as the
single declared runtime — it does not build a new one. The system becomes more
singular, not larger.

The architecture invariant is enforced by `tests/test_single_spine_architecture.py`
(AST-based): exactly one `governed_mutation` definition, one `MutationRouter`
class, and the rival runtimes gate their executing step behind the canonical
routing guard.

## 2. Ground-truth corrections made during implementation

Two items the pre-implementation micro-plan (and its recon agents) recorded were
**wrong** and are corrected here, verified by grep against `origin/main`:

| Micro-plan claim | Verified reality on `fc0a96304` | Consequence |
|---|---|---|
| `MutationSpec.degraded_mode_allowed` does not exist | **It EXISTS** — `mutation_registry.py:52` (`degraded_mode_allowed: bool = False`). WP-P0-001 added it as intended. | Designed *with* it. No change needed. |
| `governed.py` still has a `completed_ungoverned`/`failed_ungoverned` path to converge | **No such path** — `transports/api/governed.py:110` explicitly states "No ungoverned execution happens here"; the fallback delegates to `route_mutation_degraded()`, a deterministic fail-closed gate (`mutation_router.py:228-378`). Statuses are `completed_degraded`/`rejected_control_plane_unavailable`. | **Scope item #6 was already satisfied by P0.** No code change — modifying already-correct fail-closed code was avoided. |

Third check (event backbone): `substrate/execution/bridge/event_spine.py` is a
Discord **Event/EventType data model** (`Event` dataclass, `create_event()`
factory), **not** an event *transport* duplicate of the `EventSpine` bus in
`substrate/organism/event_spine.py` (which has `emit()`/`subscribe()`). The
`services/discord_bot.py:108` import is therefore legitimate. **`discord_bot.py`
was NOT repointed** — the backlog's "dual event backbone" was a data-model vs
bus conflation.

## 3. Runtime disposition table

| Runtime | File | Disposition | Mechanism in this packet |
|---|---|---|---|
| **MutationRouter** | `substrate/organism/mutation_router.py` | **CANONICAL core** | unchanged; declared canonical |
| **GovernedExecutionSpine** | `substrate/organism/governed_spine.py` | **CANONICAL gateway** | unchanged |
| **governed_mutation (shim)** | `transports/api/governed.py` | **CANONICAL public API** | unchanged (P0 already fail-closed) |
| `GovernedWorkRuntime` | `substrate/organism/governed_work_runtime.py` | **adapter** onto canonical | `execute_work` routes dispatch through canonical runtime when flag on + router injected; prior coordinator-dispatch when off |
| `CommandRuntime` | `substrate/organism/command_runtime.py` | **subordinate** (declaration only) | docstring corrected + `_SUBORDINATE_TO` marker; deep envelope wiring is **WP-P1-009** |
| `OrganismLoop` | `substrate/organism/organism_loop.py` | **converged** | Step 5 execution routes through canonical runtime when flag on + router injected; not a second choke point |
| `ConcreteExecutionSpine` | `substrate/execution/spine.py` | **keep — LLM/cognitive lineage** (NOT a mutation rival) | behavior preserved; memory writes additionally emit a canonical promotion candidate via `MemoryCandidateGenerator.generate_from_trace` |
| `EventSpine` (bus) | `substrate/organism/event_spine.py` | **keep — orthogonal** event transport | unchanged |
| `Event` model | `substrate/execution/bridge/event_spine.py` | **keep — data model** (not a bus) | unchanged; `discord_bot.py` import legitimate |
| legacy `ExecutionSpine` | `substrate/execution/runtime/execution_spine.py` | **declare deprecated** | documented here; live-Discord cutover + deletion is **WP-P1-006** (out of scope) |
| `ExecutionPipeline` | `substrate/execution/pipeline.py` | **read/signal path** | documented (ARCHITECTURE.md already classifies it) |
| `GovernedExecutionRuntime` | `substrate/organism/governed_execution_runtime.py` | **dormant read-only dashboard** ("NEVER executes") | documented; no change |

## 4. Staged cutover (routing flag)

Routing is gated by env `UMH_CANONICAL_RUNTIME_ROUTING`
(`canonical_runtime_routing_enabled()`, deterministic — 1/true/yes/on):

- **Default (unset / off):** every adapter preserves its exact pre-P1-001
  behavior. Deploying this packet changes no running behavior. This is the
  fail-safe default.
- **On + MutationRouter injected:** `GovernedWorkRuntime.execute_work` and
  `OrganismLoop` Step 5 submit their executing step through the canonical
  runtime (`work_packet_execute` mutation → `GovernedExecutionSpine`), so the
  executor is reached only via a governed verdict.

The `MutationRouter` is injected by the component that holds the daemon's spine
(the daemon / transport layer that already obtains it), not imported by
substrate from transports — dependency direction preserved.

Cutover sequence for production: (1) merge with flag off (no-op); (2) inject the
router at the daemon wiring; (3) enable the flag on one surface; (4) verify
governed traces; (5) widen.

## 5. Rollback plan

- **Instant:** unset `UMH_CANONICAL_RUNTIME_ROUTING` (or set to `off`). Every
  adapter reverts to its prior path with no code change.
- **Full:** `git revert` the PR. All changes are additive (new module, new
  optional constructor params defaulting to None, guarded branches, docstrings,
  a new test) — reverting restores the exact prior tree. No files moved or
  deleted; no state migrated.

## 6. Out of scope (do not absorb)

- **WP-P1-006** — Discord/legacy `execution_spine.py` cutover + deletion.
- **WP-P1-008** — Workcell / WorkloadRunner governance.
- **WP-P1-009** — CommandRuntime per-command envelope submission (the deep work;
  this packet only demotes CommandRuntime by declaration).
- **WP-P1-007** — approval authority (stacked on this; also blocked on unmerged
  WP-P0-004).
- The `ARCHITECTURE.md §9` "One API" distribution claim is under a
  2026-07-03 lock and is a distribution-layer statement, not a mutation-runtime
  one — left unchanged (out of scope for this runtime packet).
