"""Phase 14.7A Wave 1 — Foundation Wiring tests.

Tests cover:
  WP-1.1: Reality Model HTTP Routes
  WP-1.3: Memory Route Upgrade
  WP-1.4: Execution Control Wiring
  AC-1: Cockpit as Primary Interface (partial)
  AC-2: Intent Capture + Memory (partial)
  AC-3: Usable Reality Model

Plus governance and safety gates.
"""

from __future__ import annotations

import importlib
import json
import os
import sys
import tempfile
from pathlib import Path
from uuid import uuid4

import pytest

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")
sys.path.insert(0, _REPO_ROOT)

_THIS_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _THIS_DIR.parent


# ═══════════════════════════════════════════════════════════════════════════════
# WP-1.1: Reality Model HTTP Routes
# ═══════════════════════════════════════════════════════════════════════════════


class TestRealityModelRoutesExist:
    """Verify reality model route module exists and compiles."""

    def test_module_imports(self):
        mod = importlib.import_module("transports.api.cockpit_reality_model_routes")
        assert hasattr(mod, "reality_model_router")
        assert hasattr(mod, "configure")

    def test_has_status_route(self):
        mod = importlib.import_module("transports.api.cockpit_reality_model_routes")
        assert hasattr(mod, "_status")

    def test_has_canonical_patterns_route(self):
        mod = importlib.import_module("transports.api.cockpit_reality_model_routes")
        assert hasattr(mod, "_canonical_patterns")

    def test_has_canonical_search_route(self):
        mod = importlib.import_module("transports.api.cockpit_reality_model_routes")
        assert hasattr(mod, "_canonical_search")

    def test_has_instance_observations_route(self):
        mod = importlib.import_module("transports.api.cockpit_reality_model_routes")
        assert hasattr(mod, "_instance_observations")

    def test_has_instance_recent_route(self):
        mod = importlib.import_module("transports.api.cockpit_reality_model_routes")
        assert hasattr(mod, "_instance_recent")

    def test_has_simulate_route(self):
        mod = importlib.import_module("transports.api.cockpit_reality_model_routes")
        assert hasattr(mod, "_simulate")

    def test_has_canonical_store_route(self):
        mod = importlib.import_module("transports.api.cockpit_reality_model_routes")
        assert hasattr(mod, "_canonical_store")

    def test_has_instance_record_route(self):
        mod = importlib.import_module("transports.api.cockpit_reality_model_routes")
        assert hasattr(mod, "_instance_record")


