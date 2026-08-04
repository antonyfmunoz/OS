# Wave 2 — Critical Repair Ledger (PR #313)

## Campaign truth

```
WAVE 2 IMPLEMENTATION:          REPAIRED (R0-R4 complete)
CRITICAL FINDINGS REPAIRED:     7 / 7
WARNINGS CLOSED:                11 / 11  (0 deferred)
DETERMINISTIC QUALIFICATION:    RE-ESTABLISHED (no-quota)
FIELD HARNESS QUALIFICATION:    REHEARSED (no-quota, repaired pathways)
REAL-WORKER QUALIFICATION:      NOT RUN  (owner-gated on real Claude quota)
SECURITY REVIEW:                CLOSED - no rotation required
PRODUCTION DEPLOYMENT:          NOT PERFORMED
MERGE:                          PROHIBITED
```

Head before repairs: `57c266b380cac6ec982d50088f2aa0f95e704f76`.

The earlier green matrix and rehearsal remain **historical evidence only**. They
cannot satisfy the repaired contracts, because their tests encoded the same false
assumptions as the defective implementation (see §"False-green tests" below).

## Why the prior claims were invalidated

Two independent adversarial reviews found **seven CRITICAL** defects, each
independently verified before acceptance. Every one failed **toward green** — the
harness would have reported a successful qualification while proving nothing.

| ID | Finding | Verified how |
|---|---|---|
| C1 | AttemptProofs never persisted — `ProofRuntime` exposes neither `store_package` nor `persist`, so `_persist_proof` always takes the in-memory `_packages` fallback; `proof_packages.jsonl` never created. Every SUCCEEDED attempt carries a dangling `proof_id`, and `_default_dep_lookup` only checks truthiness. | Ran `ProofRuntime()`: `has store_package: False`, `has persist: False` |
| C2 | Failure injection never fires — the task-A matcher cannot match real `wp-<hex12>` packet IDs. `inject-failure` would arm a marker that revokes nothing; the failure pass silently runs clean. | 2000 real-form IDs → **0/2000** matched; literal `"A"` → revoked |
| C3 | Two-worker concurrency unobtainable, and the ledger wedges — runner claims one dispatch per iteration and runs the worker synchronously; both dispatches get `expires_at = now+600`, so B is quarantined as expired on claim, and **no reaper exists**. B strands in DISPATCHED forever, permanently consuming a slot. | Read loop (one `claim_next` + blocking `run_worker_in_lease`); `grep quarantine` in poller/scheduler/runner → docstring only |
| C4 | Independent verification is blind — `_assignment_lookup` calls a nonexistent `list_assignments` and always returns `None`; `lease_lookup` never passed; `diff_scope` hardcoded `ok=True`; no independent checks. Any commit of anything earns a Proof. | Store API inspection; runtime lookup returns `None` |
| SEC-C1 | The bare 64-hex redaction rule (added during the incident fix) **destroys the proof manifest** — eats `artifact_sha256`, `package_hash`, `scope_hash`, docker image IDs. Plus an ordering bug: files are hashed, *then* rewritten by `_redact_tree`, so recorded hashes can never re-verify. | Regex applied to real hash shapes → all redacted; 40-hex git SHAs preserved; line order 1547 → 1551 |
| SEC-C2 | `worker_home` = `dirname(worktree_path)` → **shared across all leases**; real `~/.claude/.credentials.json` copied in and **never deleted**. OAuth credential persists past teardown; both concurrent workers share it read-write. | Path derivation identical for distinct leases; no cleanup anywhere in tree |
| SEC-C3 | A NOT-ready deploy still exits 0 — `readiness` is recorded but never branched on; `main()` returns 0 unconditionally. | Code path 786→803, `main()` `return 0` |

**SEC-C2 never fired** — 0 `.worker-home` dirs, 0 credential copies, 0 lease
worktrees, 0 signed artifacts on disk, because no worker ever ran. Pausing before
quota prevented a real credential incident. See
`docs/wave2_security_incident_closure.md`.

## Repair structure

| Commit | Scope | Status |
|---|---|---|
| R0 | Containment, teardown, security closure | **DONE** `c7e9279e` |
| R1 | Per-attempt credential/home isolation; immutable evidence pipeline | **DONE** `0cdd9ddc` |
| R2 | Durable canonical Proof (`2adc06ad`); real-Task-ID failure injection (`5a5017f3`) | **DONE** |
| R3 | Two-worker concurrency; fail-closed verification; readiness exit semantics | **DONE** `da07f866` |
| R4 | Eleven warnings; migration; read-only-path sweep; matrix + runbook + requalification | **DONE** (this commit) |

