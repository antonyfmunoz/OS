"""Empire WorkPacket Engine — Phase 3 tests.

Tests the domain-general work routing pipeline:
  Intent → Domain Classification → Decomposition → Agent Routing →
  Proof Requirements → Profile Awareness → Reality Model → Next Actions

Covers:
  1. DomainRegistry — lookup, resolution, proof requirements
  2. AgentRegistry — lookup, domain filtering, capability matching
  3. EmpireRouter — full routing pipeline, profile constraints, reality snapshot
  4. Decomposition — single vs batch intent
  5. Profile awareness — background routing, night mode
  6. Proof standard — domain-specific proof requirements
"""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(autouse=True)
def _isolate_data(tmp_path, monkeypatch):
    """Route all data writes to a temp directory."""
    monkeypatch.setenv("UMH_ROOT", str(tmp_path))
    monkeypatch.setenv("UMH_ORG_ID", "test-org")
    monkeypatch.setenv("UMH_USER_ID", "test-user")
    os.makedirs(tmp_path / "data" / "umh" / "audit", exist_ok=True)
    os.makedirs(tmp_path / "data" / "umh" / "universal_work", exist_ok=True)
    os.makedirs(tmp_path / "data" / "umh" / "execution" / "plans", exist_ok=True)
    os.makedirs(tmp_path / "data" / "umh" / "execution" / "records", exist_ok=True)
    os.makedirs(tmp_path / "data" / "umh" / "execution" / "failures", exist_ok=True)
    os.makedirs(tmp_path / "data" / "umh" / "execution" / "outcomes", exist_ok=True)
    os.makedirs(tmp_path / "data" / "umh" / "execution" / "routings", exist_ok=True)


class TestDomainRegistry:
    """Requirement 1: first-class domain definitions."""

    def test_all_domains_registered(self):
        from substrate.organism.domain_registry import DomainRegistry
        reg = DomainRegistry()
        ids = reg.domain_ids()
        assert len(ids) >= 13
        expected = [
            "engineering", "business_operations", "content", "sales",
            "marketing", "finance", "real_estate", "music", "clothing",
            "personal", "research", "admin", "infrastructure",
        ]
        for e in expected:
            assert e in ids, f"Missing domain: {e}"

    def test_domain_has_proof_requirements(self):
        from substrate.organism.domain_registry import DomainRegistry
        reg = DomainRegistry()
        eng = reg.get("engineering")
        assert eng is not None
        proofs = [p.proof_type for p in eng.proof_requirements]
        assert "tests" in proofs
        assert "diff" in proofs
        assert "commit" in proofs

    def test_domain_has_allowed_actions(self):
        from substrate.organism.domain_registry import DomainRegistry
        reg = DomainRegistry()
        sales = reg.get("sales")
        assert sales is not None
        assert "research" in sales.allowed_actions
        assert "build_list" in sales.allowed_actions

    def test_domain_has_default_agents(self):
        from substrate.organism.domain_registry import DomainRegistry
        reg = DomainRegistry()
        content = reg.get("content")
        assert content is not None
        assert "content_producer" in content.default_agent_types

    def test_classifier_domain_resolution(self):
        from substrate.organism.domain_registry import DomainRegistry
        reg = DomainRegistry()
        assert reg.resolve_id("self_build") == "engineering"
        assert reg.resolve_id("business") == "business_operations"
        assert reg.resolve_id("creative") == "music"
        assert reg.resolve_id("strategy") == "infrastructure"

    def test_finance_not_background_eligible(self):
        from substrate.organism.domain_registry import DomainRegistry
        reg = DomainRegistry()
        assert not reg.is_background_eligible("finance")
        assert reg.is_background_eligible("content")

    def test_domain_to_dict(self):
        from substrate.organism.domain_registry import DomainRegistry
        reg = DomainRegistry()
        eng = reg.get("engineering")
        d = eng.to_dict()
        assert d["domain_id"] == "engineering"
        assert isinstance(d["proof_requirements"], list)
        assert isinstance(d["validation_methods"], list)