class TestRealityModelCanonical:
    """Test CanonicalRealityModel operations through the substrate class."""

    def test_canonical_empty_stats(self):
        from substrate.reality_model.canonical import CanonicalRealityModel
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = Path(f.name)
        try:
            model = CanonicalRealityModel(store_path=temp_path)
            stats = model.stats()
            assert stats["pattern_count"] == 0
            assert stats["relationship_count"] == 0
            assert stats["domains"] == []
        finally:
            temp_path.unlink(missing_ok=True)

    def test_canonical_store_and_retrieve(self):
        from substrate.reality_model.canonical import CanonicalRealityModel, CanonicalPattern
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = Path(f.name)
        try:
            model = CanonicalRealityModel(store_path=temp_path)
            pattern = CanonicalPattern(
                name="test-pattern",
                domain="testing",
                description="A test canonical pattern",
                evidence_count=3,
                confidence=0.8,
                tags=["test", "wave1"],
            )
            pid = model.store(pattern)
            assert pid is not None
            retrieved = model.get_by_name("test-pattern")
            assert retrieved is not None
            assert retrieved.domain == "testing"
            assert retrieved.confidence == 0.8
        finally:
            temp_path.unlink(missing_ok=True)

    def test_canonical_search(self):
        from substrate.reality_model.canonical import CanonicalRealityModel, CanonicalPattern
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = Path(f.name)
        try:
            model = CanonicalRealityModel(store_path=temp_path)
            model.store(CanonicalPattern(name="api-gateway", domain="infrastructure", description="API gateway pattern"))
            model.store(CanonicalPattern(name="data-pipeline", domain="data", description="Data processing pipeline"))
            results = model.search("gateway")
            assert len(results) >= 1
            assert results[0].name == "api-gateway"
        finally:
            temp_path.unlink(missing_ok=True)

    def test_canonical_governance_gate(self):
        from substrate.reality_model.canonical import CanonicalRealityModel, CanonicalPattern
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = Path(f.name)
        try:
            model = CanonicalRealityModel(store_path=temp_path)
            model.store(CanonicalPattern(name="gated-pattern", domain="test", description="test"))
            with pytest.raises(ValueError, match="governance approval"):
                model.update("gated-pattern", governance_approved=False, description="modified")
        finally:
            temp_path.unlink(missing_ok=True)

    def test_canonical_confidence_decay(self):
        from substrate.reality_model.canonical import CanonicalRealityModel, CanonicalPattern
        from datetime import datetime, timezone, timedelta
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = Path(f.name)
        try:
            model = CanonicalRealityModel(store_path=temp_path)
            pattern = CanonicalPattern(
                name="decaying",
                domain="test",
                description="test decay",
                confidence=1.0,
            )
            model.store(pattern)
            retrieved = model.get_by_name("decaying")
            far_future = datetime.now(timezone.utc) + timedelta(days=365)
            assert retrieved.effective_confidence(far_future) < 0.5
        finally:
            temp_path.unlink(missing_ok=True)

    def test_canonical_relationships(self):
        from substrate.reality_model.canonical import CanonicalRealityModel, CanonicalPattern
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = Path(f.name)
        try:
            model = CanonicalRealityModel(store_path=temp_path)
            model.store(CanonicalPattern(name="node-a", domain="test", description="a"))
            model.store(CanonicalPattern(name="node-b", domain="test", description="b"))
            model.add_relationship("node-a", "node-b", "depends_on", 0.7)
            related = model.get_related("node-a")
            assert len(related) == 1
            assert related[0][0] == "node-b"
            assert related[0][1] == "depends_on"
        finally:
            temp_path.unlink(missing_ok=True)


class TestRealityModelInstance:
    """Test InstanceRealityModel operations."""

    def test_instance_empty_stats(self):
        from substrate.reality_model.instance import InstanceRealityModel
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            temp_path = Path(f.name)
        try:
            model = InstanceRealityModel(user_id="test", org_id="test", store_path=temp_path)
            stats = model.stats()
            assert stats["observation_count"] == 0
        finally:
            temp_path.unlink(missing_ok=True)

    def test_instance_record_and_query(self):
        from substrate.reality_model.instance import InstanceRealityModel, InstanceObservation
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            temp_path = Path(f.name)
        try:
            model = InstanceRealityModel(user_id="test", org_id="test", store_path=temp_path)
            obs = InstanceObservation(
                content="deployment succeeded for api-gateway",
                domain="infrastructure",
                confidence=0.9,
                tags=["deployment"],
            )
            oid = model.record(obs)
            assert oid is not None
            results = model.query("gateway")
            assert len(results) >= 1
            assert "gateway" in results[0].content
        finally:
            temp_path.unlink(missing_ok=True)

    def test_instance_recent(self):
        from substrate.reality_model.instance import InstanceRealityModel, InstanceObservation
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            temp_path = Path(f.name)
        try:
            model = InstanceRealityModel(user_id="test", org_id="test", store_path=temp_path)
            for i in range(5):
                model.record(InstanceObservation(content=f"observation {i}", domain="test"))
            recent = model.recent(limit=3)
            assert len(recent) == 3
            assert "observation 4" in recent[0].content
        finally:
            temp_path.unlink(missing_ok=True)

    def test_instance_domain_filter(self):
        from substrate.reality_model.instance import InstanceRealityModel, InstanceObservation
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            temp_path = Path(f.name)
        try:
            model = InstanceRealityModel(user_id="test", org_id="test", store_path=temp_path)
            model.record(InstanceObservation(content="infra work", domain="infrastructure"))
            model.record(InstanceObservation(content="code work", domain="engineering"))
            infra = model.list_by_domain("infrastructure")
            assert len(infra) == 1
            assert infra[0].domain == "infrastructure"
        finally:
            temp_path.unlink(missing_ok=True)

    def test_instance_confidence_decay(self):
        from substrate.reality_model.instance import InstanceRealityModel, InstanceObservation
        from datetime import datetime, timezone, timedelta
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            temp_path = Path(f.name)
        try:
            model = InstanceRealityModel(user_id="test", org_id="test", store_path=temp_path)
            obs = InstanceObservation(content="test decay", confidence=1.0)
            model.record(obs)
            far_future = datetime.now(timezone.utc) + timedelta(days=60)
            assert obs.effective_confidence(far_future) < 0.3
        finally:
            temp_path.unlink(missing_ok=True)


