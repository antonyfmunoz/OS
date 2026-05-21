"""UMH CLI — operator command-line surface for the UMH execution system.

Usage:
    python3 -m umh.control.cli plan "check system health"
    python3 -m umh.control.cli plan "check system health" --json
    python3 -m umh.control.cli run "check system health"
    python3 -m umh.control.cli run "check system health" --json
    python3 -m umh.control.cli execute "check system health"
    python3 -m umh.control.cli watch <task_id> [--timeout 60]
    python3 -m umh.control.cli task <task_id>
    python3 -m umh.control.cli task <task_id> --json
    python3 -m umh.control.cli tasks
    python3 -m umh.control.cli approvals
    python3 -m umh.control.cli memory [--type task] [--limit 20] [--json]
    python3 -m umh.control.cli memory-search "keyword" [--limit 10] [--json]
    python3 -m umh.control.cli memory-add --type insight --content "..." [--tags tag1,tag2] [--json]
    python3 -m umh.control.cli memory-stats [--json]
"""

from __future__ import annotations

import argparse
import json
import sys
import time

sys.path.insert(0, "/opt/OS")


# ── Formatting helpers ────────────────────────────────────────────


def _format_plan(plan) -> str:
    """Human-readable plan display — concise and scannable."""
    lines: list[str] = []
    obj = plan.objective

    # Header
    lines.append(f"Plan: {plan.plan_id}")
    lines.append(f"Status: {plan.status.value}")

    # Objective reconstruction
    lines.append("")
    lines.append("Objective:")
    lines.append(f"  Intent: {obj.intent_category or 'unknown'}")
    if obj.assumptions:
        lines.append(f"  Assumptions: {'; '.join(obj.assumptions)}")
    if obj.constraints:
        lines.append(f"  Constraints: {', '.join(obj.constraints)}")

    # Template / source
    source = plan.source.value
    if source == "template":
        lines.append(f"  Template: {obj.title}")
    else:
        lines.append(f"  Source: {source}")

    # Steps
    if plan.steps:
        lines.append("")
        lines.append("Steps:")
        for i, step in enumerate(plan.steps, 1):
            lines.append(f"  {i}. {step.name} [{step.operation}] ({step.execution_class})")

    # Validation
    lines.append("")
    quality = plan.quality_score or {}
    verdict = quality.get("verdict", "n/a")
    score = quality.get("score", 0)

    if plan.status.value == "validated":
        lines.append("Validation: PASSED")
    elif plan.status.value == "rejected":
        lines.append("Validation: REJECTED")
        if plan.validation_errors:
            for err in plan.validation_errors:
                lines.append(f"  - {err}")
    else:
        lines.append(f"Validation: {plan.status.value}")

    # Quality
    lines.append(
        f"Quality: {verdict} ({score:.3f})"
        if isinstance(score, float)
        else f"Quality: {verdict} ({score})"
    )
    reasons = quality.get("reasons", [])
    if reasons:
        for r in reasons[:5]:
            lines.append(f"  - {r}")
        if len(reasons) > 5:
            lines.append(f"  ... and {len(reasons) - 5} more")

    # Explanation
    explanation = plan.explanation or {}
    assumptions = explanation.get("assumptions", [])
    risks = explanation.get("risks", [])
    safety = explanation.get("safety_assessment", "")

    if assumptions:
        lines.append("")
        lines.append("Assumptions:")
        for a in assumptions:
            lines.append(f"  - {a}")

    if risks:
        lines.append("")
        lines.append("Risks:")
        for r in risks:
            lines.append(f"  - {r}")

    if safety:
        lines.append("")
        lines.append(f"Safety: {safety}")

    # Executable?
    lines.append("")
    if plan.status.value == "validated" and verdict != "fail":
        lines.append("Executable: yes")
    else:
        reason = "plan rejected" if plan.status.value == "rejected" else f"quality={verdict}"
        if plan.validation_errors:
            reason = plan.validation_errors[0]
        lines.append(f"Executable: no ({reason})")

    return "\n".join(lines)


def _format_plan_brief(plan) -> str:
    """Abbreviated plan summary for the run command."""
    obj = plan.objective
    quality = plan.quality_score or {}
    verdict = quality.get("verdict", "n/a")
    score = quality.get("score", 0)
    step_count = len(plan.steps)

    lines: list[str] = [
        f"Plan: {plan.plan_id} | {plan.source.value} | {step_count} step(s)",
        f"Quality: {verdict} ({score:.3f})"
        if isinstance(score, float)
        else f"Quality: {verdict} ({score})",
        f"Status: {plan.status.value}",
    ]
    return "\n".join(lines)


def _format_task(task) -> str:
    """Human-readable task summary — uses summarize_task when available."""
    try:
        from umh.orchestrator.summary import summarize_task

        summary = summarize_task(task)
        return _format_summary_dict(summary)
    except ImportError:
        pass

    # Fallback: inline formatting
    return _format_task_fallback(task)


def _format_summary_dict(summary: dict) -> str:
    """Format the dict returned by summarize_task() for terminal output."""
    lines: list[str] = []

    if "task_id" in summary:
        lines.append(f"Task: {summary['task_id']}")
    if "status" in summary:
        lines.append(f"Status: {summary['status']}")
    if "progress" in summary:
        lines.append(f"Progress: {summary['progress']}")
    if "duration" in summary:
        lines.append(f"Duration: {summary['duration']}")
    if "current_step" in summary:
        lines.append(f"Current step: {summary['current_step']}")

    steps = summary.get("steps", [])
    if steps:
        lines.append("Steps:")
        for s in steps:
            lines.append(f"  {s}")

    if summary.get("error"):
        lines.append(f"Error: {summary['error']}")

    if summary.get("approval_id"):
        lines.append(f"Approval required: {summary['approval_id']}")
    if summary.get("approval_reason"):
        lines.append(f"Approval reason: {summary['approval_reason']}")

    # Catch any remaining keys not explicitly handled
    handled = {
        "task_id",
        "status",
        "progress",
        "duration",
        "current_step",
        "steps",
        "error",
        "approval_id",
        "approval_reason",
    }
    for key in sorted(set(summary) - handled):
        val = summary[key]
        if val:
            lines.append(f"{key}: {val}")

    return "\n".join(lines) if lines else "(empty summary)"


def _format_task_fallback(task) -> str:
    """Inline task formatting when summary module is unavailable."""
    from umh.orchestrator.task import StepStatus

    lines: list[str] = []
    lines.append(f"Task: {task.id}")
    lines.append(f"Status: {task.status.value}")

    completed = sum(1 for s in task.steps if s.status == StepStatus.COMPLETED)
    lines.append(f"Progress: {completed}/{len(task.steps)} steps")

    if task.status.value == "paused" and task.paused_approval_id:
        lines.append(f"Approval required: {task.paused_approval_id}")
        if task.paused_reason:
            lines.append(f"Approval reason: {task.paused_reason}")

    if task.error:
        lines.append(f"Error: {task.error}")

    return "\n".join(lines)


# ── Commands ──────────────────────────────────────────────────────


def cmd_plan(args: argparse.Namespace) -> int:
    """Create a plan from raw input and display it."""
    from umh.planning.models import PlanStatus
    from umh.planning.planner import create_plan_from_raw

    plan = create_plan_from_raw(args.objective, requested_by="cli")

    if args.json:
        print(json.dumps(plan.to_dict(), indent=2))
    else:
        print(_format_plan(plan))

        # Show agent review if present
        review = getattr(plan, "review", None)
        if review:
            review_output = review.get("output", review)
            print(
                f"\nReview: {review_output.get('verdict', '-')} "
                f"(risk: {review_output.get('risk_level', '-')})"
            )
            issues = review_output.get("issues", [])
            if issues:
                for issue in issues:
                    print(f"  [{issue.get('severity', 'info')}] {issue.get('message', '')}")

    if plan.status == PlanStatus.REJECTED:
        return 1
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    """Plan + execute in one shot. Combines plan and execute flow."""
    from umh.planning.models import PlanStatus
    from umh.planning.planner import create_plan_from_raw, execute_plan

    plan = create_plan_from_raw(args.objective, requested_by="cli")

    # Show abbreviated plan
    if not args.json:
        print(_format_plan_brief(plan))
        print()

    # Gate: rejected plan
    if plan.status != PlanStatus.VALIDATED:
        if args.json:
            print(json.dumps({"error": "plan_not_executable", "plan": plan.to_dict()}, indent=2))
        else:
            reason = "plan rejected"
            if plan.validation_errors:
                reason = plan.validation_errors[0]
            print(f"Blocked: {reason}")
        return 1

    # Gate: quality fail
    quality = plan.quality_score or {}
    verdict = quality.get("verdict", "pass")
    if verdict == "fail":
        if args.json:
            print(
                json.dumps(
                    {
                        "error": "quality_fail",
                        "score": quality.get("score", 0),
                        "plan": plan.to_dict(),
                    },
                    indent=2,
                )
            )
        else:
            print(f"Blocked: quality verdict is 'fail' (score={quality.get('score', 0)})")
        return 1

    # Execute through the execution engine (not directly)
    try:
        task = execute_plan(plan)
    except ValueError as exc:
        if args.json:
            print(json.dumps({"error": str(exc), "plan": plan.to_dict()}, indent=2))
        else:
            print(f"Execution blocked: {exc}")
        return 2

    if task is None:
        if args.json:
            print(json.dumps({"plan": plan.to_dict(), "task": None, "dry_run": True}, indent=2))
        else:
            print("Dry run -- not executed.")
        return 0

    # Print result
    if args.json:
        print(json.dumps({"plan": plan.to_dict(), "task": task.to_dict()}, indent=2))
    else:
        print(f"Task: {task.id}")
        print(f"Status: {task.status.value}")
        print()
        print(f"Inspect: python3 -m umh.control.cli task {task.id}")

        if task.status.value == "paused" and task.paused_approval_id:
            print()
            print(f"Paused for approval: {task.paused_approval_id}")
            if task.paused_reason:
                print(f"Reason: {task.paused_reason}")

    if task.status.value == "failed":
        return 2
    return 0


def cmd_execute(args: argparse.Namespace) -> int:
    """Create a plan, then execute it through the task system."""
    from umh.planning.models import PlanStatus
    from umh.planning.planner import create_plan_from_raw, execute_plan

    plan = create_plan_from_raw(args.objective, requested_by="cli")

    if plan.status != PlanStatus.VALIDATED:
        if args.json:
            print(json.dumps({"error": "plan_rejected", "plan": plan.to_dict()}, indent=2))
        else:
            print(_format_plan(plan))
        return 1

    try:
        task = execute_plan(plan)
    except ValueError as exc:
        if args.json:
            print(json.dumps({"error": str(exc), "plan": plan.to_dict()}, indent=2))
        else:
            print(_format_plan(plan))
            print(f"\nExecution blocked: {exc}")
        return 2

    if task is None:
        # dry_run mode
        if args.json:
            print(json.dumps({"plan": plan.to_dict(), "task": None, "dry_run": True}, indent=2))
        else:
            print(_format_plan(plan))
            print("\nDry run -- not executed.")
        return 0

    if args.json:
        print(json.dumps({"plan": plan.to_dict(), "task": task.to_dict()}, indent=2))
    else:
        print(_format_plan(plan))
        print()
        print("Executing...")
        print(_format_task(task))

    if task.status.value == "failed":
        return 2
    return 0


def cmd_watch(args: argparse.Namespace) -> int:
    """Poll task status until terminal state or timeout."""
    from umh.orchestrator.task import TaskStatus, get_task

    timeout = args.timeout
    deadline = time.monotonic() + timeout
    last_status = None

    while True:
        task = get_task(args.task_id)
        if task is None:
            if args.json:
                print(json.dumps({"error": f"Task '{args.task_id}' not found"}))
            else:
                print(f"Task not found: {args.task_id}")
            return 1

        current_status = task.status.value

        if current_status != last_status:
            if not args.json:
                print(f"[{current_status}]")
            last_status = current_status

        # Terminal states
        if task.status == TaskStatus.COMPLETED:
            if args.json:
                print(json.dumps({"status": "completed", "task": task.to_dict()}, indent=2))
            else:
                print()
                print(_format_task(task))
            return 0

        if task.status == TaskStatus.FAILED:
            if args.json:
                print(json.dumps({"status": "failed", "task": task.to_dict()}, indent=2))
            else:
                print()
                print(_format_task(task))
                if task.error:
                    print(f"Error: {task.error}")
            return 2

        if task.status == TaskStatus.PAUSED:
            if args.json:
                print(json.dumps({"status": "paused", "task": task.to_dict()}, indent=2))
            else:
                print()
                print(_format_task(task))
                if task.paused_approval_id:
                    print(f"Approval required: {task.paused_approval_id}")
            return 0

        if task.status == TaskStatus.CANCELLED:
            if args.json:
                print(json.dumps({"status": "cancelled", "task": task.to_dict()}, indent=2))
            else:
                print()
                print(f"Task cancelled: {task.id}")
            return 0

        # Timeout check
        if time.monotonic() >= deadline:
            if args.json:
                print(json.dumps({"status": "timeout", "task": task.to_dict()}, indent=2))
            else:
                print()
                print(f"Timeout after {timeout}s. Current state:")
                print(_format_task(task))
            return 1

        time.sleep(2)


