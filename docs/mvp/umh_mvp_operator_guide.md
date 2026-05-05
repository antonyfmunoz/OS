# UMH MVP Operator Guide

Last updated: 2026-04-27

---

## 1. What UMH Can Do Now

UMH is an AI execution system that converts natural language intent into validated,
multi-step execution plans, runs them through a task engine, and gates risky operations
behind an approval workflow. Current capabilities:

- **Natural language planning** -- type what you want in plain text, UMH reconstructs
  a structured objective and maps it to a deterministic template or LLM-generated plan.
- **10 built-in plan templates** -- system diagnostics, file inspection, directory listing,
  text summarization, screenshot review, health checks, workspace snapshots, click demos,
  and full system diagnostics.
- **Multi-step task execution** -- plans convert to tasks with up to 10 sequential steps.
  Step outputs feed into subsequent steps via template variables.
- **Approval-gated computer actions** -- mouse clicks, keyboard input, scrolling, and
  dragging require explicit human approval before execution. Approvals expire after 5
  minutes and are single-use.
- **Quality scoring** -- every plan is scored across 6 dimensions before execution.
  Plans that fail quality are blocked from running.
- **Plan explanation** -- every plan includes a structured explanation with assumptions,
  risks, approval requirements, and safety assessment.
- **Security guard** -- shell commands are allowlisted, file operations are sandboxed,
  sensitive path patterns are denied, dangerous shell metacharacters are blocked.
- **Identity-based auth** -- every API action is attributable to an authenticated identity
  with scoped permissions (execute, approvals:read, approvals:write, metrics:read, admin).
- **Event stream** -- real-time SSE stream of all system events (execution, approval,
  task, plan lifecycle).
- **Metrics** -- task and plan metrics with status breakdowns, quality verdicts, and
  recent activity.
- **LLM-assisted planning** -- when no template matches, UMH can ask an LLM to generate
  a plan. LLM output is treated as untrusted and must pass the same validator.
- **CLI** -- command-line interface for plan creation, execution, task inspection, and
  approval listing.
- **HTTP API** -- full REST API for all operations.

---

## 2. What It Cannot Do Yet

- **No persistent storage across restarts** -- plans and tasks are stored in-memory.
  Restarting the API server loses all plan/task state. Approvals and identities persist
  in SQLite.
- **No browser automation** -- `browser_navigate`, `browser_click`, `browser_type` are
  explicitly unsupported and will be denied.
- **No OS-level operations** -- `os_reboot`, `os_shutdown`, `os_install` are denied.
- **No arbitrary shell commands** -- only 12 specific commands are in the allowlist.
  You cannot run `curl`, `pip`, `git`, `apt`, or anything else.
- **No file write/delete through plans** -- while `file_write` and `file_delete` are
  known operations, they are sandboxed to `/opt/OS/data`, `/opt/OS/logs`,
  `/opt/OS/10_Wiki`, and `/tmp`. No templates currently generate write operations.
- **No task resume from CLI** -- paused tasks can only be resumed via the API, not the CLI.
- **No parallel step execution** -- all task steps run sequentially.
- **No plan editing** -- once a plan is created, it cannot be modified. Create a new one.
- **No authentication from CLI** -- the CLI runs locally and bypasses API auth (direct
  Python calls). This is by design for operator use.
- **No UI** -- all interaction is via CLI or curl.
- **Max 10 steps per plan/task** -- hard limit enforced by both validator and task system.

---

## 3. API Usage

### Starting the API Server

```bash
# Default (port 8000)
python3 -m umh.control.api

# Custom port
UMH_API_PORT=9000 python3 -m umh.control.api

# Via uvicorn directly
uvicorn umh.control.api:app --host 127.0.0.1 --port 8000
```

### Authentication

Every request (except `/health`) requires the `X-API-Key` header.

Two auth modes:
1. **Identity store** -- structured identities with scoped permissions (SQLite-backed).
2. **Legacy fallback** -- set `UMH_API_KEY` env var and use that value as the key.
   Legacy keys get `admin` scope.

For all examples below, set your key:

```bash
export UMH_KEY="your-api-key-here"
```

### Endpoints

#### GET /health

No auth required. Returns server status.

```bash
curl http://127.0.0.1:8000/health
```

Response:
```json
{"status": "ok"}
```

