# Control Plane Phase 4 — Design

**Status:** draft, awaiting review
**Date:** 2026-04-08
**Scope:** operational hardening of the Control Plane on top of Phases 1–3
**Non-scope:** new tool skills, general orchestrator, persistence replacement,
live production webhook sends, cron modification, production workflow execution
for testing

---

## 1. Goals (in one sentence each)

1. **Discord worker activation** — make the approval-routing path fully
   exercisable via a *test* webhook, with the last-mile production step
   documented exactly. No production webhook POSTs from this session.
2. **Third workflow migration** — prove the migration pattern is boringly
   repeatable on `weekly_review.sh` without changing its behaviour.
3. **Idempotency** — give callers a way to say *"do this at most once"* using
   the smallest correct mechanism that fits the existing filesystem-first
   deferred model.
4. **Decision-log querying** — turn `logs/decisions/*.jsonl` from an archive
   into something operators can actually read and filter.
5. **Snooze wake-up** — complete the `snoozed → pending` half of the
   deferred-status lifecycle that Phase 3 left half-wired.
6. **Cron-readiness assessment** — document which cron lines can be safely
   swapped and which cannot. Do not modify cron.

---

## 2. Grounding — what I read before designing

| File | Role confirmed |
|---|---|
| `core/action_system/actions.py` | `Action` dataclass, `propose_action`, `ALLOWED_ACTION_TYPES`. Id is random uuid4 — the thing that makes idempotency necessary. |
| `core/action_system/control_plane.py` | `run_action` / `resume_action` lifecycle. This is the ONE function that must learn about idempotency. |
| `core/action_system/validator.py` | Field + safety checks. Not in Phase 4's path. |
| `core/action_system/policy.py` | Control Plane ↔ authority_engine bridge. Not in Phase 4's path. |
| `core/action_system/executor.py` | Dispatch by `action.type`. Not in Phase 4's path. |
| `core/action_system/logging.py` | `log_execution` + `log_decision` — both append to `logs/execution/YYYY-MM-DD-execution.jsonl` and `logs/decisions/YYYY-MM-DD-decisions.jsonl`. Decision records include `decision_id`, `timestamp`, `source_agent`, `context`, `options_considered`, `chosen_option`, `reasoning`, `related_action_id`. This is the schema `scripts/decisions.py` has to query. |
| `core/action_system/deferred.py` | One JSON file per deferred action. Sets the pattern Phase 4 must follow. |
| `core/action_system/deferred_status.py` | Sidecar status with `snoozed_until` already defined, plus `mark_stale_over_threshold`. Snooze wake-up is a new sibling function, not a rewrite. |
| `core/action_system/notifier.py` | `FileNotifier` writes `notifications.jsonl`; `default_notifier()` stacks Discord on top when webhook env var is set. Worker consumes this file. |
| `scripts/deferred.py` | Existing operator CLI — template for `scripts/decisions.py`, and the home for new `wake` + `idempotency` subcommands. |
| `scripts/workers/discord_approval_worker.py` | Already built, offset-tailed, deferred-aware stale skip, webhook replay-safe when inert. Activation = env var + run target + validation, not new code. |
| `scripts/scheduled/morning_prep_cp.py`, `nightly_consolidation_cp.py` | Shape the `weekly_review_cp.py` wrapper must match. |
| `scripts/scheduled/weekly_review.sh` | Read-heavy health audit; calls `claude -p ... --max-budget-usd 1.00` and posts to Discord. Stateless on disk. Good migration target at `low` risk. |
| `docs/system/control_plane.md` | Existing Phases 1–3 narrative. Phase 4 extends this doc — does not replace it. |
| `docs/audits/2026-04-08-control-plane-phase-3.md` | Explicitly lists idempotency, snooze wake-up, decision querying, and cron swap as the next scope. Phase 4 implements exactly what the audit flagged. |

---

## 3. Architectural principles (inherited from Phases 1–3)

These are the principles every Phase 4 choice must respect. I am stating them
up front so the design can be checked against them, not so they can be argued.

