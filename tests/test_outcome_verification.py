"""Tests for C26A — Outcome Verification Runtime."""

from __future__ import annotations

import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, "/opt/OS/.claude/worktrees/remaining-phases")

from substrate.organism.outcome_verification import (
    OutcomeVerification,
    OutcomeVerificationEngine,
    OutcomeVerificationStatus,
    VerificationLevel,
    VerificationMethod,
    VerificationPlan,
    VerificationPlanRegistry,
    VerificationPlanStep,
    VerificationStepResult,
)


# ── Helpers ──────────────────────────────────────────────────────────────


def _pass_result(
    level: VerificationLevel, method: VerificationMethod
) -> VerificationStepResult:
    return VerificationStepResult(
        level=level,
        method=method,
        passed=True,
        description=f"{level.value} passed",
        evidence={"check": "ok"},
    )


def _fail_result(
    level: VerificationLevel,
    method: VerificationMethod,
    error: str = "check failed",
) -> VerificationStepResult:
    return VerificationStepResult(
        level=level,
        method=method,
        passed=False,
        description=f"{level.value} failed",
        error=error,
    )


def _make_check_fn(result: VerificationStepResult):
    def fn():
        return result

    return fn


def _all_passing_fns() -> dict[
    VerificationLevel, callable
]:
    return {
        VerificationLevel.ARTIFACT_EXISTS: _make_check_fn(
            _pass_result(
                VerificationLevel.ARTIFACT_EXISTS,
                VerificationMethod.FILE_EXISTENCE,
            )
        ),
        VerificationLevel.BUILD_PASSES: _make_check_fn(
            _pass_result(
                VerificationLevel.BUILD_PASSES,
                VerificationMethod.DETERMINISTIC_CHECK,
            )
        ),
        VerificationLevel.DEPLOY_HEALTHY: _make_check_fn(
            _pass_result(
                VerificationLevel.DEPLOY_HEALTHY,
                VerificationMethod.HTTP_PROBE,
            )
        ),
        VerificationLevel.UI_OPERATIONAL: _make_check_fn(
            _pass_result(
                VerificationLevel.UI_OPERATIONAL,
                VerificationMethod.BUNDLE_INSPECTION,
            )
        ),
        VerificationLevel.WORKFLOW_OPERATIONAL: _make_check_fn(
            _pass_result(
                VerificationLevel.WORKFLOW_OPERATIONAL,
                VerificationMethod.BROWSER_CHECK,
            )
        ),
    }


# ── Type tests ───────────────────────────────────────────────────────────


class TestVerificationTypes:
    def test_verification_level_values(self):
        assert len(VerificationLevel) == 5
        assert VerificationLevel.ARTIFACT_EXISTS.value == "artifact_exists"
        assert VerificationLevel.WORKFLOW_OPERATIONAL.value == "workflow_operational"

    def test_outcome_verification_status_values(self):
        assert len(OutcomeVerificationStatus) == 4
        assert OutcomeVerificationStatus.UNVERIFIED.value == "unverified"
        assert OutcomeVerificationStatus.VERIFIED.value == "verified"

    def test_verification_method_values(self):
        assert len(VerificationMethod) == 8
        assert VerificationMethod.HTTP_PROBE.value == "http_probe"

    def test_step_result_to_dict(self):
        result = _pass_result(
            VerificationLevel.DEPLOY_HEALTHY,
            VerificationMethod.HTTP_PROBE,
        )
        d = result.to_dict()
        assert d["level"] == "deploy_healthy"
        assert d["method"] == "http_probe"
        assert d["passed"] is True
        assert "checked_at" in d

    def test_outcome_verification_to_dict(self):
        ov = OutcomeVerification(
            work_id="w1",
            task_type="deploy",
            status=OutcomeVerificationStatus.VERIFIED,
            highest_level_passed=VerificationLevel.WORKFLOW_OPERATIONAL,
            confidence=1.0,
        )
        d = ov.to_dict()
        assert d["status"] == "verified"
        assert d["highest_level_passed"] == "workflow_operational"
        assert d["confidence"] == 1.0

    def test_outcome_verification_defaults(self):
        ov = OutcomeVerification()
        assert ov.status == OutcomeVerificationStatus.UNVERIFIED
        assert ov.highest_level_passed is None
        assert ov.confidence == 0.0
        assert ov.results == []


# ── Registry tests ───────────────────────────────────────────────────────


