---
description: "Commit staged changes, push to origin, and open a PR. Boris uses this daily. Run after any completed build."
---

Commit, push, and open a PR.

!`git status --short`
!`git diff --cached --stat`

Based on the staged changes above:
1. Write a commit message following the format:
   type(scope): description

   Types: feat, fix, refactor, docs, test, chore

2. Run: git commit -m "[message]"
3. Run: git push origin [current-branch]
4. If on a feature branch: open a PR with
   title matching the commit message
   gh pr create --title "[message]" \
     --body "[what changed and why]"

Verify: git log --oneline -3
