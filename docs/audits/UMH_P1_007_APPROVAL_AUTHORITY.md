# WP-P1-007 — One Canonical Approval Authority

**Branch:** `fix/p1-007-single-approval-authority` off `origin/main @ 9a17c1234` (contains #148 / WP-P1-001 and #149 / WP-P0-004).
**Risk:** HIGH — state-authority consolidation across every approval surface; changes the operator approval contract; flips fail-open seams to fail-closed.
**Mandate:** the system becomes *more singular, not larger*. No new approval store. No file moves/deletes. No new dependencies. Additive canonical type + per-source adapters + fail-closed flips, staged.

This document is the authoritative implementation spec, verified against the live tree by three recon passes (schemas, state machines, channels/routes). Line numbers below are live at `9a17c1234`.

---

## 1. Ground truth — the fragmentation (verified)

### 1.1 Eight approval lifecycle stores

| # | Store / gate | File | Medium | Durable | CAS |
|---|---|---|---|---|---|
| 1 | `GovernedExecutionSpine._pending` | `substrate/organism/governed_spine.py:130` | RAM deque + audit JSONL | No (queue) | pop-once (weak) |
| 2 | **`PlanStore` + `GovernanceGate`** | `substrate/organism/execution_coordinator.py:617,577` | per-plan JSON + lifecycle JSONL | **Yes** | status-guard, **not atomic** |
| 3 | `CommandHistory` | `substrate/organism/command_runtime.py:1012` | JSONL | Yes | check-and-rewrite (process-local) |
| 4 | `AuthorityEngine` → SQL `ApprovalStore` | `substrate/execution/runtime/execution_spine.py:113` → `substrate/state/stores/approval_store.py:16` | Neon/Postgres | Yes | conditional UPDATE (no status guard) |
| 5 | **`OperatorApprovalGate`** | `substrate/organism/approval_gate.py:105` | RAM dict + append-only JSONL | Yes-ish | **explicit CAS under lock** |
| 6 | `ApprovalInterceptService` | `substrate/organism/executors/approval_intercept.py:127` | RAM dict + `threading.Event` | **No** | status-guard under lock |
| 7 | `ApprovalStore` (organism) | `substrate/organism/approval_store.py:19` | JSONL + `fcntl` | Yes | no status guard on `decide()` |
| 8 | `ApprovalStore` (state/SQL, DEPRECATED dup) | `substrate/state/stores/approval_store.py:16` | Neon/Postgres | Yes | conditional UPDATE |

### 1.2 Six approval data shapes, no canonical type

| Shape | File:line | Richness |
|---|---|---|
| `ApprovalPacket` (30 fields, incl. CAS fields) | `substrate/organism/approval_gate.py:37` | **richest — superset spine** |
| `ApprovalInterceptRequest` | `substrate/organism/executors/approval_intercept.py:56` | executor intercept |
| `UnifiedApproval` | `substrate/workstation/unified_approval_runtime.py:42` | read-projection item |
| `UnifiedApprovalItem` | `substrate/workstation/unified_execution_surface_runtime.py:68` | read-projection item (variant) |
| organism `ApprovalStore` dict record | `substrate/organism/approval_store.py:74` | JSONL record |
| SQL `ApprovalStore` row | `substrate/state/stores/approval_store.py:17` | opaque `request_json` blob |

Field-name instability across shapes: id (`packet_id`/`approval_id`/`id`/`work_id`/`decision_id`), risk (`risk_class`/`risk_level`), created-time (`created_at`/`requested_at`/`waiting_since`), decided-by (`decided_by`/`resolved_by`). Two state vocabularies: `rejected` (gate/intercept) vs `denied` (coordinator/executor), plus `auto_approved`, `expired`.

### 1.3 Three confirmed live defects

1. **Discord store mismatch (silent failure).** Alert originates in Store A `approvals.jsonl` (`substrate/organism/approval_store.py:75,90`, `uuid4` id); the Discord button is built with that Store-A id (`transports/discord/approval_bridge.py:207`); the button *resolves* against Store B `OperatorApprovalGate` (`approval_bridge.py:79-81,119-121`). Store-A ids never exist in Store B → `claim_approval` returns `False` → the operator sees "Already claimed by another surface" and the approval is never recorded resolved. Store A's own `decide()` is never called by Discord.
2. **`UnifiedApprovalRuntime` unconfigured → cockpit pending always empty.** `transports/api/cockpit_unified_approval_routes.py:24` builds `UnifiedApprovalRuntime()` with zero source args; all 10 sources default `None`; `configure()` is never called in production → `GET /unified-approval/pending` returns `[]`.
3. **`approval_port` vestigial.** `substrate/sockets/approval_port.py` — zero callers tree-wide; untyped `Callable`; returns `{"success": False, ...}` when unregistered (not fail-closed, not typed).

### 1.4 Two bonus defects surfaced (approval-authority bugs — in scope)

4. **Broken import.** `substrate/workstation/unified_execution_surface_runtime.py:331,398,418` imports `OperatorApprovalGate` from `substrate.organism.executors.approval_intercept`, which defines it **zero** times. It lives in `substrate/organism/approval_gate.py:105`. Those paths raise `ImportError` at runtime.
5. **Stale fail-open docstring (behavior already correct).** `substrate/organism/executor_runtime.py:1245-1246` docstring says "auto-approves (fail-open …)", but the code at `:1253-1255` already returns `False` / blocks when the intercept service is missing. Fail-CLOSED already; only the docstring lies. (Same class of finding as WP-P1-001: P0 hardened the behavior, the comment lagged. Fix the docstring; lock the behavior with a regression test; do **not** touch the already-correct control flow.)

---

## 2. Canonical decision

**One canonical `ApprovalRequest`** (in `substrate/types.py`, registered in `canonical_types.py`) that every variant round-trips into/out of.

**Authority = `ExecutionCoordinator.PlanStore` + `GovernanceGate`** as the durable plan authority, **folded with `OperatorApprovalGate`'s CAS claim/resolve semantics** as the interactive multi-surface decision mechanism. No new store: the coordinator's per-plan JSON + lifecycle JSONL is the durable spine; the gate's lock-guarded compare-and-swap is the anti-double-resolve mechanism. A thin **`ApprovalAuthority`** facade (new module `substrate/organism/approval_authority.py`) exposes the unified surface — create / pending / claim / resolve — projecting each origin's records into canonical `ApprovalRequest` and preserving the source record.

**`UnifiedApprovalRuntime` becomes the read projection** over the canonical authority: `configure()` is called with real sources so the cockpit's "what is pending" spans ≥3 channels.

**`approval_port` becomes the typed fail-closed trust seam.** Pydantic request/response; unregistered handler **raises** `ApprovalPortUnavailable` (fail-closed), never a silent no-op. The Discord/cockpit surfaces register the canonical authority behind it.

---

## 3. Canonical `ApprovalRequest` design

`substrate/types.py`, Pydantic v2 `BaseModel` matching in-module idiom. Superset of `ApprovalPacket` with canonical field names and alias-preservation.

```
class ApprovalState(str, Enum):
    PENDING, APPROVED, REJECTED, EXPIRED, PROVIDE_INPUT
    # DENIED is accepted as an input alias for REJECTED in adapters (coordinator/executor vocab)

class ApprovalOrigin(str, Enum):
    SPINE, COORDINATOR, COMMAND, EXECUTOR_INTERCEPT, DISCORD, CC_SESSION, NODE_DISTRIBUTION,
    ORGANISM_STORE, GOVERNED_WORK, SANDBOX_GATE, OTHER

class ApprovalRequest(BaseModel):
    approval_id: str                      # canonical id namespace (apr-...)
    source_origin: ApprovalOrigin
    source_id: str = ""                   # the origin's native id (packet_id/plan_id/request_id/...)
    source_channel: str = ""              # free-form origin surface label
    title / description
    operation / requested_action
    risk_class: RiskClass                 # canonical; adapters map risk_level→risk_class
    state: ApprovalState
    requester_identity / decided_by
    org_id / operator_id / session_id     # tenant/operator context where available
    created_at / expires_at / decided_at  # canonical timestamps (utc datetime)
    claimed_by_surface / resolved_by_surface   # CAS/multi-surface
    version: int = 0                      # optimistic-lock for cross-call CAS
    proof_id / trace_id                   # audit linkage
    rejection_reason / operator_input
    metadata: dict
    def to_dict(self) -> dict             # includes at least approval_id + status
    @property status(self) -> str         # test-contract alias for state.value
```

Test contract satisfied: `.approval_id`, `.status` (property → `state.value`), `.to_dict()`; store facade offers `list_pending()` + `pending_count` property.

---

## 4. Staged rollout (revertible)

- **Stage 1 (additive, zero behavior change):** canonical `ApprovalRequest` + `ApprovalState`/`ApprovalOrigin` in `substrate/types.py`; register in `canonical_types.py`; `substrate/organism/approval_authority.py` with pure round-trip adapters for every variant. Nothing wired yet. Fully revertible (delete additive files).
- **Stage 2 (shadow read):** `ApprovalAuthority.pending()` projects across origins into canonical `ApprovalRequest`; `UnifiedApprovalRuntime` configured with real sources; cockpit route reads the projection. Read-only — no resolution path changes. Revert = restore the empty `UnifiedApprovalRuntime()`.
- **Stage 3 (fix live bugs, converge resolution):** Discord alert-origin and button-resolution address the **same** authority record; fix the broken `OperatorApprovalGate` import; correct the executor docstring; type the `approval_port` and make unregistered fail-closed.
- **Stage 4 (fail-closed flips + CAS, last):** fold `OperatorApprovalGate` CAS into the authority; add `version`/PENDING-guard CAS to coordinator `approve_plan`/`deny_plan` (close the `deny_plan` missing-guard race). Independently revertible per method.

Behavior default remains prior behavior wherever a flag guards a routing change (consistent with `UMH_CANONICAL_RUNTIME_ROUTING` staying OFF — this packet does not enable it).

---

## 5. Forbidden (enforced)

- No new parallel approval store.
- No auto-approve on port failure or missing intercept (fail-closed, including missing-intercept).
- `substrate/` must not import `transports/` (Discord registers via the port).
- Type-coherence registration for the canonical type.
- No file moves/deletes; no new dependencies; Python 3.11.
- Do not enable `UMH_CANONICAL_RUNTIME_ROUTING`. Do not start WP-P1-008/009 or projection work.

---

## 6. Acceptance criteria → proof mapping

| Criterion | Proof |
|---|---|
| One registered `ApprovalRequest` | `canonical_types.py` entry + `test_approval_request_canonical.py` registration assertion |
| All variants round-trip | `test_approval_request_canonical.py` round-trip per variant |
| Unregistered `approval_port` raises | `test_unified_approval_authority.py` fail-closed test |
| Every origin lands in one auditable store | `test_unified_approval_authority.py` ≥3-channel test |
| Unified "what is pending" query | `ApprovalAuthority.pending()` + projection test |
| Executor with no intercept rejects | `test_unified_approval_authority.py` missing-intercept test (locks the already-fail-closed behavior) |
| Discord round-trip resolves displayed record | `test_unified_approval_authority.py` Discord same-record test |
| CAS prevents double-resolve | `test_unified_approval_authority.py` two-surface CAS test |
| No new store / no upward imports | gates + grep proof |
