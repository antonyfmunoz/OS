# System Architecture — Multi-Surface Operating Model

> **How to use this doc:** Load this at the start of any CC session that
> touches infrastructure, deployment, sync, or cross-device operations.
> It replaces ad-hoc rediscovery of device roles, repo locations, and
> database topology. If anything here conflicts with observed reality,
> update the doc — it is the authoritative source for operating model,
> not a snapshot.
>
> Last verified: 2026-05-20 (Layer 2 addendum — sync automation)

---

## 1. Device Roles

| Device | Tailscale IP | Role | Always-on | Primary Use |
|--------|-------------|------|-----------|-------------|
| **VPS** (Hostinger Ubuntu 24.04, srv1500858) | `100.77.233.50` | Runtime host, canonical code | Yes | UMH FastAPI (8093), Docker services, agent execution, CC sessions |
| **Windows workstation** (desktop-lvguiq9) | `100.74.199.102` | Development environment | No | Local editing (VS Code), Obsidian vault, heavy compute, Windows-only ops |
| **iPhone** (Termius) | Tailscale mesh | Mobile CLI | No | SSH into VPS for commands, logs, quick orchestration |
| **iPad** (Safari + code-server) | Tailscale mesh | Medium-mobility editing | No | code-server on VPS port 8888, full VS Code in browser |

**Connectivity model:** All devices on Tailscale private mesh. Nothing
exposed publicly. VPS is the hub — all other devices connect to it.

**SSH to Windows:**
- User: `"antonys beast pc"` (quotes required — space in username)
- Auth: ed25519 key, no password
- Git binary: `"C:\Program Files\Git\cmd\git.exe"`
- Dev repos: `C:\Users\antonys beast pc\dev\`
- Shell: PowerShell (default via OpenSSH). For `$_` variables in
  scriptblocks, use `-EncodedCommand` with Base64 UTF-16LE encoding
  to avoid SSH escaping issues.

---

## 2. Repo Topology

Five codebases. One canonical checkout on VPS. GitHub is the sync layer.

### 2.1 OS (UMH Substrate + EOS v2)

The primary development repo. Contains everything.

| Surface | Path | Remote | Role |
|---------|------|--------|------|
| VPS | `/opt/OS` | `origin` → `github.com/antonyfmunoz/OS.git` | **Canonical checkout** |
| GitHub | `antonyfmunoz/OS.git` | — | Sync hub |
| Windows | `dev\OS` | SSH → `git@github.com:antonyfmunoz/OS.git` | Local development |

**Key subdirectories:**
- `saas/` — EOS v2 backend (Hono + Drizzle + Postgres RLS, TypeScript). Not a separate repo. Never deployed standalone.
- `services/umh/` — UMH runtime services
- `runtime/` — Core runtime (cognitive loop, agent runtime, memory, model router)
- `core/` — Substrate contracts, primitives, governance
- `data/repos/` — Read-only reference clones of other repos

**Branch discipline:** Commit directly to `main` (solo founder phase).
Feature branches for experimental or risky changes. `--no-ff` merges
for phase boundaries.

### 2.2 EntrepreneurOS (EOS v1 Monolith)

| Surface | Path | Remote | Role |
|---------|------|--------|------|
| GitHub | `antonyfmunoz/EntrepreneurOS.git` | — | **Canonical** |
| Windows | `dev\EntrepreneurOS` | SSH → `git@github.com:...` | Active development |
| VPS | `data/repos/entrepreneuros/` | HTTPS clone | Read-only reference |

**Branches:** `main`, `Development` (merged into main 2026-05-20),
`feature/company-system` (active head — Clerk auth, multi-agent,
company-scoped endpoints).

**Stack:** TypeScript, React 18, Vite, Tailwind, shadcn/ui, Express,
Drizzle ORM.

### 2.3 CreatorOS

| Surface | Path | Remote | Role |
|---------|------|--------|------|
| GitHub | `antonyfmunoz/CreatorOS.git` | — | **Canonical** |
| Windows | `dev\CreatorOS` | SSH → `git@github.com:...` | Local clone |
| VPS | `data/repos/creatoros/` | HTTPS clone | Read-only reference |

**Status:** Dormant product. Same stack as EntrepreneurOS.

### 2.4 LYFEOS

| Surface | Path | Remote | Role |
|---------|------|--------|------|
| GitHub | `antonyfmunoz/LYFEOS.git` | — | **Canonical** |
| Windows | `dev\LyfeOS` | SSH → `git@github.com:...` | Local clone |
| VPS | `data/repos/lyfeos/` | HTTPS clone | Read-only reference |

**Status:** Dormant product. Firebase + Stripe + PWA. 4,624 commits.

**Note:** GitHub repo name is `LYFEOS` (all caps), Windows directory is
`LyfeOS` (mixed case). Both work. VPS clone remote uses `LyfeOS.git`
(GitHub is case-insensitive for repo names).

### Sync Flow

```
                    ┌─────────────┐
                    │   GitHub    │
                    │  (sync hub) │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │   VPS    │ │ Windows  │ │  iPad/   │
        │ /opt/OS  │ │  dev\OS  │ │  iPhone  │
        │(runtime) │ │ (editor) │ │ (via VPS)│
        └──────────┘ └──────────┘ └──────────┘
