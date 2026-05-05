"""Phase 87C — Local Workstation Baseline + Device Literacy + Optimization Readiness v1.

Tests for contracts, baseline, device literacy, storage model, app/process model,
developer environment, performance tuning, recommendations, approval policy,
views, safety, strategy docs, and regression.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from umh.workstation_optimization.contracts import (
    DeviceArea,
    DeviceBaselineCategory,
    DeviceLiteracyExplanation,
    FileClassification,
    OptimizationActionType,
    OptimizationApprovalRequirement,
    OptimizationCandidate,
    OptimizationReversibility,
    OptimizationRiskLevel,
    PerformanceTuningAdvisory,
    PerformanceTuningCategory,
    WorkstationAuditMode,
    WorkstationBaselinePlan,
    WorkstationOptimizationReport,
    normalize_action_type,
    normalize_approval,
    normalize_audit_mode,
    normalize_device_area,
    normalize_file_classification,
    normalize_reversibility,
    normalize_risk_level,
    normalize_tuning_category,
)


class TestContractNormalizers(unittest.TestCase):
    def test_normalize_device_area(self):
        self.assertEqual(normalize_device_area("storage"), DeviceArea.STORAGE)
        self.assertEqual(normalize_device_area("STORAGE"), DeviceArea.STORAGE)

    def test_normalize_audit_mode(self):
        self.assertEqual(normalize_audit_mode("planning_only"), WorkstationAuditMode.PLANNING_ONLY)

    def test_normalize_action_type(self):
        self.assertEqual(normalize_action_type("delete"), OptimizationActionType.DELETE)

    def test_normalize_risk_level(self):
        self.assertEqual(normalize_risk_level("high"), OptimizationRiskLevel.HIGH)

    def test_normalize_approval(self):
        self.assertEqual(
            normalize_approval("explicit_approval"),
            OptimizationApprovalRequirement.EXPLICIT_APPROVAL,
        )

    def test_normalize_reversibility(self):
        self.assertEqual(
            normalize_reversibility("irreversible"), OptimizationReversibility.IRREVERSIBLE
        )

    def test_normalize_file_classification(self):
        self.assertEqual(
            normalize_file_classification("system_critical"), FileClassification.SYSTEM_CRITICAL
        )

    def test_normalize_tuning_category(self):
        self.assertEqual(
            normalize_tuning_category("overclocking"), PerformanceTuningCategory.OVERCLOCKING
        )

    def test_unknowns_degrade_safely(self):
        self.assertEqual(normalize_device_area("nonsense"), DeviceArea.UNKNOWN)
        self.assertEqual(normalize_audit_mode("nonsense"), WorkstationAuditMode.UNKNOWN)
        self.assertEqual(normalize_action_type("nonsense"), OptimizationActionType.UNKNOWN)
        self.assertEqual(normalize_risk_level("nonsense"), OptimizationRiskLevel.UNKNOWN)
        self.assertEqual(normalize_approval("nonsense"), OptimizationApprovalRequirement.UNKNOWN)
        self.assertEqual(normalize_reversibility("nonsense"), OptimizationReversibility.UNKNOWN)
        self.assertEqual(normalize_file_classification("nonsense"), FileClassification.UNKNOWN)
        self.assertEqual(normalize_tuning_category("nonsense"), PerformanceTuningCategory.UNKNOWN)


class TestContractSerialization(unittest.TestCase):
    def test_baseline_category_roundtrip(self):
        c = DeviceBaselineCategory(category_id="test", area=DeviceArea.STORAGE, name="Test")
        d = c.to_dict()
        c2 = DeviceBaselineCategory.from_dict(d)
        self.assertEqual(c2.area, DeviceArea.STORAGE)
        self.assertEqual(d["area"], "storage")

    def test_baseline_plan_roundtrip(self):
        p = WorkstationBaselinePlan(plan_id="test", node_id="local_pc")
        d = p.to_dict()
        p2 = WorkstationBaselinePlan.from_dict(d)
        self.assertEqual(p2.node_id, "local_pc")

    def test_optimization_candidate_roundtrip(self):
        c = OptimizationCandidate(
            candidate_id="test", area=DeviceArea.STORAGE, action_type=OptimizationActionType.DELETE
        )
        d = c.to_dict()
        c2 = OptimizationCandidate.from_dict(d)
        self.assertEqual(c2.action_type, OptimizationActionType.DELETE)

    def test_literacy_explanation_roundtrip(self):
        e = DeviceLiteracyExplanation(explanation_id="test", area=DeviceArea.MEMORY, topic="RAM")
        d = e.to_dict()
        e2 = DeviceLiteracyExplanation.from_dict(d)
        self.assertEqual(e2.topic, "RAM")

    def test_tuning_advisory_roundtrip(self):
        a = PerformanceTuningAdvisory(
            advisory_id="test", category=PerformanceTuningCategory.OVERCLOCKING
        )
        d = a.to_dict()
        a2 = PerformanceTuningAdvisory.from_dict(d)
        self.assertEqual(a2.category, PerformanceTuningCategory.OVERCLOCKING)

    def test_report_roundtrip(self):
        r = WorkstationOptimizationReport(report_id="test", node_id="local_pc")
        d = r.to_dict()
        r2 = WorkstationOptimizationReport.from_dict(d)
        self.assertEqual(r2.node_id, "local_pc")


class TestBaseline(unittest.TestCase):
    def setUp(self):
        from umh.workstation_optimization.baseline import (
            build_default_baseline_categories,
            build_onboarding_workstation_baseline_plan,
        )

        self.categories = build_default_baseline_categories()
        self.plan = build_onboarding_workstation_baseline_plan()
        self.areas = {c.area for c in self.categories}

    def test_includes_storage(self):
        self.assertIn(DeviceArea.STORAGE, self.areas)

    def test_includes_memory(self):
        self.assertIn(DeviceArea.MEMORY, self.areas)

    def test_includes_cpu(self):
        self.assertIn(DeviceArea.CPU, self.areas)

    def test_includes_gpu(self):
        self.assertIn(DeviceArea.GPU, self.areas)

    def test_includes_startup_items(self):
        self.assertIn(DeviceArea.STARTUP_ITEMS, self.areas)

    def test_includes_background_processes(self):
        self.assertIn(DeviceArea.BACKGROUND_PROCESSES, self.areas)

    def test_includes_installed_apps(self):
        self.assertIn(DeviceArea.INSTALLED_APPS, self.areas)

    def test_includes_browser_data(self):
        self.assertIn(DeviceArea.BROWSER_DATA, self.areas)

    def test_includes_cloud_sync(self):
        self.assertIn(DeviceArea.CLOUD_SYNC, self.areas)

    def test_includes_backups(self):
        self.assertIn(DeviceArea.BACKUPS, self.areas)

    def test_includes_developer_environment(self):
        self.assertIn(DeviceArea.DEVELOPMENT_ENVIRONMENT, self.areas)

    def test_includes_docker_vm(self):
        self.assertIn(DeviceArea.DOCKER_VM, self.areas)

    def test_includes_system_settings(self):
        self.assertIn(DeviceArea.SYSTEM_SETTINGS, self.areas)

    def test_includes_drivers(self):
        self.assertIn(DeviceArea.DRIVERS, self.areas)

    def test_includes_bios_uefi(self):
        self.assertIn(DeviceArea.BIOS_UEFI, self.areas)

    def test_includes_credentials(self):
        self.assertIn(DeviceArea.CREDENTIALS, self.areas)

    def test_plan_is_planning_only(self):
        self.assertEqual(self.plan.audit_mode, WorkstationAuditMode.PLANNING_ONLY)

    def test_blocked_observations_include_credentials(self):
        blocked = " ".join(self.plan.blocked_observations).lower()
        self.assertTrue(
            "credential" in blocked or "password" in blocked or "private key" in blocked
        )

    def test_blocked_observations_include_destructive(self):
        blocked = " ".join(self.plan.blocked_observations).lower()
        self.assertIn("destructive", blocked)


class TestDeviceLiteracy(unittest.TestCase):
    def setUp(self):
        from umh.workstation_optimization.device_literacy import (
            build_default_device_literacy_explanations,
        )

        self.explanations = build_default_device_literacy_explanations()
        self.topics = {e.topic for e in self.explanations}

    def test_storage_explanation_exists(self):
        self.assertTrue(any("storage" in t.lower() or "ssd" in t.lower() for t in self.topics))

    def test_memory_explanation_exists(self):
        self.assertTrue(any("ram" in t.lower() or "memory" in t.lower() for t in self.topics))

    def test_cpu_gpu_explanation_exists(self):
        self.assertTrue(any("cpu" in t.lower() or "gpu" in t.lower() for t in self.topics))

    def test_startup_process_explanation_exists(self):
        self.assertTrue(any("startup" in t.lower() or "process" in t.lower() for t in self.topics))

    def test_cloud_sync_explanation_exists(self):
        self.assertTrue(any("cloud" in t.lower() or "sync" in t.lower() for t in self.topics))

    def test_developer_bloat_explanation_exists(self):
        self.assertTrue(any("developer" in t.lower() or "bloat" in t.lower() for t in self.topics))

    def test_overclocking_risk_explanation_exists(self):
        self.assertTrue(
            any("overclock" in t.lower() or "undervolt" in t.lower() for t in self.topics)
        )

    def test_explanations_are_plain_language(self):
        for e in self.explanations:
            self.assertTrue(len(e.plain_language_summary) > 50, f"Summary too short: {e.topic}")

    def test_explanations_include_why_it_matters(self):
        for e in self.explanations:
            self.assertTrue(len(e.why_it_matters) > 10, f"Missing why_it_matters: {e.topic}")

    def test_explanations_include_common_failure_modes(self):
        has_failures = sum(1 for e in self.explanations if len(e.common_failure_modes) > 0)
        self.assertGreater(has_failures, 5)


class TestStorageModel(unittest.TestCase):
    def setUp(self):
        from umh.workstation_optimization.storage_model import (
            classify_file_candidate,
            recommend_file_action,
        )

        self.classify = classify_file_candidate
        self.recommend = recommend_file_action

    def test_system_critical_preserves(self):
        r = self.recommend(FileClassification.SYSTEM_CRITICAL)
        self.assertEqual(r["recommended_action"], "preserve")

    def test_credential_preserves(self):
        r = self.recommend(FileClassification.CREDENTIAL_OR_SECRET)
        self.assertEqual(r["recommended_action"], "preserve")

    def test_business_critical_preserves(self):
        r = self.recommend(FileClassification.BUSINESS_CRITICAL)
        self.assertEqual(r["recommended_action"], "preserve")

    def test_legal_financial_preserves(self):
        r = self.recommend(FileClassification.LEGAL_FINANCIAL)
        self.assertEqual(r["recommended_action"], "preserve")

    def test_user_created_requires_review(self):
        r = self.recommend(FileClassification.USER_CREATED)
        self.assertIn(r["approval_required"], ("explicit_approval", "review_recommended"))

    def test_cloud_synced_requires_review(self):
        r = self.recommend(FileClassification.CLOUD_SYNCED)
        self.assertIn(r["approval_required"], ("explicit_approval", "review_recommended"))

    def test_generated_cache_cleanup_candidate(self):
        r = self.recommend(FileClassification.GENERATED_CACHE)
        self.assertIn(r["recommended_action"], ("clear_cache", "recommend"))

    def test_duplicate_candidate_requires_review(self):
        r = self.recommend(FileClassification.DUPLICATE_CANDIDATE)
        self.assertIn(r["approval_required"], ("explicit_approval", "review_recommended"))

    def test_developer_artifact_cleanup_candidate(self):
        r = self.recommend(FileClassification.DEVELOPER_ARTIFACT)
        self.assertIn(r["recommended_action"], ("clear_cache", "recommend"))

    def test_unknown_preserves(self):
        r = self.recommend(FileClassification.UNKNOWN)
        self.assertEqual(r["recommended_action"], "preserve")


class TestAppProcessModel(unittest.TestCase):
    def setUp(self):
        from umh.workstation_optimization.app_process_model import (
            classify_app_candidate,
            classify_process_candidate,
            recommend_app_action,
            recommend_process_action,
        )

        self.classify_app = classify_app_candidate
        self.classify_proc = classify_process_candidate
        self.rec_app = recommend_app_action
        self.rec_proc = recommend_process_action

    def test_security_tool_preserves(self):
        r = self.rec_app("security_tool")
        self.assertEqual(r["recommended_action"], "preserve")

    def test_password_auth_preserves(self):
        c = self.classify_app(name="1password")
        self.assertEqual(c, "security_tool")

    def test_system_process_preserves(self):
        r = self.rec_proc("system_process")
        self.assertEqual(r["recommended_action"], "preserve")

    def test_unknown_process_preserves(self):
        r = self.rec_proc("unknown")
        self.assertEqual(r["recommended_action"], "preserve")

    def test_unused_app_uninstall_candidate(self):
        r = self.rec_app("startup_bloat_candidate", usage_confidence=0.1)
        self.assertIn(r["recommended_action"], ("uninstall", "recommend"))

    def test_startup_bloat_disable_candidate(self):
        c = self.classify_app(name="spotify updater")
        self.assertEqual(c, "startup_bloat_candidate")

    def test_high_resource_unknown_investigate(self):
        c = self.classify_proc(name="unknown_proc", context="high cpu usage")
        self.assertEqual(c, "high_resource_unknown")
        r = self.rec_proc(c)
        self.assertEqual(r["recommended_action"], "recommend")

    def test_kill_requires_explicit_approval(self):
        r = self.rec_proc("high_resource_unknown")
        self.assertIn(r["approval_required"], ("explicit_approval",))

    def test_uninstall_requires_explicit_approval(self):
        r = self.rec_app("startup_bloat_candidate", usage_confidence=0.1)
        self.assertEqual(r["approval_required"], "explicit_approval")


class TestDeveloperEnvironment(unittest.TestCase):
    def setUp(self):
        from umh.workstation_optimization.developer_environment import (
            build_developer_environment_cleanup_categories,
            classify_developer_artifact,
            recommend_developer_cleanup_action,
        )

        self.categories = build_developer_environment_cleanup_categories()
        self.cat_names = {c["name"] for c in self.categories}
        self.classify = classify_developer_artifact
        self.recommend = recommend_developer_cleanup_action

    def test_includes_node_modules(self):
        self.assertIn("node_modules", self.cat_names)

    def test_includes_python_venvs(self):
        self.assertIn("python_venvs", self.cat_names)

    def test_includes_package_caches(self):
        self.assertIn("package_caches", self.cat_names)

    def test_includes_docker_images(self):
        self.assertIn("docker_images", self.cat_names)

    def test_includes_docker_volumes(self):
        self.assertIn("docker_volumes", self.cat_names)

    def test_includes_build_artifacts(self):
        self.assertIn("build_artifacts", self.cat_names)

    def test_includes_logs(self):
        self.assertIn("logs", self.cat_names)

    def test_includes_duplicate_repos(self):
        self.assertIn("duplicate_repos", self.cat_names)

    def test_source_code_preserve(self):
        r = self.recommend("source_code")
        self.assertEqual(r["action"], "preserve")

    def test_docker_volumes_high_risk(self):
        r = self.recommend("database")
        self.assertEqual(r["risk"], "high")

    def test_generated_artifacts_cleanup(self):
        r = self.recommend("build_artifact")
        self.assertEqual(r["action"], "clear_cache")

    def test_unknown_preserves(self):
        r = self.recommend("unknown")
        self.assertEqual(r["action"], "preserve")


class TestPerformanceTuning(unittest.TestCase):
    def setUp(self):
        from umh.workstation_optimization.performance_tuning import (
            build_performance_tuning_categories,
            assess_performance_tuning_risk,
            explain_safe_performance_first_steps,
            create_performance_tuning_advisory,
        )

        self.categories = build_performance_tuning_categories()
        self.cat_names = {c["category"] for c in self.categories}
        self.risk = assess_performance_tuning_risk
        self.first_steps = explain_safe_performance_first_steps()
        self.advisory = create_performance_tuning_advisory

    def test_includes_power_profile(self):
        self.assertIn("power_profile", self.cat_names)

    def test_includes_thermal_management(self):
        self.assertIn("thermal_management", self.cat_names)

    def test_includes_driver_update(self):
        self.assertIn("driver_update", self.cat_names)

    def test_includes_overclocking(self):
        self.assertIn("overclocking", self.cat_names)

    def test_includes_undervolting(self):
        self.assertIn("undervolting", self.cat_names)

    def test_includes_fan_curve(self):
        self.assertIn("fan_curve", self.cat_names)

    def test_overclocking_high_risk(self):
        self.assertEqual(self.risk(PerformanceTuningCategory.OVERCLOCKING), "high")

    def test_undervolting_high_risk(self):
        self.assertEqual(self.risk(PerformanceTuningCategory.UNDERVOLTING), "high")

    def test_bios_uefi_category_in_baseline(self):
        from umh.workstation_optimization.baseline import build_default_baseline_categories

        areas = {c.area for c in build_default_baseline_categories()}
        self.assertIn(DeviceArea.BIOS_UEFI, areas)

    def test_safe_first_steps_include_disk_space(self):
        steps = [s["step"].lower() for s in self.first_steps]
        self.assertTrue(any("disk" in s or "space" in s for s in steps))

    def test_safe_first_steps_include_startup(self):
        steps = [s["step"].lower() for s in self.first_steps]
        self.assertTrue(any("startup" in s for s in steps))

    def test_safe_first_steps_include_cooling(self):
        steps = [s["step"].lower() for s in self.first_steps]
        self.assertTrue(any("cool" in s or "airflow" in s for s in steps))

    def test_safe_first_steps_include_ram_storage_upgrade(self):
        steps = [s["step"].lower() for s in self.first_steps]
        self.assertTrue(any("ram" in s or "storage" in s for s in steps))

    def test_overclocking_never_automatic(self):
        adv = self.advisory(PerformanceTuningCategory.OVERCLOCKING)
        self.assertEqual(
            adv.approval_required, OptimizationApprovalRequirement.EXPERT_REVIEW_REQUIRED
        )

    def test_overclocking_requires_approval(self):
        adv = self.advisory(PerformanceTuningCategory.OVERCLOCKING)
        self.assertNotEqual(adv.approval_required, OptimizationApprovalRequirement.NONE)

    def test_overclocking_requires_stability_testing(self):
        adv = self.advisory(PerformanceTuningCategory.OVERCLOCKING)
        self.assertTrue(adv.stability_testing_required)


class TestRecommendationsApproval(unittest.TestCase):
    def setUp(self):
        from umh.workstation_optimization.recommendations import (
            build_onboarding_optimization_recommendations,
            build_workstation_optimization_report,
        )
        from umh.workstation_optimization.approval_policy import (
            determine_approval_requirement,
            requires_rollback_plan,
            requires_post_action_verification,
            validate_candidate_safe_for_recommendation,
            build_destructive_action_policy,
        )

        self.recommendations = build_onboarding_optimization_recommendations()
        self.report = build_workstation_optimization_report()
        self.determine = determine_approval_requirement
        self.rollback = requires_rollback_plan
        self.verify = requires_post_action_verification
        self.validate = validate_candidate_safe_for_recommendation
        self.policy = build_destructive_action_policy()

    def test_explain_no_approval(self):
        c = OptimizationCandidate(action_type=OptimizationActionType.EXPLAIN)
        self.assertEqual(self.determine(c), OptimizationApprovalRequirement.NONE)

    def test_recommend_no_approval(self):
        c = OptimizationCandidate(action_type=OptimizationActionType.RECOMMEND)
        self.assertEqual(self.determine(c), OptimizationApprovalRequirement.NONE)

    def test_preserve_no_approval(self):
        c = OptimizationCandidate(action_type=OptimizationActionType.PRESERVE)
        self.assertEqual(self.determine(c), OptimizationApprovalRequirement.NONE)

    def test_archive_requires_approval(self):
        c = OptimizationCandidate(action_type=OptimizationActionType.ARCHIVE)
        self.assertNotEqual(self.determine(c), OptimizationApprovalRequirement.NONE)

    def test_delete_requires_explicit_approval(self):
        c = OptimizationCandidate(action_type=OptimizationActionType.DELETE)
        self.assertEqual(self.determine(c), OptimizationApprovalRequirement.EXPLICIT_APPROVAL)

    def test_uninstall_requires_explicit_approval(self):
        c = OptimizationCandidate(action_type=OptimizationActionType.UNINSTALL)
        self.assertEqual(self.determine(c), OptimizationApprovalRequirement.EXPLICIT_APPROVAL)

    def test_kill_process_requires_explicit_approval(self):
        c = OptimizationCandidate(action_type=OptimizationActionType.KILL_PROCESS)
        self.assertEqual(self.determine(c), OptimizationApprovalRequirement.EXPLICIT_APPROVAL)

    def test_change_setting_requires_explicit_approval(self):
        c = OptimizationCandidate(action_type=OptimizationActionType.CHANGE_SETTING)
        self.assertEqual(self.determine(c), OptimizationApprovalRequirement.EXPLICIT_APPROVAL)

    def test_overclock_requires_high_review(self):
        c = OptimizationCandidate(action_type=OptimizationActionType.OVERCLOCK)
        self.assertEqual(self.determine(c), OptimizationApprovalRequirement.EXPERT_REVIEW_REQUIRED)

    def test_hard_to_reverse_requires_rollback(self):
        c = OptimizationCandidate(
            action_type=OptimizationActionType.DELETE,
            reversibility=OptimizationReversibility.HARD_TO_REVERSE,
        )
        self.assertTrue(self.rollback(c))

    def test_unknown_target_cannot_be_actioned(self):
        c = OptimizationCandidate(action_type=OptimizationActionType.DELETE, target="")
        r = self.validate(c)
        self.assertFalse(r["safe"])

    def test_report_includes_high_risk_items(self):
        self.assertGreater(len(self.report.high_risk_items), 0)

    def test_report_includes_preserved_items(self):
        self.assertGreater(len(self.report.preserved_items), 0)

    def test_report_includes_next_steps(self):
        self.assertGreater(len(self.report.next_steps), 0)

    def test_report_contains_no_real_scan_data(self):
        from umh.workstation_optimization.safety import validate_report_has_no_real_scan_data

        r = validate_report_has_no_real_scan_data(self.report)
        self.assertTrue(r["safe"])


class TestViews(unittest.TestCase):
    def test_baseline_view_serializes(self):
        from umh.workstation_optimization.views import baseline_category_to_view
        from umh.workstation_optimization.baseline import build_default_baseline_categories

        cats = build_default_baseline_categories()
        v = baseline_category_to_view(cats[0])
        d = v.to_dict()
        self.assertIn("area", d)

    def test_candidate_view_serializes(self):
        from umh.workstation_optimization.views import optimization_candidate_to_view
        from umh.workstation_optimization.recommendations import (
            build_onboarding_optimization_recommendations,
        )

        recs = build_onboarding_optimization_recommendations()
        v = optimization_candidate_to_view(recs[0])
        d = v.to_dict()
        self.assertIn("action_type", d)

    def test_literacy_view_serializes(self):
        from umh.workstation_optimization.views import literacy_explanation_to_view
        from umh.workstation_optimization.device_literacy import (
            build_default_device_literacy_explanations,
        )

        exps = build_default_device_literacy_explanations()
        v = literacy_explanation_to_view(exps[0])
        d = v.to_dict()
        self.assertIn("topic", d)

    def test_performance_advisory_view_serializes(self):
        from umh.workstation_optimization.views import performance_advisory_to_view
        from umh.workstation_optimization.performance_tuning import (
            create_performance_tuning_advisory,
        )

        adv = create_performance_tuning_advisory(PerformanceTuningCategory.OVERCLOCKING)
        v = performance_advisory_to_view(adv)
        d = v.to_dict()
        self.assertIn("category", d)

    def test_report_view_serializes(self):
        from umh.workstation_optimization.views import report_to_view
        from umh.workstation_optimization.recommendations import (
            build_workstation_optimization_report,
        )

        rpt = build_workstation_optimization_report()
        v = report_to_view(rpt)
        d = v.to_dict()
        self.assertIn("candidate_count", d)

    def test_dashboard_view_serializes(self):
        from umh.workstation_optimization.views import build_workstation_optimization_dashboard_view
        from umh.workstation_optimization.recommendations import (
            build_workstation_optimization_report,
        )

        rpt = build_workstation_optimization_report()
        v = build_workstation_optimization_dashboard_view(rpt)
        d = v.to_dict()
        self.assertIn("total_categories", d)

    def test_views_omit_secrets(self):
        from umh.workstation_optimization.views import report_to_view
        from umh.workstation_optimization.recommendations import (
            build_workstation_optimization_report,
        )

        rpt = build_workstation_optimization_report()
        v = report_to_view(rpt)
        d = str(v.to_dict())
        for secret_word in ("password", "api_key", "token", "secret"):
            self.assertNotIn(secret_word, d.lower())


class TestSafety(unittest.TestCase):
    def test_safety_scan_passes(self):
        from umh.workstation_optimization.safety import check_all_workstation_optimization_modules

        r = check_all_workstation_optimization_modules()
        self.assertTrue(r["all_safe"], f"Safety violations: {r}")
        self.assertGreaterEqual(r["modules_checked"], 11)

    def test_detects_subprocess(self):
        from umh.workstation_optimization.safety import check_module_safety

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("import subprocess\n")
            f.flush()
            r = check_module_safety(f.name)
            self.assertFalse(r["safe"])

    def test_detects_shutil(self):
        from umh.workstation_optimization.safety import check_module_safety

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("import shutil\n")
            f.flush()
            r = check_module_safety(f.name)
            self.assertFalse(r["safe"])

    def test_detects_unlink_pattern(self):
        from umh.workstation_optimization.safety import check_module_safety

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("def unlink():\n    pass\n")
            f.flush()
            r = check_module_safety(f.name)
            self.assertFalse(r["safe"])

    def test_detects_requests(self):
        from umh.workstation_optimization.safety import check_module_safety

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("import requests\n")
            f.flush()
            r = check_module_safety(f.name)
            self.assertFalse(r["safe"])

    def test_detects_selenium(self):
        from umh.workstation_optimization.safety import check_module_safety

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("import selenium\n")
            f.flush()
            r = check_module_safety(f.name)
            self.assertFalse(r["safe"])

    def test_detects_adapter_import(self):
        from umh.workstation_optimization.safety import check_module_safety

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("from umh.adapters.gmail import fetch\n")
            f.flush()
            r = check_module_safety(f.name)
            self.assertFalse(r["safe"])

    def test_detects_execution_pattern(self):
        from umh.workstation_optimization.safety import check_module_safety

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("def execute():\n    pass\n")
            f.flush()
            r = check_module_safety(f.name)
            self.assertFalse(r["safe"])

    def test_detects_storage_mutation(self):
        from umh.workstation_optimization.safety import check_module_safety

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("from umh.storage.writer import save\n")
            f.flush()
            r = check_module_safety(f.name)
            self.assertFalse(r["safe"])

    def test_detects_governance_mutation(self):
        from umh.workstation_optimization.safety import check_module_safety

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("from umh.governance.engine import approve\n")
            f.flush()
            r = check_module_safety(f.name)
            self.assertFalse(r["safe"])

    def test_detects_memory_promotion(self):
        from umh.workstation_optimization.safety import check_module_safety

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("def promote_memory():\n    pass\n")
            f.flush()
            r = check_module_safety(f.name)
            self.assertFalse(r["safe"])

    def test_detects_kill_pattern(self):
        from umh.workstation_optimization.safety import check_module_safety

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("def kill():\n    pass\n")
            f.flush()
            r = check_module_safety(f.name)
            self.assertFalse(r["safe"])

    def test_detects_system_call_pattern(self):
        from umh.workstation_optimization.safety import check_module_safety

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("import subprocess\nsubprocess.run(['ls'])\n")
            f.flush()
            r = check_module_safety(f.name)
            self.assertFalse(r["safe"])

    def test_candidate_has_no_execution(self):
        from umh.workstation_optimization.safety import validate_candidate_has_no_execution

        c = OptimizationCandidate(action_type=OptimizationActionType.RECOMMEND)
        r = validate_candidate_has_no_execution(c)
        self.assertTrue(r["safe"])

    def test_report_has_no_real_scan_data(self):
        from umh.workstation_optimization.safety import validate_report_has_no_real_scan_data
        from umh.workstation_optimization.recommendations import (
            build_workstation_optimization_report,
        )

        rpt = build_workstation_optimization_report()
        r = validate_report_has_no_real_scan_data(rpt)
        self.assertTrue(r["safe"])


class TestDocUpdates(unittest.TestCase):
    def test_doctrine_index_includes_local_workstation(self):
        from pathlib import Path

        text = Path("docs/strategy/current_doctrine_index.md").read_text()
        self.assertIn("Local Workstation Onboarding Doctrine", text)

    def test_doctrine_index_includes_device_literacy(self):
        from pathlib import Path

        text = Path("docs/strategy/current_doctrine_index.md").read_text()
        self.assertIn("Device Literacy Doctrine", text)

    def test_doctrine_index_includes_performance_tuning_safety(self):
        from pathlib import Path

        text = Path("docs/strategy/current_doctrine_index.md").read_text()
        self.assertIn("Performance Tuning Safety Doctrine", text)

    def test_doctrine_index_includes_destructive_action_approval(self):
        from pathlib import Path

        text = Path("docs/strategy/current_doctrine_index.md").read_text()
        self.assertIn("Destructive Action Approval Doctrine", text)

    def test_source_ingestion_map_includes_workstation_baseline(self):
        from pathlib import Path

        text = Path("docs/strategy/source_ingestion_map.md").read_text()
        self.assertIn("Local Workstation Baseline", text)

    def test_war_sprint_manifest_references_phase_87c(self):
        from pathlib import Path

        text = Path("docs/strategy/war_sprint_context_manifest.md").read_text()
        self.assertIn("87C", text)


class TestRegression(unittest.TestCase):
    def test_phase87b_importable(self):
        from umh.ingestion.contracts import SourceClass

        self.assertTrue(hasattr(SourceClass, "EMAIL"))

    def test_phase87a_importable(self):
        from umh.distributed.contracts import RuntimeNodeType

        self.assertTrue(hasattr(RuntimeNodeType, "VPS"))

    def test_phase87_importable(self):
        from umh.leverage.contracts import LeverageType

        self.assertTrue(hasattr(LeverageType, "CODE_SOFTWARE"))

    def test_phase86_importable(self):
        from umh.tomorrow.contracts import DailyObjective

        self.assertTrue(hasattr(DailyObjective, "objective_id"))


if __name__ == "__main__":
    unittest.main()
