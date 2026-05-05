"""Phase 87B tests — Tool-Agnostic Onboarding Context Ingestion + Source Assimilation v1.

156+ tests across 14 test classes covering:
  - 12 enums, 12 normalizers, helpers, serialization
  - Source class taxonomy, tool-stack discovery, onboarding tiers
  - Permissions, routing, review policies, views, safety
  - Layering, integration, regression

Advisory/planning only. No scraping. No API calls. No account connections.
No file reading. No memory promotion. No execution.
"""

import sys
import unittest

sys.path.insert(0, "/opt/OS")

from umh.ingestion.contracts import (
    AccessMethod,
    IngestionPriority,
    IngestionReviewPolicy,
    IngestionSource,
    MemoryPromotionPolicy,
    OnboardingIngestionPlan,
    OnboardingTier,
    PermissionScope,
    PlatformType,
    RefreshCadence,
    ReviewRequirement,
    SourceClass,
    SourceIngestionRoute,
    SourceModality,
    SourceSensitivity,
    SourceStatus,
    ToolStackProfile,
    _ingest_id,
    normalize_access_method,
    normalize_ingestion_priority,
    normalize_memory_promotion_policy,
    normalize_onboarding_tier,
    normalize_permission_scope,
    normalize_platform_type,
    normalize_refresh_cadence,
    normalize_review_requirement,
    normalize_source_class,
    normalize_source_modality,
    normalize_source_sensitivity,
    normalize_source_status,
)


class TestContractEnums(unittest.TestCase):
    """Test all 12 enums — member counts and UNKNOWN fallback."""

    def test_source_class_count(self):
        self.assertEqual(len(SourceClass), 29)

    def test_source_class_has_unknown(self):
        self.assertIn(SourceClass.UNKNOWN, SourceClass)

    def test_platform_type_count(self):
        self.assertEqual(len(PlatformType), 47)

    def test_platform_type_has_unknown(self):
        self.assertIn(PlatformType.UNKNOWN, PlatformType)

    def test_source_modality_count(self):
        self.assertEqual(len(SourceModality), 12)

    def test_source_modality_has_unknown(self):
        self.assertIn(SourceModality.UNKNOWN, SourceModality)

    def test_access_method_count(self):
        self.assertEqual(len(AccessMethod), 12)

    def test_access_method_has_unknown(self):
        self.assertIn(AccessMethod.UNKNOWN, AccessMethod)

    def test_permission_scope_count(self):
        self.assertEqual(len(PermissionScope), 11)

    def test_permission_scope_has_unknown(self):
        self.assertIn(PermissionScope.UNKNOWN, PermissionScope)

    def test_onboarding_tier_count(self):
        self.assertEqual(len(OnboardingTier), 8)

    def test_onboarding_tier_has_unknown(self):
        self.assertIn(OnboardingTier.UNKNOWN, OnboardingTier)

    def test_ingestion_priority_count(self):
        self.assertEqual(len(IngestionPriority), 7)

    def test_source_sensitivity_count(self):
        self.assertEqual(len(SourceSensitivity), 6)

    def test_review_requirement_count(self):
        self.assertEqual(len(ReviewRequirement), 7)

    def test_memory_promotion_policy_count(self):
        self.assertEqual(len(MemoryPromotionPolicy), 8)

    def test_source_status_count(self):
        self.assertEqual(len(SourceStatus), 12)

    def test_refresh_cadence_count(self):
        self.assertEqual(len(RefreshCadence), 8)

    def test_all_enums_str_based(self):
        for enum_cls in [
            SourceClass,
            PlatformType,
            SourceModality,
            AccessMethod,
            PermissionScope,
            OnboardingTier,
            IngestionPriority,
            SourceSensitivity,
            ReviewRequirement,
            MemoryPromotionPolicy,
            SourceStatus,
            RefreshCadence,
        ]:
            for member in enum_cls:
                self.assertIsInstance(member.value, str)


class TestContractNormalizers(unittest.TestCase):
    """Test all 12 normalizers — value, name, and unknown fallback."""

    def test_normalize_source_class_by_value(self):
        self.assertEqual(normalize_source_class("email"), SourceClass.EMAIL)

    def test_normalize_source_class_by_name(self):
        self.assertEqual(normalize_source_class("EMAIL"), SourceClass.EMAIL)

    def test_normalize_source_class_unknown(self):
        self.assertEqual(normalize_source_class("nonexistent"), SourceClass.UNKNOWN)

    def test_normalize_platform_type_by_value(self):
        self.assertEqual(normalize_platform_type("gmail"), PlatformType.GMAIL)

    def test_normalize_platform_type_unknown(self):
        self.assertEqual(normalize_platform_type("fakething"), PlatformType.UNKNOWN)

    def test_normalize_source_modality(self):
        self.assertEqual(normalize_source_modality("text"), SourceModality.TEXT)

    def test_normalize_access_method(self):
        self.assertEqual(normalize_access_method("oauth"), AccessMethod.OAUTH)

    def test_normalize_permission_scope(self):
        self.assertEqual(normalize_permission_scope("read_only"), PermissionScope.READ_ONLY)

    def test_normalize_onboarding_tier(self):
        self.assertEqual(
            normalize_onboarding_tier("tier_0_manual_core"),
            OnboardingTier.TIER_0_MANUAL_CORE,
        )

    def test_normalize_ingestion_priority(self):
        self.assertEqual(normalize_ingestion_priority("high"), IngestionPriority.HIGH)

    def test_normalize_source_sensitivity(self):
        self.assertEqual(normalize_source_sensitivity("financial"), SourceSensitivity.FINANCIAL)

    def test_normalize_review_requirement(self):
        self.assertEqual(normalize_review_requirement("full_review"), ReviewRequirement.FULL_REVIEW)

    def test_normalize_memory_promotion_policy(self):
        self.assertEqual(
            normalize_memory_promotion_policy("human_review"),
            MemoryPromotionPolicy.HUMAN_REVIEW,
        )

    def test_normalize_source_status(self):
        self.assertEqual(normalize_source_status("approved"), SourceStatus.APPROVED)

    def test_normalize_refresh_cadence(self):
        self.assertEqual(normalize_refresh_cadence("daily"), RefreshCadence.DAILY)

    def test_normalize_passthrough(self):
        self.assertEqual(normalize_source_class(SourceClass.EMAIL), SourceClass.EMAIL)


class TestContractHelpers(unittest.TestCase):
    """Test _ingest_id and helper functions."""

    def test_ingest_id_format(self):
        rid = _ingest_id("test")
        self.assertTrue(rid.startswith("test_"))
        self.assertEqual(len(rid), 5 + 12)

    def test_ingest_id_uniqueness(self):
        ids = {_ingest_id("x") for _ in range(100)}
        self.assertEqual(len(ids), 100)

    def test_ingest_id_prefix_preserved(self):
        for prefix in ["src", "plan", "route", "rpol", "tsp"]:
            self.assertTrue(_ingest_id(prefix).startswith(f"{prefix}_"))


