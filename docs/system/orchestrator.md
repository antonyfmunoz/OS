# Orchestrator (Control Plane Phase 5)

The orchestrator is a thin, deterministic execution coordinator built on
top of the Control Plane. It never bypasses `run_action()`. It adds no
database, no broker, no scheduler. Its only jobs are:

1. **Compose** actions into pipelines.
2. **Name** pipelines/callables as workflows.
3. **React** to signals by dispatching workflows.
4. **Follow up** on stale deferred actions and recent failures.

## Architecture

```
cron / systemd / tmux loop
          │
          ▼
 scripts/orchestrator_loop.py  ◄─── one-shot or --forever
          │
          ▼
 core/orchestrator/loop.py         ◄─── run_cycle()
     │      │        │
     │      │        └── _scan_failures()    ─ emits action_failed / action_retry_requested
     │      └── _scan_stale_deferred()       ─ emits deferred_stale
     └── _drain_signals()                    ─ dispatches workflows
                │
                ▼
 core/orchestrator/orchestrator.py ◄─── run_workflow(name, context)
                │
                ├── Pipeline  → core/orchestrator/pipeline.py → run_pipeline()
                │                                                   │
                │                                                   ▼
                │                                            run_action() per step
                └── callable  → invokes run_action() internally
```

## Pipeline model

A `Pipeline` is an ordered list of `Step`s. Each step is one of:

- **`ActionStep`** — a descriptor whose fields map directly to
  `run_action()`. Supports static `inputs`, or a dynamic `inputs_fn`
  that receives the shared `context` dict. Same for `idempotency_key`
  via `idempotency_key_fn`.
- **`FuncStep`** — a plain Python callable receiving `context` and
  returning a dict. Intended for pure in-memory transforms between
  side-effectful steps. Side effects belong in `ActionStep`.

Each step's result is written back to `context[step.name]`, so later
steps can read earlier outputs via `ctx["s1"]["stdout"]` (or whatever
the result shape is).

Rules:

- Steps run sequentially.
- `stop_on_fail=True` (default) halts the pipeline on any non-`ok`
  step; later steps are marked `skipped`.
- Idempotency is per-step, not per-pipeline. A pipeline itself is just
  a deterministic walker.
- Every `ActionStep` passes through full Control Plane lifecycle:
  propose → validate → approve → execute → log. Deferral, notifier,
  idempotency sentinel all still apply.
- Pipeline execution emits one high-level `log_decision` record
  capturing the choice to run and the overall outcome.

Pipeline status translation (Action → pipeline):

| Action status        | Pipeline step status |
|----------------------|----------------------|
| `executed`           | `ok`                 |
| `skipped_duplicate`  | `ok` (if result ok)  |
| `deferred`           | `deferred`           |
| `rejected`           | `rejected`           |
| `failed` / other     | `failed`             |

## Workflow registry

`Orchestrator` is a named map of workflows. A workflow is either:

- a `Pipeline`, or
- a callable `(context: dict) -> dict` that itself uses
  `run_action()` internally.

API:

```python
from core.orchestrator.orchestrator import default_orchestrator

orch = default_orchestrator()
orch.register_workflow("morning_prep", pipeline_or_callable)
orch.run_workflow("morning_prep", context={...})
```

State is persisted to `/opt/OS/logs/orchestrator_state.json` after
every run: last_run_at, last_status, last_duration_s, total_runs,
total_failures per workflow. The loop reads this file to reason about
recent activity without re-parsing execution logs.

## Signal / event layer

Signals are filesystem-backed mailboxes. Each signal lives at
`/opt/OS/logs/signals/<name>/` with `pending/` and `processed/`
subdirectories. Handler bindings are stored in a single
`bindings.json` alongside so they survive process restarts.

API:

```python
from core.orchestrator.signals import (
    define_signal, emit_signal, register_handler,
)

define_signal("morning_ready")
register_handler("morning_ready", "morning_prep")
emit_signal("morning_ready", payload={"source": "cron"})
```

Default bindings registered by `register_default_workflows()`:

| Signal            | Handler workflow         |
|-------------------|--------------------------|
| `morning_ready`   | `morning_prep`           |
| `nightly_cycle`   | `nightly_consolidation`  |
| `weekly_cycle`    | `weekly_review`          |

Loop-emitted signals (no default handler):

| Signal                     | Emitted by                  | Payload             |
|----------------------------|-----------------------------|---------------------|
| `deferred_stale`           | stale deferred scan         | action_id, age      |
| `action_failed`            | failure scan — escalation   | failed action blob  |
| `action_retry_requested`   | failure scan — retry branch | failed action blob  |

Operators bind handler workflows to these when they want the loop's
findings to drive follow-up action.

## Autonomous loop

One call to `run_cycle()` does exactly four things, in this order:

1. **Drain signals.** For every pending emission, look up the
   signal's bound handlers and dispatch each via
   `orch.run_workflow(name, context=...)`. Move the emission file to
   `processed/` with an `ok` or `failed` suffix.
2. **Scan stale deferred.** Any action in the deferred queue older
   than `stale_deferred_seconds` (default 6h) gets a decision log
   entry and a `deferred_stale` signal emission.
3. **Scan recent failures.** Read the tail of today's execution log.
   For each unique failed action:
   - **Retry branch**: action type is in `retry_eligible_types`
     (`shell_command`, `call_api`) AND the action has an
     `idempotency_key` → log a retry decision, emit
     `action_retry_requested`.
   - **Escalate branch**: otherwise → log an escalate decision, emit
     `action_failed`.
   - **One-shot per day**: a check against today's decision log
     ensures the same action id is never retried/escalated more than
     once per day, even across process restarts.
4. **Return report.** `CycleReport` dict with counts and details.

**Safety:**

- No infinite loops inside `run_cycle()`.
- No retries inside the loop itself — it *requests* retries via
  signals, leaving actual re-execution to operator-owned workflows.
- Every decision is written to `log_decision()` with a reason string.

**`run_forever()`** is provided for dev use. Production should use
cron/systemd/tmux with `scripts/orchestrator_loop.py --cycles 1`.

## Examples

### Example 1 — research → summarize → store → notify

```python
from core.orchestrator.pipeline import Pipeline, ActionStep, run_pipeline

pipeline = Pipeline(
    name="research_flow",
    steps=[
        ActionStep(
            name="research",
            type="run_script",
            description="gather sources",
            inputs={"path": "scripts/research.py", "args": ["--topic=foo"]},
            explicit_approval=True,
        ),
        ActionStep(
            name="summarize",
            type="run_script",
            description="summarize gathered sources",
            inputs_fn=lambda ctx: {
                "path": "scripts/summarize.py",
                "args": ["--input", ctx["research"].get("stdout", "")],
            },
            explicit_approval=True,
        ),
        ActionStep(
            name="store",
            type="write_file",
            description="store summary",
            inputs_fn=lambda ctx: {
                "path": "/opt/OS/logs/research_summary.md",
                "content": ctx["summarize"].get("stdout", ""),
            },
            explicit_approval=True,
        ),
        ActionStep(
            name="notify",
            type="shell_command",
            description="ping Discord",
            inputs={"command": "echo notify"},
            explicit_approval=True,
        ),
    ],
)

result = run_pipeline(pipeline)
```

### Example 2 — signal triggers a workflow

```python
from core.orchestrator.workflows import register_default_workflows
from core.orchestrator.signals import emit_signal
from core.orchestrator.loop import run_cycle

register_default_workflows()
emit_signal("morning_ready", payload={"source": "alarm"})
run_cycle()  # will dispatch morning_prep
```

### Example 3 — cron entry

```
# crontab
*/5 * * * * cd /opt/OS && python3 scripts/orchestrator_loop.py --cycles 1 >> /opt/OS/logs/orchestrator.log 2>&1
```

## Limitations (v1)

- **No scheduler.** Cadence is the caller's job (cron, systemd, tmux).
- **No DAG.** Pipelines are strictly sequential. Fan-out/fan-in is not
  supported. Use multiple pipelines bound to the same signal if you
  need parallel-ish branches.
- **No cross-process locking on cycles.** Two simultaneous
  `run_cycle()` invocations could double-process a pending signal
  emission (the file atomic-move mitigates but doesn't eliminate the
  race). In practice cron's 1-minute grain makes this a non-issue.
- **No ML / heuristics for retry policy.** Retry eligibility is a
  hand-written allowlist on action type + presence of idempotency key.
- **One-shot-per-day suppression** is keyed on today's decision log.
  A failure on 23:59 UTC could be re-examined after midnight. This is
  intentional — a new day is a fresh chance to try.
- **No backpressure.** A stuck handler workflow would slow the loop.
  Use `--cycles 1` from cron to stay bounded.
- **FuncStep has no audit trail** beyond the pipeline's own decision
  log record. Keep side effects in ActionStep.

## Files

```
core/orchestrator/
    __init__.py
    pipeline.py       ─ Pipeline, ActionStep, FuncStep, run_pipeline
    orchestrator.py   ─ Orchestrator, default_orchestrator
    signals.py        ─ define/emit/register/list signals
    loop.py           ─ run_cycle, run_forever, LoopConfig
    workflows.py      ─ register_default_workflows (CP workflow bindings)

scripts/orchestrator_loop.py   ─ CLI runner
scripts/emit_signal.py         ─ cron-safe signal emitter (Phase 7)

logs/
    orchestrator_state.json    ─ per-workflow run records
    signals/                   ─ signal mailboxes + bindings
    decisions/                 ─ (shared with Control Plane)
    execution/                 ─ (shared with Control Plane)
```

