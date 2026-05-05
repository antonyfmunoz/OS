# GitHub API + gh CLI — Best Practices

Creator-level reference. Consolidated: REST v3, GraphQL v4, gh CLI.
Last researched 2026-04-06. API version pinned `2022-11-28`.
SDK: `PyGithub>=2.1,<3`, `gh>=2.40`.

Sources: docs.github.com, cli.github.com/manual, github.blog.

---

## Authentication

### Token types
| Type | Prefix | Expiry | Repo targeting | Notes |
|---|---|---|---|---|
| PAT classic | `ghp_` | optional | all-or-nothing via scopes | Legacy |
| Fine-grained PAT | `github_pat_` | ≤1 year required | per-repo + per-permission | **Recommended** |
| GitHub App JWT | — | ≤10 min | — | RS256 signed with app key |
| App installation token | `ghs_` | **1 hour** | scoped to installation | `POST /app/installations/{id}/access_tokens` |
| OAuth App | `gho_` | — | — | Legacy; use Apps instead |
| Actions `GITHUB_TOKEN` | — | job lifetime | current repo only | Auto-injected |

### Classic PAT scopes (most used)
- `repo` — full private repo control (includes `public_repo`, `repo:status`,
  `repo_deployment`, `repo:invite`, `security_events`)
- `workflow` — update Actions workflows
- `read:org`, `write:org`, `admin:org`
- `admin:repo_hook`, `write:repo_hook`, `read:repo_hook`
- `gist`, `notifications`
- `user`, `read:user`, `user:email`
- `delete_repo`
- `read:packages`, `write:packages`, `delete:packages`
- `read:discussion`, `write:discussion`
- `admin:gpg_key`, `admin:ssh_signing_key`

### gh auth commands
```bash
gh auth login                          # interactive (web or paste token)
gh auth login --with-token < tok       # non-interactive
gh auth token                          # print active token
gh auth status                         # logged-in accounts + scopes
gh auth refresh -s workflow,repo       # add scopes
gh auth logout
gh auth switch                         # multi-account
gh auth setup-git                      # configure git credential helper
```

### GitHub App installation token flow
1. Sign JWT with app private key (RS256), `iat`, `exp ≤10 min`, `iss=APP_ID`
2. `GET /app/installations` with `Authorization: Bearer <JWT>` → list installations
3. `POST /app/installations/{id}/access_tokens` → `{token: "ghs_...", expires_at, permissions, repositories}` — valid **1 hour**
4. Optional body: `repositories`, `repository_ids`, `permissions` to narrow scope

```python
import jwt, time, requests
payload = {"iat": int(time.time())-60, "exp": int(time.time())+540, "iss": APP_ID}
j = jwt.encode(payload, PRIVATE_KEY, algorithm="RS256")
r = requests.post(f"https://api.github.com/app/installations/{inst}/access_tokens",
    headers={"Authorization": f"Bearer {j}", "Accept": "application/vnd.github+json"})
token = r.json()["token"]    # ghs_...
```

### EOS storage
- `GITHUB_TOKEN` in `/opt/OS/eos_ai/.env`
- `gh` reads `GH_TOKEN` > `GITHUB_TOKEN` > keychain
- `GH_TOKEN` overrides keychain auth

Source: docs.github.com/en/rest/overview/authenticating-to-the-rest-api.

---

## Core Operations

REST base `https://api.github.com`. GraphQL base `https://api.github.com/graphql`.

### Repositories
| Op | REST | gh |
|---|---|---|
| Get | `GET /repos/{o}/{r}` | `gh repo view OWNER/REPO` |
| Create (user) | `POST /user/repos` | `gh repo create NAME --public` |
| Create (org) | `POST /orgs/{o}/repos` | `gh repo create ORG/NAME` |
| List user | `GET /user/repos` | `gh repo list` |
| List org | `GET /orgs/{o}/repos` | `gh repo list ORG` |
| Delete | `DELETE /repos/{o}/{r}` | `gh repo delete OWNER/REPO --yes` |
| Archive | `PATCH` `{archived:true}` | `gh repo archive` |
| Fork | `POST /repos/{o}/{r}/forks` | `gh repo fork` |
| Clone | — | `gh repo clone OWNER/REPO` (handles auth) |

### Issues
| Op | REST | gh |
|---|---|---|
| Create | `POST /repos/{o}/{r}/issues` | `gh issue create -t T -b B` |
| List | `GET /repos/{o}/{r}/issues` | `gh issue list` |
| Get | `GET /repos/{o}/{r}/issues/{n}` | `gh issue view N` |
| Update | `PATCH /repos/{o}/{r}/issues/{n}` | `gh issue edit N` |
| Close | `PATCH` `{state:closed}` | `gh issue close N` |
| Comment | `POST .../comments` | `gh issue comment N -b "..."` |
| Lock | `PUT .../lock` | `gh issue lock N` |

