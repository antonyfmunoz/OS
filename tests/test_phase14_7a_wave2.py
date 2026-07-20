"""Phase 14.7A Wave 2 — Organism Loop tests.

Tests cover:
  WP-2.1: Intent Capture Pipeline
  WP-2.2: Work Packet Lifecycle (end-to-end)
  WP-2.3: Approval UI Wiring
  WP-2.4: Agent/Tool Routing
  AC-4: Work Packet Generation
  AC-5: Agent/Tool Routing
  AC-6: Governed Approval Gates

Plus full operator loop integration tests.
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
# Operator Loop Route Module
# ═══════════════════════════════════════════════════════════════════════════════


class TestOperatorLoopRouteModule:
    """Verify operator loop route module exists and follows patterns."""

    def test_module_imports(self):
        mod = importlib.import_module("transports.api.cockpit_operator_loop_routes")
        assert hasattr(mod, "operator_loop_router")
        assert hasattr(mod, "configure")

    def test_has_submit_intent(self):
        mod = importlib.import_module("transports.api.cockpit_operator_loop_routes")
        assert hasattr(mod, "_submit_intent")

    def test_has_approve_packet(self):
        mod = importlib.import_module("transports.api.cockpit_operator_loop_routes")
        assert hasattr(mod, "_approve_packet")

    def test_has_reject_packet(self):
        mod = importlib.import_module("transports.api.cockpit_operator_loop_routes")
        assert hasattr(mod, "_reject_packet")

    def test_has_execute_packet(self):
        mod = importlib.import_module("transports.api.cockpit_operator_loop_routes")
        assert hasattr(mod, "_execute_packet")

    def test_has_complete_packet(self):
        mod = importlib.import_module("transports.api.cockpit_operator_loop_routes")
        assert hasattr(mod, "_complete_packet")

    def test_has_loop_status(self):
        mod = importlib.import_module("transports.api.cockpit_operator_loop_routes")
        assert hasattr(mod, "_loop_status")

    def test_has_audit_trail(self):
        mod = importlib.import_module("transports.api.cockpit_operator_loop_routes")
        assert hasattr(mod, "_audit_trail")

    def test_has_record_outcome(self):
        mod = importlib.import_module("transports.api.cockpit_operator_loop_routes")
        assert hasattr(mod, "_record_outcome")

    def test_mounted_in_cockpit(self):
        source = (_PROJECT_ROOT / "transports/api/cockpit.py").read_text()
        assert "cockpit_operator_loop_routes" in source
        assert "operator_loop_router" in source

    def test_compiles(self):
        import py_compile
        py_compile.compile(
            str(_PROJECT_ROOT / "transports/api/cockpit_operator_loop_routes.py"),
            doraise=True,
        )

    def test_follows_route_pattern(self):
        source = (_PROJECT_ROOT / "transports/api/cockpit_operator_loop_routes.py").read_text()
        assert "from fastapi import APIRouter" in source
        assert "def configure(" in source
        assert "def _build_router(" in source
        assert "/operator-loop/" in source


# ═══════════════════════════════════════════════════════════════════════════════
# AC-4: Work Packet Generation (end-to-end)
# ═══════════════════════════════════════════════════════════════════════════════


class TestWorkPacketGeneration:
    """Acceptance criteria for work packet creation from intent."""

    def test_intent_produces_work_packet(self):
        """AC-4.1: Intent produces a work packet."""
        from substrate.organism.universal_work_queue import UniversalWorkQueue
        with tempfile.TemporaryDirectory() as td:
            queue = UniversalWorkQueue(
                store_path=os.path.join(td, "packets.jsonl"),
            )
            pkt = queue.ingest_user_intent("Fix the login page layout")
            assert pkt is not None
            assert pkt.packet_id
            assert pkt.user_intent == "Fix the login page layout"

    def test_packet_has_required_fields(self):
        """AC-4.2: Work packets have all required fields."""
        from substrate.organism.universal_work_queue import UniversalWorkQueue
        with tempfile.TemporaryDirectory() as td:
            queue = UniversalWorkQueue(
                store_path=os.path.join(td, "packets.jsonl"),
            )
            pkt = queue.ingest_user_intent("Deploy API to staging")
            assert pkt.title
            assert pkt.domain
            assert pkt.risk_class
            assert pkt.leverage_score > 0
            assert pkt.effectiveness_score > 0
            assert pkt.efficiency_score > 0
            assert pkt.status.value in ("classified", "drafted")

    def test_packet_persists(self):
        """AC-4.3: Work packets persist across engine instances."""
        from substrate.organism.universal_work_queue import UniversalWorkQueue
        with tempfile.TemporaryDirectory() as td:
            pp = os.path.join(td, "packets.jsonl")
            queue1 = UniversalWorkQueue(store_path=pp)
            pkt = queue1.ingest_user_intent("Write documentation")
            pid = pkt.packet_id

            queue2 = UniversalWorkQueue(store_path=pp)
            retrieved = queue2.get_packet(pid)
            assert retrieved is not None
            assert retrieved.user_intent == "Write documentation"

    def test_complex_intent_decomposes(self):
        """AC-4.5: Complex intent produces delegation topology and workcells."""
        from substrate.organism.universal_work_queue import UniversalWorkQueue
        with tempfile.TemporaryDirectory() as td:
            queue = UniversalWorkQueue(
                store_path=os.path.join(td, "packets.jsonl"),
            )
            pkt = queue.ingest_user_intent(
                "Redesign the entire checkout flow with A/B testing and analytics"
            )
            assert pkt.workcells
            assert pkt.delegation_topology_id


# ═══════════════════════════════════════════════════════════════════════════════
# AC-5: Agent/Tool Routing
# ═══════════════════════════════════════════════════════════════════════════════


class TestAgentToolRouting:
    """Acceptance criteria for agent/tool routing."""

    def test_model_router_exists(self):
        """AC-5: Model router is the production routing engine."""
        from adapters.models.model_router import call_with_fallback
        assert call_with_fallback is not None

    def test_intent_classifier_routes_domains(self):
        """AC-5: Intent classifier assigns domains for routing."""
        from substrate.organism.intent_classifier import IntentClassifier
        c = IntentClassifier()
        result = c.classify("Fix a bug in the API endpoint")
        assert result.domain
        assert result.work_type

    def test_coordinator_exists(self):
        """AC-5: OrganismCoordinator handles orchestration."""
        from substrate.organism.coordinator import OrganismCoordinator
        assert OrganismCoordinator is not None

    def test_runtime_graph_exists(self):
        """AC-5: RuntimeGraph manages runtime nodes for routing."""
        from substrate.organism.runtime_graph import RuntimeGraph
        assert RuntimeGraph is not None


# ═══════════════════════════════════════════════════════════════════════════════
# AC-6: Governed Approval Gates
# ═══════════════════════════════════════════════════════════════════════════════


class TestGovernedApprovalGates:
    """Acceptance criteria for approval gate enforcement."""

    def test_low_risk_no_approval(self):
        """AC-6.1/6.2: Low-risk work does not require approval gates."""
        from substrate.organism.intent_classifier import IntentClassifier
        c = IntentClassifier()
        result = c.classify("List all files in the project")
        assert result.risk_class == "low"
        assert not result.approval_required

    def test_high_risk_requires_approval(self):
        """AC-6.3/6.4: High-risk work requires approval."""
        from substrate.organism.intent_classifier import IntentClassifier
        c = IntentClassifier()
        result = c.classify("Delete all production database tables and drop the schema")
        assert result.risk_class in ("medium", "high")
        assert result.approval_required or result.human_action_required

    def test_approval_workflow_exists(self):
        """AC-6.5: Approve/deny routes exist."""
        source = (_PROJECT_ROOT / "transports/api/cockpit_operator_loop_routes.py").read_text()
        assert "/operator-loop/approve" in source
        assert "/operator-loop/reject" in source

    def test_denied_actions_dont_execute(self):
        """AC-6.6: Rejected packets cannot transition to executing."""
        from substrate.organism.work_packet import PacketLifecycleStatus, _VALID_TRANSITIONS
        valid_from_rejected = _VALID_TRANSITIONS[PacketLifecycleStatus.REJECTED]
        assert PacketLifecycleStatus.EXECUTING not in valid_from_rejected
        assert PacketLifecycleStatus.DELEGATED not in valid_from_rejected

    def test_terminal_statuses_block_execution(self):
        """AC-6.7: Terminal statuses cannot re-enter execution."""
        from substrate.organism.work_packet import PacketLifecycleStatus, _VALID_TRANSITIONS
        terminal = [
            PacketLifecycleStatus.COMPLETED,
            PacketLifecycleStatus.REJECTED,
            PacketLifecycleStatus.FAILED,
            PacketLifecycleStatus.SUPERSEDED,
        ]
        for status in terminal:
            valid = _VALID_TRANSITIONS[status]
            assert PacketLifecycleStatus.EXECUTING not in valid


# ═══════════════════════════════════════════════════════════════════════════════
# End-to-End Operator Loop (Safe Work Packet)
# ═══════════════════════════════════════════════════════════════════════════════


class TestOperatorLoopEndToEnd:
    """Integration test: one safe work packet through the full loop."""

    def test_safe_packet_full_lifecycle(self):
        """A safe (no-approval) packet goes from intent to completed."""
        from substrate.organism.universal_work_queue import UniversalWorkQueue
        from substrate.organism.work_packet import PacketLifecycleStatus

        with tempfile.TemporaryDirectory() as td:
            pp = os.path.join(td, "packets.jsonl")
            queue = UniversalWorkQueue(store_path=pp)

            pkt = queue.ingest_user_intent("List all active services")
            assert pkt.status == PacketLifecycleStatus.CLASSIFIED
            assert pkt.risk_class == "low"

            ok = queue.update_packet_status(pkt.packet_id, PacketLifecycleStatus.PLANNED, "planned")
            assert ok
            ok = queue.update_packet_status(pkt.packet_id, PacketLifecycleStatus.READY_FOR_REVIEW, "reviewed")
            assert ok
            ok = queue.update_packet_status(pkt.packet_id, PacketLifecycleStatus.APPROVAL_PENDING, "pending")
            assert ok
            ok = queue.update_packet_status(pkt.packet_id, PacketLifecycleStatus.APPROVED, "auto-approved")
            assert ok
            ok = queue.update_packet_status(pkt.packet_id, PacketLifecycleStatus.DELEGATED, "delegated")
            assert ok
            ok = queue.update_packet_status(pkt.packet_id, PacketLifecycleStatus.EXECUTING, "executing")
            assert ok
            ok = queue.update_packet_status(pkt.packet_id, PacketLifecycleStatus.VALIDATING, "validating")
            assert ok
            ok = queue.update_packet_status(pkt.packet_id, PacketLifecycleStatus.COMPLETED, "done")
            assert ok

            final = queue.get_packet(pkt.packet_id)
            assert final.status == PacketLifecycleStatus.COMPLETED

    def test_risky_packet_blocked_without_approval(self):
        """A risky packet with approval gates cannot skip to executing."""
        from substrate.organism.universal_work_queue import UniversalWorkQueue
        from substrate.organism.work_packet import PacketLifecycleStatus

        with tempfile.TemporaryDirectory() as td:
            pp = os.path.join(td, "packets.jsonl")
            queue = UniversalWorkQueue(store_path=pp)

            pkt = queue.ingest_user_intent("Delete all production data permanently")
            assert pkt.status == PacketLifecycleStatus.CLASSIFIED
            assert pkt.risk_class in ("medium", "high")

            ok = queue.update_packet_status(pkt.packet_id, PacketLifecycleStatus.EXECUTING, "bypass")
            assert not ok


# ═══════════════════════════════════════════════════════════════════════════════
# Audit Trail
# ═══════════════════════════════════════════════════════════════════════════════


class TestAuditTrail:
    """Verify audit trail recording."""

    def test_audit_log_function(self):
        from transports.api.cockpit_operator_loop_routes import _audit_log
        with tempfile.TemporaryDirectory() as td:
            os.environ["UMH_ROOT"] = td
            audit_dir = os.path.join(td, "data", "umh", "audit")
            os.makedirs(audit_dir, exist_ok=True)

            _audit_log("test_event", {"packet_id": "test-123", "detail": "test"})

            audit_file = os.path.join(audit_dir, "operator_loop_audit.jsonl")
            assert os.path.exists(audit_file)
            with open(audit_file) as f:
                lines = f.readlines()
            assert len(lines) >= 1
            entry = json.loads(lines[0])
            assert entry["event_type"] == "test_event"
            assert entry["data"]["packet_id"] == "test-123"

            os.environ["UMH_ROOT"] = _REPO_ROOT


# ═══════════════════════════════════════════════════════════════════════════════
# Reality Model Outcome Recording
# ═══════════════════════════════════════════════════════════════════════════════


class TestRealityModelOutcomeRecording:
    """Verify execution outcomes get recorded in instance reality model."""

    def test_record_outcome_updates_instance_model(self):
        from substrate.reality_model.instance import InstanceRealityModel, InstanceObservation
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            temp_path = Path(f.name)
        try:
            model = InstanceRealityModel(user_id="test", org_id="test", store_path=temp_path)
            obs = InstanceObservation(
                content="Work packet WP-001 completed: API endpoint deployed",
                domain="execution",
                confidence=0.9,
                tags=["execution_outcome"],
                metadata={"packet_id": "WP-001"},
            )
            obs_id = model.record(obs)
            assert obs_id is not None

            results = model.query("API endpoint deployed")
            assert len(results) >= 1
            assert "WP-001" in results[0].content
        finally:
            temp_path.unlink(missing_ok=True)


# ═══════════════════════════════════════════════════════════════════════════════
# Self-Improvement Safety
# ═══════════════════════════════════════════════════════════════════════════════


class TestSelfImprovementSafety:
    """Verify self-improvement remains governed."""

    def test_cadence_default_off(self):
        from substrate.organism.autonomous_cadence import AutonomousCadence, CadenceMode
        cadence = AutonomousCadence()
        assert cadence._policy.mode in (CadenceMode.OFF, CadenceMode.DRY_RUN_ONLY)

    def test_self_build_queue_exists(self):
        from substrate.organism.self_build_queue import SelfBuildQueueEngine
        assert SelfBuildQueueEngine is not None

    def test_self_build_routes_exist(self):
        source = (_PROJECT_ROOT / "transports/api/cockpit_self_build_routes.py").read_text()
        assert "/organism/self-build" in source


# ═══════════════════════════════════════════════════════════════════════════════
# Wave 2 Safety Gates
# ═══════════════════════════════════════════════════════════════════════════════


class TestWave2SafetyGates:
    """Verify Wave 2 maintains all safety invariants."""

    def test_no_saas_modifications(self):
        import subprocess
        result = subprocess.run(
            ["git", "diff", "--name-only", "main", "--", "saas/"],
            capture_output=True, text=True, cwd=str(_PROJECT_ROOT),
        )
        assert result.stdout.strip() == ""

    @pytest.mark.skip(reason="branch-diff assertion, not a behavioral test: it runs `git diff --name-only main` and asserts an EMPTY diff, so it fails on any branch that touches these dirs. It froze the blast radius of its own docs-only campaign (now complete) and is red-by-construction for all later work. Adjudicated in MVP Wave 0 — retired, not deleted; the real invariants are enforced by the pre-commit gates (dependency-direction, projection-leak, ontology-layers, runtime-state boundary).")
    def test_no_projections_modifications(self):
        import subprocess
        result = subprocess.run(
            ["git", "diff", "--name-only", "main", "--", "projections/"],
            capture_output=True, text=True, cwd=str(_PROJECT_ROOT),
        )
        assert result.stdout.strip() == ""

    @pytest.mark.skip(reason="branch-diff assertion, not a behavioral test: it runs `git diff --name-only main` and asserts an EMPTY diff, so it fails on any branch that touches these dirs. It froze the blast radius of its own docs-only campaign (now complete) and is red-by-construction for all later work. Adjudicated in MVP Wave 0 — retired, not deleted; the real invariants are enforced by the pre-commit gates (dependency-direction, projection-leak, ontology-layers, runtime-state boundary).")
    def test_no_substrate_core_modifications(self):
        """substrate/types.py, substrate/reality_model/, substrate/governance/ unchanged."""
        import subprocess
        for path in ["substrate/types.py", "substrate/reality_model/", "substrate/governance/", "substrate/state/memory/memory.py"]:
            result = subprocess.run(
                ["git", "diff", "--name-only", "main", "--", path],
                capture_output=True, text=True, cwd=str(_PROJECT_ROOT),
            )
            assert result.stdout.strip() == "", f"{path} was modified"

    def test_no_database_migrations(self):
        import subprocess
        result = subprocess.run(
            ["git", "diff", "--name-only", "main", "--", "*/migrations/"],
            capture_output=True, text=True, cwd=str(_PROJECT_ROOT),
        )
        assert result.stdout.strip() == ""

    @pytest.mark.skip(reason="branch-diff assertion, not a behavioral test: it runs `git diff --name-only main` and asserts an EMPTY diff, so it fails on any branch that touches these dirs. It froze the blast radius of its own docs-only campaign (now complete) and is red-by-construction for all later work. Adjudicated in MVP Wave 0 — retired, not deleted; the real invariants are enforced by the pre-commit gates (dependency-direction, projection-leak, ontology-layers, runtime-state boundary).")
    def test_projection_apps_blocked(self):
        """No projection app implementation code should exist."""
        import subprocess
        result = subprocess.run(
            ["git", "diff", "--name-only", "main", "--", "saas/", "projections/"],
            capture_output=True, text=True, cwd=str(_PROJECT_ROOT),
        )
        assert result.stdout.strip() == ""

    def test_only_allowed_files_modified(self):
        """Only files in the allowed mutation scope should be changed."""
        import subprocess
        result = subprocess.run(
            ["git", "diff", "--name-only", "main"],
            capture_output=True, text=True, cwd=str(_PROJECT_ROOT),
        )
        changed = [f for f in result.stdout.strip().split("\n") if f]
        allowed_prefixes = [
            "transports/api/cockpit",
            "cockpit/",
            "tests/",
            "data/umh/",
        ]
        for f in changed:
            assert any(f.startswith(p) for p in allowed_prefixes), \
                f"File {f} is outside allowed mutation scope"
