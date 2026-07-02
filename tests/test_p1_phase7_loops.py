"""P1 Phase 7 — Autonomous Operation tests.

Verifies:
1. Daemon tick stages are registered
2. Non-daemon loops classified
3. Zero architecture violations in loop modules

Run with: pytest tests/test_p1_phase7_loops.py -v
"""

import os
import sys

import pytest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)

pytestmark = pytest.mark.smoke


class TestDaemonTickStages:

    def test_daemon_has_register_stages(self):
        path = os.path.join(_REPO_ROOT, "substrate", "organism", "daemon.py")
        with open(path) as f:
            content = f.read()
        assert "register_stage" in content
        assert "_register_tick_stages" in content

    def test_at_least_18_tick_stages(self):
        path = os.path.join(_REPO_ROOT, "substrate", "organism", "daemon.py")
        with open(path) as f:
            content = f.read()
        stage_count = content.count("register_stage(")
        assert stage_count >= 18, f"Expected >= 18 tick stages, found {stage_count}"


class TestNonDaemonLoops:

    ORPHAN_LOOPS = [
        "substrate/organism/orchestration_loop.py",
        "substrate/organism/operator_loop_runtime.py",
        "substrate/organism/operating_loop_coherence_runtime.py",
        "substrate/workstation/loop_engine.py",
    ]

    ACTIVE_LOOPS = [
        "substrate/organism/strategic_tick_loop.py",
        "substrate/execution/loop/persistent_loop.py",
    ]

    def test_orphan_loops_exist(self):
        for loop in self.ORPHAN_LOOPS:
            path = os.path.join(_REPO_ROOT, loop)
            assert os.path.exists(path), f"Orphan loop missing: {loop}"

    def test_active_loops_exist(self):
        for loop in self.ACTIVE_LOOPS:
            path = os.path.join(_REPO_ROOT, loop)
            assert os.path.exists(path), f"Active loop missing: {loop}"

    def test_active_loops_dont_import_daemon(self):
        """Active non-daemon loops should not circularly import daemon."""
        for loop in self.ACTIVE_LOOPS:
            path = os.path.join(_REPO_ROOT, loop)
            if os.path.exists(path):
                with open(path) as f:
                    content = f.read()
                assert "from substrate.organism.daemon import" not in content, (
                    f"{loop} imports daemon — circular dependency"
                )
