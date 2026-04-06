---
name: git
description: "Use when committing code, pushing to GitHub, managing branches, resolving merge conflicts, reviewing history, or configuring git hooks in the EOS codebase."
allowed-tools: "Read, Bash"
version: 1.0
source_url: "https://git-scm.com/docs"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "2.43.0"
sdk_version: "git 2.43.0"
speed_category: fast
trigger: both
effort: low
context: fork
---

# Tool: Git

## What This Tool Does

Git is the distributed version control system that tracks every change in the EOS
codebase at `/opt/OS`. It provides atomic commits, branching, merging, history
traversal, and remote synchronization with GitHub.

Core capabilities used by EOS:
- **Commit history** -- every change to the AI intelligence layer, services,
  skills, and configuration is tracked with lowercase imperative messages
- **Main-only workflow** -- solo founder phase commits directly to main;
  feature branches reserved for experimental or risky changes
- **GitHub sync** -- origin at `https://github.com/antonyfmunoz/OS.git`,
  pulled to VPS, pushed from VPS or local VSCode
- **Claude Code integration** -- CC hooks run pre/post tool use, audit
  file changes, and auto-format Python on write via ruff
- **Deploy trigger** -- `git push` is the sync mechanism between local
  dev (Windows VSCode) and VPS (production tmux)

## EOS Integration

### Workflow: main-only (solo founder phase)
```
Local edit (VSCode Windows)
  -> git commit -m "type: description"
  -> git push origin main
  -> VPS: git pull origin main
  -> docker restart [container] (if service changed)
```

Feature branches exist (`dev`, `feature/ea-system`) but are used only for
experimental or risky changes. Day-to-day work goes directly to main.

### Commit message convention
From the actual git log:
```
fix: cc_sdk concurrent call handling
feat: tool mastery -- apify, instagram, notion, gmail, calendly complete
refactor: production reorganization -- structure, skills, templates, fixes
slim CLAUDE.md context -- remove @-refs and move rarely-needed content to docs/
pass1: fix foundation -- 5 critical fixes
```

Pattern: `type: lowercase imperative description`
Types observed: `feat`, `fix`, `refactor`, `docs`, `chore`, `pass1-4` (multi-step builds)
Optional scope: `type(scope): description` per commit-push-pr skill

### Claude Code hooks that interact with git
- **PostToolUse (Edit|Write)** -- runs `ruff format` on Python files automatically
- **PostToolUse (Edit|Write)** -- logs file path and timestamp to audit.log
- **PostToolUse (Edit|Write|Create)** -- verifies `import eos_ai` still works
- **commit-push-pr command** -- `/commit-push-pr` stages, commits, pushes, and
  optionally opens a PR via `gh`

### Key git-related files
- `.gitignore` -- excludes `.env`, `__pycache__/`, `logs/`, `*.session`,
  `instagram_session/`, `CLAUDE.local.md`, `.obsidian/workspace.json`
- `.claude/settings.json` -- CC hooks config, git permissions in allow list
- `install.sh` -- clones repo on fresh VPS setup

### Permission model in Claude Code
```json
"allow": [
  "Bash(git *)"
]
```
All git commands are pre-approved. No permission prompt needed.

## Authentication

### GitHub HTTPS (current)
- Remote: `https://github.com/antonyfmunoz/OS.git`
- Auth: GitHub credential helper or personal access token (PAT)
- PAT stored in git credential cache, not in `.env`
- User: `antonyfmunoz` / email: `antonyfm@empyreanstudios.co`

### GitHub SSH (alternative)
- Generate: `ssh-keygen -t ed25519 -C "antonyfm@empyreanstudios.co"`
- Add public key to GitHub Settings > SSH Keys
- Switch remote: `git remote set-url origin git@github.com:antonyfmunoz/OS.git`
- Verify: `ssh -T git@github.com`

### GitHub CLI (gh)
- Used by `/commit-push-pr` for PR creation
- Auth: `gh auth login` with PAT or browser flow
- Verify: `gh auth status`

## Quick Reference

### Commit and push (daily workflow)
```bash
git add <specific-files>
git commit -m "fix: description of what changed"
git push origin main
```

