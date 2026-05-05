# Audit: Control Plane — Phase 1

**Date:** 2026-04-08 (spec dated 2026-04-06)
**Scope:** EOS Intelligence Layer, Phase 1 — Control Plane v1
**Status:** Built, validated end-to-end, ready for integration

## What was built

A centralized Action System that routes every meaningful agent action
through `propose → validate → approve → execute → log`.

### New files

```
core/action_system/actions.py         Action dataclass + propose_action()
core/action_system/validator.py       validate_action(), approve_action(), safety rules
core/action_system/executor.py        Dispatch for shell / script / file / API
core/action_system/logging.py         log_execution(), log_decision()
core/action_system/tme.py             Tool Mastery Engine advisory hook
core/action_system/control_plane.py   Public entry point: run_action()
scripts/control_plane_run.py          Reference CLI wrapping the whole pipeline
docs/system/control_plane.md          Architecture + usage docs
docs/audits/2026-04-06-control-plane-phase-1.md   This report
```

New directories:

```
core/                         First use of core/ namespace (governance, not agents)
logs/execution/               Append-only JSONL, one file per UTC day
logs/decisions/               Append-only JSONL, one file per UTC day
```

## How it works

`run_action(...)` constructs an `Action` object, then drives it through
five stages, logging the full record at every transition:

1. **propose** — builds Action, status=`proposed`, logs.
2. **validate** — checks required fields, allowed types, safety rules.
   Sets status=`validated` or `rejected`. Logs.
3. **approve** — auto-approves low risk, requires `explicit_approval=True`
   for medium/high. Sets status=`approved` or leaves at `validated`. Logs.
4. **execute** — dispatches to the executor for the action type.
   Sets status=`executed` or `failed`. Logs.
5. **log_decision** — separate helper for recording WHY.

Each lifecycle transition emits one JSONL line. A successful low-risk
action produces four log entries — a full replayable history.

## Validation results

All four lifecycle paths verified live:

| Case | Input | Final status | Notes |
|---|---|---|---|
| Happy path | `echo hello`, low risk | `executed` | Auto-approved, stdout captured |
| Reject | `rm -rf /`, low risk | `rejected` | Blocked by dangerous-token list |
| Defer | `ls /tmp`, medium risk, no approval | `validated` | Held for explicit approval |
| Approve | `ls /tmp`, medium risk, `explicit_approval=True` | `executed` | Ran as expected |

Log counts after smoke test:
- `logs/execution/2026-04-08-execution.jsonl` — 13 lines from 4 actions
- `logs/decisions/2026-04-08-decisions.jsonl` — 1 line from CLI invocation

Imports all compile cleanly:
```bash
python3 -m py_compile core/action_system/*.py  # → OK
python3 -c "from core.action_system.control_plane import run_action"  # → OK
```

## Integration points with TME

- `core/action_system/tme.py` shells out to `scripts/query_skills.py`
  via subprocess — no import-level coupling to TME internals.
- `run_action(consult_tme=True)` invokes `query_relevant_skills(description)`
  before executing and attaches the result to `action.result["tme_consult"]`.
- Advisory only in v1 — TME availability does not block execution.

This keeps the Control Plane robust if TME evolves, and makes the
integration a clear seam for v2 (where TME could be used to *validate*
approach, not just look up skills).

## What's missing for v2

- **Approval workflow** — right now it's a boolean flag. v2 needs a real
  queue with Discord/Telegram notifications and a resume-from-validated
  helper.
- **Dry-run mode** — validate+plan without executing, emit a summary.
- **Idempotency** — re-running the same action should be detectable.
- **Per-agent policy** — e.g., outreach agent can never touch production DB
  even at low risk. Needs integration with `eos_ai/authority_engine.py`
  so risk vocabulary is unified.
- **Chain composition** — `Pipeline([...])` with stop-on-fail.
- **Shell sandboxing** — current blocklist is coarse, adversarial input
  would get through. v2 should run high-risk shell in a constrained env.
- **Decision log querying** — currently write-only. Needs a tiny reader
  so agents can learn from past decisions.
- **Wiring into existing services** — `services/discord_bot.py`,
  `orchestrator/`, and scheduled scripts should migrate to `run_action`
  one at a time. v1 provides the reference CLI; v2 should migrate the
  hot paths.

## Next steps

1. Migrate one real workflow (suggest: `scripts/scheduled/morning_prep.sh`
   or `orchestrator/`) to route through `run_action`. Measure whether
   the logs actually help debugging.
2. Add a `control_plane_resume` helper for the defer case — so
   `status="validated"` actions can be approved and executed later
   without re-proposing.
3. Hook `authority_engine.py` risk classes into the Action schema so
   LOW/MEDIUM/HIGH/CRITICAL there maps 1:1 with Control Plane risk.
4. Build a tiny decisions reader (`scripts/decisions.py list|show`) so
   the decision log becomes a queryable artifact, not just a write sink.
5. Document the Control Plane in the main EOS wiki and link from
   `CLAUDE.md` under "Protocols" so new agents discover it.

## Constraints honored

- No new tool skills built.
- No expansion of capability coverage.
- No abstractions beyond what the current features use.
- One clear chokepoint, one clear data shape, one clear log format.