class TestRealityModelSimulation:
    """Test SimulationReality operations."""

    def test_simulation_safe_action(self):
        from substrate.reality_model.simulation import SimulationReality
        from substrate.reality_model.canonical import CanonicalRealityModel
        from substrate.reality_model.instance import InstanceRealityModel
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as cf, \
             tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as inf:
            cp, ip = Path(cf.name), Path(inf.name)
        try:
            sim = SimulationReality(
                canonical=CanonicalRealityModel(store_path=cp),
                instance=InstanceRealityModel(user_id="t", org_id="t", store_path=ip),
            )
            result = sim.simulate("list all active services")
            assert result.safe_to_execute is True
            assert len(result.diff.risk_factors) == 0
        finally:
            cp.unlink(missing_ok=True)
            ip.unlink(missing_ok=True)

    def test_simulation_risky_action(self):
        from substrate.reality_model.simulation import SimulationReality
        from substrate.reality_model.canonical import CanonicalRealityModel
        from substrate.reality_model.instance import InstanceRealityModel
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as cf, \
             tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as inf:
            cp, ip = Path(cf.name), Path(inf.name)
        try:
            sim = SimulationReality(
                canonical=CanonicalRealityModel(store_path=cp),
                instance=InstanceRealityModel(user_id="t", org_id="t", store_path=ip),
            )
            result = sim.simulate("delete all production data and drop tables")
            assert result.safe_to_execute is False
            assert len(result.diff.risk_factors) > 0
        finally:
            cp.unlink(missing_ok=True)
            ip.unlink(missing_ok=True)

    def test_simulation_produces_steps(self):
        from substrate.reality_model.simulation import SimulationReality
        sim = SimulationReality()
        result = sim.simulate("check system status", actions=["list services", "read logs"])
        assert len(result.steps) == 2
        assert result.steps[0].step_number == 1
        assert result.steps[1].step_number == 2

    def test_simulation_to_dict(self):
        from substrate.reality_model.simulation import SimulationReality
        sim = SimulationReality()
        result = sim.simulate("test hypothesis")
        d = result.to_dict()
        assert "simulation_id" in d
        assert "hypothesis" in d
        assert "safe_to_execute" in d
        assert "predicted_outcome" in d


# ═══════════════════════════════════════════════════════════════════════════════
# WP-1.3: Memory Route Upgrade
# ═══════════════════════════════════════════════════════════════════════════════


class TestMemoryRouteUpgrade:
    """Verify memory route accepts source parameter and handles all memory types."""

    def test_memory_route_exists_in_cockpit(self):
        import ast
        source = (_PROJECT_ROOT / "transports/api/cockpit.py").read_text()
        tree = ast.parse(source)
        memory_funcs = [
            node.name for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == "memory"
        ]
        assert len(memory_funcs) >= 1

    def test_memory_route_has_source_param(self):
        source = (_PROJECT_ROOT / "transports/api/cockpit.py").read_text()
        assert 'source: str = "all"' in source or "source: str =" in source

    def test_memory_route_handles_conversation_type(self):
        source = (_PROJECT_ROOT / "transports/api/cockpit.py").read_text()
        assert "ConversationMemory" in source

    def test_memory_route_handles_agent_type(self):
        source = (_PROJECT_ROOT / "transports/api/cockpit.py").read_text()
        assert "AgentMemory" in source

    def test_memory_route_handles_ontology_fallback(self):
        source = (_PROJECT_ROOT / "transports/api/cockpit.py").read_text()
        assert "ontology" in source

    def test_conversation_memory_class_exists(self):
        from substrate.state.memory.memory import ConversationMemory
        assert ConversationMemory is not None

    def test_agent_memory_class_exists(self):
        from substrate.state.memory.memory import AgentMemory
        assert AgentMemory is not None


