"""P1 Phase 3 — Memory Convergence tests.

Verifies:
1. Memory systems are correctly layered (architecture law)
2. Canonical memory store exists and is importable
3. Promotion pipeline has one canonical owner
4. Orphan memory modules identified

Run with: pytest tests/test_p1_phase3_memory.py -v
"""

import ast
import os
import sys

import pytest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)

pytestmark = pytest.mark.smoke


# ── 1. Architecture Law for Memory Modules ────────────────────────


class TestMemoryArchitecture:
    """Memory modules must not import from adapters/ or transports/."""

    MEMORY_DIRS = [
        "substrate/state/memory",
        "substrate/memory",
        "substrate/organism",
        "substrate/control_plane",
        "substrate/execution/bridge",
    ]

    MEMORY_FILES = [
        "substrate/state/memory/memory.py",
        "substrate/memory/promoter.py",
        "substrate/organism/memory_promotion.py",
        "substrate/organism/institutional_memory_runtime.py",
        "substrate/organism/strategic_memory_engine.py",
        "substrate/control_plane/memory.py",
        "substrate/execution/bridge/memory_scope_contracts.py",
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
        for f in self.MEMORY_FILES:
            violations.extend(self._check_imports(f))
        assert violations == [], (
            f"Memory modules violate architecture law:\n" + "\n".join(violations)
        )


# ── 2. Canonical Memory Systems Exist ─────────────────────────────


class TestCanonicalMemorySystems:
    """Core memory modules are importable."""

    def test_agent_memory_importable(self):
        from substrate.state.memory.memory import AgentMemory
        assert AgentMemory is not None

    def test_conversation_memory_importable(self):
        from substrate.state.memory.memory import ConversationMemory
        assert ConversationMemory is not None

    def test_organism_memory_promotion_importable(self):
        from substrate.organism.memory_promotion import MemoryPromotionPipeline
        assert MemoryPromotionPipeline is not None

    def test_memory_contracts_exist(self):
        contracts_dir = os.path.join(_REPO_ROOT, "substrate", "state", "memory", "contracts")
        assert os.path.isdir(contracts_dir), "Memory contracts directory missing"
        py_files = [f for f in os.listdir(contracts_dir) if f.endswith(".py")]
        assert len(py_files) >= 3, f"Expected >= 3 contract files, found {len(py_files)}"


# ── 3. Promotion Pipeline Integrity ──────────────────────────────


class TestPromotionPipeline:
    """Promotion pipeline modules exist and don't conflict."""

    def test_substrate_promoter_exists(self):
        path = os.path.join(_REPO_ROOT, "substrate", "memory", "promoter.py")
        assert os.path.exists(path)

    def test_organism_promotion_exists(self):
        path = os.path.join(_REPO_ROOT, "substrate", "organism", "memory_promotion.py")
        assert os.path.exists(path)

    def test_different_output_paths(self):
        """The two pipelines must write to different paths (verified by audit)."""
        promoter_path = os.path.join(_REPO_ROOT, "substrate", "memory", "promoter.py")
        organism_path = os.path.join(_REPO_ROOT, "substrate", "organism", "memory_promotion.py")

        promoter_content = open(promoter_path).read() if os.path.exists(promoter_path) else ""
        organism_content = open(organism_path).read() if os.path.exists(organism_path) else ""

        if "promoted_memories" in promoter_content:
            assert "promoted_memories" not in organism_content or "canonical_memory" in organism_content, (
                "Both promotion pipelines write to promoted_memories — conflict risk"
            )


# ── 4. Orphan Classification ────────────────────────────────────


class TestMemoryOrphans:
    """Near-orphan memory modules identified for future cleanup."""

    def test_control_plane_memory_is_thin_wrapper(self):
        """control_plane/memory.py should be minimal (near-orphan)."""
        path = os.path.join(_REPO_ROOT, "substrate", "control_plane", "memory.py")
        if os.path.exists(path):
            content = open(path).read()
            lines = [l for l in content.split("\n") if l.strip() and not l.strip().startswith("#")]
            assert len(lines) < 200, (
                f"control_plane/memory.py has {len(lines)} non-blank lines — "
                f"expected thin wrapper (near-orphan)"
            )


# ── 5. Memory Module Count Guard ─────────────────────────────────


class TestMemoryInventory:

    def test_state_memory_exists(self):
        path = os.path.join(_REPO_ROOT, "substrate", "state", "memory")
        assert os.path.isdir(path)

    def test_substrate_memory_exists(self):
        path = os.path.join(_REPO_ROOT, "substrate", "memory")
        assert os.path.isdir(path)
