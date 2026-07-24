# Wave 2 — Exact Critical Ledger

One row per CRITICAL. **No finding may disappear or be downgraded without a
written adjudication recorded here.**

## Accounting reconciliation

An earlier status report said "nine new CRITICALs, three fixed, five open" —
which sums to eight. The omission was **SEC-C1** (teardown never destroys
`worker-homes/`): it was described in prose but left out of the open count. The
correct accounting is below and is now the authority.

| Round | Count | IDs |
|---|---|---|
| Round 1 (pre-repair) | 7 | C1, C2, C3, C4, SEC-C1(evidence), SEC-C2(shared home), SEC-C3(readiness exit) |
| Round 2 (post-repair review) | 9 | C-1…C-5, SEC-C1…SEC-C4 |
| **Round 2 status** | **9 = 3 fixed + 6 open** | fixed: SEC-C2, SEC-C3, SEC-C4 |

Round-1 and Round-2 IDs are namespaced by round; they are different findings that
happen to share numbering. Round 1 is closed (all 7 repaired in R1–R3). This
ledger tracks Round 2.

---

## Round 2 — the nine

### SEC-C3 — ambient env bypass disabled the entire Proof gate — **FIXED**

- **Root cause:** `lifecycle._assert_durable_proof` began with
  `if os.environ.get("UMH_W2_ALLOW_NONDURABLE_PROOF") == "1": return`.
- **Authority violated:** governed completion (Amendment v1 clause 6) — no Task
  completes without independent durable Proof.
- **Exploit path:** the runner is launched via
  `bash -c "exec env ... python ..."`, which **inherits the operator's full
  environment**. Any stale export in a shell profile, tmux pane, or prior test
  session silently converts the completion guarantee into a no-op, unlogged, on a
  live billed run. Verified: with the var set, a **nonexistent** `proof_id`
  completed an attempt.
- **Status:** FIXED — hatch deleted, no replacement bypass. The three lifecycle
  test files that used it now mint REAL durable Proofs.
- **Commit:** R4b. **Test:** `test_no_proof_bypass_exists_in_the_tree`.
- **Independent-review disposition:** raised by security review; verified
  independently before fixing.
- **Residual risk:** none. A source-level test asserts the string appears nowhere
  in `substrate/` or `scripts/`.

### SEC-C2 — Proof lineage failed OPEN on absent binding — **FIXED**

- **Root cause:** both binding checks were guarded by truthiness
  (`if recorded_attempt and recorded_attempt != ...`), so a Proof whose `action`
  carried no `attempt_id` satisfied the gate for **every** attempt.
- **Authority violated:** Proof-to-attempt binding; a Proof may only complete the
  attempt it proves.
- **Exploit path:** the plan-execution path mints proofs without `attempt_id`.
  Verified: a durable Proof with an empty `attempt_id` completed an unrelated
  attempt on the same task — so a stray proof could complete a *failed* retry.
- **Status:** FIXED — both checks are equality, absent lineage is a rejection.
- **Commit:** R4b. **Test:** `test_proof_with_absent_lineage_is_rejected`,
  `test_proof_for_another_attempt_is_rejected`.
- **Residual risk:** none for attempt proofs. Plan-execution proofs are bound by
  `work_id` + classification and are never used to complete an attempt.

### SEC-C4 — non-bwrap primitives exempted from the isolation gate — **FIXED**

- **Root cause:** `preflight_isolation` returned `(True, "not probe-verified")`
  for `systemd-run`/`nsjail`, and both call sites used
  `if not ok and prim == "bwrap"` / `ok or prim != "bwrap"` — so a non-bwrap
  primitive **could never fail** the gate.