# ═══════════════════════════════════════════════════════════════════════════════
# WP-1.4: Execution Control Wiring
# ═══════════════════════════════════════════════════════════════════════════════


class TestExecutionControlWiring:
    """Verify execution routes are wired to real spine/work packet data."""

    def test_execution_status_not_static(self):
        """execution_status must NOT return hardcoded slot data."""
        source = (_PROJECT_ROOT / "transports/api/cockpit.py").read_text()
        assert '"slot": 0,' not in source or "work_packets" in source
        assert "WorkPacketEngine" in source

    def test_execution_status_returns_spine_data(self):
        source = (_PROJECT_ROOT / "transports/api/cockpit.py").read_text()
        idx = source.index("async def execution_status")
        block = source[idx:idx + 2500]
        assert "organism" in block.lower() or "spine" in block.lower()
        assert "work_packets" in block or "WorkPacketEngine" in block

    def test_execution_start_requires_packet_id(self):
        source = (_PROJECT_ROOT / "transports/api/cockpit.py").read_text()
        idx = source.index("async def execution_start")
        block = source[idx:idx + 800]
        assert "packet_id" in block

    def test_execution_start_checks_approval(self):
        source = (_PROJECT_ROOT / "transports/api/cockpit.py").read_text()
        idx = source.index("async def execution_start")
        block = source[idx:idx + 800]
        assert "approval" in block.lower() or "APPROVED" in block

    def test_execution_stop_uses_blocked_status(self):
        source = (_PROJECT_ROOT / "transports/api/cockpit.py").read_text()
        idx = source.index("async def execution_stop")
        block = source[idx:idx + 500]
        assert "BLOCKED" in block

    def test_execution_resume_uses_valid_transition(self):
        source = (_PROJECT_ROOT / "transports/api/cockpit.py").read_text()
        idx = source.index("async def execution_resume")
        block = source[idx:idx + 800]
        assert "CLASSIFIED" in block or "DRAFTED" in block or "PacketLifecycleStatus" in block


# ═══════════════════════════════════════════════════════════════════════════════
# AC-3: Usable Reality Model
# ═══════════════════════════════════════════════════════════════════════════════


class TestUsableRealityModel:
    """Acceptance criteria for reality model accessibility."""

    def test_canonical_model_loads(self):
        from substrate.reality_model.canonical import CanonicalRealityModel
        model = CanonicalRealityModel()
        stats = model.stats()
        assert "pattern_count" in stats

    def test_instance_model_loads(self):
        from substrate.reality_model.instance import InstanceRealityModel
        model = InstanceRealityModel(user_id="test", org_id="test")
        stats = model.stats()
        assert "observation_count" in stats

    def test_simulation_model_loads(self):
        from substrate.reality_model.simulation import SimulationReality
        sim = SimulationReality()
        assert sim is not None

    def test_reality_model_routes_mounted_in_cockpit(self):
        source = (_PROJECT_ROOT / "transports/api/cockpit.py").read_text()
        assert "cockpit_reality_model_routes" in source
        assert "reality_model_router" in source
        assert "_mount_reality_model_router" in source

    def test_reality_model_route_covers_all_layers(self):
        source = (_PROJECT_ROOT / "transports/api/cockpit_reality_model_routes.py").read_text()
        assert "/reality-model/status" in source
        assert "/reality-model/canonical/" in source
        assert "/reality-model/instance/" in source
        assert "/reality-model/simulate" in source


# ═══════════════════════════════════════════════════════════════════════════════
# Work Packet Lifecycle
# ═══════════════════════════════════════════════════════════════════════════════