### Pull Requests (PRs are Issues + head/base refs)
| Op | REST | gh |
|---|---|---|
| Create | `POST /repos/{o}/{r}/pulls` | `gh pr create --fill` |
| List | `GET /repos/{o}/{r}/pulls` | `gh pr list` |
| Get | `GET /repos/{o}/{r}/pulls/{n}` | `gh pr view N` |
| Diff | `GET` `Accept: vnd.github.diff` | `gh pr diff N` |
| Merge | `PUT .../merge` | `gh pr merge N --squash` |
| Review | `POST .../reviews` | `gh pr review N --approve` |
| Checks | `GET /repos/{o}/{r}/commits/{sha}/check-runs` | `gh pr checks N` |
| Checkout | — | `gh pr checkout N` |
| Status | — | `gh pr status` |
| Files | `GET .../files` | — |

Merge methods: `merge`, `squash`, `rebase`. gh flags: `--squash`, `--rebase`,
`--merge`, `--auto`, `--delete-branch`. Allowed set is a per-repo setting.

### Actions / Workflows
| Op | REST | gh |
|---|---|---|
| List runs | `GET .../actions/runs` | `gh run list` |
| View run | `GET .../actions/runs/{id}` | `gh run view ID --log` |
| Watch | — | `gh run watch ID` (blocks) |
| Rerun | `POST .../rerun` | `gh run rerun ID` |
| Rerun failed | `POST .../rerun-failed-jobs` | `gh run rerun ID --failed` |
| Cancel | `POST .../cancel` | `gh run cancel ID` |
| Artifacts | `GET .../artifacts/{id}/zip` | `gh run download ID` |
| List workflows | `GET .../actions/workflows` | `gh workflow list` |
| Dispatch | `POST .../workflows/{id}/dispatches` | `gh workflow run file.yml -f k=v` |

### Releases
| Op | REST | gh |
|---|---|---|
| Create | `POST /repos/{o}/{r}/releases` | `gh release create v1.0 --generate-notes` |
| List | `GET /repos/{o}/{r}/releases` | `gh release list` |
| Get latest | `GET .../releases/latest` | `gh release view --latest` |
| Upload asset | POST to `upload_url` | `gh release upload v1.0 file.tar.gz` |
| Delete | `DELETE .../releases/{id}` | `gh release delete v1.0` |

### Search
`GET /search/{repositories,code,issues,users,commits}?q=...`
gh: `gh search repos|code|issues|users|prs|commits "..."`.
Hard ceiling: **1000 results per search** regardless of pagination.

### Python SDKs

**PyGithub** (`pip install 'PyGithub>=2.1,<3'`):
```python
from github import Github, Auth, GithubException
g = Github(auth=Auth.Token(token), per_page=100)
repo = g.get_repo("owner/name")
issue = repo.create_issue(title="Bug", body="...", labels=["bug"])
pr    = repo.create_pull(title="Fix", body="...", head="feat", base="main")
for r in g.search_repositories("stars:>1000 language:python"): ...
wf = repo.get_workflow("ci.yml"); wf.create_dispatch("main", inputs={})
```
v2 uses `Auth` classes (passing token str directly deprecated).

**ghapi** (auto-generated from OpenAPI, ideal for agents):
```python
from ghapi.all import GhApi, paged
api = GhApi(token=token)
api.issues.create(owner="o", repo="r", title="t", body="b")
for page in paged(api.issues.list_for_repo, per_page=100):
    for issue in page: ...
```

**github3.py** — cleaner OO, slightly less coverage.

---

## Pagination

### REST
- `Link` header: `<...?page=2>; rel="next"`, `rel="last"`, `rel="first"`, `rel="prev"`
- `per_page` default **30**, max **100** (some endpoints lower)
- Search API: hard 1000-result ceiling regardless of pagination
- Loop until no `rel="next"` — never construct URLs manually

```python
import requests
url = "https://api.github.com/repos/o/r/issues?per_page=100"
while url:
    r = requests.get(url, headers={"Authorization": f"Bearer {tok}"})
    yield from r.json()
    url = r.links.get("next", {}).get("url")
```

### gh CLI
```bash
gh api --paginate /repos/o/r/issues
gh api --paginate -X GET /search/code -f q=foo
```
**Does NOT work with `-X POST`** — POST isn't paginatable.

### PyGithub
`PaginatedList` auto-paginates on iteration. `.totalCount` triggers a HEAD.

### GraphQL (cursor)
```graphql
query($cursor: String) {
  repository(owner:"o", name:"r") {
    issues(first: 100, after: $cursor) {
      pageInfo { endCursor hasNextPage }
      nodes { number title }
    }
  }
}
```
Loop: pass `endCursor` as `$cursor` until `hasNextPage = false`.
`first`/`last` must be **1–100**.

---

## Rate Limits

### Primary (per hour unless noted)

| Identity | Core REST | Search | GraphQL |
|---|---|---|---|
| Unauthenticated | **60/hr** (per IP) | 10/min | — |
| PAT (classic or fine-grained) | **5,000/hr** | 30/min | 5,000 pts/hr |
| OAuth App | 5,000/hr | 30/min | 5,000 pts/hr |
| GitHub App (base) | 5,000/hr | 30/min | 5,000 pts/hr |
| GitHub App (Enterprise Cloud) | **15,000/hr** | — | 10,000 pts/hr |
| GitHub App scaling | +50/hr per repo over 20, +50/hr per user over 20, cap 12,500/hr | — | — |
| Actions `GITHUB_TOKEN` | **1,000/hr per repo** (15k EC) | — | 1,000 pts/hr |