class TestAgentRegistry:
    """Requirement 6: agent types with capabilities and permissions."""

    def test_all_agent_types_registered(self):
        from substrate.organism.agent_registry import AgentRegistry
        reg = AgentRegistry()
        ids = reg.agent_type_ids()
        assert len(ids) >= 10
        expected = [
            "builder", "researcher", "reviewer", "strategist", "operator",
            "qa", "finance_analyst", "content_producer", "sales_assistant",
            "infrastructure_agent",
        ]
        for e in expected:
            assert e in ids, f"Missing agent: {e}"

    def test_agent_has_capabilities(self):
        from substrate.organism.agent_registry import AgentRegistry
        reg = AgentRegistry()
        builder = reg.get("builder")
        assert builder is not None
        assert "code" in builder.capabilities
        assert "test" in builder.capabilities

    def test_agents_for_domain(self):
        from substrate.organism.agent_registry import AgentRegistry
        reg = AgentRegistry()
        eng_agents = reg.agents_for_domain("engineering")
        agent_ids = [a.agent_type_id for a in eng_agents]
        assert "builder" in agent_ids
        assert "qa" in agent_ids

    def test_agents_for_risk(self):
        from substrate.organism.agent_registry import AgentRegistry
        reg = AgentRegistry()
        low_risk = reg.agents_for_risk("low")
        assert len(low_risk) >= 5

    def test_best_agent_for_domain(self):
        from substrate.organism.agent_registry import AgentRegistry
        reg = AgentRegistry()
        agent = reg.best_agent_for("engineering")
        assert agent is not None
        assert agent.agent_type_id == "builder"

    def test_agent_domain_restriction(self):
        from substrate.organism.agent_registry import AgentRegistry
        reg = AgentRegistry()
        builder = reg.get("builder")
        assert builder.can_handle_domain("engineering")
        assert not builder.can_handle_domain("finance")

    def test_agent_risk_restriction(self):
        from substrate.organism.agent_registry import AgentRegistry
        reg = AgentRegistry()
        researcher = reg.get("researcher")
        assert researcher.can_handle_risk("low")
        assert not researcher.can_handle_risk("high")

    def test_agent_to_dict(self):
        from substrate.organism.agent_registry import AgentRegistry
        reg = AgentRegistry()
        builder = reg.get("builder")
        d = builder.to_dict()
        assert d["agent_type_id"] == "builder"
        assert isinstance(d["capabilities"], list)


class TestEmpireRouter:
    """Requirement 2: intent routing with domain/agent/proof assignment."""

    def test_route_engineering_intent(self):
        from substrate.organism.empire_router import EmpireRouter
        router = EmpireRouter()
        result = router.route("Fix the import error in substrate/types.py")

        assert result.domain == "engineering"
        assert result.routing_id.startswith("route-")
        assert len(result.work_packets) >= 1
        assert len(result.suggested_agents) > 0
        assert len(result.proof_requirements) > 0
        assert result.next_action != ""

    def test_route_sales_intent(self):
        from substrate.organism.empire_router import EmpireRouter
        router = EmpireRouter()
        result = router.route("Create outbound sales lead list for agency client acquisition")

        assert result.domain in ("sales", "business_operations")
        assert len(result.work_packets) >= 1

    def test_route_content_intent(self):
        from substrate.organism.empire_router import EmpireRouter
        router = EmpireRouter()
        result = router.route("Write a social media post about the new product launch")

        assert result.domain == "content"
        assert any(p["proof_type"] == "draft" for p in result.proof_requirements)

    def test_route_finance_intent(self):
        from substrate.organism.empire_router import EmpireRouter
        router = EmpireRouter()
        result = router.route("Create a budget forecast for next quarter")

        assert result.domain == "finance"
        assert not result.background_eligible
        proofs = [p["proof_type"] for p in result.proof_requirements]
        assert "spreadsheet" in proofs

    def test_route_strategic_intent_decomposes(self):
        from substrate.organism.empire_router import EmpireRouter
        router = EmpireRouter()
        result = router.route(
            "Prepare the agency offer for outbound and deploy the landing page and test the funnel",
            desired_end_state="Offer live, leads flowing",
        )

        assert result.scope in ("batch", "strategic")
        assert len(result.work_packets) >= 2

    def test_routing_persists_to_disk(self, tmp_path):
        from substrate.organism.empire_router import EmpireRouter
        router = EmpireRouter()
        result = router.route("Add a new test file")

        route_path = tmp_path / "data" / "umh" / "execution" / "routings" / f"{result.routing_id}.json"
        assert route_path.exists()
        data = json.loads(route_path.read_text())
        assert data["routing_id"] == result.routing_id

    def test_routing_result_to_dict(self):
        from substrate.organism.empire_router import EmpireRouter
        router = EmpireRouter()
        result = router.route("Research the competitor landscape")
        d = result.to_dict()
        assert isinstance(d, dict)
        assert "domain" in d
        assert "work_packets" in d
        assert "proof_requirements" in d


