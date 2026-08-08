# Pre-existing defect — worker self-hiding `.gitignore` (NOT introduced by the invocation-41 correction)

**Found**: 2026-08-08 by independent reviewer B during the projection-boundary review.
**Status**: PRE-EXISTING / not a regression of the projection-boundary correction / filed for a separate bounded packet — NOT fixed under the invocation-41 authorization.

## The hole

A worker can write a self-hiding `.gitignore` at the lease root and conceal an
out-of-scope UNTRACKED file from all three channels the diff-scope verifier
reads:

```bash
mkdir -p secret; echo STOLEN > secret/key.txt
printf '/secret/\n/.gitignore\n' > .gitignore
```

Driven through the real launcher under bwrap: `secret/key.txt` is present on
disk with content `STOLEN`, and `_diff_scope_verdict` returns `ok=True,
outside=[]`.

## Why it is reachable

`readonly_binds_for_scope` (`substrate/execution/attempts/field_task_scope.py`,
the top-level-entry lock) only re-binds **existing** top-level entries
read-only. No `.gitignore` exists in the fixture at lease-prep time, so the
worker can create one, and `git ls-files --others --exclude-standard`
(`verification.py:315`) honours it — hiding both the ignored path and the
`.gitignore` itself.

## Why it is NOT this correction's regression

Reviewer B reproduced it **identically under the old commit-the-projection
design** (same invisibility, same clean verdict). `--exclude-standard` predates
the change (confirmed via `git show HEAD:substrate/execution/attempts/verification.py`).
The invocation-41 correction neither introduced nor widened this path.

## Candidate fix (for a future packet, not applied here)

The independent-diff scan should not honour worker-authored ignore files.
Options: run `ls-files --others` WITHOUT `--exclude-standard` for the scope
verdict (count every untracked path against scope, honouring only the
control-plane's own `.git/info/exclude`), or explicitly refuse a worker-authored
`.gitignore`/`.git/info/exclude` change. Either is a `verification.py` change
with its own review + regression qualification — out of scope for the
projection-boundary correction, which must remain minimal.
