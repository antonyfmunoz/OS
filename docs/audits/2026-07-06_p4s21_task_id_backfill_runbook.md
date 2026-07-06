# P4S-21 — task_id Backfill: Owner-Approved Live-Data Correction Runbook

Status: **QUARANTINED — compile mode. No write may occur before the owner approval
gate (§12) is explicitly cleared.** Promoted out of Wave-1 auto-mode by operator
ruling 2026-07-06: it touches live EOS executor SQL / `agent_actions.task_id`
lineage, making it a live-data correction packet, not an additive packet.

The packet has TWO distinct parts. They are gated differently:

- **Part A — forward fix (code)**: the executor stamps `task_id` atomically in the
  completion UPDATE for future create_task executions. Code-only, no existing-row
  mutation. Still requires trunk review, but is not a data migration.
- **Part B — historical backfill (data)**: setting `task_id` on already-completed
  rows. THIS is the live-data correction and what this runbook gates.

## 1. Why the backfill is required

PR #201's proof left the linkage between the executed action and its created task
only in `result_ref`/`execution_result`. The app schema provides a first-class FK
(`agent_actions.task_id` → `tasks.id`, constraint `agent_actions_task_id_tasks_id_fk`)
that the app UI and future read surfaces (P4S-20 `/eos/tasks`) join on. Without
backfill, historical governed executions are invisible to FK-based joins.

## 2. Exact rows affected (measured read-only, 2026-07-06)

Exactly **1 row**: `action_1783367421127_b0ztpntev`
(status=completed, action_type=create_task, task_id=NULL).
Table totals at measurement: agent_actions=1 total, 1 completed create_task,
1 backfill candidate. The target task row exists:
`tasks.id = 'e455ff56-fc73-48fc-aa27-a91116e1c254'` (verified read-only).

## 3. Exact predicate

```sql
WHERE id = 'action_1783367421127_b0ztpntev'
  AND status = 'completed'
  AND action_type = 'create_task'
  AND task_id IS NULL
```
Row-pinned by primary key — the predicate cannot widen. The general-form predicate
(`action_type='create_task' AND status='completed' AND task_id IS NULL AND
execution_result ? 'task_id'`) is documented for future audits but NOT used for
this correction; each future backfill re-runs this runbook with its own row pins.

## 4. Read-only dry-run query (run and record BEFORE any write)

```sql
SELECT a.id, a.status, a.task_id AS current_task_id,
       a.execution_result->>'task_id' AS recorded_task_id,
       t.id AS task_exists
FROM agent_actions a
LEFT JOIN tasks t ON t.id = a.execution_result->>'task_id'
WHERE a.id = 'action_1783367421127_b0ztpntev'
  AND a.status = 'completed' AND a.action_type = 'create_task' AND a.task_id IS NULL;
```
Expected: exactly 1 row, `recorded_task_id = 'e455ff56-fc73-48fc-aa27-a91116e1c254'`,
`task_exists` NOT NULL. If `recorded_task_id` is NULL or the task row is missing:
**ABORT — the correction has no verified source value.**

## 5. Expected before/after counts

| Measure | Before | After |
|---|---|---|
| candidates (predicate §3) | 1 | 0 |
| agent_actions total rows | 1 | 1 (unchanged) |
| rows with task_id set | 0 | 1 |
| tasks total rows | unchanged | unchanged |

## 6. Idempotence guarantee

The predicate includes `task_id IS NULL`; a second run matches 0 rows and writes
nothing. The write sets `task_id` to a constant verified in §4 — re-running cannot
produce a different value.

## 7. Transaction / rollback plan

Single statement in one transaction:
```sql
BEGIN;
UPDATE agent_actions
SET task_id = 'e455ff56-fc73-48fc-aa27-a91116e1c254', updated_at = NOW()
WHERE id = 'action_1783367421127_b0ztpntev'
  AND status = 'completed' AND action_type = 'create_task' AND task_id IS NULL
RETURNING id, task_id, status;
-- verify RETURNING shows exactly 1 row with the expected task_id, else ROLLBACK
COMMIT;
```
Rollback (post-commit, if ever needed): the inverse single UPDATE setting
`task_id = NULL` on the same pinned id — recorded here so reversal needs no research.
No schema migration; the column and FK already exist.

## 8. Proof artifacts

- Dry-run output (§4) captured before the write.
- RETURNING row from the UPDATE.
- Post-write §5 counts.
- Read-only re-verification that `status`, `approved_by`, `approved_at`,
  `executed_at`, `completed_at`, `execution_result` are byte-identical to their
  pre-write values (SELECT captured before and after; only `task_id`/`updated_at`
  may differ).
- All committed to `data/audits/proof/` with the packet record.

## 9. Secret-scan requirements

No DSN, no connection string, no credential in any artifact or output; DB access
only via `docker exec os-operator` using in-process `EOS_DATABASE_URL`. Artifacts
scanned with the standard secret patterns before commit (expect 0 hits).

## 10. Completed-proposal proof integrity

The PR #201 proof chain is defined by the governance envelopes
(`0b29e3f9754a47ed`, `4d692aeb6b044543`) + `execution_result`/`result_ref` — none
of which this correction touches. §8's byte-identical check makes this a verified
property, not an assumption. `task_id` was NULL at proof time and the proof doc
records it as deferred debt; setting it *adds* lineage, it does not rewrite history.

## 11. No unrelated rows touched

The predicate is pinned to one primary key. §5's total-row and candidate counts
prove zero collateral. Any RETURNING count ≠ 1 aborts inside the transaction.

## 12. Owner approval gate

**No write occurs until the owner replies with explicit approval of THIS runbook**
(e.g. "approved: run P4S-21 backfill"). Approval covers exactly the §7 statement
against the §3 predicate. Part A (forward code fix) ships separately as a normal
reviewed PR and does not inherit this approval.
