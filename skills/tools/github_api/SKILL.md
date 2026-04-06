---
name: github_api
description: "Use when creating, reading, updating repos, issues, pull requests, releases, gists, branches, or workflow runs on GitHub — via REST v3, GraphQL v4, or the `gh` CLI. Also use when scripting `gh api` / `gh api graphql`, setting Actions secrets/variables, verifying webhook deliveries, dispatching workflows, or running the daily commit-push-pr loop. Consolidates `gh_cli`."
allowed-tools: "Read, Write, Edit, Bash, WebFetch, WebSearch"
version: 1.0
source_url: "https://docs.github.com/en/rest"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "2022-11-28"
sdk_version: "PyGithub>=2.1, gh>=2.40"
speed_category: "medium"
trigger: both
effort: high
context: fork
---

# Tool: GitHub API + gh CLI

Consolidated skill. Covers REST v3, GraphQL v4, and the `gh` command-line
tool as a single programmable surface. `gh` used daily in the
commit-push-pr workflow; REST/GraphQL for any scripted or agent-driven
operation beyond that loop.

## What This Tool Does

- **REST v3** (`https://api.github.com`) — default API for CRUD on repos,
  issues, PRs, releases, Actions, users. Familiar HTTP verbs, ETag caching.
- **GraphQL v4** (`https://api.github.com/graphql`) — single-round-trip
  deeply-nested reads. Some surface is GraphQL-only (Projects v2,
  Discussions, some Copilot features).
- **`gh` CLI** — GitHub client (not a git extension). First-class verbs for
  PRs, Issues, Actions, Releases, Codespaces, Secrets, Extensions. `gh api`
  is a universal, authenticated, paginating, jq-aware API client — a better
  `curl` for GitHub.

## EOS Integration

**Primary consumers:**
- Daily `commit-push-pr` workflow: `gh pr create --fill` after any
  commit-worthy change.
- Agent automation: `gh api /repos/:owner/:repo/...` resolves the current
  remote automatically — no token juggling.
- CI gating: `gh run watch` exits non-zero on failure — use for scripted
  deploy pipelines.
- Cross-repo scripting: `gh api --paginate --jq` for TSV reports.

**Token**: `GITHUB_TOKEN` in `/opt/OS/eos_ai/.env`. `gh` reads
`GH_TOKEN` > `GITHUB_TOKEN` > keychain. Classic PAT currently; plan to
migrate to a fine-grained PAT or GitHub App as scope grows.

## Authentication

**Token types (prefix → meaning):**
| Type | Prefix | Expiry | Notes |
|---|---|---|---|
| PAT classic | `ghp_` | optional | Legacy; scope-based all-or-nothing |
| Fine-grained PAT | `github_pat_` | ≤1 year required | Per-repo + per-permission |
| GitHub App JWT | — | ≤10 min | RS256 signed with app private key |
| Installation token | `ghs_` | **1 hour** | Created via `/app/installations/{id}/access_tokens` |
| OAuth App | `gho_` | — | Legacy |
| Actions `GITHUB_TOKEN` | ephemeral | job lifetime | Auto-injected in runners |

**EOS storage** — `/opt/OS/eos_ai/.env`:
```
GITHUB_TOKEN=ghp_xxx               # or github_pat_ fine-grained
GH_WEBHOOK_SECRET=whsec_xxx        # if receiving webhooks
```

**`gh` auth commands:**
```bash
gh auth login                          # interactive
gh auth login --with-token < tok       # non-interactive
gh auth status                         # check active scopes
gh auth refresh -s workflow,repo       # add scopes
gh auth token                          # print active token
```

Required scopes for EOS daily workflow: `repo`, `workflow`, `read:org`,
`read:user`, `gist`, `admin:repo_hook`.

## Quick Reference

### The daily "ship it" motion
```bash
git add -A && git commit -m "fix: x" && git push -u origin HEAD && \
  gh pr create --fill --base main && gh pr view --web
```

### `gh api` universal client
```bash
# GET with jq
gh api /repos/owner/repo/issues --jq '.[] | {n: .number, t: .title}'

# Paginated
gh api --paginate /repos/owner/repo/issues --jq '.[].number'

# POST with form fields (strings)
gh api -X POST /repos/owner/repo/issues -f title="Bug" -f body="details"

# POST with typed JSON (-F accepts bool/num/array)
gh api -X POST /repos/owner/repo/issues \
  -F draft=false -F "labels[]=bug" -F "labels[]=p1"

# PATCH / DELETE
gh api -X PATCH /repos/owner/repo/issues/1 -f state=closed
gh api -X DELETE /repos/owner/repo/issues/comments/123

# GraphQL
gh api graphql -F owner=OWNER -F repo=REPO -f query='
  query($owner:String!,$repo:String!){
    repository(owner:$owner,name:$repo){stargazerCount}
    rateLimit{cost remaining}
  }'

# API version header
gh api -H "X-GitHub-Api-Version: 2022-11-28" /repos/owner/repo
```

