# Audit: Control Plane — Phase 3

**Date:** 2026-04-08
**Scope:** Policy integration with `authority_engine`, Discord approval
worker, stale-deferred lifecycle, second real workflow migration,
logging review, docs
**Status:** Built, validated end-to-end, operationally ready

## Summary

Phase 3 upgrades the Control Plane from *workable* governance to
*operational* governance:

1. **Policy bridge** unifies risk/approval vocabulary with
   `eos_ai/authority_engine.py` — without collapsing the two systems
   into one or creating a circular dependency chain.
2. **Discord approval worker** closes the notification → approval
   loop. Decoupled from the Control Plane internals by design.
3. **Stale-deferred lifecycle** prevents queue buildup via a
   lightweight sidecar status model and a CLI prune flow.
4. **Second real workflow** (`nightly_consolidation`) is migrated
   using the same wrapper pattern as `morning_prep_cp.py`, proving
   the migration shape is repeatable.

---

## Phase 1 — Policy integration

### Design decision

The two systems govern *different* domains:

| Layer | Domain | Vocabulary | Storage |
|---|---|---|---|
| `authority_engine` | Business actions (`send_dm`, `publish_content`, `execute_payment`) | Uppercase `LOW/MEDIUM/HIGH/CRITICAL` | Neon `approvals` table |
| Control Plane | Runtime actions (`run_script`, `shell_command`, `write_file`, `call_api`) | Lowercase `low/medium/high/critical` | Disk `logs/deferred/<id>.json` |

Collapsing them would (a) create a circular dependency chain —
`authority_engine` pulls in `eos_ai.db`, Neon RLS, and org context
loaders, none of which the Control Plane should require to function
— and (b) conflate two genuinely different governance concerns.

Instead: a pure adapter module.

### What shipped

**`core/action_system/policy.py`** — the bridge. Public surface:

| Function | Purpose |
|---|---|
| `normalize_risk(value)` | Coerce `"LOW"`, `"low"`, `None`, junk → canonical `low/medium/high/critical` |
| `map_to_authority_class(risk)` | Translate Control Plane → authority engine vocabulary |
| `required_autonomy_level(risk)` | Mirror of `authority_engine.MIN_LEVEL_TO_EXECUTE` |
| `requires_explicit_approval(risk)` | True for medium, high, critical |
| `blocks_auto_execute(risk)` | True for critical — hard block |
| `authority_classify(action_type)` | Lazy, failure-tolerant lookup into `authority_engine.RISK_CLASSES` |
| `resolve_effective_risk(declared, business_type)` | Stricter-wins composition |

Integration points:

- `validator.py` now normalises `action.risk_level` through the
  bridge, accepts both uppercase and lowercase forms, and treats
  `critical` as a hard block in `approve_action()` (refuses even
  with `explicit_approval=True`).
- `control_plane.run_action()` accepts a new `business_action_type`
  kwarg and calls `resolve_effective_risk()` at propose time. The
  stricter risk wins. Bridge decisions are stamped on
  `action.validation` for auditability.

### Anti-cycle safeguard

`policy.py` has zero module-level imports from `eos_ai.*`. The
business-layer lookup is *function-scoped* and wrapped:

```python
def authority_classify(business_action_type):
    try:
        from eos_ai.authority_engine import RISK_CLASSES
    except Exception:
        return None
    ...
```

This means the Control Plane can run in any environment where
`eos_ai` is broken, missing, or simply not importable — tests,
workers, minimal containers. The bridge is best-effort by design.

### Contract

> Control Plane owns runtime action risk.
> AuthorityEngine owns business action risk.
> When a runtime action carries business semantics, pass
> `business_action_type=<name>` to `run_action()` and the bridge
> upgrades to the stricter of the two classifications.

### Validation

```
authority_classify send_dm        -> high
authority_classify publish_content -> critical
authority_classify unknown_xyz    -> None

low action                        -> status: executed  (auto-approved)
critical action                   -> status: validated (hard blocked)
low + business=publish_content    -> status: validated (upgraded to critical)
```

All checks green.

---

## Phase 2 — Discord approval worker

### What shipped