---

#### POST /plans

Create a plan from raw input or structured objective. Scope: `execute`.

**Raw input mode** (recommended for most use cases):

```bash
curl -s -X POST http://127.0.0.1:8000/plans \
  -H "X-API-Key: $UMH_KEY" \
  -H "Content-Type: application/json" \
  -d '{"raw_input": "check system health"}' | python3 -m json.tool
```

Response (200 = validated, 422 = rejected):
```json
{
  "plan_id": "eplan_a1b2c3d4e5f6",
  "objective": {
    "objective_id": "obj_abc123def456",
    "title": "inspect_system_status",
    "description": "check system health",
    "constraints": [],
    "context": {},
    "requested_by": "id_operator01",
    "max_steps": 10,
    "allowed_capabilities": [],
    "dry_run": false,
    "raw_input": "check system health",
    "intent_category": "system_health",
    "assumptions_obj": ["Template 'inspect_system_status' matches intent"]
  },
  "steps": [
    {
      "step_id": "pstep_aabb1122",
      "name": "Check uptime",
      "operation": "shell_command",
      "inputs": {"command": "uptime"},
      "execution_class": "side_effect",
      "constraints": {},
      "depends_on": [],
      "rationale": "Get system uptime and load averages"
    },
    {
      "step_id": "pstep_ccdd3344",
      "name": "Check disk usage",
      "operation": "shell_command",
      "inputs": {"command": "df -h"},
      "execution_class": "side_effect",
      "constraints": {},
      "depends_on": [],
      "rationale": "Report disk space usage"
    },
    {
      "step_id": "pstep_eeff5566",
      "name": "Check memory",
      "operation": "shell_command",
      "inputs": {"command": "free -h"},
      "execution_class": "side_effect",
      "constraints": {},
      "depends_on": [],
      "rationale": "Report memory usage"
    },
    {
      "step_id": "pstep_gghh7788",
      "name": "Check docker containers",
      "operation": "shell_command",
      "inputs": {"command": "docker ps"},
      "execution_class": "side_effect",
      "constraints": {},
      "depends_on": [],
      "rationale": "List running containers"
    }
  ],
  "source": "template",
  "confidence": 1.0,
  "assumptions": ["System has docker installed", "Shell commands are available"],
  "status": "validated",
  "created_at": "2026-04-27T12:00:00+00:00",
  "task_id": "",
  "validation_errors": [],
  "quality": {
    "score": 0.883,
    "verdict": "pass",
    "reasons": [],
    "dimensions": {
      "completeness": 1.0,
      "safety": 1.0,
      "specificity": 0.7,
      "executability": 0.8,
      "minimality": 0.8,
      "constraint_alignment": 1.0
    }
  },
  "explanation": {
    "objective_summary": "inspect_system_status: check system health",
    "steps_summary": [...],
    "assumptions": [...],
    "risks": [...],
    "approval_requirements": [],
    "plan_selection_reason": "Deterministic template selected -- confidence 1.0, 4 steps",
    "safety_assessment": "SAFE -- shell commands are allowlisted"
  }
}
```

**Structured objective mode**:

```bash
curl -s -X POST http://127.0.0.1:8000/plans \
  -H "X-API-Key: $UMH_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "inspect_file",
    "description": "Read the main config file",
    "context": {"path": "/opt/OS/data/config.json"},
    "max_steps": 5
  }' | python3 -m json.tool
```

**Dry run mode** (plan is created and validated but not executed):

```bash
curl -s -X POST http://127.0.0.1:8000/plans \
  -H "X-API-Key: $UMH_KEY" \
  -H "Content-Type: application/json" \
  -d '{"raw_input": "check system health dry run"}' | python3 -m json.tool
```

---

#### GET /plans

List all plans. Scope: `execute`.

```bash
curl -s http://127.0.0.1:8000/plans \
  -H "X-API-Key: $UMH_KEY" | python3 -m json.tool
```

---

#### GET /plans/{plan_id}

Get a specific plan. Scope: `execute`.

```bash
curl -s http://127.0.0.1:8000/plans/eplan_a1b2c3d4e5f6 \
  -H "X-API-Key: $UMH_KEY" | python3 -m json.tool
```

---

#### POST /plans/{plan_id}/execute

