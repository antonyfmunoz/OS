"""Tests for runtime.platforms.eos.roles."""

import sys

sys.path.insert(0, "/opt/OS")

import pytest
from runtime.platforms.eos.roles import (
    EOSRole,
    get_all_roles,
    get_role_meta,
    is_founder_facing,
    ROLE_TO_SUBSTRATE_SLUG,
    substrate_slug,
)


class TestEOSRole:
    def test_enum_values(self):
        assert EOSRole.EA.value == "ea"
        assert EOSRole.CEO.value == "ceo"
        assert EOSRole.PORTFOLIO_ADVISOR.value == "portfolio_advisor"
        assert EOSRole.GENERAL.value == "general"

    def test_enum_count(self):
        assert len(EOSRole) == 4


class TestRoleMetadata:
    def test_ea_meta(self):
        meta = get_role_meta(EOSRole.EA)
        assert meta["title"] == "Executive Assistant"
        assert "communication" in meta["domains"]
        assert meta["founder_facing"] is True

    def test_ceo_meta(self):
        meta = get_role_meta(EOSRole.CEO)
        assert meta["title"] == "Chief Executive Officer"
        assert "strategy" in meta["domains"]
        assert meta["founder_facing"] is False

    def test_portfolio_meta(self):
        meta = get_role_meta(EOSRole.PORTFOLIO_ADVISOR)
        assert meta["title"] == "Portfolio Advisor"
        assert "investments" in meta["domains"]
        assert meta["founder_facing"] is False

    def test_general_meta(self):
        meta = get_role_meta(EOSRole.GENERAL)
        assert meta["founder_facing"] is False

    def test_get_all_roles(self):
        all_roles = get_all_roles()
        assert len(all_roles) == 4
        role_values = {r["role"] for r in all_roles}
        assert role_values == {"ea", "ceo", "portfolio_advisor", "general"}


class TestFounderFacing:
    def test_only_ea_is_founder_facing(self):
        assert is_founder_facing(EOSRole.EA) is True
        assert is_founder_facing(EOSRole.CEO) is False
        assert is_founder_facing(EOSRole.PORTFOLIO_ADVISOR) is False
        assert is_founder_facing(EOSRole.GENERAL) is False


class TestSubstrateBridge:
    def test_slug_mapping(self):
        assert substrate_slug(EOSRole.EA) == "ea_orchestrator"
        assert substrate_slug(EOSRole.CEO) == "ceo"
        assert substrate_slug(EOSRole.PORTFOLIO_ADVISOR) == "portfolio_advisor"
        assert substrate_slug(EOSRole.GENERAL) == "ea_orchestrator"

    def test_all_roles_mapped(self):
        for role in EOSRole:
            assert role in ROLE_TO_SUBSTRATE_SLUG
