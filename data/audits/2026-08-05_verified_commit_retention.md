# Verified-commit retention + explicit trusted sandbox base

Closes the half of the field defect that is **fully wired and independently
proven**. Deterministic fan-in composition is deliberately NOT included — see
"Composition work packet" at the end.

## The defect

Field run `20260805T182714Z-p1` proved governed dependency **ordering** works and
dependency **content propagation** does not:

```
1785954665.640  ea-504fc3e29496  backend      succeeded   ← verifier-approved
                    ↓ terminalize → release(cleanup=True) → git branch -D
1785954665.696  ea-1bedcbdb4aa1  integration  leased      ← 56 ms later, content gone
```

`git cat-file -t c2783aa` → `fatal: Not a valid object name`. The integration
worker was contractually told to reconcile branches it could not see, and
correctly produced zero files.

## Reachable lifecycle — before / after

```
BEFORE                                  AFTER
attempt SUCCEEDED                       attempt SUCCEEDED
  → terminalize                           → terminalize
      (3) _release_lease                      (2b) _retain_verified   ← NEW, ordered first
          → cleanup_sandbox                        → refs/umh/verified/<c>/<r>/<t>/<a>
          → git branch -D                      (3) _release_lease
          → COMMIT UNREACHABLE                     → cleanup_sandbox
                                                   → git branch -D
                                                   → commit still reachable via its ref
```

Plus: `create_sandbox(base_commit=…)` and `LeaseManager.acquire(base_commit=…)`
now accept an **optional** trusted explicit base. Omitted, behaviour is
byte-identical to before.

## Exact changed files

| File | Change |
|---|---|
| `substrate/execution/attempts/verified_commit_retention.py` | **new** — retention, resolution, authorized release |
| `substrate/execution/attempts/terminalization.py` | `_retain_verified` ordered **before** `_release_lease`; retention gate blocks destructive cleanup; authoritative binding from persisted records; `retained_commit` / `lease_withheld_reason` / `sandbox_slot_freed` on the result; `_preserve_sandbox_slot` frees the concurrency slot on a withhold |
| `substrate/execution/attempts/poller.py` | `_terminalize` distinguishes a **deliberate withhold** from a release fault, so the RV-HIGH-2 healer no longer force-revokes (revoke → `cleanup_sandbox` → `git branch -D` destroyed the commit the withhold protected) |
| `substrate/execution/attempts/leases.py` | `acquire(base_commit=…)` → sandbox + `snapshot_ref`; signature-checked capability; divergence refused |
| `substrate/organism/worktree_sandbox.py` | `create_sandbox(base_commit=…)`, fail-closed resolve, launched-base proof; `cleanup_sandbox(preserve_branch=…)` slot-release seam (default unchanged); `WorktreeSandbox.branch_preserved` sticky+persisted so no later cleanup can delete a preserved branch |
| `tests/test_wave2_verified_commit_retention.py` | **new** — 67 tests on the real shipped path, incl. the production `poller._terminalize` caller |

**Reverted byte-identically to the committed base** (composition removal):
`substrate/execution/attempts/lifecycle.py`, `substrate/execution/attempts/records.py`,
`substrate/canonical_types.py`. **Deleted**: `fan_in_composition.py`,
`tests/test_wave2_fan_in_composition.py`.

Not modified: `verification.py`, `scheduler.py`, `field_control_plane.py`,
WorkPacket/Proof schemas, field fixture semantics, the frozen driver, the
deployed mesh hotfix.

> **Correction.** An earlier revision of this ledger listed `poller.py` as "not
> modified". That was false in the commit that made the claim, which changed 32
> lines of it. `poller.py` is an authorized, modified file — see the row above.

## Wiring status (measured, per function)

