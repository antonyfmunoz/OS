# Phase 6F — Operator Experience Audit

Audited: 2026-04-27
Status: READ-ONLY audit, no code modified

---

## Current Natural-Language Objective Flow

The full pipeline from raw input to executed result:

### 1. Raw Input (operator types a string)
Entry points: CLI `cmd_execute`/`cmd_plan` or API `POST /plans` with `raw_input`.

### 2. `reconstruct_objective()` — `/opt/OS/umh/planning/objective.py:71`
Pure function. Takes raw string, applies regex pattern matching against 9 intent pattern groups (`_INTENT_PATTERNS`, line 14). Extracts:
- Intent category (e.g. `system_health`, `file_inspect`, `summarize`)
- Template hint (e.g. `inspect_system_status`)
- File paths via `_PATH_RE`
- Flags: dry_run, sandbox, max_steps
- Produces a `PlanObjective` dataclass with `uncertainty` and `assumptions` tuples

If no pattern matches, `intent_category` = `"unknown"`, `uncertainty` includes `"Could not determine intent category"`.

### 3. `create_plan_from_raw()` — `/opt/OS/umh/planning/planner.py:41`
Wraps `reconstruct_objective()`, then calls `create_plan()`. Emits `objective.reconstructed` event.

### 4. `create_plan()` — `/opt/OS/umh/planning/planner.py:66`
1. **Template lookup**: `_try_template()` checks if `objective.title` matches a registered template name via `get_template()` in `/opt/OS/umh/planning/templates.py:31`. The title IS the template key -- this is the critical coupling between objective reconstruction and template selection.
2. **LLM fallback**: If no template, `_try_llm_plan()` sends a prompt to `lightweight_execute()` asking for a JSON plan. Response is parsed by `_parse_llm_plan()`.
3. **No match**: If both fail, a REJECTED plan is returned with `"No template found"`.

### 5. `validate_plan()` — `/opt/OS/umh/planning/validator.py:82`
Checks: step count, operation allowlist, execution class validity, shell command allowlist, capability constraints, dependency integrity. Returns `PlanValidationResult` with `valid`, `errors`, `warnings`.

### 6. `score_plan()` — `/opt/OS/umh/planning/quality.py:51`
Scores across 6 equally-weighted dimensions: completeness, safety, specificity, executability, minimality, constraint_alignment. Returns `PlanQualityScore` with numeric score and verdict (pass/warn/fail). Any `[FAIL]` reason forces fail verdict regardless of numeric score.

### 7. `explain_plan()` — `/opt/OS/umh/planning/explanation.py:44`
Pure projection. Assembles `PlanExplanation` from existing plan/validation/quality data: objective_summary, steps_summary, assumptions, risks, approval_requirements, plan_selection_reason, safety_assessment, quality_summary.

### 8. `execute_plan()` — `/opt/OS/umh/planning/planner.py:281`
Quality gate: verdict=fail blocks execution. Converts plan to task via `plan_to_task()`. Calls `execute_task()`.

### 9. `execute_task()` — `/opt/OS/umh/orchestrator/task.py:191`
Iterates through steps sequentially. For each step: resolves `{{context.key}}` / `{{prev_output.key}}` template variables, builds `ExecutionRequest`, calls `execute()`. On success, stores result in step and context. On failure, marks remaining steps as SKIPPED. On approval-required, pauses the task.

### 10. Results returned to operator
The Task object is returned with all step results embedded. Each step's `.result` contains the full `ExecutionResult.to_dict()`.

---

## What A User Sees At Each Step

### CLI: `plan` command
**Human-readable mode** (default): `_format_plan()` at `cli.py:23` produces:
```
Plan: eplan_a1b2c3d4e5f6
Status: validated
Source: template
Quality: pass (0.883)
Steps:
  1. Check uptime [shell_command] (side_effect)
  2. Check disk usage [shell_command] (side_effect)
Assumptions: ...
Risks: ...
```
This is clean and readable. The operator sees the plan structure, quality verdict, and risk assessment before deciding to execute.

**JSON mode** (`--json`): Full `plan.to_dict()` dump -- deeply nested, includes internal IDs, objective reconstruction metadata, quality dimensions. Useful for debugging but overwhelming for operator use.

### CLI: `execute` command
**Human-readable mode**: Prints the plan summary (same as `plan`), then `"Executing..."`, then `_format_task()` at `cli.py:55`:
```
Task: task_abc123def456
Status: completed
Steps: 4/4
```
**Critical gap**: The operator NEVER sees the actual execution results in human-readable mode. `_format_task()` only shows task ID, status, and step count. The actual stdout from shell commands, file contents, LLM responses -- none of it is displayed.

**JSON mode**: Full plan + task dict. Step results ARE present inside `task.steps[N].result.outputs`, but buried 4 levels deep.