Execute a validated plan. Converts it to a task and runs all steps. Scope: `execute`.

Plans with quality verdict `fail` are blocked. Plans with verdict `warn` execute but
include warnings in the response.

```bash
curl -s -X POST http://127.0.0.1:8000/plans/eplan_a1b2c3d4e5f6/execute \
  -H "X-API-Key: $UMH_KEY" | python3 -m json.tool
```

Response:
```json
{
  "id": "task_abc123def456",
  "status": "completed",
  "current_step_index": 3,
  "context": {},
  "steps": [
    {
      "id": "step_aabb1122",
      "operation": "shell_command",
      "inputs_template": {"command": "uptime"},
      "output_key": "pstep_aabb1122",
      "execution_class": "side_effect",
      "status": "completed",
      "result": {
        "execution_id": "exec_0123456789abcdef",
        "operation": "shell_command",
        "status": "succeeded",
        "outputs": {"stdout": " 12:00:00 up 45 days, ..."},
        "latency_ms": 52
      }
    }
  ],
  "created_at": "2026-04-27T12:00:01+00:00",
  "updated_at": "2026-04-27T12:00:03+00:00",
  "issued_by": "id_operator01",
  "error": ""
}
```

---

#### POST /plans/{plan_id}/validate

Re-validate an existing plan. Scope: `execute`.

```bash
curl -s -X POST http://127.0.0.1:8000/plans/eplan_a1b2c3d4e5f6/validate \
  -H "X-API-Key: $UMH_KEY" | python3 -m json.tool
```

Response:
```json
{
  "valid": true,
  "errors": [],
  "warnings": []
}
```

---

#### POST /execute

Direct execution of a single operation (bypasses planning layer). Scope: `execute`.

```bash
curl -s -X POST http://127.0.0.1:8000/execute \
  -H "X-API-Key: $UMH_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "operation": "summarize",
    "inputs": {
      "prompt": "Summarize: UMH is an AI execution system.",
      "system_prompt": "Be concise.",
      "max_tokens": 128
    },
    "execution_class": "llm_call"
  }' | python3 -m json.tool
```

---

#### POST /tasks

Create and execute a multi-step task directly (bypasses planning layer). Scope: `execute`.

```bash
curl -s -X POST http://127.0.0.1:8000/tasks \
  -H "X-API-Key: $UMH_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "steps": [
      {
        "operation": "shell_command",
        "inputs_template": {"command": "uptime"},
        "output_key": "uptime_result",
        "execution_class": "side_effect"
      },
      {
        "operation": "shell_command",
        "inputs_template": {"command": "free -h"},
        "output_key": "memory_result",
        "execution_class": "side_effect"
      }
    ]
  }' | python3 -m json.tool
```

---

#### GET /tasks

List all tasks. Scope: `execute`.

```bash
curl -s http://127.0.0.1:8000/tasks \
  -H "X-API-Key: $UMH_KEY" | python3 -m json.tool
```

---

#### GET /tasks/{task_id}

Get a specific task. Scope: `execute`.

```bash
curl -s http://127.0.0.1:8000/tasks/task_abc123def456 \
  -H "X-API-Key: $UMH_KEY" | python3 -m json.tool
```

---

#### GET /approvals

List approvals. Scope: `approvals:read`.

```bash
# All approvals
curl -s http://127.0.0.1:8000/approvals \
  -H "X-API-Key: $UMH_KEY" | python3 -m json.tool

# Pending only
curl -s "http://127.0.0.1:8000/approvals?status=pending" \
  -H "X-API-Key: $UMH_KEY" | python3 -m json.tool
```

---

#### GET /approvals/{approval_id}

Get a specific approval. Scope: `approvals:read`.

```bash
curl -s http://127.0.0.1:8000/approvals/approval_abc123def456 \
  -H "X-API-Key: $UMH_KEY" | python3 -m json.tool
```

Response:
```json
{
  "id": "approval_abc123def456",
  "execution_id": "exec_0123456789abcdef",
  "operation": "computer_click",
  "capability_type": "computer_use",
  "risk_level": "high",
  "inputs_summary": "x=500, y=300",
  "created_at": "2026-04-27T12:00:00+00:00",
  "expires_at": "2026-04-27T12:05:00+00:00",
  "status": "pending",
  "requested_by": "",
  "approved_by": ""
}
```