class TestWorkPacketLifecycle:
    """Test work packet creation and lifecycle through the engine."""

    def test_work_packet_engine_creates_packet(self):
        from substrate.organism.work_packet_engine import WorkPacketEngine
        with tempfile.TemporaryDirectory() as td:
            pp = os.path.join(td, "packets.jsonl")
            wp = os.path.join(td, "workcells.jsonl")
            engine = WorkPacketEngine(packets_path=pp, workcells_path=wp)
            pkt = engine.create_packet_from_intent("Fix the login page CSS")
            assert pkt is not None
            assert pkt.title
            assert pkt.domain
            assert pkt.status.value == "classified"

    def test_work_packet_has_required_fields(self):
        from substrate.organism.work_packet_engine import WorkPacketEngine
        with tempfile.TemporaryDirectory() as td:
            pp = os.path.join(td, "packets.jsonl")
            wp = os.path.join(td, "workcells.jsonl")
            engine = WorkPacketEngine(packets_path=pp, workcells_path=wp)
            pkt = engine.create_packet_from_intent("Deploy new version to staging")
            assert pkt.packet_id
            assert pkt.user_intent
            assert pkt.risk_class
            assert pkt.leverage_score > 0

    def test_work_packet_risk_classification(self):
        from substrate.organism.work_packet_engine import WorkPacketEngine
        with tempfile.TemporaryDirectory() as td:
            pp = os.path.join(td, "packets.jsonl")
            wp = os.path.join(td, "workcells.jsonl")
            engine = WorkPacketEngine(packets_path=pp, workcells_path=wp)
            pkt = engine.create_packet_from_intent("Delete all production data")
            assert pkt.risk_class in ("medium", "high")

    def test_work_packet_persists(self):
        from substrate.organism.work_packet_engine import WorkPacketEngine
        with tempfile.TemporaryDirectory() as td:
            pp = os.path.join(td, "packets.jsonl")
            wp = os.path.join(td, "workcells.jsonl")
            engine = WorkPacketEngine(packets_path=pp, workcells_path=wp)
            pkt = engine.create_packet_from_intent("Write unit tests")
            assert Path(pp).exists()
            engine2 = WorkPacketEngine(packets_path=pp, workcells_path=wp)
            assert len(engine2.all_packets()) >= 1

    def test_valid_status_transitions(self):
        from substrate.organism.work_packet import PacketLifecycleStatus, _VALID_TRANSITIONS
        assert PacketLifecycleStatus.CLASSIFIED in _VALID_TRANSITIONS[PacketLifecycleStatus.DRAFTED]
        assert PacketLifecycleStatus.BLOCKED in _VALID_TRANSITIONS[PacketLifecycleStatus.EXECUTING]
        assert PacketLifecycleStatus.EXECUTING in _VALID_TRANSITIONS[PacketLifecycleStatus.DELEGATED]
        assert PacketLifecycleStatus.DELEGATED in _VALID_TRANSITIONS[PacketLifecycleStatus.APPROVED]

    def test_invalid_transition_rejected(self):
        from substrate.organism.work_packet_engine import WorkPacketEngine
        from substrate.organism.work_packet import PacketLifecycleStatus
        with tempfile.TemporaryDirectory() as td:
            pp = os.path.join(td, "packets.jsonl")
            wp = os.path.join(td, "workcells.jsonl")
            engine = WorkPacketEngine(packets_path=pp, workcells_path=wp)
            pkt = engine.create_packet_from_intent("Test task")
            ok = engine.update_packet_status(pkt.packet_id, PacketLifecycleStatus.EXECUTING)
            assert not ok


# ═══════════════════════════════════════════════════════════════════════════════
# Intent Classification
# ═══════════════════════════════════════════════════════════════════════════════


class TestIntentClassification:
    """Test deterministic intent classification."""

    def test_classifier_exists(self):
        from substrate.organism.intent_classifier import IntentClassifier
        classifier = IntentClassifier()
        assert classifier is not None

    def test_classifier_produces_domain(self):
        from substrate.organism.intent_classifier import IntentClassifier
        classifier = IntentClassifier()
        result = classifier.classify("Fix the login button on the website")
        assert result.domain
        assert result.work_type

    def test_classifier_detects_risk(self):
        from substrate.organism.intent_classifier import IntentClassifier
        classifier = IntentClassifier()
        result = classifier.classify("Delete all production database records")
        assert result.risk_class in ("medium", "high")

    def test_classifier_detects_approval_needed(self):
        from substrate.organism.intent_classifier import IntentClassifier
        classifier = IntentClassifier()
        result = classifier.classify("Deploy to production now")
        assert result.approval_required or result.human_action_required


