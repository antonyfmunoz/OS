"""P1 Phase 8 — Capability Closure tests.

Verifies:
1. All 19 substrate subdirectories exist
2. Governance modules are importable
3. Contracts include canonical agent_types
4. Integrations are clean post-Phase 9

Run with: pytest tests/test_p1_phase8_closure.py -v
"""

import os
import sys

import pytest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)

pytestmark = pytest.mark.smoke


EXPECTED_SUBDIRS = [
    "composition", "contracts", "control_plane", "execution",
    "foundation", "governance", "integrations", "intelligence",
    "memory", "meta_ide", "observability", "ontology", "operator",
    "organism", "reality_model", "sockets", "state",
    "understanding", "workstation",
]


class TestSubstrateCompleteness:

    def test_all_19_subdirectories_exist(self):
        missing = []
        for d in EXPECTED_SUBDIRS:
            path = os.path.join(_REPO_ROOT, "substrate", d)
            if not os.path.isdir(path):
                missing.append(d)
        assert missing == [], f"Missing substrate subdirectories: {missing}"

    def test_subdirectory_count(self):
        sub_dir = os.path.join(_REPO_ROOT, "substrate")
        dirs = [
            d for d in os.listdir(sub_dir)
            if os.path.isdir(os.path.join(sub_dir, d))
            and d not in ("__pycache__", ".pytest_cache", "_dormant", "tests")
        ]
        assert len(dirs) >= 19, f"Expected >= 19 substrate subdirs, found {len(dirs)}: {sorted(dirs)}"


class TestGovernanceModules:

    def test_authority_engine_importable(self):
        from substrate.governance.policy.authority_engine import AuthorityEngine
        assert AuthorityEngine is not None

    def test_risk_classes_importable(self):
        path = os.path.join(_REPO_ROOT, "substrate", "governance", "risk_classes.py")
        assert os.path.exists(path)


class TestContracts:

    def test_agent_types_canonical(self):
        from substrate.contracts.agent_types import TaskType
        assert TaskType is not None

    def test_contracts_dir_exists(self):
        path = os.path.join(_REPO_ROOT, "substrate", "contracts")
        py_files = [f for f in os.listdir(path) if f.endswith(".py") and f != "__init__.py"]
        assert len(py_files) >= 5, f"Expected >= 5 contract files, found {len(py_files)}"


class TestIntegrations:

    def test_integrations_no_architecture_violations(self):
        import ast
        integ_dir = os.path.join(_REPO_ROOT, "substrate", "integrations")
        violations = []
        for f in os.listdir(integ_dir):
            if not f.endswith(".py"):
                continue
            path = os.path.join(integ_dir, f)
            with open(path) as fh:
                try:
                    tree = ast.parse(fh.read())
                except SyntaxError:
                    continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    if node.module.startswith(("adapters.", "transports.")):
                        violations.append(f"integrations/{f}:{node.lineno}: from {node.module}")
        assert violations == [], f"Integration violations:\n" + "\n".join(violations)


class TestGovernedExecutionSpine:

    def test_spine_exists(self):
        from substrate.organism.governed_spine import GovernedExecutionSpine
        assert GovernedExecutionSpine is not None
        assert hasattr(GovernedExecutionSpine, "submit")