### API: `POST /plans`
Returns enriched plan dict with `executable`, `blocked_reason`, and `warnings` added by `_enrich_plan_response()` at `api.py:546`. These fields are genuinely useful -- they tell the operator whether the plan can run and why not. HTTP 200 for validated, 422 for rejected.

### API: `POST /plans/{plan_id}/execute`
Returns full task dict with plan metadata appended: `plan_id`, `objective_summary`, `step_count`, `approval_required`, `approval_id`. If quality verdict is `warn`, `quality_warnings` is included. This is the most useful API response in the system -- it tells the operator what happened AND what to do next if paused.

### API: `GET /tasks/{task_id}`
Returns task dict with `step_statuses`, `current_step`, and `pending_approval` added at `api.py:457-459`. Good status visibility.

### API: `GET /tasks/{task_id}/timeline`
Returns ordered `TimelineEntry` list with human-readable summaries via `_summarize_event()` at `timeline.py:41`. Clean and useful.

### CLI: `approvals` command
Shows pending approvals with operation, risk level, and expiry. Clean format at `cli.py:175-195`.

### CLI: `tasks` command
Lists tasks with same limited `_format_task()` -- no execution output visible.

### CLI: `timeline` command
Shows event timestamps and types. At `cli.py:272`: `[timestamp] event_type` -- bare minimum. No human summaries, no step details.

---

## Missing Clarity Points

### 1. Template matching is invisible to the operator
When `reconstruct_objective()` maps "check system health" to `inspect_system_status`, the operator has no way to know WHY that template was chosen or what other templates were considered. The `intent_category` is buried in the objective dict. The operator guide lists templates, but the system does not surface which one was selected in the human-readable output.

**File**: `cli.py:28` -- `Source: {plan.source.value}` shows "template" but not WHICH template.

### 2. Uncertainty and assumptions are opaque in execution path
`reconstruct_objective()` carefully builds `uncertainty` and `assumptions` tuples (e.g., "No template directly matches -- may require LLM planning"). These are surfaced in the plan explanation, but only in JSON mode. The CLI human-readable format shows assumptions and risks as semicolon-joined strings, but does not distinguish uncertainty from assumptions.

**File**: `cli.py:43-51` -- assumptions and risks are printed, but uncertainty is NOT printed separately.

### 3. No confirmation before execution in CLI
`cmd_execute()` at `cli.py:92` goes straight from plan creation to `execute_plan()` with no pause for operator review. The API separates `POST /plans` from `POST /plans/{id}/execute`, giving the operator a review step. The CLI collapses this into one action with no opt-out.

### 4. LLM fallback is silent
When no template matches and the system falls through to `_try_llm_plan()` at `planner.py:176`, the operator gets no indication that an LLM is being called to generate the plan. The `source: llm` field is in the plan, but there is no explicit notice that the plan is now untrusted and LLM-generated.

### 5. Quality dimensions are not explained
The quality score (e.g., `0.883`) is shown, but the 6 individual dimension scores are only in the JSON `quality.dimensions` dict. An operator seeing `Quality: warn (0.52)` has no idea which dimension pulled the score down without switching to JSON mode.

---

## Confusing / Opaque Outputs

### 1. Task execution results are raw dicts (MOST CRITICAL)
When a task completes, each step's `result` is the full `ExecutionResult.to_dict()` -- a dict with 18 fields including `execution_id`, `correlation_id`, `causal_event_id`, `node_id`, `idempotency_key`, `execution_hash`, `retry_count`, `model_used`, `tokens_used`, `cost_usd`, `latency_ms`, `side_effects`, etc.

The actual useful information -- the stdout from a shell command, the text from a file read, the LLM response from a summarize -- is buried inside `outputs.stdout` or `outputs.response`. An operator looking at JSON output must dig through multiple levels of infrastructure metadata to find the answer to their question.

**File**: `task.py:261` -- `step.result = result_dict` stores the entire dict.
**File**: `api.py:444` -- `return result.to_dict()` dumps it all to the API consumer.

### 2. CLI `_format_task()` shows nothing useful about completed results
`cli.py:55-72`: The task formatter shows ID, status, step count, approval ID (if paused), and error (if failed). It does NOT show:
- What each step actually produced
- Shell command stdout/stderr
- LLM response text
- File contents that were read
- Any summary of what happened

An operator running `python3 -m umh.control.cli execute "check system health"` sees:
```
Plan: eplan_...
Status: validated
...
Executing...
Task: task_...
Status: completed
Steps: 4/4
```
No uptime output. No disk usage. No memory stats. No docker status. The operator asked "check system health" and got back "completed 4/4".

