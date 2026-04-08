# Control Plane — EOS Intelligence Layer, Phase 1

**Status:** v1 (production-ready, minimal)
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
| `control_plane.py` | `run_action()` — the public lifecycle runner |

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

## Related

- Tool Mastery Engine: `/opt/OS/10_Wiki/tool_mastery_engine_system.md`
- Authority engine: `eos_ai/authority_engine.py` (existing risk classes)
- Reference CLI: `scripts/control_plane_run.py`
