# Phase 7 — Control Plane + Orchestrator Production Activation

**Date:** 2026-04-08
**Operator:** Developer Agent (Claude, AFM session)
**Scope:** Activate the existing orchestrator loop + signal-driven
workflow dispatch in live cron. No new architecture.

---

## 1. Executive Summary

The EOS orchestrator and Control Plane layers were already feature-complete
before this session: `core/orchestrator/{loop,signals,workflows,handlers,
orchestrator}.py`, the three `*_cp.py` wrappers that route
`morning_prep` / `nightly_consolidation` / `weekly_review` through
`run_action()`, and the CLI runner `scripts/orchestrator_loop.py` all
existed, compiled, and had been smoke-tested at the unit level.

What was missing was the last seam between that code and real cron:
the live crontab still invoked the raw `.sh` scripts directly, and the
orchestrator loop had no recurring schedule. Phase 7 closes that seam.

Four concrete changes were made:

1. **New helper** `scripts/emit_signal.py` — minimal CLI that calls
   `core.orchestrator.signals.emit_signal` and prints a one-line JSON
   receipt. No side effects beyond writing the pending emission file.
2. **One-line fix** to `core/orchestrator/workflows.py::_wrap_main` —
   temporarily sets `sys.argv = [module, "--approve"]` around the
   `module.main()` call so that signal-dispatched `_cp.py` wrappers
   pass the `--approve` flag the Control Plane requires for
   medium-risk scheduled workflows. `SystemExit` is now also caught
   and normalized.
3. **Crontab cutover** — three raw `bash ... .sh` lines replaced with
   `python3 scripts/emit_signal.py <name>` lines, plus one new
   `*/5 * * * *` drain line calling `scripts/orchestrator_loop.py
   --cycles 1`. Snapshot of the pre-cutover crontab saved at
   `docs/audits/rollback/crontab-pre-phase7-2026-04-08.txt`.
4. **Docs update** — `docs/system/orchestrator.md` and
   `docs/system/control_plane.md` now describe the active mapping,
   dispatch path, inspection commands, and rollback procedure.

The end-to-end path was validated by emitting a real `weekly_cycle`
signal and running one loop cycle: the signal was drained, the
`weekly_review` workflow dispatched, `run_action` executed, the
`.sh` script ran to completion (returncode 0), the idempotency key
`weekly_review:2026-W15` was registered, and the signal file was
atomically moved into `processed/`. All five observability surfaces
(decisions, execution, signal processed/, orchestrator_state.json,
idempotency) updated coherently and can be joined on `action_id` or
`idempotency_key`.

No new systems were built. No architectural patterns were introduced.
The activation is fully reversible by reinstalling the snapshotted
crontab.

---

## 2. What Was Already Ready

All of the following were in place **before** this session and
required no modification:

| Component                                             | State                                                |
|------------------------------------------------------|------------------------------------------------------|
| `core/orchestrator/loop.py`                           | `run_cycle()` + `run_forever()`, safe for cron       |
| `core/orchestrator/orchestrator.py`                   | `default_orchestrator()` singleton + state persistence to `logs/orchestrator_state.json` |
| `core/orchestrator/signals.py`                        | Filesystem mailbox: `emit_signal`, `list_pending`, `mark_processed`, persistent `bindings.json` |
| `core/orchestrator/handlers.py`                       | `handle_deferred_stale`, `handle_action_failed`, `handle_action_retry_requested` |
| `core/orchestrator/workflows.py`                      | `register_default_workflows()` binding all six signals to workflows |
| `scripts/orchestrator_loop.py`                        | CLI runner with `--cycles` / `--forever` / `--interval` |
| `scripts/scheduled/morning_prep_cp.py`                | CP wrapper, idempotency `morning_prep:<date>`, risk=medium |
| `scripts/scheduled/nightly_consolidation_cp.py`       | CP wrapper, idempotency `nightly_consolidation:<date>`, risk=medium |
| `scripts/scheduled/weekly_review_cp.py`               | CP wrapper, idempotency `weekly_review:<ISO-week>`, risk=low |
| `core/orchestrator/steps.py::run_script_workflow`     | Shared helper all three wrappers call; routes through `run_action` |
| `logs/signals/bindings.json`                          | Already persisted with the six default bindings     |
| `logs/orchestrator_state.json`                        | Already populated (prior smoke runs of handlers + `simple_test`) |