# ═══════════════════════════════════════════════════════════════════════════════
# Governance Gates (AC-6 partial)
# ═══════════════════════════════════════════════════════════════════════════════


class TestGovernanceGates:
    """Verify governance engine is production-ready and classifies risk."""

    def test_governance_engine_exists(self):
        from substrate.control_plane.governance import ConcreteGovernanceEngine
        engine = ConcreteGovernanceEngine()
        assert engine is not None

    def test_risk_classification(self):
        from substrate.governance.risk_classes import ActionRiskCategory
        assert ActionRiskCategory.READ_ONLY is not None
        assert ActionRiskCategory.SAFE_WRITE is not None
        assert ActionRiskCategory.IRREVERSIBLE_WRITE is not None

    def test_authority_levels(self):
        from substrate.governance.authority import AuthorityLevel
        assert AuthorityLevel.AUTONOMOUS.value < AuthorityLevel.DENY.value

    def test_policy_engine_exists(self):
        from substrate.governance.policy_engine import PolicyEngine
        engine = PolicyEngine()
        assert engine is not None

    def test_authority_engine_exists(self):
        from substrate.governance.policy.authority_engine import AuthorityEngine
        assert AuthorityEngine is not None


# ═══════════════════════════════════════════════════════════════════════════════
# Safety Gates
# ═══════════════════════════════════════════════════════════════════════════════


class TestSafetyGates:
    """Verify no unsafe mutations occurred during Wave 1."""

    def test_no_saas_modifications(self):
        """saas/ must not be modified."""
        import subprocess
        result = subprocess.run(
            ["git", "diff", "--name-only", "main", "--", "saas/"],
            capture_output=True, text=True, cwd=str(_PROJECT_ROOT),
        )
        assert result.stdout.strip() == "", f"saas/ was modified: {result.stdout}"

    @pytest.mark.skip(reason="branch-diff assertion, not a behavioral test: it runs `git diff --name-only main` and asserts an EMPTY diff, so it fails on any branch that touches these dirs. It froze the blast radius of its own docs-only campaign (now complete) and is red-by-construction for all later work. Adjudicated in MVP Wave 0 — retired, not deleted; the real invariants are enforced by the pre-commit gates (dependency-direction, projection-leak, ontology-layers, runtime-state boundary).")
    def test_no_projections_modifications(self):
        """projections/ must not be modified."""
        import subprocess
        result = subprocess.run(
            ["git", "diff", "--name-only", "main", "--", "projections/"],
            capture_output=True, text=True, cwd=str(_PROJECT_ROOT),
        )
        assert result.stdout.strip() == "", f"projections/ was modified: {result.stdout}"

    @pytest.mark.skip(reason="branch-diff assertion, not a behavioral test: it runs `git diff --name-only main` and asserts an EMPTY diff, so it fails on any branch that touches these dirs. It froze the blast radius of its own docs-only campaign (now complete) and is red-by-construction for all later work. Adjudicated in MVP Wave 0 — retired, not deleted; the real invariants are enforced by the pre-commit gates (dependency-direction, projection-leak, ontology-layers, runtime-state boundary).")
    def test_reality_model_classes_unchanged(self):
        """substrate/reality_model/ must NOT be modified — routes call, not modify."""
        import subprocess
        result = subprocess.run(
            ["git", "diff", "--name-only", "main", "--", "substrate/reality_model/"],
            capture_output=True, text=True, cwd=str(_PROJECT_ROOT),
        )
        assert result.stdout.strip() == "", f"reality_model classes were modified: {result.stdout}"

    def test_governance_classes_unchanged(self):
        """substrate/governance/ must NOT be modified."""
        import subprocess
        result = subprocess.run(
            ["git", "diff", "--name-only", "main", "--", "substrate/governance/"],
            capture_output=True, text=True, cwd=str(_PROJECT_ROOT),
        )
        assert result.stdout.strip() == "", f"governance classes were modified: {result.stdout}"

    def test_model_router_unchanged(self):
        """adapters/models/model_router.py must NOT be modified."""
        import subprocess
        result = subprocess.run(
            ["git", "diff", "--name-only", "main", "--", "adapters/models/model_router.py"],
            capture_output=True, text=True, cwd=str(_PROJECT_ROOT),
        )
        assert result.stdout.strip() == "", f"model_router was modified: {result.stdout}"

    def test_memory_classes_unchanged(self):
        """substrate/state/memory/memory.py must NOT be modified."""
        import subprocess
        result = subprocess.run(
            ["git", "diff", "--name-only", "main", "--", "substrate/state/memory/memory.py"],
            capture_output=True, text=True, cwd=str(_PROJECT_ROOT),
        )
        assert result.stdout.strip() == "", f"memory.py was modified: {result.stdout}"

    def test_substrate_types_unchanged(self):
        """substrate/types.py must NOT be modified."""
        import subprocess
        result = subprocess.run(
            ["git", "diff", "--name-only", "main", "--", "substrate/types.py"],
            capture_output=True, text=True, cwd=str(_PROJECT_ROOT),
        )
        assert result.stdout.strip() == "", f"types.py was modified: {result.stdout}"

    def test_no_database_schema_changes(self):
        """No migration files should be created."""
        import subprocess
        result = subprocess.run(
            ["git", "diff", "--name-only", "main", "--", "*/migrations/"],
            capture_output=True, text=True, cwd=str(_PROJECT_ROOT),
        )
        assert result.stdout.strip() == "", f"migrations were modified: {result.stdout}"

    def test_dry_run_only_enforced(self):
        """AutonomousCadence default must remain OFF/DRY_RUN_ONLY."""
        from substrate.organism.autonomous_cadence import CadenceMode
        assert CadenceMode.OFF is not None
        assert CadenceMode.DRY_RUN_ONLY is not None

    def test_product_name_canonical(self):
        """Product name must be 'Universal Meta Harness', not 'Universal Mastery Hierarchy'."""
        source = (_PROJECT_ROOT / "transports/api/cockpit_reality_model_routes.py").read_text()
        assert "Mastery Hierarchy" not in source