```

**Direction:** VPS pushes → GitHub → Windows pulls. Windows pushes →
GitHub → VPS pulls. iPad/iPhone operate through VPS directly (SSH).

**Rule:** No device holds unique commits for more than one session.
Push before stepping away. Pull before starting work.

---

## 3. Neon Postgres Topology

Four separate Neon projects. Each is an independent database with its
own connection string, roles, and billing.

| Neon Project | Endpoint | Region | Purpose | Status |
|-------------|----------|--------|---------|--------|
| **ep-dark-poetry** | `ep-dark-poetry.us-east-1.aws.neon.tech` | us-east-1 | UMH substrate + EOS v2 dev | **Active** — all integration work targets this |
| **ep-winter-sea** | `ep-winter-sea.us-west-2.aws.neon.tech` | us-west-2 | EOS v1 production | Archived/sleeping — v1 CRM schema (16 tables) |
| **ep-bitter-union** | `...us-west-2.aws.neon.tech` | us-west-2 | CreatorOS | Dormant |
| **ep-small-sunset** | `...us-west-2.aws.neon.tech` | us-west-2 | LYFEOS (36 tables) | Dormant |

**ep-dark-poetry roles:**
- `neondb_owner` — migration runner, schema DDL
- `eos_app` — RLS-enforced runtime user (used by `saas/`)

**ep-winter-sea** is EOS production data, not UMH. Production cutover
from v1 to v2 deferred until v2 frontend exists (post-Phase 4).

**Connection strings** live in `.env` files (never committed):
- VPS: `/opt/OS/.env`, `/opt/OS/services/.env`, `/opt/OS/saas/.env`
- Windows: per-repo `.env` files (gitignored)

---

## 4. Running Services (VPS)

| Service | Container | Port | Description |
|---------|-----------|------|-------------|
| UMH FastAPI | `umh` (PID) | 8093 | Core runtime API, cognitive loop |
| Discord bot | `os-discord` | 8765 | Primary human interface |
| Operator | `os-operator` | 8091 | Scheduled tasks, cron |
| Webhook | `os-webhook` | 8080 | Inbound webhook handler |

**Docker note:** Use `docker restart <container_name>`, not
`docker compose restart <service>`. Container names are set via
`container_name:` in compose.yml.

**Python-only changes:** Bind-mounted. `docker restart` picks them up.
No Docker rebuild needed.

---

## 5. Sync Ritual (Operating Discipline)

### Before starting work on any device

```bash
# From VPS (canonical):
cd /opt/OS && git pull origin main