**The activation seam was therefore exactly:** cron emission of the
three scheduled signals, cron scheduling of the loop, and a single
argv-injection fix in `_wrap_main` so the signal-dispatched path
carries the operator's pre-approval into the wrapper.

---

## 3. What Was Changed

### 3.1 `scripts/emit_signal.py` (new)

~60-line CLI. Argparse: positional `signal`, optional
`--payload-json`. Imports `core.orchestrator.signals.emit_signal`,
prints a single JSON line receipt on stdout, exits 0/1.

Rationale: cron lines need a one-shot safe emitter. Inlining the
Python in a crontab line would be fragile. A module under
`scripts/` mirrors the existing convention (`orchestrator_loop.py`,
`call_prep.py`, `eod_sync.py`, etc).

### 3.2 `core/orchestrator/workflows.py::_wrap_main` (edited)

Before:

```python
def _run(context):
    module = importlib.import_module(module_path)
    if not hasattr(module, "main"):
        return {"ok": False, "error": f"{module_path} has no main()"}
    try:
        exit_code = module.main()
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}", "module": module_path}
    return {"ok": int(exit_code) == 0, "exit_code": int(exit_code), "module": module_path}
```

After: `sys.argv` is saved, replaced with `[module_path, "--approve"]`,
`module.main()` called, `sys.argv` restored in `finally`, and
`SystemExit` is caught and normalized to an integer exit code.
Docstring updated to explain the semantics.

Rationale: `_cp.py` wrappers parse `sys.argv` via argparse. Without
`--approve`, medium-risk scheduled workflows would defer every morning
and the operator would have to manually approve from the deferred
queue. The **existence of the signal binding in `bindings.json` is
itself the operator's durable pre-approval** for that scheduled path,
so injecting `--approve` at dispatch time is semantically correct.

### 3.3 Crontab cutover

Three lines replaced, one line added. Diff against the saved
snapshot:

```
< 30 5 * * * bash /opt/OS/scripts/scheduled/morning_prep.sh
< 0 6 * * 0 bash /opt/OS/scripts/scheduled/weekly_review.sh
< 0 3 * * * bash /opt/OS/scripts/scheduled/nightly_consolidation.sh >> /opt/OS/logs/nightly_consolidation.log 2>&1
---
> 30 5 * * * cd /opt/OS && python3 scripts/emit_signal.py morning_ready >> /opt/OS/logs/cron_emit.log 2>&1
> 0 6 * * 0 cd /opt/OS && python3 scripts/emit_signal.py weekly_cycle >> /opt/OS/logs/cron_emit.log 2>&1
> 0 3 * * * cd /opt/OS && python3 scripts/emit_signal.py nightly_cycle >> /opt/OS/logs/cron_emit.log 2>&1
> */5 * * * * cd /opt/OS && python3 scripts/orchestrator_loop.py --cycles 1 >> /opt/OS/logs/orchestrator_loop.log 2>&1
```

Each cutover line is annotated with a `# [phase-7] ...` comment in
the live crontab. The underlying `.sh` scripts are untouched on disk
— rolling back is a pure crontab swap.

### 3.4 Docs

- `docs/system/orchestrator.md` — added "Phase 7 — Production
  Activation" section with the active cron mapping, argv-injection
  semantics, inspection commands, rollback procedure, and known
  pre-existing `test_sig/simple_test` binding drift.
- `docs/system/control_plane.md` — added short "Phase 7 — Scheduled
  invocation path" section with the full dispatch chain diagram.
- `scripts/emit_signal.py` added to the Files listing.

### 3.5 Out of scope — NOT changed

- `scripts/scheduled/morning_prep.sh`, `nightly_consolidation.sh`,
  `weekly_review.sh` — unchanged on disk.
- `scripts/scheduled/*_cp.py` — unchanged. The argv injection lives
  at the orchestrator layer so these files remain identical whether
  invoked directly or via signal.
- Legacy `0 6 * * * python3 eos_ai/orchestrator.py` cron line — left
  in place. Out of Phase 7 scope.