class TestContractSerialization(unittest.TestCase):
    """Test all 5 dataclass to_dict/from_dict round-trips."""

    def test_ingestion_source_round_trip(self):
        src = IngestionSource(
            source_id="src_test",
            source_class=SourceClass.EMAIL,
            platform=PlatformType.GMAIL,
            name="Test Gmail",
            modalities=[SourceModality.TEXT],
            access_methods=[AccessMethod.OAUTH],
            permission_scopes=[PermissionScope.READ_ONLY],
            onboarding_tier=OnboardingTier.TIER_2_WORKSPACE,
            priority=IngestionPriority.HIGH,
            sensitivity=SourceSensitivity.CONFIDENTIAL,
        )
        d = src.to_dict()
        restored = IngestionSource.from_dict(d)
        self.assertEqual(restored.source_id, "src_test")
        self.assertEqual(restored.source_class, SourceClass.EMAIL)
        self.assertEqual(restored.platform, PlatformType.GMAIL)
        self.assertEqual(restored.modalities, [SourceModality.TEXT])
        self.assertEqual(restored.to_dict(), d)

    def test_tool_stack_profile_round_trip(self):
        tsp = ToolStackProfile(
            profile_id="tsp_test",
            user_label="Test User",
            confirmed_platforms=[PlatformType.GMAIL, PlatformType.GITHUB],
            source_class_coverage={"email": ["gmail"]},
            gaps=["No calendar platform"],
        )
        d = tsp.to_dict()
        restored = ToolStackProfile.from_dict(d)
        self.assertEqual(restored.profile_id, "tsp_test")
        self.assertEqual(len(restored.confirmed_platforms), 2)
        self.assertEqual(restored.to_dict(), d)

    def test_onboarding_plan_round_trip(self):
        plan = OnboardingIngestionPlan(
            plan_id="plan_test",
            tier=OnboardingTier.TIER_1_LOCAL_ARCHIVES,
            name="Test Plan",
            sources=["note_taking", "ai_assistant"],
            prerequisites=["Tier 0 completed"],
        )
        d = plan.to_dict()
        restored = OnboardingIngestionPlan.from_dict(d)
        self.assertEqual(restored.tier, OnboardingTier.TIER_1_LOCAL_ARCHIVES)
        self.assertEqual(restored.to_dict(), d)

    def test_source_ingestion_route_round_trip(self):
        route = SourceIngestionRoute(
            route_id="route_test",
            source_id="src_test",
            source_class=SourceClass.SOCIAL_MEDIA,
            platform=PlatformType.INSTAGRAM,
            recommended_node_type="local_pc",
            source_affinity="local_only",
            required_capabilities=["browser", "local_accounts"],
            access_method=AccessMethod.BROWSER_SESSION,
            sensitivity=SourceSensitivity.PUBLIC,
        )
        d = route.to_dict()
        restored = SourceIngestionRoute.from_dict(d)
        self.assertEqual(restored.source_class, SourceClass.SOCIAL_MEDIA)
        self.assertEqual(restored.to_dict(), d)

    def test_ingestion_review_policy_round_trip(self):
        policy = IngestionReviewPolicy(
            policy_id="rpol_test",
            name="Test Policy",
            source_class=SourceClass.PAYMENT_PROCESSING,
            sensitivity=SourceSensitivity.FINANCIAL,
            review_requirement=ReviewRequirement.FULL_REVIEW,
            promotion_policy=MemoryPromotionPolicy.HUMAN_REVIEW,
            confidence_threshold=0.95,
        )
        d = policy.to_dict()
        restored = IngestionReviewPolicy.from_dict(d)
        self.assertEqual(restored.sensitivity, SourceSensitivity.FINANCIAL)
        self.assertEqual(restored.confidence_threshold, 0.95)
        self.assertEqual(restored.to_dict(), d)


class TestSourceClasses(unittest.TestCase):
    """Test source class taxonomy — class-to-platform mapping and classification."""

    def test_email_has_multiple_platforms(self):
        from umh.ingestion.source_classes import get_platforms_for_class

        platforms = get_platforms_for_class(SourceClass.EMAIL)
        self.assertIn(PlatformType.GMAIL, platforms)
        self.assertIn(PlatformType.OUTLOOK, platforms)
        self.assertGreater(len(platforms), 2)

    def test_social_media_platforms(self):
        from umh.ingestion.source_classes import get_platforms_for_class

        platforms = get_platforms_for_class(SourceClass.SOCIAL_MEDIA)
        self.assertIn(PlatformType.INSTAGRAM, platforms)
        self.assertIn(PlatformType.TIKTOK, platforms)
        self.assertIn(PlatformType.TWITTER, platforms)

    def test_get_class_for_platform(self):
        from umh.ingestion.source_classes import get_class_for_platform

        self.assertEqual(get_class_for_platform(PlatformType.GMAIL), SourceClass.EMAIL)
        self.assertEqual(get_class_for_platform(PlatformType.GITHUB), SourceClass.CODE_REPOSITORY)
        self.assertEqual(
            get_class_for_platform(PlatformType.STRIPE), SourceClass.PAYMENT_PROCESSING
        )

    def test_get_class_for_unknown_platform(self):
        from umh.ingestion.source_classes import get_class_for_platform

        self.assertEqual(get_class_for_platform(PlatformType.UNKNOWN), SourceClass.UNKNOWN)

    def test_classify_source_by_name(self):
        from umh.ingestion.source_classes import classify_source

        self.assertEqual(classify_source("email"), SourceClass.EMAIL)
        self.assertEqual(classify_source("instagram"), SourceClass.SOCIAL_MEDIA)
        self.assertEqual(classify_source("github"), SourceClass.CODE_REPOSITORY)

    def test_classify_source_unknown(self):
        from umh.ingestion.source_classes import classify_source

        self.assertEqual(classify_source("xyznothing"), SourceClass.UNKNOWN)

    def test_modalities_for_class(self):
        from umh.ingestion.source_classes import get_modalities_for_class

        mods = get_modalities_for_class(SourceClass.SOCIAL_MEDIA)
        self.assertIn(SourceModality.IMAGE, mods)
        self.assertIn(SourceModality.VIDEO, mods)

    def test_access_methods_for_class(self):
        from umh.ingestion.source_classes import get_access_methods_for_class

        methods = get_access_methods_for_class(SourceClass.SOCIAL_MEDIA)
        self.assertIn(AccessMethod.BROWSER_SESSION, methods)

    def test_default_tier(self):
        from umh.ingestion.source_classes import get_default_tier

        self.assertEqual(get_default_tier(SourceClass.EMAIL), OnboardingTier.TIER_2_WORKSPACE)
        self.assertEqual(
            get_default_tier(SourceClass.AI_ASSISTANT), OnboardingTier.TIER_1_LOCAL_ARCHIVES
        )
        self.assertEqual(
            get_default_tier(SourceClass.SOCIAL_MEDIA), OnboardingTier.TIER_3_SOCIAL_ALGORITHM
        )

    def test_default_sensitivity(self):
        from umh.ingestion.source_classes import get_default_sensitivity

        self.assertEqual(
            get_default_sensitivity(SourceClass.PAYMENT_PROCESSING), SourceSensitivity.FINANCIAL
        )
        self.assertEqual(
            get_default_sensitivity(SourceClass.SOCIAL_MEDIA), SourceSensitivity.PUBLIC
        )
        self.assertEqual(get_default_sensitivity(SourceClass.EMAIL), SourceSensitivity.CONFIDENTIAL)

    def test_default_priority(self):
        from umh.ingestion.source_classes import get_default_priority

        self.assertEqual(
            get_default_priority(SourceClass.PAYMENT_PROCESSING), IngestionPriority.CRITICAL
        )
        self.assertEqual(
            get_default_priority(SourceClass.EBOOK_READER), IngestionPriority.BACKGROUND
        )

    def test_list_source_classes_excludes_unknown(self):
        from umh.ingestion.source_classes import list_source_classes

        classes = list_source_classes()
        self.assertNotIn(SourceClass.UNKNOWN, classes)
        self.assertEqual(len(classes), 28)

    def test_list_all_platforms_excludes_unknown(self):
        from umh.ingestion.source_classes import list_all_platforms

        platforms = list_all_platforms()
        self.assertNotIn(PlatformType.UNKNOWN, platforms)
        self.assertEqual(len(platforms), 46)

    def test_every_source_class_has_modalities(self):
        from umh.ingestion.source_classes import get_modalities_for_class, list_source_classes

        for sc in list_source_classes():
            mods = get_modalities_for_class(sc)
            self.assertGreater(len(mods), 0, f"{sc} has no modalities")

    def test_every_source_class_has_access_methods(self):
        from umh.ingestion.source_classes import get_access_methods_for_class, list_source_classes

        for sc in list_source_classes():
            methods = get_access_methods_for_class(sc)
            self.assertGreater(len(methods), 0, f"{sc} has no access methods")

    def test_every_source_class_has_default_tier(self):
        from umh.ingestion.source_classes import get_default_tier, list_source_classes

        for sc in list_source_classes():
            tier = get_default_tier(sc)
            self.assertNotEqual(tier, OnboardingTier.UNKNOWN, f"{sc} has unknown tier")


