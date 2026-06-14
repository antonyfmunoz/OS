"""Runtime State API routes — read-only workstation awareness.

Provides cockpit endpoints for querying live environment state.

Routes:
  GET /runtime/state         — full runtime state (latest snapshot)
  GET /runtime/snapshot      — latest snapshot with metadata
  GET /runtime/executions    — active executions
  GET /runtime/processes     — interesting running processes
  GET /runtime/worktrees     — git worktrees
  GET /runtime/containers    — Docker containers
  GET /runtime/history       — snapshot history (summaries only)

All routes are read-only. No mutation endpoints.

UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations

import logging

from fastapi import Request

logger = logging.getLogger(__name__)


def _get_registry():
    from substrate.organism.runtime_state_registry import (
        get_runtime_state_registry,
    )
    return get_runtime_state_registry()


async def runtime_state(request: Request) -> dict:
    """GET /runtime/state — full runtime state."""
    try:
        registry = _get_registry()
        state = registry.get_runtime_state()
        return {"success": True, **state}
    except Exception as exc:
        logger.error("runtime state failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def runtime_snapshot_latest(request: Request) -> dict:
    """GET /runtime/snapshot — latest snapshot."""
    try:
        registry = _get_registry()
        snap = registry.snapshot()
        if snap is None:
            snap_dict = registry.get_runtime_state()
        else:
            snap_dict = snap.to_dict()
        return {
            "success": True,
            "snapshot": snap_dict,
            "snapshot_count": registry.snapshot_count(),
        }
    except Exception as exc:
        logger.error("runtime snapshot failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def runtime_executions(request: Request) -> dict:
    """GET /runtime/executions — active executions."""
    try:
        registry = _get_registry()
        execs = registry.get_executions()
        return {"success": True, "executions": execs, "count": len(execs)}
    except Exception as exc:
        logger.error("runtime executions failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def runtime_processes(request: Request) -> dict:
    """GET /runtime/processes — running processes."""
    try:
        registry = _get_registry()
        procs = registry.get_processes()
        return {"success": True, "processes": procs, "count": len(procs)}
    except Exception as exc:
        logger.error("runtime processes failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def runtime_worktrees(request: Request) -> dict:
    """GET /runtime/worktrees — git worktrees."""
    try:
        registry = _get_registry()
        wts = registry.get_worktrees()
        return {"success": True, "worktrees": wts, "count": len(wts)}
    except Exception as exc:
        logger.error("runtime worktrees failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def runtime_containers(request: Request) -> dict:
    """GET /runtime/containers — Docker containers."""
    try:
        registry = _get_registry()
        containers = registry.get_containers()
        return {"success": True, "containers": containers, "count": len(containers)}
    except Exception as exc:
        logger.error("runtime containers failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def runtime_history(request: Request) -> dict:
    """GET /runtime/history — snapshot history."""
    try:
        registry = _get_registry()
        limit = 20
        limit_param = request.query_params.get("limit")
        if limit_param and limit_param.isdigit():
            limit = min(int(limit_param), 100)
        history = registry.snapshot_history(limit=limit)
        return {"success": True, "history": history, "count": len(history)}
    except Exception as exc:
        logger.error("runtime history failed: %s", exc)
        return {"success": False, "error": str(exc)}
