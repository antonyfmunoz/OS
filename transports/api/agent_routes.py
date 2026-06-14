"""Agent Executor API routes — governed cognitive worker endpoints.

Routes:
  POST /agents/run                         — submit agent task
  GET  /agents/executions                  — list agent executions
  GET  /agents/executions/{execution_id}   — single execution details
  POST /agents/executions/{execution_id}/cancel — cancel execution

All routes require Clerk auth.

UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time

from fastapi import Request

logger = logging.getLogger(__name__)


def _ensure_agent_executor_registered() -> None:
    """Register AgentExecutor with the executor runtime if not already done."""
    try:
        from substrate.organism.executor_runtime import ExecutorType, get_executor_runtime
        from substrate.organism.executors.agent_executor import AgentExecutor
        from substrate.organism.executors.execution_telemetry import get_telemetry_emitter

        runtime = get_executor_runtime()
        if not isinstance(runtime._impl_registry.get(ExecutorType.AGENT.value), AgentExecutor):
            emitter = get_telemetry_emitter()
            executor = AgentExecutor(telemetry_emitter=emitter, runtime=runtime)
            runtime._impl_registry.register(ExecutorType.AGENT.value, executor)
            logger.info("AgentExecutor registered with executor runtime")
    except Exception as exc:
        logger.warning("Failed to register AgentExecutor: %s", exc)


def _get_runtime():
    from substrate.organism.executor_runtime import get_executor_runtime
    _ensure_agent_executor_registered()
    return get_executor_runtime()


def _authenticated_operator(request: Request) -> str:
    """Extract operator identity from auth middleware."""
    return getattr(request.state, "clerk_user_id", None) or "authenticated-operator"


async def agent_run(request: Request) -> dict:
    """POST /agents/run — submit a task to AgentExecutor."""
    try:
        body = await request.json()
    except Exception:
        return {"success": False, "error": "Invalid JSON body"}

    task = body.get("task", "")
    if not task or not task.strip():
        return {"success": False, "error": "Task is required"}

    worktree_path = body.get("worktree_path", "")
    timeout_seconds = body.get("timeout_seconds")

    try:
        from substrate.organism.executor_runtime import ExecutorType

        runtime = _get_runtime()
        operator_id = _authenticated_operator(request)

        req = runtime.create_request(
            execution_plan_id=f"agent-task-{int(time.time())}",
            executor_type=ExecutorType.AGENT.value,
            description=task[:200],
            metadata={
                "operation": "run_task",
                "params": {
                    "task": task,
                    "worktree_path": worktree_path,
                    "timeout_seconds": timeout_seconds,
                },
                "submitted_by": operator_id,
            },
        )

        result = runtime.run_lifecycle(req.request_id)

        return {
            "success": True,
            "execution_id": req.request_id,
            "result": result.to_dict() if result else None,
        }

    except Exception as exc:
        logger.error("agent run failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def agent_executions(request: Request) -> dict:
    """GET /agents/executions — list agent-type executions."""
    try:
        from substrate.organism.executor_runtime import ExecutorType

        runtime = _get_runtime()
        all_requests = runtime.request_history(limit=100)
        agent_reqs = [
            r.to_dict()
            for r in all_requests
            if r.executor_type == ExecutorType.AGENT.value
        ]
        return {"success": True, "executions": agent_reqs, "count": len(agent_reqs)}
    except Exception as exc:
        logger.error("agent executions list failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def agent_execution_detail(request: Request) -> dict:
    """GET /agents/executions/{execution_id} — single agent execution."""
    try:
        execution_id = request.path_params.get("execution_id", "")
        runtime = _get_runtime()

        all_requests = runtime.request_history(limit=500)
        found = None
        for r in all_requests:
            if r.request_id == execution_id:
                found = r
                break

        if not found:
            return {"success": False, "error": "Not found"}

        result_data = None
        results = runtime.all_results()
        for res in results:
            if res.request_id == execution_id:
                result_data = res.to_dict()
                break

        return {
            "success": True,
            "execution": found.to_dict(),
            "result": result_data,
        }
    except Exception as exc:
        logger.error("agent execution detail failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def agent_cancel(request: Request) -> dict:
    """POST /agents/executions/{execution_id}/cancel — cancel agent execution."""
    try:
        execution_id = request.path_params.get("execution_id", "")
        runtime = _get_runtime()
        cancelled = runtime.cancel_request(execution_id)
        return {"success": cancelled, "execution_id": execution_id}
    except Exception as exc:
        logger.error("agent cancel failed: %s", exc)
        return {"success": False, "error": str(exc)}