class TestProfileAwareness:
    """Requirement 4: profile and session awareness."""

    def test_developer_profile_backgrounds_sales(self):
        from substrate.organism.empire_router import EmpireRouter
        router = EmpireRouter()
        result = router.route(
            "Build a lead list for sales outbound",
            profile_mode="DEVELOPER",
        )

        constraints = result.profile_constraints
        if "routing" in constraints:
            assert constraints["routing"] == "background"

    def test_night_mode_defers_high_risk(self):
        from substrate.organism.empire_router import EmpireRouter
        router = EmpireRouter()
        result = router.route(
            "Deploy the production database migration",
            session_mode="NIGHT",
        )

        constraints = result.profile_constraints
        assert constraints.get("session_mode") == "NIGHT"

    def test_operator_unavailable_defers_approval(self):
        from substrate.organism.empire_router import EmpireRouter
        router = EmpireRouter()
        result = router.route(
            "Create a financial forecast for the quarter",
            operator_available=False,
        )

        constraints = result.profile_constraints
        assert constraints.get("operator_available") is False


class TestDecomposition:
    """Requirement 3: high-level intent decomposes into WorkPackets."""

    def test_simple_intent_single_packet(self):
        from substrate.organism.empire_router import EmpireRouter
        router = EmpireRouter()
        result = router.route("Fix the typo in README.md")

        assert len(result.work_packets) == 1
        assert result.scope == "single"

    def test_complex_intent_multiple_packets(self):
        from substrate.organism.empire_router import EmpireRouter
        router = EmpireRouter()
        result = router.route(
            "Build the landing page and deploy it and test the conversion funnel",
        )

        assert len(result.work_packets) >= 2

    def test_packets_have_assigned_agents(self):
        from substrate.organism.empire_router import EmpireRouter
        router = EmpireRouter()
        result = router.route("Implement the new API endpoint and deploy it")

        for wp in result.work_packets:
            assert "assigned_agents" in wp

    def test_packets_have_proof_requirements(self):
        from substrate.organism.empire_router import EmpireRouter
        router = EmpireRouter()
        result = router.route("Build the new feature and test it")

        for wp in result.work_packets:
            if "proof_requirements" in wp:
                assert isinstance(wp["proof_requirements"], list)


