"""Sprint 3 — Test Recovery verification.

Validates that all Sprint 3 fixes are in place:
  - Mock paths reference adapters.models.model_router (not stale substrate path)
  - Integration mark is registered
  - Reconciliation receipt test handles empty directories gracefully
"""

from __future__ import annotations

import ast
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.environ.get("UMH_ROOT") or "/opt/OS")

REPO = Path(__file__).resolve().parents[1]
TEST_DIR = REPO / "tests"

FIXED_TEST_FILES = [
    "test_authority_tier.py",
    "test_domain_bridge.py",
    "test_decomposer_depth.py",
    "test_persist_all_observations.py",
    "test_capability_extraction_slice_b.py",
]

STALE_MOCK_PATH = "substrate.execution.runtime.model_router"
CORRECT_MOCK_PATH = "adapters.models.model_router"


class TestMockPathsFixed:
    """No test file should reference the stale substrate mock path."""

    @pytest.mark.parametrize("filename", FIXED_TEST_FILES)
    def test_no_stale_mock_path(self, filename: str):
        path = TEST_DIR / filename
        if not path.exists():
            pytest.skip(f"{filename} not found")
        source = path.read_text()
        assert STALE_MOCK_PATH not in source, (
            f"{filename} still references stale mock path '{STALE_MOCK_PATH}'"
        )

    @pytest.mark.parametrize("filename", FIXED_TEST_FILES)
    def test_correct_mock_path_present(self, filename: str):
        path = TEST_DIR / filename
        if not path.exists():
            pytest.skip(f"{filename} not found")
        source = path.read_text()
        assert CORRECT_MOCK_PATH in source, (
            f"{filename} missing correct mock path '{CORRECT_MOCK_PATH}'"
        )


class TestIntegrationMarkRegistered:
    def test_pyproject_has_integration_marker(self):
        pyproject = REPO / "pyproject.toml"
        content = pyproject.read_text()
        assert "integration" in content
        assert "markers" in content


class TestReconciliationReceiptTestRobust:
    def test_receipt_test_has_skip_for_empty(self):
        path = TEST_DIR / "test_canonical_memory_reconciliation_v1.py"
        if not path.exists():
            pytest.skip("Reconciliation test file not found")
        source = path.read_text()
        assert "No reconciliation receipts generated yet" in source
