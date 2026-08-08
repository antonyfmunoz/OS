# Invocation 40 Correction — Durable Object Promotion

**Date**: 2026-08-08 | **Baseline**: `9fa480d106a09e985788c5d11cd4ee9dadf39516`
**Defect**: invocation 40 (run `20260807T234550Z-p1`) — CRITICAL / Wave-2-blocking

## Root cause

`make_lease_selfcontained` copies the fixture's entire object store into the
lease's own `.git`, so a bwrap-isolated worker's commit objects live ONLY in the
lease's private object store. Retention writes refs in the durable fixture repo,
which never receives those objects → `update-ref … nonexistent object` on every
succeeded worker attempt → no retained commit → fan-in composition unreachable.

## Fix — control-plane object promotion

The control plane imports each attempt's reachable object closure into the
durable repo BEFORE verification settles, so the verifier proves an
already-durable object and retention pins that same object:

    VERIFIED_COMMIT_SHA == DURABLE_PROMOTED_COMMIT_SHA == RETAINED_REF_TARGET

- `promote_attempt_objects` (`verified_commit_retention.py`): `git fetch` of the
  attempt's private ref `refs/attempt/<id>/work` from the lease into
  `refs/umh/promoted/<cand>/<run>/<task>/<attempt>` in the durable repo. The
  commit is DERIVED by the control plane from the attempt ref, never from
  `worker_result.commits`.
- Poller (`poller.py`): promotion runs in `_verify_and_settle` BEFORE
  verification; promotion failure fails the attempt closed.
- Teardown (`run_teardown.py`): the promoted namespace joins the ref-release loop.

## Review findings closed (two independent review pairs)

| # | Severity | Finding | Fix |
|---|---|---|---|
| 1 | CRITICAL | Authorship forgery — worker points its ref at a foreign in-scope commit the self-contained lease copied in (incl. a prior promoted commit / retry contamination) | Authorship scan: every commit in `git rev-list base..head` must be NEW to the durable repo (`cat-file -e` each, before the fetch). Idempotency checked first so legit re-promotion isn't refused. |
| 2 | CRITICAL | Writable `.git/packed-refs` — worker corrupts its own git so promotion silently returns "" and the attempt SUCCEEDS with a durable Proof for a lost object | `packed-refs` create-then-locked in `git_readonly_subpaths` (empty file inert). |
| 3 | CRITICAL | Unreadable repo treated as "nothing to promote" (fail-open) | Promotion RAISES on rc≠0 rev-parse; mandatory non-empty base; missing-worktree explicit error. |
| 4 | CRITICAL | Writable `.git/commondir` — worker redirects where the locked HEAD symref reads refs from, into an evil git dir, forging a fresh foreign commit that slips past the authorship scan | `commondir` create-then-locked as the inert standalone value `.` (empty is fatal to git). |
| 5 | MEDIUM | `.git/shallow` truncation could hide a foreign parent from `base..head` | Documented + test-pinned: the `merge-base --is-ancestor` check runs FIRST and fails closed on exactly the cuts that hide an ancestor. |
| 6 | MEDIUM | Empty base disabled ancestry+authorship | Mandatory base — RAISES on empty. |
| 7 | MEDIUM | Missing worktree misreported as CPU overload (promotion + retention) | Explicit `os.path.isdir` check on both paths. |
| 8 | MEDIUM | Poller outer-guard consistency (worktree present, repo_root absent) | DISPOSITIONED: repo_root absent = "not a governed field run", not "lost durability"; must reach verification (non-field/retry callers). Unreachable for a real field worker (leases.py always sets repo_root with a worktree). |
| 9 | LOW | `.git/config.worktree` writable (benign — only sets core.worktree) | Create-then-locked for defense-in-depth symmetry (reviewer-recommended). |

## Verification

- 36 promotion tests (incl. 2 real-bwrap denial tests: packed-refs + commondir,
  and the full real-isolated-worker → promotion → retention → composition chain)
- 305 affected-suite tests, 1682 full Wave 2, all 14 gates + registry audit
- **Mutation sweep: 17/17 killed, 0 survivors**
- Two independent review pairs: final verdict 0 Critical / 0 Wave-2-blocking High

## Quota / state

Field quota unchanged at 40/45 — NO field execution during the correction cycle.
This correction mints a NEW SHA; the qualification sequence for `9fa480d10` is
permanently over (invocation 40 remains consumed).