## Warning register — ALL CLOSED (0 deferred)

Every warning is repaired and covered by a regression test. **Nothing is
deferred**: no security, Proof, concurrency, readiness, current-truth, credential
or evidence-integrity finding was eligible for deferral, and none of the
remaining warnings needed it.

| ID | Root cause | Affected authority | Repair | Regression test | Commit | Residual risk |
|---|---|---|---|---|---|---|
| W5 | Un-APPROVED packets skipped with a bare `continue`; the runner logged only when something happened, so a stall was indistinguishable from "waiting for work" — **forever, with zero output** | Operator observability of the execution frontier | `ControlPlaneCycleReport.skipped_not_approved` names the blocking tasks and their status; the runner logs an idle cycle every 30 iterations with the cause | `test_cycle_report_names_tasks_that_are_not_approved` | R4 | None. Idle logging is rate-limited by design |
| W6 | `dispatch_id = d-<attempt_id>` collided on re-dispatch and `_seq`/`nonce` reset to 0 on runner restart; the spool file is written with `os.replace` → **silent overwrite** of a pending envelope, stranding its attempt | Dispatch identity / spool integrity | uuid-suffixed `dispatch_id`, uuid `nonce` | `test_dispatch_id_is_unique_per_dispatch` | R3 | None |
| W7 | `_role_resolver_for` defined and never called, carrying the same uuid-blindness as the failure matcher — it *looked* like role differentiation but implemented nothing | None (dead code) | Deleted | `test_dead_role_resolver_is_removed` | R4 | Integration/verification tasks share the implementer role contract; SoD (verifier != worker) is separately guarded, and per-task role differentiation is **not claimed** anywhere |
| W8 | Broad `except` appended `str(exc)` and logged at `debug`; the runner printed only `errors=N` → a systematic failure showed as a bare counter with no cause | Operator diagnosability | Error text carries the exception type, logs at `warning` with traceback, runner prints each error line | `test_cycle_errors_carry_the_exception_text` | R4 | A per-grant fault still does not abort the run (by design — one bad grant must not stall others); it is now loud |
| W9 | Tests encoded the same wrong assumptions as the code; the stub modelled "revocation implies failure" while the real worker retained `Bash` and could still `cat > file` and commit | Failure-qualification truth | `Bash` added to the revoked set; false-green tests replaced (see below) | `test_revocation_fires_on_the_real_backend_packet_id` | R2 | None |
| SEC-W1 | Relocating the default store orphaned **259 live production records**; dedup/promotion reading an empty store would re-promote already-processed candidates | Memory-candidate continuity | **Migrated, not reverted** — a revert would restore the boot crash (`app.py:46` builds `ExecutionPipeline` at import). `_iter_records()` reads legacy-then-current, newest-wins on `candidate_id`; the legacy path is **read-only** | `test_legacy_records_remain_readable_after_relocation`, `test_new_records_and_legacy_records_coexist`, `test_writes_go_to_the_new_store_not_the_legacy_one` | R4 | Legacy read-through is permanent until the store is consolidated. Retirement owner: memory subsystem; wave: post-Wave-2 |
| SEC-W2 | Only the `store_dir is None` branch was made lazy; the explicit branch still did `mkdir` in `__init__`, reproducing the original crash for any caller passing a non-writable path | Operator API boot | `mkdir` removed from **both** branches; directories created lazily in `_append_jsonl` | `test_construction_never_creates_directories`, `test_construction_survives_an_unwritable_root` (proved non-vacuous by re-injecting the eager mkdir: fails with `Errno 30 Read-only file system`) | R4 | None |
| SEC-W3 | `watcher.py` / `promoter.py` / `claude_bridge.py` kept repo-relative writable defaults; latent, but the first watcher event or promotion under `/app:ro` raises **mid-run**, burning a qualification pass | Candidate runtime stability | All three resolve through `runtime_state_path`; `HASH_STORE` became a lazy resolver | `test_no_repo_relative_writable_defaults_remain`, `test_memory_stores_resolve_under_umh_state_dir` | R4 | None |
| SEC-W4 | The run secret was shredded ONLY by an explicit `teardown`; any crash/SIGKILL left it on disk (an orphan from a prior SHA was found during R0 containment) | Run-secret lifetime | Crash handler shreds it too, with the sha threaded through `_install_crash_handlers` | R0 containment evidence + `docs/wave2_security_incident_closure.md` | R1 | `deploy-candidate` deliberately does **not** shred (a later `start-runner` needs it) |
| SEC-W5 | `$(cat)` failure yielded an empty secret; the runner failed closed but the operator saw only a generic "runner did not come up" | Diagnosability of a fail-closed path | `start_runner` verifies the secret file exists and is non-empty **before** building the launch line | `test_failed_verdicts_are_detected` (`started:False` shape) | R1 | None |
| SEC-W6 | `_run_secret_path` docstring claimed the secret was "readable by the candidate control plane" — it is **host-only**. A future edit could "fix" the mount to match and hand the secret to the container | Amendment clause 3 (worker/container gets no signing secret) | Docstring corrected with an explicit do-not-change warning | `test_control_plane_api_key_never_reaches_the_worker` | R1 | None |