1. **Filesystem-first persistence.** One JSON file per logical record. No
   database. No lock manager. Approval is `os.remove`.
2. **Append-only logs.** JSONL, one file per UTC day. Grep + jq is the
   query tool of record.
3. **Sidecar metadata, not schema drift.** The deferred action file is
   Phase 2's shape forever; sidecar files carry new state.
4. **Control Plane never blocks on optional integrations.** Notifier,
   authority_engine, TME — all advisory. Phase 4's idempotency store
   must follow the same rule.
5. **Source-of-truth is the on-disk queue.** Discord is advisory.
   Idempotency store is advisory-with-teeth (it can skip a run, but
   cannot alter one).
6. **Workers are decoupled.** `discord_approval_worker.py` does not
   import `core.action_system`. Any new worker must hold the same line.
7. **Underlying `.sh` scripts stay untouched.** Every migration reverts
   by flipping one cron line back.

---

## 4. Phase-by-phase design

### 4.1 Discord worker activation (test webhook only)

**The worker is already complete.** Reading `discord_approval_worker.py`
in detail: it tails `notifications.jsonl`, stores an offset at
`.worker_offset`, verifies the per-action JSON still exists before
posting, formats a Discord-shaped payload, and handles missing webhooks
by *not* advancing the offset so replay is lossless once the env var
lands.

**What "activation" means in Phase 4:**

1. **Exact env plumbing documented.** `DISCORD_APPROVAL_WEBHOOK_URL`
   goes in `/opt/OS/eos_ai/.env` for interactive runs and as a systemd
   `Environment=` line (or tmux shell export) for long-running mode.
   Poll interval via `DISCORD_APPROVAL_POLL_SECONDS` (default 15).
2. **Validation with a test webhook.** The review cycle will set
   `DISCORD_APPROVAL_WEBHOOK_URL` to a test channel webhook the user
   pastes into the session. A synthetic deferred action is created via
   `run_action(..., risk_level="medium")`, the worker is run with
   `--once`, and the post is verified in the test channel.
3. **Production activation step — documented, not executed.** A
   clearly-marked section of `docs/system/control_plane.md` will spell
   out the exact command to flip the worker to production:

       # 1. Add to /opt/OS/eos_ai/.env:
       #    DISCORD_APPROVAL_WEBHOOK_URL=<prod channel webhook>
       # 2. Start the loop under tmux (recommended first rollout):
       #    tmux new -d -s cp-worker \
       #      "python3 /opt/OS/scripts/workers/discord_approval_worker.py --loop"
       # 3. Verify:
       #    tmux capture-pane -t cp-worker -p | tail -20

4. **No new code in the worker itself.** If any bug shows up during
   test-webhook validation I will fix it, but the current design does
   not require changes.

**Decoupling check.** The worker still imports zero `core.action_system`
modules. Idempotency does not change that — the idempotency store is a
filesystem concern readable by anything, but the worker has no reason
to read it.

---

### 4.2 Third workflow migration — `weekly_review.sh`

**Target:** `scripts/scheduled/weekly_review.sh`
**Wrapper:** `scripts/scheduled/weekly_review_cp.py`
**Pattern:** identical to `morning_prep_cp.py` and `nightly_consolidation_cp.py`.

**Risk classification: `low`.**

Rationale — and this is a deliberate departure from the previous two
wrappers which used `medium`:

- `weekly_review.sh` is **read-heavy**: it does import checks, docker
  ps, skill-count, log summary.
- It does **not** mutate wiki state or ritual state.
- It consumes up to $1.00 of CC budget via `--max-budget-usd`, which is
  higher than morning_prep — but the effect is monetary, not stateful,
  and the budget is already capped inside the `.sh`.
- It posts a Discord message at the end, which is user-visible but not
  state-changing and already has a try/except fallback.

`low` auto-approves. That means a cron invocation will execute without
needing `--approve` and without defer/notify overhead. An operator can
still override via `--risk medium` on the CLI if they want a deferred
review.