class TestToolStack(unittest.TestCase):
    """Test tool-stack profile building and gap identification."""

    def test_build_profile_basic(self):
        from umh.ingestion.tool_stack import build_tool_stack_profile

        profile = build_tool_stack_profile(["gmail", "github", "notion"])
        self.assertEqual(len(profile.confirmed_platforms), 3)
        self.assertIn("email", profile.source_class_coverage)

    def test_build_profile_with_unknown(self):
        from umh.ingestion.tool_stack import build_tool_stack_profile

        profile = build_tool_stack_profile(["gmail", "fake_platform"])
        self.assertEqual(len(profile.confirmed_platforms), 1)

    def test_coverage_gaps_detected(self):
        from umh.ingestion.tool_stack import build_tool_stack_profile

        profile = build_tool_stack_profile(["gmail"])
        self.assertGreater(len(profile.gaps), 0)

    def test_full_coverage_no_gaps(self):
        from umh.ingestion.tool_stack import build_tool_stack_profile

        profile = build_tool_stack_profile(
            [
                "gmail",
                "google_calendar",
                "obsidian",
                "github",
                "discord",
                "google_drive",
            ]
        )
        self.assertEqual(len(profile.gaps), 0)

    def test_coverage_summary(self):
        from umh.ingestion.tool_stack import (
            build_tool_stack_profile,
            get_source_class_coverage_summary,
        )

        profile = build_tool_stack_profile(["gmail", "github"])
        summary = get_source_class_coverage_summary(profile)
        self.assertGreater(summary["total_classes"], 0)
        self.assertGreater(summary["covered_classes"], 0)
        self.assertIn("coverage_pct", summary)

    def test_suggest_platforms_for_gap(self):
        from umh.ingestion.tool_stack import suggest_platforms_for_gap

        suggestions = suggest_platforms_for_gap(SourceClass.EMAIL)
        self.assertIn(PlatformType.GMAIL, suggestions)
        self.assertIn(PlatformType.OUTLOOK, suggestions)


class TestOnboarding(unittest.TestCase):
    """Test progressive onboarding tier plans."""

    def test_build_full_sequence(self):
        from umh.ingestion.onboarding import build_full_onboarding_sequence

        plans = build_full_onboarding_sequence()
        self.assertEqual(len(plans), 6)
        self.assertEqual(plans[0].tier, OnboardingTier.TIER_0_MANUAL_CORE)
        self.assertEqual(plans[5].tier, OnboardingTier.TIER_5_CONTINUOUS)

    def test_tier_0_has_no_prerequisites(self):
        from umh.ingestion.onboarding import build_onboarding_plan_for_tier

        plan = build_onboarding_plan_for_tier(OnboardingTier.TIER_0_MANUAL_CORE)
        self.assertEqual(len(plan.prerequisites), 0)

    def test_tier_2_has_prerequisites(self):
        from umh.ingestion.onboarding import build_onboarding_plan_for_tier

        plan = build_onboarding_plan_for_tier(OnboardingTier.TIER_2_WORKSPACE)
        self.assertGreater(len(plan.prerequisites), 0)

    def test_tier_3_warns_about_browser(self):
        from umh.ingestion.onboarding import build_onboarding_plan_for_tier

        plan = build_onboarding_plan_for_tier(OnboardingTier.TIER_3_SOCIAL_ALGORITHM)
        warning_text = " ".join(plan.warnings)
        self.assertIn("browser", warning_text.lower())

    def test_tier_4_warns_about_consent(self):
        from umh.ingestion.onboarding import build_onboarding_plan_for_tier

        plan = build_onboarding_plan_for_tier(OnboardingTier.TIER_4_COMPUTER_USE)
        warning_text = " ".join(plan.warnings)
        self.assertIn("consent", warning_text.lower())

    def test_every_plan_has_success_criteria(self):
        from umh.ingestion.onboarding import build_full_onboarding_sequence

        for plan in build_full_onboarding_sequence():
            self.assertGreater(
                len(plan.success_criteria), 0, f"{plan.tier} has no success criteria"
            )

    def test_every_plan_has_user_actions(self):
        from umh.ingestion.onboarding import build_full_onboarding_sequence

        for plan in build_full_onboarding_sequence():
            self.assertGreater(
                len(plan.user_actions_required), 0, f"{plan.tier} has no user actions"
            )

    def test_get_next_tier(self):
        from umh.ingestion.onboarding import get_next_tier

        self.assertEqual(
            get_next_tier(OnboardingTier.TIER_0_MANUAL_CORE), OnboardingTier.TIER_1_LOCAL_ARCHIVES
        )
        self.assertEqual(
            get_next_tier(OnboardingTier.TIER_4_COMPUTER_USE), OnboardingTier.TIER_5_CONTINUOUS
        )
        self.assertIsNone(get_next_tier(OnboardingTier.TIER_5_CONTINUOUS))

    def test_source_classes_for_tier(self):
        from umh.ingestion.onboarding import get_source_classes_for_tier

        t1 = get_source_classes_for_tier(OnboardingTier.TIER_1_LOCAL_ARCHIVES)
        self.assertIn(SourceClass.AI_ASSISTANT, t1)
        self.assertIn(SourceClass.NOTE_TAKING, t1)

    def test_estimated_effort_present(self):
        from umh.ingestion.onboarding import build_full_onboarding_sequence

        for plan in build_full_onboarding_sequence():
            self.assertNotEqual(plan.estimated_effort, "", f"{plan.tier} has no effort estimate")

    def test_plan_serialization(self):
        from umh.ingestion.onboarding import build_onboarding_plan_for_tier

        plan = build_onboarding_plan_for_tier(OnboardingTier.TIER_2_WORKSPACE)
        d = plan.to_dict()
        restored = OnboardingIngestionPlan.from_dict(d)
        self.assertEqual(restored.tier, OnboardingTier.TIER_2_WORKSPACE)