### Secondary rate limits (abuse detection, apply to everyone)
- **100 concurrent requests** (REST+GraphQL combined)
- **900 points/min** for REST
- **2,000 points/min** for GraphQL
- **90 seconds CPU time per 60 seconds real time**
- **80 content-creation requests/min, 500/hr** (issues, comments, PRs, forks…)
- **2,000 OAuth token requests/hr**

### Response headers
```
X-RateLimit-Limit: 5000
X-RateLimit-Remaining: 4999
X-RateLimit-Reset: 1696000000      # unix epoch UTC seconds
X-RateLimit-Used: 1
X-RateLimit-Resource: core         # or search | graphql | code_search
Retry-After: 60                    # on 403/429 secondary
```

### 403 vs 429
- Primary exceeded → `403 Forbidden` with `API rate limit exceeded`
- Secondary exceeded → `403` or `429` with `Retry-After`
- Always check `Retry-After` before exponential backoff

### GraphQL point calculation
`ceil(sum_of_connection_requests / 100)`, minimum 1 pt. Node limit:
**500,000 nodes/query**. `first`/`last` 1–100 per connection. Query
timeout **10 s** — timeouts incur extra points.

Include `rateLimit { cost remaining resetAt nodeCount }` in every
repeatable GraphQL query.

### Inspect
```bash
gh api /rate_limit
```
Secondary limits are **NOT visible** in `/rate_limit` — only detected on 403/429.

### Backoff (GitHub's guidance)
1. Honor `Retry-After` if present
2. Exponential backoff from 1s, jitter ±25%
3. Never retry immediately on secondary — wait ≥60s
4. Serialize creates; don't parallelize to the same resource

Source: docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api,
docs.github.com/en/graphql/overview/resource-limitations.

---

## Error Codes

### Status codes
| Code | Meaning |
|---|---|
| 200 | OK |
| 201 | Created |
| 204 | No Content (DELETE/PUT success) |
| 301 | Moved Permanently (repo renamed) — follow `Location` |
| 304 | Not Modified — conditional request, **does NOT count against rate limit** |
| 400 | Bad Request (malformed JSON) |
| 401 | Unauthorized (bad/missing token) |
| 403 | Forbidden — perms OR rate limit OR abuse |
| 404 | Not Found — OR private resource + insufficient auth (GH hides existence) |
| 409 | Conflict — merge conflict, branch exists |
| 410 | Gone |
| 422 | Unprocessable Entity — **validation failed** (most common real error) |
| 451 | Unavailable for Legal Reasons (DMCA) |
| 500/502/503 | Server errors — retry with backoff |

### Error body shape
```json
{
  "message": "Validation Failed",
  "documentation_url": "https://docs.github.com/rest/...",
  "errors": [
    {"resource": "Issue", "field": "title", "code": "missing_field"}
  ]
}
```

### `errors[].code` values
- `missing` — resource doesn't exist
- `missing_field` — required param omitted
- `invalid` — bad format
- `already_exists` — uniqueness conflict
- `unprocessable` — semantically invalid
- `custom` — see `message`

### Conditional requests (save rate limit!)
```
GET /repos/o/r
If-None-Match: "etag-from-previous-response"
→ 304 Not Modified   # does NOT count against rate limit
```
Also `If-Modified-Since` with `Last-Modified`. **Always use for polling.**

---

## SDK Idioms

### PyGithub
```python
from github import Github, Auth, GithubException
g = Github(auth=Auth.Token(os.getenv("GITHUB_TOKEN")), per_page=100)
try:
    repo = g.get_repo("owner/name")
    for issue in repo.get_issues(state="open"):   # auto-paginates
        print(issue.number, issue.title)
except GithubException as e:
    print(e.status, e.data)
g.close()
```
Pin: `PyGithub>=2.1,<3`. v2 switched to `Auth` classes.

### ghapi
```python
from ghapi.all import GhApi, paged
api = GhApi(owner="o", repo="n", token=tok)
api.issues.list_for_repo(state="open")
for page in paged(api.issues.list_for_repo, per_page=100):
    for issue in page: ...
```
Auto-generated from OpenAPI — always current. Lazy endpoint resolution.
Best choice for LLM agents (introspectable).

### gh api (shell — the universal pattern)
```bash
# GET with jq filter
gh api /repos/o/r/issues --jq '.[] | {n: .number, t: .title}'

# Paginated search
gh api --paginate "/search/code?q=foo+repo:o/r"

# POST string fields
gh api -X POST /repos/o/r/issues -f title="Bug" -f body="details"

# POST typed JSON fields (bool/num/array/file)
gh api -X POST /repos/o/r/issues -F draft=false -F "labels[]=bug" -F "labels[]=p1"

# PATCH
gh api -X PATCH /repos/o/r/issues/1 -f state=closed

# DELETE
gh api -X DELETE /repos/o/r/issues/comments/123

# GraphQL with template vars
gh api graphql -F owner=o -F name=r -f query='
  query($owner:String!,$name:String!){
    repository(owner:$owner,name:$name){stargazerCount}
    rateLimit{cost remaining}
  }'

# Go template output (alternative to jq)
gh api /repos/o/r --template '{{.full_name}} ⭐ {{.stargazers_count}}'

# Custom API version
gh api -H "X-GitHub-Api-Version: 2022-11-28" /repos/o/r
```

