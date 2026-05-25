"""Tests for the 3 final gap closures: companies endpoint, skill allocation, ingestion facade."""

import os
import sys

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("EOS_ORG_ID", "test-org-id")
os.environ.setdefault("EOS_USER_ID", "test-user-id")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest


class TestSkillAllocation:
    """Gap 2: Per-agent skill allocation codified."""

    def test_all_10_departments_present(self):
        from projections.eos.entities import SKILL_ALLOCATION

        expected = {
            "executive",
            "sales",
            "marketing",
            "finance",
            "customer_success",
            "hr",
            "legal",
            "operations",
            "product",
            "engineering",
        }
        assert set(SKILL_ALLOCATION.keys()) == expected

    def test_sales_has_skills(self):
        from projections.eos.entities import get_skills_for_department

        sales_skills = get_skills_for_department("sales")
        assert len(sales_skills) > 10
        assert "Sales/qualify_lead" in sales_skills
        assert "Outreach/dm_opener" in sales_skills

    def test_marketing_has_content_skills(self):
        from projections.eos.entities import get_skills_for_department

        marketing_skills = get_skills_for_department("marketing")
        assert len(marketing_skills) > 0
        assert "Marketing/content_calendar" in marketing_skills

    def test_operations_has_playbooks(self):
        from projections.eos.entities import get_skills_for_department

        ops_skills = get_skills_for_department("operations")
        playbooks = [s for s in ops_skills if "playbook" in s]
        assert len(playbooks) >= 5

    def test_get_department_for_skill(self):
        from projections.eos.entities import get_department_for_skill

        assert get_department_for_skill("Sales/qualify_lead") == "sales"
        assert get_department_for_skill("CustomerSuccess/churn_prevention") == "customer_success"
        assert get_department_for_skill("developer/adversarial_review") == "engineering"
        assert get_department_for_skill("nonexistent/skill") is None

    def test_unknown_department_returns_empty(self):
        from projections.eos.entities import get_skills_for_department

        assert get_skills_for_department("unknown") == []

    def test_no_skill_in_multiple_departments(self):
        from projections.eos.entities import SKILL_ALLOCATION

        all_skills = []
        for skills in SKILL_ALLOCATION.values():
            all_skills.extend(skills)
        assert len(all_skills) == len(set(all_skills)), "Duplicate skill allocation detected"

    def test_skill_allocation_matches_default_departments(self):
        from projections.eos.entities import SKILL_ALLOCATION, default_departments

        depts = default_departments("test-org")
        dept_slugs = {d.slug for d in depts}
        assert set(SKILL_ALLOCATION.keys()) == dept_slugs


class TestIngestionFacade:
    """Gap 3: substrate.execution.ingestion exposes the canonical pipeline."""

    def test_pipeline_import(self):
        from substrate.execution.ingestion import IngestionPipeline

        assert IngestionPipeline is not None

    def test_source_protocol_import(self):
        from substrate.execution.ingestion import Source, RawContent

        assert Source is not None
        assert RawContent is not None

    def test_result_types_import(self):
        from substrate.execution.ingestion import (
            IngestionResult,
            InterpretationResult,
            MemoryWrite,
            QueryProof,
            Signal,
            WorldUpdate,
        )

        for cls in [
            IngestionResult,
            InterpretationResult,
            MemoryWrite,
            QueryProof,
            Signal,
            WorldUpdate,
        ]:
            assert cls is not None

    def test_ontology_types_import(self):
        from substrate.execution.ingestion import (
            DecompositionResult,
            PrimitiveObservation,
            PrimitiveType,
            RelationshipType,
        )

        assert len(PrimitiveType) == 10
        assert len(RelationshipType) == 10

    def test_domain_bridge_import(self):
        from substrate.execution.ingestion import DomainBridge, DomainProjection

        assert DomainBridge is not None
        assert DomainProjection is not None

    def test_pipeline_instantiation(self):
        import tempfile
        from pathlib import Path

        from substrate.execution.ingestion import IngestionPipeline

        with tempfile.TemporaryDirectory() as td:
            pipeline = IngestionPipeline(memory_store_path=Path(td))
            assert pipeline is not None

    def test_all_exports_in_dunder_all(self):
        import substrate.execution.ingestion as mod

        assert hasattr(mod, "__all__")
        assert len(mod.__all__) >= 10
        for name in mod.__all__:
            assert hasattr(mod, name), f"{name} in __all__ but not importable"


class TestCompaniesEndpoint:
    """Gap 1: /entities/companies CRUD endpoints exist in cockpit router."""

    def test_endpoints_exist(self):
        from transports.api.cockpit import entity_companies, entity_company_detail, upsert_company

        assert callable(entity_companies)
        assert callable(entity_company_detail)
        assert callable(upsert_company)

    def test_endpoints_are_async(self):
        import asyncio

        from transports.api.cockpit import entity_companies, entity_company_detail, upsert_company

        assert asyncio.iscoroutinefunction(entity_companies)
        assert asyncio.iscoroutinefunction(entity_company_detail)
        assert asyncio.iscoroutinefunction(upsert_company)

    def test_routes_registered_on_router(self):
        from transports.api.cockpit import router

        routes = [r.path for r in router.routes if hasattr(r, "path")]
        companies_routes = [r for r in routes if "companies" in r]
        assert len(companies_routes) >= 2, f"Expected companies routes, got: {companies_routes}"
