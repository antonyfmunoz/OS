"""P4S31 Voice Convergence — operator_api mounts the governed voice router (Commit 3).

Proves the deployed backend (:8091, services/operator_api.py) mounts the ONE
governed voice router and that the WS path is unique. (The "no rival voice
runtime" AST assertions land in Commit 4, which deletes the rival.)
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_ROOT = Path(__file__).resolve().parent.parent
_OPERATOR_API = _ROOT / "services" / "operator_api.py"


def test_operator_api_mounts_voice_router() -> None:
    src = _OPERATOR_API.read_text(encoding="utf-8")
    assert "from transports.api.voice import router as voice_router" in src
    assert "app.include_router(voice_router)" in src
    # organism accessor wired for governed converse
    assert "wire_organism(" in src


def test_operator_api_preloads_warm_engine() -> None:
    src = _OPERATOR_API.read_text(encoding="utf-8")
    assert "preload_warm_engine" in src
    assert "_voice_warmup_task = asyncio.create_task(_run_voice_warmup(_api_executor))" in src
    assert "await asyncio.get_running_loop().run_in_executor(_api_executor, preload_warm_engine)" not in src


def test_voice_ws_path_unique() -> None:
    # Exactly one '/api/umh/voice/ws' route in the voice router (GAP6).
    from transports.api.voice import router

    ws_paths = [
        getattr(r, "path", "")
        for r in router.routes
        if getattr(r, "path", "") == "/api/umh/voice/ws"
    ]
    assert len(ws_paths) == 1


def test_operator_api_parses() -> None:
    # The file must parse (guards against a broken try/except from the edits).
    ast.parse(_OPERATOR_API.read_text(encoding="utf-8"))
