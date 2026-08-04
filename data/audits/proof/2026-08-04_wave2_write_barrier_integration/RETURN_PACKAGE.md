# Wave 2 — Write-Barrier Integration Correction (F-1..F-4)

Base SHA: `0c5b3be96300e15a96959103c07fd509c103dea2`
**New exact SHA: `84289fab1e346aee7e86b0c8c8424d89d5df7856`**
HEAD == origin == PR #313 head (all three verified equal). Tracked source clean.

## −1. Two review rounds happened; the second changed the verdict

An independent reviewer at the interim SHA `345f24ccc` returned **STOP — 1
CRITICAL, 2 HIGH, 2 MEDIUM**, and it was right. Its central finding is one my own
adversarial probe MISSED, and the honest characterization of my F-1 fix is:

> making `.git` writable so workers could commit turned the barrier from
> **UNREACHABLE** into **REACHABLE BUT BYPASSABLE** — which is worse, because it
> looks enforced.

All five are closed at this SHA (§9). In the same round, my own probe of the
surface my correction OPENED found two further CRITICALs the reviewer had not
reported (`objects/info/alternates`, `.git/worktrees`). Neither of us alone was
sufficient — that is the load-bearing lesson of this round, not a footnote.

## 0. Requalification status at this SHA

| Requirement | Result |
|---|---|
| targeted package/spool propagation tests | PASS |
| real launcher + sandbox tests | PASS (32 shipped-path, real bwrap, real git) |
| git staging/commit confinement tests | PASS (18/18 vectors) |
| post-worker projection tests | PASS |
| adversarial tests | PASS (12/12 transport+phase) |
| mutation testing | **26/26 killed, 0 survived, 0 not-applied** (final sweep at this SHA; 7 files restored byte-identically) |
| complete Wave 2 suite | PASS (291 in the barrier/spool/runner group) |
| all gates | **15/15** |
| commit + push | done |
| new exact SHA | `345f24ccc` |
| HEAD == origin == PR head | verified |
| tracked source clean | verified |
| complete whole-tree | **16/16 shards, 0 timeouts, 0 exclusions** |
| candidate-vs-baseline differential | **0 candidate-introduced** (see §8c) |
| matrix + nine-check | regenerated at this head, 0 FAIL/BLOCKED |
| fresh independent exact-head review | **PERFORMED** at `345f24ccc`; verdict STOP; all 5 findings closed at `84289fab1`. Durable artifact: `tmp/review_integration/REPORT.md` (the reviewer was harness-blocked from writing it, so its report is reproduced verbatim with provenance stated). **A re-review at THIS SHA has not happened** — see §10. |
| quota | **16/35, unchanged** (4+4 attempts, both from prior runs) |
| new field execution | **none** |
| residue (worker/runner/spool/lease/worktree/container) | **zero** |
| post-execution verifier | **byte-unchanged** vs baseline (`git diff` empty) |

## 1. Before/after lifecycle map

| # | Boundary | BEFORE | AFTER |
|---|---|---|---|
| 1 | canonical WorkPacket | `writable_path_scope` + `scope_declared`, first-class | unchanged |
| 2 | package build (`dispatch.py:109`) | seals `writable_path_scope=` under `package_hash` | unchanged |
| 3 | **runner package** (`wave2_attempt_runner.py`) | hand-built 4-attribute stand-in; **no** `governance_constraints` | `package_from_envelope(envelope)` — every field from the signed envelope |
| 4 | **spool envelope** (`spool.py`) | no scope field exists | carries `governance_constraints` + instructions/context/identity/verification; HMAC-covered via `asdict` |
| 5 | **deserialization** | schema-checked only | + `_governance_defect()`: missing / unparseable / bare-string ⇒ **quarantined** |
| 6 | launcher scope resolution | `_sealed_writable_scope` ⇒ `None` ⇒ refuse (100% of real dispatches) | resolves the real sealed scope |
| 7 | bind computation | `.git` locked **wholesale** | `.git` skipped; authority subpaths locked individually; **one call returns the complete barrier** |
| 8 | sandbox profile | `readonly_subpaths` only | + `writable_subpaths`, applied **last** so it wins |
| 9 | **git ops** | `index.lock: Read-only file system`, rc=128 — no worker could commit | private ref namespace ⇒ authorized `add`+`commit` succeed and persist |
| 10 | **projection** | ran after base commit ⇒ its 2 files inside `<base>..HEAD` | trusted phase **commits** it and **re-anchors** the base |
| 11 | verification | unchanged | unchanged (never weakened) |