**`source_agent`:** `cron`.

**`business_action_type`:** *not set* — the weekly report is an
internal health audit, not a `publish_content` or `send_dm` action.
Reviewed against `eos_ai/authority_engine.py` risk classes: none of the
business types apply here.

**Idempotency key (see §4.3):** `weekly_review:<YYYY-Www>` — one
review per ISO week. Cron runs Sundays at 06:00; a re-run the same
week becomes a no-op at the Control Plane level.

**What the wrapper does NOT do:**

- It does not modify `weekly_review.sh` behaviour.
- It does not replace the `claude -p` call with a Control Plane
  invocation of CC — that's out of scope.
- It does not change the Discord posting path inside the `.sh`. The
  Phase 4 Discord worker is for *approval routing*, not report
  delivery.

**Cron line (documented, not applied):**

    # OLD:
    # 0 6 * * 0 bash /opt/OS/scripts/scheduled/weekly_review.sh
    # NEW (recommended):
    # 0 6 * * 0 python3 /opt/OS/scripts/scheduled/weekly_review_cp.py --approve \
    #          >> /opt/OS/logs/weekly_review_cp.log 2>&1

`--approve` is technically redundant for a `low` action but included
for consistency with the other two wrappers and for forward-compat if
risk is later upgraded.

---

### 4.3 Idempotency model

**Problem statement.** `Action.id` is a random uuid4 generated per
call. Two invocations of `weekly_review_cp.py` within the same Sunday
produce two distinct Actions, two executions, two log trails. For
*stateful* runtime actions like `morning_prep` or a batched outreach
send, this means cron re-runs (due to flake, restart, or operator
double-click) can execute the same real-world effect twice.

**Scope.** We need to prevent *duplicate successful execution* of the
same logical action within a time window that the caller defines.
This is not distributed locking. It is not cross-process mutual
exclusion under high concurrency. The Control Plane is single-host,
low-concurrency (cron + occasional operator runs) and that shapes the
right solution.

**The model: filesystem sentinels keyed by `idempotency_key`.**

```
/opt/OS/logs/idempotency/<sha1(key)>.json
```

Layout — one file per key, matching the deferred queue pattern:

```json
{
  "key": "weekly_review:2026-W15",
  "action_id": "4f3e...-...",
  "status": "executed",
  "created_at": "2026-04-08T06:00:01Z",
  "completed_at": "2026-04-08T06:00:47Z",
  "ttl_seconds": 604800
}
```

**Why SHA-1 of the key as the filename:** keys will contain colons
and slashes (`weekly_review:2026-W15`, `morning_prep:2026-04-08`),
which are awkward on disk. SHA-1 sidesteps escaping, and the full
key is preserved inside the JSON for operator readability. SHA-1 is
fine here — not cryptographic, just a filesystem-safe digest.

**Status values inside the sentinel:**

| Status | Meaning |
|---|---|
| `in_flight` | Key claimed; action is executing right now |
| `executed` | Action completed successfully |
| `failed` | Action reached terminal failed state — but sentinel still exists |
| `deferred` | Action was deferred (medium/high, no explicit approval) |

**TTL.** Each sentinel carries `ttl_seconds`. After `created_at + ttl`
the sentinel is considered expired and a new call with the same key
will proceed. A TTL of 0 means "forever unless manually cleared".

**Default TTLs by caller intent** (set in the caller's wrapper, not
the core):

- `weekly_review`: 6 days (604800s, strictly less than a week, so the
  next Sunday is never blocked by its predecessor).
- `morning_prep`: 23 hours (so a 5:30 run will never collide with
  tomorrow's 5:30 run, but a flake retry within the same morning
  will be suppressed).
- `nightly_consolidation`: 23 hours (same reasoning).

**Integration into `run_action`:** one new kwarg.

```python
def run_action(
    type: str,
    description: str,
    *,
    ...,
    idempotency_key: str | None = None,
    idempotency_ttl_seconds: int | None = None,
) -> Action:
```