---

#### POST /approvals/{approval_id}/approve

Approve a pending request. Scope: `approvals:write`.

```bash
curl -s -X POST http://127.0.0.1:8000/approvals/approval_abc123def456/approve \
  -H "X-API-Key: $UMH_KEY" | python3 -m json.tool
```

Response:
```json
{
  "approved": "approval_abc123def456",
  "status": "approved",
  "approved_by": "id_operator01"
}
```

---

#### POST /approvals/{approval_id}/deny

Deny a pending request. Scope: `approvals:write`.

```bash
curl -s -X POST http://127.0.0.1:8000/approvals/approval_abc123def456/deny \
  -H "X-API-Key: $UMH_KEY" | python3 -m json.tool
```

Response:
```json
{
  "denied": "approval_abc123def456",
  "status": "denied",
  "denied_by": "id_operator01"
}
```

---

#### GET /metrics

System metrics. Scope: `metrics:read`.

```bash
curl -s http://127.0.0.1:8000/metrics \
  -H "X-API-Key: $UMH_KEY" | python3 -m json.tool
```

Response includes execution counters, task status breakdowns, plan quality averages,
and recent activity.

---

#### POST /identities

Create a new identity. Scope: `admin`.

```bash
curl -s -X POST http://127.0.0.1:8000/identities \
  -H "X-API-Key: $UMH_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "operator",
    "scopes": ["execute", "approvals:read", "approvals:write", "metrics:read"]
  }' | python3 -m json.tool
```

Response (save the `api_key` -- it is only shown once):
```json
{
  "id": "id_abc123def456",
  "name": "operator",
  "scopes": ["execute", "approvals:read", "approvals:write", "metrics:read"],
  "created_at": "2026-04-27T12:00:00+00:00",
  "status": "active",
  "api_key": "umh_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4"
}
```

---

#### GET /identities

List all identities. Scope: `admin`.

```bash
curl -s http://127.0.0.1:8000/identities \
  -H "X-API-Key: $UMH_KEY" | python3 -m json.tool
```

---

#### POST /identities/{identity_id}/disable

Disable an identity. Scope: `admin`.

```bash
curl -s -X POST http://127.0.0.1:8000/identities/id_abc123def456/disable \
  -H "X-API-Key: $UMH_KEY" | python3 -m json.tool
```

---

#### GET /orchestrator/rules

List orchestrator rules. Scope: `admin`.

```bash
curl -s http://127.0.0.1:8000/orchestrator/rules \
  -H "X-API-Key: $UMH_KEY" | python3 -m json.tool
```

---

#### GET /events

List recent events. Scope: `metrics:read`.

```bash
# Last 100 events (default)
curl -s http://127.0.0.1:8000/events \
  -H "X-API-Key: $UMH_KEY" | python3 -m json.tool

# Last 10 events
curl -s "http://127.0.0.1:8000/events?limit=10" \
  -H "X-API-Key: $UMH_KEY" | python3 -m json.tool
```

---

#### GET /events/stream

Server-Sent Events (SSE) stream. Scope: `metrics:read`.

```bash
curl -N http://127.0.0.1:8000/events/stream \
  -H "X-API-Key: $UMH_KEY"
```

Events arrive as `data: {...}\n\n` lines. Keepalives are sent as `: keepalive\n\n`.

---

## 4. CLI Usage

The CLI runs locally and calls the Python modules directly (no API server required).
It does not need authentication.

### plan -- Create a plan from natural language

```bash
# Human-readable output
python3 -m umh.control.cli plan "check system health"

# JSON output
python3 -m umh.control.cli plan "check system health" --json

# File inspection
python3 -m umh.control.cli plan "read file /opt/OS/data/config.json"

# Dry run
python3 -m umh.control.cli plan "check system health dry run"

# Summarize text
python3 -m umh.control.cli plan "summarize the README"
```

Human-readable output:
```
Plan: eplan_a1b2c3d4e5f6
Status: validated
Source: template
Quality: pass (0.883)
Steps:
  1. Check uptime [shell_command] (side_effect)
  2. Check disk usage [shell_command] (side_effect)
  3. Check memory [shell_command] (side_effect)
  4. Check docker containers [shell_command] (side_effect)
Assumptions: System has docker installed; Shell commands are available; Template 'inspect_system_status' matches intent
Risks: Shell command execution: 'uptime'; Shell command execution: 'df -h'; Shell command execution: 'free -h'; Shell command execution: 'docker ps'
```