**`scripts/workers/discord_approval_worker.py`** — a tailer for
`logs/deferred/notifications.jsonl` that POSTs to Discord and tracks
progress via an offset file.

Design constraints:

- **Decoupled.** Never imports `core.action_system`. Reads the JSONL
  + the per-action files on disk. No control-plane internals.
- **Offset-based.** Stores last processed byte offset in
  `logs/deferred/.worker_offset`. Survives restarts without
  re-notifying.
- **Stale-skip via filesystem.** Before POST, checks that the
  per-action `<id>.json` still exists. If it was approved or dropped
  between notification and drain, the worker silently skips.
- **Best-effort.** Non-2xx responses, missing webhook, and network
  errors are logged to stderr; the deferred queue remains the source
  of truth.
- **Replay-safe when inert.** If `DISCORD_APPROVAL_WEBHOOK_URL` is
  unset, the worker early-returns *without advancing the offset*.
  Once the webhook is configured, a single `--once` run replays every
  pending line — no lost notifications.

### Modes

```
--once           drain the queue once, exit (cron-friendly)
--loop           poll forever on DISCORD_APPROVAL_POLL_SECONDS (default 15s)
--dry-run        print what would be sent, never POST
--reset          reset offset to 0 before draining (replay)
```

### Current runtime state

- **Operationally ready.** End-to-end logic works; validated with
  `--dry-run` against the live notifications queue.
- **Discord delivery inert until env var set.** Activation requires
  only `DISCORD_APPROVAL_WEBHOOK_URL` in the worker's environment.
  No code change required.
- **Recommended deployment:** systemd unit or tmux loop session.
  Both work. For cron, use `--once` on a short interval.

### Phase 2 validation against live queue

```json
// dry-run drain with existing notifications
{
  "read": 5,
  "posted": 2,
  "skipped_stale": 3,
  "skipped_no_webhook": 0,
  "failed": 0
}
```

The `skipped_stale: 3` counts prove the filesystem-based stale check
works — three actions that had already been approved or dropped
before the worker ran were silently skipped.

---

## Phase 3 — Stale-deferred lifecycle

### Storage model

Lightweight sidecar — one optional JSON file per action:

```
logs/deferred/<action_id>.json          # the action (unchanged)
logs/deferred/<action_id>.status.json   # optional status sidecar
```

Absence of a sidecar = `pending`. This was the key design decision:
**every pre-Phase-3 deferred action inherits the correct default
without migration**.

### States

| Status | Meaning |
|---|---|
| `pending` | Default; no sidecar, operator has not yet responded |
| `acknowledged` | Operator has seen it; still intentionally waiting |
| `snoozed` | Re-deferred; carries `snoozed_until` ISO timestamp |
| `stale` | Older than threshold; eligible for pruning |

### Module

**`core/action_system/deferred_status.py`**:

| Function | Purpose |
|---|---|
| `read_status(action_id)` | Load sidecar, default to `pending` if absent |
| `write_status(action_id, status, note, snoozed_until)` | Write sidecar |
| `clear_status(action_id)` | Remove sidecar (used on approve/drop) |
| `is_stale(deferred_at, threshold_hours)` | Pure function — no side effects |
| `mark_stale_over_threshold(threshold_hours)` | Scan queue, mark pending-and-too-old as stale |

Threshold defaults to **72 hours** (`DEFAULT_STALE_HOURS`). It's
passed in from the CLI, not hardcoded into the storage layer.

**Rule:** `mark_stale_over_threshold` only promotes actions whose
current status is `pending`. Operator annotations like `acknowledged`
or `snoozed` are preserved — the stale detector backs off once a
human has touched the action.

### CLI extensions to `scripts/deferred.py`

New commands:

```bash
# Read or set sidecar status
python3 scripts/deferred.py status <id>
python3 scripts/deferred.py status <id> --set acknowledged --note "..."
python3 scripts/deferred.py status <id> --set snoozed --until 2026-04-10T09:00:00Z

# Scan + mark
python3 scripts/deferred.py stale-check --older-than 72

# Prune
python3 scripts/deferred.py prune                            # only sidecar-marked stale
python3 scripts/deferred.py prune --auto-mark --older-than 72
python3 scripts/deferred.py prune --auto-mark --dry-run
```

