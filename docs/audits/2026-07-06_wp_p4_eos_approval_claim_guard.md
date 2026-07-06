# WP-P4-EOS-APPROVAL-CLAIM-GUARD-001 — Packet Record

Date: 2026-07-06
Repo touched: `antonyfmunoz/EntrepreneurOS` (Beast, isolated worktree)
App PR (draft): https://github.com/antonyfmunoz/EntrepreneurOS/pull/4
Branch: `fix/approval-claim-guard` @ `1fc338f0725546c6c03dd04aecde6d3ecee94740`
(base: `feature/company-system` @ `9c8725f`)

## Defect (W2, from PR #196 deep inventory)

EntrepreneurOS `POST /api/actions/:id/approve` (`server/routes/actions.ts`)
approved via `updateAction` (`server/storage.ts`), which updates
`WHERE id = ?` with **no status claim guard**, then fired
`executeAction(...)` unconditionally:

- Double-approve (double-click, client retry, two tabs, replayed request)
  **re-fires effects** — for `send_email` that is a second real email through
  the user's connected Gmail.
- The reject path had the same unguarded write.
- It races UMH's atomic approval seam: UMH-side
  `update_action_decision` (`/opt/OS/projections/eos/integration/tables.py`)
  claims with `WHERE id = %s AND status = 'pending' ... RETURNING`, so UMH and
  the app could both "win" a decision on the same row.

## Claim design (mirrors UMH doctrine)

One new storage method, two route changes. No schema migration.

1. `IStorage.claimPendingAction(id, updates)` + `DatabaseStorage`
   implementation (`server/storage.ts`): Drizzle conditional update

   ```ts
   db.update(agentActionsTable)
     .set(updateData)
     .where(and(
       eq(agentActionsTable.id, id),
       eq(agentActionsTable.status, "pending")
     ))
     .returning();
   ```

   Returns the claimed row, or `undefined` when the row is no longer pending.
   This is the app-side twin of UMH's `AND status = 'pending'` predicate — the
   ONLY legal route-level transitions are pending→approved and
   pending→rejected, enforced atomically in the database.

2. `POST /api/actions/:id/approve` (`server/routes/actions.ts`):
   - claims pending→approved (stamping `approvedBy`/`approvedAt` in the same
     atomic write);
   - on claim failure: **409 Conflict** with
     `{ message, status: <current status> }`, and **no effects fired**;
   - on claim success only: `executeAction(claimed)` — the executor now
     receives the claimed DB row (previously a hand-built
     `{ ...action, status: "approved" }` spread).

3. `POST /api/actions/:id/reject`: same claim for pending→rejected; 409 with
   current status when not pending; returns the claimed row on success.

Deliberately NOT changed:

- `updateAction` stays as-is — the executor's internal lifecycle transitions
  (approved→executing→completed, or →failed / →pending-for-retry) are
  sequential self-transitions inside `executeAction`, not operator decisions.
- The executor's retry path resets a failed action to `pending`
  (`retryCount < maxRetries`); a fresh approve after failure is a legitimate
  new claim, and the guard permits exactly that.

## Diff summary (2 files, +40/−4)

- `server/storage.ts`
  - `IStorage`: added `claimPendingAction(id, updates)` declaration.
  - `DatabaseStorage`: added `claimPendingAction` next to `updateAction`
    (single `IStorage` implementation in the repo — verified).
- `server/routes/actions.ts`
  - approve route: `updateAction` → `claimPendingAction`; added 409 branch;
    `executeAction(claimed)`.
  - reject route: `updateAction` → `claimPendingAction`; added 409 branch.

Response-shape compatibility: success shapes unchanged (approve returns the
executor result `{ success, result?, error? }`; reject returns the updated
row). **Deliberate change:** non-pending actions now get 409 instead of a
silent re-approve + re-execute (previously 200 with duplicated effects).

## Verification (per packet safety constraints — no app run, no prod DB)

- Isolated worktree `C:\dev\dev\EntrepreneurOS-wt-claimguard` on new branch;
  the RUNNING tree (`feature/company-system` @ `9c8725f`) was never touched,
  never switched (`git status` clean before and after; only the worktree was
  modified).
- `node_modules` junctioned read-only from the main tree (no install).
- `tsc --noEmit --incremental false` run in BOTH the worktree and the
  unmodified main tree; outputs compared with `fc`: **byte-identical** →
  zero new type errors introduced by this change.
- Zero errors in either run reference `server/` — the repo's pre-existing
  type errors are all client-side and untouched.
- Code-level assertions: `eq`/`and` already imported in `storage.ts`;
  `claimPendingAction` is the only new symbol; all three `updateAction`
  call sites inside `action-executor.ts` intentionally left on the
  unconditional path (see design).
- Coordinate-free zone respected: no edits anywhere near
  `initSampleData` in `storage.ts` (the fix/destructive-boot-guard packet's
  region); this packet touched the `updateAction` region (~line 1363) and the
  interface block (~line 147) only. No overlap expected.

## Rollback

- App not redeployed by this packet — the running app still serves
  `feature/company-system` @ `9c8725f`. Nothing to roll back in production.
- To discard: close draft PR #4, `git push origin --delete
  fix/approval-claim-guard`, `git worktree remove
  C:\dev\dev\EntrepreneurOS-wt-claimguard` (junctioned `node_modules` inside
  it is a junction — removal does not delete the main tree's modules).
- If merged and a revert is needed: `git revert 1fc338f` — the change is
  additive (new method + guarded routes), no schema or data migration.

## Deferred debt

- The repo's pre-existing client-side `tsc` errors (Header/LeftRail props,
  react-query typings, implicit anys) — untouched, out of scope.
- `executeAction`'s own transitions (`approved→executing`) remain
  unconditional `updateAction` writes; a UMH-side executor claiming the same
  row between app-claim and app-execute is still theoretically racy at the
  execution (not approval) seam. The approval seam — where real-world effects
  are triggered — is now atomic on both sides. An execution-claim
  (`WHERE status = 'approved'` on the executing transition) is a candidate
  follow-on packet.
- No unit test added: the repo has no DB-free test harness for storage
  (Drizzle is bound to the live `db` client at module load), and the packet
  forbids running tests against the production `DATABASE_URL`. A testable
  seam (injectable db) is follow-on debt.
- Beast worktree `EntrepreneurOS-wt-claimguard` left in place until the PR
  is merged or closed; remove it after decision.