### Webhook verification (Flask)
```python
import hmac, hashlib, os
from flask import request, abort

SECRET = os.getenv("GH_WEBHOOK_SECRET").encode()

@app.post("/webhook")
def webhook():
    sig = request.headers.get("X-Hub-Signature-256", "")
    mac = hmac.new(SECRET, msg=request.data, digestmod=hashlib.sha256)
    expected = "sha256=" + mac.hexdigest()
    if not hmac.compare_digest(expected, sig):
        abort(401)
    event    = request.headers["X-GitHub-Event"]
    delivery = request.headers["X-GitHub-Delivery"]
    # handle...
    return "", 204
```

---

## Anti-Patterns

1. **Hardcoding tokens** — always env var / secret store. Never commit
   even expired tokens (revoke, don't archive).
2. **Unauthenticated requests** for anything real — 60/hr dies instantly.
3. **Polling for workflow completion** — use `gh run watch` instead
   (streams status, exits on done).
4. **Not setting `per_page=100`** — default 30 = 3.3× more requests than
   needed.
5. **Confusing primary and secondary rate limits** — different headers,
   different recovery. Honor `Retry-After`.
6. **`git clone https://github.com/...`** in scripts instead of `gh repo
   clone` — latter handles auth via `gh`'s token.
7. **N+1 REST calls** where GraphQL does it in one — e.g. fetching
   PR + reviews + commits + checks. Use GraphQL.
8. **PAT classic when fine-grained works** — classic is all-or-nothing.
9. **Skipping signed commits** when org requires them — use `-S` or
   `gh api` which creates signed commits via the Contents API automatically.
10. **`gh pr create` without `--fill`** — `--fill` auto-populates title/body
    from commits. Use `--fill-first` for first commit only.
11. **Not handling 301 on renamed repos** — always follow `Location`.
12. **Ignoring ETags** — conditional requests are free, use them for pollers.
13. **Creating many resources in parallel** — hits 80/min content-creation
    secondary limit. Serialize.
14. **PR body in title** — title ≤70 chars, detail in body.
15. **Fetching full file blobs for size** — use
    `GET /repos/.../git/trees/{sha}?recursive=1` and read the `size` field.

---

## Data Model

```
Organization
 └─ Team → members (Users)
Repository
 ├─ Branches → Commits → Tree → Blobs
 ├─ Tags → Releases → Assets
 ├─ Issues (unified with PRs in data model)
 │   └─ IssueComments, Labels, Milestones, Assignees, Reactions
 ├─ PullRequests (IS an Issue + head/base refs)
 │   ├─ Reviews → ReviewComments (inline, line-attached)
 │   ├─ Commits (PR-scoped)
 │   └─ Files (diff)
 ├─ Workflows (.github/workflows/*.yml)
 │   └─ Runs → Jobs → Steps → Logs, Artifacts
 ├─ CheckSuites → CheckRuns (Checks API)
 ├─ Statuses (legacy commit status API)
 ├─ Deployments → Environments → DeploymentStatuses
 ├─ Webhooks → Deliveries
 ├─ Secrets, Variables (Actions/Dependabot/Codespaces scopes)
 └─ Collaborators, Teams, BranchProtection, Rulesets
```

### Issue vs PR
- PRs are Issues with extra fields. `/repos/o/r/issues/{n}` works on PRs
  for comments/labels/assignees/state.
- Reviews, merges, diffs require `/repos/o/r/pulls/{n}`.
- `GET /issues` returns PRs unless you filter `pull_request == null`.

### Checks API vs Statuses API
- **Statuses** (legacy) — single success/failure/pending per commit.
  `POST /repos/o/r/statuses/{sha}`. Backward compat only.
- **Checks** (current) — rich annotations, output, images, actions.
  Must be created via GitHub App. `POST /repos/o/r/check-runs`.
  New integrations: always Checks.

### Projects v1 vs v2
- v1 is REST, deprecated
- v2 is GraphQL only (`organization.projectV2`, `addProjectV2ItemById`)

---

## Webhooks

### Event types (common)
`push`, `pull_request` (opened/closed/reopened/synchronize/review_requested/
edited/labeled), `pull_request_review`, `pull_request_review_comment`,
`issues`, `issue_comment`, `workflow_run`, `workflow_job`, `check_run`,
`check_suite`, `release`, `deployment`, `deployment_status`, `create`
(branch/tag), `delete`, `fork`, `star`, `watch`, `ping` (test),
`installation`, `installation_repositories`.

### Headers
- `X-GitHub-Event` — event name
- `X-GitHub-Delivery` — UUID
- `X-Hub-Signature-256` — `sha256=<hex_hmac>` (SHA-1 variant is legacy)
- `X-GitHub-Hook-ID`, `X-GitHub-Hook-Installation-Target-ID`

### Signature verification rules
- Use `hmac.compare_digest` (constant-time — prevents timing attacks)
- Hash the **raw request body bytes**, not parsed JSON
- Secret stored as env var

### Delivery retry — CRITICAL GOTCHA
**GitHub webhooks have NO retry.** Failed deliveries (non-2xx or timeout
>10s) are gone. This is radically different from Stripe's 3-day retry.

The only recovery path:
- **GitHub Apps** have a redelivery API:
  `POST /app/hook/deliveries/{id}/attempts` — you can replay
- **PATs/OAuth webhooks** have no recovery — poll or accept the loss
- `gh api /repos/o/r/hooks/{id}/deliveries` inspects delivery history and
  can redeliver via `POST .../deliveries/{id}/attempts`

### Local testing
```bash
gh webhook forward --repo=o/r --events=push --url=http://localhost:8080/webhook
```

---

## Limits

| Limit | Value |
|---|---|
| Single file (hard) | **100 MB** |
| Single file (warning) | 50 MB |
| Recommended repo size | <1 GB |
| Hard repo size | <5 GB |
| Release asset max | **2 GB/file** |
| Git push size | 2 GB |
| API request body | ~10 MB |
| GraphQL node limit | **500,000 nodes/query** |
| GraphQL `first`/`last` | 1–100 per connection |
| GraphQL query timeout | **10 seconds** |
| Issue/PR/comment body | 65,536 chars |
| Label name | 50 chars |
| Labels per issue | 100 |
| Assignees per issue | 10 |
| Topics per repo | 20 |
| Branch protection patterns | 100/repo |
| Actions concurrent jobs (free) | 20 |
| Actions job max duration | 6 hours |
| Actions workflow max duration | 35 days |
| Artifact retention default | 90 days |
| Secondary content-creation | 80/min, 500/hr |
| Search results ceiling | 1,000 total |

---

## Cost Model

### Plans
- **Free** — unlimited public + private repos, unlimited collaborators,
  2,000 Actions min/mo, 500 MB Packages, 120 Codespaces core-hours
- **Team** — **$4/user/mo** — 3,000 Actions min, 2 GB Packages, protected
  branches, required reviewers, draft PRs, code owners
- **Enterprise Cloud** — **$21/user/mo** — 50,000 Actions min, 50 GB
  Packages, SAML SSO, audit log, **15,000 req/hr** rate limit

### Actions minutes (overage)
- Linux: **$0.008/min**
- Windows: $0.016/min (2×)
- macOS: $0.08/min (10×)
- Public repos: **unlimited free**

### Storage
- Packages/Artifacts overage: $0.25/GB/mo
- Free: 500 MB; Team: 2 GB; Enterprise: 50 GB

### Codespaces
- Compute: $0.18/hr (2-core) → $2.88/hr (32-core)
- Storage: $0.07/GB/mo
- Free tier: 120 core-hours + 15 GB/mo

### API
**Free** within rate limits. No per-call charge.

---

## Version Pinning

### REST
- Header: `X-GitHub-Api-Version: 2022-11-28`
- Current versions: **2022-11-28** (default if omitted), **2026-03-10**
- Each version supported **≥24 months** after successor release
- Breaking changes (remove op, remove/rename param, add required param)
  gated behind new version
- Non-breaking changes (new optional params, new response fields) ship
  to all versions

```bash
curl -H "X-GitHub-Api-Version: 2022-11-28" https://api.github.com/repos/o/r
gh api -H "X-GitHub-Api-Version: 2022-11-28" /repos/o/r
```

### GraphQL
- **No header versioning.** Schema evolves in-place with deprecations
  (≥1 year notice)
- Preview features via `Accept: application/vnd.github.{name}-preview+json`
  — mostly deprecated/GA now. Avoid in new code.

### gh CLI
```bash
gh --version
gh extension list
brew upgrade gh                 # mac
apt install --only-upgrade gh   # debian
winget upgrade GitHub.cli       # windows
```
gh auto-warns on outdated versions.

### SDK pinning
- `PyGithub>=2.1,<3` — v2 switched to Auth classes
- `ghapi` — follows OpenAPI, pin minor for stability
- `github3.py>=4`

Source: docs.github.com/en/rest/overview/api-versions.

---

# Tier 2 — Creator Intelligence

---

## Design Intent

**Why `gh` when `curl` + `git` + `hub` existed.** `hub` (Mislav Marohnić,
2009) was a `git` proxy — alias `git=hub` and `git pull-request` worked.
Slow (Ruby), philosophically constrained: every command had to make sense
as a `git` subcommand. In 2019 Owen Ou rewrote it in Go as "gh"; GitHub
adopted it as the official CLI and rebuilt it with a fundamentally
different design — **`gh` is a GitHub client that happens to do some git,
not a git extension that happens to do GitHub**. This freed the CLI to
model PRs, Issues, Actions, Releases, Codespaces, Projects as first-class
verbs rather than shoehorning them onto git plumbing.

**Why GraphQL alongside REST.** REST (v3, 2013) remains default — caching,
familiarity, HTTP-verb semantics are free. GraphQL (v4, 2016) exists
because GitHub's own product surface (issue + author + labels + comments +
reactions + timeline + linked PRs) required 11+ REST calls to render one
issue page. Internally GitHub's web UI migrated to GraphQL for this
reason. Tradeoff: GraphQL loses HTTP caching and introduces a cost-budget
rate limit model. They kept both because REST is better for simple CRUD
and webhooks, GraphQL is better for deeply-nested reads. New surface
(Projects v2, Discussions, some Copilot features) is GraphQL-only.

