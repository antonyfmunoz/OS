# WP-P4-EOS-DESTRUCTIVE-BOOT-GUARD-001 — Packet Record

Date: 2026-07-06
Repo affected: `antonyfmunoz/EntrepreneurOS` (app repo, executor node `C:\dev\dev\EntrepreneurOS`)
This doc: packet record in the OS repo. No OS runtime code changed by this packet.

## Defect (W1, from PR #196 deep inventory)

`server/storage.ts` — `DatabaseStorage`'s constructor calls `initSampleData()`
on every process start (lines 161-167 at base commit `9c8725f`). The seed logic
(lines ~260-286) checked for an agent with `role === 'executive'`. If agents
existed but none was executive, it:

1. Deleted every agent's tasks (`db.delete(tasksTable).where(agentId = ...)`)
2. Deleted every agent's messages (`db.delete(messagesTable).where(agentId = ...)`)
3. Deleted ALL agents (`db.delete(agentsTable)` — unqualified)
4. Re-seeded sample data

No HTTP request, no auth, fires on process start, against the production
`DATABASE_URL`. Any state where the executive agent row was renamed, re-roled,
or removed meant the next boot silently destroyed all agents, tasks, and
messages in production.

## Guard design (as shipped)

1. **Insert-only seeding, empty-DB gate.** Sample data is seeded only when the
   database is genuinely empty: zero agents AND zero tasks AND zero messages
   (`databaseIsEmpty`). Seeding never deletes anything.
2. **Legacy destructive path behind an explicit flag.** The wipe+re-seed runs
   only when `process.env.ALLOW_DESTRUCTIVE_RESEED === 'true'`, and emits a
   loud multi-line `console.error` stating exactly how many agents, tasks, and
   messages it is about to delete, plus an instruction to unset the flag after
   the boot.
3. **Safe default when executive agent is missing but other data exists:**
   `console.warn`, then insert ONLY the missing executive agent — a pure
   FK-safe INSERT into `agents` (no child-table rows referenced). If the id
   `agent_executive` is already taken by a non-executive row, it refuses even
   that insert and makes no changes. Insert failure is caught and logged,
   never fatal.

## Exact diff summary

- Branch: `fix/destructive-boot-guard` (worktree
  `C:\dev\dev\EntrepreneurOS-wt-bootguard`, base `feature/company-system`
  @ `9c8725f`)
- Commit: `0f88507` — `fix(boot): never destructively re-seed on startup
  (WP-P4-EOS-DESTRUCTIVE-BOOT-GUARD-001)`
- One file, one hunk: `server/storage.ts` (+80 / −23), all inside
  `initSampleData()`. The unconditional delete block was replaced with:
  - `databaseIsEmpty` computed from agents + tasks + messages counts
  - steady-state early return (data present + executive present)
  - `ALLOW_DESTRUCTIVE_RESEED === 'true'` branch containing the ONLY deletes,
    with loud error logging, falling through to the insert-only seed
  - default branch: warn + insert only the missing executive agent, return
- Draft PR (app repo): https://github.com/antonyfmunoz/EntrepreneurOS/pull/3

## Verification performed

- **Isolation:** work done in a dedicated git worktree
  (`git worktree add C:\dev\dev\EntrepreneurOS-wt-bootguard -b fix/destructive-boot-guard`);
  the running checkout on `feature/company-system` was never touched, no
  branch switches, no resets/stashes.
- **Transfer integrity:** file edited on the VPS, uploaded via base64 +
  `certutil -decode`; `git hash-object` on both sides matched
  (`945228223965a0e45ac6c5bc7360b4bdd32369bb`) before commit.
- **TypeScript:** `npm run check` (`tsc`) with node_modules junctioned
  read-only from the main checkout — 104 pre-existing errors at base
  `9c8725f`, 104 on the branch (delta zero), and zero errors referencing
  `server/storage.ts`.
- **Code-level assertions:** within `initSampleData()`, every `db.delete`
  call sits inside the `ALLOW_DESTRUCTIVE_RESEED === 'true'` branch; the
  seed inserts are reachable only when `databaseIsEmpty` or via that gated
  branch; the default missing-executive path performs a single INSERT.
- **Not run against any database.** No app start, no live seed, no schema
  migration. Explicit file staging only (`git add server/storage.ts`).

## Rollback

- App repo: delete branch `fix/destructive-boot-guard`
  (`git push origin --delete fix/destructive-boot-guard`;
  `git -C C:\dev\dev\EntrepreneurOS branch -D fix/destructive-boot-guard`)
  and remove the worktree
  (`git -C C:\dev\dev\EntrepreneurOS worktree remove C:\dev\dev\EntrepreneurOS-wt-bootguard --force`).
- OS repo: close the packet-record PR; no runtime surface changed.

## Deferred debt

- 104 pre-existing TypeScript errors on `feature/company-system` (all in
  `client/src/pages/*`, mostly `workflows-page.tsx` react-query typing).
  Untouched by this packet; needs its own cleanup packet before `tsc` can be
  a merge gate on the app repo.
- Constructor-time seeding is still a side effect of `new DatabaseStorage()`.
  The guard makes it non-destructive, but proper fix is an explicit,
  operator-invoked seed script (e.g. `npm run db:seed`) and a constructor
  that does nothing but connect.
- `ALLOW_DESTRUCTIVE_RESEED` is a process-env kill switch, not audited or
  time-boxed. If ever used, it must be set for one boot and removed; nothing
  enforces that mechanically yet.
- The app repo has no unit-test runner (`package.json` has no `test` script);
  the guard has no automated regression test. Candidate: extract
  `initSampleData`'s decision logic into a pure function and test it.
- Sample-data inserts still hardcode ids (`task_1`..`task_5`,
  `integration_1`..`integration_3`); on a genuinely empty DB this is fine,
  but the destructive-flag path could collide with surviving integration
  rows (integrations are not wiped by the legacy path — pre-existing
  behavior, unchanged).
