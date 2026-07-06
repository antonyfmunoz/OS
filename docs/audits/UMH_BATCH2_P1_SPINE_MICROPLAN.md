# UMH Batch 2 — P1 Spine Convergence Micro-Plan

**Date:** 2026-07-04
**Author:** orchestrator (VPS `srv1500858`)
**Scope:** planning artifact only — no code changes. Translates WP-P1-001 and WP-P1-007 from `UMH_WORK_PACKET_BACKLOG.md` into an execution-ready micro-plan verified against the live tree at `main @ fc0a96304`-or-newer.
**Governing principle:** P1 does not add features. P1 *declares and enforces* **one operation runtime** and **one approval authority**. The system must become **more singular, not larger.**

Batch 2 begins with the critical path only:
1. **WP-P1-001** — one canonical governed operation runtime (retire/subordinate rival spines + event backbones).
2. **WP-P1-007** — one canonical approval authority (canonical `ApprovalRequest`, typed fail-closed port, single pending-work store).

---

## 1. Current post-P0 runtime / spine owners

> **Two carried-context corrections, verified live on this HEAD (grep-confirmed):**
> 1. **`MutationSpec.degraded_mode_allowed` does NOT exist.** `grep -rln degraded_mode_allowed` is empty; `MutationSpec` (`mutation_registry.py:29-48`) has `require_approval: bool` + `allowed_modes`, no degraded flag. Any plan text assuming WP-P0-001 added `degraded_mode_allowed` is **false against this tree** — do not build WP-P1-001/007 on it.
> 2. **The `governed.py` shim STILL has an ungoverned fallback.** `transports/api/governed.py:95-110` returns `status="completed_ungoverned"` / `"failed_ungoverned"` when the organism isn't running — i.e. it executes **outside** the choke point and **outside approval**. P0's fail-close landed on the substrate `mutation_router`/`governed_spine` path; the **shim-level fallback survived**. This is an approval-bypass path that WP-P1-001 must converge (route to fail-closed) and WP-P1-007 must account for (an approval can be skipped entirely on this path). Flag, don't assume it's gone.
>
> There are **three unrelated lineages** that all use the word "spine"/"runtime": **(A) mutation governance** (the real choke point — canonical), **(B) organism event transport** (`organism/event_spine.py` — orthogonal, keep), **(C) LLM cognitive execution** (`execution/spine.py` + legacy `runtime/execution_spine.py` — a *different* governance model, soft-verdict not mutation-governed). Plus **(D) parallel "governed" work runtimes** (`governed_work_runtime.py`, `command_runtime.py`) that each self-declare "the only path" yet **bypass the choke point**. Do not conflate C (LLM) with the mutation rivals — the true P1 convergence targets are the **D** runtimes.

Verified live on this tree (line counts from `wc -l`):

| Owner | File | Lines | Governed? | Role today |
|---|---|---|---|---|
| **MutationRouter** (choke point) | `substrate/organism/mutation_router.py` | 190 | **YES** — deterministic rules table, fail-closed | Post-P0 canonical write choke point. `MutationRouter.execute()` @ `:93`. `governed_mutation()` shim @ `transports/api/governed.py:65` delegates here; **77 graph dependents / 367 call sites in 79 files** — an order of magnitude beyond any other runtime. |
| **GovernedExecutionSpine** | `substrate/organism/governed_spine.py` | 889 | **YES** — envelope/approval/rollback/journal | Governed operation spine. Real dependents: `daemon.py`, `mutation_router.py`, 9+ test suites. Idempotency map unbounded (`:133,477-479` — WP-P1-009). |
| **ConcreteExecutionSpine** (8-stage) | `substrate/execution/spine.py` | 522 | **NO** — mandatory memory writes, no governed approval | CONFIRMED_RUNTIME per `.claude/CLAUDE.md`; `ConversationMemory.store`/`AgentMemory.log` on every signal (`:388-433`). Rival #1. |
| **Legacy sync ExecutionSpine** | `substrate/execution/runtime/execution_spine.py` | 228 | **NO** — own AuthorityEngine queue + direct writes | Self-labels legacy (`:16-18`); live Discord path via `services/discord_bot.py`. 0 graph dependents. Rival #2. Migrated by **WP-P1-006** (not this batch). |
| **ExecutionPipeline** | `substrate/execution/pipeline.py` | 557 | partial | Rival #3 — ExecutionPipeline submit path (`:142`). |
| **signal_router** | `transports/api/signal_router.py` | 208 | reads governance | "Enforces the legal processing pathway for all signals" — signal decompose/govern/outcome. Rival #4 (read/signal plane). |
| **organism_loop** | `substrate/organism/organism_loop.py` | 497 | parallel governance | `PolicyEngine → WorkPacketExecutor → CanonicalWritePath → EventSpine` (`:5,23-30`) — a **second governance choke point** disjoint from governed_spine. |
| **event_spine (canonical)** | `substrate/organism/event_spine.py` | 292 | n/a | Canonical event backbone per `PLATFORM_SPEC.md §3`. |
| **event_spine (bridge/rival)** | `substrate/execution/bridge/event_spine.py` | 206 | n/a | Non-canonical. `services/discord_bot.py:108` imports **this** instead of the canonical one. Dual-backbone defect. |