def cmd_task(args: argparse.Namespace) -> int:
    """Get a single task by ID, using summary format."""
    from umh.orchestrator.task import get_task

    task = get_task(args.task_id)
    if task is None:
        if args.json:
            print(json.dumps({"error": f"Task '{args.task_id}' not found"}))
        else:
            print(f"Task not found: {args.task_id}")
        return 1

    if args.json:
        try:
            from umh.orchestrator.summary import summarize_task

            summary = summarize_task(task)
            print(json.dumps({"task": task.to_dict(), "summary": summary}, indent=2))
        except ImportError:
            print(json.dumps(task.to_dict(), indent=2))
    else:
        print(_format_task(task))
    return 0


def cmd_tasks(args: argparse.Namespace) -> int:
    """List all tasks."""
    from umh.orchestrator.task import list_tasks

    tasks = list_tasks()

    if args.json:
        print(json.dumps([t.to_dict() for t in tasks], indent=2))
    else:
        if not tasks:
            print("No tasks.")
        else:
            for task in tasks:
                print(_format_task(task))
                print()
    return 0


def cmd_approvals(args: argparse.Namespace) -> int:
    """List pending approvals."""
    from umh.execution.approval import get_approval_store

    store = get_approval_store()
    pending = store.list_pending()

    if args.json:
        print(json.dumps([r.to_dict() for r in pending], indent=2))
    else:
        if not pending:
            print("No pending approvals.")
        else:
            for req in pending:
                print(
                    f"Approval: {req.id}\n"
                    f"  Operation: {req.operation}\n"
                    f"  Risk: {req.risk_level}\n"
                    f"  Expires: {req.expires_at}\n"
                )
    return 0


def cmd_cancel(args: argparse.Namespace) -> int:
    """Cancel a PENDING or PAUSED task."""
    from umh.orchestrator.task import cancel_task

    result = cancel_task(args.task_id)
    if result is None:
        if args.json:
            print(json.dumps({"error": f"Cannot cancel task '{args.task_id}'"}))
        else:
            print(f"Cannot cancel task: {args.task_id}")
        return 1

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(f"Cancelled: {result.id}")
    return 0


def cmd_retry(args: argparse.Namespace) -> int:
    """Retry a FAILED task by creating a new one."""
    from umh.orchestrator.task import retry_task

    new_task = retry_task(args.task_id)
    if new_task is None:
        if args.json:
            print(json.dumps({"error": f"Cannot retry task '{args.task_id}'"}))
        else:
            print(f"Cannot retry task: {args.task_id}")
        return 1

    if args.json:
        d = new_task.to_dict()
        d["retried_from"] = args.task_id
        print(json.dumps(d, indent=2))
    else:
        print(f"New task: {new_task.id} (retried from {args.task_id})")
    return 0


def cmd_timeline(args: argparse.Namespace) -> int:
    """Show event timeline for a task."""
    from umh.orchestrator.timeline import build_task_timeline

    timeline = build_task_timeline(args.task_id)

    if not timeline:
        if args.json:
            print(json.dumps({"error": f"No timeline for task '{args.task_id}'", "entries": []}))
        else:
            print(f"No events for task: {args.task_id}")
        return 1 if not timeline else 0

    if args.json:
        print(json.dumps([e.to_dict() for e in timeline], indent=2))
    else:
        for entry in timeline:
            print(f"  [{entry.timestamp}] {entry.event_type}: {entry.summary}")
    return 0


# ── Review Command ───────────────────────────────────────────────


def cmd_review(args: argparse.Namespace) -> int:
    """Show the agent review for a plan."""
    from umh.planning.planner import get_plan

    plan = get_plan(args.plan_id)
    if plan is None:
        if args.json:
            print(json.dumps({"error": f"Plan not found: {args.plan_id}"}))
        else:
            print(f"Plan not found: {args.plan_id}")
        return 1

    review = getattr(plan, "review", None)
    debug_analysis = getattr(plan, "debug_analysis", None)
    decision_trace = getattr(plan, "decision_trace", None)

    if args.json:
        result: dict = {}
        if review:
            result["review"] = review
        if debug_analysis:
            result["debug_analysis"] = debug_analysis
        if decision_trace:
            result["decision_trace"] = decision_trace
        print(json.dumps(result, indent=2))
    else:
        if review:
            review_output = review.get("output", review)
            print("=== Plan Review ===")
            print(f"Verdict: {review_output.get('verdict', '-')}")
            print(f"Risk: {review_output.get('risk_level', '-')}")
            print(f"Summary: {review_output.get('summary', '-')}")
            issues = review_output.get("issues", [])
            if issues:
                print(f"\nIssues ({len(issues)}):")
                for issue in issues:
                    sev = issue.get("severity", "info")
                    msg = issue.get("message", "")
                    step = issue.get("step_index")
                    loc = f" (step {step})" if step is not None else ""
                    print(f"  [{sev}]{loc} {msg}")
            suggestions = review_output.get("suggestions", [])
            if suggestions:
                print("\nSuggestions:")
                for s in suggestions:
                    print(f"  - {s}")
        else:
            print("No review available for this plan.")

        if debug_analysis:
            debug = debug_analysis.get("output", debug_analysis)
            print("\n=== Debug Analysis ===")
            print(f"Root cause: {debug.get('root_cause', '-')}")
            print(f"Category: {debug.get('failure_category', '-')}")
            print(f"Retryable: {debug.get('retryable', False)}")
            print(f"Suggested fix: {debug.get('suggested_fix', '-')}")
    return 0


# ── Tool Commands ────────────────────────────────────────────────


def cmd_tools(args: argparse.Namespace) -> int:
    """List all registered tools."""
    from umh.tools.registry import list_tools

    tools = list_tools()
    if args.json:
        print(
            json.dumps(
                [
                    {
                        "name": t.name,
                        "description": t.description,
                        "mutating": t.mutating,
                        "required_inputs": list(t.required_inputs),
                    }
                    for t in tools
                ],
                indent=2,
            )
        )
    else:
        if not tools:
            print("No tools registered.")
        else:
            for t in tools:
                mut = " [MUTATING]" if t.mutating else ""
                print(f"  {t.name:20s} {t.description}{mut}")
                print(f"    Required: {', '.join(t.required_inputs)}")
    return 0


def cmd_tool_run(args: argparse.Namespace) -> int:
    """Execute a tool by name through the planning layer."""
    from umh.tools.registry import get_tool
    from umh.planning.models import PlanObjective, PlanStatus
    from umh.planning.planner import create_plan, execute_plan

    tool = get_tool(args.tool_name)
    if tool is None:
        if args.json:
            print(json.dumps({"error": f"Unknown tool: {args.tool_name}"}))
        else:
            print(f"Unknown tool: {args.tool_name}")
        return 1

    method = args.method if args.method else "GET"
    context: dict = {"url": args.url or "", "method": method}
    if args.body:
        context["body"] = args.body

    template_name = "send_webhook" if tool.mutating else "fetch_data"

    objective = PlanObjective(
        title=template_name,
        description=f"Execute tool '{args.tool_name}' via CLI",
        context=context,
        requested_by="cli",
    )

    plan = create_plan(objective)

    if plan.status != PlanStatus.VALIDATED:
        reason = plan.validation_errors[0] if plan.validation_errors else "plan rejected"
        if args.json:
            print(json.dumps({"error": reason, "plan": plan.to_dict()}, indent=2))
        else:
            print(f"Blocked: {reason}")
        return 1

    try:
        task = execute_plan(plan)
    except ValueError as exc:
        if args.json:
            print(json.dumps({"error": str(exc)}, indent=2))
        else:
            print(f"Execution blocked: {exc}")
        return 2

    if task is None:
        if args.json:
            print(json.dumps({"dry_run": True}, indent=2))
        else:
            print("Dry run -- not executed.")
        return 0

    task_dict = task.to_dict()
    if args.json:
        print(json.dumps(task_dict, indent=2))
    else:
        print(f"Tool: {args.tool_name}")
        print(f"Status: {task_dict.get('status', 'unknown')}")
        steps = task_dict.get("steps", [])
        if steps:
            last_step = steps[-1]
            outputs = last_step.get("result", {})
            if outputs:
                status_code = outputs.get("status_code")
                if status_code is not None:
                    print(f"HTTP Status: {status_code}")
                body_text = outputs.get("body", "")
                if body_text:
                    preview = body_text[:500]
                    if len(body_text) > 500:
                        preview += "..."
                    print(f"Response: {preview}")
        error = task_dict.get("error")
        if error:
            print(f"Error: {error}")
    return 0


# ── Memory Commands ──────────────────────────────────────────────


def _format_memory_row(m) -> str:
    """Format a single memory as a table-like row."""
    content = m.content[:80] + "..." if len(m.content) > 80 else m.content
    tags = ", ".join(m.tags) if m.tags else ""
    return f"{m.id} | {m.type} | {content} | {tags} | {m.created_at}"


def _memory_to_dict(m) -> dict:
    """Convert a Memory to a JSON-safe dict."""
    return {
        "id": m.id,
        "type": m.type,
        "content": m.content,
        "metadata": m.metadata,
        "tags": m.tags,
        "created_at": m.created_at,
    }


def cmd_memory(args: argparse.Namespace) -> int:
    """List memories, optionally filtered by type."""
    from umh.memory.persistent_store import get_memory_store

    store = get_memory_store()
    memories = store.list_memories(type=args.type, limit=args.limit)

    if args.json:
        print(json.dumps([_memory_to_dict(m) for m in memories], indent=2))
    else:
        if not memories:
            print("No memories.")
        else:
            for m in memories:
                print(_format_memory_row(m))
    return 0


def cmd_memory_search(args: argparse.Namespace) -> int:
    """Search memories by keyword."""
    from umh.memory.persistent_store import get_memory_store

    store = get_memory_store()
    memories = store.search_memories(args.query, limit=args.limit)

    if args.json:
        print(json.dumps([_memory_to_dict(m) for m in memories], indent=2))
    else:
        if not memories:
            print("No matches.")
        else:
            for m in memories:
                print(_format_memory_row(m))
    return 0


def cmd_memory_add(args: argparse.Namespace) -> int:
    """Add a memory manually."""
    from umh.memory.persistent_store import VALID_MEMORY_TYPES, get_memory_store

    if args.type not in VALID_MEMORY_TYPES:
        msg = f"Invalid type '{args.type}'. Must be one of: {', '.join(sorted(VALID_MEMORY_TYPES))}"
        if args.json:
            print(json.dumps({"error": msg}))
        else:
            print(msg)
        return 1

    store = get_memory_store()
    tags = [t.strip() for t in args.tags.split(",") if t.strip()] if args.tags else []
    memory = store.save_memory(type=args.type, content=args.content, tags=tags)

    if args.json:
        print(json.dumps(_memory_to_dict(memory), indent=2))
    else:
        print(f"Saved: {memory.id}")
    return 0


def cmd_memory_stats(args: argparse.Namespace) -> int:
    """Show memory statistics."""
    from umh.memory.persistent_store import VALID_MEMORY_TYPES, get_memory_store

    store = get_memory_store()
    total = store.count_memories()
    type_counts: dict[str, int] = {}
    for t in sorted(VALID_MEMORY_TYPES):
        type_counts[t] = len(store.list_memories(type=t, limit=999999))

    if args.json:
        print(json.dumps({"total": total, **type_counts}, indent=2))
    else:
        parts = [f"Total: {total}"]
        for t in sorted(VALID_MEMORY_TYPES):
            parts.append(f"{t}: {type_counts[t]}")
        print(" | ".join(parts))
    return 0


# ── Schedule Commands ───────────────────────────────────────────