### 3. Plan `to_dict()` includes objective reconstruction internals
`models.py:53-75`: `PlanObjective.to_dict()` includes `raw_input`, `intent_category`, `inferred_constraints`, `uncertainty`, and `assumptions_obj`. These are useful for debugging but confusing in an operator-facing response. The field name `assumptions_obj` (line 74) is particularly odd -- it exists to avoid collision with plan-level `assumptions` but reads as a typo or internal implementation detail.

### 4. API metrics response is a wall of nested dicts
`api.py:313-319`: The `/metrics` endpoint assembles capabilities, environments, scoring stats, approvals, tasks, and plans into a single massive JSON response. No summary, no highlights, no "here is what matters" section. An operator checking system health via metrics must parse through capability status maps, per-environment scoring breakdowns, and approval counters to find anything useful.

### 5. Timeline CLI output is timestamp + event type only
`cli.py:272`: `[2026-04-27T12:00:01+00:00] task.step.started` -- no step name, no operation, no human summary. The `build_task_timeline()` function at `timeline.py:75` produces rich `TimelineEntry` objects with `.summary` strings, but the CLI formatter at `cli.py:272` ignores the summary field entirely.

---

## Approval UX Gaps

### 1. No notification system
When a task pauses for approval, the only way the operator discovers this is by:
- Seeing `"status": "paused"` in the execute response (if they are watching)
- Polling `GET /approvals?status=pending` or `python3 -m umh.control.cli approvals`
- Watching the SSE event stream (`GET /events/stream`)

There is no push notification, no CLI alert, no sound, no email, no webhook. If the operator walks away between creating the plan and the task hitting an approval-gated step, the approval will silently expire after 5 minutes.

### 2. No CLI approve/deny commands
The CLI has `approvals` (list pending) but no `approve <id>` or `deny <id>` commands. The operator must switch to curl/API to approve. The operator guide at line 730-746 explicitly documents this as a multi-step curl workflow. This breaks the CLI-first workflow.

**File**: `cli.py:276-322` -- `build_parser()` registers `plan`, `execute`, `task`, `tasks`, `approvals`, `cancel`, `retry`, `timeline`. No `approve` or `deny` subcommand exists.

### 3. No CLI resume command
After approving via API, the operator must also call `POST /tasks/{task_id}/resume` via API. There is no CLI `resume` command.

**File**: `cli.py:276-322` -- no `resume` subcommand.

### 4. Approval response lacks context about WHAT is being approved
When listing approvals (`cli.py:188-194`), the operator sees:
```
Approval: approval_abc123
  Operation: computer_click
  Risk: high
  Expires: 2026-04-27T12:05:00+00:00
```
Missing: WHICH task this approval belongs to, WHAT the click coordinates are, WHAT the screenshot looks like, WHY the system wants to click there. The approval request's `inputs_summary` field (shown in the operator guide at line 435) contains `"x=500, y=300"` but the CLI does not display it.

### 5. Denied approval leaves task in limbo
After denial (`api.py:209-223`), the task stays in `paused` status. There is no automatic transition to `failed` or `cancelled`. The operator must separately cancel the task. This is documented in the operator guide (line 710: "Task stays paused (operator must handle)") but is a poor UX -- denial should offer or trigger a task cancellation.

### 6. Expired approval has no recovery path
If the 5-minute TTL expires, the approval becomes permanently expired. The task is still paused but the approval is dead. The operator guide says "You would need to re-trigger the operation to get a fresh approval request" (line 1025) but there is no command to do this. The task is effectively stuck -- it cannot be resumed (no valid approval), and there is no "re-request approval" action.

---

## Final Result Summary Gaps

### 1. No human-readable execution summary exists
After `execute_task()` completes, the returned Task object contains all step results as raw `ExecutionResult.to_dict()` blobs inside `task.steps[N].result`. There is no module, function, or formatter that extracts the useful output and presents it.

**Missing file**: `/opt/OS/umh/orchestrator/summary.py` does not exist. The audit confirms this file was expected but never created.

### 2. CLI execute output ignores step results entirely
As documented above, `_format_task()` at `cli.py:55-72` does not access step results at all. The most important information -- the actual answer to the operator's question -- is silently discarded in human-readable mode.

### 3. API execute response includes results but without extraction
The API at `api.py:444` returns `result.to_dict()` which includes full step results, but there is no summary layer. An operator who asked "check system health" gets back a nested JSON with 4 step results, each containing `outputs.stdout` buried under execution metadata. The useful information requires manual extraction:
```
response.steps[0].result.outputs.stdout -> uptime string
response.steps[1].result.outputs.stdout -> df -h output
response.steps[2].result.outputs.stdout -> free -h output
response.steps[3].result.outputs.stdout -> docker ps output
```

### 4. No aggregated success/failure summary
When a task completes with some steps succeeded and some failed, there is no summary telling the operator: "3/4 steps succeeded. Step 4 (docker ps) failed because docker is not running." The `task.error` field (line 305 in task.py) captures the failure message but only for the FIRST failed step.

