# Wave 2 — w16/w17/w18 Collector Observation Correction (durable history-backed)

**Authorized by:** OWNER DECISION — "ACCEPT INVOCATION #52 HARNESS OBSERVATION DEFECT.
AUTHORIZE ONE BOUNDED CORRECTION CYCLE FOR THE W16/W17/W18 COLLECTOR OBSERVATION MODEL."
(2026-08-08). No field execution, no quota change (52/56).

**Prior SHA:** `c6462dc25c51e70d1a41fefd591f10c770696f58`
**Triggering field result:** invocation #52, run `20260808T233546Z-p1` — a CORRECT
fast-completing A+B→C→D graph failed at `w16_ab_running_concurrent` because the collector
polled after the transient running/blocked/verified states had legitimately advanced.

## Core correction law applied
Qualification now verifies that a required lifecycle TRANSITION OCCURRED during this run —
NOT that the system is STILL in that transient state when the collector polls. Point-in-time
predicates were replaced with durable/history-backed observation. The semantic requirements
were NOT weakened; only how occurrence is observed changed.

## Intended semantics (unchanged) vs old vs new model

### w16_ab_running_concurrent — A and B executed concurrently
- **Old (WRONG):** poll until `status=="running"` for ≥2 distinct tasks NOW. `running` is a
  zero-width instant in the ledger (poller stamps `dispatched→running` and `running→verifying`
  at the same time when the worker RESULT arrives), so a fast graph never shows two "running."