Exit codes: 0 = success, 1 = plan rejected, 2 = execution error.

### execute -- Create a plan and run it

```bash
# Human-readable
python3 -m umh.control.cli execute "check system health"

# JSON output
python3 -m umh.control.cli execute "check system health" --json

# Summarize
python3 -m umh.control.cli execute "summarize the quick brown fox"

# Directory listing
python3 -m umh.control.cli execute "list files in /opt/OS/data"
```

### task -- Get a task by ID

```bash
python3 -m umh.control.cli task task_abc123def456

python3 -m umh.control.cli task task_abc123def456 --json
```

### tasks -- List all tasks

```bash
python3 -m umh.control.cli tasks

python3 -m umh.control.cli tasks --json
```

### approvals -- List pending approvals

```bash
python3 -m umh.control.cli approvals

python3 -m umh.control.cli approvals --json
```

---

## 5. Approval Lifecycle

Certain operations require explicit human approval before they can execute. This is
the full lifecycle:

### Which operations require approval?

The following computer mutation operations are approval-gated:

| Operation | Description |
|---|---|
| `computer_click` | Click at screen coordinates |
| `computer_type` | Type text |
| `computer_key` | Press a key |
| `computer_scroll` | Scroll |
| `computer_drag` | Drag from one point to another |

Read-only computer operations (`computer_screenshot`, `computer_get_screen_size`,
`computer_get_active_window`) do NOT require approval.

### Lifecycle flow

```
1. Task step attempts approval-gated operation
2. Security guard returns REQUIRES_APPROVAL
3. ApprovalRequest created (status: pending, TTL: 5 minutes)
4. Task pauses at that step (status: paused)
5. Events emitted: approval.created, task.paused
6. Operator reviews and approves or denies via API
7a. If approved:
    - Approval status -> approved
    - Event: approval.approved
    - Operator resumes the task (via resume_task API)
    - Execution re-runs the paused step with approval_id injected
    - After success, approval status -> consumed (single-use)
    - Event: approval.consumed
    - Remaining steps continue
7b. If denied:
    - Approval status -> denied
    - Event: approval.denied
    - Task stays paused (operator must handle)
7c. If TTL expires (5 minutes):
    - Approval status -> expired
    - Cannot be approved after expiration
```

### Approval statuses

| Status | Meaning |
|---|---|
| `pending` | Awaiting operator decision |
| `approved` | Operator approved, ready for execution to consume |
| `denied` | Operator denied |
| `expired` | TTL elapsed without action |
| `consumed` | Approval was used by a successful execution (single-use) |

### Operator workflow for approvals

```bash
# 1. Check for pending approvals
curl -s "http://127.0.0.1:8000/approvals?status=pending" \
  -H "X-API-Key: $UMH_KEY" | python3 -m json.tool

# 2. Review the specific approval
curl -s http://127.0.0.1:8000/approvals/approval_abc123 \
  -H "X-API-Key: $UMH_KEY" | python3 -m json.tool

# 3. Approve it
curl -s -X POST http://127.0.0.1:8000/approvals/approval_abc123/approve \
  -H "X-API-Key: $UMH_KEY" | python3 -m json.tool

# Or deny it
curl -s -X POST http://127.0.0.1:8000/approvals/approval_abc123/deny \
  -H "X-API-Key: $UMH_KEY" | python3 -m json.tool
```

### Important constraints

- Approvals expire after **300 seconds (5 minutes)**.
- Each approval is **single-use** -- once consumed, it cannot be reused.
- Approval must match the exact **operation** and **capability_type** of the execution.
- You cannot approve an already-consumed or expired request.
- You cannot deny an already-consumed request.

---

## 6. Available Templates

Templates are deterministic plan generators. When raw input matches a template via
intent reconstruction, that template generates the plan with confidence 1.0.