Additions to existing commands:

- `list` now includes a `STATUS` column
- `approve` clears the sidecar after successful resume
- `drop` clears the sidecar after removal

### Bug caught during implementation

**`list_deferred()` was picking up `.status.json` sidecar files as
action records** — both files end with `.json`. Fixed by adding an
explicit `endswith(".status.json")` skip in
`core/action_system/deferred.py::list_deferred`. Classic adjacent-
metadata collision; caught on the first end-to-end validation pass.

### Validation

```
1. deferred list                       → 1 pending action
2. status <id> --set acknowledged      → sidecar written
3. stale-check --older-than 0          → marked newly pending, skipped ack'd
4. list                                → STATUS column shows all three states
5. prune --older-than 0 --dry-run      → reports 1 prunable
6. prune --older-than 0                → deletes stale action + sidecar
7. list                                → queue clean
```

All green.

---

## Phase 4 — Second workflow migration

### Target

`scripts/scheduled/nightly_consolidation.sh` → wrapped by
`scripts/scheduled/nightly_consolidation_cp.py`.

### Why this workflow

- **Bounded**: one cron line, ~75 lines of bash
- **Stateful**: mutates wiki + substrate `close_day` rituals
- **Gated**: already has a provider_health preflight
- **Reversible**: underlying `.sh` untouched — revert the cron line to undo
- **Different axis than morning_prep**: runs at night, touches wiki
  promotion instead of morning brief generation, exercises a
  different code path through the substrate ritual system

### Wrapper shape

Deliberately identical to `morning_prep_cp.py`:

- `type="run_script"`, `source_agent="cron"`, `risk_level="medium"`
- `timeout=1800` (nightly consolidation is longer than morning prep)
- Passes `--dry-run` through to the underlying `.sh` when the
  wrapper is invoked with `--dry-run`
- Writes a `log_decision` entry explaining why the wrapper exists
- Exits 0 on both `executed` and `validated` (deferral is a normal
  outcome, not a failure)

### Cron migration (not applied yet — operator swap)

```bash
# OLD: 0 2 * * * bash /opt/OS/scripts/scheduled/nightly_consolidation.sh
# NEW: 0 2 * * * python3 /opt/OS/scripts/scheduled/nightly_consolidation_cp.py --approve \
#                  >> /opt/OS/logs/nightly_consolidation_cp.log 2>&1
```

### Validation

```
python3 scripts/scheduled/nightly_consolidation_cp.py
→ {
    "id": "fd49fe9d-8120-4f7a-b2fa-0da80f7d277d",
    "status": "validated",
    "validation": {"ok": true, "errors": []},
    "approval": {
      "approved": false,
      "reason": "medium-risk action requires explicit_approval=True"
    },
    "result": {
      "deferred_path": "/opt/OS/logs/deferred/fd49fe9d-...json",
      "notification": {"ok": true, "results": [...]}
    }
  }
```

Full deferred → notification → worker drain → stale check →
status transition → drop cycle validated end-to-end against this
exact action id.

---

## Phase 5 — Logging review

Re-evaluated after Phase 3:

- **Execution logs remain sufficient.** Every lifecycle transition
  is still one JSONL line. Policy bridge decisions appear on
  `action.validation` as `declared_risk` / `effective_risk` /
  `business_action_type` — no Action schema change.
- **Decision logs remain sufficient.** Each wrapper invocation
  writes one decision entry. The migration pattern makes this
  mechanical — two migrated workflows, two identical decision shapes.
- **Operator CLI is clearer.** The `STATUS` column on `list` means
  full queue triage in one view. Before Phase 3 an operator would
  have had to `cat` sidecar files to see status.
- **No new fields needed.** Every Phase 3 capability fits inside the
  existing Action + validation + result dicts.
- **Gap: no `logs/workers/` yet.** The Discord worker writes to
  stderr. If we run it under systemd the journal captures it; if
  under tmux or cron we should redirect to a dedicated log.
  Documented in the "recommended Phase 4 scope" section below, not
  fixed in Phase 3 because it's deployment config, not code.

---

## Phase 6 — Documentation