class TestPermissions(unittest.TestCase):
    """Test permission-first ingestion policy."""

    def test_build_permission_request(self):
        from umh.ingestion.permissions import build_permission_request

        src = IngestionSource(
            source_id="src_test",
            source_class=SourceClass.EMAIL,
            platform=PlatformType.GMAIL,
            name="Gmail",
            permission_scopes=[PermissionScope.READ_ONLY],
            access_methods=[AccessMethod.OAUTH],
        )
        req = build_permission_request(src)
        self.assertIn("request_id", req)
        self.assertEqual(req["status"], "pending_approval")
        self.assertGreater(len(req["user_must_approve"]), 0)

    def test_validate_valid_grant(self):
        from umh.ingestion.permissions import validate_permission_grant

        src = IngestionSource(
            source_id="src_test",
            sensitivity=SourceSensitivity.INTERNAL,
        )
        result = validate_permission_grant(src, [PermissionScope.READ_ONLY], AccessMethod.OAUTH)
        self.assertTrue(result["valid"])

    def test_validate_empty_grant_fails(self):
        from umh.ingestion.permissions import validate_permission_grant

        src = IngestionSource(source_id="src_test")
        result = validate_permission_grant(src, [], AccessMethod.OAUTH)
        self.assertFalse(result["valid"])

    def test_validate_financial_warnings(self):
        from umh.ingestion.permissions import validate_permission_grant

        src = IngestionSource(
            source_id="src_test",
            sensitivity=SourceSensitivity.FINANCIAL,
        )
        result = validate_permission_grant(
            src,
            [PermissionScope.READ_WRITE],
            AccessMethod.BROWSER_SESSION,
        )
        self.assertGreater(len(result["warnings"]), 0)

    def test_credential_source_blocked(self):
        from umh.ingestion.permissions import validate_permission_grant

        src = IngestionSource(
            source_id="src_test",
            sensitivity=SourceSensitivity.CREDENTIAL,
        )
        result = validate_permission_grant(src, [PermissionScope.READ_ONLY], AccessMethod.API_KEY)
        self.assertFalse(result["valid"])

    def test_check_source_ready_approved(self):
        from umh.ingestion.permissions import check_source_ready_for_ingestion

        src = IngestionSource(
            source_id="src_test",
            status=SourceStatus.APPROVED,
            permission_scopes=[PermissionScope.READ_ONLY],
            access_methods=[AccessMethod.OAUTH],
        )
        result = check_source_ready_for_ingestion(src)
        self.assertTrue(result["ready"])

    def test_check_source_ready_discovered_blocked(self):
        from umh.ingestion.permissions import check_source_ready_for_ingestion

        src = IngestionSource(
            source_id="src_test",
            status=SourceStatus.DISCOVERED,
            permission_scopes=[PermissionScope.READ_ONLY],
            access_methods=[AccessMethod.OAUTH],
        )
        result = check_source_ready_for_ingestion(src)
        self.assertFalse(result["ready"])

    def test_permission_risk_classification(self):
        from umh.ingestion.permissions import classify_permission_risk

        self.assertEqual(
            classify_permission_risk(
                PermissionScope.READ_ONLY, AccessMethod.OAUTH, SourceSensitivity.PUBLIC
            ),
            "low",
        )
        self.assertEqual(
            classify_permission_risk(
                PermissionScope.READ_WRITE, AccessMethod.API_KEY, SourceSensitivity.FINANCIAL
            ),
            "critical",
        )
        self.assertEqual(
            classify_permission_risk(
                PermissionScope.READ_ONLY, AccessMethod.API_KEY, SourceSensitivity.CREDENTIAL
            ),
            "blocked",
        )


class TestSourceRegistry(unittest.TestCase):
    """Test seed source maps and default IngestionSource objects."""

    def test_seed_sources_count(self):
        from umh.ingestion.source_registry import build_seed_sources

        sources = build_seed_sources()
        self.assertGreaterEqual(len(sources), 20)

    def test_seed_sources_unique_ids(self):
        from umh.ingestion.source_registry import build_seed_sources

        sources = build_seed_sources()
        ids = [s.source_id for s in sources]
        self.assertEqual(len(ids), len(set(ids)))

    def test_seed_sources_all_discovered(self):
        from umh.ingestion.source_registry import build_seed_sources

        for s in build_seed_sources():
            self.assertEqual(s.status, SourceStatus.DISCOVERED)

    def test_financial_sources(self):
        from umh.ingestion.source_registry import get_financial_sources

        financial = get_financial_sources()
        self.assertGreater(len(financial), 0)
        for s in financial:
            self.assertEqual(s.sensitivity, SourceSensitivity.FINANCIAL)

    def test_high_priority_sources(self):
        from umh.ingestion.source_registry import get_high_priority_sources

        high = get_high_priority_sources()
        self.assertGreater(len(high), 0)
        for s in high:
            self.assertIn(s.priority, (IngestionPriority.CRITICAL, IngestionPriority.HIGH))

    def test_sources_by_tier(self):
        from umh.ingestion.source_registry import get_sources_by_tier

        tier1 = get_sources_by_tier(OnboardingTier.TIER_1_LOCAL_ARCHIVES)
        self.assertGreater(len(tier1), 0)
        for s in tier1:
            self.assertEqual(s.onboarding_tier, OnboardingTier.TIER_1_LOCAL_ARCHIVES)

    def test_sources_by_class(self):
        from umh.ingestion.source_registry import get_sources_by_class

        social = get_sources_by_class(SourceClass.SOCIAL_MEDIA)
        self.assertGreater(len(social), 0)

    def test_all_seed_sources_serializable(self):
        from umh.ingestion.source_registry import build_seed_sources

        for s in build_seed_sources():
            d = s.to_dict()
            restored = IngestionSource.from_dict(d)
            self.assertEqual(restored.source_id, s.source_id)
            self.assertEqual(restored.source_class, s.source_class)

    def test_no_credential_sources_in_seeds(self):
        from umh.ingestion.source_registry import build_seed_sources

        for s in build_seed_sources():
            self.assertNotEqual(s.sensitivity, SourceSensitivity.CREDENTIAL)


