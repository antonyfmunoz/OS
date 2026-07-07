# LyfeOS / CreatorOS Feature Clusters + Pre-Build Checklist

**Packet:** WP-P4-LYFEOS-CREATOROS-FEATURE-CLUSTERS-001
**Date:** 2026-07-06
**Scope:** Recon + planning only. Docs-only change on /opt/OS. Beast was READ-ONLY this packet (git log/status/diff --stat, dir, type, findstr — zero mutations of any kind).
**Builds on:** `docs/audits/2026-07-06_wp_p4_creatoros_lyfeos_source_state.md` (PR #189) — repo state, dirty-file classification, WIP preservation (`wip/2026-07-06-preserve` @ `b4bdb42a`), 1Password verification, and mirror maps live THERE and are not repeated here.

---

## 1. Terminology correction (binding for future packets)

These repos are **NOT "dormant"**. Correct language:

| Repo | Correct state term | Meaning |
|---|---|---|
| LyfeOS (`C:\dev\dev\LyfeOS`) | **source-dirty** | Real uncommitted WIP existed (now preserved on a Beast-local branch); active migration mid-flight; repo checked out on `wip/2026-07-06-preserve` |
| CreatorOS (`C:\dev\dev\CreatorOS`) | **source-current** | `main` == `origin/main`, zero tracked modifications; only debris is one stale untracked pg_dump |
| Both, on the VPS | **schema-only mirrored** | `/opt/OS/data/repos/*` holds inert config/schema snapshots — no app body, no `.git`. Nothing on the VPS is source of truth. |

"Dormant" implies abandoned code that nothing depends on. Both apps are complete, deployable products (Dockerfile + fly.toml + full client/server bodies) whose source of truth is the Beast per Node Role Discipline. Use *source-dirty / source-current / schema-only mirrored* in all future packet language.

---

## 2. New ground-truth finding: the Clerk migration is mostly COMMITTED

The prior increment characterized the LyfeOS dirty state as "Firebase→Clerk migration WIP." Recon this packet sharpens that materially — **the bulk of the migration already landed on `main`**:

```
6ce1ae3e chore(secrets): standardize 1Password runtime references   (HEAD of main)
536b8888 add optional avatarUrl field to users table schema
0ca85f31 add CLERK_SECRET_KEY startup check
...
18432cba remove firebase dependencies and clean up env              (committed earlier)
a89d913b rewrite auth context to use Clerk                          (committed earlier)
```

Evidence of committed-state progress (all read-only checks on Beast):

- `package.json` contains **zero** firebase dependencies (case-insensitive findstr: no match); `@clerk/clerk-react ^5.61.8` + `@clerk/express ^2.1.30` present.
- `client/src/lib/firebase*.ts` — **gone** (deleted in committed history).
- `server/firebaseAdmin.ts` — **gone**; `server/clerkAdmin.ts` exists (the planned rewrite happened).
- `server/routes/auth.ts` is now 308 lines with 12 Clerk references — the preserved WIP commit is what gutted the 1,171-line custom auth file (−863 lines).

So the preserved branch `wip/2026-07-06-preserve` (`b4bdb42a`, 26 files, +803/−1,147) is the **tail-end cleanup pass** of an already-landed migration, not the migration itself. Remaining Firebase footprint is FCM-only: 1 reference in `server/notificationScheduler.ts`, 1 in `client/src/hooks/usePushNotifications.ts` — pending the migration doc's unresolved **Option A (keep FCM) vs Option B (Web Push API)** decision.

**Consequence for planning:** resuming LyfeOS is not "restart a migration" — it is "review + land one cleanup branch, then decide the FCM question."

---

## 3. LyfeOS feature-cluster map

Source body: `client/` (React 18 + Vite + wouter routing, 42 pages), `server/` (Express; 9 registered route groups via `server/routes.ts` shim), `shared/schema.ts` (Drizzle, 1,449 lines, **35 pgTable definitions**), `server/storage.ts` (2,333 lines, single storage layer), `tests/` (5 vitest files).

Completeness legend — assessed from **source state only** (static recon; no runtime was started this packet):
**working** = committed on main, coherent, no WIP touch · **WIP** = touched by the preserved Clerk branch · **stub** = visibly incomplete in source.

| # | Cluster | What it does | Key source files | Schema domains | Completeness | Clerk-WIP touches it? |
|---|---|---|---|---|---|---|
| 1 | **Auth & identity** | Clerk-based sign-in/up, email verify, password reset, session middleware | `server/routes/auth.ts` (308 ln, 7 endpoints), `server/routes/middleware.ts` (184 ln), `server/clerkAdmin.ts`, `client/src/lib/{authContext.tsx,clerk.ts}`, pages: Login, Register, VerifyEmail, ForgotPassword, ResetPassword, LoginSuccess | `users`, `userIntegrations` | **WIP** — core landed on main; tail-end cleanup on preserved branch | **YES — epicenter** (auth.ts −863, VerifyEmail, ResetPassword, ForgotPassword, ProfilePage, authContext, middleware, api-auth.test.ts) |
| 2 | **Onboarding & ceremony** | New-user onboarding flow, daily-init ceremony ritual | pages: Onboarding, Ceremony; `client/src/components/dailyInit/` (DailyInitModal) | `userProfile`, `userDailyLogs` | **WIP** (auth-coupled edits) | YES (OnboardingPage 26 ln, CeremonyPage, DailyInitModal 11 ln) |
| 3 | **Dashboard & gamified stats** | Main dashboard; XP/rank system; per-stat detail pages (attention, time, energy, health, wealth, experience, streak, efficiency) | DashboardPage + 9 `*DetailPage.tsx`, `components/{dashboard,stats}/`, `lib/{experienceUtils,ranks,gamified-toast}`, `server/routes/profile.ts` (1,595 ln, 19 endpoints) | `userStats`, `userDailyLogs`, `userActivityEvents`, `widgetStates`, `progressTrackers` | **working** (xp-calculations.test.ts exists) | Marginal (DashboardPage 2 ln, profile.ts 26 ln — auth plumbing only) |
| 4 | **Quests / missions / goals** | Quest lifecycle, mission pages/views, vision goals + archive | pages: Quests, MissionDetail, EnhancedMission, MissionArchive, GoalsArchive; `server/routes/quests.ts` (587 ln, 14 endpoints), `server/routes/goals.ts` (535 ln, 19 endpoints) | `quests`, `missionPages`, `missionViews`, `visionGoals` | **working** | Trivial (quests.ts 2 ln) |
| 5 | **Content & knowledge system** | Journal (Chronilog), timeline, codex, knowledge vault, rituals, canvases/graphs, templates, spreadsheets, media, kanban backing APIs — the app's largest surface | `server/routes/content.ts` (**2,545 ln, 98 endpoints** — biggest route file), pages: Chronilog, Timeline(+Detail), Codex, KnowledgeArchive, JournalArchive, RitualsArchive; `components/{chronilog,timeline,markdown}/` | `canvases`, `graphs`, `folders`, `templates`, `spreadsheets`, `mediaAlbums`, `mediaItems`, `dismissedKnowledge`, `userCategories`, `ritualGroups`, `smartReminders`, `calendarEvents` | **working** | Trivial (content.ts 2 ln) |
| 6 | **Document vault** | Document storage/retrieval UI + API | DocumentVaultPage, `server/routes/documents.ts` (962 ln, 23 endpoints) | `documents`, `folders` | **working** | Trivial (documents.ts 2 ln) |
| 7 | **Kanban** | Boards, columns, tasks | pages: Kanban, KanbanBoard (APIs served from content cluster) | `kanbanBoards`, `kanbanColumns`, `kanbanTasks` | **working** | No |
| 8 | **AI assistant (Nova) + voice** | AI chat page, voice control overlay, nova actions | AIPage, `VoiceOverlay.tsx`, hooks `use-nova-actions`/`use-voice-control`, `server/openai.ts` (72 ln), `server/replit_integrations/chat/` (routes, storage, knowledge-base) + `batch/` | `aiMessages`, `conversations`, `messages` | **working** | Marginal (chat/routes.ts 8 ln) |
| 9 | **Google integration** | Google OAuth + Calendar/Gmail/Drive surface (36 calendar/gmail/drive references) | `server/routes/google.ts` (1,043 ln, 14 endpoints) | `integrations`, `userIntegrations`, `calendarEvents` | **working** (needs runtime re-verify after Clerk lands — OAuth callback coupling) | No |
| 10 | **Notifications / PWA push** | Scheduled push notifications, PWA install, push subscriptions | `server/notificationScheduler.ts` (276 ln), `client/src/hooks/usePushNotifications.ts`, `PWAInstallPrompt.tsx` | `pushSubscriptions` | **WIP / blocked** — FCM Option A vs B undecided; 1 firebase ref remains in each of scheduler + hook | YES (notificationScheduler.ts 67 ln) |
| 11 | **Waitlist / landing / subscription** | Public landing, waitlist capture, subscription page | pages: Landing, Waitlist, WaitlistThankYou, Subscription; `server/routes/waitlist.ts` (25 ln, 1 endpoint) | `waitlistEmails` | Waitlist **working**; **subscription is a stub** — `App.tsx` routes `/subscription` to `LandingPage` (no billing implementation found) | No |
| 12 | **Rolodex / contacts** | Personal CRM page | RolodexPage | `contacts` | **working** (source-coherent) | No |
| 13 | **Analytics** | In-app analytics page | AnalyticsPage | (reads existing stats tables) | **working** (source-coherent) | No |

Cross-cutting: `server/storage.ts` (2,333 ln — WIP touched 10 ln), `shared/schema.ts` (WIP removed 2 ln), `scripts/seed-demo-user.ts` (WIP 3 ln), layout shell `components/layout/` (RootLayout/Sidebar — WIP 8 ln total).

**WIP blast-radius summary:** the preserved branch is concentrated in clusters 1–2 (auth + onboarding) and 10 (notifications). Clusters 3–9 and 11–13 receive only mechanical auth-plumbing edits (2–26 lines each). Landing the WIP branch is an auth-review problem, not a whole-app review problem.

Stray source debris noted (not actioned): `client/src/lib/context.tsx.bak` (backup file committed/on disk next to the real `context.tsx`).

---

## 4. CreatorOS — confirmation pass + coarse clusters

**Confirmation:** re-checked this packet — `main...origin/main` in sync, `git status` shows exactly one untracked file: `dump (1).sql` (the already-classified disposable stale pg_dump). **No source risk beyond it. Zero tracked modifications.** CreatorOS is source-current.

Source body: `client/` (React 18 + Vite, 16 pages, component dirs: ai, communities, explore, feed, layout, marketplace, messages, notifications, profile, ui), `server/` (flat — **one** `routes.ts` at 1,523 ln / 68 endpoints, `storage.ts` 3,034 ln), `shared/schema.ts` (567 ln, **20 pgTable definitions**), `migrations/` (one Drizzle migration), no tests dir. Auth is already Clerk (`@clerk/clerk-react` + `@clerk/express`, `server/{auth.ts,clerkAdmin.ts}`); `openai` dep for AI features; `posthog.ts` for product analytics; `upload.ts` + `/uploads` static serving for media.

Coarse clusters (source-coherent; no per-file completeness pass needed — clean tree):

| # | Cluster | Pages / components | Schema domains |
|---|---|---|---|
| 1 | **Feed & posts** | create-post, new-text-post, explore, saved-posts; `components/{feed,explore}` | `posts`, `savedPosts`, `comments`, `stories`, `taggedUsers` |
| 2 | **Social graph** | followers, following, contacts | `followers`, `contacts` |
| 3 | **Communities & channels** | communities; `components/communities` | `communities`, `channels`, `channelMessages` |
| 4 | **Direct messages** | `components/messages` | `conversations`, `conversationParticipants`, `directMessages` |
| 5 | **Marketplace & monetization** | marketplace, create-product, revenue; `components/marketplace` | `products`, `revenue` |
| 6 | **AI agents & chat** | ai.tsx; `components/ai`; `server/openai` usage | `aiAgents`, `aiChats` |
| 7 | **Documents** | documents.tsx | `documents` |
| 8 | **Profile & auth (Clerk)** | profile, auth-page; `components/profile` | `users` |
| 9 | **Notifications** | `components/notifications` | `notifications` |
| 10 | **Ops/infra** | `server/{upload,posthog,cleanup,db,vite}.ts`, Dockerfile, fly.toml | — |

Architecture note for future stabilization work: CreatorOS concentrates all 68 endpoints in one 1,523-line `routes.ts` and one 3,034-line `storage.ts`; LyfeOS already made the split into per-domain route modules. If CreatorOS route work is ever scheduled, the LyfeOS `server/routes/` shape is the in-family precedent.

---

## 5. Pre-build backup/branch checklist (operator-approvable, run BEFORE any build work on either repo)

Every item below is a precondition to the first build/feature/cleanup commit on either app. Items 1–5 are LyfeOS; 6 is CreatorOS; 7–8 are both. All commands run **on the Beast** (`ssh "antonys beast pc@100.74.199.102"`, cmd.exe) unless marked VPS. Key NAMES only are referenced near secrets — never values.

1. **Push the preserved WIP branch off-Beast** (currently the only copy of commit `b4bdb42a` is Beast-local):
   ```
   cd /d C:\dev\dev\LyfeOS
   git push -u origin wip/2026-07-06-preserve
   ```
   Verify: `git branch -r` lists `origin/wip/2026-07-06-preserve`.

2. **Confirm every key in the plaintext `.env.tpl` is vaulted in 1Password (LyfeOS vault)** before the file is touched. The file holds (names only): a Neon `DATABASE_URL` (with embedded password), `SESSION_SECRET`, Google OAuth client id + client secret, plus two already-vaulted op:// URIs. Check item presence without printing values:
   ```
   op item list --vault LyfeOS
   op item get <item-name> --vault LyfeOS --format json | findstr /i "label"
   ```
   Any key missing from the vault gets created by the operator in the 1Password UI (never via echo on a shell — no values in command lines, per Credential Injection Law).

3. **Rotate the leaked credentials** — they have sat plaintext on disk since 2026-06-21 and must be treated as exposed regardless of vaulting:
   - Neon: reset the database role password in the Neon console; update the `DATABASE_URL` item in the LyfeOS vault.
   - `SESSION_SECRET`: generate a new value, update the vault item (invalidates existing sessions — acceptable pre-launch).
   - Google OAuth: rotate the client secret in Google Cloud Console → Credentials; update the vault item.
   Verify: `op run --env-file=.env.op.tpl -- cmd /c echo env-ok` prints `env-ok` (resolves without printing values).

4. **Delete the plaintext file only after 2 and 3 are green:**
   ```
   del C:\dev\dev\LyfeOS\.env.tpl
   ```
   Verify: `dir /b C:\dev\dev\LyfeOS\.env.tpl` errors with File Not Found; `.env.op.tpl` (the canonical op:// template) remains.

5. **Disposition the untracked non-source files** (operator decision, then delete — none belong in git):
   ```
   del "C:\dev\dev\LyfeOS\dump.sql"
   del C:\dev\dev\LyfeOS\cookies.txt C:\dev\dev\LyfeOS\cookies2.txt
   del C:\dev\dev\LyfeOS\client\src\lib\context.tsx.bak
   ```
   `dump.sql` is a 2026-03-30 pg_dump (DB data — confirm no recovery value first); cookies files are possible session cookies (inspect, then purge). After this, `git status --porcelain` on the wip branch is empty.

6. **CreatorOS equivalent disposition:**
   ```
   del "C:\dev\dev\CreatorOS\dump (1).sql"
   ```
   No branch/backup action needed — `main` is already on origin with a clean tree; that IS the backup. Verify freshness immediately before build work: `git fetch && git status -sb` shows `## main...origin/main` with no divergence.

7. **Tag the pre-build baseline on both repos** (cheap, immutable recovery points; additive only):
   ```
   cd /d C:\dev\dev\LyfeOS   && git tag pre-build-20260706 wip/2026-07-06-preserve && git push origin pre-build-20260706
   cd /d C:\dev\dev\CreatorOS && git tag pre-build-20260706 main                   && git push origin pre-build-20260706
   ```

8. **VPS mirror purge of cookie files** (VPS, /opt/OS): remove `cookies.txt` / `cookies2.txt` from `/opt/OS/data/repos/LYFEOS` (they are neither schema nor config). Fold the wider mirror trim (Node Role Discipline: `shared/schema.ts` only) into a separate mirror-hygiene packet — do not block build work on it.

Gate that is NOT a backup step but blocks resuming the LyfeOS WIP: **decide FCM Option A (keep firebase-admin for messaging only) vs Option B (Web Push API)** — the migration checklist rows 4.10–4.12 / 5.16 hinge on it, and `notificationScheduler.ts` + `usePushNotifications.ts` each still carry one firebase reference.

---

## 6. Deferred debt (carried + new)

Carried from PR #189 (still open): plaintext `.env.tpl` (→ checklist items 2–4), stale pg_dumps (→ items 5–6), cookies files both nodes (→ items 5, 8), VPS mirror over-scope (separate packet), WIP branch Beast-local (→ item 1), repo parked on wip branch (intentional until WIP lands).

New this packet:
1. **FCM Option A/B decision** — blocks final Clerk-migration cleanup (owner: operator decision before the LyfeOS resume packet).
2. **LyfeOS `/subscription` route is a stub** (renders LandingPage; no billing) — product gap to schedule, not a defect.
3. **`context.tsx.bak`** stray backup file in LyfeOS client lib (→ checklist item 5).
4. **CreatorOS god-file shape** — `routes.ts` 1,523 ln / `storage.ts` 3,034 ln; acceptable now, split along the LyfeOS per-domain pattern if route work is scheduled.
5. **Completeness grades are static** — no runtime was started this packet; first LyfeOS build session should smoke `/api/health`, auth round-trip, and the Google OAuth callback before feature work.

---

## 7. Method + rollback

Method: all Beast access read-only over SSH (`git status -sb`, `git log --oneline`, `git diff main..wip/2026-07-06-preserve --stat`, `dir /b`, `type`, `findstr`, `find /c /v ""`). No push, no branch/tag creation, no file writes, no `git add` of any kind on Beast. Endpoint counts = `findstr` matches of `app.get/post/put/patch/delete(` per route file; table counts = `pgTable(` definitions in `shared/schema.ts` (LyfeOS 35, CreatorOS 20).

Rollback: this document is the only change on /opt/OS — revert the commit.