def cmd_schedules(args: argparse.Namespace) -> int:
    """List all scheduled workflows."""
    from umh.scheduler.store import get_schedule_store

    store = get_schedule_store()
    workflows = store.list_all()

    if args.json:
        print(json.dumps([w.to_dict() for w in workflows], indent=2))
    else:
        if not workflows:
            print("No schedules.")
        else:
            for w in workflows:
                status = "ENABLED" if w.enabled else "DISABLED"
                print(
                    f"  {w.id}  {w.name:30s}  {status:10s}  "
                    f"{w.schedule_type.value}:{w.schedule_value}"
                )
                if w.next_run_at:
                    print(f"    Next: {w.next_run_at}")
                if w.last_run_at:
                    print(f"    Last: {w.last_run_at} ({w.last_run_status})")
    return 0


def cmd_schedule_create(args: argparse.Namespace) -> int:
    """Create a new scheduled workflow."""
    from umh.scheduler.models import ScheduleType, ScheduledWorkflow
    from umh.scheduler.store import get_schedule_store
    from umh.events.stream import publish as _publish_event

    # Determine schedule type and value
    if args.interval:
        stype = ScheduleType.INTERVAL
        svalue = args.interval
    elif args.daily:
        stype = ScheduleType.DAILY
        svalue = args.daily
    elif args.weekly:
        stype = ScheduleType.WEEKLY
        svalue = args.weekly
    else:
        stype = ScheduleType.INTERVAL
        svalue = "60"

    workflow = ScheduledWorkflow(
        name=args.name,
        objective=args.objective,
        schedule_type=stype,
        schedule_value=svalue,
        created_by="cli",
    )

    store = get_schedule_store()
    store.create(workflow)

    _publish_event(
        "schedule.created",
        payload={
            "schedule_id": workflow.id,
            "name": workflow.name,
            "schedule_type": stype.value,
        },
        actor_id="cli",
    )

    if args.json:
        print(json.dumps(workflow.to_dict(), indent=2))
    else:
        print(f"Created: {workflow.id}")
        print(f"  Name: {workflow.name}")
        print(f"  Schedule: {stype.value}:{svalue}")
        print(f"  Status: DISABLED (use schedule-enable to activate)")
    return 0


def cmd_schedule_enable(args: argparse.Namespace) -> int:
    """Enable a scheduled workflow."""
    from umh.scheduler.store import get_schedule_store

    store = get_schedule_store()
    workflow = store.enable(args.schedule_id)
    if workflow is None:
        if args.json:
            print(json.dumps({"error": f"Schedule not found: {args.schedule_id}"}))
        else:
            print(f"Schedule not found: {args.schedule_id}")
        return 1
    if args.json:
        print(json.dumps(workflow.to_dict(), indent=2))
    else:
        print(f"Enabled: {workflow.id}")
        print(f"  Next run: {workflow.next_run_at}")
    return 0


def cmd_schedule_disable(args: argparse.Namespace) -> int:
    """Disable a scheduled workflow."""
    from umh.scheduler.store import get_schedule_store

    store = get_schedule_store()
    workflow = store.disable(args.schedule_id)
    if workflow is None:
        if args.json:
            print(json.dumps({"error": f"Schedule not found: {args.schedule_id}"}))
        else:
            print(f"Schedule not found: {args.schedule_id}")
        return 1
    if args.json:
        print(json.dumps(workflow.to_dict(), indent=2))
    else:
        print(f"Disabled: {workflow.id}")
    return 0


def cmd_schedule_run_now(args: argparse.Namespace) -> int:
    """Manually trigger a scheduled workflow immediately."""
    from umh.scheduler.runner import get_scheduler_runner

    runner = get_scheduler_runner()
    try:
        result = runner.run_now(args.schedule_id)
    except ValueError as exc:
        if args.json:
            print(json.dumps({"error": str(exc)}))
        else:
            print(f"Error: {exc}")
        return 1

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Triggered: {args.schedule_id}")
        print(f"  Plan: {result.get('plan_id', '-')}")
        print(f"  Task: {result.get('task_id', '-')}")
        print(f"  Status: {result.get('status', '-')}")
    return 0


def cmd_schedule_delete(args: argparse.Namespace) -> int:
    """Delete a scheduled workflow."""
    from umh.scheduler.store import get_schedule_store

    store = get_schedule_store()
    if not store.delete(args.schedule_id):
        if args.json:
            print(json.dumps({"error": f"Schedule not found: {args.schedule_id}"}))
        else:
            print(f"Schedule not found: {args.schedule_id}")
        return 1
    if args.json:
        print(json.dumps({"deleted": args.schedule_id}))
    else:
        print(f"Deleted: {args.schedule_id}")
    return 0


# ── Attention Queue Commands ──────────────────────────────────────


def cmd_queue(args: argparse.Namespace) -> int:
    """Show ordered execution queue."""
    from umh.attention.queue import get_attention_queue

    queue = get_attention_queue()
    entries = queue.list_ordered()

    if hasattr(args, "json") and args.json:
        print(
            json.dumps(
                {"queue": [e.to_dict() for e in entries], "size": queue.size()},
                indent=2,
            )
        )
        return 0

    if not entries:
        print("Execution queue is empty")
        return 0

    print(f"Execution Queue ({queue.size()} items):")
    print(f"{'#':<4} {'Task':<20} {'Score':<8} {'State':<10} {'Goal':<16} {'Age':<8}")
    print("-" * 66)
    for i, entry in enumerate(entries, 1):
        age_str = f"{entry.age_seconds:.0f}s"
        print(
            f"{i:<4} {entry.task_id[:18]:<20} {entry.priority_score:<8.3f} "
            f"{entry.state.value:<10} {entry.goal_id[:14]:<16} {age_str:<8}"
        )
    return 0


def cmd_controls(args: argparse.Namespace) -> int:
    """Show current system controls."""
    import json as _json

    from umh.attention.controls import get_system_controls

    controls = get_system_controls()

    if hasattr(args, "json") and args.json:
        print(_json.dumps(controls.to_dict(), indent=2))
        return 0

    print("System Controls:")
    print(f"  Execution Mode:       {controls.execution_mode.value}")
    print(f"  Max Concurrent Tasks: {controls.max_concurrent_tasks}")
    print(f"  Retry Policy:         {controls.retry_policy.value}")
    print(f"  Cost Sensitivity:     {controls.cost_sensitivity:.2f}")
    print(f"  Failure Tolerance:    {controls.failure_tolerance:.2f}")
    print(f"  Exploration Factor:   {controls.exploration_factor:.2f}")
    print(f"  Last Updated:         {controls.updated_at}")
    return 0


def cmd_controls_set(args: argparse.Namespace) -> int:
    """Update a system control."""
    import json as _json

    from umh.attention.controls import update_system_control

    try:
        controls = update_system_control(args.key, args.value)
        if hasattr(args, "json") and args.json:
            print(_json.dumps(controls.to_dict(), indent=2))
        else:
            print(f"Updated {args.key} = {args.value}")
            print(f"Execution Mode: {controls.execution_mode.value}")
        return 0
    except (ValueError, KeyError) as e:
        print(f"Error: {e}")
        return 1


def cmd_task_priority(args: argparse.Namespace) -> int:
    """Show priority scoring breakdown for a task."""
    import json as _json

    from umh.attention.queue import get_attention_queue
    from umh.attention.scorer import score_task
    from umh.orchestrator.task import get_task

    task = get_task(args.task_id)
    if task is None:
        print(f"Task {args.task_id} not found")
        return 1

    # Check queue first
    queue = get_attention_queue()
    for entry in queue.list_ordered():
        if entry.task_id == args.task_id:
            if hasattr(args, "json") and args.json:
                print(_json.dumps(entry.to_dict(), indent=2))
            else:
                _print_priority_breakdown(entry)
            return 0

    # Compute on the fly
    from umh.goals.models import GoalPriority

    goal_id = task.context.get("goal_id", "")
    goal = None
    goal_priority = GoalPriority.MEDIUM
    if goal_id:
        from umh.goals.store import get_goal_store

        goal = get_goal_store().get(goal_id)
        if goal is not None:
            goal_priority = goal.priority

    from datetime import datetime, timezone

    try:
        created = datetime.fromisoformat(task.created_at)
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        age = max(0.0, (datetime.now(timezone.utc) - created).total_seconds())
    except (ValueError, TypeError):
        age = 0.0
    entry = score_task(task, goal_priority, age)
    if hasattr(args, "json") and args.json:
        print(_json.dumps(entry.to_dict(), indent=2))
    else:
        _print_priority_breakdown(entry)
    return 0


def _print_priority_breakdown(entry) -> None:
    """Pretty-print a priority breakdown."""
    b = entry.breakdown
    print(f"Task:              {entry.task_id}")
    print(f"Goal:              {entry.goal_id or '(none)'}")
    print(f"Priority Score:    {entry.priority_score:.3f}")
    print(f"State:             {entry.state.value}")
    print(f"Age:               {entry.age_seconds:.0f}s")
    print(f"Starvation Boost:  {entry.starvation_boost:.3f}")
    print(f"\nBreakdown:")
    print(f"  Importance (30%):       {b.importance:.3f}")
    print(f"  Recency (20%):          {b.recency:.3f}")
    print(f"  Failure Pressure (20%): {b.failure_pressure:.3f}")
    print(f"  Dependency Value (20%): {b.dependency_value:.3f}")
    print(f"  Cost Penalty (-10%):    {b.cost_penalty:.3f}")


# ── Goal Commands ──────────────────────────────────────────────────


def cmd_goals(args: argparse.Namespace) -> int:
    """List all goals."""
    from umh.goals.store import get_goal_store

    store = get_goal_store()
    goals = store.list_all()

    if args.json:
        print(json.dumps([g.to_dict() for g in goals], indent=2))
    else:
        if not goals:
            print("No goals.")
        else:
            for g in goals:
                progress = ""
                if g.tasks_created > 0:
                    progress = f"  ({g.tasks_completed}/{g.tasks_created} tasks)"
                print(
                    f"  {g.id}  {g.name:30s}  {g.status.value:10s}  "
                    f"priority={g.priority.value}{progress}"
                )
    return 0


def cmd_goal_create(args: argparse.Namespace) -> int:
    """Create a new goal."""
    from umh.goals.models import Goal, GoalPriority
    from umh.goals.store import get_goal_store
    from umh.events.stream import publish as _publish_event

    try:
        priority = GoalPriority(args.priority)
    except ValueError:
        msg = f"Invalid priority: {args.priority}"
        if args.json:
            print(json.dumps({"error": msg}))
        else:
            print(msg)
        return 1

    goal = Goal(
        name=args.name,
        objective=args.objective,
        priority=priority,
        created_by="cli",
    )

    store = get_goal_store()
    store.create(goal)

    _publish_event(
        "goal.created",
        payload={
            "goal_id": goal.id,
            "name": goal.name,
            "priority": priority.value,
        },
        actor_id="cli",
    )

    if args.json:
        print(json.dumps(goal.to_dict(), indent=2))
    else:
        print(f"Created: {goal.id}")
    return 0


def cmd_goal_pause(args: argparse.Namespace) -> int:
    """Pause a goal."""
    from umh.goals.store import get_goal_store

    store = get_goal_store()
    goal = store.pause(args.goal_id)
    if goal is None:
        if args.json:
            print(json.dumps({"error": f"Goal not found: {args.goal_id}"}))
        else:
            print(f"Goal not found: {args.goal_id}")
        return 1
    if args.json:
        print(json.dumps(goal.to_dict(), indent=2))
    else:
        print(f"Paused: {goal.id}")
    return 0


def cmd_goal_resume(args: argparse.Namespace) -> int:
    """Resume a paused goal."""
    from umh.goals.store import get_goal_store

    store = get_goal_store()
    goal = store.resume(args.goal_id)
    if goal is None:
        if args.json:
            print(json.dumps({"error": f"Goal not found: {args.goal_id}"}))
        else:
            print(f"Goal not found: {args.goal_id}")
        return 1
    if args.json:
        print(json.dumps(goal.to_dict(), indent=2))
    else:
        print(f"Resumed: {goal.id}")
    return 0


def cmd_goal_evaluate(args: argparse.Namespace) -> int:
    """Manually trigger goal evaluation."""
    from umh.goals.goal_engine import get_goal_engine

    engine = get_goal_engine()
    result = engine.evaluate_now(args.goal_id)
    if result is None:
        if args.json:
            print(json.dumps({"error": f"Goal not found: {args.goal_id}"}))
        else:
            print(f"Goal not found: {args.goal_id}")
        return 1

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Evaluated: {args.goal_id}")
        for k, v in result.items():
            print(f"  {k}: {v}")
    return 0