**Algorithm (precise, because this is the load-bearing change):**

1. If `idempotency_key is None`, behaviour is unchanged from Phase 3.
2. Else, before calling `propose_action`:
   - Read the sentinel file. If missing → proceed; write a new
     sentinel with `status="in_flight"` and the caller-supplied TTL
     *before* propose.
   - If present and not expired:
     - `status == "in_flight"`: return an Action with
       `status="skipped_duplicate"`, `result={"ok": False, "error":
       "idempotency conflict: already in-flight", "conflict_action_id": <id>}`.
       No log write. No execution.
     - `status == "executed"`: return an Action with
       `status="skipped_duplicate"`, `result={"ok": True, "skipped":
       True, "reason": "already executed this key", "original_action_id": <id>}`.
     - `status == "failed"`: **proceed**. Failed runs should not
       block retries. Sentinel is overwritten with the new in-flight
       record.
     - `status == "deferred"`: check `logs/deferred/<action_id>.json`.
       If it still exists, return `skipped_duplicate` pointing at
       the existing deferred action — the operator still owes a
       decision on it. If the deferred file is *gone* (dropped or
       already resumed/executed by someone else), **overwrite the
       sentinel** with a fresh `in_flight` claim and proceed. A
       resumed action would already have flipped the sentinel to
       `executed` via the resume path, so reaching this branch with
       a missing deferred file implies a drop, which correctly
       unblocks retries.
   - If present and expired → proceed, overwrite.
3. Run propose → validate → approve → execute as normal.
4. On terminal state, update the sentinel:
   - `executed` → `status="executed"`, set `completed_at`.
   - `failed` → `status="failed"`, set `completed_at`. Next call
     with the same key will be allowed to retry (TTL-gated — if the
     caller wants a hard lockout on failure they set a long TTL).
   - `deferred` → `status="deferred"`. This is the trickiest state
     because the action is now sitting in the deferred queue, and a
     re-run of the wrapper should NOT defer a second copy. The
     sentinel blocks until either (a) `resume_action` fires (at
     which point it flips to executed/failed via the resume path,
     see below), or (b) the sentinel expires, or (c) the operator
     drops the deferred action (detected by file absence).
   - `rejected` by validator → **do not write a sentinel at all**.
     Rejected actions are caller bugs; re-runs should reproduce the
     error for debugging.

**`resume_action` integration.** When a deferred action is resumed and
its original proposal carried an `idempotency_key`, the resume path
must update the sentinel. The key is stored on the Action itself (see
schema note below) so `resume_action` can find it without caller help.

**New field on Action (non-breaking):**

```python
# on Action dataclass
idempotency_key: str | None = None
```

Added after `result` with default `None`. Backwards compatibility
runs in both directions and has been verified by re-reading
`deferred.py:42-50`:

- **Old deferred files → new code.** `load_deferred` builds the
  Action from `{k: v for k, v in data.items() if k in valid_keys}`.
  A pre-Phase-4 file has no `idempotency_key` entry, so the
  dataclass default of `None` is used. Loads cleanly.
- **New deferred files → old code (rollback scenario).** The
  same filtering ignores unknown keys. An Action file with
  `idempotency_key` still loads on pre-Phase-4 code, just without
  the new field. No crash, no breakage.

This is why the field goes on `Action` itself and not on a sidecar:
it needs to ride along with the action through defer → resume so
the resume path can update the sentinel, and the existing
serialisation already handles the compatibility story.

**Operator visibility.** Two new subcommands on `scripts/deferred.py`:

```bash
# List idempotency sentinels (optionally expired only)
python3 /opt/OS/scripts/deferred.py idempotency list
python3 /opt/OS/scripts/deferred.py idempotency list --expired

# Show one
python3 /opt/OS/scripts/deferred.py idempotency show <key-or-sha>

# Clear one (force future runs to proceed)
python3 /opt/OS/scripts/deferred.py idempotency clear <key-or-sha>

# Purge all expired
python3 /opt/OS/scripts/deferred.py idempotency prune
```