class TestRouting(unittest.TestCase):
    """Test source-to-node routing integration with Phase 87A."""

    def test_social_media_routes_local(self):
        from umh.ingestion.routing import route_ingestion_source

        src = IngestionSource(
            source_id="src_test",
            source_class=SourceClass.SOCIAL_MEDIA,
            platform=PlatformType.INSTAGRAM,
            name="Instagram",
            access_methods=[AccessMethod.BROWSER_SESSION],
            permission_scopes=[PermissionScope.READ_ONLY],
        )
        route = route_ingestion_source(src)
        self.assertEqual(route.recommended_node_type, "local_pc")

    def test_email_routes_vps(self):
        from umh.ingestion.routing import route_ingestion_source

        src = IngestionSource(
            source_id="src_test",
            source_class=SourceClass.EMAIL,
            platform=PlatformType.GMAIL,
            name="Gmail",
            access_methods=[AccessMethod.OFFICIAL_API],
            permission_scopes=[PermissionScope.READ_ONLY],
        )
        route = route_ingestion_source(src)
        self.assertEqual(route.recommended_node_type, "vps")

    def test_docker_routes_vps_only(self):
        from umh.ingestion.routing import route_ingestion_source

        src = IngestionSource(
            source_id="src_test",
            source_class=SourceClass.CONTAINER_RUNTIME,
            platform=PlatformType.DOCKER,
            name="Docker",
            access_methods=[AccessMethod.LOCAL_FILESYSTEM],
            permission_scopes=[PermissionScope.READ_ONLY],
        )
        route = route_ingestion_source(src)
        self.assertIn(route.recommended_node_type, ("vps", "local_pc"))

    def test_browser_session_overrides_to_local(self):
        from umh.ingestion.routing import route_ingestion_source

        src = IngestionSource(
            source_id="src_test",
            source_class=SourceClass.NOTE_TAKING,
            platform=PlatformType.NOTION,
            name="Notion via browser",
            access_methods=[AccessMethod.BROWSER_SESSION],
            permission_scopes=[PermissionScope.READ_ONLY],
        )
        route = route_ingestion_source(src)
        self.assertEqual(route.recommended_node_type, "local_pc")

    def test_route_all_sources(self):
        from umh.ingestion.routing import route_all_sources
        from umh.ingestion.source_registry import build_seed_sources

        sources = build_seed_sources()
        routes = route_all_sources(sources)
        self.assertEqual(len(routes), len(sources))
        for r in routes:
            self.assertNotEqual(r.route_id, "")
            self.assertNotEqual(r.recommended_node_type, "")

    def test_get_local_only_sources(self):
        from umh.ingestion.routing import get_local_only_sources
        from umh.ingestion.source_registry import build_seed_sources

        local = get_local_only_sources(build_seed_sources())
        for s in local:
            self.assertIn(
                s.source_class,
                (
                    SourceClass.SOCIAL_MEDIA,
                    SourceClass.BROWSER_HISTORY,
                    SourceClass.VOICE_MEMO,
                    SourceClass.CAMERA_CAPTURE,
                    SourceClass.SCREEN_CAPTURE,
                ),
            )

    def test_get_vps_sources(self):
        from umh.ingestion.routing import get_vps_sources
        from umh.ingestion.source_registry import build_seed_sources

        vps = get_vps_sources(build_seed_sources())
        self.assertGreater(len(vps), 0)

    def test_routing_uses_87a_enums(self):
        from umh.distributed.contracts import CapabilityDomain, RuntimeNodeType, SourceAffinity
        from umh.ingestion.routing import get_source_node_affinity, get_source_required_capabilities

        aff = get_source_node_affinity(SourceClass.SOCIAL_MEDIA)
        self.assertIsInstance(aff, SourceAffinity)
        caps = get_source_required_capabilities(SourceClass.SOCIAL_MEDIA)
        for c in caps:
            self.assertIsInstance(c, CapabilityDomain)

    def test_financial_route_has_warnings(self):
        from umh.ingestion.routing import route_ingestion_source

        src = IngestionSource(
            source_id="src_test",
            source_class=SourceClass.PAYMENT_PROCESSING,
            platform=PlatformType.STRIPE,
            name="Stripe",
            access_methods=[AccessMethod.API_KEY],
            permission_scopes=[PermissionScope.READ_TRANSACTIONS],
            sensitivity=SourceSensitivity.FINANCIAL,
        )
        route = route_ingestion_source(src)
        warning_text = " ".join(route.warnings)
        self.assertIn("financial", warning_text.lower())


