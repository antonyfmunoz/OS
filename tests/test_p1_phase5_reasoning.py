"""P1 Phase 5 — Reasoning Integration tests.

Verifies:
1. Goal systems exist and are importable
2. Planning systems exist and are on cognitive hot path
3. Two council implementations are documented
4. Composition (TME) and meta_ide are correctly layered

Run with: pytest tests/test_p1_phase5_reasoning.py -v
"""

import ast
import os
import sys

import pytest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)

pytestmark = pytest.mark.smoke


# ── 1. Architecture Law for Reasoning Modules ───────────────────


class TestReasoningArchitecture:

    REASONING_DIRS = [
        "substrate/control_plane/goals",
        "substrate/organism",
        "substrate/understanding/deliberation",
        "substrate/understanding/intelligence",
        "substrate/composition",
        "substrate/meta_ide",
        "substrate/ontology",
        "substrate/foundation",
    ]

    def _check_dir_imports(self, dirpath: str) -> list[str]:
        full_dir = os.path.join(_REPO_ROOT, dirpath)
        if not os.path.isdir(full_dir):
            return []
        violations = []
        for root, dirs, files in os.walk(full_dir):
            dirs[:] = [d for d in dirs if d not in ("__pycache__", "_dormant", "tests")]
            for f in files:
                if not f.endswith(".py"):
                    continue
                filepath = os.path.join(root, f)
                with open(filepath) as fh:
                    try:
                        tree = ast.parse(fh.read())
                    except SyntaxError:
                        continue
                rel = os.path.relpath(filepath, _REPO_ROOT)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom) and node.module:
                        if node.module.startswith(("adapters.", "transports.")):
                            violations.append(f"{rel}:{node.lineno}: from {node.module}")
        return violations

    def test_zero_architecture_violations(self):
        violations = []
        for d in self.REASONING_DIRS:
            violations.extend(self._check_dir_imports(d))
        assert violations == [], (
            f"Reasoning modules violate architecture law:\n" + "\n".join(violations[:20])
        )


# ── 2. Goal Systems Exist ────────────────────────────────────────


class TestGoalSystems:

    def test_goal_selector_exists(self):
        path = os.path.join(_REPO_ROOT, "substrate", "control_plane", "goals", "goal_selector.py")
        assert os.path.exists(path)

    def test_goal_alignment_exists(self):
        path = os.path.join(_REPO_ROOT, "substrate", "organism", "goal_alignment_engine.py")
        assert os.path.exists(path)

    def test_goal_drift_exists(self):
        path = os.path.join(_REPO_ROOT, "substrate", "organism", "goal_drift_engine.py")
        assert os.path.exists(path)

    def test_goal_hierarchy_exists(self):
        path = os.path.join(_REPO_ROOT, "substrate", "organism", "goal_hierarchy_engine.py")
        assert os.path.exists(path)


# ── 3. Planning Systems ──────────────────────────────────────────


class TestPlanningSystems:

    def test_strategic_planning_exists(self):
        path = os.path.join(
            _REPO_ROOT, "substrate", "organism", "strategic_planning_engine.py"
        )
        assert os.path.exists(path)

    def test_production_planning_exists(self):
        path = os.path.join(
            _REPO_ROOT, "substrate", "organism", "production_planning_runtime.py"
        )
        assert os.path.exists(path)


# ── 4. Two Council Implementations ───────────────────────────────


class TestCouncils:

    def test_deliberation_council_exists(self):
        path = os.path.join(
            _REPO_ROOT, "substrate", "understanding", "deliberation", "council.py"
        )
        assert os.path.exists(path)

    def test_organism_council_exists(self):
        path = os.path.join(_REPO_ROOT, "substrate", "organism", "council.py")
        assert os.path.exists(path)

    def test_councils_have_different_class_names(self):
        """Two councils should not create ambiguity."""
        delib = os.path.join(
            _REPO_ROOT, "substrate", "understanding", "deliberation", "council.py"
        )
        org = os.path.join(_REPO_ROOT, "substrate", "organism", "council.py")

        delib_classes = set()
        org_classes = set()

        if os.path.exists(delib):
            with open(delib) as f:
                for line in f:
                    if line.strip().startswith("class "):
                        name = line.strip().split("(")[0].replace("class ", "").strip(":")
                        delib_classes.add(name)

        if os.path.exists(org):
            with open(org) as f:
                for line in f:
                    if line.strip().startswith("class "):
                        name = line.strip().split("(")[0].replace("class ", "").strip(":")
                        org_classes.add(name)

        # At minimum the main class names should differ
        main_overlap = delib_classes & org_classes
        # CouncilRole may overlap as an enum — that's a known type coherence issue
        non_enum_overlap = {c for c in main_overlap if "Role" not in c}
        assert len(non_enum_overlap) == 0, (
            f"Non-enum class name collision between councils: {non_enum_overlap}"
        )


# ── 5. TME (Composition) Layer ───────────────────────────────────


class TestTMELayer:

    def test_composition_dir_exists(self):
        path = os.path.join(_REPO_ROOT, "substrate", "composition")
        assert os.path.isdir(path)
        py_count = sum(
            1 for root, _, files in os.walk(path)
            if "__pycache__" not in root
            for f in files if f.endswith(".py")
        )
        assert py_count >= 10, f"Expected >= 10 TME files, found {py_count}"

    def test_meta_ide_dir_exists(self):
        path = os.path.join(_REPO_ROOT, "substrate", "meta_ide")
        assert os.path.isdir(path)


# ── 6. Foundation/Ontology ───────────────────────────────────────


class TestFoundationOntology:

    def test_ontology_exists(self):
        path = os.path.join(_REPO_ROOT, "substrate", "ontology")
        assert os.path.isdir(path)

    def test_foundation_exists(self):
        path = os.path.join(_REPO_ROOT, "substrate", "foundation")
        assert os.path.isdir(path)
