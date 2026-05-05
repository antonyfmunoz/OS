# UMH MVP Golden Paths

Five end-to-end operator workflows demonstrating the UMH planning,
execution, and control loop. Each path uses the CLI
(`python3 -m umh.control.cli`) with internal APIs — no HTTP server required.

---

## Path 1: Plan Only

Create a plan from raw input and inspect it without executing.

### Commands

```bash
python3 -m umh.control.cli plan "check system health"
```

### Expected Output

```
Plan: eplan_<hash>
Status: validated
Source: template
Quality: pass (0.883)
Steps:
  1. Check uptime [shell_command] (side_effect)
  2. Check disk usage [shell_command] (side_effect)
  3. Check memory [shell_command] (side_effect)
  4. Check docker containers [shell_command] (side_effect)
Assumptions: System has docker installed; Shell commands are available; Template 'inspect_system_status' matches intent
```

Add `--json` for machine-readable output:

```bash
python3 -m umh.control.cli plan "check system health" --json
```

### What Happens

1. Objective reconstruction parses "check system health" into intent
   category `system_health` with template hint `inspect_system_status`.
2. Template `inspect_system_status` produces a 4-step plan.
3. Validator checks all operations against the known-safe allowlist.
4. Quality scorer rates the plan across 6 dimensions.
5. Explanation module generates assumptions, risks, and safety assessment.

### Exit Codes

| Code | Meaning |
|------|---------|
| 0    | Plan created and validated |
| 1    | Plan rejected (validation or quality failure) |
| 2    | Unexpected error |

### What to Do Next

- If status is `validated`: execute with Path 2.
- If status is `rejected`: check `Errors` line for the reason.

---

## Path 2: Execute Safe Workflow

Create a plan and execute it in one command.

### Commands

```bash
python3 -m umh.control.cli execute "check system health"
```

### Expected Output

```
Plan: eplan_<hash>
Status: validated
Source: template
Quality: pass (0.883)
Steps:
  1. Check uptime [shell_command] (side_effect)
  2. Check disk usage [shell_command] (side_effect)
  3. Check memory [shell_command] (side_effect)
  4. Check docker containers [shell_command] (side_effect)
Assumptions: System has docker installed; Shell commands are available; Template 'inspect_system_status' matches intent

Executing...
Task: task_<hash>
Status: completed
Steps: 4/4
```

Then inspect the task:

```bash
python3 -m umh.control.cli task <task_id>
```

Output:

```
Task: task_<hash>
Status: completed
Steps: 4/4
```

### What Happens

1. Plan creation (same as Path 1).
2. Plan converts to a Task with one TaskStep per plan step.
3. Each step executes through the execution engine sequentially.
4. Step outputs chain into subsequent steps via context.
5. Task status transitions: `pending` -> `running` -> `completed`.
6. Events emitted: `task.started`, `task.step.started/completed` (x4), `task.completed`.

### Exit Codes

| Code | Meaning |
|------|---------|
| 0    | Plan executed successfully |
| 1    | Plan rejected before execution |
| 2    | Execution failed or blocked by quality gate |

### What to Do Next

- Use `python3 -m umh.control.cli task <task_id> --json` for full result data.
- Use `python3 -m umh.control.cli timeline <task_id>` for event history.

---

## Path 3: Inspect File

File inspection workflow using the `inspect_file` template.

### Commands

```bash
python3 -m umh.control.cli execute "inspect /opt/OS/README.md"
```

### Expected Output

```
Plan: eplan_<hash>
Status: validated
Source: template
Quality: pass (0.85)
Steps:
  1. Read file: /opt/OS/README.md [file_read] (side_effect)
Assumptions: File exists at /opt/OS/README.md; Template 'inspect_file' matches intent

Executing...
Task: task_<hash>
Status: completed
Steps: 1/1
```

Inspect results:

```bash
python3 -m umh.control.cli task <task_id> --json
```

### What Happens

1. Objective reconstruction detects `file_inspect` intent and extracts
   the path `/opt/OS/README.md` from the raw input.
2. Template `inspect_file` produces a single `file_read` step.
3. Validator confirms `file_read` is a known safe operation.
4. Execution reads the file and returns contents in step result.

### Exit Codes

| Code | Meaning |
|------|---------|
| 0    | File read successfully |
| 1    | Plan rejected (e.g. no path detected) |
| 2    | Execution failed (e.g. file not found) |

### What to Do Next

- Use `--json` to get the file contents from the step result.
- For file + summary, use `"inspect file summary /opt/OS/README.md"` which
  hits the `inspect_file_summary` template (3 steps: stat, read, summarize).

---

## Path 4: Approval Flow

Demonstrates the pause/approve/resume cycle for high-risk operations.

### Commands

Step 1 — Execute something that requires approval:

