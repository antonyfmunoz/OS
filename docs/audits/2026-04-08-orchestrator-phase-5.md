# Control Plane Phase 5 — Orchestrator Audit

**Date:** 2026-04-08
**Scope:** Workflow Orchestrator + Autonomous Execution Layer
**Author:** Developer Agent

## What was built

New package: `core/orchestrator/`

| File             | Purpose |
|------------------|---------|
| `pipeline.py`    | `Pipeline`, `ActionStep`, `FuncStep`, `run_pipeline()` — sequential composition on top of `run_action()`. |
| `orchestrator.py`| `Orchestrator` class, named workflow registry, per-workflow state tracking persisted to `logs/orchestrator_state.json`, `default_orchestrator()` singleton. |
| `signals.py`     | Filesystem-backed signal mailbox. `define_signal`, `emit_signal`, `register_handler`, `list_pending`, `mark_processed`. Bindings persisted to `logs/signals/bindings.json`. |
| `loop.py`        | `run_cycle()` — deterministic 4-step cycle (drain signals → stale deferred → failures → report). `run_forever()` for dev. `LoopConfig` for tuning. One-shot-per-day suppression of retry/escalate decisions. |
| `workflows.py`   | `register_default_workflows()` — wires the 3 migrated CP workflows (morning_prep, nightly_consolidation, weekly_review) as orchestrator-callable workflows; binds default signals (`morning_ready`, `nightly_cycle`, `weekly_cycle`). |
| `__init__.py`    | Package marker. |

New script: `scripts/orchestrator_loop.py`

- CLI runner: `--cycles N`, `--forever`, `--interval`, `--stale-deferred-seconds`.
- Registers default workflows on startup.
- Prints `CycleReport` as JSON per cycle.

Docs:

- `docs/system/orchestrator.md` — architecture, pipeline model, signal model, loop behavior, examples, limitations.
- `docs/audits/2026-04-08-orchestrator-phase-5.md` — this file.

## How it integrates with the Control Plane

**Non-negotiable rule:** every side effect goes through `run_action()`.
The orchestrator enforces this structurally:

- `ActionStep` is a descriptor — it literally cannot execute anything
  without calling `run_action()`. Idempotency, validation, deferral,
  notifier, logging all still apply per step.
- `FuncStep` is explicitly scoped to pure in-memory transforms. Docs
  call this out; audit trail records it.
- Callable-style workflows (used for the 3 migrated CP workflows) are
  expected to invoke `run_action()` internally — and they already do,
  because they were migrated in Phase 2/3.
- The loop NEVER executes actions directly. It *requests* retries and
  escalations by emitting signals, leaving actual follow-up to
  operator-owned handler workflows.
- Every pipeline run writes a single `log_decision()` entry; every
  loop cycle writes per-decision entries for retry/escalate/stale.
  The audit trail is unified with the existing execution + decision
  logs.

## Validation results

Ran 6 synthetic tests against a fresh `Orchestrator` instance:

| # | Test | Result |
|---|------|--------|
| 1 | Simple 2-step pipeline executes sequentially | ✅ both steps `ok` |
| 2 | `stop_on_fail=True` halts on first failure; later steps marked `skipped` | ✅ `ok, failed, skipped` |
| 3 | `FuncStep` populates context; downstream `ActionStep.inputs_fn` reads it | ✅ computed value `42` flows into shell command |
| 4 | Orchestrator workflow registration + `run_workflow()` + state record | ✅ `total_runs=1`, `last_status=ok` |
| 5 | `emit_signal` + `run_cycle()` drains emission and triggers bound workflow | ✅ 1 drained, 1 triggered, 0 pending after |
| 6 | Pipeline step with `idempotency_key` — second run returns `skipped_duplicate`, pipeline treats as ok | ✅ `skipped=True` on second run |

Additional integration checks:

- **Loop runner smoke test:** `scripts/orchestrator_loop.py --cycles 1`
  completed cleanly, emitted cycle report with non-zero failure detection
  against the synthetic failures left in today's execution log by test 2.
- **One-shot follow-up across process restarts:** ran `run_cycle()` twice
  in separate Python invocations. Second invocation reported `failures=0`
  because the first invocation's decision log entries were found by
  `_already_followed_up()`. Confirms no runaway re-escalation.
- **Imports:** all 5 modules import cleanly. No circular dependencies.

## Limitations (v1)

See `docs/system/orchestrator.md#limitations-v1` for the full list.
Summary:

- No scheduler — cadence is cron/systemd/tmux.
- No DAG — pipelines are strictly sequential.
- No cross-process lock on `run_cycle()` — cron grain makes it safe in practice.
- Retry allowlist is hand-written (`shell_command`, `call_api` + idempotency key required).
- One-shot-per-day suppression is tied to today's decision log — a failure at 23:59 UTC could be re-examined after midnight (intentional).
- `FuncStep` has weaker audit trail than `ActionStep`.

## Recommended Phase 6 scope

Phase 5 gives us safe, composable orchestration. Phase 6 should focus on
**making decisions smarter without breaking determinism**:

1. **Operator-owned handler workflows** for the loop-emitted signals
   (`deferred_stale`, `action_failed`, `action_retry_requested`). Right
   now the loop emits and nothing is bound — these pile up in `pending/`
   until an operator wires handlers. Build:
   - `stale_deferred_notifier` — Discord notification for deferred
     actions past threshold.
   - `action_failed_triage` — log + notify + optionally re-propose
     failed action with adjusted risk.
   - `retry_runner` — re-invoke the original action via `run_action()`
     with the same idempotency key.

2. **Scheduler integration.** Wire cron to call
   `scripts/orchestrator_loop.py --cycles 1` every 5m, plus dedicated
   entries that emit `morning_ready`/`nightly_cycle`/`weekly_cycle`
   instead of calling the CP workflows directly. This collapses all
   scheduling through the signal layer.

3. **Pipeline library.** Replace the 3 CP workflows' internal shell
   call patterns with actual `Pipeline` definitions in a new
   `core/orchestrator/pipelines/` directory. Gives us composable
   primitives (morning_fetch_inbox, morning_brief_publish, etc.) that
   can be reused across workflows.

4. **DAG-lite.** If sequential pipelines become the bottleneck,
   introduce explicit `parallel_group` steps that fan out to N pipelines
   and join on completion. Keep it bounded — no generalized DAG engine.

5. **Observability.** A `scripts/orchestrator_status.py` CLI that reads
   `orchestrator_state.json`, pending signal counts, deferred queue
   depth, and recent cycle reports into a single dashboard.

6. **Handler contracts.** Formalize the payload schema for each
   loop-emitted signal so handlers can type-check without re-inventing
   shapes.

**Out of scope for Phase 6:** ML-based retry policy, distributed
execution, DB-backed state, full agent loop. Keep the philosophy —
filesystem-first, deterministic, Control Plane underneath everything.
