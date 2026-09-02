"""Wave 2 — _run_git handles a CPU-gate refusal gracefully (sixth layer, part 1).

``gated_subprocess_run`` returns ``None`` when the CPU gate blocks (CPU Gate
Law). Every ``_run_git`` caller in worktree_sandbox immediately reads
``result.returncode``, so a None silently became
``'NoneType' object has no attribute 'returncode'`` — an opaque crash a caller
could not distinguish from a real git failure (field run 20260725T205058Z, sixth
control-plane layer: lease git-subprocess CPU-gated under load 9.5). ``_run_git``
now raises a clear, catchable ``CpuGatedGitError`` instead; the lease-creation
path treats that as a TRANSIENT block (retry when load drops), never a crash.
"""

from __future__ import annotations

import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import pytest

import substrate.organism.worktree_sandbox as ws


def test_run_git_raises_cpu_gated_error_on_gate_none(monkeypatch):
    """When the CPU gate refuses (returns None), _run_git raises CpuGatedGitError
    — NOT an opaque AttributeError on result.returncode."""
    monkeypatch.setattr(ws, "gated_subprocess_run", lambda *a, **k: None)
    with pytest.raises(ws.CpuGatedGitError):
        ws._run_git(["rev-parse", "HEAD"], cwd="/tmp")


def test_run_git_returns_result_when_gate_allows(monkeypatch):
    """When the gate allows, _run_git returns the CompletedProcess unchanged."""
    from types import SimpleNamespace

    sentinel = SimpleNamespace(returncode=0, stdout="abc123\n", stderr="")
    monkeypatch.setattr(ws, "gated_subprocess_run", lambda *a, **k: sentinel)
    result = ws._run_git(["rev-parse", "HEAD"], cwd="/tmp")
    assert result is sentinel
    assert result.returncode == 0


def test_cpu_gated_error_is_a_runtimeerror():
    """CpuGatedGitError must be catchable as a RuntimeError so the generic
    admission `except Exception` in the scheduler still parks it as BLOCKED (and
    the re-arm step then recovers it)."""
    assert issubclass(ws.CpuGatedGitError, RuntimeError)