### 5. No cost/latency summary
Each `ExecutionResult` tracks `cost_usd`, `latency_ms`, `tokens_used`, and `model_used`. But there is no aggregation -- the operator cannot see total cost, total latency, or total tokens for a task without manually summing step results.

---

## Minimal Improvements Needed for MVP

Ranked by impact-to-effort ratio. Smallest changes, biggest UX difference.

### Rank 1: Add step output display to CLI `_format_task()` (CRITICAL)
**File**: `cli.py:55-72`
**Change**: After printing step count, iterate through completed steps and print the useful output (stdout for shell commands, response for LLM calls, content for file reads). ~20 lines of code.
**Impact**: Transforms the CLI from "it ran" to "here is what happened." This is the single biggest UX gap -- the operator currently gets zero information about execution results in the default CLI mode.

### Rank 2: Add `approve` and `deny` CLI subcommands
**File**: `cli.py` -- add two new `cmd_approve()` and `cmd_deny()` functions, register in `build_parser()`.
**Change**: Call `get_approval_store().approve(id, approved_by="cli")` and `.deny(id)`. ~30 lines.
**Impact**: Eliminates the forced switch to curl for the most time-sensitive operation in the system. Approval TTL is 5 minutes -- forcing the operator to construct a curl command is hostile.

### Rank 3: Add `resume` CLI subcommand
**File**: `cli.py` -- add `cmd_resume()` that calls `resume_task()`.
**Change**: ~20 lines.
**Impact**: Completes the CLI approval lifecycle. Currently: plan (CLI) -> execute (CLI) -> approve (API only) -> resume (API only). All four steps should be CLI-accessible.

### Rank 4: Show timeline summaries instead of raw event types in CLI
**File**: `cli.py:272`
**Change**: Replace `print(f"  [{entry['timestamp']}] {entry['type']}")` with `print(f"  [{entry['timestamp']}] {entry.get('summary', entry['type'])}")` when using `build_task_timeline()` which already produces summaries.
**Impact**: 1-line change. Timeline becomes human-readable instead of showing raw event type strings.

### Rank 5: Print which template was selected in CLI plan output
**File**: `cli.py:23-52`
**Change**: Add `lines.append(f"Template: {plan.objective.title}")` when source is "template".
**Impact**: 1-line change. Operator understands WHY the system chose this plan.

### Rank 6: Display `inputs_summary` in CLI approval listing
**File**: `cli.py:189-194`
**Change**: Add `f"  What: {req.inputs_summary}\n"` to the approval display format.
**Impact**: 1-line change. Operator sees WHAT they are approving (e.g., "x=500, y=300") without switching to JSON mode.

### Rank 7: Add task-level output summary to API execute response
**File**: `api.py:647-696`
**Change**: After getting the task result, extract key outputs from each completed step and add a `result_summary` dict to the response (e.g., `{"step_0_uptime": "up 45 days", "step_1_disk": "52% used"}`). ~15 lines.
**Impact**: API consumers get the answer without parsing nested step result dicts.

### Rank 8: Auto-cancel task on approval denial
**File**: `api.py:209-223`
**Change**: After denying an approval, find the associated paused task via `find_paused_task_by_approval()` and call `cancel_task()`. Include task cancellation in the deny response.
**Impact**: Eliminates the limbo state where a denied task sits paused with no recovery path.

### Rank 9: Add confirmation prompt to CLI execute command
**File**: `cli.py:92`
**Change**: After creating and displaying the plan, ask `Execute? [y/N]` before calling `execute_plan()`. Add `--yes` flag to skip.
**Impact**: Gives the operator a review step before execution, matching the API's two-step flow.

### Rank 10: Display quality dimension breakdown for warn/fail verdicts in CLI
**File**: `cli.py:32-33`
**Change**: When verdict is warn or fail, print individual dimension scores from `plan.quality_score.get("dimensions", {})`.
**Impact**: Operator understands which quality dimension failed without switching to JSON mode.

---

## Summary of Findings

The planning pipeline (objective reconstruction through quality scoring and explanation) is well-engineered with thoughtful separation of concerns. The validation, quality, and explanation layers produce rich, structured data.

The critical failure is in the **last mile**: the system generates useful execution results but does not surface them to the operator. The CLI `_format_task()` function is the single biggest gap -- it discards all step outputs. An operator who asks "check system health" and gets back "Steps: 4/4" has learned nothing.

The approval workflow is functionally correct but operationally broken for CLI users. The three-step sequence (approve via API, resume via API) forces a context switch from CLI to curl at the most time-sensitive moment in the system (5-minute TTL).

Rank 1-3 improvements would make the MVP genuinely usable as a daily operator tool. Rank 4-6 are single-line changes with disproportionate clarity gains. All 10 items are achievable in a single session.
