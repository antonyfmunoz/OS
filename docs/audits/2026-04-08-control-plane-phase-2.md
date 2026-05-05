# Audit: Control Plane — Phase 2

**Date:** 2026-04-08
**Scope:** Real-workflow migration + deferred action persistence +
notifier foundation + logging review
**Status:** Built, validated end-to-end, ready for Phase 3

## What was built

### 1. First real workflow migrated: `morning_prep`

`scripts/scheduled/morning_prep.sh` was the selected target from the
spec's preferred list. After inspection it proved to be a good choice:
bounded, a mix of state mutation (ritual start/finish) and expensive
external calls (up to $0.30 CC budget + provider health gate), and
run daily from cron — so the migration immediately stresses both the
approval policy and the logging.

Migration shape: a thin Python wrapper
(`scripts/scheduled/morning_prep_cp.py`) that routes the existing
`.sh` through `run_action` as a `run_script` action. The `.sh` itself
is untouched — the migration is reversible by reverting the cron line.

Key decisions:
- **risk_level="medium"**: mutates ritual state + consumes CC budget.
  Not destructive, but not free. Medium means cron runs need
  `--approve`, and ad-hoc runs default to deferring so operators see
  what's happening before CC money moves.
- **source_agent="cron"**: future per-agent policy hooks can
  distinguish scheduled automation from interactive runs.
- **timeout=600**: the .sh includes a long CC call with a 30¢ budget;
  600s gives headroom without being a silent runaway.

Cron change (pending operator swap, not applied in this phase):

```bash
# OLD: 30 5 * * * bash /opt/OS/scripts/scheduled/morning_prep.sh
# NEW: 30 5 * * * python3 /opt/OS/scripts/scheduled/morning_prep_cp.py --approve \
#                  >> /opt/OS/logs/morning_prep_cp.log 2>&1
```

### 2. Deferred action persistence + resume

New module: `core/action_system/deferred.py`

| Function | Purpose |
|---|---|
| `save_deferred(action)` | Write action to `/opt/OS/logs/deferred/<id>.json` |
| `load_deferred(action_id)` | Reconstruct an Action from disk |
| `delete_deferred(action_id)` | Remove (on approve or drop) |
| `list_deferred()` | Return summary dicts for all deferred actions |

One-file-per-action design: `approve` is `os.remove`, no rewrites,
no shared-file race. Listing is `os.listdir` + per-file JSON parse,
which is fine up to thousands of pending approvals (far beyond v2).

`control_plane.run_action` now calls `save_deferred` + notifier when
an action lands in `status="validated"`, and logs a fifth execution
line with `deferred_path` and `notification` metadata so forensics
from logs alone can reconstruct the full trail.

New public entry: `control_plane.resume_action(action_id)`. Loads the
persisted action, grants explicit approval, executes, logs every
transition (including a decision log entry explaining the resume),
and deletes the deferred file on any terminal state.

New operator CLI: `scripts/deferred.py`

| Subcommand | Effect |
|---|---|
| `list` | Table view of every deferred action |
| `show <id>` | Full JSON of one deferred action |
| `approve <id>` | Resume → approve → execute → delete |
| `drop <id>` | Remove without executing |

### 3. Notifier foundation

New module: `core/action_system/notifier.py`

A `Notifier` `Protocol` — any object with `notify(action) -> dict`
works. Three concrete implementations:

- `FileNotifier` — always-on, appends to
  `/opt/OS/logs/deferred/notifications.jsonl`. Future workers
  (Discord bot, Telegram worker, dashboard) can tail or drain it
  without ever importing Control Plane internals.
- `DiscordNotifier` — reads `DISCORD_APPROVAL_WEBHOOK_URL` from env.
  POSTs a formatted approval prompt with the exact `approve_cmd` to
  run. If the env var is missing or the POST fails, returns
  `{"ok": False, ...}` but never raises.
- `MultiNotifier` — fan-out to a list of notifiers.

`default_notifier()` returns `FileNotifier` always, plus
`DiscordNotifier` if the webhook env var is set. `run_action` uses
this by default; callers can pass any other `Notifier`.

Design rationale: the file queue is the load-bearing channel.
Discord is additive and best-effort. A notification failure never
costs the deferred record — persistence and notification are
independent concerns.

### 4. Logging review — findings from real use

**Gap found and fixed:** in the initial Phase 2 implementation, the
`deferred_path` and `notification` fields were attached to the
returned Action *after* the last `log_execution` call. A consumer
replaying from logs alone could see "this action was validated but
not approved" without seeing where the deferred file lived. Fixed by
adding one more `log_execution(action)` call after persistence +
notification complete.

**Sufficient for Phase 2:**
- One JSONL line per lifecycle transition is the right primitive.
- Execution logs + decision logs split cleanly — "what happened" vs
  "why".