| Function | Production callers | Status |
|---|---|---|
| `retain_verified_commit` | `terminalization.py` `_retain_verified` (call site `terminalization.py:544`) | **wired** — reached on every SUCCEEDED terminalization through `poller._terminalize`, verified by a production-path test that sets **no** environment variables |
| `resolve_trusted_commit` | 0 outside the module | read-side API; used internally by `retain_verified_commit`'s immutability check |
| `release_trusted_refs` | 0 | **owner-controlled cleanup entry point** |
| `trusted_ref` | 0 outside the module | path constructor; used internally |

Stated plainly: `release_trusted_refs` has **no automatic caller**. It is the
explicit owner-controlled cleanup surface the authorization asks for
("final graph or explicit owner-controlled cleanup can remove refs safely"), not
an automatic teardown hook. Wiring it into `sweep_run` would require
`substrate/execution/attempts/run_teardown.py`, which is **outside this cycle's
authorized surface** — so it is deliberately left as an operator/owner-invoked
API rather than widened without authorization. The consequence, truthfully: until
it is called, retained refs persist for the life of the fixture repo. They are
scoped by candidate+run, bounded (one ref per succeeded attempt), and each pins
one small commit — but they are not auto-collected.

`resolve_trusted_commit` and `trusted_ref` are load-bearing *inside* the module
(immutability check and ref construction) and are additionally the read-side API a
future consumer needs; they are not dead in the sense the removed composition
module was.

## Trusted-ref design and access control

`refs/umh/verified/<candidate>/<run>/<task>/<attempt>` — one verified commit.

Deliberately **outside `refs/heads`**: `field_task_scope.py:688-696` records that a
worker lease can create refs under `refs/heads` (measured: `update-ref
refs/heads/protected-main` succeeded), so a retention ref there would be
worker-forgeable. Host isolation keeps the rest of `refs/` non-writable.

Every path component is validated: character class, plus explicit refusal of a
leading `-` (git would read it as an option) and of `.`/`..` (namespace traversal).
Both extra rules exist because the character class **alone** let `-x` and `..`
through — measured, then fixed.

Namespaced by candidate **and** run, so one run's teardown cannot free another's.

Rules:
- only `reason == "succeeded"` retains; failed/rejected/cancelled/revoked leave **no** ref;
- an attempt whose HEAD equals its lease base produced no commit and retains nothing
  (otherwise the pre-existing base would be published as "verified output");
- retry lineage needs no special case — a failed attempt simply has nothing to find;
- **immutable**: re-retaining the same commit is a no-op, rewriting to a different
  commit is refused; `update-ref <ref> <new> ""` (CAS against must-not-exist) makes
  concurrent terminalization race-free;
- a retention failure returns from `terminalize` BEFORE `_release_lease`, so the
  worker branch is never deleted and the verified commit survives. The lease is
  deliberately left ACTIVE (recoverable) rather than destroying an unrecoverable
  commit.

## Explicit-base design

- Omitted → `git rev-parse HEAD`, exactly as before.
- Supplied → must resolve to a real commit in **this** repo, or `RuntimeError`; no
  silent fallback to HEAD.
- Selected only by trusted control-plane code; never worker input.
- The created worktree is **proven** to sit on the recorded base (`rev-parse HEAD`
  compared after `worktree add`), and the sandbox is torn down if it does not.
- `LeaseManager` records the same value as `snapshot_ref` **and** refuses a sandbox
  that honoured a different base — recorded ≠ launched would void every scope verdict.
- A sandbox manager predating the parameter keeps working; one that cannot honour an
  explicit base **fails closed** rather than quietly branching from HEAD. Decided by
  `inspect.signature`, never by catching `TypeError` (which would mask a real fault).

## Security corrections preserved (all on the reachable path)

Two of the three adversarial-review findings apply to retention and are kept:

- **CPU-gate refusal must not read as a git answer.** Mapping a refusal to `rc=1`
  made every `rc != 0` consumer read "no commit to retain" / "no such ref" /
  "nothing to delete" — so on a loaded host the commit was **not retained**, the
  lease was released, `branch -D` ran, and the original defect returned *silently*.
  Now raises `CpuGateRefused` (subclass of `RetentionError`), matching the
  existing `worktree_sandbox.CpuGatedGitError` discipline — **and
  `terminalize` returns before `_release_lease` when retention failed**.
  Raising alone was NOT enough: an earlier version recorded the error and
  fell through to release, so the branch was still deleted and the verified
  commit still destroyed. That changed the *reporting*, not the *outcome*. A failed ref **listing** also no longer reports a release that did not
  happen.