### Check status
```bash
git status              # working tree status
git status --short      # compact view
git diff                # unstaged changes
git diff --cached       # staged changes
git diff --cached --stat  # staged file summary
```

### View history
```bash
git log --oneline -20            # recent commits
git log --oneline --all --graph  # branch topology
git log -p -1                    # full diff of last commit
git log --author="antonyfmunoz" --since="2026-04-01"  # filtered
```

### Branch operations (rare in EOS)
```bash
git branch                          # list local branches
git branch -a                       # list all including remote
git checkout -b feature/name        # create and switch
git checkout main                   # switch back
git merge feature/name              # merge to current
git branch -d feature/name          # delete after merge
```

### Worktree (parallel work)
```bash
git worktree add ../OS-experiment feature/experiment  # new worktree
git worktree list                                      # list worktrees
git worktree remove ../OS-experiment                   # clean up
```
Worktrees let you have multiple checked-out branches simultaneously
without stashing. Useful for hotfixes while mid-build.

### Stash
```bash
git stash                    # save working changes
git stash list               # list stashes
git stash pop                # apply and remove
git stash apply stash@{0}   # apply without removing
git stash drop stash@{0}    # discard a stash
```

### Reset and recover
```bash
git reset HEAD <file>        # unstage a file
git checkout -- <file>       # discard changes to file (DESTRUCTIVE)
git reset --soft HEAD~1      # undo last commit, keep changes staged
git reflog                   # find lost commits
git cherry-pick <hash>       # apply specific commit
```

### GitHub CLI (PR workflow)
```bash
gh pr create --title "feat: description" --body "what and why"
gh pr list
gh pr view <number>
gh pr merge <number>
```

## Conceptual Model

```
Working Directory          Staging Area (Index)         Local Repo (.git)
     |                          |                            |
     |--- git add ------------>|                            |
     |                          |--- git commit ----------->|
     |                          |                            |
     |<-- git checkout --------|<-- git reset --------------|
     |                          |                            |
     |                          |                    Remote (GitHub)
     |                          |                            |
     |                          |            git push ------>|
     |                          |            git pull <------|
     |                          |            git fetch <-----|

EOS Git Flow (main-only):
  edit -> stage -> commit -> push -> (VPS pull / auto-deploy)

EOS Feature Branch Flow (rare):
  checkout -b feature/x -> edit -> commit -> push -> PR -> merge -> delete branch
```

See references/best_practices.md for full technical reference.

## Gotchas

### Never use git add -A or git add . in EOS
The repo contains `.env` files, session JSONs, and local override files.
Broad staging risks committing secrets. Always `git add <specific-files>`.
The `.gitignore` catches most cases but is not a security guarantee.

### CLAUDE.local.md is gitignored
`CLAUDE.local.md` contains personal preferences and is in `.gitignore`.
Never create it as a tracked file. If it appears in `git status`, the
gitignore pattern `*.local` should catch it -- verify the pattern exists.

### git push requires credential on VPS
The VPS uses HTTPS remote. If credential cache expires, push fails silently
or prompts for auth in a non-interactive tmux session. Use `git config
credential.helper store` or switch to SSH to avoid interactive auth prompts.

### Claude Code hooks run on every file write
Every `Edit` or `Write` triggers ruff format + import check + audit log.
This means git diffs may show formatting changes you did not make manually.
This is expected behavior -- ruff format is authoritative.

### Never amend when a pre-commit hook fails
If a commit fails due to hooks, the commit did NOT happen. Running
`git commit --amend` would modify the PREVIOUS commit, not retry the
failed one. Always create a NEW commit after fixing the issue.

### Feature branches exist but are stale
`dev` and `feature/ea-system` branches exist in the repo. They are not
actively used in the current solo-founder main-only workflow. Do not
merge them without checking divergence first: `git log main..dev --oneline`.

### Destructive commands need confirmation
Never run `git reset --hard`, `git push --force`, `git clean -f`, or
`git checkout .` without explicit human confirmation. These destroy
uncommitted work with no recovery path.