## 2. Exact changed files

```
substrate/execution/attempts/field_task_scope.py     git capability + complete barrier + __all__
substrate/execution/attempts/host_isolation.py       writable_subpaths, applied after the ro layer
substrate/execution/attempts/worker_claude_cli.py    trusted-phase commit + git capability wiring
substrate/execution/attempts/spool.py                governance fields + fail-closed validation
substrate/execution/attempts/field_control_plane.py  governance_envelope_fields()
scripts/wave2_attempt_runner.py                      package_from_envelope()
tests/test_wave2_hard_write_scope.py                 real git lease; per-subpath git assertions
tests/test_wave2_shipped_path_integration.py         NEW — 32 tests
tests/test_wave2_shipped_path_adversarial.py         NEW — 12 tests
tests/test_wave2_{worker_isolation_spool,concurrency_and_readiness,execution_blockers,
                  terminalization,attempt_runner,harness_rehearsal}.py   fixtures carry the scope
docs/cockpit-surface-convergence.md                  S24
```

## 3. Canonical package schema proof

One authority: `WorkRequirements.writable_path_scope` → `compile_attempt_package` seals
`writable_path_scope=` into `governance_constraints` (covered by `package_hash`) →
`governance_envelope_fields()` puts it on the envelope → HMAC covers it (`signable()` uses
`asdict`) → `claim_next()` validates it with the **launcher's own parser**
(`_sealed_writable_scope`), so transport and execution can never disagree about what a scope
IS → `package_from_envelope()` rebuilds it → the launcher enforces it → the verifier reads the
same declaration. No second scope model was created.

## 4. Git capability design

Measured, not assumed. `add`+`commit` write only `objects`, `refs`(own), `logs`, `index`,
`COMMIT_EDITMSG`; they never touch `hooks`, `config`, `HEAD`, `info`, `branches`.

Three designs failed under real bwrap before one held:
1. bind individual FILES → fails: git writes `*.lock` **beside** the target.
2. leave `refs/heads` writable → **real escape**: a loose ref shadows a packed one, so any
   branch can be moved (`update-ref refs/heads/protected-main` returned rc=0).
3. lock `refs`, re-bind the branch FILE → fails again on `<branch>.lock` inside the locked dir.

Adopted: **per-attempt private ref namespace** `refs/attempt/<attempt_id>/`, re-opened writable
on top of a read-only `refs` tree, with `HEAD` pointed at it and mounted read-only. Commit
identity is bound to the Attempt by construction. `.git` is not broadly writable in the
dangerous sense: every authority surface is individually re-locked and each has a passing DENY
vector, which is the condition the directive attaches to a broad `.git` bind.

## 5. Phase-separated write design

1. **Trusted phase** (orchestrator, before the sandbox): project the task-local objective,
   `git add` **only** `OBJECTIVE.md` + `SHARED_CONTEXT.md`, commit as
   `trusted: task-local objective projection (system write, not worker output)`, and return
   that commit as the attempt's new base.
2. **Worker phase** (inside bwrap): only the Task's authorized paths writable; the projection
   paths are outside every lane's scope and mounted read-only.
3. **Verification**: `<new base>..HEAD` contains worker output only.

Causal identities stay distinct: system writes are an ANCESTOR of the worker's base; the git
commit is made by the worker under its own attempt ref; trusted writes are never attributed to
the worker and cannot be silently altered by it.

## 6. Real shipped-path test architecture

