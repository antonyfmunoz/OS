# Control Plane Phase 4 — Audit

**Date:** 2026-04-08
**Design doc:** `docs/superpowers/specs/2026-04-08-control-plane-phase-4-design.md`
**Scope delivered:** idempotency, Discord worker test activation,
third workflow migration, decision log querying, snooze wake-up
completion, documentation + validation.

---

## 1. What shipped

### 1.1 Idempotency (Phase 4.1)

- New module `core/action_system/idempotency.py` — filesystem sentinel
  store, O_EXCL atomic claim, TTL-gated expiry, operator helpers.
- `Action` dataclass gains optional `idempotency_key: str | None = None`.
  Backwards-compatible via `load_deferred`'s `valid_keys` filter (both
  directions — old file/new code and new file/old code).
- `run_action` gains `idempotency_key` and `idempotency_ttl_seconds`
  kwargs. Full pre-flight state machine matching the design:

  | Sentinel | Behaviour |
  |---|---|
  | missing / expired | claim + proceed |
  | `in_flight` | `skipped_duplicate` (conflict) |
  | `executed` | `skipped_duplicate` (success short-circuit) |
  | `failed` | proceed + overwrite |
  | `deferred` + file present | `skipped_duplicate` |
  | `deferred` + file dropped | proceed + overwrite |

- Terminal states flip the sentinel (`executed` | `failed` | `deferred`).
- Validator-rejected actions **clear** the sentinel — rejection is a
  caller bug and the next call should reproduce the error.
- `resume_action` reads the key from the persisted Action and flips
  the sentinel on terminal state.

### 1.2 Discord worker activation (Phase 4.2)

No worker code changes. Phase 4 delivers:

- Exact test-webhook activation steps in
  `docs/system/control_plane.md#42-discord-approval-worker--test-vs-production`.
- Exact production activation commands, clearly marked as
  documentation, not executed.
- Confirmation the worker still imports zero `core.action_system`
  modules — decoupling invariant preserved.

### 1.3 Third workflow migration (Phase 4.3)

- New wrapper `scripts/scheduled/weekly_review_cp.py`.
- Risk `low` (design §4.2 rationale: read-heavy, no state mutation,
  $1.00 budget already capped inside the .sh).
- Idempotency key `weekly_review:<ISO-week>`, TTL 6 days.
- First two wrappers retrofitted with idempotency:
  - `morning_prep_cp.py`: `morning_prep:<UTC-date>`, 23h TTL.
  - `nightly_consolidation_cp.py`: same pattern; dry-run uses a
    distinct prefix so it never claims the real slot.

### 1.4 Decision log query CLI (Phase 4.4)

- New `scripts/decisions.py` — read-only, imports nothing from
  `core.action_system`.
- Commands: `list`, `show <decision_id>`, `for-action <action_id>`.
- Filters: `--agent`, `--context`, `--since`, `--today`, `--limit`,
  `--json`.

### 1.5 Snooze wake-up completion (Phase 4.5)

- `deferred_status.wake_due_snoozed()` — scans sidecars, promotes
  `snoozed → pending` when `snoozed_until <= now`, leaves a
  `"auto-woken at <iso>"` note.
- `deferred_status.list_overdue_snoozed()` — read-only companion used
  by `--dry-run` and `list --overdue-snoozed`.
- `scripts/deferred.py wake` subcommand (`--dry-run` supported).
- `scripts/deferred.py list --overdue-snoozed` filter.
- **Waking never auto-executes** — the explicit approval path via
  `resume_action` remains the single approval pathway.
- Stale / wake interaction verified: snoozed items are immune from
  `mark_stale_over_threshold` until wake promotes them to pending.

### 1.6 Idempotency CLI (sibling to 4.1)

- `scripts/deferred.py idempotency list [--expired]`
- `scripts/deferred.py idempotency show <key-or-sha>`
- `scripts/deferred.py idempotency clear <key-or-sha>`
- `scripts/deferred.py idempotency prune`

### 1.7 Documentation (Phase 4.7)

- `docs/system/control_plane.md` gains a Phase 4 section covering
  every bullet above, including the cron-readiness table.

---

## 2. Validation results

Run via `/tmp/phase4_validation.py` — a synthetic-only harness that
never touches the real weekly_review.sh or a production webhook.

| # | Scenario | Outcome |
|---|---|---|
| 1 | Idempotency happy path (`shell_command`) | **PASS** — dup returns `skipped_duplicate` pointing at original action_id |
| 2 | Idempotency TTL expiry | **PASS** — fresh action after sleep > TTL |
| 3 | Idempotency + deferred + drop + retry | **PASS** — dropped deferred file unblocks next claim |
| 4 | Idempotency + resume flips sentinel | **PASS** — resume_action flips `deferred → executed` |
| 5 | Idempotency + failure allows retry | **PASS** — failed sentinel does not block retry |
| 6 | `list_all` + `prune_expired` | **PASS** — two expired sentinels pruned |
| 7 | `decisions.py list` | **PASS** — rc=0, table rendered |
| 8 | `weekly_review_cp.py --help` + fixture validation + real-path validation | **PASS** — both fixture and real weekly_review.sh path pass validator |
| 9 | Snooze wake-up | **PASS** — overdue listed, woken, sidecar flipped to pending |
| 10 | Stale-check ignores snoozed, acts post-wake | **PASS** — both halves verified |
| 11 | Discord worker `--once` with no webhook | **PASS** — rc=0, no POST attempted |