- The existing Action schema didn't need new fields.
- Operator CLI verbs (`list/show/approve/drop`) map directly to
  operator intent. No confusion in practice.

No broader logging changes made. The logs were already the
strongest part of Phase 1 and Phase 2 only needed a one-line patch.

## Validation results

Full end-to-end demonstration executed live:

| Step | Outcome |
|---|---|
| `morning_prep_cp.py` no `--approve` | Deferred, persisted, notified ✓ |
| `deferred list` | Renders table with risk/type/agent/id/description ✓ |
| `deferred drop <id>` | Removes deferred file ✓ |
| Harmless medium-risk action (`echo ...`) no approval | Deferred, persisted, notified ✓ |
| `deferred approve <id>` | Loads → approves → executes → deletes → logs ✓ |
| `deferred list` after approve | Empty ✓ |
| Notifications queue | Two valid JSONL lines, each with `approve_cmd` ✓ |
| Post-fix revalidation via `resume_action` | `deferred → executed`, file removed ✓ |

Log state after validation:
- `logs/execution/2026-04-08-execution.jsonl` — 27+ lines
- `logs/decisions/2026-04-08-decisions.jsonl` — 4+ lines
- `logs/deferred/notifications.jsonl` — 2+ lines
- `logs/deferred/` — empty (all test actions resumed or dropped)

## Files changed/added

```
core/action_system/deferred.py          NEW  durable deferred store
core/action_system/notifier.py          NEW  Notifier protocol + impls
core/action_system/control_plane.py     MOD  deferred + notify + resume
scripts/deferred.py                     NEW  operator CLI
scripts/scheduled/morning_prep_cp.py    NEW  migrated workflow wrapper
docs/system/control_plane.md            MOD  Phase 2 section added
docs/audits/2026-04-08-control-plane-phase-2.md   NEW  this report
```

## Findings from real operational use

1. **Defer-as-default is the right policy for non-trivial cost.**
   Running `morning_prep_cp.py` without `--approve` lands it cleanly
   in the queue. Cron gets `--approve` because it's pre-authorized;
   humans get the queue because they should look before spending
   money. This split felt correct on the first try.

2. **The notifications.jsonl queue is the quiet hero.** It means
   Discord integration can be built entirely *outside* the Control
   Plane — any worker that tails the file and handles approvals has
   everything it needs (`action_id`, `approve_cmd`). The Control
   Plane itself never needs to know about Discord.

3. **One-file-per-action is noticeably simpler to reason about than
   a shared queue file.** No locking, no partial writes, no rewrite
   dance. The list view is O(n) filesystem scans but n is tiny.

4. **The `resume_action` decision log entry is more valuable than
   expected.** It turns "someone approved this" into a first-class
   artifact — which matters for any action big enough to be deferred
   in the first place.

5. **Minor missing piece:** there's no timeout / stale-deferred
   policy. A deferred action sits in the queue forever. Not a
   problem yet, but worth a cron or status field in Phase 3.

## Recommended Phase 3 scope

Ordered by leverage:

1. **Per-agent / per-venture policy.** Integrate with
   `eos_ai/authority_engine.py` so its existing risk classes and the
   Control Plane's risk classes share one vocabulary. Let each
   `source_agent` have a policy like "outreach agent cannot run
   shell commands matching pattern X even at low risk."
2. **Discord approval worker.** Tail `notifications.jsonl` or POST
   via `DISCORD_APPROVAL_WEBHOOK_URL`. Approvals come back through
   a message handler that shells out to `scripts/deferred.py approve`.
   This completes the loop without touching Control Plane internals.
3. **Stale-deferred cleanup.** `scripts/deferred.py prune --older-than 72h`
   plus a `status` field on deferred actions (e.g., `acknowledged`,
   `snoozed`) for richer ops.
4. **Second and third migrations.** Pick the next two workflows —
   suggest `scripts/scheduled/nightly_consolidation.sh` and one
   orchestrator entry. More workflows = more real feedback on what
   the Control Plane is still missing.
5. **Chain composition.** `Pipeline([action_a, action_b, action_c])`
   with stop-on-fail semantics so multi-step workflows can move
   through the Control Plane as one unit. Use the nightly job as
   the first test case.
6. **Dry-run mode.** `run_action(..., dry_run=True)` stops after
   validation + approval and emits a plan. Useful for CI-style
   policy checks on PR branches.
7. **Decision log reader.** Tiny `scripts/decisions.py list|show`
   so the "why" artifact is actually queryable.

## Constraints honored

- No new tool skills built.
- No new capability coverage.
- No full orchestrator.
- No over-engineered approval workflow.
- Every addition is reversible — revert the new files and the
  original `morning_prep.sh` still runs unchanged.