---

## Phase 7 — Production Activation (2026-04-08)

As of 2026-04-08 the orchestrator loop runs live from cron and drains
the scheduled signal rhythm. This section documents the active
operational state; `docs/audits/2026-04-08-phase-7-activation.md` has
the full activation report.

### Active cron → signal mapping

| Schedule (UTC)  | Cron line                                                                             | Signal          | Bound workflow (via `register_default_workflows`) |
|-----------------|---------------------------------------------------------------------------------------|-----------------|--------------------------------------------------|
| `30 5 * * *`    | `python3 scripts/emit_signal.py morning_ready`                          | `morning_ready` | `morning_prep` → `morning_prep_cp.py` → `run_action` |
| `0 3 * * *`     | `cd /opt/OS && python3 scripts/emit_signal.py nightly_cycle`                          | `nightly_cycle` | `nightly_consolidation` → `nightly_consolidation_cp.py` → `run_action` |
| `0 6 * * 0`     | `cd /opt/OS && python3 scripts/emit_signal.py weekly_cycle`                           | `weekly_cycle`  | `weekly_review` → `weekly_review_cp.py` → `run_action` |
| `*/5 * * * *`   | `cd /opt/OS && python3 scripts/orchestrator_loop.py --cycles 1`                       | —               | drains pending signals + scans stale/failures    |

Latency from signal emission to workflow execution is bounded by the
loop cadence (≤5 minutes). Morning prep emitted at 05:30 runs no later
than 05:35. This is intentional slack — the loop is the single
chokepoint the operator can inspect, pause, or widen.

### How signal dispatch approves the wrapper

`core.orchestrator.workflows._wrap_main` injects `sys.argv = [module, "--approve"]`
around the `module.main()` call. The semantic: **the existence of the
signal→workflow binding in `bindings.json` is the operator's durable
pre-approval.** If the operator wants to pause a scheduled workflow,
they unbind the signal (or comment out the cron line) — they do NOT
need to race a daily deferred-approval queue. This keeps the Control
Plane's defer path reserved for ad-hoc or novel invocations.

### Inspecting pending signals

```bash
# Pending emissions per signal
for d in /opt/OS/logs/signals/*/pending; do
  n=$(ls "$d" 2>/dev/null | wc -l)
  [ "$n" -gt 0 ] && echo "$(basename $(dirname $d)): $n"
done

# Processed outcomes (last 5, any signal)
find /opt/OS/logs/signals/*/processed -name '*.json' -printf '%T@ %p\n' 2>/dev/null \
  | sort -rn | head -5 | cut -d' ' -f2-

# Signal bindings
cat /opt/OS/logs/signals/bindings.json
```

### Inspecting orchestrator state

```bash
# Per-workflow run history
cat /opt/OS/logs/orchestrator_state.json | python3 -m json.tool

# Last loop cycle (driven by cron */5)
tail -40 /opt/OS/logs/orchestrator_loop.log

# Today's decisions trail (includes every dispatched workflow)
tail -20 /opt/OS/logs/decisions/$(date -u +%Y-%m-%d)-decisions.jsonl

# Today's execution trail (every run_action call)
tail -20 /opt/OS/logs/execution/$(date -u +%Y-%m-%d)-execution.jsonl
```

### Manual signal emission

```bash
cd /opt/OS
python3 scripts/emit_signal.py weekly_cycle
python3 scripts/emit_signal.py nightly_cycle --payload-json '{"source":"manual"}'
```

The next `*/5` loop tick picks it up. For immediate execution:

```bash
python3 scripts/emit_signal.py weekly_cycle && \
  python3 scripts/orchestrator_loop.py --cycles 1
```

### Rollback

A crontab snapshot from before cutover is at
`/opt/OS/docs/audits/rollback/crontab-pre-phase7-2026-04-08.txt`.

```bash
crontab /opt/OS/docs/audits/rollback/crontab-pre-phase7-2026-04-08.txt
```

This restores the raw `bash ... .sh` lines and removes both the
emit_signal cron entries and the `*/5 orchestrator_loop` drain line.
The underlying `.sh` scripts were never modified, so rollback is
exact. `bindings.json` can remain in place — unbound signals are
inert.

### Known pre-existing drift

`logs/signals/bindings.json` still contains the legacy entry
`"test_sig": ["simple_test"]` from earlier dev work. `simple_test` is
not in `register_default_workflows()`, so every cron-driven loop tick
that sees a `test_sig` emission reports `"status": "unregistered"` for
that handler and moves on. Harmless but noisy. To remove:

```bash
python3 -c "
import sys; sys.path.insert(0,'/opt/OS')
from core.orchestrator.signals import unregister_handler
unregister_handler('test_sig', 'simple_test')
"
```