# From Windows (via terminal):
cd dev\OS && git pull origin main
```

### After completing work on any device

```bash
git add <specific-files>
git commit -m "lowercase imperative description"
git push origin main
```

### Full cross-device sync check

```bash
scripts/sync_all.sh --dry-run    # see what's out of sync
scripts/sync_all.sh --pull       # fast-forward behind clones
```

### Rules

1. **Push before stepping away.** No device holds unique commits
   overnight.
2. **Pull before starting work.** Stale checkouts cause unnecessary
   merge conflicts.
3. **Never force-push main.** Solo founder phase, but the discipline
   matters.
4. **Fast-forward only for sync pulls.** If a pull can't fast-forward,
   something diverged — investigate before merging.
5. **Push from the device that did the work.** Don't pull from device A
   and push as device B.

### Automation

Two mechanisms keep surfaces in sync automatically:

| Mechanism | Trigger | Latency | Covers |
|-----------|---------|---------|--------|
| **`post-merge` hook** | Every `git merge` / `git pull` on VPS | Instant (background) | Pulls from origin, merges on VPS |
| **Cron `*/30`** | Every 30 minutes | ≤30 min | Pushes from Windows, GitHub Actions, any non-VPS origin |

Both run `sync_all.sh --pull` (fast-forward only, refuses dirty/non-ff).
Both log to `logs/sync_all.log`.

**What's still manual:** `git push origin main` after a VPS merge. Git
has no client-side `post-push` hook, so the post-merge hook fires before
the push has landed on origin. The cron catches it within 30 minutes, or
run `sync_all.sh --pull` manually after pushing.

**Install/verify:**
```bash
scripts/install_sync_automation.sh           # install hook + cron
scripts/install_sync_automation.sh --check   # verify without changes
```

Canonical config tracked in repo:
- `scripts/hooks/post-merge` — hook content (symlinked into `.git/hooks/`)
- `scripts/cron/sync_all.cron` — cron entry
- `scripts/install_sync_automation.sh` — idempotent installer

### Bootstrapping a new VPS

After cloning the OS repo to a new VPS:

```bash
cd /opt/OS
scripts/install_sync_automation.sh   # hook + cron
scripts/sync_all.sh --dry-run        # verify connectivity
```

---

## 6. Operational Lessons (System Properties)

These are hard-won patterns from Layer 1 codebase sync. They apply to
all future cross-device operations.

### Delete + reclone over rename

When a clone has no unique work (strict ancestor of canonical), the
correct consolidation is delete + reclone, not rename. Renames on
Windows hit kernel handle locks on `.git/` internals, `.venv/`
symlinks, and other OS-managed files. A fresh `git clone` is atomic,
lock-proof, and symlink-safe.

### Stop cleanly on unexpected failure

When an automated operation hits unexpected failure, the system must:
1. Stop immediately (no push-through)
2. Report state accurately (what succeeded, what failed, what's at risk)
3. Propose a sound recovery path

Heroic push-through that compounds damage is the failure mode to avoid.
The robocopy `/MOVE` incident is canonical: the flag deletes source
files after copying, so a killed mid-operation robocopy destroyed the
source repo.

### Escalate strategies, accept gracefully when blocked

For stubborn system-level problems (kernel handle locks, permission
errors), try an escalation ladder of strategies. If all fail, document
the residue and the system-standard resolution mechanism (e.g., reboot,
`PendingFileRenameOperations` registry). Don't force-kill blindly.

### Post-merge hook + cron beats post-push

Git has no client-side `post-push` hook. The natural instinct is to sync
after push, but you can't hook that event. The correct design:
`post-merge` hook for instant propagation after pulls/merges (the
receiving side), plus a cron safety net for everything else. Accept that
VPS-originated merges have a manual push step before sync propagates —
this matches Rule 5 anyway.

### Windows-specific gotchas

- `.venv/` symlinks confuse robocopy — use `git clone` instead
- Kernel handles on directories survive process kill, Explorer restart,
  and .NET `Directory.Delete(path, true)`
- `PendingFileRenameOperations` registry is the standard mechanism for
  stubborn locked files/directories
- SSH PowerShell: `$_` variables get escaped by SSH before PowerShell
  sees them. Use `-EncodedCommand` with Base64 UTF-16LE encoding.
- Git binary path: `"C:\Program Files\Git\cmd\git.exe"` (quotes required)

### Capability gap tracking

Anything that ever required manual operator action gets logged as a
sync ritual capability gap until automated. Current gaps:

| Gap | Workaround | Status |
|-----|-----------|--------|
| Dead `dev\OSv2` directory shell | `rmdir /S /Q` after reboot | Cosmetic, non-blocking |
| ~~Manual sync ritual triggering~~ | ~~Run sync_all.sh by hand~~ | **Resolved** — post-merge hook + cron (see `scripts/install_sync_automation.sh`) |

---

## 7. Archive Locations

| Archive | Path | Contents | Date |
|---------|------|----------|------|
| March 2026 CRM data | Windows `dev\_archive_march_2026_crm\` | 52 files: leads, outreach messages, ICP insights, content ideas | Archived 2026-05-20 |
| Deleted branch SHAs | VPS `/root/.claude/jobs/a15ec24a/deleted_branches_shas.txt` | 12 branch SHAs for rollback | 2026-05-20 |

---

## 8. Reference: Tailscale Network

| Device | IP | Hostname |
|--------|-----|----------|
| VPS | `100.77.233.50` | srv1500858 |
| Windows | `100.74.199.102` | desktop-lvguiq9 |
| iPhone | Mesh-assigned | — |
| iPad | Mesh-assigned | — |

All inter-device communication uses Tailscale IPs. No public ports
exposed. SSH key auth on all paths.
