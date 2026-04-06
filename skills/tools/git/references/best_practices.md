# Git -- Creator-Level Best Practices
Source: https://git-scm.com/docs
API Version: Git 2.43.0 (VPS), GitHub REST API v3
SDK Version: git CLI 2.43.0, gh CLI (GitHub CLI)
Last Researched: 2026-04-06

---

# Tier 1 -- Technical Mastery

## Authentication

### SSH key auth (recommended for VPS)
- Generate: `ssh-keygen -t ed25519 -C "email@example.com"`
- Add to agent: `eval "$(ssh-agent -s)" && ssh-add ~/.ssh/id_ed25519`
- Add public key to GitHub: Settings > SSH and GPG keys > New SSH key
- Test: `ssh -T git@github.com` -- should say "Hi username!"
- Remote format: `git@github.com:user/repo.git`

### HTTPS with PAT (current EOS setup)
- Generate at GitHub: Settings > Developer settings > Personal access tokens > Fine-grained tokens
- Required permissions: Contents (read/write), Pull requests (read/write), Metadata (read)
- Store: `git config --global credential.helper store` (plaintext in `~/.git-credentials`)
- Better: `git config --global credential.helper cache --timeout=86400` (24h memory cache)
- Remote format: `https://github.com/user/repo.git`
- Token does NOT go in `.env` -- it lives in git's credential store

### GitHub CLI auth
- `gh auth login` -- interactive setup, stores token in `~/.config/gh/hosts.yml`
- `gh auth status` -- verify current auth
- Scopes needed: `repo`, `read:org`, `workflow` (for PR creation and CI)
- `gh auth refresh -s repo,read:org` -- add missing scopes

### EOS-specific auth context
- VPS remote: `https://github.com/antonyfmunoz/OS.git` (HTTPS)
- User: `antonyfmunoz`, email: `antonyfm@empyreanstudios.co`
- Config is repo-local (`git config --list --local`)
- Multiple devices (VPS, Windows, iPad, iPhone) all push to same remote
- Tailscale connects devices but git goes through GitHub, not peer-to-peer

## Core Operations with Exact Signatures

### Staging
```bash
git add <pathspec>...          # stage specific files
git add -p <file>              # interactive hunk staging
git add -u                     # stage all tracked modified files (no new files)
git reset HEAD <file>          # unstage a file
git restore --staged <file>    # unstage (modern syntax, git 2.23+)
```

### Committing
```bash
git commit -m "message"                    # commit with inline message
git commit -m "line1" -m "line2"           # multi-paragraph
git commit --amend -m "new message"        # rewrite last commit (DESTRUCTIVE to history)
git commit --amend --no-edit               # add staged changes to last commit
git commit --allow-empty -m "trigger CI"   # empty commit
```

### Remote sync
```bash
git push origin <branch>           # push branch to remote
git push -u origin <branch>        # push and set upstream tracking
git pull origin <branch>           # fetch + merge
git pull --rebase origin <branch>  # fetch + rebase (cleaner history)
git fetch origin                   # fetch without merge
git fetch --prune                  # fetch and remove deleted remote branches
```

### Branching
```bash
git branch <name>                    # create branch
git branch -d <name>                 # delete (only if merged)
git branch -D <name>                 # force delete (DESTRUCTIVE)
git checkout <branch>                # switch branch
git checkout -b <name>               # create and switch
git switch <branch>                  # switch (modern syntax, git 2.23+)
git switch -c <name>                 # create and switch (modern)
```

### Diffing
```bash
git diff                       # working tree vs index
git diff --cached               # index vs HEAD (staged changes)
git diff HEAD                   # working tree vs HEAD (all changes)
git diff <branch1>..<branch2>  # commits in branch2 not in branch1
git diff <branch1>...<branch2> # changes since branches diverged
git diff --stat                 # summary: files changed, insertions, deletions
git diff --name-only            # just filenames
```