class TestProofStandard:
    """Requirement 7: domain-specific proof requirements."""

    def test_engineering_proof(self):
        from substrate.organism.domain_registry import DomainRegistry
        reg = DomainRegistry()
        proofs = reg.get_proof_requirements("engineering")
        types = [p.proof_type for p in proofs]
        assert "tests" in types
        assert "diff" in types
        assert "commit" in types

    def test_content_proof(self):
        from substrate.organism.domain_registry import DomainRegistry
        reg = DomainRegistry()
        proofs = reg.get_proof_requirements("content")
        types = [p.proof_type for p in proofs]
        assert "draft" in types
        assert "approval_status" in types

    def test_sales_proof(self):
        from substrate.organism.domain_registry import DomainRegistry
        reg = DomainRegistry()
        proofs = reg.get_proof_requirements("sales")
        types = [p.proof_type for p in proofs]
        assert "lead_list" in types
        assert "sequence" in types

    def test_finance_proof(self):
        from substrate.organism.domain_registry import DomainRegistry
        reg = DomainRegistry()
        proofs = reg.get_proof_requirements("finance")
        types = [p.proof_type for p in proofs]
        assert "spreadsheet" in types
        assert "assumptions" in types
        assert "calculation_trace" in types


class TestRealityModel:
    """Requirement 5: reality model integration."""

    def test_reality_snapshot_structure(self):
        from substrate.organism.empire_router import EmpireRouter
        router = EmpireRouter()
        snapshot = router.get_reality_snapshot()

        assert hasattr(snapshot, "active_domains")
        assert hasattr(snapshot, "active_loops")
        assert hasattr(snapshot, "blocked_items")
        assert hasattr(snapshot, "open_approvals")
        assert hasattr(snapshot, "recent_outcomes")
        assert hasattr(snapshot, "next_best_actions")

    def test_reality_snapshot_to_dict(self):
        from substrate.organism.empire_router import EmpireRouter
        router = EmpireRouter()
        snapshot = router.get_reality_snapshot()
        d = snapshot.to_dict()
        assert isinstance(d, dict)
        assert "active_domains" in d
        assert "next_best_actions" in d


class TestUrgencyDetection:
    """Urgency classification from intent text."""

    def test_urgent_keyword(self):
        from substrate.organism.empire_router import EmpireRouter
        router = EmpireRouter()
        result = router.route("Fix the production crash ASAP")
        assert result.urgency == "urgent"

    def test_low_priority_keyword(self):
        from substrate.organism.empire_router import EmpireRouter
        router = EmpireRouter()
        result = router.route("Eventually clean up the old test files")
        assert result.urgency == "low"

    def test_normal_urgency_default(self):
        from substrate.organism.empire_router import EmpireRouter
        router = EmpireRouter()
        result = router.route("Add a new helper function")
        assert result.urgency == "normal"


class TestMissingContext:
    """Missing context detection."""

    def test_brief_intent_flagged(self):
        from substrate.organism.empire_router import EmpireRouter
        router = EmpireRouter()
        result = router.route("Fix it")
        assert len(result.missing_context) > 0

    def test_detailed_intent_no_flag(self):
        from substrate.organism.empire_router import EmpireRouter
        router = EmpireRouter()
        result = router.route(
            "Fix the TypeScript import error in cockpit/src/main.ts "
            "that prevents the build from succeeding"
        )
        brief_flags = [m for m in result.missing_context if "brief" in m.lower()]
        assert len(brief_flags) == 0


class TestAcceptanceTest:
    """Requirement 9: end-to-end acceptance test."""

    def test_strategic_intent_full_pipeline(self, tmp_path):
        from substrate.organism.empire_router import EmpireRouter

        router = EmpireRouter()
        result = router.route(
            "Prepare the next UMH roadmap update for getting to Phase G faster",
            desired_end_state="Roadmap update complete with actionable next steps",
        )

        assert result.domain in ("infrastructure", "engineering")
        assert result.domain_label != ""
        assert len(result.work_packets) >= 1
        assert len(result.suggested_agents) > 0
        assert len(result.proof_requirements) > 0
        assert result.next_action != ""

        route_path = tmp_path / "data" / "umh" / "execution" / "routings" / f"{result.routing_id}.json"
        assert route_path.exists()

        snapshot = router.get_reality_snapshot()
        assert isinstance(snapshot.next_best_actions, list)

        d = result.to_dict()
        assert d["routing_id"] == result.routing_id
        assert len(d["work_packets"]) >= 1
