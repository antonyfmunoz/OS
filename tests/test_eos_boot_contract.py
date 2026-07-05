"""WP-P4-003 — EOS integration boot-contract regression tests.

The EOS boot path (`transports/api/app.py::_register_eos_integration`) reads the
config produced by `load_eos_config()` and constructs an `EOSPoller`. A defect
had `app.py` read `config["org_ids"]` and pass `org_ids=`, but `load_eos_config()`
returns `user_ids` (never `org_ids`) and `EOSPoller.__init__` accepts `user_ids`
(not `org_ids`). With `EOS_DATABASE_URL` set, that raised `KeyError` — swallowed by
the boot try/except, so the poller silently never started whenever EOS was
actually configured.

`org_ids` is a vestigial name from the superseded multi-org design (DESIGN.md);
the canonical config key is `user_ids`.

These tests lock the boot contract without importing `transports.api.app`, which
currently fails to import for an unrelated, pre-existing reason (a live module
imports `governed_shell_adapter_v1` from its old location after it moved to
`_dormant/`). No collected test imports that module, so this is out of scope here.
"""

from __future__ import annotations

import ast
import inspect
import os
import sys
from pathlib import Path

_WORKTREE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _WORKTREE not in sys.path:
    sys.path.insert(0, _WORKTREE)

from projections.eos.integration.manifest import load_eos_config
from projections.eos.integration.poller import EOSPoller

_APP_PY = Path(_WORKTREE) / "transports" / "api" / "app.py"


def test_load_eos_config_returns_user_ids_not_org_ids(monkeypatch):
    """The config the boot path consumes carries `user_ids`, never `org_ids`."""
    monkeypatch.setenv("EOS_DATABASE_URL", "postgres://test")
    monkeypatch.setenv("EOS_USER_IDS", "u1,u2")
    config = load_eos_config()
    assert "user_ids" in config, "load_eos_config must return the canonical key user_ids"
    assert "org_ids" not in config, "org_ids is vestigial and must not be produced"
    assert config["user_ids"] == ["u1", "u2"]


def test_eos_poller_accepts_user_ids_not_org_ids():
    """The poller's whitelist kwarg is `user_ids`; passing `org_ids=` is a TypeError."""
    params = set(inspect.signature(EOSPoller.__init__).parameters)
    assert "user_ids" in params
    assert "org_ids" not in params


def _register_eos_integration_source() -> str:
    """The source of `_register_eos_integration`, extracted without importing app.py
    (which has an unrelated pre-existing import break — see module docstring)."""
    text = _APP_PY.read_text(encoding="utf-8")
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_register_eos_integration":
            return ast.get_source_segment(text, node) or ""
    raise AssertionError("_register_eos_integration not found in transports/api/app.py")


def test_boot_reads_user_ids_and_passes_user_ids_kwarg():
    """WP-P4-003: `_register_eos_integration` reads config["user_ids"] and passes the
    EOSPoller `user_ids=` kwarg — and never touches the dead `org_ids` key/kwarg.
    This is the regression that proves the boot path no longer KeyErrors when
    EOS_DATABASE_URL is set."""
    src = _register_eos_integration_source()
    assert 'config["user_ids"]' in src, "boot must read the canonical config key user_ids"
    assert "user_ids=" in src, "boot must pass the EOSPoller user_ids= kwarg"
    assert "org_ids" not in src, (
        "the vestigial org_ids key/kwarg must not appear in the EOS boot path — "
        "load_eos_config() never returns it, so reading it KeyErrors when configured"
    )