class TestVerificationPlanRegistry:
    def test_load_from_config(self):
        config = {
            "deploy": [
                {
                    "level": "artifact_exists",
                    "method": "file_existence",
                    "description": "check files",
                    "required": True,
                },
                {
                    "level": "build_passes",
                    "method": "deterministic_check",
                    "description": "check build",
                },
            ]
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(config, f)
            path = f.name

        try:
            registry = VerificationPlanRegistry(path)
            plan = registry.get_plan("deploy")
            assert len(plan.steps) == 2
            assert plan.steps[0].level == VerificationLevel.ARTIFACT_EXISTS
            assert plan.steps[1].level == VerificationLevel.BUILD_PASSES
            assert plan.max_level == VerificationLevel.BUILD_PASSES
        finally:
            os.unlink(path)

    def test_missing_config_returns_empty_plan(self):
        registry = VerificationPlanRegistry("/nonexistent/path.json")
        plan = registry.get_plan("deploy")
        assert len(plan.steps) == 0

    def test_default_plan_fallback(self):
        config = {
            "default": [
                {
                    "level": "artifact_exists",
                    "method": "file_existence",
                    "description": "default check",
                }
            ]
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(config, f)
            path = f.name

        try:
            registry = VerificationPlanRegistry(path)
            plan = registry.get_plan("unknown_type")
            assert len(plan.steps) == 1
            assert plan.steps[0].level == VerificationLevel.ARTIFACT_EXISTS
        finally:
            os.unlink(path)

    def test_register_plan_programmatic(self):
        registry = VerificationPlanRegistry("/nonexistent/path.json")
        registry.register_plan(
            "test",
            [
                {
                    "level": "artifact_exists",
                    "method": "file_existence",
                    "description": "file exists",
                }
            ],
        )
        assert "test" in registry.task_types
        plan = registry.get_plan("test")
        assert len(plan.steps) == 1


# ── Engine tests ─────────────────────────────────────────────────────────


class TestOutcomeVerificationEngine:
    def _engine_with_deploy_plan(self):
        config = {
            "deploy": [
                {
                    "level": "artifact_exists",
                    "method": "file_existence",
                    "description": "artifacts exist",
                },
                {
                    "level": "build_passes",
                    "method": "deterministic_check",
                    "description": "build passes",
                },
                {
                    "level": "deploy_healthy",
                    "method": "http_probe",
                    "description": "health 200",
                },
                {
                    "level": "ui_operational",
                    "method": "bundle_inspection",
                    "description": "bundle has values",
                },
                {
                    "level": "workflow_operational",
                    "method": "browser_check",
                    "description": "app renders",
                },
            ]
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(config, f)
            path = f.name

        registry = VerificationPlanRegistry(path)
        engine = OutcomeVerificationEngine(registry=registry)
        return engine, path

    def test_all_passing_returns_verified(self):
        engine, path = self._engine_with_deploy_plan()
        try:
            result = engine.verify("w1", "deploy", _all_passing_fns())
            assert result.status == OutcomeVerificationStatus.VERIFIED
            assert result.confidence == 1.0
            assert (
                result.highest_level_passed
                == VerificationLevel.WORKFLOW_OPERATIONAL
            )
            assert result.verified_at is not None
            assert len(result.results) == 5
        finally:
            os.unlink(path)

    def test_l3_failure_returns_partial(self):
        """Simulates the C25 white screen bug — deploy healthy but no Clerk key in bundle."""
        engine, path = self._engine_with_deploy_plan()
        try:
            fns = _all_passing_fns()
            fns[VerificationLevel.UI_OPERATIONAL] = _make_check_fn(
                _fail_result(
                    VerificationLevel.UI_OPERATIONAL,
                    VerificationMethod.BUNDLE_INSPECTION,
                    "VITE_CLERK_PUBLISHABLE_KEY not found in bundle",
                )
            )
            result = engine.verify("w2", "deploy", fns)
            assert result.status == OutcomeVerificationStatus.PARTIAL
            assert (
                result.highest_level_passed
                == VerificationLevel.DEPLOY_HEALTHY
            )
            assert result.confidence == pytest.approx(0.6)
            assert len(result.results) == 4  # stopped at UI failure
            assert result.verified_at is None
        finally:
            os.unlink(path)

    def test_first_step_failure_returns_failed(self):
        engine, path = self._engine_with_deploy_plan()
        try:
            fns = {
                VerificationLevel.ARTIFACT_EXISTS: _make_check_fn(
                    _fail_result(
                        VerificationLevel.ARTIFACT_EXISTS,
                        VerificationMethod.FILE_EXISTENCE,
                        "Dockerfile not found",
                    )
                )
            }
            result = engine.verify("w3", "deploy", fns)
            assert result.status == OutcomeVerificationStatus.FAILED
            assert result.confidence == 0.0
            assert result.highest_level_passed is None
            assert len(result.results) == 1
        finally:
            os.unlink(path)

    def test_exception_in_check_fn_treated_as_failure(self):
        engine, path = self._engine_with_deploy_plan()
        try:

            def exploding_fn():
                raise RuntimeError("boom")

            fns = {VerificationLevel.ARTIFACT_EXISTS: exploding_fn}
            result = engine.verify("w4", "deploy", fns)
            assert result.status == OutcomeVerificationStatus.FAILED
            assert result.results[0].error == "boom"
        finally:
            os.unlink(path)

    def test_get_verification_retrieval(self):
        engine, path = self._engine_with_deploy_plan()
        try:
            engine.verify("w5", "deploy", _all_passing_fns())
            retrieved = engine.get_verification("w5")
            assert retrieved is not None
            assert retrieved.status == OutcomeVerificationStatus.VERIFIED
            assert engine.get_verification("nonexistent") is None
        finally:
            os.unlink(path)

    def test_make_verify_fn_compatibility(self):
        """Verify backward compatibility with VerificationStrategy.verify_fn (Callable[[], bool])."""
        engine, path = self._engine_with_deploy_plan()
        try:
            fn_pass = engine.make_verify_fn("w6", "deploy", _all_passing_fns())
            assert fn_pass() is True

            broken_fns = _all_passing_fns()
            broken_fns[VerificationLevel.UI_OPERATIONAL] = _make_check_fn(
                _fail_result(
                    VerificationLevel.UI_OPERATIONAL,
                    VerificationMethod.BUNDLE_INSPECTION,
                )
            )
            fn_fail = engine.make_verify_fn("w7", "deploy", broken_fns)
            assert fn_fail() is False
        finally:
            os.unlink(path)

    def test_evidence_summary_structure(self):
        engine, path = self._engine_with_deploy_plan()
        try:
            fns = _all_passing_fns()
            fns[VerificationLevel.DEPLOY_HEALTHY] = _make_check_fn(
                _fail_result(
                    VerificationLevel.DEPLOY_HEALTHY,
                    VerificationMethod.HTTP_PROBE,
                    "health returned 500",
                )
            )
            result = engine.verify("w8", "deploy", fns)
            summary = result.evidence_summary
            assert "levels_passed" in summary
            assert "levels_failed" in summary
            assert "errors" in summary
            assert "artifact_exists" in summary["levels_passed"]
            assert "deploy_healthy" in summary["levels_failed"]
        finally:
            os.unlink(path)

    def test_to_dict_round_trip(self):
        engine, path = self._engine_with_deploy_plan()
        try:
            result = engine.verify("w9", "deploy", _all_passing_fns())
            d = result.to_dict()
            assert d["verification_id"].startswith("ov-")
            assert d["work_id"] == "w9"
            assert d["status"] == "verified"
            assert isinstance(d["results"], list)
            assert len(d["results"]) == 5
        finally:
            os.unlink(path)


# ── Integration: failing verification cannot reach VERIFIED ──────────────


class TestVerificationIntegrity:
    def test_failed_required_step_blocks_verified_status(self):
        """C26A Task 9: Failing verification cannot reach VERIFIED.

        This is the core invariant — if ANY required step fails,
        the overall status MUST NOT be VERIFIED.
        """
        config = {
            "deploy": [
                {
                    "level": "artifact_exists",
                    "method": "file_existence",
                    "description": "files exist",
                },
                {
                    "level": "build_passes",
                    "method": "deterministic_check",
                    "description": "build passes",
                },
                {
                    "level": "deploy_healthy",
                    "method": "http_probe",
                    "description": "health ok",
                },
                {
                    "level": "ui_operational",
                    "method": "bundle_inspection",
                    "description": "bundle ok",
                },
                {
                    "level": "workflow_operational",
                    "method": "browser_check",
                    "description": "workflow ok",
                },
            ]
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(config, f)
            path = f.name

        try:
            registry = VerificationPlanRegistry(path)
            engine = OutcomeVerificationEngine(registry=registry)

            for fail_at in VerificationLevel:
                fns = _all_passing_fns()
                fns[fail_at] = _make_check_fn(
                    _fail_result(fail_at, VerificationMethod.DETERMINISTIC_CHECK)
                )
                result = engine.verify(
                    f"integrity-{fail_at.value}", "deploy", fns
                )
                assert result.status != OutcomeVerificationStatus.VERIFIED, (
                    f"Status was VERIFIED despite {fail_at.value} failing"
                )
        finally:
            os.unlink(path)

    def test_no_check_fn_prevents_verified(self):
        """If a step has no check function, it fails — cannot reach VERIFIED."""
        config = {
            "deploy": [
                {
                    "level": "artifact_exists",
                    "method": "file_existence",
                    "description": "files exist",
                },
                {
                    "level": "build_passes",
                    "method": "deterministic_check",
                    "description": "build passes",
                },
            ]
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(config, f)
            path = f.name

        try:
            registry = VerificationPlanRegistry(path)
            engine = OutcomeVerificationEngine(registry=registry)
            result = engine.verify("no-fns", "deploy", {})
            assert result.status == OutcomeVerificationStatus.FAILED
        finally:
            os.unlink(path)


# ── Canonical type registration ──────────────────────────────────────────


class TestCanonicalTypeRegistration:
    def test_types_registered(self):
        from substrate.canonical_types import lookup

        for name in [
            "VerificationLevel",
            "OutcomeVerificationStatus",
            "VerificationMethod",
            "VerificationStepResult",
            "VerificationPlan",
            "OutcomeVerification",
        ]:
            result = lookup(name)
            assert result is not None, f"{name} not registered"
            assert "substrate.organism.outcome_verification" in result[0]