- **Sandbox-base divergence refused** (recorded ≠ launched).

The third — hostile `updates` masking absence guards — belonged **exclusively** to
the reverted composition lifecycle guard. `lifecycle.py` is byte-identical to the
committed base, so there is no reachable caller for that fix and it is not carried.
It is recorded in the composition work packet as a mandatory requirement.

## Verification

**Behavioural: 24/24** on the real `SandboxManager`, real git, real `LeaseManager`,
real `terminalize()`.

**Mutation: 14 mutants, all crossing real boundaries** (git, sandbox, lease,
terminalization). All files restored byte-identically (sha256 verified on a
quiesced tree).

The first sweep left **one survivor — R14** (*a failed `for-each-ref` listing
reported as a successful release*): no test forced the listing to fail, so the
fail-closed guard was unverified. Added
`test_failed_ref_listing_never_reports_a_successful_release`, which stubs the
gate to fail only that one command; R14 then died.

**Process rule learned the hard way:** the sweep mutates files in place and restores
after each mutant. Running it concurrently with a review or an edit session is
invalid — a reviewer saw live `MUTANT` markers, and a restore trap silently reverted
two of my fixes. Sweeps now run alone.

## Defects this work's own verification caught

1. `..` and a leading `-` escaped the ref-component validator;
2. retention pinned the **base** commit when a worker never committed;
3. a trusted ref could be silently rewritten to a different commit;
4. threading `base_commit` unconditionally broke every pre-existing sandbox
   implementation — **60 failures** in `test_wave2_terminalization.py`;
5. a **name shadow** in `acquire()` — the local `base_commit = ""` overwrote the
   *parameter* before it was read, so every explicit base was silently dropped and
   the lease branched from HEAD anyway. Same class as the original defect, and it
   would have made the whole change a no-op;
6. the lease recorded the sandbox's base rather than the requested one;
7. CPU-gate refusal failing open (above);
8. retention ordered after release survived the first mutation sweep because no
   test drove the real `terminalize()` — fixed by adding one that does.

9. **"fail closed" was cosmetic** — the most serious of the eight. `_retain_verified`
   recorded the error and control fell straight through to `_release_lease`, so a
   refused retention still ran `git branch -D` and destroyed the verified commit.
   Raising `CpuGateRefused` had fixed the *reporting*, not the *outcome*: on a
   loaded host this reproduced field run `20260805T182714Z-p1` **exactly, on the
   precise trigger this module exists to survive**. Reproduced through the real
   `terminalize()`/`LeaseManager`/`SandboxManager` (`result.ok=False` **and**
   `COMMIT REACHABLE: False`). Found by the final independent review.

   My own test was named `test_terminalize_fails_closed_when_retention_is_refused`
   and its docstring stated the correct invariant — but it asserted only
   `not result.ok` and `"retention" in errors`, both of which were already true
   while the commit was being destroyed. **A test that asserts the status flag
   instead of the outcome its docstring names is worse than no test: it certifies
   the wrong thing.** Fixed by returning before `_release_lease` (keyed on a stable
   `_RETENTION_FAILED_PREFIX` marker, not a message substring) and by asserting the
   commit's survival, the un-released lease, and the surviving **branch**.

   Deliberate trade: the lease is left **ACTIVE**, which blocks retry admission
   for that Task.

   **Correction 1 — the recovery story was wrong in BOTH directions.** An early
   version called the withhold 'recoverable' via an operator revoke or
   `recover_stale_runs`; that was false, because both call `LeaseManager.revoke()`,
   which runs `cleanup_sandbox` → `git branch -D` and destroys the very commit the
   withhold protects (`recover_stale_runs` additionally only runs at process START
   against prior dead runs, never the live one). The correction then over-swung to
   "not a self-healing state", which is *also* false: `LeaseManager.expire_stale`
   runs **every poller cycle** (`scripts/wave2_attempt_runner.py:511`), only flips
   `status` to `expired`, and touches neither the sandbox nor any branch. The lease
   therefore self-heals at TTL with the commit intact — measured
   (`test_expire_stale_does_not_destroy_a_preserved_commit`).

   **Correction 2 — the blast radius was understated.** An early version said the
   withhold "blocks retry admission for that Task". A withheld lease also held its
   **sandbox concurrency slot**, and at the production `max_parallel=2`
   (`scripts/wave2_attempt_runner.py:256`) two withholds blocked `create_sandbox`
   for *every* subsequent Task — a whole-run halt, not a per-Task stall — while
   `expire_stale` cleared the leases but never the slots. Reproduced, then fixed:
   the withhold now frees the slot with the branch preserved
   (`cleanup_sandbox(preserve_branch=True)`), proven by
   `test_two_withholds_do_not_starve_a_third_task_at_production_max_parallel`.

   Bounded retry of retention before release would avoid the withhold entirely and
   is still NOT implemented — recorded as open.


