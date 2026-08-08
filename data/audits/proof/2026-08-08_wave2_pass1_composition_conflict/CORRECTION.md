# Invocation 41 Correction — Task-Local Projection is Execution Context

**Date**: 2026-08-08 | **Failed SHA**: `69f9fe272d5bbb1b4d0b16b503e1879807ff8c5d`
**Defect**: invocation 41 (run `20260808T014829Z-p1`) — CANDIDATE / DETERMINISTIC / Wave-2-blocking

## Root cause

The worker trusted phase (`worker_claude_cli.project_task_local_objective` →
`_commit_trusted_projection`) rewrote `OBJECTIVE.md` to each Task's own
task-local objective, wrote `SHARED_CONTEXT.md`, **committed** them, and
re-anchored the attempt's base to that commit. That kept the projection out of
each worker's DIFF but placed it in each worker's retained LINEAGE:

- A's retained commit carried `OBJECTIVE.md` = "# Your Task … wp-47fb00e975d0"
- B's retained commit carried `OBJECTIVE.md` = "# Your Task … wp-94f3bcd9a755"

The worker code slices were perfectly disjoint (A: `app/static` + a UI test;
B: `app/main.py`+`app/store.py` + an API test). But `compose_predecessors`
correctly refused the tree because A and B genuinely conflicted on the
system-projected `OBJECTIVE.md`. Every predecessor pair conflicts by
construction → Task C blocks → Task D never runs → the graph never completes.

## Core invariant restored

**System-projected task context must not become worker-authored deliverable
content.** The worker may SEE its task-local objective during execution; the
trusted durable worker result must represent only the authorized worker delta
against the canonical governed base.

## Fix — the projection is EXECUTION CONTEXT, not versioned work product

`_mark_projection_execution_context` (replaces `_commit_trusted_projection`):

- tracked projection paths (`OBJECTIVE.md`) get `git update-index
  --skip-worktree` — measured on git 2.43: `status --porcelain`, `diff <base>`,
  `diff <base>..HEAD` all report nothing; `git add OBJECTIVE.md` is refused by
  git (sparse-checkout guard); `add -A`/`commit -am` skip it.
- untracked projection paths (`SHARED_CONTEXT.md`) are registered in
  `.git/info/exclude` — measured: absent from `ls-files --others
  --exclude-standard` (the exact untracked listing the verifier runs); a plain
  `git add` refuses them.
- the attempt is **NOT re-anchored** — HEAD stays the canonical governed base,
  so the retained commit is `canonical base + authorized worker delta`, nothing
  else, and disjoint predecessors compose cleanly.
- the marking **PROVES invisibility before any worker runs** (`status
  --porcelain` + `ls-files --others` over the projection paths) and RAISES
  otherwise — a projection that cannot be hidden fails closed, never runs a
  worker who would be blamed for system writes.

Producer/trust boundary hardening (composition unchanged — it must keep
rejecting genuine conflicts):

- `.git/info` is now **create-then-locked read-only** in
  `field_task_scope.git_readonly_subpaths` (moved out of the skip-if-absent
  tuple). `info/exclude` is an authority surface — a worker that could edit it
  could re-expose or hide untracked paths from the verifier.
- `run_worker_in_lease` refuses any sealed `writable_path_scope` that names a
  projection path (SYSTEM-OWNED PATH LAW): a worker must never gain authority to
  version control-plane execution context. Checked structurally against
  `TRUSTED_PROJECTION_PATHS`, never a hardcoded filename.

## The one remaining index channel, adjudicated

`.git/index` must stay writable (`git add` needs it), so a worker CAN run
`git update-index --no-skip-worktree OBJECTIVE.md`, stage the projected content,
and commit it — but that puts `OBJECTIVE.md` into `<base>..HEAD`, where the
existing diff-scope verdict refuses the attempt. rc=0 on the update-index is
benign; a SUCCEEDED attempt carrying projection content is not, and is refused.
Pinned by `test_projection_only_change_cannot_mint_a_deliverable` and
`test_worker_cannot_version_the_projection_through_the_index`.

## Verifier / retention / composition invariants (unchanged, re-proven)

- `VERIFIED_SHA == PROMOTED_DURABLE_SHA == RETAINED_REF_TARGET`, and that commit
  is `canonical base + authorized worker delta` — the retained `OBJECTIVE.md`
  is the canonical base blob (asserted in the A+B→C→D E2E).
