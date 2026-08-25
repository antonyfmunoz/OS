"""Mesh dispatch — sends engineering plan tasks to a connected node via mesh HTTP relay.

Dispatches each task in sequence to a Beast node running Claude Code.
Each task sends an argv list to the mesh relay (no shell string building).
After execution, assembles a proof package for operator review.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

logger = logging.getLogger(__name__)

_MESH_RELAY_HOST = os.environ.get("UMH_MESH_RELAY_HOST", "localhost")
_MESH_RELAY_URL = f"http://{_MESH_RELAY_HOST}:8095/dispatch"
_MESH_RELAY_SECRET = os.environ.get("UMH_MESH_RELAY_SECRET", "").strip()

_ALLOWED_NODE_IDS = frozenset({"windows-desktop"})
_ALLOWED_CWD_ROOTS = (
    r"C:\dev\dev" + "\\",
    r"C:\dev" + "\\",
    r"D:\dev" + "\\",
)

_proof_packages: dict[str, Any] = {}


def get_proof_packages() -> dict[str, Any]:
    return dict(_proof_packages)


def _validate_node_id(node_id: str) -> None:
    if node_id not in _ALLOWED_NODE_IDS:
        raise ValueError(f"node_id not in allowlist: {node_id}")


def _validate_cwd(cwd: str) -> None:
    from pathlib import PureWindowsPath

    normalized = str(PureWindowsPath(cwd))
    if ".." in normalized or normalized.startswith("\\\\"):
        raise ValueError("cwd rejected: path traversal or UNC not allowed")
    check = normalized.lower().rstrip("\\") + "\\"
    if not any(check.startswith(root.lower()) for root in _ALLOWED_CWD_ROOTS):
        raise ValueError("cwd not under allowed workspace root")


async def dispatch_plan_to_node(
    plan: Any,
    node_id: str = "windows-desktop",
    cwd: str = r"C:\dev\dev\LYFEOS",
    timeout_per_task: int = 300,
) -> dict[str, Any]:
    """Dispatch all tasks from an engineering plan to a mesh node.

    Sends each task sequentially via the mesh HTTP relay.
    Each task sends an argv list (not a shell string) to avoid injection.
    After all tasks complete, assembles a proof package for review.
    """
    import httpx

    _validate_node_id(node_id)
    _validate_cwd(cwd)

    results: list[dict[str, Any]] = []
    dispatched = 0
    failed = 0

    tasks = plan.tasks if hasattr(plan, "tasks") else []

    _health_headers = (
        {"Authorization": f"Bearer {_MESH_RELAY_SECRET}"} if _MESH_RELAY_SECRET else {}
    )
    try:
        async with httpx.AsyncClient(timeout=10) as warmup:
            health_url = _MESH_RELAY_URL.rsplit("/", 1)[0] + "/health"
            await warmup.get(health_url, headers=_health_headers)
            logger.info("mesh relay warmup ok")
    except Exception as warmup_exc:
        logger.warning("mesh relay warmup failed (proceeding anyway): %r", warmup_exc)

    for task in tasks:
        description = task.description if hasattr(task, "description") else str(task)
        task_id = task.task_id if hasattr(task, "task_id") else ""

        prompt = _build_claude_prompt(description, plan)
        argv = ["claude", "-p", prompt, "--output-format", "json"]

        try:
            from uuid import uuid4

            from substrate.execution.mesh_verdict import get_verdict_secret, sign_verdict

            req_headers = {}
            if _MESH_RELAY_SECRET:
                req_headers["Authorization"] = f"Bearer {_MESH_RELAY_SECRET}"
            logger.info(
                "dispatch task %s sending to %s (timeout=%d)",
                task_id,
                _MESH_RELAY_URL,
                timeout_per_task,
            )
            timeouts = httpx.Timeout(timeout_per_task + 10, connect=10.0)

            # Shell is write-class — mint a signed verdict bound to node+capability
            # so the relay and node can validate before executing (fail-closed).
            if not get_verdict_secret():
                failed += 1
                logger.error(
                    "dispatch task %s aborted: no mesh verdict secret (fail-closed)", task_id
                )
                results.append(
                    {
                        "task_id": task_id,
                        "description": description[:120],
                        "status": "error",
                        "error": "no mesh verdict secret configured (fail-closed)",
                    }
                )
                continue
            verdict_token = sign_verdict(
                verdict_id=uuid4().hex,
                node_id=node_id,
                capability="shell",
                risk_class="reversible_write",
                ttl_seconds=timeout_per_task + 30,
            )
            payload = {
                "node_id": node_id,
                "capability": "shell",
                "params": {"argv": argv, "cwd": cwd},
                "risk_class": "reversible_write",
                "verdict_token": verdict_token,
                "timeout": timeout_per_task,
            }
            data = None
            for attempt in range(3):
                try:
                    if attempt > 0:
                        import asyncio

                        await asyncio.sleep(1)
                        try:
                            async with httpx.AsyncClient(timeout=10) as warmup:
                                health_url = _MESH_RELAY_URL.rsplit("/", 1)[0] + "/health"
                                await warmup.get(health_url, headers=_health_headers)
                                logger.info("dispatch task %s retry warmup ok", task_id)
                        except Exception:
                            pass
                    async with httpx.AsyncClient(timeout=timeouts) as client:
                        resp = await client.post(_MESH_RELAY_URL, headers=req_headers, json=payload)
                        logger.info(
                            "dispatch task %s got HTTP %d, %d bytes",
                            task_id,
                            resp.status_code,
                            len(resp.content),
                        )
                        data = resp.json()
                    break
                except httpx.ReadError as read_err:
                    if attempt < 2:
                        logger.warning(
                            "dispatch task %s ReadError on attempt %d, retrying: %r",
                            task_id,
                            attempt + 1,
                            read_err,
                        )
                        continue
                    raise

            logger.info(
                "dispatch task %s response: ok=%s latency=%s",
                task_id,
                data.get("ok"),
                data.get("latency_ms"),
            )
            if data.get("ok"):
                dispatched += 1
                results.append(
                    {
                        "task_id": task_id,
                        "description": description[:120],
                        "status": "executed",
                        "result": data.get("result_data", {}),
                        "latency_ms": data.get("latency_ms"),
                    }
                )
            else:
                failed += 1
                logger.warning("dispatch task %s not ok: %s", task_id, json.dumps(data)[:500])
                results.append(
                    {
                        "task_id": task_id,
                        "description": description[:120],
                        "status": "failed",
                        "error": data.get("error", "unknown"),
                    }
                )

        except Exception as exc:
            failed += 1
            logger.error("dispatch task %s failed: %r", task_id, exc)
            results.append(
                {
                    "task_id": task_id,
                    "description": description[:120],
                    "status": "error",
                    "error": "dispatch failed",
                }
            )

    proof = _assemble_proof(plan, results, node_id)

    return {
        "plan_id": plan.plan_id if hasattr(plan, "plan_id") else "",
        "node_id": node_id,
        "dispatched": dispatched,
        "failed": failed,
        "total_tasks": len(tasks),
        "results": results,
        "proof_id": proof.get("proof_id", ""),
    }


def _assemble_proof(
    plan: Any,
    results: list[dict[str, Any]],
    node_id: str,
) -> dict[str, Any]:
    """Assemble a proof package from dispatch results for operator review."""
    from substrate.meta_ide.engineering_execution import (
        EngineeringExecutionSession,
        EngineeringExecutionStatus,
        EngineeringProofPackage,
        OperatorRecommendation,
    )

    plan_id = plan.plan_id if hasattr(plan, "plan_id") else ""

    session = EngineeringExecutionSession(
        plan_id=plan_id,
        workspace_targets=[node_id],
    )

    all_succeeded = True
    for r in results:
        task_id = r.get("task_id", "")
        succeeded = r.get("status") == "executed"
        result_data = r.get("result", {})
        session.task_results[task_id] = {
            "success": succeeded,
            "outcome": r.get("status", "unknown"),
            "stdout": result_data.get("stdout", "")[:2000] if isinstance(result_data, dict) else "",
            "stderr": result_data.get("stderr", "")[:2000] if isinstance(result_data, dict) else "",
            "exit_code": result_data.get("exit_code") if isinstance(result_data, dict) else None,
            "latency_ms": r.get("latency_ms"),
        }
        if not succeeded:
            all_succeeded = False
            session.errors.append(f"Task {task_id}: {r.get('error', r.get('status'))}")

    if all_succeeded:
        session.status = EngineeringExecutionStatus.AWAITING_REVIEW
    else:
        session.status = EngineeringExecutionStatus.FAILED

    session.completed_at = time.time()
    session.updated_at = time.time()

    try:
        from substrate.meta_ide.review_package_builder import ReviewPackageBuilder

        builder = ReviewPackageBuilder()
        proof = builder.build_package(session)
    except Exception as exc:
        logger.error("proof assembly failed, building minimal: %s", exc)
        recommendation = (
            OperatorRecommendation.APPROVE if all_succeeded else OperatorRecommendation.REJECT
        )
        proof = EngineeringProofPackage(
            session_id=session.session_id,
            plan_id=plan_id,
            operator_recommendation=recommendation,
            recommendation_reasoning=[
                f"{'All tasks succeeded' if all_succeeded else 'Some tasks failed'}",
                f"Total: {len(results)}, Failed: {sum(1 for r in results if r.get('status') != 'executed')}",
            ],
        )

    proof_dict = proof.to_dict()
    _proof_packages[proof.proof_id] = proof_dict

    logger.info(
        "proof package %s assembled for plan %s: %s",
        proof.proof_id,
        plan_id,
        proof.operator_recommendation.value
        if hasattr(proof.operator_recommendation, "value")
        else proof.operator_recommendation,
    )

    return proof_dict


def _build_claude_prompt(task_description: str, plan: Any) -> str:
    """Build the Claude Code prompt for a task."""
    goal = plan.intent.goal if hasattr(plan, "intent") and hasattr(plan.intent, "goal") else ""
    return (
        f"You are working on: {goal}\n\n"
        f"Current task: {task_description}\n\n"
        f"Work in the current directory. Make real changes. "
        f"Run tests after changes. Commit when done."
    )