def cmd_goal_delete(args: argparse.Namespace) -> int:
    """Delete a goal."""
    from umh.goals.store import get_goal_store

    store = get_goal_store()
    if not store.delete(args.goal_id):
        if args.json:
            print(json.dumps({"error": f"Goal not found: {args.goal_id}"}))
        else:
            print(f"Goal not found: {args.goal_id}")
        return 1
    if args.json:
        print(json.dumps({"deleted": args.goal_id}))
    else:
        print(f"Deleted: {args.goal_id}")
    return 0


def cmd_goal_strategy(args: argparse.Namespace) -> int:
    """Show or recompute strategy for a goal."""
    from umh.goals.store import get_goal_store
    from umh.strategy.decomposer import (
        cache_strategy,
        decompose_goal,
        get_cached_strategy,
        invalidate_strategy,
    )

    store = get_goal_store()
    goal = store.get(args.goal_id)
    if goal is None:
        if args.json:
            print(json.dumps({"error": f"Goal not found: {args.goal_id}"}))
        else:
            print(f"Goal not found: {args.goal_id}")
        return 1

    if getattr(args, "recompute", False):
        invalidate_strategy(args.goal_id)

    strategy = get_cached_strategy(args.goal_id)
    if strategy is None:
        strategy = decompose_goal(goal)
        cache_strategy(strategy)

    if args.json:
        print(json.dumps(strategy.to_dict(), indent=2))
    else:
        print(f"Strategy: {strategy.id}")
        print(f"Template: {strategy.template_used or 'none'}")
        print(f"Approach: {strategy.approach_type.value}")
        print(f"Confidence: {strategy.confidence:.0%}")
        print(f"Progress: {strategy.progress():.0%}")
        print(f"Steps ({len(strategy.steps)}):")
        for i, step in enumerate(strategy.steps, 1):
            deps = f" [depends: {', '.join(step.dependencies)}]" if step.dependencies else ""
            tasks = f" [tasks: {', '.join(step.task_ids)}]" if step.task_ids else ""
            print(f"  {i}. [{step.status.value}] {step.description}")
            print(
                f"     type={step.type.value} complexity={step.estimated_complexity.value}{deps}{tasks}"
            )
    return 0


def cmd_goal_refine(args: argparse.Namespace) -> int:
    """Show refinement proposal for a goal."""
    from umh.strategy.refiner import get_proposal, refine_strategy, store_proposal

    proposal = get_proposal(args.goal_id)
    if proposal is None:
        proposal = refine_strategy(args.goal_id)
        if proposal is not None:
            store_proposal(proposal)

    if proposal is None:
        if args.json:
            print(json.dumps({"message": "No refinement needed or insufficient data"}))
        else:
            print("No refinement needed or insufficient evaluation data.")
        return 0

    if args.json:
        print(json.dumps(proposal.to_dict(), indent=2))
    else:
        print(f"Refinement Proposal: {proposal.id}")
        print(f"Confidence: {proposal.confidence:.0%}")
        print(f"Expected Improvement: {proposal.expected_improvement:.0%}")
        print(f"Recommended: {'YES' if proposal.recommended else 'no'}")
        if proposal.current_score:
            s = proposal.current_score
            print(
                f"Current Score: efficiency={s.efficiency:.2f} reliability={s.reliability:.2f} complexity={s.complexity:.2f} overall={s.overall:.2f}"
            )
        print(f"Issues ({len(proposal.issues_detected)}):")
        for i, issue in enumerate(proposal.issues_detected, 1):
            print(f"  {i}. [{issue.severity}] {issue.issue_type}: {issue.description}")
        print(f"Suggested Changes ({len(proposal.suggested_changes)}):")
        for i, change in enumerate(proposal.suggested_changes, 1):
            print(f"  {i}. {change}")
        if proposal.new_strategy:
            print(f"New Strategy: {len(proposal.new_strategy.steps)} steps")
    return 0


def cmd_goal_apply_refinement(args: argparse.Namespace) -> int:
    """Apply a refinement proposal to a goal."""
    from umh.goals.store import get_goal_store
    from umh.strategy.decomposer import cache_strategy, invalidate_strategy
    from umh.strategy.history import record_strategy_version
    from umh.strategy.refiner import clear_proposal, get_proposal

    store = get_goal_store()
    goal = store.get(args.goal_id)
    if goal is None:
        if args.json:
            print(json.dumps({"error": f"Goal not found: {args.goal_id}"}))
        else:
            print(f"Goal not found: {args.goal_id}")
        return 1

    proposal = get_proposal(args.goal_id)
    if proposal is None:
        if args.json:
            print(json.dumps({"error": "No refinement proposal available"}))
        else:
            print("No refinement proposal available.")
        return 1

    if proposal.new_strategy is None:
        if args.json:
            print(json.dumps({"error": "Proposal has no new strategy"}))
        else:
            print("Proposal has no new strategy.")
        return 1

    new_strategy = proposal.new_strategy
    invalidate_strategy(args.goal_id)
    cache_strategy(new_strategy)
    record_strategy_version(args.goal_id, new_strategy)
    clear_proposal(args.goal_id)

    from umh.events.stream import publish as _publish_event

    _publish_event(
        "strategy.refinement_applied",
        payload={
            "goal_id": args.goal_id,
            "proposal_id": proposal.id,
            "new_strategy_id": new_strategy.id,
        },
        actor_id="cli",
    )

    if args.json:
        print(json.dumps({"applied": True, "strategy": new_strategy.to_dict()}, indent=2))
    else:
        print(f"Applied refinement: {proposal.id}")
        print(f"New strategy: {new_strategy.id} ({len(new_strategy.steps)} steps)")
    return 0


# ── Brain Commands ────────────────────────────────────────────────


def cmd_brains(args: argparse.Namespace) -> int:
    """List all registered brains."""
    from umh.brains.registry import list_all

    profiles = list_all()
    if getattr(args, "json", False):
        print(json.dumps({"brains": [p.to_dict() for p in profiles]}, indent=2))
    else:
        if not profiles:
            print("No brains registered.")
        else:
            for p in profiles:
                parent = f" (parent: {p.parent_brain_id})" if p.parent_brain_id else ""
                print(
                    f"  {p.brain_id:20s}  {p.name:15s}  {p.brain_type:10s}  {p.authority.value}{parent}"
                )
    return 0


def cmd_brain_show(args: argparse.Namespace) -> int:
    """Show a brain profile (with inheritance resolved)."""
    from umh.brains.registry import get, resolve_with_inheritance

    profile = get(args.brain_id)
    if profile is None:
        print(f"Brain '{args.brain_id}' not found.", file=sys.stderr)
        return 1

    resolved = resolve_with_inheritance(args.brain_id)
    if getattr(args, "json", False):
        print(
            json.dumps(
                {
                    "profile": profile.to_dict(),
                    "resolved": resolved.to_dict() if resolved else None,
                },
                indent=2,
            )
        )
    else:
        print(f"Brain: {profile.brain_id}")
        print(f"  Name:       {profile.name}")
        print(f"  Type:       {profile.brain_type}")
        print(f"  Authority:  {profile.authority.value}")
        print(f"  Parent:     {profile.parent_brain_id or '(none)'}")
        print(f"  Primitives: {', '.join(profile.active_primitives) or '(none)'}")
        if resolved and resolved.amplified_concepts:
            print(f"  Amplified:  {', '.join(sorted(resolved.amplified_concepts))}")
        if resolved and resolved.silenced_concepts:
            print(f"  Silenced:   {', '.join(sorted(resolved.silenced_concepts))}")
    return 0


def cmd_brain_expression(args: argparse.Namespace) -> int:
    """Show expression state for a brain."""
    from umh.brains.registry import get, get_expression

    if get(args.brain_id) is None:
        print(f"Brain '{args.brain_id}' not found.", file=sys.stderr)
        return 1

    state = get_expression(args.brain_id)
    if state is None:
        print("No expression state.")
        return 0

    if getattr(args, "json", False):
        print(json.dumps(state.to_dict(), indent=2))
    else:
        print(f"Expression state for {args.brain_id} (v{state.checkpoint_version}):")
        if state.amplified_concepts:
            print(f"  Amplified:    {state.amplified_concepts}")
        if state.silenced_concepts:
            print(f"  Silenced:     {state.silenced_concepts}")
        if state.preferred_patterns:
            print(f"  Patterns:     {state.preferred_patterns}")
        if state.concept_weights:
            print(f"  Weights:      {state.concept_weights}")
        corrections = len(state.learned_corrections)
        if corrections:
            print(f"  Corrections:  {corrections}")
        print(f"  Updated:      {state.updated_at}")
    return 0


def cmd_brain_children(args: argparse.Namespace) -> int:
    """List children of a brain."""
    from umh.brains.registry import children

    kids = children(args.brain_id)
    if getattr(args, "json", False):
        print(json.dumps({"children": [p.to_dict() for p in kids]}, indent=2))
    else:
        if not kids:
            print(f"No children for '{args.brain_id}'.")
        else:
            for p in kids:
                print(f"  {p.brain_id:20s}  {p.name:15s}  {p.brain_type:10s}  {p.authority.value}")
    return 0


def cmd_brain_signals(args: argparse.Namespace) -> int:
    """List brain signals."""
    from umh.brains.signals import list_all_signals, list_signals

    brain_id = getattr(args, "brain_id", None)
    signal_type = getattr(args, "type", None)
    limit = getattr(args, "limit", 50)

    if brain_id:
        signals = list_signals(brain_id, signal_type=signal_type, limit=limit)
    else:
        signals = list_all_signals(signal_type=signal_type, limit=limit)

    if getattr(args, "json", False):
        print(json.dumps({"signals": [s.to_dict() for s in signals]}, indent=2))
    else:
        if not signals:
            print("No signals.")
        else:
            for s in signals:
                target = f" → {s.target_brain_id}" if s.target_brain_id else ""
                print(f"  [{s.timestamp}] {s.brain_id}{target}  {s.signal_type}  {s.signal_id}")
    return 0


# ── Feedback (Phase 78) ────────────────────────────────────────────


def cmd_feedback_outcomes(args: argparse.Namespace) -> int:
    from umh.feedback.store import get_feedback_store

    store = get_feedback_store()
    outcomes = store.list_outcomes(limit=getattr(args, "limit", 20))
    if getattr(args, "json", False):
        print(json.dumps([o.to_dict() for o in outcomes], indent=2))
    else:
        for o in outcomes:
            print(
                f"  {o.outcome_id}  {o.status.value:<20s}  trace={o.trace_id}  score={o.success_score:.2f}"
            )
    return 0


def cmd_feedback_records(args: argparse.Namespace) -> int:
    from umh.feedback.store import get_feedback_store

    store = get_feedback_store()
    records = store.list_feedback(limit=getattr(args, "limit", 20))
    if getattr(args, "json", False):
        print(json.dumps([r.to_dict() for r in records], indent=2))
    else:
        for r in records:
            print(
                f"  {r.feedback_id}  {r.signal_type.value:<20s}  source={r.source.value}  score={r.score:.2f}"
            )
    return 0


def cmd_feedback_candidates(args: argparse.Namespace) -> int:
    from umh.feedback.store import get_feedback_store

    store = get_feedback_store()
    candidates = store.list_memory_candidates(limit=getattr(args, "limit", 20))
    if getattr(args, "json", False):
        print(json.dumps([c.to_dict() for c in candidates], indent=2))
    else:
        for c in candidates:
            print(
                f"  {c.candidate_id}  {c.memory_type.value:<20s}  status={c.promotion_status.value}  conf={c.confidence:.2f}"
            )
    return 0


def cmd_feedback_add(args: argparse.Namespace) -> int:
    from umh.feedback.outcome import clamp_score
    from umh.feedback.records import (
        FeedbackRecord,
        FeedbackSource,
        create_feedback_id,
        normalize_feedback_signal,
    )
    from umh.feedback.store import get_feedback_store
    from umh.core.clock import iso_now

    signal_type = normalize_feedback_signal(getattr(args, "signal", "user_positive"))
    feedback = FeedbackRecord(
        feedback_id=create_feedback_id(args.trace_id, signal_type.value, "user"),
        trace_id=args.trace_id,
        outcome_id="",
        user_id="cli_user",
        signal_type=signal_type,
        score=clamp_score(float(getattr(args, "score", 0.5))),
        confidence=0.9,
        source=FeedbackSource.USER,
        notes=getattr(args, "notes", ""),
        timestamp=iso_now(),
    )
    store = get_feedback_store()
    store.append_feedback(feedback)
    print(f"Feedback recorded: {feedback.feedback_id}")
    return 0