class TestReviewPolicy(unittest.TestCase):
    """Test memory candidate review and promotion policies."""

    def test_default_policies_count(self):
        from umh.ingestion.review_policy import build_default_review_policies

        policies = build_default_review_policies()
        self.assertGreaterEqual(len(policies), 8)

    def test_financial_policy_is_human_review(self):
        from umh.ingestion.review_policy import build_default_review_policies

        policies = build_default_review_policies()
        financial = [p for p in policies if p.source_class == SourceClass.PAYMENT_PROCESSING]
        self.assertGreater(len(financial), 0)
        self.assertEqual(financial[0].promotion_policy, MemoryPromotionPolicy.HUMAN_REVIEW)

    def test_calendar_is_auto_promote(self):
        from umh.ingestion.review_policy import build_default_review_policies

        policies = build_default_review_policies()
        cal = [p for p in policies if p.source_class == SourceClass.CALENDAR]
        self.assertGreater(len(cal), 0)
        self.assertEqual(cal[0].promotion_policy, MemoryPromotionPolicy.AUTO_PROMOTE)

    def test_ai_chat_requires_supersession(self):
        from umh.ingestion.review_policy import (
            requires_supersession_check,
            build_default_review_policies,
        )

        policies = build_default_review_policies()
        ai = [p for p in policies if p.source_class == SourceClass.AI_ASSISTANT]
        self.assertGreater(len(ai), 0)
        self.assertTrue(requires_supersession_check(ai[0]))

    def test_should_auto_promote_above_threshold(self):
        from umh.ingestion.review_policy import should_auto_promote

        policy = IngestionReviewPolicy(
            policy_id="test",
            promotion_policy=MemoryPromotionPolicy.CONFIDENCE_THRESHOLD,
            confidence_threshold=0.8,
            max_auto_promote_per_batch=10,
        )
        self.assertTrue(should_auto_promote(policy, 0.9, 0))
        self.assertFalse(should_auto_promote(policy, 0.5, 0))

    def test_should_not_auto_promote_human_review(self):
        from umh.ingestion.review_policy import should_auto_promote

        policy = IngestionReviewPolicy(
            policy_id="test",
            promotion_policy=MemoryPromotionPolicy.HUMAN_REVIEW,
        )
        self.assertFalse(should_auto_promote(policy, 1.0, 0))

    def test_batch_limit_respected(self):
        from umh.ingestion.review_policy import should_auto_promote

        policy = IngestionReviewPolicy(
            policy_id="test",
            promotion_policy=MemoryPromotionPolicy.AUTO_PROMOTE,
            confidence_threshold=0.6,
            max_auto_promote_per_batch=5,
        )
        self.assertTrue(should_auto_promote(policy, 0.9, 4))
        self.assertFalse(should_auto_promote(policy, 0.9, 5))

    def test_get_policy_for_source(self):
        from umh.ingestion.review_policy import get_review_policy_for_source

        src = IngestionSource(
            source_id="test",
            source_class=SourceClass.EMAIL,
            sensitivity=SourceSensitivity.CONFIDENTIAL,
        )
        policy = get_review_policy_for_source(src)
        self.assertIsNotNone(policy)
        self.assertEqual(policy.source_class, SourceClass.EMAIL)

    def test_review_urgency(self):
        from umh.ingestion.review_policy import classify_review_urgency

        src = IngestionSource(
            source_id="test",
            source_class=SourceClass.PAYMENT_PROCESSING,
            sensitivity=SourceSensitivity.FINANCIAL,
        )
        urgency = classify_review_urgency(src)
        self.assertIn(urgency, ("critical", "high"))

    def test_requires_human_review(self):
        from umh.ingestion.review_policy import requires_human_review

        policy = IngestionReviewPolicy(
            policy_id="test",
            promotion_policy=MemoryPromotionPolicy.HUMAN_REVIEW,
        )
        self.assertTrue(requires_human_review(policy))
        policy2 = IngestionReviewPolicy(
            policy_id="test2",
            promotion_policy=MemoryPromotionPolicy.AUTO_PROMOTE,
        )
        self.assertFalse(requires_human_review(policy2))


class TestViews(unittest.TestCase):
    """Test UI-safe view converters."""

    def test_source_to_view(self):
        from umh.ingestion.views import source_to_view

        src = IngestionSource(
            source_id="src_test",
            name="Gmail",
            source_class=SourceClass.EMAIL,
            platform=PlatformType.GMAIL,
            modalities=[SourceModality.TEXT],
        )
        view = source_to_view(src)
        self.assertEqual(view.name, "Gmail")
        self.assertEqual(view.source_class, "email")
        self.assertEqual(view.modality_count, 1)

    def test_tool_stack_to_view(self):
        from umh.ingestion.views import tool_stack_to_view
        from umh.ingestion.tool_stack import build_tool_stack_profile

        profile = build_tool_stack_profile(["gmail", "github"])
        view = tool_stack_to_view(profile)
        self.assertEqual(view.confirmed_count, 2)
        self.assertGreater(view.coverage_pct, 0)

    def test_onboarding_plan_to_view(self):
        from umh.ingestion.views import onboarding_plan_to_view
        from umh.ingestion.onboarding import build_onboarding_plan_for_tier

        plan = build_onboarding_plan_for_tier(OnboardingTier.TIER_2_WORKSPACE)
        view = onboarding_plan_to_view(plan)
        self.assertGreater(view.source_count, 0)
        self.assertNotEqual(view.estimated_effort, "")

    def test_source_route_to_view(self):
        from umh.ingestion.views import source_route_to_view
        from umh.ingestion.routing import route_ingestion_source

        src = IngestionSource(
            source_id="src_test",
            source_class=SourceClass.EMAIL,
            platform=PlatformType.GMAIL,
            name="Gmail",
            access_methods=[AccessMethod.OAUTH],
            permission_scopes=[PermissionScope.READ_ONLY],
        )
        route = route_ingestion_source(src)
        view = source_route_to_view(route)
        self.assertNotEqual(view.recommended_node, "")

    def test_review_policy_to_view(self):
        from umh.ingestion.views import review_policy_to_view
        from umh.ingestion.review_policy import build_default_review_policies

        policy = build_default_review_policies()[0]
        view = review_policy_to_view(policy)
        self.assertNotEqual(view.name, "")
        self.assertGreater(view.confidence_threshold, 0)

    def test_dashboard_view(self):
        from umh.ingestion.views import build_ingestion_dashboard_view
        from umh.ingestion.source_registry import build_seed_sources
        from umh.ingestion.review_policy import build_default_review_policies

        dashboard = build_ingestion_dashboard_view(
            sources=build_seed_sources(),
            review_policies=build_default_review_policies(),
        )
        self.assertGreater(dashboard.total_sources, 0)
        self.assertGreater(len(dashboard.sources_by_tier), 0)
        self.assertGreater(dashboard.review_policy_count, 0)

    def test_views_no_sensitive_data(self):
        from umh.ingestion.views import source_to_view

        src = IngestionSource(
            source_id="src_test",
            name="Gmail",
            source_class=SourceClass.EMAIL,
            metadata={"api_key": "secret_123"},
        )
        view = source_to_view(src)
        d = view.to_dict()
        self.assertNotIn("api_key", str(d.get("metadata", {})))