### History
```bash
git log --oneline -N               # last N commits, compact
git log --oneline --all --graph    # full topology visualization
git log -p -1                      # full patch of last commit
git log --since="2 weeks ago"      # time-based filter
git log --author="name"            # author filter
git log -- <file>                  # history of specific file
git log --follow -- <file>         # history including renames
git shortlog -sn                   # commit count by author
```

### Worktree
```bash
git worktree add <path> <branch>   # create worktree for branch
git worktree add <path> -b <new>   # create worktree with new branch
git worktree list                  # list all worktrees
git worktree remove <path>         # remove worktree
git worktree prune                 # clean up stale entries
```

### Stash
```bash
git stash                          # stash working changes
git stash push -m "description"    # stash with message
git stash list                     # list stashes
git stash pop                      # apply latest and remove
git stash apply stash@{N}          # apply Nth stash, keep it
git stash drop stash@{N}           # discard Nth stash
git stash show -p stash@{N}        # show stash diff
git stash branch <name> stash@{N}  # create branch from stash
```

## Pagination Patterns

Git log output is paginated through the system pager (usually `less`).
For programmatic use:
```bash
git log --oneline -N                  # limit to N entries
git log --oneline --skip=20 -10       # skip 20, show next 10
git log --format="%H %s" | head -100  # pipe to head for exact control
git --no-pager log --oneline -50      # disable pager entirely
```

GitHub API pagination (via gh):
```bash
gh api repos/owner/repo/commits --paginate  # auto-paginate all pages
gh api repos/owner/repo/pulls?per_page=100  # max 100 per page
```

GitHub API uses Link headers with `rel="next"` for cursor-based pagination.
The `gh` CLI handles this transparently with `--paginate`.

## Rate Limits

### Git operations: no rate limit
Git itself has no rate limiting. Push/pull/fetch are limited only by
network bandwidth and server capacity.

### GitHub API rate limits
- Authenticated: 5,000 requests/hour
- Unauthenticated: 60 requests/hour
- Search API: 30 requests/minute (authenticated)
- GraphQL API: 5,000 points/hour
- Check limits: `gh api rate_limit`
- Response headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`

### GitHub push limits
- Max push size: 2 GB per push
- Max file size: 100 MB (hard limit), warning at 50 MB
- Files over 100 MB require Git LFS
- Max refs per push: 5,000

### Secondary rate limits (abuse detection)
GitHub has undocumented secondary limits for rapid API calls. If hit:
- 403 response with `retry-after` header
- Exponential backoff: wait `retry-after` seconds, then 2x on each retry
- Creating content (PRs, issues, comments) has stricter limits than reading

## Error Codes and Recovery

### Git exit codes
- 0: success
- 1: generic error (merge conflict, diff found differences, etc.)
- 128: fatal error (bad repo, permission denied, corrupt objects)
- 129: usage error (bad arguments)

### Common errors and fixes
| Error | Cause | Fix |
|-------|-------|-----|
| `fatal: not a git repository` | Wrong directory | `cd /opt/OS` |
| `error: failed to push some refs` | Remote has new commits | `git pull --rebase origin main && git push` |
| `CONFLICT (content)` | Merge conflict | Edit file, `git add`, `git commit` |
| `fatal: refusing to merge unrelated histories` | Diverged repos | `git pull --allow-unrelated-histories` (rare) |
| `error: Your local changes would be overwritten` | Uncommitted changes | `git stash && git pull && git stash pop` |
| `remote: Permission denied` | Auth expired | `gh auth login` or refresh PAT |
| `fatal: bad object HEAD` | Corrupt repo | `git fsck --full`, or re-clone |
| `error: pathspec did not match` | File doesn't exist | Check spelling, check branch |

### Merge conflict resolution
```bash
# 1. See conflicted files
git status
# 2. Edit files — resolve <<<<<<< / ======= / >>>>>>> markers
# 3. Stage resolved files
git add <resolved-file>
# 4. Complete the merge
git commit
```

### Recovering lost commits
```bash
git reflog                    # shows HEAD movements for 90 days
git checkout <hash>           # detached HEAD to inspect
git cherry-pick <hash>        # apply lost commit to current branch
git branch recovery <hash>    # create branch at lost commit
```

## SDK Idioms

Git is a CLI tool, not an SDK. The "idiomatic" patterns are shell commands.

### Python subprocess pattern (when needed)
```python
import subprocess

