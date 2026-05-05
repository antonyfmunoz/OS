"""Phase 14 validation — eos/ fully collapsed into UMH.

Proves that:
1. eos/ directory no longer exists
2. No eos. or eos_ai. imports remain in UMH
3. UMH is self-sufficient — all modules importable
4. No services/interfaces imports in UMH core
"""

from __future__ import annotations

import ast
import os
import sys

import pytest

sys.path.insert(0, "/opt/OS")

UMH_ROOT = "/opt/OS/umh"


class TestEosDirectoryDeleted:
    """eos/ must not exist after Phase 14 collapse."""

    def test_eos_directory_gone(self):
        assert not os.path.exists("/opt/OS/eos"), "eos/ directory still exists"

    def test_eos_ai_directory_gone(self):
        assert not os.path.exists("/opt/OS/eos_ai"), "eos_ai/ directory still exists"


class TestNoLegacyImportsInUMH:
    """No eos. or eos_ai. imports may exist in UMH."""

    def _collect_umh_files(self):
        files = []
        for root, dirs, filenames in os.walk(UMH_ROOT):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for f in filenames:
                if f.endswith(".py"):
                    files.append(os.path.join(root, f))
        return sorted(files)

    def test_no_eos_imports(self):
        violations = []
        for filepath in self._collect_umh_files():
            tree = ast.parse(open(filepath).read())
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    if node.module.startswith(("eos.", "eos_ai.")):
                        rel = filepath.replace("/opt/OS/", "")
                        violations.append(f"{rel}:{node.lineno} → {node.module}")
        assert violations == [], "Legacy imports found:\n" + "\n".join(violations)

    def test_no_external_imports(self):
        violations = []
        for filepath in self._collect_umh_files():
            if "/interfaces/" in filepath:
                continue
            tree = ast.parse(open(filepath).read())
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    if node.module.startswith(("services.", "interfaces.")):
                        rel = filepath.replace("/opt/OS/", "")
                        violations.append(f"{rel}:{node.lineno} → {node.module}")
        assert violations == [], "External imports in UMH:\n" + "\n".join(violations)


class TestUMHSelfSufficient:
    """Core UMH subpackages must be importable."""

    @pytest.mark.parametrize("module", [
        "umh.primitives.ontological",
        "umh.world.types",
        "umh.world.reasoning",
        "umh.world.calibration",
        "umh.world.state",
        "umh.memory.storage",
        "umh.decision.trace",
        "umh.goals.state",
        "umh.goals.objective",
        "umh.strategy.memory",
    ])
    def test_core_module_imports(self, module):
        __import__(module)


class TestUMHCompiles:
    """All UMH Python files must compile without syntax errors."""

    def test_all_files_compile(self):
        import py_compile

        errors = []
        for root, dirs, files in os.walk(UMH_ROOT):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for f in files:
                if f.endswith(".py"):
                    path = os.path.join(root, f)
                    try:
                        py_compile.compile(path, doraise=True)
                    except py_compile.PyCompileError as e:
                        errors.append(str(e))
        assert errors == [], f"{len(errors)} compile errors:\n" + "\n".join(errors)