**Concurrency.** The claim step uses `os.open(path, O_CREAT | O_EXCL
| O_WRONLY)` to create the sentinel file atomically. This is the
smallest correct single-host mutual exclusion: the OS guarantees
exactly one caller wins the create, the loser catches `FileExistsError`
and treats it as a hit. No `fcntl.flock`, no database, no lock manager.

Two edge cases are explicit:

- **Claim wins, then crash before execution.** The sentinel is on
  disk with `status="in_flight"`. Next call with the same key sees
  `in_flight` and returns `skipped_duplicate` — safer than
  re-running, because the previous attempt may have had side effects
  we can't see. Operator recovery: `deferred.py idempotency clear <key>`.
- **Expired `in_flight`.** If the sentinel is older than its TTL
  *and* still `in_flight`, we treat it as a crashed prior run and
  allow takeover (overwrite). This prevents permanent lockout from
  a single crash.

**Coupling check.** The idempotency store lives in its own module
(`core/action_system/idempotency.py`). It imports nothing from
`notifier`, `executor`, `validator`, `policy`, or `deferred`. It is
imported *only* by `control_plane.py`. One new module, one new call
site — the smallest surface that gets the job done.

---

### 4.4 Decision-log querying — `scripts/decisions.py`

**Problem.** `logs/decisions/YYYY-MM-DD-decisions.jsonl` accumulates
append-only records with `decision_id`, `timestamp`, `source_agent`,
`context`, `options_considered`, `chosen_option`, `reasoning`,
`related_action_id`. The Phase 3 audit flagged this as write-only.

**Solution shape.** A CLI that mirrors `scripts/deferred.py` — same
argparse-subcommand structure, same text-table output, same
`--json` flag for scripting.

**Commands:**

```bash
# Recent N decisions across all days (default 20)
python3 /opt/OS/scripts/decisions.py list
python3 /opt/OS/scripts/decisions.py list --limit 50

# One specific decision
python3 /opt/OS/scripts/decisions.py show <decision_id>

# All decisions related to an action
python3 /opt/OS/scripts/decisions.py for-action <action_id>

# Filter by source_agent
python3 /opt/OS/scripts/decisions.py list --agent cron
python3 /opt/OS/scripts/decisions.py list --agent developer --limit 10

# Filter by context substring (useful for "morning_prep" / "weekly_review")
python3 /opt/OS/scripts/decisions.py list --context morning_prep

# Date scoping — default is last 7 days, override with --since
python3 /opt/OS/scripts/decisions.py list --since 2026-04-01
python3 /opt/OS/scripts/decisions.py list --today

# JSON output for scripting
python3 /opt/OS/scripts/decisions.py list --json
```

**Implementation approach.** The log directory is small (~1 file/day).
`list` reads the last N days of `*-decisions.jsonl`, parses line by
line, applies filters, sorts by timestamp descending, applies
`--limit`. No indexing, no cache. If this grows to thousands of files
we revisit — but a decision log that grows faster than that is itself
a signal the Control Plane is being overused.

**What this tool does NOT do:**

- No tagging or mutation of decisions.
- No cross-referencing to the execution log. `related_action_id` is
  enough to pivot manually via `grep`.
- No `decision_id` inference from partial prefixes — full UUID only.
  (Deferred CLI has the same rule — consistency wins.)
- No outcome tracking. The current decision schema has no `outcome`
  field; adding one is a Phase 5 discussion.

**Output format — `list`:**

```
TIMESTAMP                      AGENT                CONTEXT                                    ACTION_ID (short)
2026-04-08T06:00:02Z          cron                 scheduled invocation of morning_prep       25c42826
2026-04-08T02:00:01Z          cron                 scheduled invocation of nightly_consolid…  4f3e9d01
...

3 decision(s).
```

**Module decoupling.** Lives in `scripts/decisions.py`, imports
*nothing* from `core.action_system`. It only reads JSONL files. This
matches the worker's decoupling discipline. A broken Control Plane
never breaks the decision query tool.