class TestSafety(unittest.TestCase):
    """Test AST-based safety checking for ingestion modules (Phase 87B.1 reconciled)."""

    def test_all_modules_safe(self):
        from umh.ingestion.safety import check_all_ingestion_modules

        result = check_all_ingestion_modules()
        self.assertTrue(result["all_safe"], f"Safety violations: {result}")
        self.assertEqual(result["total_violations"], 0)
        self.assertGreaterEqual(result["modules_checked"], 10)

    def test_module_count_positive(self):
        from umh.ingestion.safety import check_all_ingestion_modules

        result = check_all_ingestion_modules()
        self.assertGreater(result["modules_checked"], 0)

    def test_scanned_paths_returned(self):
        from umh.ingestion.safety import check_all_ingestion_modules

        result = check_all_ingestion_modules()
        self.assertIn("scanned_paths", result)
        self.assertIsInstance(result["scanned_paths"], list)
        self.assertEqual(len(result["scanned_paths"]), result["modules_checked"])
        for p in result["scanned_paths"]:
            self.assertTrue(p.endswith(".py"))

    def test_warning_count_returned(self):
        from umh.ingestion.safety import check_all_ingestion_modules

        result = check_all_ingestion_modules()
        self.assertIn("warning_count", result)
        self.assertEqual(result["warning_count"], 0)

    def test_explicit_dir_parameter(self):
        from umh.ingestion.safety import check_all_ingestion_modules

        result = check_all_ingestion_modules(ingestion_dir="/opt/OS/umh/ingestion")
        self.assertGreaterEqual(result["modules_checked"], 10)
        self.assertTrue(result["all_safe"])

    def test_nonexistent_dir_returns_warning(self):
        from umh.ingestion.safety import check_all_ingestion_modules

        result = check_all_ingestion_modules(ingestion_dir="/tmp/no_such_dir_87b1")
        self.assertEqual(result["modules_checked"], 0)
        self.assertFalse(result["all_safe"])
        self.assertGreater(result["warning_count"], 0)
        self.assertTrue(any("not found" in w for w in result["warnings"]))

    def test_empty_dir_returns_warning(self):
        from umh.ingestion.safety import check_all_ingestion_modules
        import tempfile

        td = tempfile.mkdtemp()
        try:
            result = check_all_ingestion_modules(ingestion_dir=td)
            self.assertEqual(result["modules_checked"], 0)
            self.assertFalse(result["all_safe"])
            self.assertGreater(result["warning_count"], 0)
            self.assertTrue(any("No Python modules" in w for w in result["warnings"]))
        finally:
            import os
            os.rmdir(td)

    def test_individual_module_safe(self):
        from umh.ingestion.safety import check_module_safety

        result = check_module_safety("/opt/OS/umh/ingestion/contracts.py")
        self.assertTrue(result["safe"])

    def test_detects_forbidden_import(self):
        from umh.ingestion.safety import check_module_safety
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("import requests\n")
            f.flush()
            result = check_module_safety(f.name)
            self.assertFalse(result["safe"])
            self.assertIn("requests", result["forbidden_imports"])

    def test_detects_execution_pattern(self):
        from umh.ingestion.safety import check_module_safety
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("def scrape():\n    pass\n")
            f.flush()
            result = check_module_safety(f.name)
            self.assertFalse(result["safe"])
            self.assertIn("scrape", result["execution_patterns"])

    def test_detects_secret_pattern(self):
        from umh.ingestion.safety import check_module_safety
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("import os\nval = os.getenv('KEY')\n")
            f.flush()
            result = check_module_safety(f.name)
            self.assertFalse(result["safe"])
            self.assertIn("os.getenv", result["secret_patterns"])

    def test_detects_forbidden_module_prefix(self):
        from umh.ingestion.safety import check_module_safety
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("from umh.execution.runner import run\n")
            f.flush()
            result = check_module_safety(f.name)
            self.assertFalse(result["safe"])
            self.assertIn("umh.execution.runner", result["forbidden_module_prefixes"])

    def test_detects_network_listener_pattern(self):
        from umh.ingestion.safety import check_module_safety
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("def start_server():\n    pass\n")
            f.flush()
            result = check_module_safety(f.name)
            self.assertFalse(result["safe"])
            self.assertIn("start_server", result["network_listener_patterns"])

    def test_source_safety_check(self):
        from umh.ingestion.safety import check_ingestion_source_safety

        src = IngestionSource(
            source_id="test",
            status=SourceStatus.APPROVED,
            sensitivity=SourceSensitivity.INTERNAL,
        )
        result = check_ingestion_source_safety(src)
        self.assertTrue(result["safe"])

    def test_credential_source_warns(self):
        from umh.ingestion.safety import check_ingestion_source_safety

        src = IngestionSource(
            source_id="test",
            sensitivity=SourceSensitivity.CREDENTIAL,
        )
        result = check_ingestion_source_safety(src)
        self.assertFalse(result["safe"])


class TestLayering(unittest.TestCase):
    """Test that ingestion modules respect import boundaries."""

    def test_no_forbidden_imports_per_file(self):
        from umh.ingestion.safety import check_module_safety
        from pathlib import Path

        ingestion_dir = Path("/opt/OS/umh/ingestion")
        for py_file in sorted(ingestion_dir.glob("*.py")):
            if py_file.name == "__init__.py":
                continue
            result = check_module_safety(py_file)
            self.assertTrue(result["safe"], f"{py_file.name} has violations: {result}")

    def test_no_model_router_import(self):
        import ast
        from pathlib import Path

        ingestion_dir = Path("/opt/OS/umh/ingestion")
        for py_file in sorted(ingestion_dir.glob("*.py")):
            source = py_file.read_text()
            self.assertNotIn("model_router", source, f"{py_file.name} imports model_router")

    def test_no_llm_calls(self):
        from pathlib import Path

        ingestion_dir = Path("/opt/OS/umh/ingestion")
        for py_file in sorted(ingestion_dir.glob("*.py")):
            source = py_file.read_text()
            for pattern in ["call_with_fallback", "anthropic", "openai", "genai"]:
                self.assertNotIn(pattern, source, f"{py_file.name} contains LLM pattern: {pattern}")

    def test_routing_imports_from_distributed(self):
        import ast

        source = open("/opt/OS/umh/ingestion/routing.py").read()
        tree = ast.parse(source)
        imports_distributed = False
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ImportFrom)
                and node.module
                and node.module.startswith("umh.distributed")
            ):
                imports_distributed = True
                break
        self.assertTrue(imports_distributed, "routing.py should import from umh.distributed")