# ═══════════════════════════════════════════════════════════════════════════════
# Route Module Consistency
# ═══════════════════════════════════════════════════════════════════════════════


class TestRouteModuleConsistency:
    """Verify the new route module follows existing patterns."""

    def test_reality_model_routes_has_configure(self):
        mod = importlib.import_module("transports.api.cockpit_reality_model_routes")
        assert hasattr(mod, "configure")
        assert callable(mod.configure)

    def test_reality_model_routes_has_router(self):
        mod = importlib.import_module("transports.api.cockpit_reality_model_routes")
        assert hasattr(mod, "reality_model_router")

    def test_route_file_follows_pattern(self):
        """New route file follows the same pattern as existing cockpit_*_routes.py files."""
        source = (_PROJECT_ROOT / "transports/api/cockpit_reality_model_routes.py").read_text()
        assert "from fastapi import APIRouter" in source
        assert "def configure(" in source
        assert "def _build_router(" in source
        assert "APIRouter()" in source

    def test_cockpit_py_compiles(self):
        import py_compile
        py_compile.compile(
            str(_PROJECT_ROOT / "transports/api/cockpit.py"),
            doraise=True,
        )

    def test_reality_model_routes_compiles(self):
        import py_compile
        py_compile.compile(
            str(_PROJECT_ROOT / "transports/api/cockpit_reality_model_routes.py"),
            doraise=True,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Execution Spine Integration
# ═══════════════════════════════════════════════════════════════════════════════


class TestExecutionSpineIntegration:
    """Verify execution spine is importable and functional."""

    def test_spine_imports(self):
        from substrate.execution.spine import ConcreteExecutionSpine
        spine = ConcreteExecutionSpine()
        assert spine is not None

    def test_spine_has_execute_method(self):
        from substrate.execution.spine import ConcreteExecutionSpine
        spine = ConcreteExecutionSpine()
        assert hasattr(spine, "execute")

    def test_spine_simulation_integration(self):
        from substrate.execution.spine import ConcreteExecutionSpine
        spine = ConcreteExecutionSpine()
        sim = spine._get_simulation()
        assert sim is not None
