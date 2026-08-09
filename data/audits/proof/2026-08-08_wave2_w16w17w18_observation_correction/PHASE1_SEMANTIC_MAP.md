# Phase 1 — w16/w17/w18 Observation Semantic Map (traced before editing)

Collector: `scripts/wave2_field_collector.py`. All three stages read the CANONICAL
attempt ledger via API (`GET /api/umh/execution/by-plan/{plan_record_id}`, through
`_read_attempts`), NOT the DOM for the primary check (the DOM count is a secondary
corroboration in w16). The defect is that each stage checks the attempt's CURRENT
`status` field — a point-in-time snapshot — instead of reconstructing the required
transition from durable history.

## Durable evidence available (verified against invocation #52 records)

Each `ExecutionAttempt` carries a `transitions: list[{from_status, to_status, actor,
reason, event_id, at}]` array (`records.py:316`) with per-transition timestamps.
Reconstructed from #52:

| Attempt | dispatched interval (real worker execution) | verified/succeeded at |
|---|---|---|
| A1 `wp-d322f3853606` a1 (FAILED) | [213.086, 295.751] (82.7s) | failed 296.972 |
| B `wp-d22f64e318c6` a1 (SUCCEEDED) | [213.048, 294.363] (81.3s) | succeeded 295.722 |
| A2 `wp-d322f3853606` a2 (SUCCEEDED, prev=A1) | [297.027, 382.868] (85.8s) | succeeded 384.390 |
| C `wp-9a428972beb0` a1 (composition) | created→ready 384.435 → verifying 384.499 | succeeded 386.097 |
| D `wp-d87f2198112e` a1 (zero-write) | [388.170, 561.498] | succeeded 562.792 |

**A1 ∩ B dispatched-overlap = 81.3s** — genuine concurrency of the two independent
first attempts. (A2 is the sequential retry after A1 failed; 0 overlap with B, correct.)

## Per-stage semantic map

### w16_ab_running_concurrent
- **Intends to prove:** the two independent implementation tasks (A, B) executed
  concurrently — real temporal overlap.
- **Current predicate (WRONG):** poll until `status=="running"` for ≥2 distinct tasks
  *right now* (`_w16` line 1937-1956). `running` is a ZERO-WIDTH instant in the ledger
  (`dispatched→running` and `running→verifying` share a timestamp — the poller stamps
  both when the worker RESULT arrives), so a fast graph never shows two "running" at once.
- **Durable source:** the **dispatched-phase interval** (`leased→dispatched` → 
  `dispatched→running`) is the true worker-execution window. Concurrency =
  `A.dispatched_interval ∩ B.dispatched_interval != ∅`.
- **Concurrent pair identity:** the two tasks are the two *first* implementation attempts
  (attempt_number 1) that are NOT the composition task and NOT the verification task.
  A1||B is the qualifying overlap (A2 is recovery).

### w17_c_blocked
- **Intends to prove:** the integration task C was correctly WITHHELD until its
  predecessors (A, B) were complete — it did not run early.
- **Current predicate (WRONG):** poll until a non-A/B task shows `status=="blocked"` now,
  and no non-A/B task has advanced (`_w17` line 1980-2010). Once C composes+succeeds the
  live "blocked" snapshot is gone.
- **Durable source:** from `transitions`, C's `created→ready` timestamp is AFTER both
  predecessors reached a terminal-good state; equivalently, C has no `running`/`dispatched`
  transition earlier than the predecessors' success. And no non-A/B task advanced to
  running/succeeded before the predecessors verified.

### w18_ab_verified
- **Intends to prove:** A (its qualifying successful attempt) and B each SUCCEEDED with a
  durable Proof, BEFORE C consumed them, and C's composition binds exactly those results.
- **Current predicate (WRONG):** poll until 2 tasks in the running-set show
  `status=="succeeded"` with a `proof_id` now (`_w18` line 2025-2035). After reconvergence/
  teardown the live view may not show them.
- **Durable source:** each of {A-successful-attempt, B} has a non-empty `proof_id` and a
  `verifying→succeeded` transition; both succeeded BEFORE C's composition
  (`leased→verifying` by `composer:control-plane`); and C's composition Proof
  (`GET /api/umh/proof-inspector/packages/{proof_id}` → `action.predecessor_commits`)
  references exactly A's-successful and B's commits.

## C identity — WITHOUT needing a new API field
C is identified purely from durable evidence already API-reachable: **C is the attempt
whose Proof carries `predecessor_commits`** (composition proof). Verified from #52:
`proof-ea8f2c8cd591` → attempt `ea-3c87e8c62568` (task `wp-9a428972beb0`),
`predecessor_commits = {wp-d22f64e318c6, wp-d322f3853606}`. No `execution_kind` exposure
is required.

## Evidence availability & authorized surface — NO source widening required
| Need | Endpoint | Field | Reachable? |
|---|---|---|---|
| per-attempt transitions | `GET /api/umh/execution/attempts/{attempt_id}` (`attempt_detail`) | `transitions` | YES (line 139) |
| retry lineage | same | `retry_of_attempt_id` (=previous_attempt_id) | YES |
| verified proof id | same / by-plan | `proof_id` | YES |
| composition predecessors | `GET /api/umh/proof-inspector/packages/{proof_id}` (`_package_detail`) | `action.predecessor_commits`, `composed_commit` | YES (`pkg.to_dict()`) |

**Conclusion:** every required historical truth exists in durable canonical state AND is
reachable through EXISTING read endpoints. The correction is **collector-only**
(`scripts/wave2_field_collector.py` + tests). NO transport/candidate/scheduler/lifecycle/
schema change is required. No design-gap STOP is warranted.

The only extra cost is per-attempt `attempt_detail` calls (to obtain `transitions`, which
`by-plan`'s `_attempt_row` omits) — acceptable for a qualification harness; the collector
already knows each attempt_id from the by-plan read.
