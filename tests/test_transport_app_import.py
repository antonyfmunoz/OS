"""WP-P4-004 — transport app import viability.

`transports.api.app` is the transport-layer FastAPI app surface. It must import
cleanly (module-level `import`), because a broken top-level import poisons the
entire transport boot path and makes true end-to-end app boot impossible.

Regression: commit c40a8b3e0 ("freeze 32 speculative workstation files") swept
four still-in-use workstation modules into `_dormant/` — `governed_shell_adapter_v1`,
`workstation_operational_modes_v1`, `workstation_observability_pipeline_v1`,
`workstation_continuity_bridge_v1`. The live `WorkstationExecutionOrchestrator`
(instantiated at import in `transports/api/workstation.py`) and the live
`TmuxOperationalAdapter` import all four, so `import transports.api.app` raised
ModuleNotFoundError. WP-P4-004 moved those four back to the live workstation dir
(relocation reversal — zero source edits). This test locks the import surface so a
future over-broad freeze can't silently re-poison it.

No env vars are required to import the app (CLERK warnings are non-fatal; the heavy
runtime wiring — EOS/Notion pollers, DB URLs — lives inside functions/lifespan
handlers, not at import scope). This test therefore does NOT set EOS_DATABASE_URL,
which also confirms env-disabled boot is import-clean.
"""

from __future__ import annotations

import importlib
import os
import sys
import warnings

_WORKTREE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _WORKTREE not in sys.path:
    sys.path.insert(0, _WORKTREE)


def test_transports_api_app_imports_cleanly(monkeypatch):
    """`import transports.api.app` succeeds without EOS_DATABASE_URL set."""
    monkeypatch.delenv("EOS_DATABASE_URL", raising=False)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        mod = importlib.import_module("transports.api.app")
    assert mod is not None
    # The workstation router (whose orchestrator triggered the break) is wired in.
    assert hasattr(mod, "_register_eos_integration")


def test_live_workstation_modules_are_importable():
    """The four workstation modules the live orchestrator/tmux adapter depend on
    resolve from the live package (not `_dormant/`), so the orchestrator's
    top-level imports don't ModuleNotFoundError."""
    for name in (
        "governed_shell_adapter_v1",
        "workstation_operational_modes_v1",
        "workstation_observability_pipeline_v1",
        "workstation_continuity_bridge_v1",
    ):
        mod = importlib.import_module(
            f"substrate.execution.workers.workstation.{name}"
        )
        assert mod is not None, name