- **New (durable):** the true worker-execution window is the **`dispatched` phase**
  ([`leased→dispatched`, `dispatched→running`]) reconstructed from each attempt's `transitions`.
  Concurrency = genuine temporal OVERLAP: `A1.dispatched ∩ B.dispatched > 0`. Sequential
  A-then-B yields overlap 0 → fails. (#52: A1∩B overlap = 81.3s.)

### w17_c_blocked — C was withheld until predecessors completed
- **Old (WRONG):** poll until a non-A/B task shows `status=="blocked"` NOW.
- **New (durable):** from `transitions`, C's `created→ready` (admission) is AT/AFTER both
  predecessors' `verifying→succeeded`, AND no non-A/B/C task dispatched before the predecessors
  verified. Distinguishes "C correctly withheld" from "C never ran (unrelated failure)": a real
  C attempt with a composition Proof must exist AND be admitted after predecessor success.

### w18_ab_verified — A/B verified with Proofs before C composed, C binds their commits
- **Old (WRONG):** poll until 2 tasks show `succeeded` + `proof_id` NOW.
- **New (durable):** each predecessor's qualifying SUCCEEDED attempt has a non-empty `proof_id`
  and a `verifying→succeeded` transition (both_proofed); both succeeded BEFORE C's composition
  (`c_compose_at ≥ ab_verified_at`); and C's composition Proof `predecessor_commits`
  (`GET /api/umh/proof-inspector/packages/{proof_id}`) binds EXACTLY the two predecessor tasks to
  their succeeded commits (preds_bound — one strict check, no vacuous skip). A failed A1 cannot
  satisfy A; a missing/foreign/wrong-commit predecessor fails.

## Concurrency definition (exact)
`A.dispatched_interval ∩ B.dispatched_interval != ∅`, where dispatched_interval =
[time(`leased→dispatched`), time(`dispatched→running`)] — the real worker-execution window.
The concurrent pair = the two `attempt_number == 1` attempts of C's two predecessor tasks
(A2 retry is sequential recovery, correctly 0-overlap with B).

## C-blocked proof semantics
From durable evidence, valid AFTER C has composed: C exists (composition Proof), C's admission
(`created→ready`) post-dates both predecessors' success, and nothing outside {A,B,C} dispatched
before the dependency gate (max predecessor-success time).

## A/B verification proof semantics
A2 (the qualifying retry) and B each carry a durable Proof and `verifying→succeeded`; both
precede C's composition; C's Proof `predecessor_commits` binds exactly {A-task→A2-commit,
B-task→B-commit}.

## C identity WITHOUT a new API field
C is the attempt whose Proof carries `predecessor_commits` (composition proof) — reachable via
the EXISTING `/api/umh/proof-inspector/packages/{proof_id}` endpoint. No `execution_kind`
exposure, no transport/candidate/schema change required.

## Files changed (authorized surface only)
- `scripts/wave2_field_collector.py` (+331/-70): new durable-observation helpers
  (`_attempt_detail`, `_transition_at`, `_dispatched_interval`, `_intervals_overlap`,
  `_composition_proof`, `_identify_composition`) + rewritten `_w16/_w17/_w18`.
- `tests/test_wave2_collector_history_observation.py` (NEW): 24 behavioral tests.
- **No** transport / candidate execution / scheduler / poller / lifecycle / promotion /
  projection / retention / composition / Task-D / authority / schema change. All required
  historical evidence exists in durable canonical state AND is reachable via existing read
  endpoints (`attempt_detail` exposes `transitions`; `proof-inspector` exposes
  `predecessor_commits`), so NO source widening / STOP was warranted.

## Most-important regression — PROVEN against real #52 evidence
The preserved #52 durable records (attempts ledger + composition Proof) reconstruct all three
stages to PASS: w16 `dispatched_overlap_s=81.3`, w17 `c_withheld=True`, w18
`both_proofed/composed_after/preds_bound=True`. The exact run that FAILED live now qualifies
from durable run-bound evidence.

## Behavioral tests (24) — the owner's 15 scenarios + discriminators
slow-passes, fast-already-succeeded-passes (#52), sequential-fails, C-blocked-from-history,
C-never-admitted-does-not-pass, ab-verified-after-terminal, missing-proof-fails,
wrong-predecessor-fails, failed-A1-cannot-verify, fast-complete-qualifies-all,
slow-complete-qualifies, reconstruct-after-completion, C-before-predecessors-fails,
missing-surface-fails, final-success-alone-insufficient, only-succeeded-verifies (not later
failed), foreign-predecessor-set-fails, commit-mismatch-fails, stale/foreign-run-rejected,
succeeded-without-transition-fails, foreign-early-advance-fails, + MOST-IMPORTANT regression.

## Mutation sweep — 0 non-equivalent survivors
| Mutation | Killed by |
|---|---|
| CM1 remove overlap requirement | sequential/overlap tests |
| CM2 sequential allowed (overlap≥0) | test_03/test_15 |
| CM3 C-blocked from final success only | test_13 |
| CM4 drop proof/succeeded guard (w18 collection) | test_20 (trailing-failed) |
| CM5 drop predecessor set-equality | test_17/test_21 (folded into preds_bound) |
| CM6 drop commit binding | test_18 |
| CM7 drop composed_after ordering | test_13 |
| CM8 running-instant instead of dispatched interval | overlap tests (running=0-width) |
| CM11 drop both_proofed | test_22 (succeeded-without-transition) |
| CM12 ignore early-advance | test_23 (foreign early dispatch) |

The redundant `preds_match` term (tautological with `pred_tasks` derivation) was FOLDED into a
single load-bearing `preds_bound` check to remove an equivalent-mutation surface.

## Substrate-assumption verification (independent, against source)
The durable reconstruction rests on three substrate facts, all confirmed in source:
- **`dispatched` = worker-execution window:** `poller.py:222-231` stamps `dispatched→running`
  "as soon as we see any result for a dispatched attempt" (`reason="worker result received"`),
  then `running→verifying` in the SAME pass — so `running` is a zero-width instant and the
  `dispatched` phase ([`leased→dispatched`, `dispatched→running`]) is when the worker actually
  ran. w16's overlap math is therefore correct.
- **Single-clock timestamps:** `AttemptTransition.at = field(default_factory=time.time)`
  (`records.py:276`), stamped by the store (`store.py:731-738`) on the VPS orchestrator — A and
  B's transitions are stamped by the same poller process on one host, so overlap comparison is valid.
- **`created→ready` = dependency-satisfied admission:** the scheduler gates `created→ready` at
  `scheduler.py:371` (`if not all(self._dep_lookup(d) for d in deps): continue`), and
  `_dep_lookup` (`:204-209`) returns True only for a dependency with a SUCCEEDED attempt AND a
  Proof. So C's `created→ready` provably cannot fire before both predecessors succeeded with
  Proofs — a real, scheduler-enforced ordering, exactly the w17 dependency-blocking semantic.

## Independent review pair — both PASS
Two fresh adversarial reviewers (no shared context), each answering the owner's two questions
and each DRIVING the real stage methods with fabricated durable records for every false-inference
vector.

- **PRIMARY** ("Can a correct fast-completing run fail merely because the collector polls after
  transient states advanced?") — **Reviewer A: NO. Reviewer B: NO.**
- **SECONDARY** ("Can it falsely infer concurrency/dependency/verification from final success?") —
  **Reviewer A: NO. Reviewer B: NO.** (Both drove all four attack vectors — a/b/c/d — every one
  fail-closed.)
- **Critical / Wave-2-blocking-High: NONE (both).**

Both independently confirmed the three substrate assumptions (dispatched=execution window,
single-host clock, `created→ready` = dep-gated admission), and Reviewer A additionally verified
`composition.py::resolve_predecessor_commits` refuses to compose until each predecessor is
SUCCEEDED with a pinned `refs/umh/verified` commit — so C provably cannot begin before both
predecessors verified (making the w17 ordering physically real, not merely observed).

Four convergent LOW/informational observations, none blocking, all fail-CLOSED (never false-pass):
(1) 1s clock slack — safe (same-process timestamps + substrate hard-guards ordering; `test_13`
proves a genuinely-early C still fails); (2) w16 measures first-attempt (possibly failed)
dispatched windows — legitimate/stricter, fail-closes if absent; (3) 12-char commit prefix match —
C's side is the authoritative pinned ref, a mismatch fail-closes; (4) w16 keys the A/B pair off
C's composition — intentional whole-scenario fan-in cert, fail-closed. No finding required a change.

## Non-field requalification — GREEN
- `tests/test_wave2_collector_history_observation.py`: 24 passed. `#52` durable evidence
  reconstructs all three stages to PASS.
- All 65 `tests/test_wave2_*.py` files: **1754 passed, 0 failed**.
- Gates: type-divergence registry-audit (1165 entries) ✓; dependency-direction ✓; cpu-gate ✓;
  ontology-homes ✓; projection-leak ✓; instance-leak ✓. `ruff check` + `ruff format` clean.

## Scope note
`_w19_c_reconverges` (C reconverges/succeeds) was left unchanged — it observes a TERMINAL
success state (persists, unlike the transient w16/w17/w18 states) and is outside the authorized
w16/w17/w18 surface.
