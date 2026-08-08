# Wave 2 — Green-Pass sys.path Substrate Preseed Correction

**Authorized by:** OWNER DECISION — "ACCEPT GREEN-PASS SYS.PATH HARNESS DEFECT.
AUTHORIZE ONE BOUNDED HARNESS CORRECTION FOR THE WORKTREE-SUBSTRATE PRESEED / GREEN
RUN PATH." (2026-08-08). NO field execution, NO quota consumption.

**Prior SHA (defective green path):** `4778030c7f62e46c831826e9cef04d99f1365a3c`
**Field defect that triggered this:** invocation #51, run `20260808T213735Z-p1`
(Green Pass 1) — `ModuleNotFoundError: No module named 'substrate.execution.attempts'`
at `scripts/wave2_field_dispatch.py:2713` (`_capture_execution_binding`). Collector
reached w15 (consumed one mandatory unit); zero attempts created; candidate innocent.

---

## 1. Module-resolution topology (measured, before → after)

**Split-tree condition (measured):**
- Worktree `substrate/execution/attempts/field_scenario_map.py` — PRESENT.
- `/opt/OS` (main, `6952687274545911e29f1859b8e563199a2d2203`)
  `substrate/execution/attempts/` — ABSENT (`ls: No such file or directory`).

**Before (defective):**
```
green run_passes
  → _wait_candidate_ready / _verify_beast_collector_commit
      → _mesh_read → sys.path.insert(0, "/opt/OS")
          → import substrate.sockets.mesh_dispatch_port
              ⇒ sys.modules["substrate"]           = /opt/OS/substrate/__init__.py
              ⇒ sys.modules["substrate.execution"] = /opt/OS/substrate/execution/__init__.py
  → _wait_for_bindable_grant → _capture_execution_binding
      → sys.path.insert(0, _WORKTREE)     # too late — parent already cached
      → from substrate.execution.attempts.field_scenario_map import ExecutionBinding
          ⇒ substrate.execution.attempts resolved as a subpackage of the CACHED
            /opt/OS-rooted substrate.execution → /opt/OS/substrate/execution/attempts/
          ⇒ ModuleNotFoundError: No module named 'substrate.execution.attempts'
```

**After (corrected):**
```
green run_passes
  → (mesh reads still cache /opt/OS substrate — unchanged)
  → _preseed_worktree_substrate()          # NEW, at the one boundary green first needs it
      1. sys.path: remove stale copies of _WORKTREE, insert _WORKTREE at [0]
      2. evict every substrate/substrate.* module whose __file__ is NOT under _WORKTREE
  → _wait_for_bindable_grant → _capture_execution_binding
      → from substrate.execution.attempts.field_scenario_map import ExecutionBinding
          ⇒ substrate               = <worktree>/substrate/__init__.py
          ⇒ substrate.execution     = <worktree>/substrate/execution/__init__.py
          ⇒ substrate.execution.attempts = <worktree>/substrate/execution/attempts/__init__.py
          ⇒ SUCCEEDS
```
Reproduction transcript: `measurement_reproduction.txt` (this dir).

## 2. Exact stale-module causal chain
The mesh reads that precede the binding wait import `substrate.sockets.mesh_dispatch_port`
from `/opt/OS`, populating `sys.modules["substrate"]` and `sys.modules["substrate.execution"]`
with `/opt/OS`-rooted packages. Python resolves any later `substrate.execution.attempts`
as a child of the ALREADY-CACHED `substrate.execution` package object, whose `__path__`
points at `/opt/OS/substrate/execution/` — which has no `attempts/`. A later
`sys.path.insert(0, _WORKTREE)` does not help because the parent package is already bound.

## 3. There is no `_preseed_worktree_substrate()` in the prior tree
The owner directive and the prior session summary referenced a helper
`_preseed_worktree_substrate()` in a "frozen failure/recovery driver." **Measured: that
function did not exist anywhere in the repo, and there is no frozen driver file.** The
codebase's actual cache-bypass precedent is `_import_field_task_scope()` — an
`importlib.util.spec_from_file_location` LEAF load. The correction creates
`_preseed_worktree_substrate()` for the first time, named to match the invariant it
enforces.

## 4. Was a leaf importlib load sufficient? — NO (measured)
Approach A (importlib `spec_from_file_location` for `field_scenario_map` from the worktree,
stale parent left cached) **FAILED** with the same `ModuleNotFoundError`: the leaf's own
line-68 internal import `from substrate.execution.attempts.field_task_scope import ...`
still resolves against the stale `/opt/OS` parent. **The whole `substrate.execution*`
subtree — the package identity — must resolve from the worktree.** This is the owner's
item-8 "broader import-boundary context," and it is why the fix evicts the cached subtree
rather than loading one module. Proof: `measurement_reproduction.txt` STEP 3.

## 5. Design requirement satisfied
Harness invariant enforced: *a qualification run for candidate worktree W imports
qualification-facing candidate modules from W, not from /opt/OS merely because /opt/OS was
imported earlier.* Deterministic (path front-load + cache eviction), idempotent, and
NEVER silently falls back to `/opt/OS` (a missing worktree package raises on the
subsequent import — fail-closed, never swallowed). The green and failure/recovery paths
resolve the SAME candidate implementation, differing only in failure injection.

## 6. Files changed (within the authorized surface)
- `scripts/wave2_field_dispatch.py`
  - NEW `_preseed_worktree_substrate()` (beside `_import_field_task_scope`).
  - `run_passes`: call `_preseed_worktree_substrate()` (non-dry-run) at the w15 → binding
    boundary, BEFORE `_wait_for_bindable_grant`.