- **Authority violated:** Amendment v1 clause 4 (enforced host isolation).
- **Exploit path:** `systemd-run` creates no mount namespace (`/opt/OS`, all
  credentials, every other run's state readable); `nsjail --chroot /` is the
  whole filesystem. Neither propagates `CLAUDE_CONFIG_DIR`/`TMPDIR`/`XDG_*`, so
  the per-attempt credential boundary collapses to the real `~/.claude` —
  reinstating the shared-home defect while reporting `isolation_ok: true`.
- **Status:** FIXED — unprovable primitives return `False`; both gates use
  `if not ok`. Wave 2 hard-requires bwrap.
- **Commit:** R4b. **Test:** `test_non_bwrap_primitive_cannot_qualify`,
  `test_isolation_gates_fail_closed_for_every_primitive`.
- **Residual risk:** the run cannot proceed on a host without bwrap. Intended.

### C-1 — `diff_scope` is a structural no-op — **OPEN**

- **Root cause:** `LeaseManager.acquire` always sets
  `writable_paths=[worktree_path]`; verification normalizes that single absolute
  entry to `"."` → `whole_worktree=True` → `scope_ok=True` unconditionally, and
  the computed `outside` list is discarded.
- **Authority violated:** diff-scope containment; the packet's declared allowed
  paths.
- **Failure path:** a worker that rewrites the fixture's own tests, or writes
  anywhere in the worktree, earns a valid AttemptProof. The repair replaced a
  hardcoded `ok=True` with a computation whose result is thrown away — the same
  false green with more code.
- **Status:** OPEN — repair in progress (order §3).

### C-2 — the lease is never released; retry deadlocks — **OPEN**

- **Root cause:** `LeaseManager.release()` has **zero production callers**
  (verified by grep across `substrate/` and `scripts/`).
- **Authority violated:** one-active-lease-per-task; retry-as-new-attempt.
- **Failure path:** A1 fails → scheduler mints A2 → `acquire()` raises
  `LeaseError` (l-1 still active) → caught at `scheduler.py` and logged at
  **debug** → A2 → BLOCKED → re-READY → BLOCKED, forever. The failure pass then
  produces the **exact observable shape the qualification expects** ("A failed, C
  blocked, no false Proof") for entirely the wrong reason.
- **Status:** OPEN — repair in progress (order §4).

### C-3 — `scenario_map.json` has no field writer — **OPEN**

- **Root cause:** `write_scenario_map` is called only from tests; the sole
  non-test occurrence is inside a **remediation string**.
- **Authority violated:** failure-injection targeting.
- **Failure path:** `arming_is_valid()` → `{}` → `armed: False` → exit 3 on every
  `inject-failure`. The fail-closed works, but the failure pass is *unrunnable* —
  and an operator hitting exit 3 repeatedly will hand-write the map with guessed
  ids or delete the check, restoring the original defect.
- **Status:** OPEN — repair in progress (order §5).

### C-4 — the verifier executes worker-authored code unconfined — **OPEN**

- **Root cause:** `_independent_checks_for` runs `pytest` with
  `cwd=<lease worktree>` via `gated_subprocess_run` — no `build_isolated_command`,
  no bwrap, no `scrub_worker_env`, full host environment.
- **Authority violated:** Amendment v1 clause 4; the entire R1 credential
  boundary.
- **Exploit path:** the worker's job is to write files in that worktree,
  including test modules. A `conftest.py` there is arbitrary Python that pytest
  imports and executes as the runner user with the runner's environment
  (including `CLAUDE_CODE_OAUTH_TOKEN`). The runner refuses to start without
  bwrap and then runs adversary-influenced code unconfined a few frames later.
- **Status:** OPEN — repair in progress (order §6).

### C-5 — `reconcile`/`teardown` exit 0 on failure — **OPEN**

- **Root cause:** `_result_declares_failure` checks
  `("deploy_ok","started","armed","ok","ready")`; `reconcile` returns
  `all_passed`, `teardown` returns no verdict key at all.
- **Authority violated:** readiness/verdict exit semantics (the SEC-C3 class from
  round 1), in the scoring command.
- **Failure path:** a reconciliation scoring 0.0 — or scoring **zero passes** —
  exits 0. A driver chaining `deploy → run → reconcile` by exit code treats a
  failed or empty reconciliation as success. `teardown` failing to shred the run
  secret also exits 0.
- **Status:** OPEN — repair in progress (order §7).

### SEC-C1 — teardown never destroys `worker-homes/`; residue assert is dead — **OPEN**

- **Root cause:** `assert_no_credential_residue` is defined, exported and tested
  but **called from nowhere in production**; `teardown()` contains zero
  references to `worker-homes`.
- **Authority violated:** credential lifetime (the incident this campaign opened
  with).
- **Exploit path:** `stop_runner` sends SIGTERM; the runner installs **no signal
  handler**, so the `finally:` that destroys the attempt home never runs and the
  operator's real OAuth credential survives on disk indefinitely. The cleanup
  guarantee holds only on the graceful path.
- **Status:** OPEN — repair in progress (order §8).

---

## Warnings from round 2 (non-critical, tracked)

W-1 double proof record; W-2 `reread_durable` substring fast-path; W-3 CPU-gate
fallback to worker self-report; W-4 concurrency test never exercises `run_loop`;
W-5 three independent `2` caps + CPU gate denies the second worker; W-6 Bash
revocation semantics; W-7 no VERIFYING recovery; W-8 nonce replay on recovery;
SEC-W1 finalization not idempotent; SEC-W2 dispatch secret unmatched by typed
patterns; SEC-W3 residue raise inside `finally` strands the claim; SEC-W4
`_safe_component` not injective; SEC-W5 launch log outside the evidence tree;
SEC-W6 over-redaction of URLs/base64; SEC-W7 memory read cost; SEC-W8 detached
manifest hash is not out-of-band.

Disposition recorded per item in `docs/wave2_repair_ledger.md` as each is closed.
