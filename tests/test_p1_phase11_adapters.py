"""P1 Phase 11 — Adapter Layer Convergence tests.

Verifies:
1. Adapter file count
2. No upward imports (services/, projections/)
3. Model routing is canonical

Run with: pytest tests/test_p1_phase11_adapters.py -v
"""

import ast
import os
import sys

import pytest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)

pytestmark = pytest.mark.smoke

ADAPTERS_DIR = os.path.join(_REPO_ROOT, "adapters")


class TestAdapterInventory:

    def test_adapter_dir_exists(self):
        assert os.path.isdir(ADAPTERS_DIR)

    def test_minimum_file_count(self):
        count = sum(
            1 for root, _, files in os.walk(ADAPTERS_DIR)
            if "__pycache__" not in root
            for f in files if f.endswith(".py")
        )
        assert count >= 90, f"Expected >= 90 adapter files, found {count}"

    def test_model_router_exists(self):
        path = os.path.join(ADAPTERS_DIR, "models", "model_router.py")
        assert os.path.exists(path)


class TestAdapterArchitecture:

    def test_no_services_imports(self):
        violations = []
        for root, dirs, files in os.walk(ADAPTERS_DIR):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
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
                        if node.module.startswith("services."):
                            violations.append(f"{rel}:{node.lineno}: from {node.module}")
        assert violations == [], (
            f"Adapter files import from services/ (upward):\n" + "\n".join(violations)
        )

    def test_no_projections_imports(self):
        violations = []
        for root, dirs, files in os.walk(ADAPTERS_DIR):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
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
                        if node.module.startswith("projections."):
                            violations.append(f"{rel}:{node.lineno}: from {node.module}")
        assert violations == [], (
            f"Adapter files import from projections/ (upward):\n" + "\n".join(violations)
        )


class TestSocketRegistration:

    def test_socket_registration_exists(self):
        path = os.path.join(ADAPTERS_DIR, "socket_registration.py")
        assert os.path.exists(path)
