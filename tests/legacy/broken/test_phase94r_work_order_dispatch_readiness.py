"""
Dispatch readiness tests for Phase 94R.

Tests that the dispatch package builds correctly, validates properly,
enforces safety, and never calls network or executes actions.

Additive-only — does not test or modify any existing substrate module.
"""

import sys
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, "/opt/OS")

from runtime.substrate.work_order_contracts import (
    UNIVERSAL_BLOCKED_ACTIONS,
    WorkOrderStatus,
    WorkOrderTaskType,
)
from runtime.substrate.work_order_dispatch import (
    DispatchPackage,
    DispatchReadiness,
    ReadinessCheck,
    assess_readiness,
    build_dispatch_package,
    check_contract_readiness,
    check_local_healthcheck_status,
    check_vps_file_readiness,
    save_dispatch_package,
)


def test_dispatch_package_builds():
    """Dispatch package can be built without errors."""
    package = build_dispatch_package(local_healthcheck_passed=False)
    assert isinstance(package, DispatchPackage)
    assert package.work_order is not None
    assert package.work_order.work_order_id.startswith("wo_")
    assert package.payload is not None
    assert isinstance(package.readiness_checks, list)
    assert len(package.readiness_checks) > 0
    assert package.created_at is not None


def test_work_order_validates():
    """Factory-built work order has no validation errors."""
    package = build_dispatch_package()
    assert package.validation_errors == [], f"Unexpected errors: {package.validation_errors}"


def test_blocked_actions_preserved():
    """All 16 universal blocked actions are in the dispatch package."""
    package = build_dispatch_package()
    wo_blocked = set(package.work_order.blocked_actions)
    for action in UNIVERSAL_BLOCKED_ACTIONS:
        assert action in wo_blocked, f"Missing blocked action: {action}"
    assert len(wo_blocked) >= 16


def test_no_network_calls():
    """Build does not call requests or any network library."""
    with patch("requests.get") as mock_get, patch("requests.post") as mock_post:
        package = build_dispatch_package()
        mock_get.assert_not_called()
        mock_post.assert_not_called()
    assert package is not None


def test_no_execution():
    """Work order status remains CREATED — nothing is executed."""
    package = build_dispatch_package()
    assert package.work_order.status == WorkOrderStatus.CREATED
    assert package.work_order.claimed_at is None
    assert package.work_order.completed_at is None


def test_output_serializes():
    """Dispatch package serializes to valid JSON."""
    package = build_dispatch_package()
    d = package.to_dict()
    json_str = json.dumps(d)
    parsed = json.loads(json_str)
    assert parsed["work_order"]["work_order_id"] == package.work_order.work_order_id
    assert parsed["readiness"] in [r.value for r in DispatchReadiness]
    assert isinstance(parsed["readiness_checks"], list)


def test_missing_local_healthcheck_prevents_ready_to_dispatch():
    """Without local healthcheck, status cannot be READY_TO_DISPATCH."""
    package = build_dispatch_package(local_healthcheck_passed=False)
    assert package.readiness != DispatchReadiness.READY_TO_DISPATCH


def test_readiness_ready_after_local_healthcheck():
    """With all VPS checks passing but no local healthcheck, status is READY_AFTER_LOCAL_HEALTHCHECK."""
    package = build_dispatch_package(local_healthcheck_passed=False)
    vps_and_contract_pass = all(
        c.passed for c in package.readiness_checks if not c.name.startswith("local:")
    )
    if vps_and_contract_pass:
        assert package.readiness == DispatchReadiness.READY_AFTER_LOCAL_HEALTHCHECK


def test_readiness_ready_to_dispatch_with_local():
    """With local healthcheck passed and all files present, status is READY_TO_DISPATCH."""
    package = build_dispatch_package(local_healthcheck_passed=True)
    all_pass = all(c.passed for c in package.readiness_checks)
    if all_pass:
        assert package.readiness == DispatchReadiness.READY_TO_DISPATCH


def test_assess_readiness_all_pass():
    """All checks passing yields READY_TO_DISPATCH."""
    checks = [
        ReadinessCheck("file:a", True, "ok"),
        ReadinessCheck("factory:build", True, "ok"),
        ReadinessCheck("local:healthcheck", True, "ok"),
    ]
    assert assess_readiness(checks) == DispatchReadiness.READY_TO_DISPATCH


def test_assess_readiness_local_only_fail():
    """Only local checks failing yields READY_AFTER_LOCAL_HEALTHCHECK."""
    checks = [
        ReadinessCheck("file:a", True, "ok"),
        ReadinessCheck("factory:build", True, "ok"),
        ReadinessCheck("local:healthcheck", False, "not run"),
    ]
    assert assess_readiness(checks) == DispatchReadiness.READY_AFTER_LOCAL_HEALTHCHECK


def test_assess_readiness_file_missing():
    """Missing file yields NEEDS_REPAIR."""
    checks = [
        ReadinessCheck("file:missing.py", False, "MISSING"),
        ReadinessCheck("local:healthcheck", True, "ok"),
    ]
    assert assess_readiness(checks) == DispatchReadiness.NEEDS_REPAIR


def test_assess_readiness_contract_broken():
    """Broken contract yields NEEDS_REPAIR."""
    checks = [
        ReadinessCheck("file:a", True, "ok"),
        ReadinessCheck("factory:build", False, "import error"),
        ReadinessCheck("local:healthcheck", True, "ok"),
    ]
    assert assess_readiness(checks) == DispatchReadiness.NEEDS_REPAIR


def test_vps_file_checks():
    """VPS file checks return results for all required files."""
    checks = check_vps_file_readiness()
    assert len(checks) >= 8
    for c in checks:
        assert c.name.startswith("file:")


def test_contract_checks():
    """Contract checks verify build, validate, safety, and serialization."""
    checks = check_contract_readiness()
    names = {c.name for c in checks}
    assert "factory:build" in names
    assert "factory:validate" in names
    assert "safety:blocked_actions" in names
    assert "serialization:payload" in names


def test_local_healthcheck_default_false():
    """Local healthcheck defaults to not passed."""
    checks = check_local_healthcheck_status()
    assert len(checks) == 1
    assert not checks[0].passed


def test_local_healthcheck_explicit_true():
    """Local healthcheck can be explicitly set to passed."""
    checks = check_local_healthcheck_status(local_healthcheck_passed=True)
    assert len(checks) == 1
    assert checks[0].passed


def test_save_dispatch_package():
    """Dispatch package can be saved to disk."""
    package = build_dispatch_package()
    with tempfile.TemporaryDirectory() as tmpdir:
        path = save_dispatch_package(package, directory=tmpdir)
        assert path.exists()
        assert path.name.endswith("_dispatch.json")
        data = json.loads(path.read_text())
        assert data["work_order"]["work_order_id"] == package.work_order.work_order_id


def test_work_order_task_type():
    """Dispatch package has correct task type."""
    package = build_dispatch_package()
    assert package.work_order.task_type == WorkOrderTaskType.GOOGLE_WORKSPACE_DISCOVERY


def test_payload_matches_work_order():
    """Payload dict matches work order to_dict output."""
    package = build_dispatch_package()
    assert package.payload == package.work_order.to_dict()


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
            print(f"  PASS  {t.__name__}")
        except Exception as e:
            failed += 1
            print(f"  FAIL  {t.__name__}: {e}")
    print(f"\n{passed} passed, {failed} failed out of {len(tests)} tests")
    sys.exit(1 if failed else 0)
