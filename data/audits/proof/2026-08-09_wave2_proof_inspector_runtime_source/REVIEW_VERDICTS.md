# Independent Review Verdicts — Proof-Inspector Canonical Runtime Source

Four independent review passes on the correction (two adversarial, two
verification), run against the live uncommitted worktree on top of
`83c56cb6d9782b60dc81aa019bcb9bb8a73bb2e0`. Every finding was verified by
execution, not by reading.

## Round 1 — eos-code-reviewer (adversarial): REJECT

Reviewed the initial revision (runtime-first reads on ALL routes, merged
query/summary). Verdict REJECT with three criticals, each reproduced by
execution:

1. **CRITICAL — mkdir on the read path reintroduces the root cause.**
   `ProofRuntime()`'s default path resolution mkdirs the state dir; a failed
   mkdir (read-only mount, uid mismatch) was swallowed at `logger.debug` and
   silently degraded the source to legacy-only — the reviewer reproduced the
   exact post-fix w16 404 (`BEFORE breakage: 200 / AFTER breakage: 404`).
   Also demonstrated the read surface creating directories as a side effect,
   and that a chmod-based test is a false pass under root (mode bits
   bypassed).
2. **CRITICAL — cockpit panel corruption.** Runtime and legacy packages have
   disjoint wire shapes (`outcome`/`timestamp` vs `status`/`created_at`);
   merging them into `/packages`/`/artifacts` produced "Invalid Date", blank
   status badges, and rows invisible to every panel filter.
3. **CRITICAL — summary vocabulary merge.** `by_status` mixed `success`/
   `failure` (runtime) with `pending`/`approved`/`rejected` (legacy);
   panel total no longer reconciled with its own counters.

Plus warnings: `limit=10**9` full-scan with in-place sort; `_ts` truthiness
chain; pre-existing torn-JSONL and unbounded `_packages` in ProofRuntime.

## Resolution applied

- Read path resolves via `runtime_state_path(..., create_parent=False)` +
  `ProofRuntime(store_path=...)` — zero writes; degradation logs at WARNING.
- Runtime proofs exposed by id ONLY (the reviewer's own recommended minimal
  option); `query()`/`summary()` are legacy passthroughs — `/packages`,
  `/artifacts`, `/summary` wire bytes unchanged from pre-fix behavior.
- Warnings 1–2 eliminated (code paths deleted); warnings 3–4 recorded in
  `CORRECTION.md` §2 as pre-existing ProofRuntime debt.
- New tests: mkdir-forbidden read (monkeypatched `Path.mkdir`, not chmod),
  zero-directory side-effect, legacy-only listing/summary contract.

## Round 2 — eos-code-reviewer (adversarial): APPROVE-WITH-NOTES ("merge")

All three criticals verified CLOSED by execution:

- Instrumented every write-capable syscall across all seven routes — zero
  writes on the proof read path; the round-1 killer scenario now returns 200.
- Diffed normalized wire bytes patched-vs-baseline across six variants
  (`packages`/`summary`/`artifacts`/limit/offset/status) — all identical.
- Path parity writer↔reader verified in four env shapes; hostile 404 matrix
  (trailing slash, symlinked bind-mount, legacy-store construction failure)
  all 200. The only 404s were genuine env misconfigurations (`UMH_STATE_DIR`
  unset/empty), now loudly warned.
- Wrote six independent mutants: five killed; the sixth (lookup-order
  inversion, WARNING 5) survived as a TEST GAP (not a live fault — runtime
  wins today; natural collision odds ~1 in 2.8×10¹⁴).
- WARNING 6 (pre-existing): `/timeline`'s `ExecutionJournal.__init__`
  performs one mkdir — outside the reviewed proof path, untouched by this
  patch, cannot cause a w16 404. Ledgered here.

**WARNING 5 closed post-review:** `test_runtime_wins_on_proof_id_collision`
plants the same proof_id in both stores and asserts the runtime shape is
served; the reviewer's surviving M-C mutant now fails (verified: 1 failed /
10 passed under the mutant; 11/11 green restored).

## Rounds 1+2 — eos-verifier: VERIFIED (both rounds)

6/6 checks each round: clean import; full test file green; end-to-end
simulation of the exact field failure shape (fresh env, empty `UMH_ROOT`,
state-dir proof via `ProofRuntime.create_direct`, mounted router, GET by id →
200 with `action.predecessor_commits` intact); mkdir-forbidden read still
200; listing/summary legacy-shaped only; execution-routes regression suite
green; git status exactly the intended change set; cpu-gate clean.