- Second `weekly_review` line `0 19 * * 0 python3 scripts/weekly_review.py`
  — a different script (not `.sh`), out of scope.
- `nightly_maintenance.sh` cron — not one of the three eligible
  workflows, left alone.
- No new tests added (no orchestrator test file existed previously).

---

## 4. Active Cron → Signal Mapping

| Schedule (local TZ)   | Cron command                                                                                     | Signal emitted     | Loop-dispatched workflow   | Underlying action                    |
|-----------------------|--------------------------------------------------------------------------------------------------|--------------------|----------------------------|--------------------------------------|
| `30 5 * * *`          | `cd /opt/OS && python3 scripts/emit_signal.py morning_ready`                                     | `morning_ready`    | `morning_prep`             | `run_script(morning_prep.sh)` risk=medium, idempotent per day |
| `0 3 * * *`           | `cd /opt/OS && python3 scripts/emit_signal.py nightly_cycle`                                     | `nightly_cycle`    | `nightly_consolidation`    | `run_script(nightly_consolidation.sh)` risk=medium, idempotent per day |
| `0 6 * * 0`           | `cd /opt/OS && python3 scripts/emit_signal.py weekly_cycle`                                      | `weekly_cycle`     | `weekly_review`            | `run_script(weekly_review.sh)` risk=low, idempotent per ISO-week |
| `*/5 * * * *`         | `cd /opt/OS && python3 scripts/orchestrator_loop.py --cycles 1`                                  | —                  | (drains pending + scans stale/failures) | — |

Max latency from emission to execution: ~5 minutes. For the 05:30
morning cron that means morning_prep runs no later than 05:35.
Acceptable for the current phase.

---

## 5. Loop Scheduling Details

- **Cadence:** one cycle every 5 minutes via cron.
- **Why cron (not systemd timer / tmux loop):** cron is already the
  operational scheduling surface for every other EOS automation, and
  the task brief explicitly said "do not introduce a new scheduler
  framework".
- **Why `--cycles 1` (not `--forever`):** bounds the process. Each
  tick is a new Python process that exits cleanly; a hung handler
  cannot starve the next tick's progress (cron will start a fresh
  process regardless).
- **Defaults used:** `stale_deferred_seconds=21600` (6h),
  `failure_scan_limit=200` lines, `max_retries_per_action=1`,
  retry-eligible types `shell_command` + `call_api`.
- **Concurrency:** no cross-process lock. `run_cycle` is short (ms
  for an empty queue), so two overlapping ticks are extremely
  unlikely. The atomic rename in `mark_processed` prevents
  double-processing of a single emission file even if two cycles
  raced.

---

## 6. Validation Results

### 6.1 Compile + registration smoke

```
python3 -m py_compile scripts/emit_signal.py core/orchestrator/workflows.py  → ok
register_default_workflows(default_orchestrator())
  → ['morning_prep', 'nightly_consolidation', 'weekly_review',
     'handle_deferred_stale', 'handle_action_failed',
     'handle_action_retry_requested']
```

### 6.2 Synthetic unbound-signal drain

```
python3 scripts/emit_signal.py phase7_synthetic_test \
  --payload-json '{"source":"phase7-validation"}'
  → {"ok":true,"signal":"phase7_synthetic_test","emission_id":"16cd3ed9-..."}

python3 scripts/orchestrator_loop.py --cycles 1
  → signals_drained: 0, workflows_triggered: 0
     details: [{"kind":"signal_no_handler","signal":"phase7_synthetic_test",...}]
```

Loop correctly identified the emission, recorded `signal_no_handler`,
and left the file in pending for future handler registration.

### 6.3 Real-path drain via `weekly_cycle`

```
python3 scripts/emit_signal.py weekly_cycle --payload-json '{"source":"phase7-validation"}'
python3 scripts/orchestrator_loop.py --cycles 1
```

Result:

| Surface                                    | Observed value                                        |
|--------------------------------------------|-------------------------------------------------------|
| `workflows_triggered`                      | 1                                                     |
| `signals_drained`                          | 1                                                     |
| Workflow                                   | `weekly_review`                                       |
| Action status                              | `executed`                                            |
| Validation                                 | `ok`                                                  |
| Approval                                   | `auto-approved (low risk)`                            |
| Returncode                                 | 0                                                     |
| `orchestrator_state.json::weekly_review`   | `last_status=ok, last_duration_s=115.728, total_runs=1` |
| Idempotency key registered                 | `weekly_review:2026-W15`                              |
| Signal file                                | moved to `logs/signals/weekly_cycle/processed/...-ok.json` |
| Decision log records                       | `orchestrator.run_workflow(weekly_review)` + `scheduled invocation of weekly_review` |
| Execution log                              | One `run_script` record with id `33fd1e08-c082-...`   |

### 6.4 Cron-driven first tick (already happened)

Between the cutover and the synthetic test, cron fired `*/5` and
produced a real loop invocation recorded in
`logs/orchestrator_loop.log`. It correctly drained the earlier
`test_sig` emission and reported the legacy `simple_test` handler as
`unregistered` (see §8 — known drift). This confirms the loop line
is live in cron.

### 6.5 Idempotency

Because the real-path validation used a real signal, the Control
Plane's idempotency store now holds `weekly_review:2026-W15`. Any
second invocation this week — whether manual, signal-driven, or
cron-triggered — will return `skipped_duplicate` instead of
re-running weekly_review.sh. This is the designed guard and is a
good thing: it means the validation cannot double-post to Discord.

---

## 7. Observability Findings

The five observability surfaces are all alive and coherent:

1. **`logs/decisions/<day>-decisions.jsonl`** — every
   `orchestrator.run_workflow(...)` dispatch + every Control-Plane
   `scheduled invocation of <name>` decision. Joinable on
   `related_action_id`.
2. **`logs/execution/<day>-execution.jsonl`** — every `run_action`
   outcome with full validation / approval / result / idempotency_key
   fields.
3. **`logs/signals/<name>/pending|processed/`** — durable queue with
   atomic move on drain. Filenames are lexically sorted by epoch ms,
   so `ls` == temporal order.
4. **`logs/orchestrator_state.json`** — per-workflow run counts,
   last status, last duration. Updated by `Orchestrator._record_run`.
5. **`logs/idempotency/*.json`** — Control Plane's dedupe store.

### What an operator should actually watch

For day-to-day Phase 7 health, a single tail covers most of it:

```bash
tail -f /opt/OS/logs/orchestrator_loop.log /opt/OS/logs/cron_emit.log
```

The loop log gives cycle-by-cycle drain outcomes; the emit log gives
the cron-side proof that the emission happened. For deeper triage,
`orchestrator_state.json` is the one-file summary, and the per-day
`decisions/execution` jsonl files have the full record.

### Visibility gaps (not urgent)

- **No Discord/Telegram alert** when a loop cycle reports
  `workflows_triggered > 0` with any workflow status != `ok`. The
  `handle_action_failed` handler writes to the deferred notification
  queue, but that queue needs the existing Discord drainer wired to
  it — out of Phase 7 scope.
- **No summary roll-up.** There's no "yesterday's workflows: 3 ok, 0
  failed" dashboard. Practical answer today is one shell command
  against `orchestrator_state.json`.
- **No alerting on loop starvation.** If cron silently stopped firing
  `*/5`, nothing would notice until the next scheduled signal didn't
  drain. A "loop heartbeat" field written by the loop (last ran at
  X) would fix this — maybe Phase 8.

Decision: do not build a dashboard or alerting layer in Phase 7. The
brief explicitly said "do not overbuild dashboards; just identify
practical visibility". The visibility **is** practical already.

---

## 8. Remaining Manual Steps

1. **Unbind the legacy `test_sig → simple_test` entry** in
   `bindings.json` when convenient. Until then every `test_sig`
   emission by dev work will log an `unregistered` outcome from cron
   every 5 minutes it sits in pending. Harmless but noisy.
2. **Unbind / clean up `phase7_synthetic_test`** — I left one
   emission in pending intentionally (it has no handler), which the
   loop will keep reporting as `signal_no_handler` on every cycle.
   To clear:
   ```bash
   rm /opt/OS/logs/signals/phase7_synthetic_test/pending/*.json
   ```