---

### 4.5 Snooze wake-up + stale lifecycle completion

**Problem.** `deferred_status.write_status(..., status="snoozed",
snoozed_until=...)` exists; nothing promotes snoozed → pending when
the timestamp passes. Operators set snooze and then the action is
invisible to `list` triage patterns (it's there, but nothing tells
them "this is ready now").

**Solution — minimal and filesystem-consistent:**

1. **New helper in `deferred_status.py`:**

   ```python
   def wake_due_snoozed(now: datetime | None = None) -> list[str]:
       """Scan sidecars, promote snoozed → pending where snoozed_until ≤ now."""
   ```

   Scans `*.status.json`, reads each, and for any record whose
   `status == "snoozed"` and `snoozed_until` is in the past, rewrites
   the sidecar with `status="pending"` and a note
   `"auto-woken at <iso>"`. Returns the list of woken action ids.

2. **New CLI verb on `scripts/deferred.py`:**

   ```bash
   # Preview what would wake up
   python3 /opt/OS/scripts/deferred.py wake --dry-run

   # Actually wake them
   python3 /opt/OS/scripts/deferred.py wake

   # List snoozed items that are overdue (read-only)
   python3 /opt/OS/scripts/deferred.py list --overdue-snoozed
   ```

3. **New read filter on `list`:** `--overdue-snoozed` narrows the
   output to actions whose sidecar status is `snoozed` AND whose
   `snoozed_until` has passed. Lets an operator triage without
   mutating anything.

4. **No auto-resume.** Waking does *not* execute. Waking flips the
   sidecar status to `pending` so the action reappears in the default
   `list` view the same way a freshly-deferred action does. Humans
   decide; the wake helper only surfaces.

**Rationale for flip-to-pending, not auto-execute.** The whole reason
an action was snoozed is that the operator wanted it re-evaluated
later, not auto-approved later. Auto-execute would break that
contract, and it would create a second "approval pathway" that
diverges from the explicit `resume_action` flow. One approval
pathway, always explicit.

**Stale-check interaction.** `mark_stale_over_threshold` already
skips non-pending statuses. A snoozed-but-overdue item will NOT be
marked stale even if its `deferred_at` is ancient — because its
sidecar status is `snoozed`, not `pending`. The Phase 4 wake helper
promotes `snoozed → pending`, and only from that point can the stale
detector act on it. That is the intended interaction: snoozing
grants an action immunity from stale pruning until it wakes up.

---

### 4.6 Cron-readiness assessment (documentation only)

**What this section produces:** a table in
`docs/system/control_plane.md` with one row per cron-scheduled
workflow, judging swap readiness. It is *not* a cron modification.

**Criteria:**

1. **Wrapper exists.** Is there a `*_cp.py` wrapper?
2. **Risk is honest.** Is the declared risk level an accurate
   reflection of blast radius?
3. **Idempotency is safe.** Does a duplicate call the same day
   produce the correct outcome (either a natural no-op or blocked by
   idempotency key)?
4. **Failure mode is visible.** Do cron failures surface via
   `logs/execution/` + `deferred` queue + optional Discord?
5. **Reversible.** Can the cron line flip back to the bash path in
   one commit?

**Initial table (to be filled in as part of the implementation, not
decided now):**

| Workflow | Wrapper | Risk | Idempotency | Swap recommendation |
|---|---|---|---|---|
| `morning_prep.sh` | `morning_prep_cp.py` | medium | will be added Phase 4 | swap-ready after Phase 4 |
| `nightly_consolidation.sh` | `nightly_consolidation_cp.py` | medium | will be added Phase 4 | swap-ready after Phase 4 |
| `weekly_review.sh` | `weekly_review_cp.py` (new) | low | built-in | swap-ready after Phase 4 |
| `nightly_maintenance.sh` | none | — | — | **not ready** — not migrated |

**The audit report is where the swap recommendation is made. The
actual cron modification is out of Phase 4 scope.**

---