**Issues as a superset of PRs.** PRs ARE Issues in the database — every
PR has an issue number drawn from the same sequence (can't have issue #42
and PR #42 in the same repo). A design compromise from the monolith days:
a single query can filter issues+PRs uniformly, labels/milestones/
assignees work identically on both, `gh issue` and `gh pr` share most
backend. Cost: `/issues` also returns PRs unless filtered.

**Webhooks as the extensibility spine.** Every meaningful mutation emits
an event. The single most important architectural decision: turned
GitHub from a product into a platform. Integrations (Slack, Jira, CI
vendors) all bootstrapped off webhooks before Apps existed.

**Actions as GitHub's "functions" product.** Co-locating CI with code
eliminated the #1 friction of 2010s CI (keeping `.travis.yml`/Jenkinsfile
in sync with an external vendor). The bet: vertical integration beats
best-of-breed. It worked.

**Checks API vs Statuses.** Statuses (legacy) — single row per commit per
context. Checks (2018) — structured objects with line-level annotations,
rerun support, output — power "View details" and inline PR comments from
CI. New integrations: always Checks.

Sources: cli/cli docs/gh-vs-hub.md, mislav.net/2020/01/github-cli,
docs.github.com comparing REST and GraphQL.

---

## Problem-Solution Map

**Extensions are the plugin system most users don't know exists.**
`gh extension install owner/gh-foo` turns any `gh-foo` binary into
`gh foo`. Popular:
- `dlvhdr/gh-dash` — TUI dashboard for PRs/issues across repos
- `github/gh-poi` — safe local branch cleanup, detects merged branches
  even after squash merges