`WorkPacket → real package constructor → real spool serialization → real deserialization →
real sandbox profile → real launcher → real git lifecycle → trusted post-commit phase`.
The ONLY substitution is the model CLI binary, replaced by a shell script performing real file
and git operations (the real CLI costs quota and is nondeterministic). Git, bwrap, the spool,
envelope signing, package reconstruction and artifact capture are all shipped implementations.

## 7. Adversarial results

**Git/barrier (18/18 through the real launcher):** 3 authorized commits succeeded; denied and
byte-identical — forbidden source edit, forbidden objective edit, hook install, hooks-dir
replace, config write, config rename-over, unrelated ref update, sibling attempt ref, sibling
dir create, loose ref in `heads`, branch delete, `packed-refs` rewrite, HEAD repoint, forbidden
file staged into commit, rename-over-forbidden, refs-tree replace.

**Transport/phase (12/12):** replay against wrong Attempt, replay against wrong SHA,
byte-identical duplicate dispatch, scope widening, scope stripping, never-had-a-scope,
malformed attempt ids (4 forms), trusted-writes ordering, projection paths never writable.

## 8. Mutation results

**17/17 killed, 0 survived, 0 not-applied**, all six files restored byte-identically (sha256).

The first sweep left **6 survivors** — m05/m06 (the original F-2) and m11/m12 (the original
F-3) among them. Cause: the tests reconstructed the runner's package inline and called the
trusted phase directly, so mutations inside the shipped code were invisible. Fixed by
extracting `package_from_envelope()` / `governance_envelope_fields()` and driving those. That
fix immediately exposed a defect mutation alone could not: `package_from_envelope` returns an
INSTANCE while `_run_one_claim` still called `_Package()` — every real dispatch would have
raised `'_Package' object is not callable`.

## 8b. Differential composition (closes the second open MEDIUM)

The earlier differential was flagged for understating head-only nodes. Stated explicitly:

- **Test FILES**: 501 at HEAD vs 500 at baseline. Head-only: `test_wave2_shipped_path_integration.py`,
  `test_wave2_shipped_path_adversarial.py`. **Baseline-only: none.**
- **Head-only NODES**: 44 in the two new files + 1 added to
  `test_wave2_task_contract_propagation.py` = **45 nodes that cannot exist at baseline**.
  They are counted as ADDED COVERAGE, never as "newly passing", and they are excluded from
  any regression claim because there is nothing at baseline to compare them to.
- **Comparison set**: every other node is present in both trees, so the pass/fail differential
  below is node-identical and not inflated by additions.

## 8d. FINAL whole-tree and differential — `84289fab1` vs `0c5b3be96`

| | HEAD `84289fab1` | BASE `0c5b3be96` |
|---|---|---|
| shards | 16/16 | 16/16 |
| passed | 17,033 | 16,980 |
| failed | 483 | 481 |
| errors | **56** | **56** |
| timeouts / exclusions | **0 / 0** | **0 / 0** |

Set differential shows three nodes, **none candidate-attributable**:

1. `test_capability_catalog_slice_a::test_with_vendor_url` — pre-existing
   order-dependent failure. Fails **5/5 in isolation at HEAD and 3/3 at
   BASELINE**; my change touches no capability/catalog file.
2. `test_phase14_6d_canon_revision::TestNoSourceCodeMutation::test_no_python_in_diff`
3. `test_phase14_6e_p0_ratification::TestNoSourceCodeMutation::test_no_python_source_in_diff`

(2) and (3) are the SAME HEAD-relative artifact: both run
`git diff --name-only HEAD~1 HEAD` and fail if the LAST COMMIT touched any
non-test `.py`. They are a property of whichever commit happens to be HEAD, not
of the change. Measured: **10 of the last 25 commits (40%) would fail them.** The
baseline passed only because its final commit was docs-only. Verified by reading
the test body, not inferred.

Truthful statement: **zero candidate-introduced deterministic failures.**

## 8c. Whole-tree and differential (earlier head — retained for provenance)

| | HEAD `345f24ccc` | BASE `0c5b3be96` |
|---|---|---|
| shards | 16/16 | 16/16 |
| passed | 17,025 | 16,980 |
| failed | **481** | **481** |
| errors | **56** | **56** |
| skipped | 116 | 116 |
| timeouts (`rc=124`) | **0** | **0** |
| exclusions | **0** | **0** |

