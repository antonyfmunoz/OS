# Control Plane — EOS Intelligence Layer

**Status:** v3 (Phase 3 complete — policy bridge, Discord approval worker, stale-deferred lifecycle, second real workflow migrated)
**Location:** `/opt/OS/core/action_system/`
**Entry point:** `core.action_system.control_plane.run_action`

## Purpose

EOS already has capability coverage across frontend, backend, infra, and
creator systems. What it lacked was **control**: a single chokepoint every
meaningful agent action flows through, so we get validation, approval,
and an audit trail for free.

The Control Plane provides that chokepoint.

## Lifecycle

Every action follows the same five stages:

```
propose → validate → approve → execute → log
```

Each transition is persisted to the execution log. The log is
append-only JSONL, one file per UTC day, so forensics is `grep` + `jq`.

```
┌────────┐    ┌──────────┐    ┌──────────┐    ┌─────────┐    ┌─────┐
│propose │───▶│ validate │───▶│ approve  │───▶│ execute │───▶│ log │
└────────┘    └──────────┘    └──────────┘    └─────────┘    └─────┘
                   │               │               │
                   ▼               ▼               ▼
               rejected         awaiting        failed
                                 approval
```

## Components

| File | Responsibility |
|---|---|
| `actions.py` | `Action` dataclass, `propose_action()`, allowed types |
| `validator.py` | `validate_action()`, `approve_action()`, safety rules |
| `executor.py` | Dispatch by `action.type`: shell, script, file, API |
| `logging.py` | `log_execution()`, `log_decision()` — append-only JSONL |
| `tme.py` | Optional Tool Mastery Engine lookup (`query_relevant_skills`) |
| `deferred.py` | Durable persistence for deferred actions (one JSON file per action) |
| `notifier.py` | Notifier protocol + `FileNotifier`, `DiscordNotifier`, `MultiNotifier` |
| `control_plane.py` | `run_action()`, `resume_action()` — the public lifecycle runners |

## Action schema

```python
Action(
    id: str                    # uuid4, auto-generated
    type: str                  # run_script | shell_command | write_file | call_api
    description: str
    inputs: dict               # type-specific payload
    expected_output: str
    risk_level: str            # low | medium | high
    source_agent: str
    timestamp: str             # ISO 8601 UTC
    status: str                # proposed|validated|approved|executed|failed|rejected
    validation: dict           # {ok: bool, errors: [...]}
    approval: dict             # {approved: bool, reason: str}
    result: dict               # executor output
)
```

## Approval policy (v1)

| Risk | Policy |
|---|---|
| `low` | Auto-approved |
| `medium` | Requires `explicit_approval=True` |
| `high` | Requires `explicit_approval=True` |

Non-approved medium/high actions stay in the `validated` state so an
orchestrator (or human) can revisit them later without re-proposing.

## Safety rules

- **Forbidden path prefixes** (`write_file`): `/etc`, `/boot`, `/sys`, `/proc`, `/dev`, `/root/.ssh`
- **Dangerous shell tokens** (`shell_command`): `rm -rf /`, `mkfs`, fork bomb, `dd if=`, `shutdown`, `reboot`, `> /dev/sda`
- **`run_script`** must target a `.py` or `.sh` file
- **`call_api`** must have a URL

These are intentionally coarse. v2 will let agents declare policies per
source_agent and per venture.

## Usage

### From Python

```python
import sys; sys.path.insert(0, "/opt/OS")
from core.action_system.control_plane import run_action, log_decision

action = run_action(
    type="shell_command",
    description="refresh morning brief cache",
    inputs={"command": "python3 /opt/OS/scripts/call_prep.py --refresh"},
    risk_level="low",
    source_agent="orchestrator",
)
print(action.status, action.result)
```

### From the CLI

```bash
python3 /opt/OS/scripts/control_plane_run.py shell "echo hello"
python3 /opt/OS/scripts/control_plane_run.py script scripts/query_skills.py count
python3 /opt/OS/scripts/control_plane_run.py shell "ls /opt/OS" \
    --agent developer --risk medium --approve
```

## Logs

```
/opt/OS/logs/execution/YYYY-MM-DD-execution.jsonl
/opt/OS/logs/decisions/YYYY-MM-DD-decisions.jsonl
```