| Template Name | Trigger Keywords | Steps | Description |
|---|---|---|---|
| `inspect_system_status` | system health, status, uptime, check system | 4 | uptime, df -h, free -h, docker ps |
| `inspect_file` | inspect/read/view/show file + path | 1 | Read file at given path |
| `list_directory` | list, ls, dir, directory, files in | 1 | List files in directory (default: /opt/OS) |
| `summarize_text` | summarize, summary, tldr, brief | 1 | LLM summarization of provided text |
| `shell_health_check` | load/cpu/memory/disk + check/status | 3 | /proc/loadavg, df -h, free -h |
| `computer_screenshot_review` | screenshot, screen capture | 2 | Take screenshot + LLM description |
| `inspect_file_summary` | (used via structured objective) | 3 | file_stat + file_read + LLM summary |
| `workspace_snapshot` | (used via structured objective) | 2 | screenshot + get screen size |
| `approval_click_demo` | (used via structured objective) | 2 | screenshot + approval-gated click at (x, y) |
| `full_system_diagnostic` | (used via structured objective) | 5 | loadavg, df -h, free -h, ps aux, docker ps |

Templates that require context parameters (path, coordinates) are typically invoked
via the structured objective API rather than raw input.

---

## 7. Safety Boundaries

### Operation Allowlist

These are the only operations the system will execute:

**LLM operations** (no security guard, run freely):
- `classify_intent`
- `extract_entities`
- `summarize`
- `short_response`
- `validation`

**File operations** (sandboxed):
- `file_read`
- `file_write`
- `file_list`
- `file_delete`
- `file_stat`

**Shell operations** (allowlisted):
- `shell_command` (exact command must be in allowlist)

**Computer operations** (read-only are free, mutations need approval):
- `computer_screenshot` -- free
- `computer_get_screen_size` -- free
- `computer_get_active_window` -- free
- `computer_click` -- approval required
- `computer_type` -- approval required
- `computer_key` -- approval required
- `computer_scroll` -- approval required
- `computer_drag` -- approval required

### Explicitly Denied Operations

These are always rejected:
- `browser_navigate`
- `browser_click`
- `browser_type`
- `os_reboot`
- `os_shutdown`
- `os_install`

Any operation not in the known operations list is also denied.

### Shell Command Allowlist

Only these exact commands are permitted:

```
uptime
df -h
free -h
ps aux
whoami
hostname
uname -a
date
ls
ls -la
cat /proc/loadavg
docker ps
```