# ── Phase 79: Observability Commands (read-only) ─────────────────


def _print(args: argparse.Namespace, data: dict, label: str = "") -> None:
    if getattr(args, "json", False):
        print(json.dumps(data, indent=2, default=str))
    else:
        if label:
            print(f"── {label} ──")
        print(json.dumps(data, indent=2, default=str))


def cmd_observe_status(args: argparse.Namespace) -> int:
    from umh.control.trace_store import get_trace_store
    from umh.feedback.store import get_feedback_store
    from umh.observability.system_status import build_system_status

    status = build_system_status(
        trace_store=get_trace_store(),
        feedback_store=get_feedback_store(),
    )
    _print(args, status.to_dict(), label="System Status")
    return 0


def cmd_observe_dashboard(args: argparse.Namespace) -> int:
    from umh.control.trace_store import get_trace_store
    from umh.feedback.store import get_feedback_store
    from umh.observability.operator_views import build_operator_dashboard_snapshot

    limit = getattr(args, "limit", 25)
    snapshot = build_operator_dashboard_snapshot(
        user_id="cli_user",
        trace_store=get_trace_store(),
        feedback_store=get_feedback_store(),
        limit=min(limit, 100),
    )
    _print(args, snapshot.to_dict(), label="Dashboard")
    return 0


def cmd_observe_timeline(args: argparse.Namespace) -> int:
    from umh.control.trace_store import get_trace_store
    from umh.feedback.store import get_feedback_store
    from umh.observability.timeline import build_timeline

    limit = getattr(args, "limit", 50)
    ts = get_trace_store()
    fs = get_feedback_store()
    traces = ts.list_traces(limit=min(limit, 100))
    outcomes = fs.list_outcomes(limit=min(limit, 100))
    feedback = fs.list_feedback(limit=min(limit, 100))
    tl = build_timeline(traces=traces, outcomes=outcomes, feedback=feedback, limit=limit)
    _print(args, tl.to_dict(), label="Timeline")
    return 0


def cmd_observe_traces(args: argparse.Namespace) -> int:
    from umh.control.trace_store import get_trace_store
    from umh.observability.trace_query import TraceQuery, query_traces

    limit = getattr(args, "limit", 25)
    q = TraceQuery(limit=min(limit, 100))
    result = query_traces(get_trace_store(), q)
    _print(args, result.to_dict(), label="Traces")
    return 0


def cmd_observe_trace(args: argparse.Namespace) -> int:
    from umh.control.trace_store import get_trace_store
    from umh.observability.trace_query import get_trace_view

    view = get_trace_view(get_trace_store(), args.trace_id)
    if view is None:
        print("Trace not found")
        return 1
    _print(args, view.to_dict(), label="Trace")
    return 0


def cmd_observe_explain(args: argparse.Namespace) -> int:
    from umh.control.trace_store import get_trace_store
    from umh.observability.decision_explainer import explain_trace

    ts = get_trace_store()
    trace = ts.get_trace(args.trace_id)
    if trace is None:
        print("Trace not found")
        return 1
    explanation = explain_trace(trace)
    _print(args, explanation.to_dict(), label="Explanation")
    return 0


def cmd_observe_failures(args: argparse.Namespace) -> int:
    from umh.feedback.store import get_feedback_store
    from umh.observability.failure_search import FailureSearchQuery, search_failures

    limit = getattr(args, "limit", 25)
    fs = get_feedback_store()
    outcomes = fs.list_outcomes(limit=min(limit, 100))
    q = FailureSearchQuery(limit=min(limit, 100))
    result = search_failures(outcomes=outcomes, query=q)
    _print(args, result.to_dict(), label="Failures")
    return 0


def cmd_observe_summary(args: argparse.Namespace) -> int:
    from umh.control.trace_store import get_trace_store
    from umh.feedback.store import get_feedback_store
    from umh.observability.execution_summary import summarize_executions

    limit = getattr(args, "limit", 100)
    traces = get_trace_store().list_traces(limit=min(limit, 100))
    outcomes = get_feedback_store().list_outcomes(limit=min(limit, 100))
    summary = summarize_executions(traces=traces, outcomes=outcomes, limit=limit)
    _print(args, summary.to_dict(), label="Summary")
    return 0


# ── Phase 80: Registry Commands ───────────────────────────────────


def cmd_registry_catalog(args: argparse.Namespace) -> int:
    from umh.registry.catalog import build_default_registry_catalog

    catalog = build_default_registry_catalog()
    _print(args, catalog.to_dict(), label="Registry Catalog")
    return 0


def cmd_registry_overview(args: argparse.Namespace) -> int:
    from umh.registry.catalog import build_default_registry_catalog
    from umh.registry.views import build_catalog_view

    catalog = build_default_registry_catalog()
    _print(args, build_catalog_view(catalog).to_dict(), label="Registry Overview")
    return 0


def cmd_registry_health(args: argparse.Namespace) -> int:
    from umh.registry.catalog import build_default_registry_catalog
    from umh.registry.views import build_registry_health_view

    catalog = build_default_registry_catalog()
    _print(args, build_registry_health_view(catalog).to_dict(), label="Registry Health")
    return 0


def cmd_registry_query(args: argparse.Namespace) -> int:
    from umh.registry.catalog import build_default_registry_catalog
    from umh.registry.contracts import RegistryQuery
    from umh.registry.query import query_registry

    catalog = build_default_registry_catalog()
    q = RegistryQuery(
        registry_type=getattr(args, "type", "") or "",
        name=getattr(args, "name", "") or "",
        capability=getattr(args, "capability", "") or "",
        environment=getattr(args, "environment", "") or "",
        tag=getattr(args, "tag", "") or "",
        status=getattr(args, "status", "") or "",
        risk_level=getattr(args, "risk_level", "") or "",
        limit=getattr(args, "limit", 50),
    )
    result = query_registry(catalog, q)
    _print(args, result.to_dict(), label="Registry Query")
    return 0


def cmd_registry_item(args: argparse.Namespace) -> int:
    from umh.registry.catalog import build_default_registry_catalog
    from umh.registry.views import registry_item_to_view

    catalog = build_default_registry_catalog()
    item_id = getattr(args, "item_id", "")
    item = catalog.by_id(item_id)
    if item is None:
        print(f"Not found: {item_id}")
        return 1
    _print(args, registry_item_to_view(item).to_dict(), label="Registry Item")
    return 0


def cmd_registry_capabilities(args: argparse.Namespace) -> int:
    from umh.registry.catalog import build_default_registry_catalog
    from umh.registry.query import find_capabilities
    from umh.registry.views import registry_item_to_view

    catalog = build_default_registry_catalog()
    items = find_capabilities(
        catalog,
        environment=getattr(args, "environment", "") or "",
        risk_level=getattr(args, "risk_level", "") or "",
        limit=getattr(args, "limit", 50),
    )
    _print(args, [registry_item_to_view(i).to_dict() for i in items], label="Capabilities")
    return 0


def cmd_registry_environments(args: argparse.Namespace) -> int:
    from umh.registry.catalog import build_default_registry_catalog
    from umh.registry.query import find_environments
    from umh.registry.views import registry_item_to_view

    catalog = build_default_registry_catalog()
    items = find_environments(
        catalog,
        capability=getattr(args, "capability", "") or "",
        limit=getattr(args, "limit", 50),
    )
    _print(args, [registry_item_to_view(i).to_dict() for i in items], label="Environments")
    return 0


def cmd_registry_modes(args: argparse.Namespace) -> int:
    from umh.registry.catalog import build_default_registry_catalog
    from umh.registry.query import find_workstation_modes
    from umh.registry.views import registry_item_to_view

    catalog = build_default_registry_catalog()
    items = find_workstation_modes(catalog, limit=getattr(args, "limit", 50))
    _print(args, [registry_item_to_view(i).to_dict() for i in items], label="Modes")
    return 0


def cmd_registry_policies(args: argparse.Namespace) -> int:
    from umh.registry.catalog import build_default_registry_catalog
    from umh.registry.query import find_policies
    from umh.registry.views import registry_item_to_view

    catalog = build_default_registry_catalog()
    items = find_policies(catalog, limit=getattr(args, "limit", 50))
    _print(args, [registry_item_to_view(i).to_dict() for i in items], label="Policies")
    return 0


# ── Phase 81: Ontology Commands ───────────────────────────────────


def cmd_ontology_status(args: argparse.Namespace) -> int:
    from umh.ontology.correspondence import get_correspondence_maps
    from umh.ontology.domain_projection import get_domain_projections
    from umh.ontology.laws import get_laws
    from umh.ontology.primitives import get_primitives
    from umh.ontology.validation import validate_ontology_kernel
    from umh.ontology.views import build_ontology_kernel_view

    prims = get_primitives()
    laws = get_laws()
    projs = get_domain_projections()
    corrs = get_correspondence_maps()
    vr = validate_ontology_kernel(prims, laws, projs)
    _print(
        args,
        build_ontology_kernel_view(prims, laws, projs, corrs, vr).to_dict(),
        label="Ontology Kernel",
    )
    return 0


def cmd_ontology_primitives(args: argparse.Namespace) -> int:
    from umh.ontology.primitives import get_primitives
    from umh.ontology.views import primitive_to_view

    _print(
        args,
        [primitive_to_view(p).to_dict() for p in get_primitives()],
        label="Universal Primitives",
    )
    return 0


def cmd_ontology_laws(args: argparse.Namespace) -> int:
    from umh.ontology.laws import get_laws
    from umh.ontology.views import law_to_view

    _print(args, [law_to_view(l).to_dict() for l in get_laws()], label="Universal Laws")
    return 0


def cmd_ontology_projections(args: argparse.Namespace) -> int:
    from umh.ontology.domain_projection import get_domain_projections
    from umh.ontology.views import domain_projection_to_view

    _print(
        args,
        [domain_projection_to_view(ps).to_dict() for ps in get_domain_projections()],
        label="Domain Projections",
    )
    return 0


def cmd_ontology_correspondence(args: argparse.Namespace) -> int:
    from umh.ontology.correspondence import get_correspondence_maps
    from umh.ontology.views import correspondence_to_view

    _print(
        args,
        [correspondence_to_view(cm).to_dict() for cm in get_correspondence_maps()],
        label="Correspondence Maps",
    )
    return 0


def cmd_ontology_validate(args: argparse.Namespace) -> int:
    from umh.ontology.domain_projection import get_domain_projections
    from umh.ontology.laws import get_laws
    from umh.ontology.primitives import get_primitives
    from umh.ontology.validation import validate_ontology_kernel

    prims = get_primitives()
    laws = get_laws()
    projs = get_domain_projections()
    result = validate_ontology_kernel(prims, laws, projs)
    _print(args, result.to_dict(), label="Ontology Validation")
    return 0


# ── Unity / Polarity Synthesis (Phase 84A) ────────────────────────


def cmd_ontology_unity(args: argparse.Namespace) -> int:
    from umh.ontology.laws import get_law_by_id
    from umh.ontology.views import law_to_view

    law = get_law_by_id("law_unity_oneness")
    if law is None:
        _print(args, {"error": "Unity / Oneness law not found"}, label="Unity Law")
        return 1
    _print(args, law_to_view(law).to_dict(), label="Unity / Oneness")
    return 0


def cmd_ontology_synthesize(args: argparse.Namespace) -> int:
    from umh.ontology.polarity_synthesis import (
        PolarityPoleType,
        create_polarity_pair,
        create_polarity_pole,
        synthesize_polarity,
    )
    from umh.ontology.views import polarity_synthesis_to_view

    pa = create_polarity_pole(
        "speed",
        pole_type=PolarityPoleType.FORCE,
        truth_claim="Fast iteration matters for learning",
        value_preserved="responsiveness",
        risk_if_dominant="Reckless errors and technical debt",
    )
    pb = create_polarity_pole(
        "safety",
        pole_type=PolarityPoleType.FORCE,
        truth_claim="Safety prevents costly mistakes",
        value_preserved="reliability",
        risk_if_dominant="Paralysis and missed opportunities",
    )
    pair = create_polarity_pair(
        pa,
        pb,
        shared_context="software development",
        contradiction_layer="resource allocation between speed and safety",
    )
    result = synthesize_polarity(pair)
    _print(args, polarity_synthesis_to_view(result).to_dict(), label="Polarity Synthesis Demo")
    return 0


