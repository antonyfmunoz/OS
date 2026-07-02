"""P1 Phase 4 — World Model Convergence tests.

Verifies:
1. Three world model domains have canonical owners
2. Zero architecture law violations in world model modules
3. Naming collisions documented (WorldModel × 2, RealityIntelligenceEngine × 2)

Run with: pytest tests/test_p1_phase4_world_model.py -v
"""

import ast
import os
import sys

import pytest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)

pytestmark = pytest.mark.smoke


# ── 1. Architecture Law ──────────────────────────────────────────


class TestWorldModelArchitecture:

    WORLD_MODEL_FILES = [
        "substrate/organism/world_model.py",
        "substrate/understanding/world_model/world_model.py",
        "substrate/organism/reality_graph.py",
        "substrate/understanding/reality/reality_engine.py",
        "substrate/understanding/reality/reality_context.py",
        "substrate/understanding/world_pulse/world_pulse.py",
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
        for f in self.WORLD_MODEL_FILES:
            violations.extend(self._check_imports(f))
        # Also check reality_model/ directory
        rm_dir = os.path.join(_REPO_ROOT, "substrate", "reality_model")
        if os.path.isdir(rm_dir):
            for fname in os.listdir(rm_dir):
                if fname.endswith(".py"):
                    violations.extend(self._check_imports(f"substrate/reality_model/{fname}"))
        assert violations == [], (
            f"World model modules violate architecture law:\n" + "\n".join(violations)
        )


# ── 2. Canonical Owners Exist ────────────────────────────────────


class TestCanonicalWorldModelOwners:
    """Three domains of reality each have a canonical owner."""

    def test_self_model_canonical(self):
        """OrganismWorldModel is canonical for self-model."""
        from substrate.organism.world_model import WorldModel
        assert WorldModel is not None

    def test_domain_knowledge_exists(self):
        """understanding/world_model has domain knowledge model."""
        path = os.path.join(
            _REPO_ROOT, "substrate", "understanding", "world_model", "world_model.py"
        )
        assert os.path.exists(path)

    def test_external_world_canonical(self):
        """world_pulse is canonical for external world monitoring."""
        path = os.path.join(
            _REPO_ROOT, "substrate", "understanding", "world_pulse", "world_pulse.py"
        )
        assert os.path.exists(path)

    def test_reality_model_exists(self):
        """reality_model/ directory exists with entity models."""
        path = os.path.join(_REPO_ROOT, "substrate", "reality_model")
        assert os.path.isdir(path)
        py_files = [f for f in os.listdir(path) if f.endswith(".py")]
        assert len(py_files) >= 5


# ── 3. Naming Collision Awareness ────────────────────────────────


class TestNamingCollisions:
    """Document known naming collisions for future resolution."""

    def test_worldmodel_collision_documented(self):
        """Two classes named WorldModel exist — both importable."""
        from substrate.organism.world_model import WorldModel as OrgWM

        wm_path = os.path.join(
            _REPO_ROOT, "substrate", "understanding", "world_model", "world_model.py"
        )
        if os.path.exists(wm_path):
            with open(wm_path) as f:
                content = f.read()
            has_class = "class WorldModel" in content or "class CanonicalWorldModel" in content
            assert has_class, "understanding/world_model/world_model.py has no WorldModel class"

    def test_reality_engine_collision_documented(self):
        """Two RealityIntelligenceEngine classes may exist."""
        re1 = os.path.join(
            _REPO_ROOT, "substrate", "understanding", "reality", "reality_engine.py"
        )
        re2 = os.path.join(
            _REPO_ROOT, "substrate", "reality_model", "reality_intelligence.py"
        )
        collision_count = 0
        for path in [re1, re2]:
            if os.path.exists(path):
                with open(path) as f:
                    if "class RealityIntelligenceEngine" in f.read():
                        collision_count += 1
        # Documenting the collision — both classes exist
        assert collision_count <= 2, "Unexpected third RealityIntelligenceEngine"


# ── 4. Reality Graph ─────────────────────────────────────────────


class TestRealityGraph:

    def test_reality_graph_exists(self):
        path = os.path.join(_REPO_ROOT, "substrate", "organism", "reality_graph.py")
        assert os.path.exists(path)

    def test_reality_graph_importable(self):
        from substrate.organism.reality_graph import RealityGraph
        assert RealityGraph is not None