## 5. New files and modules

| Path | Purpose |
|---|---|
| `core/action_system/idempotency.py` | Sentinel store (read, claim, complete, expire, list, clear). Pure filesystem + JSON. No deps on other Control Plane modules. |
| `scripts/scheduled/weekly_review_cp.py` | Third workflow wrapper. Same shape as Phase 2/3 wrappers. |
| `scripts/decisions.py` | Decision log query CLI. No `core.action_system` imports. |
| `docs/superpowers/specs/2026-04-08-control-plane-phase-4-design.md` | This document. |
| `docs/audits/2026-04-08-control-plane-phase-4.md` | Final audit (written during implementation, not now). |

## 6. Modified files

| Path | Change |
|---|---|
| `core/action_system/actions.py` | Add `idempotency_key: str \| None = None` field. |
| `core/action_system/control_plane.py` | New `idempotency_key` + `idempotency_ttl_seconds` kwargs; pre-flight sentinel check; post-execution sentinel update; resume path sentinel flip. |
| `core/action_system/deferred_status.py` | New `wake_due_snoozed()` helper. |
| `scripts/deferred.py` | New subcommands: `wake`, `idempotency list/show/clear/prune`; new `list --overdue-snoozed` flag. |
| `scripts/scheduled/morning_prep_cp.py` | Add `idempotency_key=f"morning_prep:{UTC-date}"`, TTL 23h. |
| `scripts/scheduled/nightly_consolidation_cp.py` | Add `idempotency_key=f"nightly_consolidation:{UTC-date}"`, TTL 23h. |
| `docs/system/control_plane.md` | New Phase 4 section: Discord activation, idempotency, decision querying, third migration, wake-up flow, cron-readiness table. |

## 7. Files explicitly NOT touched

- `core/action_system/validator.py` — no schema change beyond the new optional Action field, which validator doesn't inspect.
- `core/action_system/policy.py` — authority bridge is stable.
- `core/action_system/executor.py` — dispatch is unchanged.
- `core/action_system/notifier.py` — worker is already complete.
- `scripts/workers/discord_approval_worker.py` — no changes unless test-webhook validation exposes a bug.
- `scripts/scheduled/*.sh` — never modified.
- `cron` entries — never modified.

---

## 8. Validation plan (Phase 8 of the execution)

All validation uses **synthetic actions** or the **test Discord webhook**.
No production workflow is executed. No production webhook is touched.

1. **Idempotency happy path.** Call `run_action(type="shell_command",
   inputs={"command": "echo phase4"}, idempotency_key="phase4-test-1",
   idempotency_ttl_seconds=60)` twice. First returns `executed`.
   Second returns `skipped_duplicate` with `original_action_id`
   pointing at the first. Sentinel file present, status `executed`.
2. **Idempotency expiry.** Same key, short TTL (2s), sleep 3, call
   again — proceeds fresh, overwrites sentinel.
3. **Idempotency + deferred.** Call with `risk_level="medium"`, no
   `explicit_approval`, idempotency_key set. First call defers and
   writes sentinel with `status="deferred"`. Second call returns
   `skipped_duplicate`. Operator drops the deferred action via
   `deferred.py drop <id>`. Third call proceeds fresh (file absence
   detected).
4. **Idempotency + resume.** Same setup. First call defers, writes
   sentinel `deferred`. Operator approves via `deferred.py approve
   <id>`. Sentinel flips to `executed`. A fresh call with the same
   key then returns `skipped_duplicate`.
5. **Idempotency + failure.** Use a `run_script` pointing at a
   non-existent path. First call fails. Sentinel shows `failed`.
   Second call with same key proceeds fresh.
6. **Idempotency CLI.** `list`, `show`, `clear`, `prune` all work
   against real sentinels from the previous steps.
7. **Decision query CLI.** `list`, `show`, `for-action`, `--agent`,
   `--context`, `--since` exercised against
   `logs/decisions/2026-04-08-decisions.jsonl` (which already exists).