## 2. Every live execution path after P0

Distinct mutation-capable paths reaching state today:

1. **HTTP API → governed_mutation → MutationRouter → GovernedExecutionSpine** — the canonical governed path (~30 call sites). ✅ governed.
2. **organism_loop → PolicyEngine → WorkPacketExecutor → CanonicalWritePath → EventSpine** — parallel governance, disjoint from #1. ⚠️ two choke points for one class of change.
3. **Discord hot path → `execution/runtime/execution_spine.py` (legacy)** — own AuthorityEngine queue + direct `ConversationMemory`/`AgentMemory`/`storage.put`. ⚠️ bypasses governed mutation. (WP-P1-006 owns the cutover; WP-P1-001 only declares canonical + resolves the event_spine import.)
4. **ConcreteExecutionSpine 8-stage (`execution/spine.py`)** — signal processing with mandatory memory writes, no governed approval. ⚠️ ungoverned; pinned "current" by `tests/test_spine_full.py:10`.
5. **ExecutionPipeline (`execution/pipeline.py`)** — submit path. ⚠️ rival.
6. **signal_router (`transports/api/signal_router.py`)** — signal legal-pathway processing (read/decompose/govern). Mostly read/signal; classify read-only or converge.
7. **Mesh remote dispatch → governed_mutation (`remote_node_exec`/`tmux_send`)** — closed & governed by **WP-P0-002** (already merged). ✅ governed.
8. **Event backbone: canonical `organism/event_spine.py` vs rival `execution/bridge/event_spine.py`** — deployed Discord service imports the rival. ⚠️ dual backbone.

## 3. Which runtime becomes canonical for WP-P1-001

**Canonical = the governed spine reached via `governed_mutation()` → `MutationRouter` → `GovernedExecutionSpine`.**

Rationale (evidence, not preference):
- It is the **only governed** mutation path — envelope + risk class + approval + rollback + journal.
- **WP-P0-001 already made `MutationRouter`/`GovernedExecutionSpine` the fail-closed substrate choke point.** Declaring it canonical ratifies reality — the singular-not-larger mandate. `check_ungoverned_mutations.py` enforces this path repo-wide, which *is* the codebase's definition of "governed."
- It is the **most-depended-on surface by an order of magnitude**: the `governed.py` shim = **77 graph dependents / 367 call sites / 79 files**, and it's the only path wired into the daemon singleton (`daemon.py:302`, accessor `:827`). The self-declared rivals `governed_work_runtime` and `command_runtime` have **0 graph dependents** each.
- Deterministic rules table = `GovernedExecutionSpine._governance_check()` (`governed_spine.py:339-374`): unregistered-name reject → allowed-mode check → risk→mode requirement → idempotency reject. No LLM in the decision.

**Canonical event backbone = `substrate/organism/event_spine.py`** (per `PLATFORM_SPEC.md §3`; 14 dependents; the mutation spine emits into it at `governed_spine.py:46`). Note: `execution/bridge/event_spine.py` (`discord_bot.py:108`) is an **Event/EventType data model**, a different layer — verify whether the backlog's "dual event backbone" is a real transport duplication or a conflation with this data model before repointing (see §4).

## 4. Which spines become wrappers / adapters / deprecated / dormant

**Primary convergence targets (the real "rival spines" — three objects each claiming to be "the only path"):**

| Rival | Self-claim | Reality | Disposition under WP-P1-001 | Mechanism |
|---|---|---|---|---|
| **`substrate/organism/governed_work_runtime.py`** (497L) | `:1` "exactly ONE path… the only execution surface… all route through THIS" | routes via `ExecutionCoordinator` + `ApprovalRegistry` (`:242,:250`); **zero `governed_spine`/`governed_mutation` refs** | **Wrapper/adapter onto the canonical spine** — `submit_work`/`execute_work` route through `governed_mutation`/spine (its cockpit callers already do the state write via `governed_mutation`, so this is the lifecycle object, not the write). | route through flag |
| **`substrate/organism/command_runtime.py`** (1353L) | `:1` "canonical intent-to-action layer for all operator surfaces" | routes via `EmpireRouter` (`:1163`); own approval (`:1152`); **no spine refs** | **Wrapper/adapter onto the canonical spine** — mutation-classed commands submit envelopes (this overlaps WP-P1-009, which owns the deeper CommandRuntime governance; P1-001 only declares the demotion). | route through flag |
| **`governed.py:95-110` ungoverned fallback** | — | executes outside the choke point when organism down | **Converge to fail-closed** (coordinate with P0 posture — see §20 note). | remove/gate fallback |

**Orthogonal / lower-priority (do not conflate with the above):**