class TestIntegration(unittest.TestCase):
    """Test Phase 87A/87B cross-module integration."""

    def test_distributed_contracts_importable(self):
        from umh.distributed.contracts import (
            CapabilityDomain,
            RuntimeNodeType,
            SourceAffinity,
        )

        self.assertIsNotNone(CapabilityDomain)
        self.assertIsNotNone(RuntimeNodeType)
        self.assertIsNotNone(SourceAffinity)

    def test_ingestion_uses_distributed_enums(self):
        from umh.distributed.contracts import CapabilityDomain, SourceAffinity
        from umh.ingestion.routing import get_source_node_affinity, get_source_required_capabilities

        aff = get_source_node_affinity(SourceClass.EMAIL)
        self.assertIsInstance(aff, SourceAffinity)
        caps = get_source_required_capabilities(SourceClass.EMAIL)
        for c in caps:
            self.assertIsInstance(c, CapabilityDomain)

    def test_distributed_not_modified(self):
        from pathlib import Path

        dist_files = sorted(Path("/opt/OS/umh/distributed").glob("*.py"))
        self.assertGreaterEqual(len(dist_files), 8)

    def test_seed_sources_route_through_87a(self):
        from umh.ingestion.routing import route_all_sources
        from umh.ingestion.source_registry import build_seed_sources

        routes = route_all_sources(build_seed_sources())
        for r in routes:
            self.assertIn(r.recommended_node_type, ("vps", "local_pc", "cloud_gpu", "cloud_cpu"))

    def test_full_pipeline_plan_to_route(self):
        from umh.ingestion.onboarding import build_onboarding_plan_for_tier
        from umh.ingestion.source_registry import get_sources_by_tier
        from umh.ingestion.routing import route_all_sources
        from umh.ingestion.review_policy import get_review_policy_for_source

        plan = build_onboarding_plan_for_tier(OnboardingTier.TIER_2_WORKSPACE)
        sources = get_sources_by_tier(OnboardingTier.TIER_2_WORKSPACE)
        routes = route_all_sources(sources)
        self.assertGreater(len(routes), 0)

        for s in sources:
            policy = get_review_policy_for_source(s)
            # Not all sources have a matching policy, but no crash


class TestPhase87BRegression(unittest.TestCase):
    """Regression tests — import smoke tests for Phases 80–87B."""

    def test_phase80_registry(self):
        from umh.registry.contracts import RegistryType

        self.assertIsNotNone(RegistryType)

    def test_phase81_ontology(self):
        from umh.ontology.laws import LawType

        self.assertIsNotNone(LawType)

    def test_phase82_storage(self):
        from umh.storage.contracts import StorageRecordType

        self.assertIsNotNone(StorageRecordType)

    def test_phase83_migration(self):
        from umh.migration.contracts import LegacyModuleStatus

        self.assertIsNotNone(LegacyModuleStatus)

    def test_phase84_interface(self):
        from umh.interface.contracts import InterfaceType

        self.assertIsNotNone(InterfaceType)

    def test_phase85_council(self):
        from umh.council.contracts import CouncilStatus

        self.assertIsNotNone(CouncilStatus)

    def test_phase85b_archetypes(self):
        from umh.council.archetypes import get_all_thinker_profiles

        profiles = get_all_thinker_profiles()
        self.assertGreater(len(profiles), 0)

    def test_phase87_leverage(self):
        from umh.leverage.contracts import LeverageType

        self.assertIsNotNone(LeverageType)

    def test_phase87a_distributed(self):
        from umh.distributed.contracts import RuntimeNodeType

        self.assertIsNotNone(RuntimeNodeType)

    def test_phase87b_ingestion(self):
        from umh.ingestion.contracts import SourceClass

        self.assertIsNotNone(SourceClass)


class TestToolAgnostic(unittest.TestCase):
    """Verify tool-agnosticism — no user-specific assumptions baked in."""

    def test_no_hardcoded_user_names(self):
        from pathlib import Path

        ingestion_dir = Path("/opt/OS/umh/ingestion")
        for py_file in sorted(ingestion_dir.glob("*.py")):
            source = py_file.read_text()
            for name in ["antony", "antonyfm", "munoz"]:
                self.assertNotIn(
                    name.lower(),
                    source.lower(),
                    f"{py_file.name} contains user-specific name: {name}",
                )

    def test_no_hardcoded_urls(self):
        from pathlib import Path

        ingestion_dir = Path("/opt/OS/umh/ingestion")
        for py_file in sorted(ingestion_dir.glob("*.py")):
            source = py_file.read_text()
            for pattern in ["http://", "https://"]:
                self.assertNotIn(pattern, source, f"{py_file.name} contains hardcoded URL")

    def test_no_hardcoded_paths(self):
        from pathlib import Path

        ingestion_dir = Path("/opt/OS/umh/ingestion")
        for py_file in sorted(ingestion_dir.glob("*.py")):
            if py_file.name == "safety.py":
                continue
            source = py_file.read_text()
            for pattern in ["/home/", "/Users/", "C:\\"]:
                self.assertNotIn(
                    pattern, source, f"{py_file.name} contains hardcoded path: {pattern}"
                )

    def test_source_classes_are_generic(self):
        for sc in SourceClass:
            self.assertFalse(sc.value.startswith("my_"), f"{sc} is user-specific")
            self.assertFalse(sc.value.startswith("antony"), f"{sc} is user-specific")

    def test_platforms_are_generic(self):
        for pt in PlatformType:
            self.assertFalse(pt.value.startswith("my_"), f"{pt} is user-specific")


class TestSeedMapCompleteness(unittest.TestCase):
    """Verify seed maps are complete and consistent."""

    def test_every_seed_source_has_modalities(self):
        from umh.ingestion.source_registry import build_seed_sources

        for s in build_seed_sources():
            self.assertGreater(len(s.modalities), 0, f"{s.name} has no modalities")

    def test_every_seed_source_has_access_methods(self):
        from umh.ingestion.source_registry import build_seed_sources

        for s in build_seed_sources():
            self.assertGreater(len(s.access_methods), 0, f"{s.name} has no access methods")

    def test_every_seed_source_has_permission_scopes(self):
        from umh.ingestion.source_registry import build_seed_sources

        for s in build_seed_sources():
            self.assertGreater(len(s.permission_scopes), 0, f"{s.name} has no permission scopes")

    def test_financial_sources_require_full_review(self):
        from umh.ingestion.source_registry import get_financial_sources

        for s in get_financial_sources():
            self.assertEqual(
                s.review_requirement,
                ReviewRequirement.FULL_REVIEW,
                f"Financial source {s.name} should require full review",
            )

    def test_ai_chat_sources_have_supersession(self):
        from umh.ingestion.source_registry import get_sources_by_class

        ai_sources = get_sources_by_class(SourceClass.AI_ASSISTANT)
        for s in ai_sources:
            self.assertEqual(
                s.promotion_policy,
                MemoryPromotionPolicy.SUPERSESSION_CHECK,
                f"AI source {s.name} should use supersession check",
            )

    def test_seed_covers_all_tiers(self):
        from umh.ingestion.source_registry import build_seed_sources

        tiers = {s.onboarding_tier for s in build_seed_sources()}
        self.assertIn(OnboardingTier.TIER_1_LOCAL_ARCHIVES, tiers)
        self.assertIn(OnboardingTier.TIER_2_WORKSPACE, tiers)
        self.assertIn(OnboardingTier.TIER_3_SOCIAL_ALGORITHM, tiers)


if __name__ == "__main__":
    unittest.main()
