"""Tests for browser control wiring to department agents."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from projections.eos.agents.base import DepartmentAgent, SkillResult
from substrate.types import PermissionTier, required_tier_for_action


class TestBrowserTierMapping:
    def test_browser_research_is_read_tier(self):
        assert required_tier_for_action("browser_research") == PermissionTier.READ

    def test_browser_act_is_execute_tier(self):
        assert required_tier_for_action("browser_act") == PermissionTier.EXECUTE

    def test_browser_execution_is_execute_tier(self):
        assert required_tier_for_action("browser_execution") == PermissionTier.EXECUTE


class TestBrowserSkillRegistration:
    def test_all_agents_have_browser_research(self):
        from projections.eos.agents import AGENT_CLASSES

        for name, cls in AGENT_CLASSES.items():
            agent = cls()
            assert "browser_research" in agent.skills, f"{name} missing browser_research"

    def test_all_agents_have_browser_act(self):
        from projections.eos.agents import AGENT_CLASSES

        for name, cls in AGENT_CLASSES.items():
            agent = cls()
            assert "browser_act" in agent.skills, f"{name} missing browser_act"

    def test_browser_research_tier_is_read(self):
        from projections.eos.agents import AGENT_CLASSES

        for name, cls in AGENT_CLASSES.items():
            agent = cls()
            assert agent.skills["browser_research"]["min_tier"] == "read"

    def test_browser_act_tier_is_execute(self):
        from projections.eos.agents import AGENT_CLASSES

        for name, cls in AGENT_CLASSES.items():
            agent = cls()
            assert agent.skills["browser_act"]["min_tier"] == "execute"

    def test_metadata_shows_browser_capable(self):
        from projections.eos.agents import AGENT_CLASSES

        for name, cls in AGENT_CLASSES.items():
            agent = cls()
            assert agent.metadata()["browser_capable"] is True


class TestBrowserSkillExecution:
    def test_browser_research_requires_url(self):
        agent = DepartmentAgent()
        result = agent.execute_skill("browser_research")
        assert not result.success
        assert "url required" in result.error

    def test_browser_act_requires_url_and_task(self):
        agent = DepartmentAgent()
        result = agent.execute_skill("browser_act")
        assert not result.success
        assert "url and task required" in result.error

    def test_browser_act_requires_task(self):
        agent = DepartmentAgent()
        result = agent.execute_skill("browser_act", url="https://example.com")
        assert not result.success
        assert "url and task required" in result.error


class TestDraftAgentBrowserGate:
    def test_draft_agent_can_research(self):
        """DRAFT tier agents can do browser_research (READ tier)."""
        from projections.eos.agents.product import ProductAgent

        agent = ProductAgent()
        assert agent.PERMISSION_TIER == PermissionTier.DRAFT
        skill = agent._skills["browser_research"]
        assert agent.PERMISSION_TIER.permits(skill.min_tier)

    def test_draft_agent_cannot_browser_act(self):
        """DRAFT tier agents cannot do browser_act (EXECUTE tier)."""
        from projections.eos.agents.product import ProductAgent

        agent = ProductAgent()
        result = agent.execute_skill("browser_act", url="https://example.com", task="fill form")
        assert not result.success
        assert "cannot execute" in result.error
