"""Tests for adapter_engine/adapter_taxonomy.py — Phase 96.8A.1."""

import sys

sys.path.insert(0, "/opt/OS")

import unittest
from core.adapter_engine.adapter_taxonomy import (
    AdapterCategory,
    ExternalSystemType,
    adapter_category_requires_boundary,
    external_system_requires_adapter,
    adapter_category_requires_tool_mastery,
    adapter_category_requires_governance,
    adapter_category_requires_proof,
    list_all_adapter_categories,
    list_all_external_system_types,
    classify_external_system,
)


class TestEveryAdapterCategoryRequiresBoundary(unittest.TestCase):
    def test_all_categories_require_boundary(self):
        for cat in AdapterCategory:
            self.assertTrue(
                adapter_category_requires_boundary(cat),
                f"{cat.value} must require boundary",
            )


class TestEveryExternalSystemRequiresAdapter(unittest.TestCase):
    def test_all_systems_require_adapter(self):
        for sys_type in ExternalSystemType:
            self.assertTrue(
                external_system_requires_adapter(sys_type),
                f"{sys_type.value} must require adapter",
            )


class TestHumanApprovalRequiresAdapter(unittest.TestCase):
    def test_human_approval_requires_boundary(self):
        self.assertTrue(adapter_category_requires_boundary(AdapterCategory.HUMAN_APPROVAL))

    def test_founder_confirmation_requires_adapter(self):
        self.assertTrue(external_system_requires_adapter(ExternalSystemType.FOUNDER_CONFIRMATION))


class TestEnvironmentRequiresAdapter(unittest.TestCase):
    def test_environment_requires_boundary(self):
        self.assertTrue(adapter_category_requires_boundary(AdapterCategory.ENVIRONMENT))

    def test_local_wsl_requires_adapter(self):
        self.assertTrue(external_system_requires_adapter(ExternalSystemType.LOCAL_WSL))

    def test_local_gui_requires_adapter(self):
        self.assertTrue(external_system_requires_adapter(ExternalSystemType.LOCAL_WINDOWS_GUI))

    def test_tmux_requires_adapter(self):
        self.assertTrue(external_system_requires_adapter(ExternalSystemType.TMUX))


class TestModelRequiresAdapter(unittest.TestCase):
    def test_model_requires_boundary(self):
        self.assertTrue(adapter_category_requires_boundary(AdapterCategory.MODEL))

    def test_anthropic_api_requires_adapter(self):
        self.assertTrue(external_system_requires_adapter(ExternalSystemType.ANTHROPIC_API))

    def test_openai_api_requires_adapter(self):
        self.assertTrue(external_system_requires_adapter(ExternalSystemType.OPENAI_API))


class TestDataSourceRequiresAdapter(unittest.TestCase):
    def test_data_source_requires_boundary(self):
        self.assertTrue(adapter_category_requires_boundary(AdapterCategory.DATA_SOURCE))

    def test_filesystem_requires_adapter(self):
        self.assertTrue(external_system_requires_adapter(ExternalSystemType.FILESYSTEM))

    def test_database_requires_adapter(self):
        self.assertTrue(external_system_requires_adapter(ExternalSystemType.DATABASE))


class TestToolMasteryRequired(unittest.TestCase):
    def test_tool_category_requires_mastery(self):
        self.assertTrue(adapter_category_requires_tool_mastery(AdapterCategory.TOOL))

    def test_saas_category_requires_mastery(self):
        self.assertTrue(adapter_category_requires_tool_mastery(AdapterCategory.SAAS))

    def test_api_category_requires_mastery(self):
        self.assertTrue(adapter_category_requires_tool_mastery(AdapterCategory.API))

    def test_browser_category_requires_mastery(self):
        self.assertTrue(adapter_category_requires_tool_mastery(AdapterCategory.BROWSER))

    def test_environment_does_not_require_tool_mastery(self):
        self.assertFalse(adapter_category_requires_tool_mastery(AdapterCategory.ENVIRONMENT))

    def test_human_approval_does_not_require_tool_mastery(self):
        self.assertFalse(adapter_category_requires_tool_mastery(AdapterCategory.HUMAN_APPROVAL))


class TestGovernanceAndProof(unittest.TestCase):
    def test_all_categories_require_governance(self):
        for cat in AdapterCategory:
            self.assertTrue(
                adapter_category_requires_governance(cat),
                f"{cat.value} must require governance",
            )

    def test_all_categories_require_proof(self):
        for cat in AdapterCategory:
            self.assertTrue(
                adapter_category_requires_proof(cat),
                f"{cat.value} must require proof",
            )


class TestClassifyExternalSystem(unittest.TestCase):
    def test_google_drive_is_saas(self):
        self.assertEqual(
            classify_external_system(ExternalSystemType.GOOGLE_DRIVE),
            AdapterCategory.SAAS,
        )

    def test_local_wsl_is_environment(self):
        self.assertEqual(
            classify_external_system(ExternalSystemType.LOCAL_WSL),
            AdapterCategory.ENVIRONMENT,
        )

    def test_anthropic_api_is_model(self):
        self.assertEqual(
            classify_external_system(ExternalSystemType.ANTHROPIC_API),
            AdapterCategory.MODEL,
        )

    def test_founder_is_human_approval(self):
        self.assertEqual(
            classify_external_system(ExternalSystemType.FOUNDER_CONFIRMATION),
            AdapterCategory.HUMAN_APPROVAL,
        )

    def test_chrome_is_browser(self):
        self.assertEqual(
            classify_external_system(ExternalSystemType.CHROME_BROWSER),
            AdapterCategory.BROWSER,
        )

    def test_database_is_database(self):
        self.assertEqual(
            classify_external_system(ExternalSystemType.DATABASE),
            AdapterCategory.DATABASE,
        )


class TestListFunctions(unittest.TestCase):
    def test_list_all_categories(self):
        cats = list_all_adapter_categories()
        self.assertEqual(len(cats), 15)

    def test_list_all_external_systems(self):
        systems = list_all_external_system_types()
        self.assertEqual(len(systems), 21)


if __name__ == "__main__":
    unittest.main()