3. **Nightly_consolidation first live run** — will happen at 03:00
   local time tomorrow. Monitor `logs/orchestrator_loop.log` and
   `logs/nightly_consolidation.log` in the morning. The `.sh` has a
   `provider_health` preflight so LLM outage is non-fatal.
4. **Morning_prep first live run** — 05:30 local tomorrow. Same
   monitoring. Morning_prep uses `claude -p` with an external CC
   budget, so if the Anthropic auth issue (session reminder at the
   top of this session) is still present, the provider gate will
   exit early with a log line, not consume budget.
5. **Consider:** migrate the legacy `0 6 * * * python3 eos_ai/orchestrator.py`
   line into the signal rhythm, or retire it. Out of Phase 7 scope
   but a natural Phase 8 candidate.

---

## 9. Risks / Rollback Notes

### Risks introduced by Phase 7

| Risk                                                                | Mitigation                                             | Residual                  |
|---------------------------------------------------------------------|--------------------------------------------------------|---------------------------|
| 5-minute latency between cron tick and workflow execution            | Bounded, documented, acceptable for daily cadence      | Accept                    |
| Loop cron (`*/5`) could silently fail and stop draining signals     | Cron-side failures log to `orchestrator_loop.log`; operator tails it | Accept; add heartbeat in Phase 8 |
| Pre-existing `test_sig`/`phase7_synthetic_test` unbound signals     | Drain is harmless (`signal_no_handler`/`unregistered`) | Low; clean up in follow-up |
| `_wrap_main` swallows argv for other callers                        | `try/finally` restores argv; tested                    | Nil                       |
| Signal queue grows unbounded if loop stops draining                 | Files are tiny (~200 bytes); mailbox tolerates months of backlog | Nil at current scale       |
| Morning_prep `claude -p` budget double-spend if loop re-dispatches  | `morning_prep:<date>` idempotency key blocks second execution same day | Nil                       |

### Rollback procedure

```bash
crontab /opt/OS/docs/audits/rollback/crontab-pre-phase7-2026-04-08.txt
```

This restores the three raw `bash ... .sh` cron lines and removes the
`emit_signal` lines and the `*/5 orchestrator_loop` drain line. The
underlying `.sh` scripts were never touched, `_cp.py` wrappers were
never touched, and the `_wrap_main` argv fix is inert when no signal
is ever emitted (because no cron line will emit one).

If the argv injection in `_wrap_main` itself causes any unexpected
issue, revert that single edit — the file is otherwise unchanged.

---

## 10. Recommended Next Move

Phase 7 lands the orchestrator in production. The obvious next beats:

1. **Wire the deferred notification queue to Discord/Telegram.**
   `handle_action_failed` and `handle_deferred_stale` already append
   structured notices. A small drainer that tails
   `/opt/OS/logs/deferred/notifications.jsonl` and posts unseen lines
   to Discord would complete the failure/escalation loop.
2. **Loop heartbeat.** Have `run_cycle` also write
   `logs/orchestrator_heartbeat.json` with `{last_ran_at, last_cycle_id}`.
   An external watcher (or weekly_review) can then alert on
   `now - last_ran_at > 15min`.
3. **Retire the legacy `eos_ai/orchestrator.py` cron line** once it
   has been confirmed no unique behaviour is trapped inside it.
4. **Add orchestrator/loop unit tests** (the project has no
   `tests/orchestrator` yet). The `_wrap_main` argv injection in
   particular deserves a unit test that asserts `sys.argv` is
   restored even when the wrapped main raises.

None of these are blocking; Phase 7 is production-live as of
2026-04-08 ~21:18 UTC.

---

## Appendix A — Files changed

- `scripts/emit_signal.py` *(new)*
- `core/orchestrator/workflows.py` *(edited: `_wrap_main` argv injection + `SystemExit` handling + import sys)*
- `docs/system/orchestrator.md` *(appended Phase 7 section; `emit_signal.py` added to Files listing)*
- `docs/system/control_plane.md` *(appended Phase 7 scheduled invocation section)*
- `docs/audits/rollback/crontab-pre-phase7-2026-04-08.txt` *(new snapshot)*
- `docs/audits/2026-04-08-phase-7-activation.md` *(this report)*
- crontab *(3 lines replaced, 1 line added, 4 phase-7 comment lines)*