```bash
python3 -m umh.control.cli execute "click at position 100 200"
```

Expected output (task pauses):

```
Plan: eplan_<hash>
Status: validated
Source: template
Quality: warn (0.55)
Steps:
  1. Take screenshot [computer_screenshot] (side_effect)
  2. Click at (100, 200) [computer_click] (side_effect)

Executing...
Task: task_<hash>
Status: paused
Steps: 0/2
Approval required: appr_<hash>
```

Step 2 — Check pending approvals:

```bash
python3 -m umh.control.cli approvals
```

Output:

```
Approval: appr_<hash>
  Operation: computer_click
  Risk: high
  Expires: 2026-04-27T12:05:00Z
```

Step 3 — Approve via API (no CLI resume command currently):

```bash
curl -X POST http://127.0.0.1:8000/approvals/<approval_id>/approve \
  -H "X-API-Key: $UMH_API_KEY"
```

Then resume the task:

```bash
curl -X POST http://127.0.0.1:8000/tasks/<task_id>/resume \
  -H "X-API-Key: $UMH_API_KEY"
```

### What Happens

1. Objective reconstruction detects `computer_action` intent.
2. Template `approval_click_demo` produces a 2-step plan (screenshot + click).
3. Quality scorer flags approval-gated operations as warnings.
4. During execution, `computer_click` triggers the authority engine.
5. Authority engine creates an approval request and returns
   `requires_approval: true`.
6. Task pauses at step 1 with status `paused`.
7. Operator approves and resumes — execution continues from the paused step.

### Exit Codes

| Code | Meaning |
|------|---------|
| 0    | Completed (after resume) |
| 2    | Execution blocked or failed |

### What to Do Next

- `python3 -m umh.control.cli timeline <task_id>` shows the full
  pause/resume lifecycle.
- `python3 -m umh.control.cli cancel <task_id>` cancels a paused task
  instead of resuming it.

---

## Path 5: Failure + Retry

Demonstrates the failure detection and retry cycle.

### Commands

Step 1 — Execute something that will fail:

```bash
python3 -m umh.control.cli execute "do something completely invalid"
```

Expected output:

```
Plan: eplan_<hash>
Status: rejected
Source: manual
Quality: fail (0.0)
Errors: No template found for 'do something completely invalid'
```

Exit code: 1 (plan rejected before execution).

Step 2 — For a task that fails during execution (e.g. after plan validates
but a step errors out), retry creates a fresh task:

```bash
python3 -m umh.control.cli retry <task_id>
```

Output:

```
New task: task_<new_hash> (retried from task_<old_hash>)
```

### What Happens

**Rejection path:**
1. Objective reconstruction cannot match any template.
2. No LLM fallback available (or LLM also fails).
3. Plan created with status `rejected` and empty steps.
4. Quality scorer returns `fail` (0.0) — "Plan has no steps".

**Retry path:**
1. `retry_task` checks the original task has status `failed`.
2. Creates a new Task with the same steps, reset to `pending`.
3. New task context includes `retried_from: <original_task_id>`.
4. New task is enqueued (status `pending`).

### Exit Codes

| Code | Meaning |
|------|---------|
| 0    | Retry enqueued successfully |
| 1    | Cannot retry (task not found or not in failed state) |
| 2    | Unexpected error |

### What to Do Next

- `python3 -m umh.control.cli tasks` lists all tasks including retried ones.
- `python3 -m umh.control.cli task <new_task_id>` checks the retried task.

---

## Quick Reference

| Command | Description |
|---------|-------------|
| `plan "<objective>"` | Create and validate a plan |
| `execute "<objective>"` | Create, validate, and execute a plan |
| `task <id>` | Get task status |
| `tasks` | List all tasks |
| `approvals` | List pending approvals |
| `cancel <id>` | Cancel a pending/paused task |
| `retry <id>` | Retry a failed task |
| `timeline <id>` | Show task event timeline |

All commands accept `--json` for machine-readable output.

## Available Templates

| Template Name | Trigger Keywords | Steps |
|---------------|-----------------|-------|
| `inspect_system_status` | system health, status, check system | uptime, disk, memory, docker |
| `inspect_file` | inspect, read, view + file/path | file_read |
| `list_directory` | list, ls, directory | file_list |
| `summarize_text` | summarize, summary, tldr | LLM summarize |
| `shell_health_check` | load, cpu, memory + check/status | loadavg, disk, memory |
| `computer_screenshot_review` | screenshot, screen capture | screenshot + LLM describe |
| `inspect_file_summary` | (via structured objective) | stat + read + summarize |
| `workspace_snapshot` | (via structured objective) | screenshot + screen size |
| `approval_click_demo` | click, type, scroll | screenshot + click (approval-gated) |
| `full_system_diagnostic` | (via structured objective) | loadavg, disk, memory, ps, docker |