# ── Storage + Memory Discipline (Phase 82) ────────────────────────


def cmd_storage_status(args: argparse.Namespace) -> int:
    from umh.storage.gateway import StorageGateway
    from umh.storage.views import build_storage_health_view

    gw = StorageGateway()
    descs = gw.list_descriptors(limit=500)
    view = build_storage_health_view(descs, backend_names=sorted(gw.backends.keys()))
    _print(args, view.to_dict(), label="Storage Health")
    return 0


def cmd_storage_descriptors(args: argparse.Namespace) -> int:
    from umh.storage.gateway import StorageGateway
    from umh.storage.views import build_descriptor_view

    gw = StorageGateway()
    limit = getattr(args, "limit", 50)
    descs = gw.list_descriptors(limit=limit)
    _print(args, [build_descriptor_view(d).to_dict() for d in descs], label="Storage Descriptors")
    return 0


def cmd_storage_audit(args: argparse.Namespace) -> int:
    from umh.storage.audit import audit_storage_boundaries
    from umh.storage.views import build_storage_audit_view

    include_tests = getattr(args, "include_tests", False)
    report = audit_storage_boundaries(include_tests=include_tests)
    view = build_storage_audit_view(report)
    _print(args, view.to_dict(), label="Storage Audit")
    return 0


def cmd_storage_policy(args: argparse.Namespace) -> int:
    from umh.storage.policy import build_default_storage_policy

    _print(args, build_default_storage_policy().to_dict(), label="Storage Policy")
    return 0


def cmd_memory_discipline_status(args: argparse.Namespace) -> int:
    from umh.memory.views import build_memory_discipline_health_view

    view = build_memory_discipline_health_view()
    _print(args, view.to_dict(), label="Memory Discipline Health")
    return 0


def cmd_memory_discipline_policy(args: argparse.Namespace) -> int:
    from umh.memory.discipline import build_default_memory_write_policy

    _print(args, build_default_memory_write_policy().to_dict(), label="Memory Write Policy")
    return 0


# ── Migration Commands (Phase 83) ──────────────────────────────────


def cmd_migration_status(args: argparse.Namespace) -> int:
    from umh.migration.deprecation_registry import build_default_deprecation_registry
    from umh.migration.views import build_migration_health_view

    registry = build_default_deprecation_registry()
    view = build_migration_health_view(registry)
    _print(args, view.to_dict(), label="Migration Health")
    return 0


def cmd_migration_inventory(args: argparse.Namespace) -> int:
    from umh.migration.inventory import build_legacy_inventory, summarize_inventory

    inv = build_legacy_inventory()
    summary = summarize_inventory(inv.records)
    limit = getattr(args, "limit", 100)
    data = {"summary": summary, "record_count": len(inv.records), "warnings": inv.warnings}
    if limit > 0:
        data["records_preview"] = [r.to_dict() for r in inv.records[:limit]]
    _print(args, data, label="Migration Inventory")
    return 0


def cmd_migration_deprecated(args: argparse.Namespace) -> int:
    from umh.migration.deprecation_registry import build_default_deprecation_registry
    from umh.migration.views import legacy_module_to_view

    registry = build_default_deprecation_registry()
    deprecated = registry.list_deprecated(limit=getattr(args, "limit", 100))
    _print(
        args, [legacy_module_to_view(r).to_dict() for r in deprecated], label="Deprecated Modules"
    )
    return 0


def cmd_migration_bypass_risk(args: argparse.Namespace) -> int:
    from umh.migration.deprecation_registry import build_default_deprecation_registry
    from umh.migration.views import legacy_module_to_view

    registry = build_default_deprecation_registry()
    risks = registry.list_bypass_risk(limit=getattr(args, "limit", 100))
    _print(args, [legacy_module_to_view(r).to_dict() for r in risks], label="Bypass-Risk Modules")
    return 0


def cmd_migration_mappings(args: argparse.Namespace) -> int:
    from umh.migration.compatibility import get_known_clean_equivalents

    equivs = get_known_clean_equivalents()
    limit = getattr(args, "limit", 100)
    items = [{"legacy": k, "clean": v} for k, v in list(equivs.items())[:limit]]
    _print(args, {"total": len(equivs), "mappings": items}, label="Migration Mappings")
    return 0


def cmd_migration_imports(args: argparse.Namespace) -> int:
    from umh.migration.import_boundary import (
        import_boundary_findings_to_report,
        scan_import_boundaries,
    )

    findings = scan_import_boundaries()
    limit = getattr(args, "limit", 100)
    report = import_boundary_findings_to_report(findings[:limit])
    _print(args, report, label="Import Boundary Findings")
    return 0


def cmd_migration_dashboard(args: argparse.Namespace) -> int:
    from umh.migration.deprecation_registry import build_default_deprecation_registry
    from umh.migration.import_boundary import scan_import_boundaries
    from umh.migration.views import build_migration_dashboard_view

    registry = build_default_deprecation_registry()
    findings = scan_import_boundaries()
    limit = getattr(args, "limit", 100)
    view = build_migration_dashboard_view(registry, findings, limit=limit)
    _print(args, view.to_dict(), label="Migration Dashboard")
    return 0


# ── Phase 84: Interface commands ────────────────────────────────────


def cmd_interface_status(args: argparse.Namespace) -> int:
    from umh.interface.safety import validate_interface_module_boundaries
    from umh.interface.surface_registry import build_default_surface_registry

    reg = build_default_surface_registry()
    safety = validate_interface_module_boundaries()
    result = {
        "surface_count": reg.surface_count,
        "safety": safety.to_dict(),
        "status": "ok" if safety.safe else "degraded",
    }
    _print(args, result, label="Interface Status")
    return 0


def cmd_interface_surfaces(args: argparse.Namespace) -> int:
    from umh.interface.surface_registry import build_default_surface_registry

    reg = build_default_surface_registry()
    limit = getattr(args, "limit", 100)
    surfaces = reg.list_surfaces(limit=limit)
    _print(args, [s.to_dict() for s in surfaces], label="Interface Surfaces")
    return 0


def cmd_interface_matrix(args: argparse.Namespace) -> int:
    from umh.interface.surface_registry import build_default_surface_registry

    reg = build_default_surface_registry()
    limit = getattr(args, "limit", 100)
    matrix = reg.build_capability_matrix(limit=limit)
    _print(args, [m.to_dict() for m in matrix], label="Capability Matrix")
    return 0


def cmd_interface_command_center(args: argparse.Namespace) -> int:
    from umh.interface.command_center import build_command_center_snapshot

    snapshot = build_command_center_snapshot()
    _print(args, snapshot.to_dict(), label="Command Center")
    return 0


def cmd_interface_voice_wave(args: argparse.Namespace) -> int:
    from umh.interface.voice_wave import VoiceWaveState, get_default_six_line_wave

    glyph = get_default_six_line_wave(VoiceWaveState.IDLE)
    _print(args, glyph.to_dict(), label="Voice Wave")
    return 0


def cmd_interface_notifications(args: argparse.Namespace) -> int:
    _print(
        args,
        {"notifications": [], "total": 0, "note": "Phase 84: display records only"},
        label="Notifications",
    )
    return 0


def cmd_interface_approvals(args: argparse.Namespace) -> int:
    _print(
        args,
        {"approvals": [], "total": 0, "note": "Phase 84: display records only"},
        label="Approvals",
    )
    return 0


def cmd_interface_safety(args: argparse.Namespace) -> int:
    from umh.interface.safety import validate_interface_module_boundaries

    result = validate_interface_module_boundaries()
    _print(args, result.to_dict(), label="Interface Safety")
    return 0


# ── Phase 85: Deliberation Council commands ──────────────────────


def cmd_council_status(args: argparse.Namespace) -> int:
    from umh.council.views import build_council_health_view

    view = build_council_health_view()
    _print(args, view.to_dict(), label="Council Health")
    return 0


def cmd_council_roles(args: argparse.Namespace) -> int:
    from umh.council.roles import get_default_council_roles

    roles = get_default_council_roles()
    _print(args, [r.to_dict() for r in roles], label="Council Roles")
    return 0


def cmd_council_deliberate(args: argparse.Namespace) -> int:
    from umh.council.contracts import (
        ConfidenceLevel,
        DeliberationDomain,
        EvidenceItem,
        EvidenceStrength,
        UrgencyLevel,
    )
    from umh.council.deliberation import deliberate
    from umh.council.perspective import create_perspective_report
    from umh.council.request import create_deliberation_request
    from umh.council.roles import get_default_council_roles

    question = getattr(args, "question", "Should we proceed?")

    dreq = create_deliberation_request(
        question,
        context="CLI demo deliberation",
        domain=DeliberationDomain.CROSS_DOMAIN,
        urgency=UrgencyLevel.MEDIUM,
    )

    roles = get_default_council_roles()
    perspectives = []
    for role in roles:
        perspectives.append(
            create_perspective_report(
                dreq.request_id,
                role.role_id,
                position=f"Demo: {role.name} on '{question[:40]}'",
                reasoning=f"From {role.perspective_lens}",
                recommendation=f"Consider {role.name.lower()} view",
                evidence=[
                    EvidenceItem(
                        evidence_id=f"ev_{role.role_id}",
                        claim=f"Relevant from {role.domain.value}",
                        strength=EvidenceStrength.MODERATE,
                        source=role.name,
                        domain=role.domain,
                        confidence=0.6,
                    )
                ],
                confidence=ConfidenceLevel.MEDIUM,
                score=0.6,
            )
        )

    advisory = deliberate(dreq, perspectives, roles=roles)
    _print(args, advisory.to_dict(), label="Council Advisory")
    return 0


def cmd_council_safety(args: argparse.Namespace) -> int:
    from umh.council.safety import validate_council_module_boundaries

    result = validate_council_module_boundaries()
    _print(args, result.to_dict(), label="Council Safety")
    return 0


