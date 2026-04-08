"""Workflow registry — wires existing Control Plane workflows into the orchestrator.

The three migrated CP workflows (morning_prep_cp, nightly_consolidation_cp,
weekly_review_cp) already call `run_action()` internally with idempotency
keys, so the orchestrator treats each one as a callable workflow that
returns a simple {"ok": bool} summary.

Calling `register_default_workflows()` is idempotent and safe to call
from any entry point (scripts/orchestrator_loop.py, a Python shell, a
test). Signal bindings are registered alongside the workflows so a
fresh environment works end-to-end without manual setup.
"""

from __future__ import annotations

import importlib
from typing import Any

from .orchestrator import Orchestrator, default_orchestrator
from .signals import register_handler


_CP_WORKFLOW_MODULES = {
    "morning_prep": "scripts.scheduled.morning_prep_cp",
    "nightly_consolidation": "scripts.scheduled.nightly_consolidation_cp",
    "weekly_review": "scripts.scheduled.weekly_review_cp",
}


def _wrap_main(module_path: str):
    """Build an orchestrator-compatible callable from a CP workflow module.

    The migrated workflows expose `main() -> int` (exit code). We import
    lazily so registering the workflow doesn't trigger network calls or
    heavy imports at module load time.
    """

    def _run(context: dict[str, Any]) -> dict[str, Any]:
        module = importlib.import_module(module_path)
        if not hasattr(module, "main"):
            return {"ok": False, "error": f"{module_path} has no main()"}
        try:
            exit_code = module.main()
        except Exception as e:
            return {
                "ok": False,
                "error": f"{type(e).__name__}: {e}",
                "module": module_path,
            }
        return {
            "ok": int(exit_code) == 0,
            "exit_code": int(exit_code),
            "module": module_path,
        }

    return _run


def register_default_workflows(orch: Orchestrator | None = None) -> list[str]:
    """Register all known CP workflows on the given (or default) orchestrator.

    Returns the list of registered workflow names. Safe to call repeatedly.
    """
    orch = orch or default_orchestrator()
    registered: list[str] = []
    for name, module_path in _CP_WORKFLOW_MODULES.items():
        orch.register_workflow(name, _wrap_main(module_path))
        registered.append(name)

    # Default signal bindings. These match the natural rhythm:
    #   morning_ready  → morning_prep
    #   nightly_cycle  → nightly_consolidation
    #   weekly_cycle   → weekly_review
    register_handler("morning_ready", "morning_prep")
    register_handler("nightly_cycle", "nightly_consolidation")
    register_handler("weekly_cycle", "weekly_review")
    return registered


__all__ = ["register_default_workflows"]