## Production-nullification defects (found at 66f327b6a, fixed here)

Both were invisible to every test that called `terminalize()` directly, and both
were found by an independent review that executed the **real production caller**.

**CRITICAL A — retention never ran in production.** The candidate/run binding was
read from `UMH_W2_CANDIDATE_SHA` / `UMH_W2_RUN_ID`. A whole-tree grep found those
names in exactly two files: the reader, and this suite's `monkeypatch.setenv`.
**Nothing in production set them.** The absent binding took a `steps.append(...)`
early return, so on a perfectly healthy host: `result.ok=True`, `errors=[]`,
`retained_commit=''`, and the verified commit destroyed by the next step. Field run
`20260805T182714Z-p1` reproducing on EVERY normal run, silently.

Fixed by deriving the binding from records the control plane already owns:
`run_id` ← `attempt.correlation_id` (`w2-<run_id>`, confirmed against real field
records) and `candidate` ← the lease's `repo_root`
(`.../candidates/<lane>/<sha>/targets/<run-id>/…`), with a path-only fallback.
A missing binding is now a retention **failure**, not a skip — but only when a
commit is actually at risk (`_commit_above_base`), so the other ten terminal paths
that `terminalize` serves are not blocked for nothing.

**CRITICAL B — the poller reversed the fix one frame up.** `poller._terminalize` is
the only production caller. Its RV-HIGH-2 healer keys on `lease_released == False`
and force-revokes to unblock retry — and `revoke()` also runs `cleanup_sandbox` →
`git branch -D`. So the gate held inside `terminalize()` and was undone immediately
after. Two fixes from different cycles reading the same boolean with opposite
intent.