Security, evidence, Proof, readiness, concurrency and current-truth warnings are
**not deferrable** per the order — and none were deferred.

## False-green tests to replace

| Old test | Wrong assumption | Replacement |
|---|---|---|
| Finding | Old test | Wrong assumption it encoded | Adversarial replacement | Proof the replacement fails against the OLD implementation |
|---|---|---|---|---|
| C1 | `test_wave2_verification_proof::_ProofRT` stub + `assert proof_id in rt._packages` | that an id held in memory is a Proof | real `ProofRuntime`; `assert reread_durable(proof_id) is not None`; plus fabricated-id, wrong-attempt, and restart-durability cases | The old stub exposes no `create_direct`, so `_persist_proof` now raises `ProofDurabilityError` — 9 tests failed the moment the guard landed and had to be rewritten |
| C2 | `test_wave2_field_failure_policy` using `task_id="A"` | that the harness controls packet ids | real `wp-<hex12>` ids resolved through `scenario_map.json`; the fake-id test is **retained** asserting those ids control nothing | The 2000-id measurement: **0/2000** matched before, **2000/2000** after |
| C3 | `test_driver_admits_independent_frontier_first` | that admission implies execution | `test_two_workers_overlap_in_wall_clock` asserts `max(started) < min(finished)` from measured timestamps behind a thread barrier | Mutation-tested against the sequential loop: `max(started) < min(finished)` is **False**, so the assertion fails |
| C4 | verification tests with `writable_paths=["/tmp/wt"]` and no assignment | that `diff_scope` was checked (it was hardcoded `ok=True`) | `test_diff_outside_allowlist_fails_verification`, `test_missing_assignment_fails_verification`, `test_missing_lease_fails_verification` | With `ok=True` hardcoded the scope test passes trivially; with the real computation an out-of-allowlist path fails |
| SEC-C1 | none (the redaction had no evidence-integrity test) | that redaction was safe for hashes | `test_legitimate_hashes_survive_redaction`, `test_recorded_hashes_describe_final_bytes`, `test_verify_detects_post_finalization_mutation` | Applying the withdrawn bare-64-hex rule to a sha256 redacts it — asserted directly |
| SEC-C2 | none (no per-lease isolation test existed) | that a shared home was acceptable | `test_worker_cannot_read_another_attempts_credential` runs a REAL bwrap probe | Mutation-tested: binding the parent dir makes the same probe print `LEAK` and read the planted token |
| SEC-C3 | none (readiness had no exit-code test) | that recording readiness was sufficient | `test_run_passes_refuses_when_candidate_not_ready` + every failure-verdict shape | The old `main()` returned 0 unconditionally; `_result_declares_failure` now drives exit 3 |

A test that mocks away the contract under test does not count. Where a claim is
about the sandbox or about wall-clock overlap, the test runs a real process and
asserts on what it observed.

## Verified-sound (not changed by the repair)

- Launch line does **not** leak to `ps`/`cmdline` (400 `/proc` samples); old form
  reproduced side-by-side and still leaks — regression genuinely closed.
- `_mint_run_secret` atomic `O_EXCL|0600`, fail-closed, 256-bit.
- `launch_log_tail` redacted **before** slicing.
- Worker cannot inherit `UMH_W2_DISPATCH_SECRET` (allowlist scrub →
  `['CLAUDE_CODE_OAUTH_TOKEN','HOME','PATH']`).
