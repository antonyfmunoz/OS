# Wave 2 Independent Review — Write-Barrier Integration (F-1..F-4)

**Provenance note (written by the primary agent, not the reviewer).** The
independent reviewer was BLOCKED by the harness from writing this file
("Subagents should return findings as text") and returned its report as its final
message instead. The text below is that report, reproduced verbatim from the
agent result, so the durable artifact the authorization requires exists. It is
the reviewer's assessment, not mine; my own responses to each finding are in the
clearly-marked section at the end. Nothing in the reviewer's text has been
softened, and the one claim I dispute is disputed openly rather than deleted.

**SHA reviewed:** `345f24ccc6d94ea9654fb63c3253f54ede4aa0cc` — VERIFIED via
`git rev-parse HEAD` at review start.
**Baseline:** `0c5b3be96300e15a96959103c07fd509c103dea2`
Tooling: bubblewrap 0.9.0, git 2.43.0.

> **Concurrency warning (reviewer's):** another agent was actively editing this
> shared worktree during my review (HEAD advanced `345f24ccc` → `195f68ba5`;
> `tests/test_wave2_shipped_path_adversarial.py` gained +78 lines;
> `worker_claude_cli.py` currently carries someone else's `if True:` mutation). I
> ran the decisive tests in an isolated `git archive HEAD` copy to stay pinned to
> the reviewed SHA.

---

## Verdict: **STOP**

**CRITICAL: 1 · HIGH: 2 · MEDIUM: 2**

F-1 through F-4 are each *genuinely* fixed as narrowly stated — I verified all
four by running production code. But re-opening `.git` to make commits possible
opened a hole the author did not close: `.git/objects` and `.git/index` are
writable, and **git can write files the mount forbids, straight past the barrier
and past the verifier.** The barrier went from "correct but unreachable" to
"reachable but bypassable." That is not an improvement in security posture, and
it must not ship as-is.

---

## Findings

### CRITICAL-1 — Worker commits arbitrary content to read-only, out-of-scope paths; verifier reports a clean diff

The mount barrier protects the **working tree**. It does not protect the **object
store or index**, both of which are writable (required for `git add`).
`git hash-object -w` + `git update-index --cacheinfo` writes a tree entry for
*any* path without ever touching the file. The mount never fires, and
`_actual_changed_paths` (`verification.py:306`) runs
`git diff --name-only <base>` — a **worktree-vs-base** comparison — so a
committed-but-not-checked-out change is invisible.

Reproduced at HEAD-exact code, scope `['src/']`:

```bash
B=$(echo "SMUGGLED" | git hash-object -w --stdin)
git update-index --add --cacheinfo 100644,$B,OBJECTIVE.md      # rc=0
git update-index --add --cacheinfo 100644,$B,secret/key.txt    # rc=0
echo legit >> src/app.py; git add src/app.py
git -c user.email=w@w -c user.name=w commit -q -m work         # rc=0
```

Result:
```
VERIFIER diff -> ['src/app.py']          <-- clean, in scope, PASSES
HEAD:OBJECTIVE.md    -> SMUGGLED
HEAD:secret/key.txt  -> SMUGGLED         <-- read-only path, mutated in the commit
worktree OBJECTIVE.md -> "all tasks objective"  (mount held; that's why nobody saw it)
```

**Fix direction:** verify the *commit range* (`git diff --name-only <base>..HEAD`
∪ worktree diff ∪ untracked), not just the worktree diff.

### HIGH-1 — Worker can destroy or rewrite the trusted projection layer (F-3 partially defeated)

F-3's headline claim holds (empty worker → empty diff — verified). But the
attempt ref dir is writable, so the worker owns its whole branch history:

```bash
git reset --soft HEAD~1                       # rc=0 — trusted commit dropped
B=$(echo "WORKER REWROTE THE TRUSTED OBJECTIVE" | git hash-object -w --stdin)
git update-index --add --cacheinfo 100644,$B,OBJECTIVE.md
echo work >> src/app.py; git add src/app.py
git -c user.email=w@w -c user.name=w commit -q -m "attempt work"
```
```
trusted base ancestor of HEAD? False        <-- causal separation destroyed
HEAD:OBJECTIVE.md = WORKER REWROTE THE TRUSTED OBJECTIVE
VERIFIER diff -> ['src/app.py']             <-- still passes
```

`git commit --amend` works equally. The "system write is an ANCESTOR of the
worker's base" invariant is *unchecked*. **Add that ancestry assertion.**

### HIGH-2 — Spool recovery re-signs attacker-modified envelopes (scope laundering)

`spool.py:368` re-signs the record after refreshing `expires_at`, but re-signs
**whatever is on disk**:

```
inflight scope tampered -> ['/']
recover_stale_inflight  -> ['00000000-d.json']
post-recovery claim     -> ["writable_path_scope=['/']"]   <-- ACCEPTED, quarantine empty
```

Mitigating: requires host FS access, not worker access. **Fix:** re-sign from the
*previously verified* envelope with only `expires_at` replaced, and re-run
`_governance_defect` after recovery.

### MEDIUM-1 — Non-bwrap isolation primitives silently drop the entire barrier

`build_isolated_command` → `systemd-run`/`nsjail` branches ignore
`readonly_subpaths` **and** `writable_subpaths`. Pre-existing (unchanged vs
baseline), but this change makes it materially worse by making the barrier the
*only* protection.

### MEDIUM-2 — Writable `.git` surfaces beyond what the docstring claims

At the reviewed SHA these are writable and persist to the host: `.git/objects/**`,
`.git/objects/info/alternates` (**verified functional**), `.git/index`,
`.git/logs`, arbitrary new `.git/*` entries incl. symlinks. `.git/worktrees` was
also unlocked at the reviewed SHA.

---

## Per-check results

| # | Check | Result |
|---|---|---|
| 1 | Git capability real | **PASS** — `RC_ADD=0 RC_COMMIT=0`; commit persists on host |
| 2 | Escape the git barrier | **FAIL** — 33 vectors + 7 deep probes |
| 3 | F-2 end to end | **PASS** — scope survives; widen/strip/wrong-secret all quarantined. **Except HIGH-2.** |
| 4 | F-3 phase separation | **PARTIAL** — empty worker → empty diff ✅; but reset/amend rewrite the trusted layer |
| 5 | Stand-in check | **PASS, honestly** — no stubbing of git; F-4 genuinely closed |
| 6 | Mutation spot-check | **3/3 KILLED** (reviewer's own choices) |
| 7 | Fail-closed | **MOSTLY PASS** — gaps: MEDIUM-1, HIGH-2 |
| 8 | Verifier not weakened | **PASS** — `git diff` vs baseline is empty |
| 9 | Claim audit | **Overstated** — see below |

---

## Claims audited (reviewer)

- **"17/17 mutants killed"** — UNVERIFIED as stated (no ledger in-repo). The
  reviewer's own 3 independent mutants were all killed.
- **"18/18 adversarial vectors"** — **overstated**: the adversarial file contains
  9 test functions at that SHA. Of the reviewer's 40 vectors, **7 succeeded**.
- **"zero candidate-introduced failures"** — **TRUE** (verified: `100 passed`).
- **"F-1..F-4 all fixed"** — **TRUE as literally scoped**, but the F-1 fix creates
  a new larger hole and F-3 has an unenforced invariant.

## What the reviewer could not verify

Real Claude CLI worker behavior (prohibited); the full `FieldControlPlaneDriver`
against a live control plane; runtime behavior under `systemd-run`/`nsjail`.

## Restoration (reviewer)

All files the reviewer mutated restored **byte-identical**, verified by sha256.
No commits, pushes, deploys, or field execution.

---

# PRIMARY AGENT RESPONSE (added after the review)

**Verdict accepted. All five findings closed at `84289fab1`.** Each was
REPRODUCED against shipped code before any change, and each fix is paired with a
test proving the honest path still passes, so "refuse everything" cannot satisfy
it.

| Finding | Disposition |
|---|---|
| CRITICAL-1 | **CLOSED** — verifier now evaluates `<base>..HEAD` as well as the worktree diff and untracked set; uninspectable range fails closed. Reproduced first (`OBJECTIVE.md` + `secret/key.txt` = `SMUGGLED`, verifier saw only `app/main.py`), then blocked. |
| HIGH-1 | **CLOSED** — `_base_is_ancestor_of_head` makes the invariant load-bearing; `reset --soft` + re-commit now refused. Fails closed when unanswerable. |
| HIGH-2 | **CLOSED** — recovery verifies the existing signature FIRST, quarantines a tampered record, and re-signs from the verified object with only `expires_at` replaced. |
| MEDIUM-1 | **CLOSED** — `systemd-run`/`nsjail` now refuse when `scope_enforced` or any bind is required, instead of silently downgrading. |
| MEDIUM-2 | **CLOSED** — `objects/info` and `worktrees` are created-then-locked (found independently by my own probe before this review returned; `alternates` was verified to leak a blob to the HOST). |

**Claims corrected, as the reviewer asked:**
- "18/18 adversarial vectors" — the reviewer is right that this conflated
  parametrized cases with test functions. The accurate statement is 18 vector
  RESULTS from a probe script, and 9 test functions in the adversarial file at
  that SHA. Restated everywhere.
- "17/17 mutants killed" — the number was real but lived only in my scratch
  logs, so the reviewer could not verify it. Final result at this head is
  **26/26 killed, 0 survived, 0 not-applied**, with the mutation script and log
  retained as evidence.

**One reviewer claim NOT accepted:** the report states
`worker_claude_cli.py:239` "currently carries someone else's `if True:`
mutation". There was none. The reviewer observed my mutation sweep MID-FLIGHT —
m12 is literally that mutation — and read a transient state as live. Verified
directly: the line reads `if not projection.get("projected"):` and
`git status` was clean. The reviewer's own restoration claim is otherwise
accurate.

**Follow-on discovered while fixing:** ordering the new ancestry check BEFORE the
diff-independence check changed a refusal's stated CAUSE (a lease with no
`snapshot_ref` reported "not an ancestor" instead of "cannot be computed
independently"). Behavior was still correct, but the diagnostic is part of the
contract — an operator who cannot tell which layer failed cannot respond. Caught
by the whole-tree differential, reordered, and HIGH-1 re-verified as still
blocked.