Any other command string -- including variations like `df -H` or `ls -l` -- is rejected.
Shell metacharacters (`;`, `|`, `&`, `` ` ``, `$`, `(`, `)`, `{`, `}`, `<`, `>`, `\`,
newlines) are blocked by the security guard before the allowlist check.

### File Sandbox

File operations are restricted to these directory roots:
- `/opt/OS/data`
- `/opt/OS/logs`
- `/opt/OS/10_Wiki`
- `/tmp`

Additionally, paths containing these patterns are denied:
- `.env`
- `credentials`
- `secret`
- `.ssh`
- `.gnupg`
- `private_key`

---

## 8. Quality Scoring

Every plan is scored across 6 dimensions before execution. The score determines
whether the plan can run.

### Dimensions

| Dimension | Weight | What it measures |
|---|---|---|
| `completeness` | Equal (1/6) | Does the objective have a title, description, and steps? |
| `safety` | Equal (1/6) | Are all operations known, allowlisted, and properly gated? |
| `specificity` | Equal (1/6) | Is the objective specific enough? Penalized by uncertainty. |
| `executability` | Equal (1/6) | Can steps actually run? Required inputs present? LLM plans get -0.1. |
| `minimality` | Equal (1/6) | Is the plan as small as needed? 1-3 steps = 1.0, 4-5 = 0.8, 6-8 = 0.6, 9-10 = 0.3. |
| `constraint_alignment` | Equal (1/6) | Does the plan respect max_steps and allowed_capabilities? |

### Verdicts

The final score is the average of all 6 dimensions.

| Verdict | Score Range | Effect |
|---|---|---|
| `pass` | >= 0.7 | Plan executes normally |
| `warn` | 0.4 -- 0.69 | Plan executes with warnings included in response |
| `fail` | < 0.4 | Plan execution is **blocked** |

Any individual dimension flagged with `[FAIL]` forces the overall verdict to `fail`
regardless of the numeric score.

### Common fail triggers

- Objective has no title
- Step uses an unknown or unsupported operation
- Shell command not in allowlist
- Approval-gated operation without `side_effect` execution class
- Step has non-dict inputs
- Empty shell command
- Operation not in `allowed_capabilities` (if specified)

---

## 9. Example Raw Inputs

These examples show what you can type and what happens.

### 1. System health check

```bash
python3 -m umh.control.cli plan "check system health"
```
Maps to template `inspect_system_status`. 4 steps: uptime, df -h, free -h, docker ps.

### 2. Read a file

```bash
python3 -m umh.control.cli plan "read file /opt/OS/data/config.json"
```
Maps to template `inspect_file`. 1 step: file_read at the extracted path.

### 3. List a directory

```bash
python3 -m umh.control.cli plan "list files in /opt/OS/data"
```
Maps to template `list_directory`. 1 step: file_list at the extracted path.

### 4. Summarize text

```bash
python3 -m umh.control.cli plan "summarize UMH is an AI execution framework that validates plans"
```
Maps to template `summarize_text`. 1 step: LLM summarization.

### 5. CPU/memory health check

```bash
python3 -m umh.control.cli plan "memory usage check"
```
Maps to template `shell_health_check`. 3 steps: loadavg, df -h, free -h.

### 6. Screenshot review

```bash
python3 -m umh.control.cli plan "take a screenshot"
```
Maps to template `computer_screenshot_review`. 2 steps: screenshot + LLM description.

### 7. System status (alternate phrasing)

```bash
python3 -m umh.control.cli plan "what is my system status"
```
Maps to template `inspect_system_status` via the "status" keyword.

### 8. Dry run mode

```bash
python3 -m umh.control.cli plan "check system health dry run"
```
Creates a validated plan with `dry_run: true`. Execution will skip actual task creation.

### 9. Unknown intent (falls through to LLM)

```bash
python3 -m umh.control.cli plan "deploy the latest version"
```
No template matches. UMH attempts LLM-assisted planning. If LLM fails or returns
an invalid plan, the plan is rejected with "No template found" error.

### 10. Metrics/dashboard check

```bash
python3 -m umh.control.cli plan "show me the system metrics"
```
Maps to template `inspect_system_status` via the "metrics" keyword.

---

## 10. Troubleshooting

### Plan rejected: "No template found for '...'"

Your input did not match any template and LLM planning failed or is unavailable.
Use one of the known trigger keywords from the template table, or use the structured
objective API with an explicit template name as the `title`.

### Plan rejected: shell command not in allowlist

You requested a shell command that is not in the 12-command allowlist. Only `uptime`,
`df -h`, `free -h`, `ps aux`, `whoami`, `hostname`, `uname -a`, `date`, `ls`, `ls -la`,
`cat /proc/loadavg`, and `docker ps` are allowed.

### Quality verdict: fail

Check the `quality.reasons` field in the plan response. Common causes:
- Empty objective title
- Unknown operation in a step
- Shell command not in allowlist
- Missing required inputs (e.g., file_read without a path)

### Task paused: requires approval

The task hit an approval-gated operation. Check `paused_approval_id` in the task
response, then approve via the API.

### 401 "Invalid or missing API key"

Either the `X-API-Key` header is missing, or the key does not match any identity in the
store and does not match the `UMH_API_KEY` env var.

### 403 "Insufficient scope"

Your identity exists but lacks the required scope for the endpoint. Create a new identity
with the needed scopes or use an admin identity.

### 409 "Approval has expired"

The 5-minute TTL elapsed before you approved. The paused task's approval is no longer
valid. You would need to re-trigger the operation to get a fresh approval request.

### 409 "Plan status is '...', must be 'validated'"

You tried to execute a plan that is not in `validated` status. It may be already
executing, completed, failed, or rejected. Create a new plan.

### 422 "Plan quality verdict is 'fail'"

The plan passed validation but failed quality scoring. Check `quality.reasons` for
specifics. Create a new plan with a more specific objective or use a template directly.

### API server not responding

```bash
# Check if the server process is running
ps aux | grep "umh.control"

# Start it
python3 -m umh.control.api &

# Check health
curl http://127.0.0.1:8000/health
```

### CLI errors

The CLI runs Python modules directly and requires the `umh` package to be importable
from `/opt/OS`. If you get import errors:

```bash
cd /opt/OS && python3 -c "import umh.control.cli; print('ok')"
```

---

## 11. Exact Commands to Run

### First-time setup

```bash
# 1. Start the API server (background)
cd /opt/OS && python3 -m umh.control.api &

# 2. Set a legacy API key (quickstart -- skip identity setup)
export UMH_API_KEY="my-secret-key-12345"
export UMH_KEY="my-secret-key-12345"

# 3. Verify server is running
curl http://127.0.0.1:8000/health
```

### Identity setup (production)

```bash
# Create an admin identity (use legacy key for bootstrap)
curl -s -X POST http://127.0.0.1:8000/identities \
  -H "X-API-Key: $UMH_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "admin", "scopes": ["admin"]}' | python3 -m json.tool

# Save the returned api_key, then use it going forward
export UMH_KEY="umh_<the-returned-key>"

# Create a scoped operator identity
curl -s -X POST http://127.0.0.1:8000/identities \
  -H "X-API-Key: $UMH_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "operator", "scopes": ["execute", "approvals:read", "approvals:write", "metrics:read"]}' \
  | python3 -m json.tool
```

### Plan + execute workflow (API)

```bash
# Step 1: Create a plan
PLAN_RESPONSE=$(curl -s -X POST http://127.0.0.1:8000/plans \
  -H "X-API-Key: $UMH_KEY" \
  -H "Content-Type: application/json" \
  -d '{"raw_input": "check system health"}')
echo "$PLAN_RESPONSE" | python3 -m json.tool

# Step 2: Extract plan_id
PLAN_ID=$(echo "$PLAN_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['plan_id'])")
echo "Plan ID: $PLAN_ID"

# Step 3: Execute the plan
curl -s -X POST "http://127.0.0.1:8000/plans/$PLAN_ID/execute" \
  -H "X-API-Key: $UMH_KEY" | python3 -m json.tool
```

### Plan + execute workflow (CLI -- single command)

```bash
python3 -m umh.control.cli execute "check system health"
```

### Check system health (CLI)

```bash
python3 -m umh.control.cli execute "check system health" --json
```

### Read a file (CLI)

```bash
python3 -m umh.control.cli execute "read file /opt/OS/data/runtime/identities.sqlite"
```

### List directory (CLI)

```bash
python3 -m umh.control.cli execute "list files in /opt/OS/data"
```

### Summarize text (CLI)

```bash
python3 -m umh.control.cli execute "summarize the quick brown fox jumps over the lazy dog"
```

### Full approval workflow (API)

```bash
# 1. Execute something that requires approval (e.g., the click demo template)
PLAN_RESPONSE=$(curl -s -X POST http://127.0.0.1:8000/plans \
  -H "X-API-Key: $UMH_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "approval_click_demo",
    "description": "Demo click at coordinates",
    "context": {"x": 500, "y": 300}
  }')
PLAN_ID=$(echo "$PLAN_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['plan_id'])")

# 2. Execute the plan (will pause at the click step)
TASK_RESPONSE=$(curl -s -X POST "http://127.0.0.1:8000/plans/$PLAN_ID/execute" \
  -H "X-API-Key: $UMH_KEY")
echo "$TASK_RESPONSE" | python3 -m json.tool

# 3. Check pending approvals
curl -s "http://127.0.0.1:8000/approvals?status=pending" \
  -H "X-API-Key: $UMH_KEY" | python3 -m json.tool

# 4. Approve (replace with actual approval_id from step 3)
curl -s -X POST http://127.0.0.1:8000/approvals/approval_XXXXXXXXXXXX/approve \
  -H "X-API-Key: $UMH_KEY" | python3 -m json.tool
```

### Monitor events in real time

```bash
# Stream all events (Ctrl+C to stop)
curl -N http://127.0.0.1:8000/events/stream \
  -H "X-API-Key: $UMH_KEY"
```

### Check metrics

```bash
curl -s http://127.0.0.1:8000/metrics \
  -H "X-API-Key: $UMH_KEY" | python3 -m json.tool
```

### View recent events

```bash
curl -s "http://127.0.0.1:8000/events?limit=20" \
  -H "X-API-Key: $UMH_KEY" | python3 -m json.tool
```

### List all tasks and their status

```bash
python3 -m umh.control.cli tasks --json
```

### Stop the API server

```bash
pkill -f "umh.control.api"
```