Every lifecycle transition writes one execution line. That means a single
action produces ~4 entries (proposed, validated, approved, executed).
This is deliberate — it gives you a replayable history, not just a snapshot.

Decision logs are separate because "why did we do X" has a different
query pattern than "what happened" — you want to read decisions narratively.

### Quick forensics

```bash
# What ran today?
jq -r '.action | [.timestamp, .status, .type, .description] | @tsv' \
    /opt/OS/logs/execution/$(date -u +%F)-execution.jsonl

# What got rejected?
jq 'select(.action.status=="rejected")' \
    /opt/OS/logs/execution/$(date -u +%F)-execution.jsonl

# Why did we do that?
jq . /opt/OS/logs/decisions/$(date -u +%F)-decisions.jsonl
```

## TME integration

Pass `consult_tme=True` to `run_action()` (or `--consult-tme` on the CLI)
to shell out to `scripts/query_skills.py` before executing. The result is
attached to `action.result["tme_consult"]`. It's advisory — the Control
Plane does not block on TME availability.

## How agents should use this

**Rule of thumb:** if an action changes state on disk, on the network, or
in a database — route it through `run_action()`. Pure reads (status
checks, log queries, `git status`) don't need the Control Plane.

New agents added to EOS should:

1. Import `run_action` instead of calling `subprocess.run` directly.
2. Pass a meaningful `source_agent` and `description` so logs are useful.
3. Declare risk honestly. Low means "if this goes wrong, nothing breaks."
4. Log the *reasoning* separately via `log_decision()` when the action
   is non-obvious or one of several options.

## Limitations (v1)

- **Approval is a boolean flag, not a workflow.** No queue, no UI, no
  notifications. Medium/high actions just sit in `validated` until
  someone calls `run_action(..., explicit_approval=True)`.
- **No dry-run mode.** `validate_action()` is the closest thing — it
  checks fields and safety but doesn't simulate execution.
- **No idempotency keys.** Re-running the same action produces a new
  `id` and a new log entry.
- **Shell safety is a blocklist**, not a sandbox. Don't rely on it for
  adversarial input.
- **No cross-action orchestration.** Each `run_action` is independent;
  there's no DAG or dependency tracking yet.
- **Decision log is write-only.** No query helper, no indexing.

## What v2 should add

