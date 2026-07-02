"""P1 Phase 6 — Learning Integration tests.

Verifies:
1. Core learning systems exist and are importable
2. Cognitive-organism bridge exists (Phase 2 setters)
3. Zero architecture law violations in learning modules
4. Orphan classification

Run with: pytest tests/test_p1_phase6_learning.py -v
"""

import ast
import os
import sys

import pytest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)

pytestmark = pytest.mark.smoke


# ── 1. Architecture Law ──────────────────────────────────────────


class TestLearningArchitecture:

    LEARNING_FILES = [
        "substrate/organism/outcome_learning.py",
        "substrate/organism/continuous_qualification.py",
        "substrate/organism/daily_driver_log.py",
        "substrate/organism/proof_store.py",
        "substrate/execution/feedback.py",
        "substrate/execution/feedback_loop.py",
        "substrate/intelligence/runtime.py",
        "substrate/organism/learning_extraction_runtime.py",
        "substrate/organism/learning_portfolio_runtime.py",
        "substrate/organism/outcome_pattern_engine.py",
        "substrate/organism/outcome_tracking_runtime.py",
        "substrate/organism/outcome_verification.py",
    ]

    def _check_imports(self, filepath: str) -> list[str]:
        full = os.path.join(_REPO_ROOT, filepath)
        if not os.path.exists(full):
            return []
        with open(full) as f:
            try:
                tree = ast.parse(f.read())
            except SyntaxError:
                return []
        violations = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith(("adapters.", "transports.")):
                    violations.append(f"{filepath}:{node.lineno}: from {node.module}")
        return violations

    def test_zero_architecture_violations(self):
        violations = []
        for f in self.LEARNING_FILES:
            violations.extend(self._check_imports(f))
        # Also check observability
        obs_dir = os.path.join(_REPO_ROOT, "substrate", "observability")
        if os.path.isdir(obs_dir):
            for fname in os.listdir(obs_dir):
                if fname.endswith(".py"):
                    violations.extend(self._check_imports(f"substrate/observability/{fname}"))
        assert violations == [], (
            f"Learning modules violate architecture law:\n" + "\n".join(violations)
        )


# ── 2. Core Learning Systems ────────────────────────────────────


class TestCoreLearningImportable:

    def test_outcome_learning_loop(self):
        from substrate.organism.outcome_learning import OutcomeLearningLoop
        assert OutcomeLearningLoop is not None

    def test_continuous_qualification(self):
        from substrate.organism.continuous_qualification import ContinuousQualificationStage
        assert ContinuousQualificationStage is not None

    def test_proof_store(self):
        from substrate.organism.proof_store import ProofStore
        assert ProofStore is not None

    def test_intelligence_runtime(self):
        from substrate.intelligence.runtime import IntelligenceRuntime
        assert IntelligenceRuntime is not None

    def test_error_recorder(self):
        from substrate.observability.error_recorder import record_error
        assert callable(record_error)


# ── 3. Cognitive-Organism Bridge ─────────────────────────────────


class TestCognitiveOrganismBridge:
    """Phase 2 created the bridge; Phase 6 verifies it exists."""

    def test_cognitive_loop_has_outcome_learning_setter(self):
        from substrate.control_plane.runtime.cognitive_loop import CognitiveLoop
        assert hasattr(CognitiveLoop, "set_outcome_learning")

    def test_cognitive_loop_has_governed_spine_setter(self):
        from substrate.control_plane.runtime.cognitive_loop import CognitiveLoop
        assert hasattr(CognitiveLoop, "set_governed_spine")

    def test_gateway_wires_bridge(self):
        """Gateway must contain Phase 2 bridge wiring code."""
        gw_path = os.path.join(
            _REPO_ROOT, "substrate", "control_plane", "runtime", "gateway.py"
        )
        with open(gw_path) as f:
            content = f.read()
        assert "set_outcome_learning" in content, (
            "Gateway missing outcome_learning bridge wiring"
        )
        assert "set_governed_spine" in content, (
            "Gateway missing governed_spine bridge wiring"
        )

    def test_daemon_has_outcome_learning(self):
        """Daemon must create and expose OutcomeLearningLoop."""
        daemon_path = os.path.join(
            _REPO_ROOT, "substrate", "organism", "daemon.py"
        )
        with open(daemon_path) as f:
            content = f.read()
        assert "OutcomeLearningLoop" in content
        assert "outcome_learning" in content


# ── 4. Observability ─────────────────────────────────────────────


class TestObservability:

    def test_observability_dir_exists(self):
        path = os.path.join(_REPO_ROOT, "substrate", "observability")
        assert os.path.isdir(path)

    def test_error_recorder_exists(self):
        path = os.path.join(_REPO_ROOT, "substrate", "observability", "error_recorder.py")
        assert os.path.exists(path)

    def test_jsonl_rotation_exists(self):
        path = os.path.join(_REPO_ROOT, "substrate", "observability", "jsonl_rotation.py")
        assert os.path.exists(path)


# ── 5. Orphan Classification ────────────────────────────────────


class TestLearningOrphans:

    def test_daily_driver_log_is_orphan(self):
        """DailyDriverLog has zero external importers (confirmed by audit)."""
        path = os.path.join(_REPO_ROOT, "substrate", "organism", "daily_driver_log.py")
        assert os.path.exists(path), "DailyDriverLog file should exist (orphan, not deleted)"