def git_cmd(*args: str) -> str:
    """Run a git command and return stdout."""
    result = subprocess.run(
        ["git", *args],
        capture_output=True, text=True,
        cwd="/opt/OS"
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {args[0]} failed: {result.stderr}")
    return result.stdout.strip()

# Usage
status = git_cmd("status", "--short")
git_cmd("add", "eos_ai/model_router.py")
git_cmd("commit", "-m", "fix: routing fallback")
```

### GitPython (not used in EOS, but available)
```python
# pip install gitpython
from git import Repo
repo = Repo("/opt/OS")
repo.index.add(["file.py"])
repo.index.commit("fix: description")
origin = repo.remote("origin")
origin.push()
```
EOS does not use GitPython -- all git operations are via CLI or Claude Code.

### gh CLI from Python
```python
import subprocess
result = subprocess.run(
    ["gh", "pr", "create", "--title", "feat: thing", "--body", "details"],
    capture_output=True, text=True, cwd="/opt/OS"
)
```

## Anti-Patterns

### 1. Using `git add .` or `git add -A`
**Wrong:**
```bash
git add .
git commit -m "update"
```
**Right:**
```bash
git add eos_ai/model_router.py services/discord_bot.py
git commit -m "fix: model router fallback chain"
```
Broad staging risks committing `.env`, session files, or large binaries.

### 2. Vague commit messages
**Wrong:**
```bash
git commit -m "updates"
git commit -m "fix stuff"
git commit -m "WIP"
```
**Right:**
```bash
git commit -m "fix: cc_sdk concurrent call handling"
git commit -m "feat: tool mastery -- docker, ollama, playwright complete"
```
Every commit should explain what and why in lowercase imperative.

### 3. Using `--force` push without reason
**Wrong:**
```bash
git push --force origin main
```
**Right:**
```bash
# Only after explicit discussion about rewriting history
git push --force-with-lease origin feature/branch
```
`--force` on main destroys remote history. `--force-with-lease` at least
checks that no one else pushed since your last fetch.

### 4. Amending after hook failure
**Wrong:**
```bash
git commit -m "feat: thing"     # hook fails
git commit --amend -m "feat: thing"  # AMENDS PREVIOUS COMMIT
```
**Right:**
```bash
git commit -m "feat: thing"     # hook fails
# fix the issue
git add <fixed-files>
git commit -m "feat: thing"     # NEW commit
```

### 5. Committing large files
**Wrong:**
```bash
git add model-weights.bin  # 500MB file
```
**Right:**
```bash
# Add to .gitignore, or use Git LFS
echo "*.bin" >> .gitignore
git lfs track "*.bin"
```
GitHub hard-blocks files over 100MB. Even 10MB files bloat the repo permanently.

### 6. Not pulling before pushing
**Wrong:**
```bash
# Edit on VPS, push
# Edit on Windows, push --> REJECTED
```
**Right:**
```bash
git pull --rebase origin main
# then push
```
With multiple devices (VPS, Windows, iPad), always pull before editing.

### 7. Interactive flags in non-interactive contexts
**Wrong:**
```bash
git rebase -i HEAD~3    # requires editor -- fails in Claude Code
git add -i              # requires stdin -- fails in automation
```
**Right:**
```bash
git rebase --onto main HEAD~3  # non-interactive rebase
git add <specific-files>        # explicit staging
```

## Data Model

### Git object types
- **Blob** -- file contents (no filename, just content hash)
- **Tree** -- directory listing (maps names to blob/tree hashes)
- **Commit** -- snapshot pointer (tree hash + parent hash + message + author + timestamp)
- **Tag** -- named pointer to a commit (annotated tags also store tagger + message)

### Reference types
- **HEAD** -- pointer to current branch (or detached commit)
- **Branch** -- pointer to latest commit on a line of development
- **Remote tracking branch** -- `origin/main` mirrors the remote state
- **Tag** -- immutable pointer to a specific commit
- **Stash** -- special ref at `refs/stash`, stored as commit chain

### EOS repo structure
```
.git/
  HEAD              -> refs/heads/main
  refs/heads/
    main            -> d0c6ffb (latest commit)
    dev             -> (stale, diverged)
    feature/ea-system -> (stale)
  refs/remotes/origin/
    HEAD            -> refs/remotes/origin/main
    main            -> (last fetched state)
  objects/          -> all blobs, trees, commits (content-addressed)
  hooks/            -> sample hooks only (no active custom hooks)
  config            -> repo-local git config
```

### Commit anatomy
```
commit d0c6ffb
Author: antonyfmunoz <antonyfm@empyreanstudios.co>
Date:   [timestamp]

    fix: cc_sdk concurrent call handling

Parent: 3b0a87a
Tree:   [hash] -> snapshot of entire repo at this point
```

## Webhooks and Events

### Git hooks (local, in .git/hooks/)
Git hooks are scripts that run at specific points in the git workflow.
EOS currently uses **no custom git hooks** in `.git/hooks/` -- only sample files exist.

Available hooks:
| Hook | Trigger | Use case |
|------|---------|----------|
| `pre-commit` | Before commit created | Lint, format, test |
| `commit-msg` | After message written | Validate message format |
| `pre-push` | Before push to remote | Run tests, block force push |
| `post-commit` | After commit created | Notifications |
| `post-merge` | After merge/pull | Install deps, rebuild |
| `pre-rebase` | Before rebase starts | Warn about shared branches |

### Claude Code hooks (substitute for git hooks)
EOS uses Claude Code hooks instead of git hooks for the AI development workflow:
- **PostToolUse (Edit|Write)** -- auto-formats Python via ruff
- **PostToolUse (Edit|Write|Create)** -- verifies `import eos_ai` integrity
- **PostToolUse (Edit|Write)** -- audit logs every file change
- **Stop hook** -- runs `wiki_stop_hook.py` on session end

These serve the same purpose as pre-commit hooks but operate at the
Claude Code tool level rather than the git commit level.

### GitHub webhooks (remote)
GitHub can send POST requests to a URL on events:
- `push` -- any push to the repo
- `pull_request` -- PR opened, closed, merged
- `issues` -- issue created, edited, closed
- Configure: GitHub repo > Settings > Webhooks
- EOS currently has no GitHub webhooks configured -- deploy is manual
  (`git pull` on VPS)

## Limits

### Repository limits
- Max repo size: 5 GB recommended (GitHub warns at 1 GB, blocks push at ~5 GB)
- Max file size: 100 MB hard limit (GitHub), 50 MB warning
- Max files per commit: no hard limit, but push times degrade past 10K files
- Pack file limit: ~2 GB per packfile on 32-bit systems

### Commit message limits
- Subject line: no hard limit, convention is 50 chars (72 max)
- Body: no hard limit, convention is 72-char line wrap
- GitHub truncates subject at 72 chars in UI

### Branch/tag limits
- No hard limit on number of branches
- Branch name: max 255 bytes, no spaces, no `..`, no trailing `.lock`
- Tag name: same restrictions as branch names

### GitHub API limits
- PR body: 65,536 characters max
- Issue body: 65,536 characters max
- Comment body: 65,536 characters max
- Labels per issue: 100
- Assignees per issue: 10
- Files per PR diff view: 3,000 (larger PRs don't render in UI)

### Git LFS limits (if used)
- GitHub free: 1 GB storage, 1 GB bandwidth/month
- Data packs: $5/month for 50 GB storage + 50 GB bandwidth

## Cost Model

### Git itself: free
Git is open source (GPLv2). No cost for any local operation.

### GitHub (current tier)
- Free plan: unlimited public and private repos
- Free plan limits: 500 MB packages storage, 2,000 CI minutes/month
- Actions: not currently used by EOS
- GitHub Pro: $4/month (more CI minutes, required reviewers)
- GitHub Team: $4/user/month

### EOS cost: $0/month
Currently using GitHub Free tier. No GitHub Actions, no LFS, no paid features.
All deployment is manual (git pull on VPS). CI/CD would add cost only if
GitHub Actions or a paid CI service is added.

### Cost optimization
- Keep repo under 1 GB to stay comfortable on free tier
- Don't commit large binaries (models, datasets, media) -- use external storage
- If CI is added: cache dependencies to minimize minutes

## Version Pinning

### Git version
- VPS: git 2.43.0 (Ubuntu 24.04 default)
- Pin concern: low. Git has exceptional backward compatibility.
  Commands from git 1.x still work in 2.x.
- New features to use: `git switch`/`git restore` (2.23+),
  `git maintenance` (2.29+), `--force-with-lease` (1.8.5+)

### GitHub API version
- REST API: v3 (via Accept header `application/vnd.github.v3+json`)
- GraphQL API: no versioning (schema evolution)
- gh CLI handles versioning transparently

### .gitignore syntax: stable
No versioning concern. Syntax has been stable since git 1.x.

### Deprecation watch
- `git checkout` is being soft-deprecated in favor of `git switch` (branch)
  and `git restore` (files). Both work. `checkout` will not be removed.
- `git stash save` deprecated in favor of `git stash push` (git 2.16+)
- SHA-1 to SHA-256 transition is in progress but years away from default

---

# Tier 2 -- Creator Intelligence

## Design Intent and Tradeoffs

### Why git was built
Linus Torvalds created git in 2005 to replace BitKeeper for Linux kernel
development. The design priorities, in order:
1. **Distributed** -- every clone is a full repo, no central server required
2. **Fast** -- branching and merging are O(1) pointer operations
3. **Data integrity** -- SHA-1 content addressing means corruption is detectable
4. **Non-linear development** -- thousands of parallel branches is a first-class use case

### Key design tradeoffs
- **Complexity over simplicity** -- git exposes the full DAG model rather than
  hiding it. This makes it powerful but has a steep learning curve.
- **Content-addressed over name-addressed** -- files are tracked by content hash,
  not by name. Renames are detected heuristically, not tracked explicitly.
- **Immutable history over mutable history** -- commits are immutable objects.
  "Rewriting history" actually creates new commits and moves pointers.
- **Speed over disk space** -- git stores full snapshots (compressed), not
  incremental diffs. This makes checkout instant but repos grow with history.
- **Local-first over server-first** -- every operation except push/pull/fetch
  is local and instant. No network round-trip for status, log, diff, commit.

### What git is NOT
- Not a backup system (though it functions as one)
- Not a deployment tool (though EOS uses push/pull as deploy trigger)
- Not a file sync service (use rsync/syncthing for that)
- Not a database (don't store structured data that changes frequently)

## Problem-Solution Map and Hidden Capabilities

### Worktrees for parallel development
Most developers don't know about `git worktree`. It lets you check out
multiple branches simultaneously in different directories:
```bash
git worktree add /opt/OS-hotfix main    # hotfix while mid-feature
git worktree add /opt/OS-test feature/x  # test branch without switching
```
For EOS: work on a risky feature in a worktree while main stays clean
for production.

### Bisect for finding regressions
```bash
git bisect start
git bisect bad HEAD           # current commit is broken
git bisect good abc1234       # this commit was working
# git checks out midpoint, you test, mark good/bad
git bisect good               # or git bisect bad
# repeat until guilty commit found
git bisect reset
```
Can be automated: `git bisect run python3 -c "import eos_ai"` finds the
exact commit that broke imports.

### Reflog as safety net
`git reflog` records every HEAD movement for 90 days. Even after `reset --hard`,
the old commits still exist and can be recovered:
```bash
git reflog
# Find the hash before the mistake
git reset --hard <hash>       # or cherry-pick, or create branch
```

### Partial staging with -p
```bash
git add -p eos_ai/model_router.py
```
Lets you stage individual hunks within a file. Useful for splitting
a large change into logical commits.

### Commit message templates
```bash
git config commit.template ~/.gitmessage
```
Create a template that enforces the EOS format with type prefixes.

### git maintenance for large repos
```bash
git maintenance start       # enables background optimization
git maintenance run --auto  # manual trigger
```
Runs garbage collection, prefetch, and pack optimization on schedule.

### Sparse checkout for monorepos
```bash
git sparse-checkout init --cone
git sparse-checkout set eos_ai services
```
Only materializes specified directories. Not needed for EOS (repo is small)
but useful if the repo grows significantly.

## Operational Behavior and Edge Cases

### Line ending normalization
- Linux (VPS): LF line endings
- Windows (VSCode): CRLF by default
- Fix: `git config --global core.autocrlf input` on all machines
- Or add `.gitattributes`: `* text=auto eol=lf`
- EOS has no `.gitattributes` -- relies on per-machine config
- Edge case: Python files with mixed endings can cause syntax errors

### Merge conflicts in JSON files
Session state files (`session_state.json`, `notion_sync_state.json`) are
modified by automation. If two devices edit simultaneously:
- JSON merge conflicts produce invalid JSON
- Fix: take one side entirely (`git checkout --ours/--theirs <file>`)
- Prevention: these files should be in `.gitignore` (most already are)

### Empty directories
Git does not track empty directories. If a directory must exist:
- Add a `.gitkeep` file inside it
- Or document that the directory is created at runtime

### File permission changes
Git tracks executable bit (`chmod +x`). On Windows, this can cause
spurious permission changes. Fix: `git config core.fileMode false`

### Detached HEAD state
Checking out a commit hash (not a branch) puts you in detached HEAD:
```bash
git checkout abc1234        # detached HEAD
git switch -c recovery      # create branch to save work
```
Any commits made in detached HEAD are orphaned if you switch away
without creating a branch.

### Rebase vs merge in EOS
EOS uses merge (default `git pull` behavior). Rebase creates cleaner
linear history but rewrites commits. For solo developer on main:
- `git pull --rebase` is safe and preferred (no merge commits)
- Never rebase commits that have been pushed to shared branches

### Large file detection
```bash
git rev-list --objects --all | \
  git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' | \
  awk '/^blob/ {print $3, $4}' | sort -rn | head -20
```
Finds the largest files in repo history. Important for keeping repo lean.

## Ecosystem Position and Composition

### Git + GitHub (current)
- Git: local version control
- GitHub: remote hosting, PR workflow, issue tracking
- gh CLI: GitHub operations from terminal
- Together: complete development workflow

### Git + CI/CD (future)
- GitHub Actions: would trigger on push to main
- Natural workflow: push -> CI runs tests -> deploy if green
- EOS currently deploys manually (git pull on VPS)

### Git + Docker (current)
- Python files are bind-mounted into Docker containers
- Code changes are live without rebuild: `docker restart os-discord`
- Dockerfile only needs rebuild for dependency changes

### Git + Claude Code (current)
- Claude Code reads/writes files -> PostToolUse hooks run
- `/commit-push-pr` command automates the git workflow
- Claude Code has full `Bash(git *)` permissions
- Claude Code hooks replace traditional git hooks for AI-assisted development

### What NOT to pair with git
- Don't use git for database backups (use pg_dump)
- Don't use git for secrets management (use .env + vault)
- Don't use git for large media files (use object storage)
- Don't use git as a message queue (use actual queues)

## Trajectory and Evolution

### Git development (2024-2026)
- SHA-256 support: experimental, not default. Transition will take years.
- `git switch` / `git restore`: gaining adoption, replacing `checkout`
- Scalar (Microsoft): performance optimizations for large repos, some merged upstream
- Partial clone / sparse checkout: increasingly important for monorepos
- `git maintenance`: background housekeeping, stable since 2.29

### GitHub evolution
- GitHub Copilot: AI in the editor, not directly related to git
- GitHub Actions: increasingly central to CI/CD
- GitHub Codespaces: cloud dev environments (alternative to VPS + SSH)
- Fine-grained PATs: replacing classic tokens (more secure, scoped)

### Deprecation watch
- Classic PATs: GitHub encouraging migration to fine-grained tokens
- `git checkout` dual purpose: slowly being replaced by `switch`/`restore`
- `git stash save`: deprecated, use `git stash push`
- RSA SSH keys: GitHub dropped RSA support below 2048 bits

### What to adopt early
- Fine-grained PATs (more secure than classic tokens)
- `git maintenance start` for automated repo optimization
- `--force-with-lease` instead of `--force` (always)
- Signed commits with SSH keys (`git config gpg.format ssh`)

## Conceptual Model and Solution Recipes

### Mental model: git as a DAG of snapshots
Every commit is a snapshot of the entire repo (not a diff). Branches are
just movable pointers to commits. Merging creates a commit with two parents.
The entire history is a directed acyclic graph (DAG).

```
A -- B -- C -- D (main)
      \       /
       E -- F (feature)
```

Understanding this model makes every git operation intuitive:
- `branch` = create pointer
- `commit` = create snapshot, move pointer forward
- `merge` = create snapshot with two parents
- `rebase` = replay commits on new base (creates NEW commits)
- `reset` = move pointer backward
- `cherry-pick` = copy a single snapshot to current branch

### Recipe 1: Daily EOS development cycle
```bash
# Start of session (VPS)
cd /opt/OS
git status                              # check state
git pull --rebase origin main           # sync with any remote changes

# Work
# ... edit files via Claude Code ...

# Commit (after build is verified)
git add eos_ai/model_router.py services/discord_bot.py
git commit -m "fix: model router fallback chain"
git push origin main

# Verify
git log --oneline -3
```

### Recipe 2: Experimental feature (safe isolation)
```bash
# Create feature branch
git checkout -b feature/new-agent
# ... build and test ...
git add <files>
git commit -m "feat: new agent architecture"
git push -u origin feature/new-agent

# When ready to merge
git checkout main
git pull origin main
git merge feature/new-agent
git push origin main
git branch -d feature/new-agent
git push origin --delete feature/new-agent
```

### Recipe 3: Emergency hotfix while mid-build
```bash
# Option A: stash
git stash push -m "mid-build WIP"
# fix the issue
git add <hotfix-files>
git commit -m "fix: critical issue"
git push origin main
git stash pop

# Option B: worktree (cleaner)
git worktree add /opt/OS-hotfix main
cd /opt/OS-hotfix
# fix the issue
git add <hotfix-files>
git commit -m "fix: critical issue"
git push origin main
cd /opt/OS
git worktree remove /opt/OS-hotfix
git pull --rebase origin main    # get the hotfix
```

### Recipe 4: Undo a bad commit (already pushed)
```bash
# Revert creates a NEW commit that undoes the bad one
git revert <bad-commit-hash>
git push origin main
# History preserved, change undone safely
```

### Recipe 5: Find what broke and when
```bash
# Automated bisect
git bisect start
git bisect bad HEAD
git bisect good <last-known-good-hash>
git bisect run python3 -c "import sys; sys.path.insert(0,'/opt/OS'); import eos_ai"
# Git finds the exact commit that broke imports
git bisect reset
```

## Industry Expert and Cutting-Edge Usage

### Trunk-based development (what EOS does)
Google, Facebook, and most high-velocity teams use trunk-based development:
commit directly to main, use feature flags instead of long-lived branches.
This is exactly the EOS pattern. Benefits:
- No merge conflicts from stale branches
- Every commit is a deployable state
- Faster feedback loops

### Git + AI coding assistants
The emerging pattern (which EOS implements via Claude Code):
- AI writes code -> hooks validate -> human reviews -> commit
- Commit messages written by AI from diff analysis
- PR descriptions auto-generated from commit history
- Import verification as automated gate (EOS PostToolUse hook)

### Signed commits with SSH keys
```bash
git config gpg.format ssh
git config user.signingkey ~/.ssh/id_ed25519.pub
git config commit.gpgsign true
```
Uses existing SSH key for commit signing. No GPG needed.
GitHub shows "Verified" badge. Increasingly expected for professional repos.

### Git absorb (advanced fixup)
```bash
# pip install git-absorb or cargo install git-absorb
git absorb --and-rebase
```
Automatically assigns fixup commits to the right parent commit and
rebases. Eliminates manual `fixup!` and interactive rebase.

### Conventional Commits for automation
Format: `type(scope): description`
Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`
Tools like `semantic-release` can auto-version based on commit types:
- `feat` -> minor version bump
- `fix` -> patch version bump
- `BREAKING CHANGE` in footer -> major version bump
EOS partially follows this with `feat:`, `fix:`, `refactor:` prefixes.

### Pre-commit framework
```bash
pip install pre-commit
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.0
    hooks:
      - id: ruff-format
      - id: ruff
```
EOS achieves this via Claude Code PostToolUse hooks instead, which is
more integrated with the AI development workflow.

### Git worktrees for CI-like local testing
```bash
git worktree add /tmp/test-build main
cd /tmp/test-build
python3 -c "import sys; sys.path.insert(0,'.'); import eos_ai"
# Test passes -> safe to push
cd /opt/OS
git worktree remove /tmp/test-build
```
Tests against a clean checkout without polluting working directory.

---

## EOS Usage Patterns

### Devices and sync flow
```
Windows (VSCode) --push--> GitHub --pull--> VPS (tmux/Claude Code)
iPad (code-server) --push--> GitHub --pull--> VPS
iPhone (Termius) --> SSH to VPS --> direct git operations
```

### Files that should never be committed
- `eos_ai/.env` -- API keys and secrets
- `services/.env` -- bot tokens
- `*.session` -- Instagram/Telegram sessions
- `instagram_session/` -- browser state
- `CLAUDE.local.md` -- personal preferences
- `logs/` -- runtime logs

### Deploy pattern (current)
No CI/CD pipeline. Manual deploy:
1. `git push origin main` (from dev machine)
2. `git pull origin main` (on VPS)
3. `docker restart <container>` (if service code changed)
4. Python bind-mount means code changes are live without rebuild

### Commit frequency
- Atomic commits: one logical change per commit
- Multi-step builds use `pass1:`, `pass2:` prefixes
- Feature builds often consolidated: `feat: tool mastery -- X, Y, Z complete`
- Fixes are immediate and specific: `fix: cc_sdk concurrent call handling`

## Gotchas

### Session JSON files cause merge noise
`session_state.json`, `notion_sync_state.json`, and `notion_tasks_sync_state.json`
are tracked but change frequently from automation. They often show up in
`git status` and can cause unnecessary merge conflicts. Consider moving
them to `.gitignore` and keeping state in Neon instead.

### Multiple devices = pull before everything
VPS, Windows, iPad, and iPhone all access the repo. Forgetting to pull
before starting work on any device is the most common source of push
rejection. Always: `git pull --rebase origin main` first.

### Claude Code PostToolUse hooks mutate files
Ruff format runs on every Python file write. This means the file on disk
may differ from what you wrote. `git diff` will show formatting changes
that are expected. Do not try to "fix" these -- ruff is authoritative.

### No custom git hooks installed
`.git/hooks/` contains only sample files. All validation is done through
Claude Code hooks. If running git operations outside Claude Code (e.g.,
from raw terminal), there is no pre-commit lint or import check.