- `github/gh-copilot` — **deprecated Oct 2025**, replaced by standalone
  Copilot CLI (Jan 2026)
- `gh-aw` — agentic workflows
- `ChrisCarini/gh-copilot-review` — request Copilot code reviews from CLI

**LLM in the shell.** `gh copilot suggest "find files larger than 10MB
modified this week"` → shell command. `gh copilot explain "<cmd>"` →
reverse. Now ships under the new Copilot CLI binary.

**Drop to raw GraphQL.** `gh api graphql -f query='...'` uses existing
auth, no curl/token setup. `-F owner=o -F name=r` for template variables.

**`gh api --paginate --jq`.** The killer combo for shell reports:
```bash
gh api --paginate "/orgs/ORG/issues?state=open" \
  --jq '.[] | [.number,.title,.user.login] | @tsv'
```

**`gh pr checkout 123`.** Auto-fetches the branch *even from forks*, sets
up tracking, handles the whole `git fetch + checkout -b` dance.

**`gh pr create --fill`.** Uses last commit message as PR title+body.
`--fill-first` uses only the first commit. The default "ship it" motion.

**`gh issue develop NUMBER --checkout`.** Create a branch linked to an
issue and check it out — auto-closes the issue on merge.

**`gh run watch`.** Live-stream an Actions run. Exits non-zero on failure.

**`gh browse -n`.** Print the current file/branch URL without opening.

**`gh secret set KEY --body "$VALUE"`.** Manage Actions secrets without
the web UI. `--env`, `--org`, `--repo` scopes supported.

**`gh codespace ssh` / `gh codespace cp`.** Codespaces is a full CLI
citizen.

**`gh alias set prs "pr list --author @me"`.** Personal shortcuts
persisted in `~/.config/gh/config.yml`.

**Rulesets** (2023 GA, 2024 replacing branch protection): multiple
rulesets can apply at once (branch protection allowed only one matching
rule), target tags and branch *creation* (not just existing), and can
be org-wide — one ruleset applied across all repos matching a pattern.
Branch protection can't do that.

**Fine-grained PATs + Rulesets + GitHub Apps** are the three pillars of
modern GitHub security hygiene.

Sources: awesome-gh-cli-extensions, docs.github.com/en/repositories/
configuring-branches-and-merges-in-your-repository/managing-rulesets.

---

## Operational Behavior

**Rate limits are three layers, not one.** REST primary (5k/hr), GraphQL
primary (5k points/hr — points are computed from query complexity), and
secondary (100 concurrent across both APIs, 2000 points/min GraphQL, plus
unpublished abuse heuristics).

**GitHub Apps scale to 15,000 req/hr** based on installation size (org
users + repos).

**GraphQL timeouts double-charge.** A timed-out query costs extra points
on your next hour's budget. Always exponential-backoff retries.

**Cost-aware queries.** Always include at top level of repeatable queries:
```graphql
rateLimit { cost remaining resetAt nodeCount }
```

**Pagination silently truncates.** REST caps 100/page, GraphQL 100/nodes
per connection. `--paginate` handles it; hand-rolled clients that forget
`Link: rel="next"` lose data.

**Webhooks don't retry.** The single biggest reliability gotcha. Unlike
Stripe (3 days, exponential backoff, dashboard replay), **GitHub webhooks
have no retry and no replay API** for PATs/OAuth. If your endpoint is
down for 30 seconds during a push, those events are gone. Recovery:
poll, or use GitHub Apps (which DO have a redelivery API at
`/app/hook/deliveries/{id}/attempts`).

