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
| `substrate/execution/attempts/terminalization.py` | `_retain_verified` ordered **before** `_release_lease`; `retained_commit` on the result |
| `substrate/execution/attempts/leases.py` | `acquire(base_commit=…)` → sandbox + `snapshot_ref`; signature-checked capability; divergence refused |
| `substrate/organism/worktree_sandbox.py` | `create_sandbox(base_commit=…)`, fail-closed resolve, launched-base proof |
| `tests/test_wave2_verified_commit_retention.py` | **new** — 21 tests on the real shipped path |

**Reverted byte-identically to the committed base** (composition removal):
`substrate/execution/attempts/lifecycle.py`, `substrate/execution/attempts/records.py`,
`substrate/canonical_types.py`. **Deleted**: `fan_in_composition.py`,
`tests/test_wave2_fan_in_composition.py`.

Not modified: `verification.py`, `poller.py`, `scheduler.py`,
`field_control_plane.py`, WorkPacket/Proof schemas, field fixture semantics, the
frozen driver, the deployed mesh hotfix.

## Wiring status (measured, per function)

| Function | Production callers | Status |
|---|---|---|
| `retain_verified_commit` | `terminalization.py:298,302` | **wired** — runs on every SUCCEEDED terminalization |
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
- a retention failure is a real error, so `TerminalizationResult.ok` is False and
  destructive cleanup is blocked.

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
  Now raises `CpuGateRefused` (subclass of `RetentionError`, so terminalization
  fails closed), matching the existing `worktree_sandbox.CpuGatedGitError`
  discipline. A failed ref **listing** also no longer reports a release that did not
  happen.
- **Sandbox-base divergence refused** (recorded ≠ launched).

The third — hostile `updates` masking absence guards — belonged **exclusively** to
the reverted composition lifecycle guard. `lifecycle.py` is byte-identical to the
committed base, so there is no reachable caller for that fix and it is not carried.
It is recorded in the composition work packet as a mandatory requirement.

## Verification

**Behavioural: 22/22** on the real `SandboxManager`, real git, real `LeaseManager`,
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