- two workers with different task-local objectives + disjoint slices compose
  successfully; a genuine overlapping worker-content conflict still refuses.

## Verification

- New `tests/test_wave2_projection_boundary.py` (13 tests) incl. the full
  A+B→C→D **real-bwrap-isolation** E2E, genuine-conflict-still-blocks,
  malicious-projection-edit refusal, mount-level write denial,
  `.git/info` read-only in the sandbox, crash/retry idempotency, and the
  forced-failure invisibility-verification test.
- Updated pinned tests (`test_wave2_shipped_path_integration.py`,
  `test_wave2_shipped_path_adversarial.py`, `test_wave2_retry_and_trusted_base.py`).
- **Full Wave 2 suite: 1688 passed.** All 15 pre-commit gates + registry audit
  green. Format + lint clean.
- **Mutation sweep: 11/11 killed, 0 survivors** — including the KEY mutation
  (re-commit the projection with composition unchanged → the A+B→C→D acceptance
  test fails).

## Files changed

| File | Change |
|---|---|
| `substrate/execution/attempts/worker_claude_cli.py` | `_commit_trusted_projection` → `_mark_projection_execution_context` (skip-worktree/info-exclude, base unmoved, fail-closed invisibility check); scope-contradiction refusal in `run_worker_in_lease` |
| `substrate/execution/attempts/field_task_scope.py` | `.git/info` create-then-locked read-only in `git_readonly_subpaths` |
| `substrate/execution/attempts/verification.py` | comment only (base-ancestry rationale wording) |
| `substrate/execution/attempts/poller.py` | comment only (re-anchor rationale wording) |
| `scripts/wave2_attempt_runner.py` | comment only (trusted_base reporting wording) |
| `tests/test_wave2_projection_boundary.py` | NEW — 13 behavioral tests |
| `tests/test_wave2_shipped_path_integration.py` | projection-invisible assertions; scope-contradiction test |
| `tests/test_wave2_shipped_path_adversarial.py` | index-channel + base-detach vectors reworked |
| `tests/test_wave2_retry_and_trusted_base.py` | trusted_base = canonical un-moved base |

## Quota / state

Field quota unchanged at **41/46 consumed, 5 available** — NO field execution
during this correction cycle. This correction mints a NEW SHA; the qualification
sequence for `69f9fe272` is permanently over (invocation 41 remains consumed).

## Independent review pair (fresh, adversarial)

Two independent reviewers ran the four primary questions against live source
with real-git + real-bwrap experiments.

**Reviewer A** — CLEAN on all four invariants; no Critical/High/Wave-2-blocking.
One LOW (defense-in-depth): the system-owned-path guard compared raw scope
strings while the verifier normalizes, so a scope spelled `./OBJECTIVE.md`
could evade the guard. FIXED: the guard now calls `normalize_allowed_paths`
first (fails closed on an un-normalizable scope). Pinned by
`test_scope_contradiction_guard_normalizes_before_checking`.

**Reviewer B** — correction sound; no Critical, no Wave-2-blocking High. One
MEDIUM: A's normalization fix had a CALLER-LEVEL TEST GAP — the guarding test
asserted the helpers in isolation but never drove `run_worker_in_lease`, so
reverting `_normalized_scope`→`declared_scope` survived the behavioral suite.
FIXED: `test_19` is now parametrized over the canonical AND three non-canonical
spellings (`./OBJECTIVE.md`, `OBJECTIVE.md/`, `app/../OBJECTIVE.md`) driving the
REAL launcher. B's exact mutant now dies (verified directly); the full mutation
sweep is 11/11 with the m6 killer updated to the caller-level test.

Reviewer B additionally noted a PRE-EXISTING, non-blocking `.gitignore`
self-hiding hole that predates this diff (reproduced identically under the old
design). Filed separately in
`data/audits/2026-08-08_wave2_gitignore_selfhide_prereexisting.md` — NOT fixed
here, correctly out of scope.

Answers to the four primary questions after fixes: Q1 NO, Q2 NO, Q3 YES, Q4 YES.

## Post-review requalification

- Full Wave 2 suite green; new `test_wave2_projection_boundary.py` (14 tests)
  + parametrized `test_19` (4 cases).
- All 15 pre-commit gates + registry audit pass; format + lint clean.
- Mutation sweep 11/11 killed, 0 survivors (m6 now killed at the caller level;
  B's exact normalization mutant independently confirmed killed).