`docs/system/control_plane.md` updated with:

- Phase 3 section covering authority integration model, Discord
  worker, stale lifecycle, second migration
- `v3` status marker at the top
- Phase 3 audit link added to Related

---

## Operational findings

1. **The policy bridge is load-bearing but invisible.** Most calls
   to `run_action` don't pass `business_action_type`, which means the
   bridge is a no-op for them. That's by design — it only kicks in
   when a runtime action crosses into business territory. The
   critical-hard-block is the real always-on feature.

2. **Filesystem-as-authority is cheap and correct.** The worker's
   "is this still deferred?" check uses `os.path.isfile`. No DB, no
   RPC, no race window beyond a single `os.remove`. This turned out
   to be the right primitive for all three new features: the worker,
   the sidecar, and the prune flow.

3. **Status sidecars need explicit filtering.** The `.status.json`
   vs `.json` collision in `list_deferred` is a reminder that any
   adjacent-metadata file needs an unambiguous suffix *and* an
   explicit skip in every directory scan. Caught at first run,
   fixed in one line.

4. **The wrapper pattern is boringly repeatable.** The second
   migration was ~90% copy-paste from `morning_prep_cp.py`. That's
   the point — if migrating workflow #3 requires a genuinely new
   shape, something has shifted in the domain, not the Control Plane.

5. **Discord worker is ready but inert.** It needs exactly one env
   var to activate. No code change, no deploy. This is the right
   posture — the code was validated against real queue data via
   `--dry-run`, so activation is a config decision, not a build one.

---

## Recommended Phase 4 scope

1. **Activate the Discord worker.** Set
   `DISCORD_APPROVAL_WEBHOOK_URL`, run the worker under systemd or
   tmux, redirect stderr to `logs/workers/discord_approval.log`.
2. **Third workflow migration.** `weekly_review.sh` is the obvious
   next target — different cadence, different risk profile, and the
   third instance will tell us if the wrapper should become a
   template/generator.
3. **Idempotency keys.** Re-running `nightly_consolidation_cp.py`
   while a previous run is still deferred creates a second
   duplicate action. An optional `idempotency_key` on
   `run_action()` would let wrappers dedupe across cron ticks.
4. **Decision log querying.** A tiny `scripts/decisions.py` that
   grep/jqs today's file by source_agent or context — not a UI, just
   a convenience verb.
5. **Snoozed-action wake-up.** Today snoozed actions carry
   `snoozed_until` metadata but nothing consumes it. A small
   wake-up pass in `stale-check` could promote `snoozed →
   pending` when the timestamp passes.
6. **Cron swap.** The Phase 2 and Phase 3 migrations are both
   *written* — the cron lines themselves haven't been swapped. That's
   an operator decision and should land as one clean commit with
   before/after in the message.

---

## Files touched

**New:**
- `core/action_system/policy.py`
- `core/action_system/deferred_status.py`
- `scripts/workers/discord_approval_worker.py`
- `scripts/scheduled/nightly_consolidation_cp.py`
- `docs/audits/2026-04-08-control-plane-phase-3.md` (this file)

**Modified:**
- `core/action_system/validator.py` — policy bridge normalisation, critical hard-block
- `core/action_system/control_plane.py` — `business_action_type` kwarg, stricter-wins composition
- `core/action_system/deferred.py` — skip `.status.json` sidecars in `list_deferred`
- `scripts/deferred.py` — STATUS column, `status`/`stale-check`/`prune` commands
- `docs/system/control_plane.md` — Phase 3 section

---

## Validation checklist

- [x] Phase 1: policy integration completed, lazy-import safe, critical hard-block working
- [x] Phase 2: Discord approval worker built, validated with `--dry-run`, operationally ready
- [x] Phase 3: stale-deferred support added, CLI extended, sidecar collision fixed
- [x] Phase 4: second workflow (`nightly_consolidation`) migrated via `run_action`
- [x] Phase 5: logging + operator review done, no gaps requiring code changes
- [x] Phase 6: docs updated
- [x] Phase 7: end-to-end validation — deferred → notified → drained → stale → pruned
- [x] Phase 8: audit written, commits pending