**Checks vs statuses confusion.** Both render in the PR "checks" tab.
Different APIs, different permission scopes, different webhook events
(`status` vs `check_run`/`check_suite`). New code: Checks only.

**Search eventual consistency.** New repos, issues, code take seconds to
minutes to appear. Don't write tests that create then immediately search.

**PR merge methods are per-repo.** `gh pr merge --squash` fails if the
repo has squash disabled. Check settings or catch the 405.

**Force-pushed PR branches.** Reviews stay attached to commit SHAs; if
you force-push, the "View changes since last review" works but some older
UI views appear to lose review state. Don't force-push during active
review unless the team agrees.

**Renamed repos/orgs** keep redirects for `git clone` and most REST
calls, but GraphQL node IDs can 404 and some webhook payloads use the
old name until cache expiry.

**`X-RateLimit-Reset` is epoch UTC seconds**, not ISO8601.

**`gh pr create` on detached HEAD.** Auto base-branch detection depends
on git tracking. On detached HEAD pass `--base main --head your-branch`
explicitly.

Sources: github.com/orgs/community/discussions on webhook retry,
docs.github.com/en/webhooks.

---

## Ecosystem Position

**Why GitHub won.** GitLab is technically broader (built-in CI long
before Actions, built-in container registry, built-in monitoring).
Bitbucket has Atlassian integration. Gitea/Forgejo are self-host darlings.
GitHub won on **network effects**: your OSS dependencies live there, your
resume lives there, your identity lives there. Microsoft's 2018
acquisition accelerated Actions, Codespaces, Copilot — three features
that widened the moat.

**Composition sweet spots:**
- **`gh + jq`** — the universal API scripting pattern. `gh api` is a
  better `curl` for GitHub because it handles auth + pagination + JSON.
- **`gh + fzf`** — `gh pr list --json number,title --jq '.[] | "\(.number) \(.title)"' | fzf | awk '{print $1}' | xargs gh pr checkout`
  is the canonical "pick a PR" motion.
- **`gh + GitHub Actions`** — `gh` is pre-installed on every runner with
  `GITHUB_TOKEN` already set. Script anything in a workflow step without
  adding Marketplace actions.
- **`gh + Claude Code / Cursor`** — direct `gh` invocation gives agents a
  clean API without token juggling.

**Actions vs standalone CI.** Actions eats the low end (free tier, zero
setup) and increasingly the middle (reusable workflows, composite
actions, matrix, self-hosted runners, ARC on Kubernetes). CircleCI/
Buildkite survive on perf + enterprise features.

**Registry sprawl.** GitHub Packages (npm/maven/nuget/rubygems) is legacy.
`ghcr.io` (containers) is the one you want — best auth story, free
public pulls.

**Projects v2** is a totally different product from v1 — v1 REST,
v2 GraphQL-only. Automations via Actions are the expected integration path.

---

## Trajectory

**Deprecations:**
- Projects v1 → v2 only
- Branch protection → rulesets (coexist now, rulesets are the future)
- Classic PATs → fine-grained PATs / Apps
- `gh-copilot` extension → standalone Copilot CLI (cutover Oct 2025,
  shipped Jan 2026)

**Where investment flows (2025–2026):**
- **Copilot Workspace** — 55,000+ devs, 10,000+ merged PRs. GitHub's
  natural-language-to-PR bet.
- **GitHub Spark** — "Dream it. See it. Ship it." Copilot Pro+/Enterprise
  preview. Natural-language app builder with live preview. The 2026
  flagship.
- **GitHub Models** — first-party model hosting (OpenAI, Anthropic,
  Gemini, Mistral) billed via Copilot plans. GitHub wants to be the
  neutral routing layer for AI models.
- **Multi-model Copilot** — Claude 3.5/4, Gemini 1.5/2, GPT-4o/o1.
  "Developer choice" framing launched at Universe 2024.
- **Coding Agent / Agent Mode** — autonomous multi-step coding agent in
  IDEs (GA 2026). Creates branches, edits files, runs terminal, iterates
  on errors, opens PRs.
- **Agentic code review** — Copilot reviewing PRs automatically.
- **Rulesets** — continued expansion; expect evaluation history + drift
  detection.
- **Advanced Security** (CodeQL, secret scanning, Dependabot) — big
  enterprise revenue driver alongside Copilot.
- **Codespaces** — slower growth than expected; backbone for Spark/
  Workspace.

**Where investment is NOT flowing:** REST API (stable, feature-frozen),
Projects v1, OAuth apps, classic PATs, gists.

Sources: github.blog/changelog, GitHub Universe 2024 press release,
docs.github.com/en/copilot/concepts/spark.

---

## Conceptual Model

**Primitives.** Repo, Branch, Commit, Tree, Blob, Tag, Issue, PR (subtype
of Issue), Review, Comment, Label, Milestone, Workflow, Run, Job, Step,
Artifact, Release, Check Run, Check Suite, Status, Deployment,
Environment, Secret, Variable, Ruleset, Webhook, App, Installation.

**Verbs.** fork, clone, branch, commit, push, pull, pull-request, review,
approve, merge (merge/squash/rebase), tag, release, deploy, dispatch
(workflow), cancel, rerun.

