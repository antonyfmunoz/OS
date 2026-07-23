"""Wave 1 grounding root — instance-independent repository-root resolution.

Owner order (FINAL WAVE 1 MERGE-READINESS CLOSURE, defect B): the grounding
module must NOT carry a hardcoded ``/opt/OS`` fallback. Explicit ``UMH_ROOT``
wins; with no explicit root the module derives one from its own on-disk location
so it works from ANY checkout path (worktree, container mount, CI clone).
"""

from __future__ import annotations

import os
from pathlib import Path

import substrate.execution.planning.grounding as grounding


def test_no_hardcoded_opt_os_literal_in_source():
    """The module source carries no bare '/opt/OS' deployment literal."""
    src = Path(grounding.__file__).read_text(encoding="utf-8")
    assert '"/opt/OS"' not in src
    assert "'/opt/OS'" not in src


def test_explicit_umh_root_is_honored(monkeypatch):
    monkeypatch.setenv("UMH_ROOT", "/some/other/checkout")
    assert grounding._repo_root() == "/some/other/checkout"


def test_blank_umh_root_falls_through_to_derived_root(monkeypatch):
    """A blank/whitespace UMH_ROOT is not an explicit root — derive instead."""
    monkeypatch.setenv("UMH_ROOT", "   ")
    root = grounding._repo_root()
    assert root.strip()
    assert root != "/opt/OS"


def test_derived_root_when_env_unset_points_at_a_real_checkout(monkeypatch):
    """With no UMH_ROOT set, the derived root is this module's own repository
    root — never a hardcoded '/opt/OS'. Proven by locating the module relative
    to the derived root, independent of where the checkout physically lives."""
    monkeypatch.delenv("UMH_ROOT", raising=False)
    root = Path(grounding._repo_root())
    # The grounding module lives under <root>/substrate/execution/planning/.
    assert (root / "substrate" / "execution" / "planning" / "grounding.py").is_file()
    # And it matches the module file's own real parent chain (works from any path).
    assert root == Path(grounding.__file__).resolve().parents[3]


def test_module_functions_outside_opt_os(monkeypatch, tmp_path):
    """Point UMH_ROOT at a synthetic checkout OUTSIDE /opt/OS and prove the
    grounding path probes resolve there — the whole point of removing the
    hardcoded fallback."""
    fake_root = tmp_path / "elsewhere" / "umh-checkout"
    (fake_root / "data" / "umh" / "organism").mkdir(parents=True)
    monkeypatch.setenv("UMH_ROOT", str(fake_root))

    assert grounding._repo_root() == str(fake_root)
    # The legacy-runtime dir probe uses _repo_root(); it must land under fake_root.
    probe = grounding._bounded_dir_probe(
        os.path.join(grounding._repo_root(), "data", "umh", "organism")
    )
    assert probe["exists"] is True
    assert str(fake_root) in probe["path"]