- nginx `${CANDIDATE_UPSTREAM}` substitution complete and fail-closed; WS block
  keeps a literal address (no keepalive pool).
- Poller always runs the scheduler pass after draining — the driver's
  first-frontier assumption is correct, and removing the redundant direct pass
  eliminated the lease-conflict path.
- Runner never mutates the ledger; no status inferred from file presence.

## Harness correction — stale `signed_spool` self-check (2026-08-04)

**Not a candidate defect.** The write-barrier repair (F-2, commit `55c57c472`)
made the transport refuse any envelope whose write authority cannot be enforced:
`spool._governance_defect` quarantines an envelope carrying no
`writable_path_scope=` constraint *even when its HMAC is valid*. That is the
barrier working as designed.

`scripts/wave2_harness_selfcheck.py::check_spool` had never been updated to match.
It built `DispatchEnvelope(dispatch_id="d1", attempt_id="ea1", …)` with **no**
`governance_constraints`, so the production gate correctly quarantined it and the
check reported `delivered=False` → `harness_runnable=False`. The harness was
stale; the candidate was right. The real dispatch path always seals the scope
(`dispatch.py:110`), and the 11 control-plane rehearsal tests over that path were
green throughout.

### The correction

The synthetic envelope is now minted by the **canonical path**, not a literal:

```
compile_attempt_package(...)      # production compiler — seals writable_path_scope=
    → governance_envelope_fields(package)   # production projector used at the
                                            # dispatch site (field_control_plane.py:469)
    → DispatchEnvelope(**fields) → spool.enqueue → claim_next
```

`governance_envelope_fields`' own docstring states the requirement this satisfies:
*"A test that inlines the same dict proves nothing about the dispatch path."*
Inlining `governance_constraints=["writable_path_scope=[...]"]` would keep passing
after the compiler stopped sealing the scope — precisely the blindness removed.

Fail-closed behaviour is **unchanged and still asserted**, now across four
controls rather than two:

| Control | Assertion |
|---|---|
| positive | canonically compiled envelope is DELIVERED |
| signature | wrong-secret reader quarantines it |
| governance (F-2) | **no** `writable_path_scope=` → quarantined despite a VALID signature |
| widening | scope widened on disk after signing → quarantined (constraints are inside the HMAC) |

`scope_declared=False` remains refused inside the real compiler
(`DispatchBlocked`), asserted by the new test file.

### Files changed (harness + tests only — zero production files)

- `scripts/wave2_harness_selfcheck.py` — `canonical_governance_fields()` added;
  `check_spool()` rewritten to drive the real path; `_widen_scope_on_disk()`
  probe added (returns `False` when no inbox record exists, so a relocated spool
  layout fails rather than passing vacuously).
- `tests/test_wave2_harness_selfcheck_spool.py` — **new**, 8 tests pinning the
  correction.

### Mutation results — 4 / 4 killed, 0 survivors

Each mutant was applied to production, measured, then reverted (`git diff` on
`substrate/` empty afterwards):

| # | Mutation | Result |
|---|---|---|
| M1 | `dispatch.py` stops appending `writable_path_scope=` | **KILLED** — `signed_spool` FAILs "canonical compiler emitted no writable_path_scope="; 4 of 8 new tests fail |
| M2 | `_governance_defect` returns `""` for a missing scope | **KILLED** — `no_scope_rejected=False`; 2 of 8 new tests fail |
| M3 | HMAC verification returns `True` unconditionally | **KILLED** — `bad_sig_rejected=False` |
| M4 | `governance_constraints` popped from `signable()` | **KILLED** — `widened_scope_rejected=False` |

M1 is the load-bearing one: it proves the positive case is bound to the real
compiler and not to a hard-coded string.

### Qualification after the correction

```
wave2_harness_selfcheck.py   PASS=8  OWNER_GATED=1  FAIL=0  → harness_runnable=True
Wave 2 suite (-k "wave2 and not phase14")   1203 passed, 0 failed
All 15 pre-commit gates                     PASS
ruff                                        no new findings (2 pre-existing E741 untouched)
```

`tests/test_phase14_8b_wave2.py` / `test_phase14_7a_wave2.py` show 16 failed /
26 errors from hard-coded `/opt/OS` paths under a worktree. Measured **identical
with this change stashed** — pre-existing, unrelated to the Wave 2 execution
slice, not introduced here.

`oauth_token` remains the single OWNER_GATED item; no field quota was spent, no
worker launched, and no field residue was produced by this correction.