**Mental model.** Every action is either (a) a git operation that
eventually touches the object store, or (b) a metadata operation layered
on top of git refs. PRs, reviews, labels, issues, check runs — all
metadata. Commits, branches, tags, blobs — all git. Webhooks fire on
both layers.

**Recipe 1 — Ship it.**
```bash
git add -A && git commit -m "fix: x" && git push -u origin HEAD && \
  gh pr create --fill --base main
```

**Recipe 2 — Trigger a deploy.**
```bash
gh workflow run deploy.yml -f env=prod -r main
gh run watch
```

**Recipe 3 — All issues assigned to me across every org.**
```bash
gh api -X GET search/issues -f q='assignee:@me is:open archived:false' \
  --jq '.items[] | [.repository_url, .number, .title] | @tsv'
```

**Recipe 4 — Release with auto changelog.**
```bash
gh release create v1.2.0 --generate-notes --target main
```

**Recipe 5 — Issue + comments + reactions + author in one GraphQL round trip.**
```bash
gh api graphql -F owner=OWNER -F repo=REPO -F number=42 -f query='
query($owner:String!,$repo:String!,$number:Int!){
  repository(owner:$owner,name:$repo){
    issue(number:$number){
      title body author{login}
      labels(first:20){nodes{name}}
      reactions(first:100){nodes{content user{login}}}
      comments(first:100){nodes{author{login} body createdAt}}
    }
  }
  rateLimit{cost remaining resetAt}
}'
```

**Recipe 6 — Mass-merge a labeled batch.**
```bash
gh pr list --label ready --json number --jq '.[].number' \
  | xargs -I{} gh pr merge {} --squash --delete-branch
```

**Recipe 7 — Set a secret across every repo in an org.**
```bash
gh repo list ORG --limit 500 --json name --jq '.[].name' \
  | xargs -I{} gh secret set MY_SECRET --body "$VALUE" --repo ORG/{}
```

---

## Industry Expert

**The solo-founder + Claude Code + gh pattern (THIS IS EOS's daily loop).**
1. Edit files with Claude Code
2. Agent runs tests / imports
3. Agent commits with conventional prefix
4. `gh pr create --fill` (or direct push to main in solo phase)
5. `gh run watch` if CI is live
6. Agent reads `gh run view --log-failed` on failure and loops

This is explicitly enabled by `gh` being a **universal, authenticated,
JSON-producing API client**. An LLM agent never needs to handle a token —
the agent shell inherits `gh auth`.

**`gh api` as universal client.** `gh api /user --jq .login` verifies
auth anywhere. `gh api repos/:owner/:repo/...` with `:owner`/`:repo`
template vars resolved from the current git remote is how you write
scripts that work in any repo without parameters.

**Reusable workflows + composite actions = function calls.** Expert pattern:
- Composite actions = in-process function calls (share runner)
- Reusable workflows (`uses: org/repo/.github/workflows/x.yml@ref`) =
  out-of-process function calls (new runner, inputs/outputs/secrets contract)
- Matrix + strategy = map/reduce
- Treat `.github/workflows/` as a module system.

**GraphQL + jq for cross-repo reporting.** Expert move: one GraphQL query
with `repository(owner,name){...}` aliases for 10 repos in a single call,
then `jq` to pivot into TSV for a weekly report. Stays under cost budget
because aliases share child resolvers.

**Rulesets for monorepo policies.** One org-level ruleset targeting
`~DEFAULT_BRANCH` across all repos matching `production-*`, enforcing
required checks, required reviewers, signed commits, linear history, and
bypass lists for release bots. Impossible with branch protection.

**GitHub Apps over PATs at scale.** PATs belong to humans. Apps belong to
automation. Apps:
- 15,000 req/hr per installation (PATs 5,000)
- 1-hour short-lived installation tokens (PATs can live forever — audit
  nightmare)
- Fine-grained repo-level permissions
- Installation webhooks so you know when scope changes
- Post as their own identity (no "bot user" required)

Migration path: any automation living longer than a hackathon should
become an App.

**Dogfood trivia.** GitHub's own web UI uses GraphQL for nearly all
reads — the same API you have access to. When a feature ships internally,
GraphQL usually gets the schema before REST (if REST gets it at all).

**Shell-alias issue triage.** OSS maintainers alias `triage` to something
like `gh issue list --search "no:label sort:created-asc" --limit 20`,
then pipe through `fzf` to walk the backlog.

**Copilot CLI (Jan 2026).** The new `gh copilot` (standalone binary,
replaces the old extension) is positioned as a general coding agent in
the terminal — not just command suggestions.

**The EOS-aligned takeaway.** `gh` + GraphQL + Actions + Apps is a
complete programmable business-infrastructure substrate. Treat the repo
as the database, Issues as the work queue, PRs as the audit log, Actions
as the cron + worker pool, Rulesets as the access-control layer. This is
the same mental model used by platform engineering teams at scale — and
it's free for a solo founder with `gh` installed.

Sources: github.blog/2021-03-11-scripting-with-github-cli,
adamj.eu/tech/2025/11/24/github-top-gh-cli-commands,
docs.github.com/en/apps/creating-github-apps/about-creating-github-apps.
