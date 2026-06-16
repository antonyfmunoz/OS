"""Phase 23 — Engineering Proof Loop test suite.

Tests governed execution session coordination, proof package assembly,
operator recommendation, multi-agent dispatch, and governance enforcement.

67 tests across 13 test classes.
"""

from __future__ import annotations

import sys
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, "/opt/OS")

from substrate.meta_ide.engineering_execution import (
    EngineeringArtifact,
    EngineeringArtifactType,
    EngineeringExecutionSession,
    EngineeringExecutionStatus,
    EngineeringProofPackage,
    OperatorRecommendation,
    _classify_artifact_type,
)
from substrate.meta_ide.engineering_intent import (
    EngineeringIntent,
    EngineeringIntentType,
    EngineeringPlan,
    EngineeringTask,
)
from substrate.meta_ide.engineering_session_coordinator import (
    EngineeringSessionCoordinator,
    _build_execution_waves,
)
from substrate.meta_ide.review_package_builder import ReviewPackageBuilder


# ── Helpers ──────────────────────────────────────────────────────


def _make_plan(
    status: str = "approved",
    task_count: int = 3,
    deps: dict[str, list[str]] | None = None,
) -> EngineeringPlan:
    tasks = []
    for i in range(task_count):
        tasks.append(
            EngineeringTask(
                task_id=f"et-task{i}",
                title=f"Task {i}",
                description=f"Description for task {i}",
                task_type="implementation" if i % 2 == 0 else "testing",
                risk_class="low" if i < 2 else "medium",
            )
        )
    return EngineeringPlan(
        plan_id="ep-testplan001",
        intent=EngineeringIntent(
            raw_input="build test feature",
            intent_type=EngineeringIntentType.FEATURE,
            goal="test feature",
        ),
        tasks=tasks,
        dependency_graph=deps or {},
        status=status,
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test Classes
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestExecutionContracts(unittest.TestCase):
    """Workcell A: enum values, dataclass shapes, defaults."""

    def test_execution_status_values(self) -> None:
        expected = {
            "pending",
            "planned",
            "executing",
            "validating",
            "awaiting_review",
            "approved",
            "rejected",
            "failed",
            "paused",
            "cancelled",
        }
        actual = {s.value for s in EngineeringExecutionStatus}
        self.assertEqual(actual, expected)

    def test_operator_recommendation_values(self) -> None:
        expected = {"approve", "approve_with_notes", "needs_review", "reject"}
        actual = {r.value for r in OperatorRecommendation}
        self.assertEqual(actual, expected)

    def test_artifact_type_values(self) -> None:
        expected = {"code", "test", "documentation", "configuration", "report"}
        actual = {t.value for t in EngineeringArtifactType}
        self.assertEqual(actual, expected)

    def test_session_id_prefix(self) -> None:
        s = EngineeringExecutionSession()
        self.assertTrue(s.session_id.startswith("ees-"))

    def test_artifact_id_prefix(self) -> None:
        a = EngineeringArtifact()
        self.assertTrue(a.artifact_id.startswith("eart-"))

    def test_proof_id_prefix(self) -> None:
        p = EngineeringProofPackage()
        self.assertTrue(p.proof_id.startswith("epp-"))

    def test_session_defaults(self) -> None:
        s = EngineeringExecutionSession()
        self.assertEqual(s.status, EngineeringExecutionStatus.PENDING)
        self.assertEqual(s.workspace_targets, [])
        self.assertEqual(s.worker_assignments, {})
        self.assertEqual(s.artifacts, [])
        self.assertEqual(s.errors, [])

    def test_proof_package_defaults(self) -> None:
        p = EngineeringProofPackage()
        self.assertEqual(
            p.operator_recommendation,
            OperatorRecommendation.NEEDS_REVIEW,
        )
        self.assertEqual(p.recommendation_reasoning, [])
        self.assertEqual(p.review_status, "pending")

    def test_session_to_dict(self) -> None:
        s = EngineeringExecutionSession(
            workspace_targets=["OS", "CreatorOS"],
            worker_assignments={"t1": "w1"},
        )
        d = s.to_dict()
        self.assertEqual(d["workspace_targets"], ["OS", "CreatorOS"])
        self.assertEqual(d["worker_assignments"], {"t1": "w1"})
        self.assertEqual(d["status"], "pending")

    def test_artifact_classify(self) -> None:
        self.assertEqual(
            _classify_artifact_type("test_file"),
            EngineeringArtifactType.TEST,
        )
        self.assertEqual(
            _classify_artifact_type("config"),
            EngineeringArtifactType.CONFIGURATION,
        )
        self.assertEqual(
            _classify_artifact_type("documentation"),
            EngineeringArtifactType.DOCUMENTATION,
        )
        self.assertEqual(
            _classify_artifact_type("report"),
            EngineeringArtifactType.REPORT,
        )
        self.assertEqual(
            _classify_artifact_type("something"),
            EngineeringArtifactType.CODE,
        )


class TestSessionCoordinator(unittest.TestCase):
    """Workcell B: create, execute, pause, cancel sessions."""

    def setUp(self) -> None:
        self.coord = EngineeringSessionCoordinator()
        self.plan = _make_plan()
        self.coord.register_plan(self.plan)

    def test_create_session(self) -> None:
        session = self.coord.create_session("ep-testplan001")
        self.assertTrue(session.session_id.startswith("ees-"))
        self.assertEqual(session.plan_id, "ep-testplan001")
        self.assertEqual(session.status, EngineeringExecutionStatus.PLANNED)

    def test_create_session_with_targets(self) -> None:
        session = self.coord.create_session(
            "ep-testplan001",
            workspace_targets=["OS", "CreatorOS"],
        )
        self.assertEqual(session.workspace_targets, ["OS", "CreatorOS"])

    def test_create_session_rejects_unapproved(self) -> None:
        plan = _make_plan(status="draft")
        self.coord.register_plan(plan)
        with self.assertRaises(ValueError):
            self.coord.create_session(plan.plan_id)

    def test_create_session_rejects_unknown_plan(self) -> None:
        with self.assertRaises(ValueError):
            self.coord.create_session("ep-nonexistent")

    def test_execute_session(self) -> None:
        session = self.coord.create_session("ep-testplan001")
        result = self.coord.execute_session(session.session_id)
        self.assertEqual(result.status, EngineeringExecutionStatus.AWAITING_REVIEW)
        self.assertTrue(len(result.artifacts) > 0)

    def test_execute_populates_worker_assignments(self) -> None:
        session = self.coord.create_session("ep-testplan001")
        result = self.coord.execute_session(session.session_id)
        self.assertEqual(len(result.worker_assignments), len(self.plan.tasks))

    def test_execute_collects_task_results(self) -> None:
        session = self.coord.create_session("ep-testplan001")
        result = self.coord.execute_session(session.session_id)
        for task in self.plan.tasks:
            self.assertIn(task.task_id, result.task_results)
        self.assertIn("__validation__", result.task_results)

    def test_pause_session(self) -> None:
        session = self.coord.create_session("ep-testplan001")
        ok = self.coord.pause_session(session.session_id)
        self.assertFalse(ok)

    def test_cancel_session(self) -> None:
        session = self.coord.create_session("ep-testplan001")
        ok = self.coord.cancel_session(session.session_id)
        self.assertTrue(ok)
        s = self.coord.get_session(session.session_id)
        self.assertEqual(s.status, EngineeringExecutionStatus.CANCELLED)

    def test_list_sessions(self) -> None:
        self.coord.create_session("ep-testplan001")
        self.coord.create_session("ep-testplan001")
        self.assertEqual(len(self.coord.list_sessions()), 2)

    def test_get_nonexistent_session(self) -> None:
        self.assertIsNone(self.coord.get_session("ees-doesnotexist"))

    def test_execute_already_cancelled(self) -> None:
        session = self.coord.create_session("ep-testplan001")
        self.coord.cancel_session(session.session_id)
        with self.assertRaises(ValueError):
            self.coord.execute_session(session.session_id)


class TestReviewPackageBuilder(unittest.TestCase):
    """Workcell C: proof assembly and recommendation logic."""

    def setUp(self) -> None:
        self.builder = ReviewPackageBuilder()

    def _make_session(self, errors: list[str] | None = None) -> EngineeringExecutionSession:
        session = EngineeringExecutionSession(
            plan_id="ep-test",
            status=EngineeringExecutionStatus.AWAITING_REVIEW,
        )
        session.artifacts = [
            EngineeringArtifact(
                file_path="src/test.py",
                content_hash="abc123",
                artifact_type=EngineeringArtifactType.CODE,
            ),
            EngineeringArtifact(
                file_path="tests/test_test.py",
                content_hash="def456",
                artifact_type=EngineeringArtifactType.TEST,
            ),
        ]
        session.task_results = {
            "t1": {"success": True, "outcome": "ok", "artifacts": []},
            "t2": {"success": True, "outcome": "ok", "artifacts": []},
            "__validation__": {
                "total": 2,
                "passed": 2,
                "failed": 0,
                "details": [
                    {"artifact_id": "a1", "file_path": "src/test.py", "passed": True},
                    {"artifact_id": "a2", "file_path": "tests/test_test.py", "passed": True},
                ],
            },
        }
        if errors:
            session.errors = errors
        return session

    def test_build_package(self) -> None:
        session = self._make_session()
        pkg = self.builder.build_package(session)
        self.assertTrue(pkg.proof_id.startswith("epp-"))
        self.assertEqual(pkg.session_id, session.session_id)
        self.assertEqual(len(pkg.artifacts), 2)

    def test_diff_summary(self) -> None:
        session = self._make_session()
        pkg = self.builder.build_package(session)
        self.assertEqual(pkg.diff_summary["total_files"], 2)
        self.assertIn("code", pkg.diff_summary["by_type"])

    def test_recommendation_approve(self) -> None:
        session = self._make_session()
        pkg = self.builder.build_package(session)
        self.assertEqual(pkg.operator_recommendation, OperatorRecommendation.APPROVE)

    def test_recommendation_reject_on_errors(self) -> None:
        session = self._make_session(errors=["something broke"])
        pkg = self.builder.build_package(session)
        self.assertEqual(pkg.operator_recommendation, OperatorRecommendation.REJECT)

    def test_recommendation_reject_on_failed_task(self) -> None:
        session = self._make_session()
        session.task_results["t1"] = {"success": False, "outcome": "error"}
        pkg = self.builder.build_package(session)
        self.assertEqual(pkg.operator_recommendation, OperatorRecommendation.REJECT)

    def test_recommendation_needs_review_on_validation_fail(self) -> None:
        session = self._make_session()
        session.task_results["__validation__"]["failed"] = 1
        session.task_results["__validation__"]["details"][0]["passed"] = False
        pkg = self.builder.build_package(session)
        self.assertEqual(
            pkg.operator_recommendation,
            OperatorRecommendation.NEEDS_REVIEW,
        )

    def test_recommendation_approve_with_notes_on_high_risk(self) -> None:
        session = self._make_session()
        session.artifacts[0].metadata = {"risk_class": "high"}
        pkg = self.builder.build_package(session)
        self.assertEqual(
            pkg.operator_recommendation,
            OperatorRecommendation.APPROVE_WITH_NOTES,
        )

    def test_empty_artifacts(self) -> None:
        session = EngineeringExecutionSession(
            status=EngineeringExecutionStatus.AWAITING_REVIEW,
        )
        session.task_results = {
            "t1": {"success": True, "outcome": "ok"},
            "__validation__": {"total": 0, "passed": 0, "failed": 0, "details": []},
        }
        pkg = self.builder.build_package(session)
        self.assertEqual(
            pkg.operator_recommendation,
            OperatorRecommendation.APPROVE_WITH_NOTES,
        )
        self.assertTrue(any("No artifacts" in r for r in pkg.recommendation_reasoning))


class TestExecutorComposition(unittest.TestCase):
    """Verifies Phase 23 composes with existing executor types."""

    def test_uses_executor_request(self) -> None:
        from substrate.organism.executor_runtime import ExecutorRequest

        req = ExecutorRequest(description="test task")
        self.assertTrue(req.request_id.startswith("exrq-"))

    def test_uses_executor_result(self) -> None:
        from substrate.organism.executor_runtime import ExecutorResult

        res = ExecutorResult(success=True, outcome="done")
        self.assertTrue(res.result_id.startswith("exrs-"))

    def test_uses_executor_artifact(self) -> None:
        from substrate.organism.executor_runtime import ExecutorArtifact

        art = ExecutorArtifact(name="test.py", content="hello")
        self.assertTrue(art.artifact_id.startswith("exart-"))

    def test_maps_executor_to_engineering_artifact(self) -> None:
        art_dict = {
            "artifact_type": "code",
            "name": "src/feature.py",
            "content": "# new feature",
            "metadata": {},
        }
        ea = EngineeringArtifact.from_executor_artifact(
            art_dict, session_id="ees-test", task_id="et-test"
        )
        self.assertEqual(ea.session_id, "ees-test")
        self.assertEqual(ea.task_id, "et-test")
        self.assertEqual(ea.file_path, "src/feature.py")
        self.assertTrue(len(ea.content_hash) > 0)

    def test_simulation_mode(self) -> None:
        coord = EngineeringSessionCoordinator()
        plan = _make_plan(task_count=1)
        coord.register_plan(plan)
        session = coord.create_session(plan.plan_id)
        result = coord.execute_session(session.session_id)
        self.assertEqual(result.status, EngineeringExecutionStatus.AWAITING_REVIEW)
        self.assertTrue(len(result.artifacts) > 0)


class TestMultiAgentDispatch(unittest.TestCase):
    """Verifies wave-based parallel dispatch."""

    def test_no_deps_single_wave(self) -> None:
        tasks = [
            EngineeringTask(task_id="a"),
            EngineeringTask(task_id="b"),
            EngineeringTask(task_id="c"),
        ]
        waves = _build_execution_waves(tasks, {})
        self.assertEqual(len(waves), 1)
        self.assertEqual(len(waves[0]), 3)

    def test_linear_deps_three_waves(self) -> None:
        tasks = [
            EngineeringTask(task_id="a"),
            EngineeringTask(task_id="b"),
            EngineeringTask(task_id="c"),
        ]
        deps = {"b": ["a"], "c": ["b"]}
        waves = _build_execution_waves(tasks, deps)
        self.assertEqual(len(waves), 3)
        self.assertEqual(waves[0][0].task_id, "a")
        self.assertEqual(waves[1][0].task_id, "b")
        self.assertEqual(waves[2][0].task_id, "c")

    def test_diamond_deps(self) -> None:
        tasks = [
            EngineeringTask(task_id="a"),
            EngineeringTask(task_id="b"),
            EngineeringTask(task_id="c"),
            EngineeringTask(task_id="d"),
        ]
        deps = {"b": ["a"], "c": ["a"], "d": ["b", "c"]}
        waves = _build_execution_waves(tasks, deps)
        self.assertEqual(len(waves), 3)
        self.assertEqual(waves[0][0].task_id, "a")
        wave1_ids = {t.task_id for t in waves[1]}
        self.assertEqual(wave1_ids, {"b", "c"})
        self.assertEqual(waves[2][0].task_id, "d")

    def test_worker_assignments_populated(self) -> None:
        coord = EngineeringSessionCoordinator()
        plan = _make_plan(task_count=3)
        coord.register_plan(plan)
        session = coord.create_session(plan.plan_id)
        result = coord.execute_session(session.session_id)
        self.assertEqual(len(result.worker_assignments), 3)
        for task in plan.tasks:
            self.assertIn(task.task_id, result.worker_assignments)
            self.assertTrue(result.worker_assignments[task.task_id].startswith("worker-"))


class TestGovernanceEnforcement(unittest.TestCase):
    """Verifies no bypass of governance constraints."""

    def test_no_merge_method(self) -> None:
        coord = EngineeringSessionCoordinator()
        self.assertFalse(hasattr(coord, "merge"))
        self.assertFalse(hasattr(coord, "git_merge"))

    def test_no_push_method(self) -> None:
        coord = EngineeringSessionCoordinator()
        self.assertFalse(hasattr(coord, "push"))
        self.assertFalse(hasattr(coord, "git_push"))

    def test_no_deploy_method(self) -> None:
        coord = EngineeringSessionCoordinator()
        self.assertFalse(hasattr(coord, "deploy"))
        self.assertFalse(hasattr(coord, "auto_deploy"))

    def test_proof_package_no_deploy(self) -> None:
        builder = ReviewPackageBuilder()
        self.assertFalse(hasattr(builder, "deploy"))
        self.assertFalse(hasattr(builder, "merge"))
        self.assertFalse(hasattr(builder, "push"))


class TestNoNewAuthority(unittest.TestCase):
    """Coordinator dispatches only — no raw subprocess, no git mutation."""

    def test_no_subprocess_import(self) -> None:
        import inspect

        src = inspect.getsource(EngineeringSessionCoordinator)
        self.assertNotIn("subprocess", src)

    def test_no_os_system_import(self) -> None:
        import inspect

        src = inspect.getsource(EngineeringSessionCoordinator)
        self.assertNotIn("os.system(", src)

    def test_no_git_mutation(self) -> None:
        import inspect

        src = inspect.getsource(EngineeringSessionCoordinator)
        for cmd in ["git push", "git merge", "git checkout", "git commit"]:
            self.assertNotIn(cmd, src)


class TestDeterministicFirst(unittest.TestCase):
    """No LLM imports, works with None engines."""

    def test_no_llm_imports_execution(self) -> None:
        import importlib

        mod = importlib.import_module("substrate.meta_ide.engineering_execution")
        src = open(mod.__file__).read()
        for pattern in [
            "call_with_fallback",
            "model_router",
            "llm_adapter",
            "anthropic",
            "google.genai",
        ]:
            self.assertNotIn(pattern, src)

    def test_no_llm_imports_coordinator(self) -> None:
        import importlib

        mod = importlib.import_module("substrate.meta_ide.engineering_session_coordinator")
        src = open(mod.__file__).read()
        for pattern in [
            "call_with_fallback",
            "model_router",
            "llm_adapter",
        ]:
            self.assertNotIn(pattern, src)

    def test_works_with_none_executor(self) -> None:
        coord = EngineeringSessionCoordinator(executor=None)
        plan = _make_plan(task_count=1)
        coord.register_plan(plan)
        session = coord.create_session(plan.plan_id)
        result = coord.execute_session(session.session_id)
        self.assertEqual(result.status, EngineeringExecutionStatus.AWAITING_REVIEW)


class TestGracefulDegradation(unittest.TestCase):
    """Handles None dependencies gracefully."""

    def test_none_executor(self) -> None:
        coord = EngineeringSessionCoordinator(executor=None)
        plan = _make_plan(task_count=1)
        coord.register_plan(plan)
        session = coord.create_session(plan.plan_id)
        result = coord.execute_session(session.session_id)
        self.assertTrue(len(result.artifacts) > 0)

    def test_none_event_spine(self) -> None:
        coord = EngineeringSessionCoordinator(event_spine=None)
        plan = _make_plan(task_count=1)
        coord.register_plan(plan)
        session = coord.create_session(plan.plan_id)
        result = coord.execute_session(session.session_id)
        self.assertEqual(result.status, EngineeringExecutionStatus.AWAITING_REVIEW)

    def test_none_planner(self) -> None:
        coord = EngineeringSessionCoordinator(planner=None)
        plan = _make_plan(task_count=1)
        coord.register_plan(plan)
        session = coord.create_session(plan.plan_id)
        self.assertIsNotNone(session)


class TestApproveRejectFlow(unittest.TestCase):
    """End-to-end review approval and rejection."""

    def setUp(self) -> None:
        self.coord = EngineeringSessionCoordinator()
        self.plan = _make_plan(task_count=2)
        self.coord.register_plan(self.plan)

    def test_approve_flow(self) -> None:
        session = self.coord.create_session(self.plan.plan_id)
        session = self.coord.execute_session(session.session_id)
        builder = ReviewPackageBuilder()
        pkg = builder.build_package(session)
        self.coord.store_proof_package(pkg)

        approved = self.coord.approve_review(pkg.proof_id, reviewed_by="operator")
        self.assertEqual(approved.review_status, "approved")
        self.assertEqual(approved.reviewed_by, "operator")

        s = self.coord.get_session(session.session_id)
        self.assertEqual(s.status, EngineeringExecutionStatus.APPROVED)

    def test_reject_flow(self) -> None:
        session = self.coord.create_session(self.plan.plan_id)
        session = self.coord.execute_session(session.session_id)
        builder = ReviewPackageBuilder()
        pkg = builder.build_package(session)
        self.coord.store_proof_package(pkg)

        rejected = self.coord.reject_review(pkg.proof_id, reason="needs more tests")
        self.assertEqual(rejected.review_status, "rejected")
        self.assertEqual(rejected.rejection_reason, "needs more tests")

        s = self.coord.get_session(session.session_id)
        self.assertEqual(s.status, EngineeringExecutionStatus.REJECTED)

    def test_approve_nonexistent(self) -> None:
        result = self.coord.approve_review("epp-doesnotexist")
        self.assertIsNone(result)

    def test_list_proof_packages(self) -> None:
        session = self.coord.create_session(self.plan.plan_id)
        session = self.coord.execute_session(session.session_id)
        builder = ReviewPackageBuilder()
        pkg = builder.build_package(session)
        self.coord.store_proof_package(pkg)

        packages = self.coord.list_proof_packages()
        self.assertEqual(len(packages), 1)


class TestCockpitReviewRoutes(unittest.TestCase):
    """API route module loads and has expected structure."""

    def test_module_imports(self) -> None:
        from transports.api import cockpit_engineering_review_routes

        self.assertTrue(hasattr(cockpit_engineering_review_routes, "configure"))
        self.assertTrue(
            hasattr(
                cockpit_engineering_review_routes,
                "engineering_review_router",
            )
        )

    def test_configure_callable(self) -> None:
        from transports.api import cockpit_engineering_review_routes

        mock_dep = MagicMock()
        cockpit_engineering_review_routes.configure(mock_dep)

    def test_router_has_routes(self) -> None:
        from transports.api import cockpit_engineering_review_routes

        mock_dep = MagicMock()
        cockpit_engineering_review_routes.configure(mock_dep)
        router = cockpit_engineering_review_routes.engineering_review_router
        paths = [r.path for r in router.routes]
        self.assertTrue(any("/engineering/sessions" in p for p in paths))
        self.assertTrue(any("/engineering/reviews" in p for p in paths))

    def test_session_routes_exist(self) -> None:
        from transports.api import cockpit_engineering_review_routes

        mock_dep = MagicMock()
        cockpit_engineering_review_routes.configure(mock_dep)
        router = cockpit_engineering_review_routes.engineering_review_router
        paths = [r.path for r in router.routes]
        for expected in [
            "/engineering/sessions",
            "/engineering/sessions/{session_id}",
            "/engineering/sessions/{session_id}/execute",
            "/engineering/sessions/{session_id}/pause",
            "/engineering/sessions/{session_id}/cancel",
        ]:
            self.assertTrue(
                any(expected in p for p in paths),
                f"Missing route: {expected}",
            )

    def test_review_routes_exist(self) -> None:
        from transports.api import cockpit_engineering_review_routes

        mock_dep = MagicMock()
        cockpit_engineering_review_routes.configure(mock_dep)
        router = cockpit_engineering_review_routes.engineering_review_router
        paths = [r.path for r in router.routes]
        for expected in [
            "/engineering/reviews",
            "/engineering/reviews/{proof_id}",
            "/engineering/reviews/{proof_id}/approve",
            "/engineering/reviews/{proof_id}/reject",
        ]:
            self.assertTrue(
                any(expected in p for p in paths),
                f"Missing route: {expected}",
            )

    def test_no_merge_deploy_routes(self) -> None:
        from transports.api import cockpit_engineering_review_routes

        mock_dep = MagicMock()
        cockpit_engineering_review_routes.configure(mock_dep)
        router = cockpit_engineering_review_routes.engineering_review_router
        paths = [r.path for r in router.routes]
        for forbidden in ["merge", "deploy", "push"]:
            self.assertFalse(
                any(forbidden in p for p in paths),
                f"Forbidden route found: {forbidden}",
            )


class TestTypeRegistry(unittest.TestCase):
    """All Phase 23 types registered in canonical_types.py."""

    def test_types_registered(self) -> None:
        from substrate.canonical_types import CANONICAL_TYPES

        expected = [
            "EngineeringExecutionStatus",
            "EngineeringArtifactType",
            "OperatorRecommendation",
            "EngineeringExecutionSession",
            "EngineeringArtifact",
            "EngineeringProofPackage",
            "EngineeringSessionCoordinator",
            "ReviewPackageBuilder",
        ]
        for name in expected:
            self.assertIn(name, CANONICAL_TYPES, f"Missing: {name}")

    def test_no_duplicate_registrations(self) -> None:
        from substrate.canonical_types import CANONICAL_TYPES

        for name in [
            "EngineeringExecutionStatus",
            "EngineeringArtifactType",
            "OperatorRecommendation",
        ]:
            result = CANONICAL_TYPES.get(name, [])
            self.assertIsInstance(result, list)
            self.assertEqual(len(result), 1, f"Duplicate: {name}")


class TestRealityIntegration(unittest.TestCase):
    """Engineering execution events become reality observations."""

    def test_mutation_source_exists(self) -> None:
        from substrate.reality_model.reality_mutation import MutationSource

        self.assertEqual(
            MutationSource.ENGINEERING_EXECUTION.value,
            "engineering_execution",
        )

    def test_mutation_source_distinct(self) -> None:
        from substrate.reality_model.reality_mutation import MutationSource

        self.assertNotEqual(
            MutationSource.ENGINEERING.value,
            MutationSource.ENGINEERING_EXECUTION.value,
        )


class TestIntegrationE2E(unittest.TestCase):
    """Full flow: plan → session → execute → proof → review."""

    def test_full_flow(self) -> None:
        plan = _make_plan(task_count=2)
        coord = EngineeringSessionCoordinator()
        coord.register_plan(plan)

        session = coord.create_session(plan.plan_id, workspace_targets=["OS"])
        self.assertEqual(session.status, EngineeringExecutionStatus.PLANNED)

        session = coord.execute_session(session.session_id)
        self.assertEqual(session.status, EngineeringExecutionStatus.AWAITING_REVIEW)
        self.assertTrue(len(session.artifacts) > 0)
        self.assertEqual(len(session.worker_assignments), 2)

        builder = ReviewPackageBuilder()
        pkg = builder.build_package(session)
        self.assertEqual(pkg.operator_recommendation, OperatorRecommendation.APPROVE)

        coord.store_proof_package(pkg)
        approved = coord.approve_review(pkg.proof_id, reviewed_by="AFM")
        self.assertEqual(approved.review_status, "approved")

        final = coord.get_session(session.session_id)
        self.assertEqual(final.status, EngineeringExecutionStatus.APPROVED)

    def test_full_flow_with_rejection(self) -> None:
        plan = _make_plan(task_count=1)
        coord = EngineeringSessionCoordinator()
        coord.register_plan(plan)

        session = coord.create_session(plan.plan_id)
        session = coord.execute_session(session.session_id)

        builder = ReviewPackageBuilder()
        pkg = builder.build_package(session)
        coord.store_proof_package(pkg)

        rejected = coord.reject_review(pkg.proof_id, reason="needs refactor")
        self.assertEqual(rejected.review_status, "rejected")

        final = coord.get_session(session.session_id)
        self.assertEqual(final.status, EngineeringExecutionStatus.REJECTED)

    def test_lineage_chain(self) -> None:
        plan = _make_plan(task_count=2)
        coord = EngineeringSessionCoordinator()
        coord.register_plan(plan)
        session = coord.create_session(plan.plan_id)
        session = coord.execute_session(session.session_id)
        builder = ReviewPackageBuilder()
        pkg = builder.build_package(session)

        self.assertEqual(pkg.plan_id, plan.plan_id)
        self.assertEqual(pkg.session_id, session.session_id)
        for artifact in pkg.artifacts:
            self.assertEqual(artifact.session_id, session.session_id)
            self.assertIn(artifact.task_id, [t.task_id for t in plan.tasks])

    def test_to_dict_roundtrip(self) -> None:
        plan = _make_plan(task_count=1)
        coord = EngineeringSessionCoordinator()
        coord.register_plan(plan)
        session = coord.create_session(plan.plan_id)
        session = coord.execute_session(session.session_id)
        builder = ReviewPackageBuilder()
        pkg = builder.build_package(session)

        session_dict = session.to_dict()
        self.assertIn("workspace_targets", session_dict)
        self.assertIn("worker_assignments", session_dict)

        pkg_dict = pkg.to_dict()
        self.assertIn("operator_recommendation", pkg_dict)
        self.assertIn("recommendation_reasoning", pkg_dict)

    def test_meta_ide_exports(self) -> None:
        from substrate.meta_ide import (
            EngineeringArtifact,
            EngineeringArtifactType,
            EngineeringExecutionSession,
            EngineeringExecutionStatus,
            EngineeringProofPackage,
            EngineeringSessionCoordinator,
            OperatorRecommendation,
            ReviewPackageBuilder,
        )

        self.assertIsNotNone(EngineeringSessionCoordinator)
        self.assertIsNotNone(ReviewPackageBuilder)
        self.assertIsNotNone(OperatorRecommendation)


if __name__ == "__main__":
    unittest.main()