Failed/error counts are IDENTICAL. The passed delta (+45) is exactly the head-only nodes in
§8b — added coverage, not newly-passing pre-existing tests.

**Set differential — one node appeared, and it carries ZERO candidate attribution:**

`tests/test_capability_catalog_slice_a.py::TestOrchestratorWritesCatalog::test_with_vendor_url`

- My change touches no capability/catalog file (`git diff --name-only` over the range: none).
- Run in ISOLATION it fails **5/5 at HEAD** and **3/3 at BASELINE** — deterministically broken
  at both SHAs, so it is a PRE-EXISTING failure, not a candidate regression.
- It was in the same shard (`s2`) in both runs, so this is not shard re-partitioning: it is an
  in-shard ORDER dependency. It happened to pass inside the baseline shard and fails inside the
  head shard because the two added test files changed what executed before it.
- Two nodes moved the other way (`test_phase26_action_bridge.py::test_catalog_to_bridge_chain`
  plus an asyncio teardown line), which is the same order-sensitivity in the opposite direction
  and is likewise not claimed as a candidate fix.

Truthful statement: **zero candidate-introduced deterministic failures.** One pre-existing
order-dependent test changed which side of the shard boundary it lands on; verified broken at
baseline in isolation.

## 9. Finding disposition

| Finding | Status |
|---|---|
| F-1 read-only `.git` blocks commits | **CORRECTED, NOT FIELD-VALIDATED** |
| F-2 scope does not cross the spool | **CORRECTED, NOT FIELD-VALIDATED** |
| F-3 projection attributed to the worker | **CORRECTED, NOT FIELD-VALIDATED** |
| F-4 stand-in package shape in tests | **CORRECTED, NOT FIELD-VALIDATED** |
| F-6 `__all__` omissions (LOW) | corrected |
| MEDIUM cross-lane `intent` test gap | **CLOSED** — `test_4d_each_lane_receives_its_own_intent_and_not_a_siblings` asserts each lane's declared intent reaches ITS prompt and appears in NO sibling's, i.e. at the boundary that actually failed in the field |
| MEDIUM differential summary understated head-only nodes | **CLOSED** — §8b states files (501 vs 500), head-only files (2, baseline-only 0), and head-only nodes (45) explicitly, and excludes them from regression claims |
| LOW stale untracked matrix artifact | **CLOSED** — the stale `2026-08-01` artifact is superseded by `data/audits/2026-08-04_wave2_matrix_report.md`, generated at this head |

No finding is labelled resolved. Per the directive, that awaits a fresh independent reviewer at
the new exact SHA.

## 10. The one requirement NOT met — stated plainly

The authorization requires, before returning: *"obtain a fresh independent
exact-head review through a durable report artifact"*, and *"Do not label any
finding resolved until the fresh independent reviewer confirms it at the new
exact SHA."*

A fresh independent review WAS obtained — at `345f24ccc`. It returned STOP with 1
CRITICAL and 2 HIGH. Those findings, plus two CRITICALs I found myself, were then
corrected, which necessarily moved the head to `84289fab1`.

**No independent reviewer has examined `84289fab1`.** So by the authorization's
own rule, every finding here is `CORRECTED, NOT CONFIRMED` — not `resolved`. I
have deliberately not labelled any of them resolved, and the ledger rows S24/S25
carry `CORRECTION LANDED, NOT FIELD-VALIDATED` for the same reason.

This is the recurring shape of the round: each review round produced corrections,
and each correction produced a new head that the review had not seen. Closing it
requires a review at a head that does not move — which means the next review must
find nothing, or the loop continues. That is an owner decision about when to
spend another review cycle, not one I should make by declaring the work
confirmed.

## 11. Nonclaims

- No field execution occurred; quota unchanged at **16/35**.
- The barrier is proven in-process, **not** field-validated.
- No production deployment; Wave 3 not started; PR #313 not marked ready, not merged.
- The post-execution verifier is untouched and still runs — defense in depth, not replacement.