- Per-agent and per-venture policy (e.g., "outreach agent can't touch
  production DB even at low risk").
- Approval queue with Discord/Telegram notifications for medium/high.
- Dry-run mode that stops after validation and emits a plan.
- Idempotency keys and replay.
- Chain composition: `Pipeline([action1, action2, action3])` with
  stop-on-fail semantics.
- Decision log querying and tagging (so "why" becomes learnable).
- Integration with the authority_engine risk classes so Control Plane
  risk and architectural risk share one vocabulary.

---

## Phase 2: Deferred actions, resume, notifications, real-workflow migration

Phase 2 proves the Control Plane in real usage. The Phase 1 defer state
became operationally usable by adding persistence, a resume path, and a
notifier foundation — and the `morning_prep` workflow was migrated as
the first real consumer.

### Deferred-action model

When an action is medium/high risk and has no explicit approval,
`run_action`:

1. Leaves the action in `status="validated"`.
2. Persists the full Action record to
   `/opt/OS/logs/deferred/<action_id>.json`.
3. Calls `default_notifier().notify(action)`, which appends to
   `/opt/OS/logs/deferred/notifications.jsonl` (always) and fires a
   Discord webhook (if `DISCORD_APPROVAL_WEBHOOK_URL` is set).
4. Logs one `deferred` line to the execution log so forensics from
   logs alone can find the `deferred_path` and `notification` metadata.

One JSON file per action (not a shared JSONL) — approval is
`os.remove`, no rewrites, no shared-file races.

### Resume

```python
from core.action_system.control_plane import resume_action

action = resume_action("25c42826-aece-470f-a58e-375987461a76")
# loads the deferred file → grants explicit approval → executes →
# logs every transition → deletes the deferred file on terminal state
```

`resume_action` also writes a decision log entry so the "why did we
approve this" question has a permanent answer.

### Operator CLI

```bash
# What's waiting for approval?
python3 /opt/OS/scripts/deferred.py list

# Inspect one
python3 /opt/OS/scripts/deferred.py show <action_id>

# Approve + execute
python3 /opt/OS/scripts/deferred.py approve <action_id>

# Abandon without executing
python3 /opt/OS/scripts/deferred.py drop <action_id>
```

### Notifier foundation

The notifier layer is a `Protocol`, not a class hierarchy. Any object
with `notify(action) -> dict` works.

| Class | Use |
|---|---|
| `FileNotifier` | Always-on durable queue at `logs/deferred/notifications.jsonl`. Future Discord/Telegram workers can tail or drain it. |
| `DiscordNotifier` | Best-effort webhook POST. Reads `DISCORD_APPROVAL_WEBHOOK_URL`. Silently skips if missing. Never raises. |
| `MultiNotifier` | Fan-out to a list of notifiers. |
| `default_notifier()` | Returns `FileNotifier` always, plus `DiscordNotifier` if the webhook env var is set. |

The notifier is advisory — if every channel fails, the action is still
persisted to the deferred queue. Durability does not depend on
notification success.

Discord/Telegram integration in Phase 3 should:

1. Run as a worker that tails `notifications.jsonl`, OR
2. Drop a `DiscordNotifier` with a real webhook URL into the
   `MultiNotifier` stack via `default_notifier()`.

Either works. The file queue is the safer path because it decouples
notification delivery from the Control Plane's execution timing.

### Migrated workflow: `morning_prep`

`scripts/scheduled/morning_prep.sh` is the first real workflow to
route through the Control Plane. A thin Python wrapper
(`scripts/scheduled/morning_prep_cp.py`) runs the `.sh` as a
`run_script` action with `risk_level="medium"` and
`source_agent="cron"`.

Why medium risk: `morning_prep.sh` mutates ritual state, consumes up
to $0.30 of CC budget, and gates on provider health. Not destructive,
but not free.

Cron migration:

```bash
# OLD:
# 30 5 * * * bash /opt/OS/scripts/scheduled/morning_prep.sh

# NEW:
# 30 5 * * * python3 /opt/OS/scripts/scheduled/morning_prep_cp.py --approve \
#   >> /opt/OS/logs/morning_prep_cp.log 2>&1
```

`--approve` grants explicit approval so cron runs don't defer.
Operators running the wrapper interactively can omit it to push the
run into the deferred queue and approve manually.

### Operator flow (end-to-end)

```bash
# Cron (or anyone with pre-authorization):
python3 /opt/OS/scripts/scheduled/morning_prep_cp.py --approve

# Manual / investigating:
python3 /opt/OS/scripts/scheduled/morning_prep_cp.py
# → deferred, notification dropped in logs/deferred/notifications.jsonl

python3 /opt/OS/scripts/deferred.py list
# RISK   TYPE         AGENT  ID                                    DESCRIPTION
# medium run_script   cron   25c42826-...                          scheduled morning prep ...

python3 /opt/OS/scripts/deferred.py approve 25c42826-...
# → executed, file removed, full trail in logs/execution/
```

### Logging review — findings from real use

- **Lifecycle logs are sufficient** for the current four types
  (shell, script, write, api). Every transition is one JSONL line.
- **Gap found and fixed:** the original implementation attached
  `deferred_path` and `notification` to the returned Action *after*
  the last log line, so log-only replay couldn't find the deferred
  file. Added a fifth log line (`# deferred`) once persistence and
  notification complete. `resume_action` logs its own decision and
  execution transitions, so the full deferred-resume-executed trail
  is recoverable from logs alone.
- **No additional fields needed** on the Action schema for Phase 2.
- **Defer/resume is operationally clear** — the CLI verbs
  (`list/show/approve/drop`) map 1:1 to operator intent.

## Related

- Tool Mastery Engine: `/opt/OS/10_Wiki/tool_mastery_engine_system.md`
- Authority engine: `eos_ai/authority_engine.py` (existing risk classes)
- Reference CLI: `scripts/control_plane_run.py`
- Deferred CLI: `scripts/deferred.py`
- First migration: `scripts/scheduled/morning_prep_cp.py`
- Phase 1 audit: `docs/audits/2026-04-06-control-plane-phase-1.md`
- Phase 2 audit: `docs/audits/2026-04-08-control-plane-phase-2.md`
- Phase 3 audit: `docs/audits/2026-04-08-control-plane-phase-3.md`

---

## Phase 3: Policy bridge, Discord worker, stale lifecycle, second migration

Phase 3 upgrades the Control Plane from workable governance to
operational governance by (a) unifying policy with `authority_engine`,
(b) closing the approval loop through a worker, (c) preventing
deferred-action buildup, and (d) proving the migration pattern on a
second real workflow.

### Authority integration model

`core/action_system/policy.py` is the minimum correct bridge between
the Control Plane and `eos_ai/authority_engine.py`. Two governance
systems coexist with **different domains** and must not be collapsed:

| Layer | Domain | Vocabulary | Source of truth |
|---|---|---|---|
| `authority_engine` | Business actions (`send_dm`, `publish_content`, `execute_payment`) | Uppercase (`LOW/MEDIUM/HIGH/CRITICAL`) | Neon (`approvals` table) |
| Control Plane | Runtime actions (`run_script`, `shell_command`, `write_file`, `call_api`) | Lowercase (`low/medium/high/critical`) | Disk (`logs/deferred/`) |

The policy bridge:

- Exposes one canonical Control Plane vocabulary.
- Provides `normalize_risk()`, `map_to_authority_class()`,
  `required_autonomy_level()`, `requires_explicit_approval()`,
  `blocks_auto_execute()`.
- Lazily imports `authority_engine.RISK_CLASSES` via
  `authority_classify()` — wrapped in a try/except so the runtime
  layer never crashes when the business layer is unavailable.
- Composes the two classifications with `resolve_effective_risk()`
  where **the stricter always wins** — a low-declared runtime action
  that maps to a `CRITICAL` business classification is upgraded to
  `critical` at propose time.

**Integration contract.**

    Control Plane owns runtime action risk.
    AuthorityEngine owns business action risk.
    When a runtime action carries business semantics, pass
    `business_action_type=<name>` to `run_action()` and the bridge
    will upgrade the risk to the stricter of the two.

**`critical` is a hard block.** Critical-risk actions are never
auto-executed, even with `explicit_approval=True`. They stay in
`validated` for operator visibility but `approve_action` refuses
them. Downgrading a critical action requires a code change (a
policy decision, not a call-site decision).

**No circular dependency.** `policy.py` has no module-level import of
`eos_ai.*`. The lookup is function-scoped so the Control Plane can
run in minimal environments (tests, workers) even if the business
layer is broken.

```python
from core.action_system.control_plane import run_action

# Runtime-only action — risk stays low
run_action(type="shell_command", description="cache refresh",
           inputs={"command": "..."}, risk_level="low")

# Runtime action with business semantics — bridge upgrades to critical
run_action(type="run_script", description="send outreach batch",
           inputs={"path": "..."}, risk_level="low",
           business_action_type="publish_content")
# → action.risk_level == "critical", status == "validated" (blocked)
```

### Discord approval worker

`scripts/workers/discord_approval_worker.py` is the integration seam
between `notifications.jsonl` and external approval channels.

Design constraints:

- **Decoupled.** Never imports `core.action_system`. Reads the JSONL
  + checks the deferred directory. The Control Plane's execution path
  is never blocked on notification delivery.
- **Offset-based tailing.** Stores the last processed byte offset in
  `logs/deferred/.worker_offset`. Restarts don't re-notify old events.
- **Stale-skip via filesystem.** Before posting, the worker verifies
  the per-action JSON still exists. Actions approved or dropped from
  CLI between notification and drain are silently skipped.
- **Best-effort POST.** Non-2xx and missing-webhook cases are logged
  to stderr. The deferred queue remains the source of truth.
- **Replay-safe when inert.** If `DISCORD_APPROVAL_WEBHOOK_URL` is
  unset, the offset is *not* advanced — once the webhook is
  configured, a single `--once` drain replays every pending line.

Configuration:

    DISCORD_APPROVAL_WEBHOOK_URL    # required for real delivery
    DISCORD_APPROVAL_POLL_SECONDS   # loop mode interval (default 15s)

Operator flow:

```bash
# Drain once (cron-friendly):
python3 /opt/OS/scripts/workers/discord_approval_worker.py --once

# Tail forever (systemd / tmux):
python3 /opt/OS/scripts/workers/discord_approval_worker.py --loop

# Dry-run without a webhook (inspect what would be sent):
python3 /opt/OS/scripts/workers/discord_approval_worker.py --once --dry-run

# Replay the entire queue (for debugging):
python3 /opt/OS/scripts/workers/discord_approval_worker.py --reset --once
```

**Current runtime state.** The worker is operationally ready. Real
Discord delivery requires only one env var (`DISCORD_APPROVAL_WEBHOOK_URL`);
the worker is otherwise fully functional and has been validated with
`--dry-run`.

### Stale-deferred lifecycle

Deferred actions now carry an optional sidecar status. Absence of a
sidecar = `pending`, so every pre-Phase-3 deferred action inherits the
correct default without migration.

**Storage.** `/opt/OS/logs/deferred/<action_id>.status.json` holds the
sidecar. The Phase 2 queue layout (`<action_id>.json` per action) is
unchanged. `list_deferred()` skips `*.status.json` to avoid collision.

**States:**

| Status | Meaning |
|---|---|
| `pending` | Default; no sidecar, operator has not yet responded |
| `acknowledged` | Operator has seen it, intentionally still waiting |
| `snoozed` | Intentionally deferred again; `snoozed_until` is ISO timestamp |
| `stale` | Older than the threshold; eligible for pruning |

**Threshold** defaults to **72 hours** and is configurable on every
stale-check / prune invocation via `--older-than N`. The threshold
lives with the operator interface, not the storage layer.

**Operator commands** (all on `scripts/deferred.py`):

```bash
# Read or set sidecar status
python3 /opt/OS/scripts/deferred.py status <id>
python3 /opt/OS/scripts/deferred.py status <id> --set acknowledged --note "triaged"
python3 /opt/OS/scripts/deferred.py status <id> --set snoozed --until 2026-04-10T09:00:00Z

# Scan queue and mark pending-and-too-old as stale
python3 /opt/OS/scripts/deferred.py stale-check --older-than 72

# Prune stale actions
python3 /opt/OS/scripts/deferred.py prune                     # only sidecar-marked stale
python3 /opt/OS/scripts/deferred.py prune --auto-mark --older-than 72
python3 /opt/OS/scripts/deferred.py prune --auto-mark --dry-run

# List now includes a STATUS column
python3 /opt/OS/scripts/deferred.py list
```

`approve` and `drop` automatically clear the sidecar so a resumed or
abandoned action never leaves stray status metadata on disk.

**Rule.** `stale-check` only promotes `pending` actions to `stale` —
it never overwrites operator annotations like `acknowledged` or
`snoozed`. Once an operator touches an action, the stale detector
backs off.

### Second workflow migrated: `nightly_consolidation`

`scripts/scheduled/nightly_consolidation_cp.py` wraps
`scripts/scheduled/nightly_consolidation.sh` as a `run_script` action
with `risk_level="medium"` and `source_agent="cron"`. The wrapper
shape is deliberately identical to `morning_prep_cp.py` — the
migration pattern is now boringly repeatable.

Why this workflow:

- **Bounded**: one cron line, ~75 lines of bash
- **Stateful**: mutates wiki + substrate `close_day` rituals
- **Gated**: already has a provider_health preflight
- **Reversible**: underlying `.sh` untouched, revert the cron line to undo

Cron migration:

```bash
# OLD:
# 0 2 * * * bash /opt/OS/scripts/scheduled/nightly_consolidation.sh

# NEW:
# 0 2 * * * python3 /opt/OS/scripts/scheduled/nightly_consolidation_cp.py --approve \
#          >> /opt/OS/logs/nightly_consolidation_cp.log 2>&1
```

The `--dry-run` flag on the wrapper passes through to the underlying
`.sh`, so operators can defer a dry run, inspect it, and approve only
if the preview looks right.

### Logging review — Phase 3 findings

Re-evaluating the logs now that two workflows, notifications, and
stale states coexist:

- **Execution logs are still sufficient.** Every lifecycle transition
  is still one JSONL line. Risk upgrades from the policy bridge
  appear in `action.validation` as `declared_risk` /
  `effective_risk` / `business_action_type` — no schema change on
  Action itself.
- **Decision logs are still sufficient.** Each migrated wrapper
  writes one decision entry per invocation, which is enough to
  reconstruct "why did cron run this tonight" narratively.
- **Operator commands are clearer.** The `STATUS` column in
  `deferred list` means an operator can triage the full queue in one
  view instead of having to cross-reference sidecar files.
- **No new fields needed** on the Action schema — the policy bridge
  information lives on `action.validation`, which already exists.
- **Notification queue is unchanged.** The worker reads it
  without requiring any additional fields.

---
