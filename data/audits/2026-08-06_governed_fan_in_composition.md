# Governed Fan-In Composition — Implementation Ledger

**Packet SHA:** `86904563ec76ead11de27f551a9f6f3e77572753`
**Parent (authorization SHA):** `14c57a211fec861e2a3aa28f8621c4104a254fed`
**Branch:** `feat/mvp-wave2-governed-execution` (PR #313, OPEN / DRAFT / UNMERGED)
**Date:** 2026-08-06

---

## What was closed

Verified-commit retention (PR #313 @ `14c57a211fec`) pinned each SUCCEEDED worker
attempt's commit under `refs/umh/verified/<candidate>/<run>/<task>/<attempt>` before
the lease was released — and **nothing consumed those commits**. With Task C
depending on verified Tasks A and B, the scheduler had no way to compose the two
verified commits, no way to create an attempt without a model worker, and no way to
hand the result to Task D.

This packet ships the complete production wiring:

```
verified predecessor Attempts
  → protected refs/umh/verified commits
  → deterministic conflict-free merge-tree composition
  → Attempt-bound integration verification
  → Attempt-bound Proof
  → refs/umh/composed (the downstream trusted base)
  → bounded cleanup with a real zero-residue gate
```

---

## Measured git semantics (probe run BEFORE encoding)

The first implementation action was the authorized throwaway-repo probe on
**git 2.43.0**. It confirmed most of the documented table — and **contradicted one
entry**, which was reported and corrected before any contract was encoded.

| Behavior | Documented | Measured | Encoded |
|---|---|---|---|
| clean merge | rc=0, stdout line 1 = tree OID | ✅ confirmed | rc=0 + 40-hex ⇒ success |
| conflict | rc=1 + conflict stages | ✅ confirmed (stage 1/2/3 lines) | rc=1 **with** tree OID ⇒ `CompositionConflict` |
| **git error** | **rc>1** | ❌ **a bad/unmergeable commit ALSO returns rc=1** | rc=1 **without** tree OID ⇒ `CompositionError`; plus a `cat-file -t` pre-flight |
| bad `--merge-base` | rc>1 | ✅ rc=128 | rc>1 ⇒ `CompositionError` |
| tree order-independence | assumed | ✅ `merge-tree(A,B) == merge-tree(B,A)` | canonical sort is for PARENT order, not the tree |
| commit determinism | assumed | ✅ same inputs ⇒ same SHA; parent order / message / dates each change it | identity + dates pinned, parents canonically sorted |
| delete | — | path ABSENT in composed tree | `D` ⇒ must be absent |
| rename | — | old absent, new present, blob preserved | `R` ⇒ old absent + new present, blob+mode equal |
| mode change | — | `100644`→`100755`, blob unchanged | `T`/`M` ⇒ mode compared explicitly |
| empty file | — | canonical `e69de29b…` | equality on blob SHA, no special case |
| CAS `update-ref … ""` | — | second create fails | race-free pin |

**The contradiction mattered.** Classifying on the return code alone would have
reported a *missing or garbage-collected trusted ref* as a *content conflict* —
the wrong failure class, and Requirement 10's conflict test would have passed for
the wrong reason. Fixed by (a) validating every predecessor with `cat-file -t`
before merge-tree, and (b) classifying by `(rc, stdout shape)`, never rc alone.

---

## Mandatory Clarification A — same-Attempt lease recovery

Resolved against source; **no lifecycle or store widening was required.**

| Question | Answer | Evidence |
|---|---|---|
| Does reacquisition mint a new `lease_id`? | **Yes** | `leases.py:51` — `default_factory=lambda: _new_id("lease")`; no caller may supply one |
| Does `ExecutionAttempt` persist `lease_id`? | Yes | `records.py:116` |
| Is it immutable? | **No — mutable binding field** | `'lease_id' in ATTEMPT_IMMUTABLE_FIELDS` → `False` (executed) |
| Who resolves the lease? | **`attempt.lease_id`, never by attempt_id** | `terminalization.py:206`, `:471`, `:578`, `:678`; `poller.py:466-478`. There is no `lease_for_attempt()` path — so a stale `lease_id` WOULD terminalize the wrong lease. The hazard is real. |
| Is `leased → leased` legal? | **No** | `TRANSITIONS['leased'] == ('dispatched','verifying','blocked','cancelled')` |

**Selected mechanism (all edges already legal):** `LEASED → BLOCKED → READY → LEASED`,
rebinding `lease_id` in the same CAS that re-enters LEASED. Same `attempt_id`
throughout; no illegal mutation; no new Attempt.

| Persisted state | Lease record | Action |
|---|---|---|
| LEASED | active row, `lease_id` matches, worktree exists | **Reuse** (no transition) |
| LEASED | active row, `lease_id` **mismatched** | **FAIL CLOSED** — rival identities, never guess |
| LEASED | released/revoked/expired/absent | **Rebind** via BLOCKED→READY→LEASED |

Note: `LeaseManager.expire_stale` has **zero production callers**, so in production a
lease does not auto-expire on restart — the reuse path is the normal one and the
rebind path covers crash-swept/revoked leases.

---

## Mandatory Clarification B — zero-residue is wired into qualification

Four **separate** outcomes, deliberately not collapsed:

| Outcome | Field | Rule |
|---|---|---|
| Operational teardown | `RunSweepResult.ok` | MAY pass with quarantined refs — the host must still destroy credentials and shred the secret |
| Evidence preservation | quarantine record | PASS when written |
| Residue accounting | `quarantined_refs` | every survivor listed |
| **Field qualification** | `zero_ref_residue` | **FAILS while ANY ref survives** |

`quarantined_refs ⊆ ref_residue` — quarantine accounts for a leak, it never converts
one into "clean". Wired at the **real production caller**:

`_sweep_run_homes` (`wave2_field_dispatch.py:1959-1975`) → `sweep_run(run_root, repo_root=…/fixture, candidate=sha, run_id=run_id)`
→ `teardown()` (`:1915`) → mandatory gate `teardown:zero_ref_residue`
(`qualification_verdict`, `:2907+`). A **missing** key is treated as FAILURE, so an
older teardown result cannot let residue hide behind absence.

---

## Composition authority — why a new persisted field was unavoidable

`WorkPacket` has **no** `semantic_label` field (verified: `grep` returns zero hits in
`substrate/organism/work_packet.py`). The label is written onto the lane → gap →
`ObjectivePlanNode` (`compiler.py:218`, `:557`) and **stops there**;
`materialize_packets` never copies it to the packet. `lifecycle.py` receives only the
attempt, so it could not see it under any design.

Empty-worker inference was also refuted by **real production data**: run
`20260805T182714Z-p1` shows `worker_identity == 'cc-cli@vps-host'` on **all five**
attempts including the three FAILED ones — the field never varies, so it
discriminates nothing.

**Minimum addition:** `AttemptExecutionKind` + immutable
`ExecutionAttempt.execution_kind`, stamped once at creation from the **validated**
scenario map and listed in `ATTEMPT_IMMUTABLE_FIELDS` (so `transition_cas` raises on
any `updates` write). Legacy records deserialize to `worker` — **no migration**
(`_from_dict` filters unknown keys and back-fills defaults, `records.py:36-37`).

---

## Verification performed

| Item | Result |
|---|---|
| Fan-in behavioral tests | **43 passed** — real git, real stores, real leases, real sandboxes |
| Production-shaped A+B→C→D | **PASS** — real `AttemptScheduler`, `ExecutionAttemptStore`, `LeaseManager`, `SandboxManager`, lifecycle CAS, `ProofRuntime`, `terminalize` |
| Verified-retention regression | **PASS**, unchanged |
| Run-teardown regression | **PASS** |
| Terminalization regression | **PASS** |
| Full Wave 2 suite | **1505 passed** (up from 1501) |
| Pre-existing failures | 16 failed / 26 errors, ALL `test_phase14_*`, **verified identical at pristine HEAD via `git stash`** — unrelated to this packet |
| Mutations | **29 applied, 29 killed, 0 survivors, 0 unapplied**; every file restored byte-identically (sha256 checked) |
| Gates | **15/15 PASS** |

Mutation coverage spans all ten required layers: scenario-map authority, scheduler
composition routing, lifecycle transition, retained-ref resolution, composition,
acceptance verification, Proof binding, downstream base propagation,
terminalization, teardown qualification. Three scheduler mutations and the lifecycle
transition-table mutation are killed **through the production-shaped A+B→C→D test**,
not through a direct unit test.

### Defects found and fixed during implementation

1. **Unconditional `base_commit` kwarg broke lease-manager compatibility.** Passing
   it always broke any `acquire()` predating the parameter — measured: it broke
   `test_admission_failure_releases_the_lease`, which then leaked a lease because
   the pass aborted *before* acquiring one. Fixed: pass it only when a base was
   actually resolved, so the non-composition call is byte-identical to before.

2. **`ruff --fix` swept 413 files.** Reverted all 402 unauthorized files; only the
   11 authorized files are in the commit. `scripts/wave2_field_dispatch.py` was
   restored to pristine and re-patched by hand so its diff is exactly the two
   functional hunks (30 insertions, 1 deletion) with no cosmetic reflow of the
   frozen driver.

---

## Field state (no execution performed)

| Item | State |
|---|---|
| Field execution | **NONE** — no attempt file written today; no dispatch process |
| Quota | **37/42 — UNCHANGED** |
| Leaked refs | **ZERO** in the worktree and in `/opt/OS` |
| Working tree | clean (tracked source); only pre-existing `data/umh/` runtime drift |
| Mesh hotfix | **unchanged** — `git diff 14c57a211fec..HEAD -- transports/node_mesh/ services/` is empty |
| PR #313 | **OPEN / DRAFT / UNMERGED** |
| Wave 3 | **NOT STARTED** |

### Driver digests

| SHA | `scripts/wave2_field_dispatch.py` sha256 |
|---|---|
| `14c57a211fec` (old) | `1ebd916abc244bfe2c2460d0f4e687a6493d1600b12d38a23a6e2e559238d809` |
| `86904563e` (new) | `0b6e171d45510dc5af57de9726d098fe6f0490a5f857fe405cedcf4181db604b` |

The driver changed by exactly the two authorized functional hunks (sweep binding +
zero-residue gate) and must be **re-frozen for the new exact SHA** before any field
invocation.

---

## Bounded residuals (stated, not hidden)

1. **The driver's own `_composition_producer` is not exercised end-to-end by an
   automated test.** The production-shaped A+B→C→D test drives the real scheduler
   with a behaviorally equivalent local producer, because the driver's closure
   requires a full candidate state tree (`execution_binding.json`, canonical plan /
   packet / grant JSONL) that only a real field run materializes. What IS proven
   automatically: all four closures construct correctly for a candidate-shaped path
   and return `None` cleanly for a non-candidate path; the producer is wired into
   `_build_scheduler`; and the scheduler's composition fork, base threading and
   predicate are each mutation-killed through the production path. First field run
   is the remaining proof.

2. **`_composition_acceptance_verifier` runs a confined full-suite pytest against an
   isolated checkout of the composed commit.** Its three conjuncts (suite exit code,
   predecessor-derived collection floor, both-parent ancestry) are individually
   tested, but the bwrap-confined execution itself is only reachable on a host with
   the verifier fixture present — same first-field-run caveat.

3. **`LeaseManager.expire_stale` still has zero production callers.** Not introduced
   by this packet and not in its authorized surface; recorded because the recovery
   design depends on knowing it.
