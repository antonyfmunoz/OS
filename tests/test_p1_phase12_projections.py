"""P1 Phase 12 — Projections & Nodes Convergence tests.

Verifies:
1. Projections and nodes exist with expected file counts
2. Projections import downward (from substrate/ and adapters/)
3. Nodes have work packet types

Run with: pytest tests/test_p1_phase12_projections.py -v
"""

import os
import sys

import pytest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)

pytestmark = pytest.mark.smoke


class TestProjectionInventory:

    def test_projections_dir_exists(self):
        path = os.path.join(_REPO_ROOT, "projections")
        assert os.path.isdir(path)

    def test_eos_projection_exists(self):
        path = os.path.join(_REPO_ROOT, "projections", "eos")
        assert os.path.isdir(path)

    def test_minimum_projection_files(self):
        proj_dir = os.path.join(_REPO_ROOT, "projections")
        count = sum(
            1 for root, _, files in os.walk(proj_dir)
            if "__pycache__" not in root
            for f in files if f.endswith(".py")
        )
        assert count >= 30, f"Expected >= 30 projection files, found {count}"


class TestNodeInventory:

    def test_nodes_dir_exists(self):
        path = os.path.join(_REPO_ROOT, "nodes")
        assert os.path.isdir(path)

    def test_windows_node_exists(self):
        path = os.path.join(_REPO_ROOT, "nodes", "windows")
        assert os.path.isdir(path)

    def test_environments_node_exists(self):
        path = os.path.join(_REPO_ROOT, "nodes", "environments")
        assert os.path.isdir(path)

    def test_work_packet_exists(self):
        path = os.path.join(_REPO_ROOT, "nodes", "environments", "work_packet.py")
        assert os.path.exists(path)


class TestProjectionDependencyDirection:

    def test_projections_dont_import_services(self):
        proj_dir = os.path.join(_REPO_ROOT, "projections")
        violations = []
        for root, dirs, files in os.walk(proj_dir):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for f in files:
                if not f.endswith(".py"):
                    continue
                path = os.path.join(root, f)
                with open(path) as fh:
                    content = fh.read()
                if "from services." in content:
                    rel = os.path.relpath(path, _REPO_ROOT)
                    violations.append(rel)
        assert violations == [], (
            f"Projections import from services/ (wrong direction):\n"
            + "\n".join(violations)
        )