| Runtime | Disposition | Mechanism |
|---|---|---|
| `substrate/organism/event_spine.py` (canonical event bus, 14 dependents) | **Keep — orthogonal.** The spine emits into it. | none |
| `execution/spine.py` (ConcreteExecutionSpine, LLM lineage) | **Keep as the LLM pipeline; wrap its state/memory writes** through `canonical_write.py:177`. It is CONFIRMED_RUNTIME and soft-verdict-governed, not a mutation rival. **Not deleted.** | staged memory-write routing |
| `execution/runtime/execution_spine.py` (legacy LLM sync) | **Deprecate → adapter.** Live in `operator_api.py:250`/`operator.py:58`; its callers already wrap results in `governed_mutation`. Discord-path cutover + deletion is **WP-P1-006**, not this packet. | doc + declaration now |
| `execution/bridge/event_spine.py` (Discord event *data model*) | **Keep — different layer** (it's an Event/EventType dataclass, not a mutation path). The `discord_bot.py:108` import is legitimate for the data model; the dual-*backbone* concern in the backlog refers to event *transport* — verify whether a repoint is actually needed or the backlog conflated the data model with the bus. | verify, then repoint only if a transport dup exists |
| `governed_execution_runtime.py` (666L, "NEVER executes") | **Dormant read-only dashboard** — deprecate or rename; 0 non-test dependents. | doc |
| `organism_loop` PolicyEngine→WorkPacketExecutor | **Converge** — WorkPacketExecutor submits into the governed path instead of governing independently. | route change behind flag |
| `execution/pipeline.py`, `transports/api/signal_router.py` | **Document read-only / converged** into the canonical submission entry. | migration doc |

> **Scope discipline:** WP-P1-001 *declares* canonicity and demotes `governed_work_runtime` + `command_runtime` to adapters behind a routing flag. The deep per-runtime governance work is spread across sibling P1 packets (WP-P1-006 Discord/legacy-spine, WP-P1-008 workcell/WorkloadRunner, WP-P1-009 CommandRuntime envelopes). P1-001 must not absorb them — it sets the single entry and the arch test that the siblings then satisfy.

## 5. Files touched by WP-P1-001

**Inspect:** `substrate/organism/governed_spine.py`; `substrate/execution/spine.py:388-433`; `substrate/execution/runtime/execution_spine.py`; `substrate/execution/pipeline.py:142`; `substrate/organism/organism_loop.py`; `transports/api/signal_router.py`; `substrate/organism/event_spine.py`; `substrate/execution/bridge/event_spine.py`; `services/discord_bot.py:108`; `substrate/memory/canonical_write.py:177`; `substrate/organism/mutation_router.py`; `ARCHITECTURE.md`; `PLATFORM_SPEC.md §3`; `tests/test_spine_full.py`.

Add to inspect (from spine recon): `substrate/organism/governed_work_runtime.py:1,211-273`; `substrate/organism/command_runtime.py:1,1096-1180`; `substrate/organism/daemon.py:302-337,827` (the `set_governed_spine` injection seam to reuse); `transports/api/governed.py:95-110` (ungoverned fallback).

**Likely modified:**
- `substrate/organism/governed_work_runtime.py` — demote to adapter: `submit_work`/`execute_work` route through `governed_mutation`/spine (behind flag).
- `substrate/organism/command_runtime.py` — demote to adapter (declaration + flag; deep envelope work is WP-P1-009's).
- `substrate/organism/organism_loop.py` — route WorkPacketExecutor through the governed path (behind flag).
- `transports/api/governed.py` — converge the `completed_ungoverned` fallback (`:95-110`) toward fail-closed (coordinate with P0 posture).
- `substrate/execution/spine.py` — route its `ConversationMemory`/`AgentMemory` writes (`:388-433`) through `canonical_write.py:177`. **Behavior otherwise preserved** (CONFIRMED_RUNTIME LLM pipeline, not a mutation rival).
- `services/discord_bot.py` — repoint event import to canonical **only if** the dual-backbone concern is a real transport duplication (verify first — `bridge/event_spine.py` is a data model).
- `tests/test_spine_full.py` — migrate off the ungoverned `ConcreteExecutionSpine` pin, or mark legacy.
- `ARCHITECTURE.md` — correct §9 "One API — transports/api/http/ serves all clients" (the live HTTP authority is `services/operator_api.py:8091`).
- `.claude/CLAUDE.md` — status-taxonomy correction.
- new migration doc: `docs/audits/UMH_P1_SPINE_MIGRATION.md`.

**Reuse, don't invent:** the daemon already has a `set_governed_spine(...)` injection seam used by `workload_runner`, `assisted_executor`, `plan_execution_adapter` (`daemon.py:327-337`) and `cognitive_loop.set_governed_spine` (`:325`). The routing flag and the `governed_work_runtime`/`command_runtime` demotion should wire through this existing seam, not a new mechanism.

**New:** `tests/test_single_spine_architecture.py` (AST arch test), `tests/test_single_event_spine.py`.

## 6. Files touched by WP-P1-007

**Inspect:** `governed_spine.py:256`; `execution_coordinator.py:900-1010`; `command_runtime.py:1186-1310`; `execution/runtime/execution_spine.py:113-127`; `transports/api/{execcoord_routes,executor_routes,agent_routes,approval_routes}.py`; `executor_runtime.py:733-760,1242-1245`; `transports/discord/approval_bridge.py:68-121`; `nodes/distribution/distributor.py:218-262`; `approval_gate.py:38`; `executors/approval_intercept.py:57`; `workstation/unified_approval_runtime.py:43`; `approval_store.py:19`; `sockets/approval_port.py:13-41`; `tests/test_phase31_operator_home.py:122`.

**Likely modified:**
- `substrate/types.py` — new canonical `ApprovalRequest`.
- `substrate/canonical_types.py` — register it.
- `substrate/organism/execution_coordinator.py` — the PlanStore/GovernanceGate becomes the canonical authority holding `ApprovalRequest` (extend, don't fork).
- `substrate/organism/approval_gate.py` — its CAS `claim_approval`/`resolve_approval` folded into the authority; ApprovalPacket → adapter.
- `substrate/sockets/approval_port.py` — typed Pydantic request/response + **fail-closed** when no handler (raise/queue, not silent `{"success": False}`), wired to the canonical authority; **or** removed if left dead.
- `substrate/organism/executor_runtime.py` — replace the **fail-open auto-approve** (`:1245`) with fail-closed reject.
- `executors/approval_intercept.py`, `workstation/unified_approval_runtime.py`, `approval_store.py` — adapters/projections mapping their variants to canonical `ApprovalRequest`; every decision lands in the one authority.
- `substrate/state/stores/approval_store.py` — retire the DEPRECATED SQL store (grep zero importers beyond AuthorityEngine first).
- `transports/discord/approval_bridge.py` — fix alert-origin ≠ resolution-store mismatch (bug 1).
- `transports/api/cockpit_unified_approval_routes.py` — wire `UnifiedApprovalRuntime` to the canonical store via `configure()` (bug 2).
- the four handler-library route files (`execcoord_routes`, `executor_routes`, `agent_routes`, `approval_routes`) — submit envelopes / wrap in `governed_mutation`.
- the three approval-channel adapters (Discord bridge, CC-session, distributor).

**New:** `tests/test_unified_approval_authority.py`, `tests/test_approval_request_canonical.py`; fix `tests/test_phase31_operator_home.py:122` mock to the real type.

## 7. The single approval authority

> **Ground-truth correction (deep recon).** The landscape is worse than the backlog's "4 machines + 2 dict stores" summary: there are **7 decision-owning stores + 1 aggregator + 1 dead seam** plus ~30 cockpit surfaces. `substrate/workstation/unified_approval_runtime.py:6` even self-documents *"11 active approval systems. 6 persistence models."* Two live integrity bugs were found (see §8 bottom). The canonical anchor is therefore chosen by **who owns a durable, audited decision record with a state machine** — not by "which dict store the daemon happens to import."

**One approval authority = the `ExecutionCoordinator` plan-approval store (`substrate/organism/execution_coordinator.py` — `PlanStore` `:619`, `GovernanceGate` `:577`, `approve_plan` `:861`/`deny_plan` `:887`) promoted to THE canonical decision-owner, folding in `OperatorApprovalGate`'s multi-surface CAS protocol (`approval_gate.py:272-339`), keyed by a canonical `ApprovalRequest` (substrate/types.py, registered in canonical_types.py).**

Evidence for choosing the ExecutionCoordinator store over the others:
- It is the **only** store with all four properties: (a) durable per-record persistence (`<coord_data_dir>/plans/{id}.json`), (b) an explicit `CoordinatorApprovalState` state machine (PENDING/APPROVED/DENIED/EXPIRED), (c) an **append-only lifecycle audit trail** (`lifecycle/events.jsonl`), (d) an existing gate other runtimes already honor (`GovernanceGate.can_dispatch`).
- `GovernedWorkRuntime` **already delegates** its approve/reject to `execution_coordinator.approve_plan/deny_plan` (`governed_work_runtime.py:277-333`) — it owns no state, so consolidating here follows the existing flow, not against it.
- `OperatorApprovalGate` (JSONL + CAS claim/resolve, `:272-339`) is the **only concurrency-correct** piece — Discord + cockpit `/claim`+`/resolve` already write there. Its CAS protocol is folded in to serialize multi-surface races into the canonical record.
- The daemon-wired organism `ApprovalStore` (`approval_store.py`), the SQL store (self-marked **DEPRECATED**), the in-memory `ApprovalInterceptService`, and the spine `_pending` deque are all **narrower or ephemeral** — they become sources/adapters, not the authority.

The typed fail-closed **`substrate/sockets/approval_port.py`** remains the trust-boundary seam, but recon confirms it currently has **zero callers** (vestigial). WP-P1-007 either wires the canonical authority behind it (making it load-bearing) **or** documents it dead and removes it — decide during implementation; do not leave a dead seam and a live path in parallel.

## 8. Existing approval stores/surfaces → projections / read-models / adapters

| Existing | Owns a durable record? | Becomes |
|---|---|---|
| **ExecutionCoordinator PlanStore** (`execution_coordinator.py:619`) | **yes — durable + state machine + audit log** | **THE authority** (holds canonical `ApprovalRequest`; single approval-ID namespace) |
| **OperatorApprovalGate CAS** (`approval_gate.py:272-339`) | yes — JSONL + claim/resolve | **folded into the authority** (contributes the multi-surface concurrency protocol) |
| organism `ApprovalStore` (`approval_store.py`, JSONL, daemon-wired) | yes — narrow (blocked signals only) | **adapter/source** → canonical; command-center + Discord-alert origin re-pointed |
| SQL `ApprovalStore` (`substrate/state/stores/approval_store.py`) | yes but **self-marked DEPRECATED** | **retire** |
| `ApprovalInterceptService` (`executors/approval_intercept.py`, in-memory) | yes but **loses state on restart** | **adapter/projection** → canonical (gains persistence via it) |
| GovernedExecutionSpine `_pending` deque (`governed_spine.py:130,256`) | weak — in-memory | **source** — submits into the authority |
| CommandRuntime JSONL lifecycle (`command_runtime.py:1186`) | partial | **source** → adapter |
| Work-packet status field (`work_packet.py` enum) | partial — status only | **state-holder** — reflects the canonical decision |
| legacy AuthorityEngine queue (`execution_spine.py:113-127`) | yes | **source** → adapter (retired with WP-P1-006) |
| **`UnifiedApprovalRuntime`** (`workstation/unified_approval_runtime.py`) | **no — aggregator, owns nothing** | **the read-projection + surface router** (already ~90% there; stop it delegating to divergent stores — point every route at the canonical store) |
| `AuthorityEngine` / `ExecutionAuthorityEngine v1` / `control_plane/governance.py` | no — classifiers/facade | **classifiers** — the ≥4 independent RiskClass→approval tables collapse to one |
| Discord bridge / CC-session buttons / `distributor.py` | no | **channel adapters** registering through the port |
| cockpit routes (§4-many) + `ApprovalCard.tsx` client | no | **read-only projections/surfaces** (cockpit-client single queue is WP-P5-004, later) |
| `substrate/sockets/approval_port.py` | **dead — zero callers** | **wire to canonical or remove** (no dead seam left beside a live path) |

**Integrity bugs to fix as part of 007 (surfaced by recon, not in the backlog text):**
1. **Discord alert-origin ≠ resolution store:** organism `ApprovalStore` raises the alert (`data/umh/organism/approvals.jsonl`, `uuid4` ids) but the Discord Approve/Deny buttons resolve against `OperatorApprovalGate` (`approval_packets.jsonl`, `apk-<hex>` ids) — a Discord approval never resolves the signal it was raised for. Convergence onto one authority closes this.
2. **`UnifiedApprovalRuntime()` instantiated with no sources** (`cockpit_unified_approval_routes.py:24`; the `configure()` seam at `:28` is never called) — the cockpit HUD's aggregated pending list returns empty. Wire it to the canonical store.
3. **`governed_mutation` ungoverned-fallback** (`governed.py:95-104`) bypasses approval when the organism isn't running — must honor P0 fail-closed semantics (coordinate with WP-P0-001 posture).

## 9. What must NOT be deleted

- `substrate/execution/spine.py` — CONFIRMED_RUNTIME. Subordinate, never remove behavior without the migration doc + dependents check + staged cutover.
- Any approval store's records / on-disk JSONL state — additive migration only; adapters preserve old shapes at boundaries.
- `substrate/execution/runtime/execution_spine.py` — do **not** delete in this batch; WP-P1-006 owns its cutover + deletion. Declaration only here.
- The GovernedExecutionSpine journal / trace records — append-only, never rewritten.
- `PLATFORM_SPEC.md` contracts (frozen; corrections to `ARCHITECTURE.md` deployment claims are the only doc edits).

## 10. What must NOT be moved

- No file moves in either packet (hard constraint). Convergence is by **declaration, routing flag, and adapter** — not relocation.
- `governed_mutation` stays where P0 put it (`transports/api/governed.py` shim → substrate MutationRouter). Do not relocate the choke point.
- Approval modules stay in place; only their *types* converge and adapters are added.
- Event spine files stay in place; only the **import in `discord_bot.py:108`** is repointed.

## 11. Required tests (existing, must pass)

- WP-P1-001: `tests/test_gate3_governed_work_runtime.py`, `tests/test_c34_mutation_router.py`, the memory-promotion suite, `tests/test_spine_full.py` (post-migration), `substrate/organism/tests/test_phase61_governed_spine.py` + `test_phase62_spine_enforcement.py` + `test_phase63_autonomous_gate.py`.
- WP-P1-007: `tests/test_phase31_operator_home.py` (with fixed mock), `substrate/organism/tests/test_approval_store.py`, `tests/test_unified_approval_runtime.py`, the P0 fail-closed suites (`tests/test_governed_mutation_fail_closed.py`).
- Both: `pytest --collect-only` exit 0 (WP-P0-011 gate); full mesh + fail-closed suites.

## 12. Required new tests

- WP-P1-001: `tests/test_single_spine_architecture.py` — **AST-based**: no mutation-executing path reaches an executor without a governed verdict; only one spine entry point exported. `tests/test_single_event_spine.py` — grep/AST proves a single event-spine import in the deployed path.
- WP-P1-007: `tests/test_unified_approval_authority.py` — multi-channel approvals (≥3 origin channels) land in one store; **fail-closed** when the port has no handler and when the intercept service is missing. `tests/test_approval_request_canonical.py` — every variant constructible from / convertible to canonical `ApprovalRequest`, round-trip.

## 13. Gate scripts to run (both packets, before "done")

```
python3 scripts/check_dependency_direction.py        # substrate ⊄ transports/services
python3 scripts/check_type_divergence.py             # canonical_types.py registration
python3 scripts/check_instance_leak.py               # no hardcoded instance context in substrate/
python3 scripts/check_projection_leak.py             # projection boundary
python3 scripts/check_cpu_gate.py                     # no raw subprocess in gated dirs
python3 scripts/check_ungoverned_mutations.py --all   # (node_modules noise pre-existing; 0 UMH violations expected)
python3 scripts/check_pytest_collection.py           # collect-only exit 0
python3 scripts/check_credential_injection.py
python3 scripts/check_mesh_relay_firewall.py         # unchanged; regression guard
```

## 14. Rollback plan

- **WP-P1-001:** staged cutover behind a **routing flag** — each subordinated path flips independently; rollback = flip flag off + `git revert` per stage. Journal entries from the governed path are additive (safe). Doc/`.claude` changes are non-executable. `execution/spine.py` behavior preserved until its stage is proven.
- **WP-P1-007:** staged — introduce the unified store as a **shadow reader first** (dual-write, read-old); adapters preserve old shapes at boundaries; revert adapters if drift detected. Canonical `ApprovalRequest` is additive; fail-closed flips are the last stage and independently revertible.
- Neither deletes state; both are reversible without data loss.

## 15. Risk classification

- **WP-P1-001: HIGH** — core execution/event backbone; affects every executing service. Requires clean restart of Discord/operator services.
- **WP-P1-007: HIGH** — core state-authority consolidation across every approval surface; changes the operator approval contract; flips a fail-open path to fail-closed.

## 16. Human approval requirement

**Both require human approval before merge** (`Requires human approval: yes` in the backlog). WP-P1-001 is an architecture decision retiring/subordinating a confirmed-runtime spine. WP-P1-007 has large blast radius and changes the approval contract. Per Batch-1 protocol: implement as draft PRs, hold for operator approval, do not merge without authorization, do not bypass P0 fail-closed semantics.

## 17. Separate PRs?

**Yes — one PR per packet.** `fix/p1-001-canonical-operation-runtime` and `fix/p1-007-single-approval-authority`. Same one-PR-per-packet discipline proven in Batch 1.

## 18. Does WP-P1-007 depend on WP-P1-001?

**Yes — hard dependency.** Backlog `WP-P1-007 → Dependencies: WP-P0-001, WP-P0-004, WP-P1-001` (line 490); critical path `WP-P0-001 → WP-P1-001 → WP-P1-007` (plan §5). WP-P1-007 consolidates approval **around the canonical spine's envelope/verdict flow**, so the canonical runtime must be declared first. **WP-P1-007 is stacked on WP-P1-001** (like WP-P0-002 was stacked on WP-P0-001): implement 001 → get approval/merge → rebase 007 onto merged main → implement/merge 007.

> ⚠️ WP-P0-004 is also a stated dependency of WP-P1-007. Confirm WP-P0-004 is merged/satisfied before WP-P1-007 implementation begins (P0 batch was WP-P0-001/002/007/010/011; **WP-P0-004 was not in Batch 1**). If WP-P0-004 is unmet, WP-P1-007 is **blocked** until it lands — this does not block WP-P1-001.

## 19. Acceptance criteria per packet

**WP-P1-001:**
- AST arch test proves no mutation-executing path reaches an executor without a governed verdict.
- Only one spine entry point exported; the documented single submission entry is referenced by cron/services.
- Dual event_spine resolved — grep shows a single event-spine import in the deployed path.
- `ConcreteExecutionSpine` memory writes go through `canonical_write.py`.
- `ARCHITECTURE.md §9` matches deployment reality.
- `tests/test_spine_full.py` no longer pins the ungoverned variant.
- Discord/operator services restart clean.
- **Proof:** arch-test output; a WorkPacket execution passing governed stages end-to-end (trace/ledger); event-spine import grep; a canonical-path memory write; corrected-doc diff; container restart logs.

**WP-P1-007:**
- One registered `ApprovalRequest`; all variants round-trip.
- Unregistered `approval_port` handler **raises/queues** (never silent no-op).
- Every approval (spine, coordinator, command, node, Discord, CC) lands in one auditable store.
- "What is pending approval?" returns a single unified view.
- Executor-runtime with no intercept service **rejects** (not auto-approve).
- Discord approval round-trip works.
- **Proof:** unified pending-approval query spanning ≥3 channels; fail-closed log for missing intercept service; round-trip test output; a live/TestClient approval-flow trace.

## 20. No-go list (both packets)

- ❌ No mega-rewrite. ❌ No file moves. ❌ No file deletes (esp. CONFIRMED_RUNTIME `execution/spine.py`; legacy `execution_spine.py` deletion is WP-P1-006's, not this batch).
- ❌ No new dependencies. ❌ No new spine. ❌ No new/parallel approval store.
- ❌ No projection feature work (cockpit `unifiedApprovalStore` is WP-P5-004; EOS product-approval is WP-P4-009).
- ❌ Do not bypass P0 fail-closed semantics. ❌ No fail-open degraded paths — the executor-runtime auto-approve fallback (`executor_runtime.py:1245`) flips to fail-**closed**, and the `governed.py:95-110` `completed_ungoverned` shim fallback converges toward it (do not add new ungoverned paths).
- ❌ Do not repoint `discord_bot.py:108` (event backbone) without first proving a real transport duplication — it may be a data-model vs bus conflation in the backlog.
- ❌ Do not absorb sibling P1 packets into 001: WP-P1-006 (Discord/legacy spine), WP-P1-008 (workcell/WorkloadRunner), WP-P1-009 (CommandRuntime envelopes) own the deep per-runtime work. 001 declares canonicity + demotes the two rivals to adapters behind a flag.
- ❌ `substrate/` must not import `transports/`/`services/` (Discord bridge registers via the port).
- ❌ Do not treat the unprovisioned mesh secrets (from WP-P0-002) as a code failure or a P1 blocker.
- ❌ Do not restart all services simultaneously; CPU-gate any spawned work.
- ❌ Do not mark complete without tests + proof (AST arch test + governed-trace for 001; unified-query + fail-closed logs for 007).

---

## 21. Exact implementation prompt for WP-P1-001 only

> **Mission:** Implement **WP-P1-001 — establish one canonical governed operation runtime** as a single draft PR off latest `main`. Declare the governed spine (`governed_mutation` → `MutationRouter` → `GovernedExecutionSpine`) as **the** canonical operation runtime and subordinate/retire the rivals **by declaration, routing flag, and adapter — never by rewrite, move, or delete.** The system must become more singular, not larger.
>
> **Branch:** `fix/p1-001-canonical-operation-runtime` off `main`. One PR. Draft. **Do not merge.**
>
> **Preconditions to verify first:** `main` is at `fc0a96304` or newer; WP-P0-001 is merged (`governed_mutation` fail-closed choke point in `substrate/organism/mutation_router.py`, shim at `transports/api/governed.py:65`). Read every "Files to inspect" file before editing. Run `scripts/query_graph.py dependents` on each spine before touching it.
>
> **First, verify ground truth (three carried-context items are known-wrong or unverified — confirm on live HEAD before designing):**
> - `grep -rln degraded_mode_allowed` — expected **empty**. `MutationSpec` has no degraded flag; do not design around one.
> - `grep -n "completed_ungoverned" transports/api/governed.py` — the ungoverned fallback (`:95-110`) is expected to **still exist**. P0 fail-closed landed on the substrate path; this shim fallback survived. Decide its disposition in this packet.
> - Confirm whether `bridge/event_spine.py` (a Discord Event/EventType *data model*) is genuinely a duplicate *event transport* of `organism/event_spine.py`, or the backlog conflated the data model with the bus. **Do not repoint `discord_bot.py:108` unless a real transport duplication exists.**
>
> **Do (each step behind a routing flag, deterministic-first, no LLM in routing):**
> 1. **Declare canonical:** the governed spine via `governed_mutation` → `MutationRouter` → `GovernedExecutionSpine` (backed by `mutation_registry`) is THE operation runtime. Export exactly one documented submission entry. Add the AST arch test that enforces it.
> 2. **Demote the two self-declared rivals to adapters** (the real convergence target): `governed_work_runtime.py` (`submit_work`/`execute_work` → route through `governed_mutation`/spine; today it uses `ExecutionCoordinator`+`ApprovalRegistry`, `:242,:250`) and `command_runtime.py` (declaration + flag only; deep envelope routing is WP-P1-009). **Reuse the existing `daemon.set_governed_spine(...)` injection seam** (`daemon.py:327-337`) — do not invent a new wiring mechanism.
> 3. **Converge organism_loop:** route `WorkPacketExecutor` (`organism_loop.py:23-30`) through the governed path so the two governance choke points become one.
> 4. **Converge the `governed.py` ungoverned fallback** (`:95-110`) toward P0 fail-closed semantics — no `completed_ungoverned` execution outside the choke point. Coordinate posture with WP-P0-001; behind the flag.
> 5. **Route `execution/spine.py` memory writes** (`ConversationMemory`/`AgentMemory`, `:388-433`) through `canonical_write.py:177`. This is the LLM lineage — **preserve its pipeline behavior**, only redirect the memory-write side. Do not treat it as a mutation rival; do not remove behavior (CONFIRMED_RUNTIME).
> 6. **Migrate the test pin:** `tests/test_spine_full.py:10` must stop pinning the ungoverned `ConcreteExecutionSpine` — migrate to `GovernedExecutionSpine` or mark it explicitly legacy.
> 7. **Correct the docs:** fix `ARCHITECTURE.md §9` "One API — transports/api/http/ serves all clients" to deployment reality (live HTTP authority is `services/operator_api.py:8091`); correct `.claude/CLAUDE.md` status taxonomy. Write `docs/audits/UMH_P1_SPINE_MIGRATION.md` documenting every rival's disposition (canonical / adapter / deprecate / keep-orthogonal / read-only) + staged cutover + per-stage rollback.
> 8. **Declare-only (no behavior change here):** `execution/runtime/execution_spine.py` (legacy — WP-P1-006 owns its cutover/deletion), `pipeline.py`, `signal_router.py`, `governed_execution_runtime.py` (dormant "never executes" dashboard) — document their dispositions in the migration doc.
>
> **New tests (required):**
> - `tests/test_single_spine_architecture.py` — **AST-based**: assert no mutation-executing code path reaches an executor without a governed verdict, and that exactly one spine entry point is exported. This is the verification spine of the whole packet — it must genuinely fail when a bypass is injected.
> - `tests/test_single_event_spine.py` — **only if** step-0 confirms a real dual event *transport*; assert a single event-spine import in the deployed path. If it's a data-model/bus distinction, drop this test and document why.
>
> **Run and attach as proof:** the new arch test(s); `tests/test_gate3_governed_work_runtime.py`; `tests/test_c34_mutation_router.py` (**note:** the registry test asserts `>= 46` specs — `test_c40a_runtime_convergence.py:315`); the memory-promotion suite; `tests/test_spine_full.py` (post-migration); `substrate/organism/tests/test_phase61_governed_spine.py`, `test_phase62_spine_enforcement.py`, `test_phase63_autonomous_gate.py`; `pytest --collect-only` (exit 0). A trace/ledger record showing a WorkPacket execution passing governed stages end-to-end via the demoted `governed_work_runtime` adapter. A memory write via the canonical path. The corrected-doc diff. Clean `docker logs os-discord` + operator restart logs (restart individually, never all at once; CPU-gate).
>
> **Gates (all must pass):** `check_dependency_direction.py`, `check_type_divergence.py`, `check_instance_leak.py`, `check_projection_leak.py`, `check_cpu_gate.py`, `check_pytest_collection.py`, `check_ungoverned_mutations.py --all` (node_modules noise is pre-existing; assert 0 UMH violations), `check_credential_injection.py`.
>
> **Hard constraints:** No mega-rewrite. No file moves. No file deletes. No new dependencies. No new spine. Do not bypass P0 fail-closed semantics. No fail-open degraded paths. `substrate/` must not import `transports/`/`services/`. Python 3.11 syntax only. Staged behind a routing flag with per-stage rollback. **Do not merge — draft PR, hold for human approval** (HIGH risk, architecture decision retiring/subordinating a confirmed-runtime spine).
>
> **Definition of done (before you claim it):** re-audit as a hostile reviewer; the AST arch test genuinely fails when a bypass is injected; the governed-trace proof shows real end-to-end execution through the demoted adapters; the ground-truth checks (no `degraded_mode_allowed`; ungoverned fallback converged) hold; services restart clean. Report with the full proof set. Do not start WP-P1-007 — it is stacked on this **and** blocked until WP-P0-004 (CC-webhook auth) lands (verified **not** merged as of this plan).

---

## Final planning verdict

- **Recommended first implementation packet:** **WP-P1-001** — it is the keystone; WP-P1-007 is stacked on it.
- **Is WP-P1-001 safe to implement?** **Yes**, as a staged, flag-gated, draft PR with the AST arch test as the verification spine and no deletes/moves. It ratifies the P0 choke point rather than building new infrastructure. Hold for human approval before merge (HIGH).
- **WP-P1-007 gating note (verified):** WP-P1-007 depends on **WP-P0-004** (CC-webhook auth), which is **NOT merged** — Batch 1 shipped only WP-P0-001/002/007/010/011 (git confirms WP-P0-004 has no PR/commit). **WP-P1-007 is therefore blocked** until WP-P0-004 lands, and it is stacked on WP-P1-001. **This does not gate WP-P1-001.** Recommended sequence: implement + merge WP-P1-001 → land WP-P0-004 → rebase + implement WP-P1-007.
- **Ground-truth corrections folded in (grep-verified on live HEAD):** `MutationSpec.degraded_mode_allowed` does not exist; the `governed.py:95-110` `completed_ungoverned` ungoverned fallback still exists (P0 fail-close was substrate-path only); the real convergence rivals are `governed_work_runtime.py` + `command_runtime.py` (not the LLM `execution/spine.py`); the canonical approval authority is the ExecutionCoordinator PlanStore + OperatorApprovalGate CAS (not the daemon-wired dict store); three approval integrity bugs surfaced (Discord store mismatch, unwired UnifiedApprovalRuntime, ungoverned-fallback approval skip).