Fixed with an explicit `TerminalizationResult.lease_withheld_reason`. The healer
now runs only for a genuine release fault; a deliberate withhold is surfaced as a
blocking report error that names the hazard ("do NOT revoke this lease, revoking
destroys the commit").

**The lesson, stated plainly:** the previous cycle proved its fix at the function
boundary and never executed the production caller — the same category of error it
was written to correct. The suite now drives `poller._terminalize` directly.

## Composition work packet (NOT implemented)

Deterministic fan-in composition is proven correct in isolation but has **no
production caller** and its lifecycle path dead-ends. It is deferred in full.

**Required producer.** A control-plane component that, when a dependent Task's
declared dependency closure is all SUCCEEDED-with-Proof, resolves each
predecessor's retained commit and composes them.

**Composition primitive (validated, not shipped).** `git merge-tree --write-tree`
with an explicit `--merge-base` from `git merge-base --octopus`, folded pairwise
over a canonical `(task_id, commit)` sort, then `git commit-tree` with every
predecessor as a parent and pinned author/committer identity **and date**.
Measured: N ∈ {2,3,4,5} → one tree and one commit id across all 120 permutations at
N=5. Intermediates must be **parentless** and keyed on the sorted consumed set —
`parents=[acc, nxt]` encodes the fold path and produced 6 distinct ids at N=3, 24 at
N=4. `rc > 1` must be distinguished from `rc == 1` or a git error is reported as a
conflict.

**Poller integration.** `poller._apply_result` advances only `DISPATCHED`/`RUNNING`;
a composed attempt would never be picked up.

**Verification integration.** `verify_attempt` requires a non-empty `package_hash`
and non-empty worker artifacts — both structurally impossible for a workerless
composition. It needs a composition-aware path whose evidence is the composition
commit, not a `WorkerResult`.

**Legal lifecycle path.** A guarded transition reaching VERIFYING without a worker
identity. **Mandatory:** absence guards must read **persisted state only** — a
caller-supplied `updates` dict could otherwise blank `worker_identity` and
`instruction_package_hash`, letting a real worker attempt skip dispatch entirely,
and `transition_cas` would persist the blanks, erasing the audit trail. Verified
exploitable. Also: `worker_identity` and `instruction_package_hash` should join
`ATTEMPT_IMMUTABLE_FIELDS`, and a composition ref must be checked for its **exact**
task/attempt binding, not merely its namespace prefix.

**Union-scope authority (open gap).** Each predecessor is verified against *its own*
declared path scope. The composition unions those trees, and nothing asserts the
union stays within the dependent's authorized paths. Because the composed commit
becomes the dependent's diff base, everything inherited is invisible to
`_diff_scope_verdict` by construction. `merge-tree` refuses only *textual* conflicts.

**Attempt-bound Proof flow.** `verify_plan_execution`'s Proof shape is unusable —
`lifecycle.py:178-180` records that a Proof with an empty `attempt_id` satisfied the
completion gate for *every* attempt on the same task.

**Task C / Task D wiring.** C consumes the composed base; D consumes the same
verified commit as its explicit base.

**Exact additional production files required:**
`substrate/execution/attempts/verification.py`,
`substrate/execution/attempts/poller.py`,
`substrate/execution/attempts/lifecycle.py`,
`substrate/execution/attempts/records.py`,
a producer (`field_control_plane.py` or `scheduler.py`),
and a new composition module.

## Preserved open finding

Worker **stdout, stderr, and exit status are not persisted** in durable run evidence
(`WorkerResult` carries them; nothing writes them). Untouched by this cycle —
recorded for separate disposition.

## Correction cycle — HIGH-1 / HIGH-2 (after the exact-head production-path review)

Both were found by an independent review that exercised the **real** production
caller and the **production** concurrency limit. Both are fixed here.

### HIGH-1 — a withheld lease starved the whole run

`terminalize()` deliberately withholds a lease to keep a verified commit
reachable. The withhold also kept the **sandbox concurrency slot**. At the
production `max_parallel=2` (`scripts/wave2_attempt_runner.py:256`), two
withholds — one transient CPU-gate spike hitting two SUCCEEDED attempts — made
`create_sandbox` raise `Max parallel sandboxes (2) reached` for every subsequent
Task. `expire_stale` (every poller cycle) cleared the *leases* but never the
*slots*, so the run never recovered. Reproduced before the fix:

```
withhold 1: withheld=True  active_sandboxes=1
withhold 2: withheld=True  active_sandboxes=2
THIRD TASK BLOCKED: Max parallel sandboxes (2) reached. Active: 2
expire_stale cleared: 2 leases → active_sandboxes STILL 2 → still blocked
```

**Fix.** `SandboxManager.cleanup_sandbox(sandbox_id, *, preserve_branch=False)`.
With `preserve_branch=True` the worktree is removed (slot returns) and the branch
ref is kept, so every commit on it stays reachable and survives `git gc`. The
withhold path calls it via `_preserve_sandbox_slot`, which **fails closed**: if
the sandbox manager is missing, or its `cleanup_sandbox` has no `preserve_branch`
parameter (signature-checked with `inspect.signature`), it does **nothing** — it
never falls back to the destructive call. The default is unchanged, so ordinary
cleanup still deletes the branch.

The lease itself is untouched: it stays ACTIVE, so retry for **that Task** remains
blocked (the intended trade), and it self-heals at TTL through `expire_stale`,
which is non-destructive.

### HIGH-2 — an empty `base_commit` failed open

`_commit_above_base` returned `""` ("nothing at risk", → proceed to destroy) when
the lease recorded no base. Unreachable today — the real `SandboxManager` always
resolves a base or raises — but the safety rested on an invariant that function
does not own, so any future sandbox returning an empty base would silently
reopen the destruction defect with `ok=True, errors=[]`.

**Fix.** An empty/unresolved base now returns `"unknown"`, the same at-risk answer
already used for a CPU-gate refusal. Valid bases are unchanged.

### Binding resolver — wrong-but-plausible outputs (found by hostile probing here)

Last-occurrence anchoring alone still emitted **silently wrong** bindings:

| repo path | before | after |
|---|---|---|
| `/a/candidates/candidates/candidates/targets/R/f` | candidate `R` (the run id) | refused |
| `/candidates/candidates/x/targets/R/f` | candidate `targets` | refused |
| `/a/candidates/wave2/candidates/targets/R/f` | candidate `R` | refused |
| `/var/lib/umh/candidates/wave2/S/targets/R/fixture` | `S`, `R` | `S`, `R` (unchanged) |

A ref written under another run's namespace is worse than no ref — it silently
misattributes verified work. The candidate is now accepted **only** when the full
canonical shape is present (`<anchor>/<lane>/<candidate>/targets/<run>/…`).

### Coverage added

`tests/test_wave2_verified_commit_retention.py` (56 tests, all on the real path):

| Test | Proves |
|---|---|
| `test_two_withholds_do_not_starve_a_third_task_at_production_max_parallel` | at `max_parallel=2`, two withholds still admit a third Task; both leases stay ACTIVE; both commits survive `gc` |
| `test_expire_stale_does_not_destroy_a_preserved_commit` | the self-heal path is non-destructive |
| `test_preserve_branch_keeps_the_branch_and_frees_the_slot` | the seam: worktree gone, slot freed, branch kept |
| `test_default_cleanup_still_deletes_the_branch` | `preserve_branch` is opt-in; default unchanged |
| `test_slot_preserve_refuses_a_sandbox_without_preserve_branch_support` | no destructive fallback, ever |
| `test_empty_base_commit_fails_closed` | empty/blank/None base → at risk; valid base unchanged |
| `test_empty_base_blocks_destruction_end_to_end` | through `poller._terminalize`, with the base erased from the **persisted** lease |
| `test_no_commit_attempt_does_not_publish_its_base_as_verified` | closes the `base_commit`-dropped mutant: a no-commit attempt retains nothing |
| `test_binding_resolver_refuses_ambiguous_or_hostile_input` | 6 new hostile path shapes, plus the canonical shape still resolving |

### Mutation results

**20 mutants, 20 killed, 0 survivors** at this point in the cycle — slot
preservation (8), empty-base fail-closed (2), retention reachability and binding
(7), the poller's withhold distinction (3). Four more were added for sticky
preservation below; the final count is **24/24**.

Two earlier survivors were investigated rather than papered over: one was a
**proven equivalent mutant** (disabling a log-only `elif` branch), and the other
(`base_commit=""`) exposed a genuine coverage gap that is now closed by
`test_no_commit_attempt_does_not_publish_its_base_as_verified`.

### Follow-on within the same cycle — preservation must be STICKY

Found by my own hostile probing of the HIGH-1 fix **before** the independent
review returned, and reachable in production today.

Preservation was initially per-CALL. A **later** `cleanup_sandbox(sandbox_id)`
with the default argument therefore deleted the preserved branch:

```
after preserve:  branch = auto/low-risk/s-25964c0e
2nd ordinary cleanup returned: True | branch now: ''
commit survives after 2nd cleanup: False
```

The trigger is not hypothetical — it is the **documented operator recovery** for a
withheld lease. `LeaseManager.revoke()` (and `release()`) call exactly that
cleanup, so recovering a withheld lease destroyed the very commit the withhold
had just protected. End-to-end before the fix, through `poller._terminalize`:

```
withheld, lease status: active
after expire, lease status: expired
commit survives an operator revoke AFTER the withhold: False
```

**Fix.** `WorktreeSandbox.branch_preserved` — a sticky, **persisted** flag. Once a
branch has been preserved, every later cleanup of that sandbox refuses to delete
it: the default argument, an explicit `preserve_branch=False`, and a cleanup
issued after a full process restart (the flag is written to and re-read from the
sandbox index). Behaviour is unchanged for any sandbox that was never preserved.

After the fix, the same end-to-end sequence:

```
commit survives operator revoke + release AFTER withhold: True
branches: 'auto/low-risk/attempt-ea-1-02d4c1f5\n* master'
```

Pinned by `test_preservation_is_sticky_across_later_cleanups_and_restart` and
`test_operator_revoke_after_a_withhold_does_not_destroy_the_commit`.

### Acknowledged residual — preserved branches are not auto-collected

A preserved branch is deliberately immune to cleanup, so preserved branches
**accumulate** for the life of the fixture repo, one per withheld attempt. This is
the same disposition as the retained refs above: bounded (one per withhold, each
pinning one small commit) and owner-collectable, but not automatic. Reclaiming
them safely requires knowing the retention condition was resolved, which is the
bounded-retry work packet — outside this cycle's authorized surface. Recorded,
not silently accepted.

### Final mutation results

**28 mutants, 28 killed, 0 survivors** — slot preservation (8), sticky
preservation and its persistence (4), empty-base fail-closed (2), retention
reachability and binding (8), poller withhold distinction (3), plus the three
raised by the independent review (see below).

## Independent review disposition (reviewed `a374748a7`, fixed at head)

The review executed the real production caller at the production concurrency
limit. Its verdicts on the two authorized HIGHs: **HIGH-1 genuinely closed**
(third Task admitted, both commits survive `gc`, both leases stay ACTIVE),
**HIGH-2 genuinely closed** (empty / whitespace / `None` / nonexistent / garbage
base all withhold with the commit alive). It also confirmed the
`test_wave2_terminalization.py` stub change was **legitimate, not a weakening**
— `create_sandbox` resolves a base or raises on both branches, so the old stub
asserted a state production cannot reach.

| Finding | Disposition |
|---|---|
| **CRITICAL-1** — a preserved branch is destroyed by every later cleanup, incl. `LeaseManager.revoke()` | **Already fixed** at `a301dafbd` (sticky `branch_preserved`), which the review did not see — it reviewed the parent commit. Its independent reproduction matches mine exactly. |
| **HIGH-1** — binding resolver still emits wrong-but-plausible refs on two shapes | **Fixed here.** Confirmed reproducible at `a301dafbd` before fixing. |
| **MEDIUM-1** — `worktree prune` mutant survives (zero coverage) | **Fixed here** — test added; the mutant now dies. |
| **MEDIUM-2** — `sandbox_slot_freed` can always lie (no production reader) | **Fixed here** — tests now assert the OUTCOME (`active_sandboxes == 0`) and that a cleanup returning `False`/`None`/`0` or raising is never reported as freed. |

### HIGH-1 — one anchor must yield BOTH components

`candidate` was resolved from the last `candidates` anchor while the path's run
came from the last `targets` anchor — **independent** anchors that can name
different levels of the same path. Two shapes therefore wrote a real trusted ref
into the wrong namespace with `errors=0`:

| repo path | before | after |
|---|---|---|
| `…/candidates/wave2/targets/targets/<RUN>/fixture` | candidate `targets` | refused |
| `…/candidates/wave2/aaaa/targets/RUN_A/targets/RUN_B/f` (correlation `RUN_B`) | `aaaa` / **`RUN_B`** — run read from a deeper level than the candidate | refused (run mismatch) |
| the same path read consistently (correlation `RUN_A`) | — | `aaaa` / `RUN_A` |
| `/candidates/candidates/x/targets/R/f` | candidate `targets` | `x` / `R` — a genuine canonical match, now read correctly |
| canonical | `SHA1` / `<RUN>` | unchanged |

Both components now come from a single anchor match (`candidates/<lane>/<candidate>/targets/<run>`),
a component that is itself a structural marker is refused, and two *different*
canonical matches in one path are refused as ambiguous. Escape/injection was
already closed by `_validate_component`; this closes silent **misattribution**.

## Correction cycle 2 — CRITICAL-1, CRITICAL-2, HIGH (CAS) (70f3c0ee2)

Three confirmed production defects at SHA `f8171cf3b`, fixed in one bounded cycle.

### CRITICAL-1 — sandbox starvation under real CPU-gate refusal

`_preserve_sandbox_slot` called `cleanup_sandbox` → `_run_git` → `gated_subprocess_run`,
the same gate whose refusal caused the withhold. At production `max_parallel=2`
(`scripts/wave2_attempt_runner.py:256`), two withheld attempts fill all slots and
unrelated Tasks starve permanently. `expire_stale` clears leases but not occupied
sandbox slots.

**Fix:** Two-tier `_preserve_sandbox_slot`:
- Tier 1: `cleanup_sandbox(preserve_branch=True)` — normal git path
- Tier 2: `emergency_free_slot(sandbox_id)` — filesystem-only (`shutil.rmtree`),
  no git subprocesses, branch preserved, `needs_worktree_prune=True` recorded for
  deferred admin cleanup

`emergency_free_slot` enforces 9 safety checks: sandbox exists, worktree path is
a real directory, NOT a symlink (`os.path.islink`), NOT the repo root
(`real_wt == real_repo`), strictly under the managed worktree root
(`real_wt.startswith(real_root + os.sep)`) using `os.path.realpath` to resolve
traversal. `branch_preserved` is set STICKY before status update.

**Proof:** `test_two_withholds_use_emergency_when_gate_refuses_both_layers` —
both retention AND sandbox gates refuse, emergency frees slots, third Task admitted.

### CRITICAL-2 — no-raise contract violation (FileNotFoundError)

When the worktree is already absent, `_commit_above_base` and `_retain_verified`
did not catch `FileNotFoundError` / `OSError`. `terminalize()` raised even with
`raise_on_security_failure=False`. No stable withheld reason was persisted; the
slot remained occupied.

**Fix:** `except (FileNotFoundError, OSError)` handlers in both functions.
Defense-in-depth: `gated_subprocess_run` currently swallows `FileNotFoundError`
as a gate refusal (returns `None` → `CpuGateRefused`), so these handlers fire
only if the gate's swallowing behavior changes. Tests monkeypatch `_git` /
`retain_verified_commit` to raise `FileNotFoundError` directly, proving the
handlers are load-bearing independently of the gate's internal behavior.

### HIGH — CAS old-value is load-bearing

`git update-ref ref head ""` — the `""` is a compare-and-swap against "must not
exist". Removing it would let concurrent terminalizations both succeed while one
overwrites the other's retained commit.

**Proof:** `test_cas_old_value_in_retain_verified_commit_blocks_race` monkeypatches
`resolve_trusted_commit` to return `""` (simulating a TOCTOU race past the
pre-flight check), then proves the second writer fails at the git CAS level.

### Verification

- 83 retention tests + 34 terminalization tests = **117 pass**
- **22/22 mutation sweep mutants killed**, 0 survivors
- All 15 pre-commit gates pass
- Field quota: **37/42 untouched** (no field dispatch in this cycle)
- PR #313: OPEN/DRAFT/UNMERGED