**No real workflow was executed. No production webhook was touched.**

---

## 3. Edge cases covered

- **Crash during in_flight.** Expired `in_flight` is treated as a
  crashed prior run; next call overwrites. Operator recovery via
  `idempotency clear <key>`.
- **Dropped deferred + idempotency.** Covered by explicit file-exists
  check in `run_action`. Verified end-to-end in validation step 3.
- **Dry-run collision.** `nightly_consolidation_cp --dry-run` uses a
  distinct key prefix so operators running a dry check don't lock
  out the real nightly run.
- **Validator rejection.** Sentinel is cleared on rejection so the
  next call reproduces the error. Intentional — rejections are caller
  bugs, not lockable work.
- **`resume_action` with no key.** Handled by the
  `if action.idempotency_key:` guard — resuming a pre-Phase-4
  deferred file is a no-op on the sentinel store.
- **Snoozed + stale interaction.** Snoozed items are immune from
  stale pruning until wake; validated in step 10.

---

## 4. Deviations from design

**One minor deviation: `nightly_consolidation_cp` dry-run key.**

The design specified `nightly_consolidation:<UTC-date>` as the key.
I split it into `nightly_consolidation:<UTC-date>` and
`nightly_consolidation_dry:<UTC-date>` so a `--dry-run` invocation
cannot claim the real daily slot. This is strictly safer than what
the design spelled out and matches the design's own rule that dry
runs should not interfere with real runs.

**No other deviations.** Every other file, module, and behaviour
matches §5 and §6 of the design exactly.

---

## 5. Backwards compatibility

- **Old deferred files → new code.** `load_deferred` filters by
  `valid_keys`, so old files without `idempotency_key` load with the
  dataclass default of `None`. Verified by re-reading
  `deferred.py:42-50` and by running `resume_action` against a fresh
  action in validation step 4.
- **New deferred files → old code (rollback scenario).** Same filter
  drops the unknown field silently. No crash.
- **Callers without `idempotency_key`.** `run_action` preserves
  pre-Phase-4 behaviour byte-for-byte when the kwarg is `None`.
  Verified by morning_prep_cp/nightly_consolidation_cp tests prior to
  their own idempotency retrofit.

---

## 6. Files created

| Path | Role |
|---|---|
| `core/action_system/idempotency.py` | Sentinel store |
| `scripts/scheduled/weekly_review_cp.py` | Third workflow wrapper |
| `scripts/decisions.py` | Decision log CLI |
| `docs/audits/2026-04-08-control-plane-phase-4.md` | This report |
| `tests/fixtures/noop.sh` | Validation fixture (created by the harness) |

## 7. Files modified

| Path | Change |
|---|---|
| `core/action_system/actions.py` | Added `idempotency_key` field |
| `core/action_system/control_plane.py` | Pre-flight + post-exec idempotency integration |
| `core/action_system/deferred_status.py` | `wake_due_snoozed` + `list_overdue_snoozed` |
| `scripts/deferred.py` | `wake`, `idempotency` subcommands, `list --overdue-snoozed` |
| `scripts/scheduled/morning_prep_cp.py` | Idempotency key + TTL |
| `scripts/scheduled/nightly_consolidation_cp.py` | Idempotency key + TTL (dry-run safe) |
| `docs/system/control_plane.md` | Phase 4 section |

## 8. Files explicitly NOT touched

- `core/action_system/validator.py`
- `core/action_system/policy.py`
- `core/action_system/executor.py`
- `core/action_system/notifier.py`
- `scripts/workers/discord_approval_worker.py`
- Any `scripts/scheduled/*.sh`
- `/etc/cron.d/*` and the root crontab

---

## 9. Readiness for Phase 5

Phase 4 clears every item the Phase 3 audit flagged. Phase 5 scope
(tentative, from the design doc §10):

1. **Decision outcomes.** Add an `outcome` field to decision records,
   flipped asynchronously when the related action reaches terminal
   state. Makes `decisions.py` answer "did we get what we decided to
   get?"
2. **Production Discord activation.** First live webhook POST, under
   tmux for first 24h, then systemd unit.
3. **Cron swap.** Flip the three ready wrappers live, one at a time,
   after a week of parallel operation where we can compare bash vs
   wrapper outputs.
4. **Per-agent policies.** Already flagged in Phase 1 limitations.
5. **Dry-run mode for `run_action`.** Stop after validation and emit
   a plan — distinct from deferred state because it never writes to
   the deferred queue.

**No blockers identified.** Phase 4 is complete and every validation
scenario from the design passes.
