"""P1 Phase 14 — Cockpit UI Convergence tests.

Verifies:
1. Cockpit TypeScript source exists with expected file count
2. No dead panels calling dormant modules
3. Device naming protocol compliance

Run with: pytest tests/test_p1_phase14_cockpit.py -v
"""

import os

import pytest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

pytestmark = pytest.mark.smoke

COCKPIT_DIR = os.path.join(_REPO_ROOT, "cockpit")
COCKPIT_SRC = os.path.join(COCKPIT_DIR, "src")


class TestCockpitInventory:

    def test_cockpit_dir_exists(self):
        assert os.path.isdir(COCKPIT_DIR)

    def test_cockpit_src_exists(self):
        assert os.path.isdir(COCKPIT_SRC)

    def test_minimum_ts_file_count(self):
        count = sum(
            1 for root, _, files in os.walk(COCKPIT_SRC)
            if "node_modules" not in root and "dist" not in root
            for f in files if f.endswith((".ts", ".tsx"))
        )
        assert count >= 250, f"Expected >= 250 TS files, found {count}"

    def test_package_json_exists(self):
        path = os.path.join(COCKPIT_DIR, "package.json")
        assert os.path.exists(path)


class TestCockpitHealth:

    def test_no_dormant_api_calls(self):
        violations = []
        for root, dirs, files in os.walk(COCKPIT_SRC):
            dirs[:] = [d for d in dirs if d not in ("node_modules", "dist")]
            for f in files:
                if not f.endswith((".ts", ".tsx")):
                    continue
                path = os.path.join(root, f)
                with open(path) as fh:
                    for i, line in enumerate(fh, 1):
                        if "_dormant" in line.lower():
                            rel = os.path.relpath(path, _REPO_ROOT)
                            violations.append(f"{rel}:{i}: {line.strip()[:80]}")
        assert violations == [], (
            f"Cockpit files reference _dormant modules:\n" + "\n".join(violations)
        )

    def test_device_constants_file_exists(self):
        path = os.path.join(
            COCKPIT_SRC, "renderer", "constants", "devices.ts"
        )
        assert os.path.exists(path), (
            "Missing cockpit/src/renderer/constants/devices.ts — "
            "device naming protocol requires this file"
        )
