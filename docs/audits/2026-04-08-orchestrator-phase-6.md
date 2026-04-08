# Orchestrator Phase 6 — Operator Intelligence Layer

**Date:** 2026-04-08
**Scope:** Signal handler workflows, decision logic, operator CLI,
workflow decomposition, cron→signal mapping (doc-only).
**Prior phases:** 1 (run_action), 2 (deferred), 3–5 (CP workflow
migration + orchestrator + signals + loop).

---

## Goal

Phases 1–5 delivered a safe, orchestrated Control Plane: every
side effect goes through `run_action`, workflows compose via
`Pipeline`, a filesystem-backed signal layer feeds the autonomous
loop, and three production cron jobs are wrapped (morning_prep,
nightly_consolidation, weekly_review).

Gap at the start of Phase 6: the loop *emits* `deferred_stale`,
`action_failed`, and `action_retry_requested` signals, but nothing
consumes them. The system had observation without reaction.

Phase 6 closes that loop without granting the observer execution
authority. Handlers react through the Control Plane; the loop
continues to never execute directly.

---

## What shipped

### 1. Signal handler workflows (`core/orchestrator/handlers.py`)

Three handlers, registered on `default_orchestrator()` and bound
via `register_default_workflows()`:

| Signal | Handler | Side effect |
|---|---|---|
| `deferred_stale` | `handle_deferred_stale` | Log decision + append operator notice to deferred notifications queue. **Never auto-approves.** |
| `action_failed` | `handle_action_failed` | Re-checks `should_ignore`, otherwise logs escalation + notifier notice. |
| `action_retry_requested` | `handle_action_retry_requested` | Re-checks `should_retry`; if still eligible, dispatches a new `run_action` with key `retry:<original_id>:<utc_date>`; otherwise escalates. |

**Invariants:**
- Handlers never re-emit the signal they handle (no cascade loops).
- Handlers never bypass `run_action`; the retry path goes through
  the full Control Plane lifecycle, including idempotency dedup.
- Every handler returns `{"ok": bool, ...}` so the orchestrator
  and loop reports stay uniform.

### 2. Decision helpers (`core/orchestrator/decisions.py`)

Deterministic predicates:

- `should_retry(action)` — true iff type ∈ `{shell_command, call_api}`,
  idempotency key present, risk not high, and today's retry count
  for this action id is below `MAX_RETRIES_PER_DAY` (default 1).
- `should_escalate(action)` — `not should_retry(action)`. Escalation
  is the safe default.
- `should_ignore(action)` — narrow: only `idempotency_skip` actions
  with `result.ok = True`. Everything else is handled.
- `retry_count_today(action_id)` — derives the count from today's
  decision log (contexts `orchestrator.loop.retry` and
  `orchestrator.handler.retry`). Single source of truth; no separate
  counter file.

Rules intentionally mirror `LoopConfig` defaults so the loop and
handlers agree on what "retryable" means.

### 3. Operator status CLI (`scripts/orchestrator_status.py`)

Read-only snapshot with five sections:

1. **Pending signals** — per-signal count, oldest age, bound handlers.
2. **Deferred queue** — total count, by risk level, oldest entry id + age.
3. **Recent workflows** — per-workflow last run, status, duration,
   totals (sourced from `logs/orchestrator_state.json`).
4. **Recent failures (today)** — grouped by action id, from today's
   execution log.
5. **Loop activity (today)** — counts of `orchestrator.loop.*` and
   `orchestrator.handler.*` decisions, last decision timestamp.

Flags: `--json` for machine consumption, default is compact text.
Safe to call from cron, tmux status bar, or ad-hoc shell.

### 4. Workflow decomposition (`core/orchestrator/steps.py`)

Extracted the `_cp.py` wrapper pattern into a reusable helper:

- `ScriptWorkflowSpec` — declarative shape (name, script, description,
  risk, timeout, idempotency key, reasoning).
- `run_script_workflow(spec, *, approve)` — runs the full boilerplate
  (decision log → run_action → JSON summary → exit code mapping).
- `script_step(...)` / `api_step(...)` — `ActionStep` factories for
  use inside a `Pipeline`, so future workflows can declare pipeline
  composition without restating the full ActionStep kwarg surface.

**Before/after line counts** (wrapper main functions):

| Wrapper | Before | After |
|---|---|---|
| `morning_prep_cp.py` | ~70 | ~30 |
| `nightly_consolidation_cp.py` | ~90 | ~45 |
| `weekly_review_cp.py` | ~95 | ~40 |

Each wrapper keeps ownership of its idempotency key shape (daily
vs ISO-week) because that's the one genuinely per-workflow knob.

### 5. Cron → signal transition mapping (doc only)

**Not applied.** This is the target topology for Phase 7, documented
here so the migration can be reviewed before touching cron.

Current cron (relevant lines only):

```
30 5 * * * bash /opt/OS/scripts/scheduled/morning_prep.sh
0  3 * * * bash /opt/OS/scripts/scheduled/nightly_consolidation.sh >> ...
0  6 * * 0 bash /opt/OS/scripts/scheduled/weekly_review.sh
0  6 * * * cd /opt/OS && python3 eos_ai/orchestrator.py >> ...
```

Target topology:

| Cron line | Emits signal | Handler (already registered) |
|---|---|---|
| `30 5 * * *` | `morning_ready` | `morning_prep` |
| `0 3 * * *` | `nightly_cycle` | `nightly_consolidation` |
| `0 6 * * 0` | `weekly_cycle` | `weekly_review` |
| `*/5 * * * *` (new) | — (drains signals) | `scripts/orchestrator_loop.py --cycles 1` |

Migration sketch (do NOT apply without Phase 7 review):

```cron
# Cron as emitter only — one-liners that push a signal file
30 5 * * * python3 -c "import sys; sys.path.insert(0,'/opt/OS'); \
           from core.orchestrator.signals import emit_signal; \
           emit_signal('morning_ready')"
0 3 * * *  python3 -c "import sys; sys.path.insert(0,'/opt/OS'); \
           from core.orchestrator.signals import emit_signal; \
           emit_signal('nightly_cycle')"
0 6 * * 0  python3 -c "import sys; sys.path.insert(0,'/opt/OS'); \
           from core.orchestrator.signals import emit_signal; \
           emit_signal('weekly_cycle')"

# Loop drainer — the only thing that actually runs workflows
*/5 * * * * python3 /opt/OS/scripts/orchestrator_loop.py --cycles 1 \
            >> /opt/OS/logs/orchestrator_loop.log 2>&1
```

**Why this is better:**
- Decouples *when to trigger* from *what to run*. Signal bindings
  change in one file (`bindings.json`), not in crontab.
- A missed run is recoverable: the signal sits in `pending/` until
  the next drainer cycle. Today a missed cron line is just gone.
- Adding a new reactor is a code change, not a cron change.
- Operator can replay: `emit_signal('morning_ready')` from a shell
  triggers the same path cron would.

**Risks to address before applying:**
- The `*/5` drainer cadence must be reconciled with any deferred
  approval expectations (currently the loop's stale threshold is
  6h; unchanged).
- Timezone: current cron is local time. The `emitted_at` field is
  UTC. No actual conflict — just noting so the operator doesn't
  chase a phantom drift.
- Nightly maintenance (`0 2 * * *`) is **not** in scope for this
  migration; it remains a raw bash line.

---

## Validation (Phase 6 smoke)

All executed in-session against the live VPS:

1. **Decision helpers** — 5 assertions covering retry-eligible,
   non-eligible type, high-risk, missing-idempotency, ignore-path.
   All pass.
2. **deferred_stale end-to-end** — emitted a synthetic signal,
   ran one `run_cycle()`, confirmed `handle_deferred_stale` returned
   `ok`, pending count dropped to 0, decision log wrote
   `orchestrator.handler.deferred_stale`.
3. **action_failed drain** — six pre-existing pending `action_failed`
   emissions (from prior loop runs) drained in the same cycle, all
   handlers returned ok, operator notices appended to
   `logs/deferred/notifications.jsonl`.
4. **action_retry_requested** — emitted a synthetic `shell_command`
   retry payload with an idempotency key; handler ran, invoked
   `run_action` with key `retry:<id>:<date>`, returned
   `retry_status=executed`.
5. **Status CLI** — reflected the updated state correctly:
   workflow run counts, loop/handler decision counts, zero pending
   signals, zero deferred, recent failures still visible.
6. **Wrapper refactor** — imported each `_cp.py` module, confirmed
   `main()` callable present. No behavioral change (same
   `run_script` action, same idempotency keys, same exit codes).

No execution bypassed the Control Plane. Retries passed through
the full `propose → validate → approve → execute → log` cycle.

---

## Files added / changed

**Added:**
- `core/orchestrator/decisions.py`
- `core/orchestrator/handlers.py`
- `core/orchestrator/steps.py`
- `scripts/orchestrator_status.py`
- `docs/audits/2026-04-08-orchestrator-phase-6.md` (this file)

**Changed:**
- `core/orchestrator/workflows.py` — register handlers + bind signals
- `scripts/scheduled/morning_prep_cp.py` — use `run_script_workflow`
- `scripts/scheduled/nightly_consolidation_cp.py` — use `run_script_workflow`
- `scripts/scheduled/weekly_review_cp.py` — use `run_script_workflow`

**Unchanged on purpose:**
- `core/orchestrator/loop.py` — still the only place that *emits*
  these signals. The loop's authority boundary is unchanged.
- All `.sh` scripts — wrapper refactor is Python-only.
- Crontab — Phase 7.

---

## Readiness for autonomy

What Phase 6 unlocks:
- The loop can fail-safe: stale deferrals and failed actions now
  have a reactor, so the operator gets a single notification stream
  rather than needing to tail multiple logs.
- Retries are bounded, audited, and idempotent. A single line in
  the decision log tells you why any retry happened and when.
- The status CLI is the canonical "how is the orchestrator doing"
  view — no more chasing pending files across `logs/signals/*`.

What Phase 6 deliberately does NOT unlock:
- No auto-approval of deferred actions. Stale deferrals get
  surfaced, not greenlit.
- No self-scheduled cycles. Cadence still belongs to cron /
  systemd / the operator.
- No ML. Decisions remain a hand-written ruleset in one file.

Next recommended phase: apply the cron → signal mapping above with
a real drainer cadence, then start binding non-cron signals (e.g.
`budget_threshold_crossed`, `meeting_finished`) into Phase-7
handler workflows.
