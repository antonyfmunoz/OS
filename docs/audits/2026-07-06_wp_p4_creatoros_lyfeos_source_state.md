# CreatorOS / LyfeOS Source Stabilization — Recon + WIP Preservation

**Packet:** WP-P4-CREATOROS-LYFEOS-SOURCE-STATE-001
**Date:** 2026-07-06
**Scope:** Reconnaissance + preservation ONLY. No feature work. No destructive git operations.
**Ground truth:** Projection source of truth lives on the Beast (`C:\dev\dev\`). /opt/OS holds mirrors/snapshots only (Node Role Discipline).

---

## 1. Beast repo state (read-only recon)

### CreatorOS (`C:\dev\dev\CreatorOS`)

| Item | Value |
|---|---|
| Branch | `main`, up to date with `origin/main` |
| HEAD | `139e2c9` chore(secrets): standardize 1Password runtime references |
| Remote branches | `origin/main`, `origin/Development`, `origin/chore/secrets-1password-runtime` |
| Dirty files | 1 untracked: `dump (1).sql` |
| Repo hazards | None — no mid-merge, no detached HEAD, no submodules |

Recent log:

```
139e2c9 chore(secrets): standardize 1Password runtime references
ca4e161 fix: single-stage build to preserve vite for runtime import
e752965 fix: add VITE_CLERK_PUBLISHABLE_KEY to Dockerfile build args
bf10c7b bind to 0.0.0.0 for fly.io proxy access
5638596 fix fly.toml internal_port to match app default 3000
```

### LyfeOS (`C:\dev\dev\LyfeOS`)

| Item | Value |
|---|---|
| Branch (before preservation) | `main`, up to date with `origin/main` |
| HEAD (before preservation) | `6ce1ae3e` chore(secrets): standardize 1Password runtime references |
| Local branches | `main`, `backup/beast-source-20260705-1341` (yesterday's safety branch, also on origin) |
| Remote branches | `origin/main`, `origin/Development`, `origin/backup/beast-source-20260705-1341`, `origin/chore/secrets-1password-runtime` |
| Dirty files | 24 modified tracked + 4 untracked |
| Repo hazards | None — no mid-merge, no detached HEAD, no `.gitmodules` |

---

## 2. Dirty-file classification

### CreatorOS — `dump (1).sql` → DISPOSABLE ARTIFACT

Evidence:

- 17,531 bytes, file date **2026-03-30 19:28** — over three months stale.
- Filename carries a browser-download duplicate suffix `(1)`.
- Header confirms it is a raw `pg_dump` output (PostgreSQL 16.10), not source:

```
--
-- PostgreSQL database dump
--
-- Dumped from database version 16.10
-- Dumped by pg_dump version 16.10
```

- Untracked only — `git diff --stat` is empty; zero tracked modifications in the repo.

**Classification: disposable artifact (stale DB dump download). NOT discarded** — left in place per packet rules. Disposal is a separate operator decision (it contains database data and should be deleted, not committed).

### LyfeOS — 24 modified files → REAL WIP (Firebase → Clerk auth migration)

`git diff --stat` totals: **24 files, +282 / −1,147**. The shape is unambiguous — a Firebase-to-Clerk authentication migration:

```
server/routes/auth.ts                              | 863 +-------------------- (custom auth gutted)
client/src/pages/VerifyEmailPage.tsx               | 124 +--
client/src/pages/ProfilePage.tsx                   |  96 +--
client/src/pages/ResetPasswordPage.tsx             |  92 ++-
client/src/pages/ForgotPasswordPage.tsx            |  35 +-
server/notificationScheduler.ts                    |  67 +-
client/src/lib/authContext.tsx                     |  12 +-
... (17 more: layout, onboarding, middleware, storage, schema, tests)
```

Corroborated by the two untracked migration docs (below), both dated 2026-07-05.

### LyfeOS — 4 untracked files

| File | Size / date | Classification |
|---|---|---|
| `FIREBASE_TO_CLERK_MIGRATION.md` | 17,705 B, 2026-07-05 | **Real WIP** — migration design doc. Preserved in commit. |
| `MIGRATION_VERIFICATION_CHECKLIST.md` | 18,375 B, 2026-07-05 | **Real WIP** — verification checklist. Preserved in commit. |
| `dump.sql` | 182,162 B, 2026-03-30 | **Disposable artifact** — stale pg_dump (PostgreSQL 16.10 header), same vintage as the CreatorOS dump. NOT committed (DB data does not belong in git). Left untouched on disk. |
| `.env.tpl` | 697 B, 2026-06-21 | **SECURITY DEBT — contains RAW plaintext secrets** (Neon DATABASE_URL with password, SESSION_SECRET, Google OAuth client secret) mixed with two op:// URIs. **NOT committed** — committing would violate the Credential Injection Law. Left untouched on disk. See deferred debt. |

---

## 3. LyfeOS WIP preservation (the only mutation performed on Beast)

Repo state was verified safe first (on `main`, no merge/rebase in progress, no detached HEAD, no submodules). Exact commands executed:

```
cd /d C:\dev\dev\LyfeOS
git switch -c wip/2026-07-06-preserve
git add client/src/components/dailyInit/DailyInitModal.tsx \
        client/src/components/layout/RootLayout.tsx \
        client/src/components/layout/Sidebar.tsx \
        client/src/lib/authContext.tsx \
        client/src/lib/context.tsx \
        client/src/pages/CeremonyPage.tsx \
        client/src/pages/DashboardPage.tsx \
        client/src/pages/ForgotPasswordPage.tsx \
        client/src/pages/OnboardingPage.tsx \
        client/src/pages/ProfilePage.tsx \
        client/src/pages/ResetPasswordPage.tsx \
        client/src/pages/VerifyEmailPage.tsx \
        scripts/seed-demo-user.ts \
        server/notificationScheduler.ts \
        server/replit_integrations/chat/routes.ts \
        server/routes/auth.ts \
        server/routes/content.ts \
        server/routes/documents.ts \
        server/routes/middleware.ts \
        server/routes/profile.ts \
        server/routes/quests.ts \
        server/storage.ts \
        shared/schema.ts \
        tests/api-auth.test.ts \
        FIREBASE_TO_CLERK_MIGRATION.md \
        MIGRATION_VERIFICATION_CHECKLIST.md
git commit -m "wip: preserve uncommitted work before stabilization"
```

Result:

- Commit **`b4bdb42a`** on branch **`wip/2026-07-06-preserve`** — 26 files changed, +803 / −1,147.
- Explicit file list staged — `git add -A` was NOT used. `.env.tpl` and `dump.sql` deliberately excluded.
- Working tree content is byte-identical to before; post-commit `git status --porcelain` shows only the two intentionally excluded untracked files (`.env.tpl`, `dump.sql`).
- **No push** (per hard rules). Branch is local to Beast; commit `b4bdb42a` is the recovery point.
- Repo is left checked out on `wip/2026-07-06-preserve`. Recovery of the pre-packet view: the WIP is now `git show wip/2026-07-06-preserve`; `main` still points at `6ce1ae3e`.

No `reset`, `clean`, `stash`, `checkout --`, force op, or push was executed. CreatorOS received zero mutations.

---

## 4. 1Password runtime verification (green)

| Check | Result |
|---|---|
| `op` CLI on Beast | Present — `C:\Program Files\1Password CLI\op.exe` |
| `op vault list` | 4 vaults accessible: **CreatorOS**, **EntrepreneurOS**, **LyfeOS**, **UMH-Production** (titles only; no item values read) |
| `CreatorOS\.env.op.tpl` | Exists — 3 assignments, **all op:// URIs** (WP-P4-SECRETS-001 header) |
| `LyfeOS\.env.op.tpl` | Exists — 6 assignments, **all op:// URIs** (WP-P4-SECRETS-001 header) |
| `EntrepreneurOS\.env.op.tpl` | Exists — 11 assignments, **all op:// URIs** (WP-P4-SECRETS-001 header) |

Verification method: counted assignment lines vs op:// lines per file; the single non-op line in each is the `# Managed by 1Password ... op run --env-file=...` header comment. No resolved secret values were printed. The `op run --env-file=.env.op.tpl` runtime pattern is intact for all three apps.

Note: LyfeOS's stray `.env.tpl` (raw secrets, 2026-06-21) is a **legacy pre-vaulting leftover**, distinct from the canonical `.env.op.tpl` — see deferred debt.

---

## 5. Real app body vs snapshot mirror maps

### CreatorOS

**Real body — Beast `C:\dev\dev\CreatorOS` (full repo, full git history):**

- App code: `client/` (React 18 + Vite + Tailwind), `server/` (Express, entry `server/index.ts`), `shared/` (`shared/schema.ts` — Drizzle ORM schema), `scripts/`, `migrations/`
- Build/deploy: `package.json` (`dev`: `tsx server/index.ts`; `build`: `vite build && esbuild server/index.ts → dist/`; `start`: `node dist/index.js`; `db:push`: drizzle-kit), `Dockerfile`, `fly.toml`, `vite.config.ts`, `drizzle.config.ts`, `tsconfig.json`, `tailwind.config.ts`
- Secrets: `.env.op.tpl` (pure op:// template, CreatorOS vault)
- Local-only bulk: `node_modules/`, `dist/`, `attached_assets/`, `uploads/`, `AUDIT_AUTH.md`, `dump (1).sql` (disposable)

**Mirror — VPS `/opt/OS`:**

- `/opt/OS/data/repos/creatoros` — **14-file config/schema snapshot** (no `.git`, no client/server code): `shared/schema.ts`, `package.json`, `package-lock.json`, `drizzle.config.ts`, `vite.config.ts`, `tsconfig.json`, `tailwind.config.ts`, `postcss.config.js`, `theme.json`, `.replit`, `replit.nix`, `.gitignore`, `generated-icon.png`, `scripts/seed-db.ts`
- `/opt/OS/projections/creatoros/integration/` — UMH projection integration shell (signals, handlers, manifest, outcomes, correlation, tables) — substrate-side code, not app source
- `/opt/OS/data/umh/creatoros_lossless_canon/` + `trinity_convergence/` — phase-14 canon/convergence JSON artifacts (knowledge snapshots, not source)

### LyfeOS

**Real body — Beast `C:\dev\dev\LyfeOS` (full repo, full git history):**

- App code: `client/` (React 18 + Vite + Tailwind), `server/` (Express, entry `server/index.ts`; `server/routes/`, `server/storage.ts`, `server/notificationScheduler.ts`, `server/replit_integrations/`), `shared/` (`shared/schema.ts`, `shared/models/chat.ts`), `scripts/`, `migrations/`, `tests/` (vitest)
- Build/deploy: `package.json` (same script shape as CreatorOS: tsx dev, vite+esbuild build, `dist/index.js` start, drizzle-kit push), `Dockerfile`, `fly.toml`, `build.sh`, `vite.config.ts`, `vitest.config.ts`, `drizzle.config.ts`
- Secrets: `.env.op.tpl` (pure op:// template, LyfeOS vault); stray legacy `.env.tpl` (raw secrets — debt)
- WIP: Firebase→Clerk migration, preserved on `wip/2026-07-06-preserve` (`b4bdb42a`); safety branch `backup/beast-source-20260705-1341` also exists locally and on origin
- Local-only bulk: `node_modules/`, `dist/`, `attached_assets/`, `dump.sql`, `cookies.txt`, `cookies2.txt`

**Mirror — VPS `/opt/OS`:**

- `/opt/OS/data/repos/LYFEOS` — **23-file config/schema/tests snapshot** (no `.git`, no client/server code): `shared/schema.ts`, `shared/models/chat.ts`, `tests/api-auth.test.ts`, `tests/xp-calculations.test.ts`, `scripts/` (3 files), `package.json`, `package-lock.json`, build/config files, `replit.md`, plus **`cookies.txt` / `cookies2.txt`** (should not be on the VPS mirror — debt)
- `/opt/OS/projections/lyfeos/integration/` — UMH projection integration shell (same 7-module shape as creatoros)
- `/opt/OS/data/umh/trinity_convergence/phase14_6b_lyfeos/` + convergence/stack JSONs — knowledge snapshots, not source

**Mirror tier verdict:** both `/opt/OS/data/repos/*` snapshots exceed the Node Role Discipline target ("shared/schema.ts ONLY") but are inert config-level mirrors — no app body, no git history. The mirror-vs-body boundary is intact: nothing on the VPS can be mistaken for source of truth.

---

## 6. Deferred debt (not actioned in this packet)

1. **LyfeOS `C:\dev\dev\LyfeOS\.env.tpl`** — raw plaintext secrets on disk (Neon DB URL+password, SESSION_SECRET, Google OAuth client secret). Should be: values confirmed vaulted in the LyfeOS 1Password vault, file deleted, secrets rotated (they have lived unvaulted on disk since 2026-06-21). Owner: secrets follow-on packet.
2. **Stale pg_dumps** — `CreatorOS\dump (1).sql` (17.5 KB) and `LyfeOS\dump.sql` (182 KB), both 2026-03-30. Contain database data; should be deleted after operator confirms no recovery value.
3. **`cookies.txt` / `cookies2.txt`** — present in the Beast LyfeOS repo dir AND in the VPS mirror `/opt/OS/data/repos/LYFEOS`. Possible session cookies; should be inspected and purged from both nodes.
4. **VPS mirror over-scope** — `/opt/OS/data/repos/{creatoros,LYFEOS,entrepreneuros}` carry more than `shared/schema.ts` (Node Role Discipline). Trim in a mirror-hygiene packet.
5. **LyfeOS WIP branch is local-only** — `wip/2026-07-06-preserve` exists only on Beast (pushes from Beast were out of scope). If off-Beast durability is wanted, the operator can push it: `git push -u origin wip/2026-07-06-preserve`.
6. **LyfeOS repo left on `wip/2026-07-06-preserve`** — intentional (keeps working tree identical). Returning to `main` is safe once the migration WIP resumes, since the WIP is committed.

---

## 7. Rollback

- **Beast LyfeOS:** the packet's only mutation is additive — one local branch + one commit. To undo entirely: `git switch main && git branch -D wip/2026-07-06-preserve` (would restore the previous *risk*, not recommended). The working tree was never altered.
- **Beast CreatorOS:** zero mutations; nothing to roll back.
- **/opt/OS:** this document is the only change; revert the commit to roll back.