# ── Parser ────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="umh-cli",
        description="UMH command-line interface",
    )
    sub = parser.add_subparsers(dest="command")

    # plan
    p_plan = sub.add_parser("plan", help="Create a plan from raw input")
    p_plan.add_argument("objective", help="Raw objective string")
    p_plan.add_argument("--json", action="store_true", help="JSON output")

    # run (plan + execute combined)
    p_run = sub.add_parser("run", help="Plan and execute in one shot")
    p_run.add_argument("objective", help="Raw objective string")
    p_run.add_argument("--json", action="store_true", help="JSON output")

    # execute
    p_exec = sub.add_parser("execute", help="Create and execute a plan")
    p_exec.add_argument("objective", help="Raw objective string")
    p_exec.add_argument("--json", action="store_true", help="JSON output")

    # watch
    p_watch = sub.add_parser("watch", help="Watch task until terminal state")
    p_watch.add_argument("task_id", help="Task ID to watch")
    p_watch.add_argument("--timeout", type=int, default=60, help="Timeout in seconds (default 60)")
    p_watch.add_argument("--json", action="store_true", help="JSON output")

    # task
    p_task = sub.add_parser("task", help="Get task status by ID")
    p_task.add_argument("task_id", help="Task ID")
    p_task.add_argument("--json", action="store_true", help="JSON output")

    # tasks
    p_tasks = sub.add_parser("tasks", help="List all tasks")
    p_tasks.add_argument("--json", action="store_true", help="JSON output")

    # approvals
    p_approvals = sub.add_parser("approvals", help="List pending approvals")
    p_approvals.add_argument("--json", action="store_true", help="JSON output")

    # cancel
    p_cancel = sub.add_parser("cancel", help="Cancel a PENDING or PAUSED task")
    p_cancel.add_argument("task_id", help="Task ID to cancel")
    p_cancel.add_argument("--json", action="store_true", help="JSON output")

    # retry
    p_retry = sub.add_parser("retry", help="Retry a FAILED task")
    p_retry.add_argument("task_id", help="Task ID to retry")
    p_retry.add_argument("--json", action="store_true", help="JSON output")

    # timeline
    p_timeline = sub.add_parser("timeline", help="Show event timeline for a task")
    p_timeline.add_argument("task_id", help="Task ID")
    p_timeline.add_argument("--json", action="store_true", help="JSON output")

    # review
    p_review = sub.add_parser("review", help="Show agent review for a plan")
    p_review.add_argument("plan_id", help="Plan ID to review")
    p_review.add_argument("--json", action="store_true", help="JSON output")

    # controls
    p_controls = sub.add_parser("controls", help="Show system controls")
    p_controls.add_argument("--json", action="store_true", help="JSON output")

    # controls-set
    p_cs = sub.add_parser("controls-set", help="Update a system control")
    p_cs.add_argument(
        "key",
        help="Control key (execution_mode, max_concurrent_tasks, retry_policy, "
        "cost_sensitivity, failure_tolerance, exploration_factor)",
    )
    p_cs.add_argument("value", help="New value")
    p_cs.add_argument("--json", action="store_true", help="JSON output")

    # queue
    p_queue = sub.add_parser("queue", help="Show execution queue")
    p_queue.add_argument("--json", action="store_true", help="JSON output")

    # task-priority
    p_tp = sub.add_parser("task-priority", help="Show task priority breakdown")
    p_tp.add_argument("task_id", help="Task ID")
    p_tp.add_argument("--json", action="store_true", help="JSON output")

    # tools
    p_tools = sub.add_parser("tools", help="List registered tools")
    p_tools.add_argument("--json", action="store_true", help="JSON output")

    # tool-run
    p_tool_run = sub.add_parser("tool-run", help="Execute a tool by name")
    p_tool_run.add_argument("tool_name", help="Tool name (e.g. http_get)")
    p_tool_run.add_argument("--url", default=None, help="URL for HTTP tools")
    p_tool_run.add_argument("--method", default=None, help="HTTP method (default: GET)")
    p_tool_run.add_argument("--body", default=None, help="Request body (string)")
    p_tool_run.add_argument("--json", action="store_true", help="JSON output")

    # memory
    p_memory = sub.add_parser("memory", help="List memories")
    p_memory.add_argument(
        "--type",
        choices=["task", "summary", "insight", "system"],
        default=None,
        help="Filter by memory type",
    )
    p_memory.add_argument("--limit", type=int, default=20, help="Max results (default 20)")
    p_memory.add_argument("--json", action="store_true", help="JSON output")

    # memory-search
    p_msearch = sub.add_parser("memory-search", help="Search memories by keyword")
    p_msearch.add_argument("query", help="Search keyword")
    p_msearch.add_argument("--limit", type=int, default=10, help="Max results (default 10)")
    p_msearch.add_argument("--json", action="store_true", help="JSON output")

    # memory-add
    p_madd = sub.add_parser("memory-add", help="Add a memory manually")
    p_madd.add_argument("--type", required=True, help="Memory type (task|summary|insight|system)")
    p_madd.add_argument("--content", required=True, help="Memory content")
    p_madd.add_argument("--tags", default=None, help="Comma-separated tags")
    p_madd.add_argument("--json", action="store_true", help="JSON output")

    # memory-stats
    p_mstats = sub.add_parser("memory-stats", help="Show memory statistics")
    p_mstats.add_argument("--json", action="store_true", help="JSON output")

    # schedules
    p_scheds = sub.add_parser("schedules", help="List scheduled workflows")
    p_scheds.add_argument("--json", action="store_true", help="JSON output")

    # schedule-create
    p_screate = sub.add_parser("schedule-create", help="Create a scheduled workflow")
    p_screate.add_argument("name", help="Schedule name")
    p_screate.add_argument("--objective", required=True, help="Objective to execute")
    p_screate.add_argument("--interval", default=None, help="Interval in minutes")
    p_screate.add_argument("--daily", default=None, help="Daily time (HH:MM)")
    p_screate.add_argument("--weekly", default=None, help="Weekly day+time (e.g. mon 09:00)")
    p_screate.add_argument("--json", action="store_true", help="JSON output")

    # schedule-enable
    p_senable = sub.add_parser("schedule-enable", help="Enable a schedule")
    p_senable.add_argument("schedule_id", help="Schedule ID")
    p_senable.add_argument("--json", action="store_true", help="JSON output")

    # schedule-disable
    p_sdisable = sub.add_parser("schedule-disable", help="Disable a schedule")
    p_sdisable.add_argument("schedule_id", help="Schedule ID")
    p_sdisable.add_argument("--json", action="store_true", help="JSON output")

    # schedule-run-now
    p_srun = sub.add_parser("schedule-run-now", help="Trigger a schedule immediately")
    p_srun.add_argument("schedule_id", help="Schedule ID")
    p_srun.add_argument("--json", action="store_true", help="JSON output")

    # schedule-delete
    p_sdelete = sub.add_parser("schedule-delete", help="Delete a schedule")
    p_sdelete.add_argument("schedule_id", help="Schedule ID")
    p_sdelete.add_argument("--json", action="store_true", help="JSON output")

    # goals
    p_goals = sub.add_parser("goals", help="List goals")
    p_goals.add_argument("--json", action="store_true", help="JSON output")

    # goal-create
    p_gcreate = sub.add_parser("goal-create", help="Create a goal")
    p_gcreate.add_argument("name", help="Goal name")
    p_gcreate.add_argument("--objective", required=True, help="Goal objective")
    p_gcreate.add_argument(
        "--priority", default="medium", help="Priority (low|medium|high|critical)"
    )
    p_gcreate.add_argument("--json", action="store_true", help="JSON output")

    # goal-pause
    p_gpause = sub.add_parser("goal-pause", help="Pause a goal")
    p_gpause.add_argument("goal_id", help="Goal ID")
    p_gpause.add_argument("--json", action="store_true", help="JSON output")

    # goal-resume
    p_gresume = sub.add_parser("goal-resume", help="Resume a goal")
    p_gresume.add_argument("goal_id", help="Goal ID")
    p_gresume.add_argument("--json", action="store_true", help="JSON output")

    # goal-evaluate
    p_geval = sub.add_parser("goal-evaluate", help="Evaluate a goal")
    p_geval.add_argument("goal_id", help="Goal ID")
    p_geval.add_argument("--json", action="store_true", help="JSON output")

    # goal-delete
    p_gdelete = sub.add_parser("goal-delete", help="Delete a goal")
    p_gdelete.add_argument("goal_id", help="Goal ID")
    p_gdelete.add_argument("--json", action="store_true", help="JSON output")

    # goal-strategy
    p_gstrat = sub.add_parser("goal-strategy", help="Show goal decomposition strategy")
    p_gstrat.add_argument("goal_id", help="Goal ID")
    p_gstrat.add_argument("--recompute", action="store_true", help="Force strategy recomputation")
    p_gstrat.add_argument("--json", action="store_true", help="JSON output")

    # goal-refine
    p_grefine = sub.add_parser("goal-refine", help="Show refinement proposal")
    p_grefine.add_argument("goal_id", help="Goal ID")
    p_grefine.add_argument("--json", action="store_true", help="JSON output")

    # goal-apply-refinement
    p_gapply = sub.add_parser("goal-apply-refinement", help="Apply refinement proposal")
    p_gapply.add_argument("goal_id", help="Goal ID")
    p_gapply.add_argument("--json", action="store_true", help="JSON output")

    # brains
    p_brains = sub.add_parser("brains", help="List registered brains")
    p_brains.add_argument("--json", action="store_true", help="JSON output")

    # brain-show
    p_bshow = sub.add_parser("brain-show", help="Show a brain profile")
    p_bshow.add_argument("brain_id", help="Brain ID")
    p_bshow.add_argument("--json", action="store_true", help="JSON output")

    # brain-expression
    p_bexpr = sub.add_parser("brain-expression", help="Show brain expression state")
    p_bexpr.add_argument("brain_id", help="Brain ID")
    p_bexpr.add_argument("--json", action="store_true", help="JSON output")

    # brain-children
    p_bchildren = sub.add_parser("brain-children", help="List children of a brain")
    p_bchildren.add_argument("brain_id", help="Brain ID")
    p_bchildren.add_argument("--json", action="store_true", help="JSON output")

    # brain-signals
    p_bsignals = sub.add_parser("brain-signals", help="List brain signals")
    p_bsignals.add_argument("--brain-id", default=None, help="Filter by brain ID")
    p_bsignals.add_argument("--type", default=None, help="Filter by signal type")
    p_bsignals.add_argument("--limit", type=int, default=50, help="Max results")
    p_bsignals.add_argument("--json", action="store_true", help="JSON output")

    # feedback outcomes
    p_fb_oc = sub.add_parser("feedback-outcomes", help="List feedback outcomes")
    p_fb_oc.add_argument("--limit", type=int, default=20, help="Max results")
    p_fb_oc.add_argument("--json", action="store_true", help="JSON output")

    # feedback records
    p_fb_rec = sub.add_parser("feedback-records", help="List feedback records")
    p_fb_rec.add_argument("--limit", type=int, default=20, help="Max results")
    p_fb_rec.add_argument("--json", action="store_true", help="JSON output")

    # feedback memory-candidates
    p_fb_mc = sub.add_parser("feedback-candidates", help="List memory candidates")
    p_fb_mc.add_argument("--limit", type=int, default=20, help="Max results")
    p_fb_mc.add_argument("--json", action="store_true", help="JSON output")

    # feedback add
    p_fb_add = sub.add_parser("feedback-add", help="Add user feedback for a trace")
    p_fb_add.add_argument("--trace-id", required=True, help="Trace ID")
    p_fb_add.add_argument("--score", type=float, default=0.5, help="Score [0.0, 1.0]")
    p_fb_add.add_argument("--signal", default="user_positive", help="Signal type")
    p_fb_add.add_argument("--notes", default="", help="Notes")

    # Phase 79: observability (read-only)
    p_obs_status = sub.add_parser("observe-status", help="System health status")
    p_obs_status.add_argument("--json", action="store_true", help="JSON output")

    p_obs_dash = sub.add_parser("observe-dashboard", help="Operator dashboard snapshot")
    p_obs_dash.add_argument("--limit", type=int, default=25, help="Max items")
    p_obs_dash.add_argument("--json", action="store_true", help="JSON output")

    p_obs_tl = sub.add_parser("observe-timeline", help="Execution timeline")
    p_obs_tl.add_argument("--limit", type=int, default=50, help="Max events")
    p_obs_tl.add_argument("--json", action="store_true", help="JSON output")

    p_obs_traces = sub.add_parser("observe-traces", help="List recent traces")
    p_obs_traces.add_argument("--limit", type=int, default=25, help="Max results")
    p_obs_traces.add_argument("--json", action="store_true", help="JSON output")

    p_obs_trace = sub.add_parser("observe-trace", help="Show single trace")
    p_obs_trace.add_argument("--trace-id", required=True, help="Trace ID")
    p_obs_trace.add_argument("--json", action="store_true", help="JSON output")

    p_obs_explain = sub.add_parser("observe-explain", help="Explain a trace decision")
    p_obs_explain.add_argument("--trace-id", required=True, help="Trace ID")
    p_obs_explain.add_argument("--json", action="store_true", help="JSON output")

    p_obs_fail = sub.add_parser("observe-failures", help="Search failures")
    p_obs_fail.add_argument("--limit", type=int, default=25, help="Max results")
    p_obs_fail.add_argument("--json", action="store_true", help="JSON output")

    p_obs_sum = sub.add_parser("observe-summary", help="Execution summary")
    p_obs_sum.add_argument("--limit", type=int, default=100, help="Max items")
    p_obs_sum.add_argument("--json", action="store_true", help="JSON output")

    # Phase 80: registry (read-only)
    p_reg_cat = sub.add_parser("registry-catalog", help="Full registry catalog")
    p_reg_cat.add_argument("--json", action="store_true", help="JSON output")

    p_reg_over = sub.add_parser("registry-overview", help="Registry summary view")
    p_reg_over.add_argument("--json", action="store_true", help="JSON output")

    p_reg_health = sub.add_parser("registry-health", help="Registry health status")
    p_reg_health.add_argument("--json", action="store_true", help="JSON output")

    p_reg_q = sub.add_parser("registry-query", help="Query registry with filters")
    p_reg_q.add_argument("--type", default="", help="Registry type filter")
    p_reg_q.add_argument("--name", default="", help="Name substring filter")
    p_reg_q.add_argument("--capability", default="", help="Capability filter")
    p_reg_q.add_argument("--environment", default="", help="Environment filter")
    p_reg_q.add_argument("--tag", default="", help="Tag filter")
    p_reg_q.add_argument("--status", default="", help="Status filter")
    p_reg_q.add_argument("--risk-level", default="", help="Risk level filter")
    p_reg_q.add_argument("--limit", type=int, default=50, help="Max results")
    p_reg_q.add_argument("--json", action="store_true", help="JSON output")

    p_reg_item = sub.add_parser("registry-item", help="Show single registry item")
    p_reg_item.add_argument("--item-id", required=True, help="Item ID")
    p_reg_item.add_argument("--json", action="store_true", help="JSON output")

    p_reg_caps = sub.add_parser("registry-capabilities", help="List registered capabilities")
    p_reg_caps.add_argument("--environment", default="", help="Environment filter")
    p_reg_caps.add_argument("--risk-level", default="", help="Risk level filter")
    p_reg_caps.add_argument("--limit", type=int, default=50, help="Max results")
    p_reg_caps.add_argument("--json", action="store_true", help="JSON output")

    p_reg_envs = sub.add_parser("registry-environments", help="List registered environments")
    p_reg_envs.add_argument("--capability", default="", help="Capability filter")
    p_reg_envs.add_argument("--limit", type=int, default=50, help="Max results")
    p_reg_envs.add_argument("--json", action="store_true", help="JSON output")

    p_reg_modes = sub.add_parser("registry-modes", help="List workstation modes")
    p_reg_modes.add_argument("--limit", type=int, default=50, help="Max results")
    p_reg_modes.add_argument("--json", action="store_true", help="JSON output")

    p_reg_pol = sub.add_parser("registry-policies", help="List governance policies")
    p_reg_pol.add_argument("--limit", type=int, default=50, help="Max results")
    p_reg_pol.add_argument("--json", action="store_true", help="JSON output")

    # ── Phase 81: Ontology commands ──────────────────────────────────
    p_onto_status = sub.add_parser("ontology-status", help="Ontology kernel overview")
    p_onto_status.add_argument("--json", action="store_true", help="JSON output")

    p_onto_prims = sub.add_parser("ontology-primitives", help="List universal primitives")
    p_onto_prims.add_argument("--json", action="store_true", help="JSON output")

    p_onto_laws = sub.add_parser("ontology-laws", help="List universal laws")
    p_onto_laws.add_argument("--json", action="store_true", help="JSON output")

    p_onto_proj = sub.add_parser("ontology-projections", help="List domain projections")
    p_onto_proj.add_argument("--json", action="store_true", help="JSON output")

    p_onto_corr = sub.add_parser("ontology-correspondence", help="List correspondence maps")
    p_onto_corr.add_argument("--json", action="store_true", help="JSON output")

    p_onto_val = sub.add_parser("ontology-validate", help="Validate ontology kernel")
    p_onto_val.add_argument("--json", action="store_true", help="JSON output")

    p_onto_unity = sub.add_parser("ontology-unity", help="Show Unity / Oneness law")
    p_onto_unity.add_argument("--json", action="store_true", help="JSON output")

    p_onto_synth = sub.add_parser("ontology-synthesize", help="Demo polarity synthesis")
    p_onto_synth.add_argument("--json", action="store_true", help="JSON output")

    p_storage_status = sub.add_parser("storage-status", help="Storage gateway health")
    p_storage_status.add_argument("--json", action="store_true", help="JSON output")

    p_storage_descs = sub.add_parser("storage-descriptors", help="List storage descriptors")
    p_storage_descs.add_argument("--limit", type=int, default=50, help="Max results")
    p_storage_descs.add_argument("--json", action="store_true", help="JSON output")

    p_storage_audit = sub.add_parser("storage-audit", help="Run storage boundary audit")
    p_storage_audit.add_argument("--include-tests", action="store_true", help="Include test files")
    p_storage_audit.add_argument("--json", action="store_true", help="JSON output")

    p_storage_policy = sub.add_parser("storage-policy", help="Show storage policy")
    p_storage_policy.add_argument("--json", action="store_true", help="JSON output")

    p_mem_disc_status = sub.add_parser("memory-discipline-status", help="Memory discipline health")
    p_mem_disc_status.add_argument("--json", action="store_true", help="JSON output")

    p_mem_disc_policy = sub.add_parser("memory-discipline-policy", help="Memory write policy")
    p_mem_disc_policy.add_argument("--json", action="store_true", help="JSON output")

    # ── Phase 83: Migration commands ────────────────────────────────
    p_mig_status = sub.add_parser("migration-status", help="Migration health status")
    p_mig_status.add_argument("--json", action="store_true", help="JSON output")

    p_mig_inv = sub.add_parser("migration-inventory", help="Legacy module inventory")
    p_mig_inv.add_argument("--limit", type=int, default=100, help="Max records to show")
    p_mig_inv.add_argument("--json", action="store_true", help="JSON output")

    p_mig_dep = sub.add_parser("migration-deprecated", help="List deprecated modules")
    p_mig_dep.add_argument("--limit", type=int, default=100, help="Max results")
    p_mig_dep.add_argument("--json", action="store_true", help="JSON output")

    p_mig_risk = sub.add_parser("migration-bypass-risk", help="List bypass-risk modules")
    p_mig_risk.add_argument("--limit", type=int, default=100, help="Max results")
    p_mig_risk.add_argument("--json", action="store_true", help="JSON output")

    p_mig_map = sub.add_parser("migration-mappings", help="Show migration mappings")
    p_mig_map.add_argument("--limit", type=int, default=100, help="Max results")
    p_mig_map.add_argument("--json", action="store_true", help="JSON output")

    p_mig_imp = sub.add_parser("migration-imports", help="Scan import boundary violations")
    p_mig_imp.add_argument("--limit", type=int, default=100, help="Max findings")
    p_mig_imp.add_argument("--json", action="store_true", help="JSON output")

    p_mig_dash = sub.add_parser("migration-dashboard", help="Full migration dashboard")
    p_mig_dash.add_argument("--limit", type=int, default=100, help="Max items")
    p_mig_dash.add_argument("--json", action="store_true", help="JSON output")

    # ── Phase 84: Interface commands ────────────────────────────────
    p_if_status = sub.add_parser("interface-status", help="Interface layer status")
    p_if_status.add_argument("--json", action="store_true", help="JSON output")

    p_if_surfaces = sub.add_parser("interface-surfaces", help="List interface surfaces")
    p_if_surfaces.add_argument("--limit", type=int, default=100, help="Max results")
    p_if_surfaces.add_argument("--json", action="store_true", help="JSON output")

    p_if_matrix = sub.add_parser("interface-matrix", help="Surface capability matrix")
    p_if_matrix.add_argument("--limit", type=int, default=100, help="Max results")
    p_if_matrix.add_argument("--json", action="store_true", help="JSON output")

    p_if_cc = sub.add_parser("interface-command-center", help="Command Center snapshot")
    p_if_cc.add_argument("--json", action="store_true", help="JSON output")

    p_if_vw = sub.add_parser("interface-voice-wave", help="Voice wave state")
    p_if_vw.add_argument("--json", action="store_true", help="JSON output")

    p_if_notif = sub.add_parser("interface-notifications", help="Notification records")
    p_if_notif.add_argument("--json", action="store_true", help="JSON output")

    p_if_appr = sub.add_parser("interface-approvals", help="Approval display records")
    p_if_appr.add_argument("--json", action="store_true", help="JSON output")

    p_if_safe = sub.add_parser("interface-safety", help="Interface safety scan")
    p_if_safe.add_argument("--json", action="store_true", help="JSON output")

    # ── Phase 85: Council commands ──────────────────────────────────
    p_cncl_status = sub.add_parser("council-status", help="Council health status")
    p_cncl_status.add_argument("--json", action="store_true", help="JSON output")

    p_cncl_roles = sub.add_parser("council-roles", help="List council roles")
    p_cncl_roles.add_argument("--json", action="store_true", help="JSON output")

    p_cncl_delib = sub.add_parser("council-deliberate", help="Demo council deliberation")
    p_cncl_delib.add_argument("question", nargs="?", default="Should we proceed?", help="Question")
    p_cncl_delib.add_argument("--json", action="store_true", help="JSON output")

    p_cncl_safe = sub.add_parser("council-safety", help="Council safety scan")
    p_cncl_safe.add_argument("--json", action="store_true", help="JSON output")

    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point for the CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    dispatch = {
        "plan": cmd_plan,
        "run": cmd_run,
        "execute": cmd_execute,
        "watch": cmd_watch,
        "task": cmd_task,
        "tasks": cmd_tasks,
        "approvals": cmd_approvals,
        "cancel": cmd_cancel,
        "retry": cmd_retry,
        "timeline": cmd_timeline,
        "review": cmd_review,
        "controls": cmd_controls,
        "controls-set": cmd_controls_set,
        "queue": cmd_queue,
        "task-priority": cmd_task_priority,
        "tools": cmd_tools,
        "tool-run": cmd_tool_run,
        "memory": cmd_memory,
        "memory-search": cmd_memory_search,
        "memory-add": cmd_memory_add,
        "memory-stats": cmd_memory_stats,
        "schedules": cmd_schedules,
        "schedule-create": cmd_schedule_create,
        "schedule-enable": cmd_schedule_enable,
        "schedule-disable": cmd_schedule_disable,
        "schedule-run-now": cmd_schedule_run_now,
        "schedule-delete": cmd_schedule_delete,
        "goals": cmd_goals,
        "goal-create": cmd_goal_create,
        "goal-pause": cmd_goal_pause,
        "goal-resume": cmd_goal_resume,
        "goal-evaluate": cmd_goal_evaluate,
        "goal-delete": cmd_goal_delete,
        "goal-strategy": cmd_goal_strategy,
        "goal-refine": cmd_goal_refine,
        "goal-apply-refinement": cmd_goal_apply_refinement,
        "brains": cmd_brains,
        "brain-show": cmd_brain_show,
        "brain-expression": cmd_brain_expression,
        "brain-children": cmd_brain_children,
        "brain-signals": cmd_brain_signals,
        "feedback-outcomes": cmd_feedback_outcomes,
        "feedback-records": cmd_feedback_records,
        "feedback-candidates": cmd_feedback_candidates,
        "feedback-add": cmd_feedback_add,
        "observe-status": cmd_observe_status,
        "observe-dashboard": cmd_observe_dashboard,
        "observe-timeline": cmd_observe_timeline,
        "observe-traces": cmd_observe_traces,
        "observe-trace": cmd_observe_trace,
        "observe-explain": cmd_observe_explain,
        "observe-failures": cmd_observe_failures,
        "observe-summary": cmd_observe_summary,
        "registry-catalog": cmd_registry_catalog,
        "registry-overview": cmd_registry_overview,
        "registry-health": cmd_registry_health,
        "registry-query": cmd_registry_query,
        "registry-item": cmd_registry_item,
        "registry-capabilities": cmd_registry_capabilities,
        "registry-environments": cmd_registry_environments,
        "registry-modes": cmd_registry_modes,
        "registry-policies": cmd_registry_policies,
        "ontology-status": cmd_ontology_status,
        "ontology-primitives": cmd_ontology_primitives,
        "ontology-laws": cmd_ontology_laws,
        "ontology-projections": cmd_ontology_projections,
        "ontology-correspondence": cmd_ontology_correspondence,
        "ontology-validate": cmd_ontology_validate,
        "ontology-unity": cmd_ontology_unity,
        "ontology-synthesize": cmd_ontology_synthesize,
        "storage-status": cmd_storage_status,
        "storage-descriptors": cmd_storage_descriptors,
        "storage-audit": cmd_storage_audit,
        "storage-policy": cmd_storage_policy,
        "memory-discipline-status": cmd_memory_discipline_status,
        "memory-discipline-policy": cmd_memory_discipline_policy,
        "migration-status": cmd_migration_status,
        "migration-inventory": cmd_migration_inventory,
        "migration-deprecated": cmd_migration_deprecated,
        "migration-bypass-risk": cmd_migration_bypass_risk,
        "migration-mappings": cmd_migration_mappings,
        "migration-imports": cmd_migration_imports,
        "migration-dashboard": cmd_migration_dashboard,
        "interface-status": cmd_interface_status,
        "interface-surfaces": cmd_interface_surfaces,
        "interface-matrix": cmd_interface_matrix,
        "interface-command-center": cmd_interface_command_center,
        "interface-voice-wave": cmd_interface_voice_wave,
        "interface-notifications": cmd_interface_notifications,
        "interface-approvals": cmd_interface_approvals,
        "interface-safety": cmd_interface_safety,
        "council-status": cmd_council_status,
        "council-roles": cmd_council_roles,
        "council-deliberate": cmd_council_deliberate,
        "council-safety": cmd_council_safety,
    }

    handler = dispatch.get(args.command)
    if handler is None:
        parser.print_help()
        return 1

    try:
        return handler(args)
    except Exception as exc:
        if getattr(args, "json", False):
            print(json.dumps({"error": str(exc)}))
        else:
            print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
