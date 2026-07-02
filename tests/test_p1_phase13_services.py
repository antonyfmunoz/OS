"""P1 Phase 13 — Services, Scripts & Tests Convergence tests.

Verifies:
1. Service entrypoints exist
2. Discord bot routes through gateway
3. Pre-commit gates are present
4. Test count matches expectations

Run with: pytest tests/test_p1_phase13_services.py -v
"""

import os
import sys

import pytest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)

pytestmark = pytest.mark.smoke


class TestServiceEntrypoints:

    def test_services_dir_exists(self):
        path = os.path.join(_REPO_ROOT, "services")
        assert os.path.isdir(path)

    def test_discord_bot_exists(self):
        path = os.path.join(_REPO_ROOT, "services", "discord_bot.py")
        assert os.path.exists(path)

    def test_discord_bot_uses_gateway(self):
        path = os.path.join(_REPO_ROOT, "services", "discord_bot.py")
        with open(path) as f:
            content = f.read()
        assert "Gateway" in content or "gateway" in content, (
            "discord_bot.py doesn't reference Gateway — may bypass cognitive pipeline"
        )


class TestPreCommitGates:

    EXPECTED_GATES = [
        "scripts/check_cpu_gate.py",
        "scripts/check_dependency_direction.py",
        "scripts/check_projection_leak.py",
        "scripts/check_type_divergence.py",
        "scripts/check_instance_leak.py",
        "scripts/check_credential_injection.py",
    ]

    def test_gates_exist(self):
        missing = []
        for gate in self.EXPECTED_GATES:
            path = os.path.join(_REPO_ROOT, gate)
            if not os.path.exists(path):
                missing.append(gate)
        assert missing == [], f"Missing pre-commit gates: {missing}"


class TestScriptsInventory:

    def test_scripts_dir_exists(self):
        path = os.path.join(_REPO_ROOT, "scripts")
        assert os.path.isdir(path)

    def test_minimum_script_count(self):
        scripts_dir = os.path.join(_REPO_ROOT, "scripts")
        count = sum(
            1 for root, _, files in os.walk(scripts_dir)
            if "__pycache__" not in root
            for f in files if f.endswith(".py")
        )
        assert count >= 100, f"Expected >= 100 script files, found {count}"


class TestTestsInventory:

    def test_tests_dir_exists(self):
        path = os.path.join(_REPO_ROOT, "tests")
        assert os.path.isdir(path)

    def test_minimum_test_count(self):
        tests_dir = os.path.join(_REPO_ROOT, "tests")
        count = sum(
            1 for f in os.listdir(tests_dir)
            if f.endswith(".py") and f.startswith("test_")
        )
        assert count >= 20, f"Expected >= 20 test files, found {count}"

    def test_no_stale_dormant_imports(self):
        tests_dir = os.path.join(_REPO_ROOT, "tests")
        violations = []
        for f in os.listdir(tests_dir):
            if not f.endswith(".py"):
                continue
            if f == "test_p1_phase13_services.py":
                continue
            path = os.path.join(tests_dir, f)
            with open(path) as fh:
                for i, line in enumerate(fh, 1):
                    stripped = line.strip()
                    if stripped.startswith("from ") and "_dormant" in stripped:
                        violations.append(f"tests/{f}:{i}: {stripped}")
        assert violations == [], (
            f"Tests import from _dormant modules:\n" + "\n".join(violations)
        )