8. **Weekly review wrapper.** Run with `--help` to confirm argparse
   wiring. Then validate the Control Plane integration end-to-end
   WITHOUT executing the real `weekly_review.sh`, using a test
   fixture at `tests/fixtures/noop.sh` (a `.sh` that echoes and
   exits 0 — required because `validator._check_shell_safety` /
   `_execute_run_script` enforce `.py` or `.sh` extensions, so
   `/usr/bin/true` would be rejected). The fixture runs through
   `run_action` with `type="run_script"`, proving
   validate → approve → execute → log without touching the real
   weekly review. Finally, exercise the real wrapper in a way that
   stops before execution: call `propose_action` + `validate_action`
   directly against the real `SCRIPT_PATH` to confirm the inputs
   pass validation. **No real `weekly_review.sh` execution.**
9. **Snooze wake-up.** Create a synthetic deferred action, set
   sidecar `snoozed` with `snoozed_until` 1 minute in the past, run
   `wake --dry-run` — see it listed. Run `wake` — sidecar flips to
   `pending`.
10. **Stale/wake interaction.** Confirm `stale-check` does not
    promote `snoozed` items, then wake them, then confirm
    `stale-check` now acts on them.
11. **Discord worker with test webhook.** User pastes test webhook
    URL into session. Export `DISCORD_APPROVAL_WEBHOOK_URL`. Create
    a synthetic deferred action. Run worker `--once`. Confirm post
    in test channel. Run `--once` again — no duplicate (offset
    advanced). Drop the deferred action, re-create with same
    description — new post.
12. **Log and queue state consistency** after every step —
    `jq` the execution log, `ls` the deferred dir, `ls` the
    idempotency dir.

---

## 9. Open questions for the reviewer

1. **Idempotency TTL default on morning/nightly.** I proposed 23h.
   Confirm or override.
2. **Weekly review risk level.** I proposed `low` (read-heavy, no
   state mutation). Confirm or override.
3. **Test Discord webhook.** You'll paste it at execution time. I
   will not store it in any committed file. If you prefer it sourced
   from a temporary shell export only, say so and I'll avoid writing
   it anywhere persistent.
4. **`weekly_review.sh` validation.** I will NOT execute the real
   script during testing (per your constraint). My plan is to
   validate the wrapper code path using a no-op command override.
   Confirm that's acceptable.
5. **Cron-readiness table.** Do you want the table in
   `docs/system/control_plane.md` *and* the audit, or only the
   audit? My lean is both, because the main doc is what operators
   read day-to-day.

---

## 10. What Phase 5 should likely scope (not now)

- **Decision outcomes.** Add an `outcome` field to decision records,
  written asynchronously when the related action reaches terminal
  state. Makes `decisions.py` answer "did we get what we decided to
  get?" — genuinely learnable.
- **Approval queue DB.** If Discord worker + file queue proves
  insufficient for multi-operator scenarios, *then* consider a
  persistent approval queue. Not before.
- **Per-agent policies.** Already flagged in the Phase 1 limitations.
- **Dry-run mode for `run_action`.** Stop after validation and emit a
  plan. Distinct from the deferred state because it never writes to
  the deferred queue.

---

## 11. Risks this design does not address

Called out so they are visible, not because Phase 4 will fix them:

- **Clock skew.** All TTLs and snooze timestamps use local clock via
  `datetime.now(timezone.utc)`. The VPS is single-host, so skew
  against itself is not a concern, but skew relative to external
  systems (Discord, cron) is not accounted for.
- **Sentinel directory growth.** `prune` cleans expired ones, but an
  operator who never runs prune will see unbounded growth. Mitigated
  by the `list --expired` → `prune` habit, which the docs will spell
  out.
- **Race between `is_still_deferred` (worker) and `run_action`
  re-writing the sentinel.** The worker's stale-skip check happens
  before POST; if an operator approves an action at the exact
  millisecond the worker is formatting the payload, the worker may
  still post. This is the existing Phase 3 semantics and is
  acceptable (advisory notifier).