### Common gh verbs
```bash
gh repo view | clone | create | list | delete | fork | archive
gh issue  create | list | view | close | comment | edit | develop
gh pr     create --fill | list | view | merge --squash | checkout N | diff | checks | status
gh run    list | view --log | watch | rerun | cancel
gh workflow run deploy.yml -f env=prod -r main
gh release create v1.0 --generate-notes --target main
gh secret set KEY --body "$VALUE" [--repo OWNER/REPO] [--env NAME] [--org ORG]
gh variable set KEY --body "value"
gh gist create file.md -d "desc" --public
gh search repos "django stars:>1000"
gh browse -n                       # print current file URL
gh extension install owner/gh-foo
```

### PyGithub (`pip install 'PyGithub>=2.1,<3'`)
```python
from github import Github, Auth, GithubException
g = Github(auth=Auth.Token(os.getenv("GITHUB_TOKEN")), per_page=100)
repo = g.get_repo("owner/name")
for issue in repo.get_issues(state="open"):   # auto-paginates
    print(issue.number, issue.title)
repo.create_issue(title="Bug", body="...", labels=["bug"])
g.close()
```

### Webhook verification (Flask)
```python
import hmac, hashlib, os
SECRET = os.getenv("GH_WEBHOOK_SECRET").encode()

@app.post("/webhook")
def webhook():
    sig = request.headers.get("X-Hub-Signature-256", "")
    expected = "sha256=" + hmac.new(
        SECRET, request.data, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return ("", 401)
    event    = request.headers["X-GitHub-Event"]
    delivery = request.headers["X-GitHub-Delivery"]
    # handle event...
    return ("", 204)
```

## Conceptual Model

Every GitHub action is either:
1. A **git operation** that touches the object store (commit, push, branch,
   tag, blob), OR
2. A **metadata operation** layered on top of git refs (issue, PR, review,
   label, check run, deployment).

Webhooks fire on both layers. Once you see this split, the API layout
stops feeling arbitrary.

**PRs ARE Issues** — PR #42 and Issue #42 cannot coexist in the same repo
because they draw from the same number sequence. `/issues/{n}` endpoints
work on PRs for comments, labels, assignees, state. Use `/pulls/{n}` only
for reviews, merges, diffs.

## Gotchas

- **GitHub webhooks do NOT retry.** Unlike Stripe (3 days of retries),
  GitHub drops events if your endpoint is down for even 30 seconds. Only
  GitHub Apps have a redelivery API (`/app/hook/deliveries/{id}/attempts`).
  PAT/OAuth webhooks have no recovery — poll if reliability matters.
- **`/issues` endpoint returns PRs too.** Filter with
  `.pull_request == null` (REST) or use GraphQL `issues()` connection
  (PR-exclusive).
- **`per_page` defaults to 30, max 100.** Always pass `per_page=100` —
  3.3× fewer requests for free.
- **Primary vs secondary rate limits are different.** Primary: 5k req/hr
  (REST) or 5k points/hr (GraphQL). Secondary: 100 concurrent, 80
  content-creation/min, 900 points/min REST, 2000 points/min GraphQL.
  Secondary limits are NOT visible in `/rate_limit` — only detected on
  403/429 with `Retry-After`.
- **GraphQL timeouts double-charge.** A query timing out costs extra
  points — always backoff, never immediately retry.
- **Conditional requests are free.** Use `If-None-Match: "etag"` — a
  304 response does NOT count against rate limit.
- **Search has eventual consistency.** New repos, issues, code take
  seconds to minutes to appear. Don't write tests that create then
  immediately search.
- **`gh api --paginate` doesn't work with `-X POST`** — POST isn't
  paginatable.
- **`gh run watch` exits non-zero on workflow failure** — use in CI for
  gate behavior.
- **Actions `GITHUB_TOKEN` is 1,000 req/hr per repo.** Don't use it for
  cross-repo ops — use an App installation token or PAT.
- **`gh pr create` on detached HEAD** needs explicit `--base main --head
  your-branch`.
- **Classic PATs are being phased out.** New integrations should be
  fine-grained PATs or GitHub Apps.
- **Projects v1 is REST-deprecated; v2 is GraphQL only.**
- **Renamed repos redirect git + REST but can 404 on GraphQL node IDs.**

## Verification

```bash
python3 -c "
toolname='github_api'
c=open(f'/opt/OS/skills/tools/{toolname}/SKILL.md').read()
b=open(f'/opt/OS/skills/tools/{toolname}/references/best_practices.md').read()
assert len(c)>500 and '## Authentication' in c and '## Gotchas' in c
assert len(b)>2000
for s in ['Authentication','Core Operations','Pagination','Rate Limits',
          'Error Codes','SDK Idioms','Anti-Patterns','Data Model','Webhooks',
          'Limits','Cost Model','Version Pinning','Design Intent',
          'Problem-Solution Map','Operational Behavior','Ecosystem Position',
          'Trajectory','Conceptual Model','Industry Expert']:
    assert f'## {s}' in b, f'Missing {s}'
print('PASS')
"
```

See `references/best_practices.md` for the full 19-section reference.