- `tests/test_wave2_run_passes_runner_lifecycle.py` — +14 tests (see §7).

**No candidate execution modules touched.** No scheduler, poller, verification,
composition, promotion, projection, retention, Task-D, declaration/store authority,
lifecycle, WorkPacket/schema, or frozen candidate source changed.

## 7. Behavioral tests (14 new; 41 total in file)
- `test_preseed_precondition_opt_os_lacks_attempts` — pins the precondition (/opt/OS cached, lacks attempts).
- `test_plain_import_crashes_without_preseed` — reproduces the crash deterministically.
- `test_preseed_resolves_worktree_attempts_after_pollution` — substrate/execution/attempts all from worktree.
- `test_preseed_capture_binding_import_resolves` — the exact `_capture_execution_binding` import resolves.
- `test_preseed_resolves_internal_leaf_dependency` — the leaf's internal dep (field_task_scope) from worktree (leaf-only would fail).
- `test_preseed_is_idempotent` — second call is a clean no-op.
- `test_preseed_puts_worktree_first_on_syspath` — worktree at sys.path[0], exactly once.
- `test_preseed_no_cross_worktree_accumulation` — repeated passes leave one worktree identity.
- `test_green_preseeds_before_binding_wait` — MOST IMPORTANT ordering: preseed precedes grant_wait + write_binding.
- `test_green_full_lifecycle_order_includes_preseed` — w15 → preseed → grant_wait → write_binding → runner.
- `test_mutation_remove_preseed_reproduces_crash` — the crash returns without the preseed.
- `test_mutation_preseed_wrong_root_leaves_stale` — wrong-root preseed still fails.
- `test_capture_binding_import_not_swallowed` — the import must RAISE, never be caught-and-continued.
- `test_failure_recovery_import_path_unchanged` (tightened) — each CLI subcommand keeps its exact `sys.path.insert(0, str(_WORKTREE))` guard.

## 8. Mutation sweep — 0 non-equivalent survivors (11/11 killed)
| Mutation | Result |
|---|---|
| M1 remove preseed call | KILLED |
| M2 preseed AFTER binding wait | KILLED |
| M3 evict only bare `substrate` (skip `substrate.execution*`) | KILLED |
| M4 no eviction (path-only) | KILLED |
| M5 preseed wrong root (/opt/OS) | KILLED |
| M6 worktree appended after /opt/OS (not insert-first) | KILLED |
| M7 catch ModuleNotFoundError and continue | KILLED |
| M8 non-idempotent path accumulation | KILLED |
| M9 strip `_WORKTREE` guard from write_scenario_map (break failure/recovery) | KILLED |
| HM1 bare `startswith(wt)` (no os.sep boundary) — sibling-worktree prefix superset retained | KILLED |
| HM2 retain anchorless `substrate.*` (require anchor before eviction) | KILLED |

## 9. Independent review pair — both PASS
Two fresh adversarial reviewers (no shared context), each answering the owner's two
questions and hunting for Wave-2-blocking findings:

**PRIMARY** — "Can the canonical green qualification path accidentally import candidate
control-plane modules from /opt/OS or another stale worktree?"  **Reviewer A: NO.
Reviewer B: NO.** (Both reproduced the exact pollution + fix end-to-end; both verified
ordering — no in-process attempts import precedes the preseed; both verified the candidate
runner runs as a fresh subprocess unaffected by caching.)

**SECONDARY** — "Do failure/recovery and green resolve the same candidate implementation,
differing only in failure injection?"  **Reviewer A: YES. Reviewer B: YES.** (Green reuses
the exact `_capture_execution_binding` authority; the four failure/recovery CLI subcommands
retain their own `_WORKTREE` guards, unchanged.)

**Critical / Wave-2-blocking-High: NONE (both reviewers).**

Both reviewers independently raised the same LOW observation — the `startswith(wt)`
eviction boundary lacked an `os.sep` terminator (a sibling worktree whose path is a
prefix superset would be wrongly retained). Because two independent reviews converged on
it and it strengthens the exact invariant under review, it was applied as a bounded
hardening (§ os.sep boundary + anchorless eviction), pinned by two new tests
(`test_preseed_evicts_sibling_worktree_prefix_superset`,
`test_preseed_evicts_anchorless_substrate_module`) and mutations HM1/HM2. No reviewer
finding was left open.

## 10. Non-field requalification (all green)
- `tests/test_wave2_run_passes_runner_lifecycle.py` + `tests/test_wave2_dispatch_import_paths.py`: 45 passed.
- All 64 genuine `tests/test_wave2_*.py` files: **1730 passed, 0 failed**.
- Gates: `check_type_divergence --registry-audit` (1165 entries, 0 dup, 23 exemptions) ✓;
  `check_dependency_direction` ✓; `check_cpu_gate` ✓; `check_ontology_homes` ✓;
  `check_projection_leak` ✓; `check_instance_leak` ✓; `check_ontology_layers` ✓ (all exit 0).
- `ruff format --check` + `ruff check` on both changed files: clean.

**NOTE — the only failures anywhere are pre-existing and unrelated.** `tests/test_phase14_8b_wave2.py`
(a capability-generation endpoint file, NOT a Wave 2 attempts/composition file, not touched
by this change) fails `14 failed / 26 errors` due to a hardcoded path to a DELETED worktree
`/opt/OS/.claude/worktrees/phase-14-7b-cockpit-usability/transports/api/cockpit.py`. Proven
pre-existing: with this change stashed, the clean `4778030c7…` baseline produces the
IDENTICAL failure set. Causally isolated from this correction.
