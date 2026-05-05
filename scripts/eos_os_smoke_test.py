#!/usr/bin/env python3
"""
eos_os_smoke_test.py — End-to-end verification for the EOS AI OS.

Exercises every layer of the unified stack without relying on external
LLM providers. Prints a PASS/FAIL line per check and exits non-zero on
the first failure so CI / ops can trust the return code.

Coverage:
    1. Imports — all new core modules load cleanly
    2. Capability — enforcer decisions (allow + deny)
    3. Harness  — graph_search + a denied action
    4. Persistent agents — Observer tick (no LLM)
    5. Optimizer — run_once() writes proposals
    6. Observability — snapshot() reflects recent activity
    7. Control plane — start --once lifecycle (orchestrator + agents)

Usage:
    python3 scripts/eos_os_smoke_test.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
import traceback
from pathlib import Path

_REPO_ROOT = "/opt/OS"
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


# ---------------------------------------------------------------------------
# Tiny test harness
# ---------------------------------------------------------------------------


class SmokeRunner:
    def __init__(self) -> None:
        self.failed: list[str] = []
        self.passed: list[str] = []

    def check(self, name: str, fn) -> None:
        print(f"  … {name}", flush=True)
        try:
            fn()
        except AssertionError as e:
            self.failed.append(f"{name}: {e}")
            print(f"  ✗ {name} — {e}")
            return
        except Exception as e:
            self.failed.append(f"{name}: {type(e).__name__}: {e}")
            print(f"  ✗ {name} — {type(e).__name__}: {e}")
            traceback.print_exc()
            return
        self.passed.append(name)
        print(f"  ✓ {name}")

    def summary(self) -> int:
        total = len(self.passed) + len(self.failed)
        print()
        print("─" * 60)
        print(f"  PASSED: {len(self.passed)}/{total}")
        if self.failed:
            print(f"  FAILED: {len(self.failed)}")
            for f in self.failed:
                print(f"    - {f}")
            return 1
        print("  ALL SMOKE CHECKS PASSED")
        return 0


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


def check_imports() -> None:
    """Every new core module should import cleanly."""
    import core.capability  # noqa: F401
    import core.agent_harness  # noqa: F401
    import core.persistent_agents  # noqa: F401
    import core.optimizer  # noqa: F401
    import core.observability  # noqa: F401
    import core.control_plane  # noqa: F401


def check_capability() -> None:
    from core.capability import (
        Capability,
        CapabilityEnforcer,
        DEFAULT_PROFILES,
        OperationKind,
        RiskTier,
    )

    enforcer = CapabilityEnforcer()

    # Researcher may read the graph
    researcher = DEFAULT_PROFILES["researcher"]
    d_allow = enforcer.may(researcher, OperationKind.READ_GRAPH, RiskTier.NONE)
    assert d_allow.allowed, f"researcher should read graph: {d_allow.reason}"

    # Researcher may NOT edit a critical hub
    d_deny = enforcer.may(
        researcher, OperationKind.EDIT_CRITICAL_HUB, RiskTier.HIGH
    )
    assert not d_deny.allowed, "researcher must NOT edit critical hubs"

    # Executor may edit a file
    executor = DEFAULT_PROFILES["executor"]
    d_exec = enforcer.may(executor, OperationKind.EDIT_FILE, RiskTier.MEDIUM)
    assert d_exec.allowed, f"executor should edit files: {d_exec.reason}"

    # CEO is decisional, not executional — reads + LLM only, never mutates.
    ceo = DEFAULT_PROFILES["ceo"]
    assert ceo.max_capability == Capability.READ, (
        f"ceo should be read-only (decisional), got {ceo.max_capability}"
    )
    d_ceo_mutate = enforcer.may(ceo, OperationKind.EDIT_FILE, RiskTier.LOW)
    assert not d_ceo_mutate.allowed, "ceo must not be able to edit files"


def check_harness() -> None:
    from core.agent_harness import default_harness

    h = default_harness()

    # Graph search as researcher (READ-level) should succeed or return a
    # structured empty result — it must never raise.
    result = h.graph_search("researcher", "memory")
    assert isinstance(result.ok, bool), "graph_search must return HarnessResult"

    # A denied action should come back ok=False with a clear error.
    bad = h.run_action(
        "researcher",
        action_type="delete_file",
        target="data/agent_state/observer.json",
        reason="smoke test — expected denial",
        dry_run=True,
    )
    assert bad.ok is False, "delete should be denied for researcher"
    assert bad.error, "denied action must populate error"


def check_persistent_agents() -> None:
    from core.persistent_agents import ObserverAgent

    obs = ObserverAgent()
    r = obs.tick()
    assert r.ok, f"observer tick should succeed: {r.summary}"

    # State file should exist after tick
    assert obs.state_file.exists(), "observer state file missing after tick"
    state = json.loads(obs.state_file.read_text(encoding="utf-8"))
    assert state.get("tick_count", 0) >= 1


def check_optimizer() -> None:
    from core.optimizer import Optimizer

    opt = Optimizer()
    result = opt.run_once()
    assert result.get("ok") is True, f"optimizer.run_once failed: {result}"
    # proposals_new may be 0 — that's fine. The contract is: the call
    # runs without raising and returns a well-shaped dict.
    assert "proposals_total_pending" in result


def check_observability() -> None:
    from core.observability import Observability

    obs = Observability()
    snap = obs.snapshot()
    for key in ("workflows", "orchestrator", "harness", "agents", "optimizer"):
        assert key in snap, f"snapshot missing key: {key}"

    # After the observer tick above, agent_status should have ≥ 1 entry
    agents = obs.agent_status()
    assert any(a.get("agent") == "observer" for a in agents), (
        "observability did not pick up observer state"
    )


def check_control_plane_once() -> None:
    """Spawn `python3 -m core.control_plane start --once` as a subprocess.

    We run this as a subprocess rather than in-process so signal handling
    and thread lifecycle match how an operator actually runs it.
    """
    t0 = time.monotonic()
    proc = subprocess.run(
        [sys.executable, "-m", "core.control_plane", "start", "--once"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    dur = time.monotonic() - t0
    assert proc.returncode == 0, (
        f"control_plane exited {proc.returncode}\n"
        f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )
    assert "control_plane] started" in proc.stdout, (
        f"missing start banner\nstdout:\n{proc.stdout}"
    )
    print(f"    (control plane --once completed in {dur:.1f}s)")


def check_data_files() -> None:
    """The smoke run should have produced logs + state files on disk."""
    data = Path(_REPO_ROOT) / "data"
    must_exist = [
        data / "harness_log.jsonl",
        data / "persistent_agents_log.jsonl",
        data / "agent_state" / "observer.json",
        data / "optimizer_state.json",
        data / "control_plane_log.jsonl",
    ]
    missing = [str(p) for p in must_exist if not p.exists()]
    assert not missing, f"expected files missing: {missing}"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    print("EOS AI OS — smoke test")
    print("=" * 60)

    r = SmokeRunner()
    r.check("imports", check_imports)
    r.check("capability", check_capability)
    r.check("harness", check_harness)
    r.check("persistent_agents (observer)", check_persistent_agents)
    r.check("optimizer", check_optimizer)
    r.check("observability", check_observability)
    r.check("control_plane --once", check_control_plane_once)
    r.check("data files on disk", check_data_files)

    return r.summary()


if __name__ == "__main__":
    raise SystemExit(main())
