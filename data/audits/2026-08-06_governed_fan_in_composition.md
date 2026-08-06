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

## Independent review round (two reviewers) — 4 real defects found and fixed

Both reviewers ran against `86904563e`. **Every finding was reproduced against
source before being accepted**; none was taken on assertion. The composition
*logic* (git semantics, persisted-kind authority, lifecycle guards, proof
idempotency, immutability, ref-namespace validation, CPU gating, base resolution)
was independently attacked — 25+ concrete attacks in the security review, all
refused — and held. **All four defects were in the WIRING**, and all four were
masked by the same root cause: the E2E test substituted its own producer, so ~445
lines of driver seam were dead to the suite.

### CRITICAL-1 — a composition attempt was never terminalized

**Reproduced:** the only production `terminalize()` callers are `poller.py:352`
and `:378`, both driven exclusively by `spool.drain_results()`. A composition
never enters the spool, so the poller can never see it. The lease stayed **ACTIVE
forever**, its sandbox slot was never freed (at the production `max_parallel=2`
that starves the rest of the run), and the credential home was never destroyed.

**Fixed:** `_produce` now terminalizes its own SUCCEEDED attempt
(`field_control_plane.py`). Composition is the one terminal path that must
terminalize itself, precisely because it is the one attempt the spool does not
carry. Non-fatal but loudly recorded — a cleanup fault must not un-succeed a
verified composition.

### CRITICAL-2 — two of three `sweep_run` callers reported clean over live refs

**Reproduced:** `wave2_attempt_runner.py:417` (the run's OWN authoritative
teardown, on every exit path) and `run_teardown.py:595` (`recover_stale_runs`)
both call `sweep_run` without the binding. The explicit-args-only design took the
early return and reported `zero_ref_residue=True` over refs it never looked at.
Measured: 2 live refs surviving, result claiming clean.

**Fixed:** `sweep_run` now DERIVES the binding from the run root via the one
canonical `resolve_run_binding()` when a caller omits it. This closes all three
callers **without touching `wave2_attempt_runner.py`, which is not in the
authorized surface**. Verified against the runner's exact call shape
(`sweep_run(run_root, spool=spool)`): 2 refs → 0.

### CRITICAL-3 — the production acceptance gate was never exercised

**Reproduced:** `passed = True` (acceptance disabled entirely) and dropping the
`bool(checks)` guard (so an EMPTY check list passes vacuously) BOTH survived a
fully green suite. A Task C could reach SUCCEEDED with a durable Proof and pin
`refs/umh/composed` with **zero verification**, and Task D would lease from that
unverified commit as a trusted base.

**Fixed:** new parametrized test drives the REAL
`_composition_producer` against empty checks / a failing check / a raising
verifier, asserting the attempt does NOT succeed and mints no Proof. Both
reviewer mutations now die.

### CRITICAL-4 — found by the new tests: a refused composition stranded in VERIFYING

`TRANSITIONS['verifying']` is `('succeeded','failed')` — there is **no BLOCKED
target**. `_block()` hardcoded BLOCKED, so a failed acceptance raised `illegal
transition 'verifying' → 'blocked'`, which the handler swallowed, leaving the
attempt stranded in VERIFYING with an ACTIVE lease and its slot held.

**Fixed:** `_block()` selects the legal terminal for the state it is actually in
(FAILED from VERIFYING — the same terminal the poller uses for
`verification_rejected`) and terminalizes it, so a refused composition releases
its resources.

### HIGH — `verify_composed_scope` shipped dead

Zero callers of any kind. It is the ONLY check preventing composition — a
control-plane-performed mutation — from putting content into the trusted
downstream base that a WORKER attempt would have been refused for. **Fixed:**
wired into the acceptance check list as `composition_scope_union`, with a test
that narrows the persisted scope and asserts the check fails.

### Post-review verification

| Item | Before review | After fixes |
|---|---|---|
| Fan-in tests | 43 | **50** |
| Mutations | 29 killed / 0 survived — **but the acceptance layer was never covered** | **38 killed / 0 survived / 0 unapplied** |
| Reviewer Mutation A (`bool(checks)` removed) | **SURVIVED** | **KILLED** |
| Reviewer Mutation B (`passed = True`) | **SURVIVED** | **KILLED** |

The pre-review commit message's "29 mutations across all 10 layers, 0 survivors"
was true as stated but **misleading**: the production acceptance layer had no
mutation coverage at all. That is corrected here rather than left standing.

---

## Bounded residuals (stated, not hidden)

1. **`_validated_integration_packet_id` is not exercised end-to-end.** The
   scenario-map gate (`validate_against_run`) needs a full candidate state tree
   (`execution_binding.json` plus canonical plan / packet / grant JSONL) that only
   a real field run materializes, so the real-driver tests stub that one lookup.
   What IS proven automatically: the gate is CALLED (not a bare mapping read), the
   binding resolver refuses ambiguity, all four closures construct for a
   candidate-shaped path and return `None` cleanly otherwise, and the producer,
   acceptance gate, scope union, terminalization and failure paths are each
   mutation-killed through the real driver. First field run is the remaining proof.

2. **The bwrap-confined suite execution inside the acceptance verifier is stubbed
   in tests** (it needs bwrap + the seeded fixture). Every other check in that
   assembly — packet identity, contract hash-match, ancestry, content equivalence,
   collection floor, scope union — runs for real, and the confined seam itself is
   already covered by the existing verifier-isolation suite.

3. **`LeaseManager.expire_stale` still has zero production callers.** Not introduced
   by this packet and not in its authorized surface; recorded because the recovery
   design depends on knowing it.

4. **`field_control_plane.py:454` has a pre-existing `except Exception: pass`** on a
   manifest write (flagged by the security review). It predates this packet and is
   outside its scope; recorded rather than silently widened into.

5. **`worker_identity` is not in `ATTEMPT_IMMUTABLE_FIELDS`.** Safe today because the
   composition guard reads the PERSISTED value before `updates` are applied, so a
   caller cannot blank it to slip through. Defense-in-depth note, not an exploit;
   `records.py` hardening is out of this packet's scope.
