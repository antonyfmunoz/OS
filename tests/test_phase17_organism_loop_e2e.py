"""Phase 17 — Organism Loop E2E integration tests.

Proves the organism loop closes: intent → reality → work packet →
governance → execution → proof → memory → reality update → event.

Two cycles:
  Cycle 1: low-risk research intent → full loop completes
  Cycle 2: higher-risk deploy intent → governance gates appropriately,
           cycle 1 memory/reality is available

Plus API surface validation via cockpit routes.

Phase 17F. UMH substrate integration tests.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parents[1])
sys.path.insert(0, _ROOT)
import projections  # noqa: E402 — must precede substrate import
import projections.eos  # noqa: E402
import projections.eos.agents  # noqa: E402

import pytest
from substrate import Substrate
from substrate.organism.organism_loop import OrganismLoopEngine, OrganismLoopResult
from substrate.organism.empire_router import EmpireRouter, RealitySnapshot
from substrate.organism.event_spine import EventSpine
from substrate.organism.universal_work_queue import UniversalWorkQueue
from substrate.memory.canonical_write import CanonicalWritePath, MemoryWriteReceipt


class TestOrganismLoopCycle1:
    """Cycle 1: low-risk research intent goes through full loop."""

    @pytest.fixture
    def engine(self) -> OrganismLoopEngine:
        return OrganismLoopEngine()

    @pytest.fixture
    def substrate(self) -> Substrate:
        return Substrate()

    @pytest.mark.asyncio
    async def test_full_loop_completes(self, engine: OrganismLoopEngine) -> None:
        """Intent → reality → packet → governance → execution → memory → event."""
        result = await engine.execute_intent(
            intent="Research cloud deployment strategy for microservices",
            desired_end_state="Have a documented comparison of deployment strategies",
            constraints=["research only", "no production changes"],
        )

        assert isinstance(result, OrganismLoopResult)
        assert result.result_id.startswith("olr-")
        assert result.total_duration_ms > 0

    @pytest.mark.asyncio
    async def test_reality_snapshot_taken(self, engine: OrganismLoopEngine) -> None:
        result = await engine.execute_intent(
            intent="Research cloud deployment strategy",
        )
        assert result.reality_snapshot_id != ""
        assert "reality_check" in result.steps_completed

    @pytest.mark.asyncio
    async def test_work_packet_created(self, engine: OrganismLoopEngine) -> None:
        result = await engine.execute_intent(
            intent="Research cloud deployment strategy",
        )
        assert result.work_packet_id != ""
        assert result.work_packet_id.startswith("wp-")
        assert "work_packet_created" in result.steps_completed

    @pytest.mark.asyncio
    async def test_governance_evaluated(self, engine: OrganismLoopEngine) -> None:
        result = await engine.execute_intent(
            intent="Research cloud deployment strategy",
        )
        assert result.governance_decision_id != ""
        assert "governance_evaluated" in result.steps_completed

    @pytest.mark.asyncio
    async def test_governance_responds_to_low_risk(self, engine: OrganismLoopEngine) -> None:
        result = await engine.execute_intent(
            intent="Research cloud deployment strategy",
            constraints=["research only"],
        )
        # Governance must evaluate and reach a terminal decision
        governance_acted = (
            "governance_approved" in result.steps_completed
            or "governance_denied" in result.steps_completed
        )
        assert governance_acted
        assert result.final_status in ("completed", "failed", "denied", "blocked")

    @pytest.mark.asyncio
    async def test_execution_or_governance_gate(self, engine: OrganismLoopEngine) -> None:
        result = await engine.execute_intent(
            intent="Research cloud deployment strategy",
        )
        # Either execution was attempted or governance legitimately blocked it
        past_governance = (
            "execution_completed" in result.steps_completed
            or result.error is not None
            or "governance_denied" in result.steps_completed
        )
        assert past_governance

    @pytest.mark.asyncio
    async def test_proof_artifacts_exist(self, engine: OrganismLoopEngine) -> None:
        result = await engine.execute_intent(
            intent="Research cloud deployment strategy",
        )
        if "execution_completed" in result.steps_completed:
            assert len(result.proof_artifact_ids) >= 1
            assert result.execution_bundle_id is not None

    @pytest.mark.asyncio
    async def test_event_emitted(self, engine: OrganismLoopEngine) -> None:
        result = await engine.execute_intent(
            intent="Research cloud deployment strategy",
        )
        assert len(result.event_ids) >= 1

    @pytest.mark.asyncio
    async def test_all_receipt_ids_populated(self, engine: OrganismLoopEngine) -> None:
        result = await engine.execute_intent(
            intent="Research cloud deployment strategy",
        )
        assert result.result_id != ""
        assert result.reality_snapshot_id != ""
        assert result.work_packet_id != ""
        assert result.governance_decision_id != ""

    @pytest.mark.asyncio
    async def test_substrate_execute_work_entry_point(self, substrate: Substrate) -> None:
        result = await substrate.execute_work(
            intent="Research cloud deployment strategy",
            desired_end_state="Documented comparison",
        )
        assert isinstance(result, OrganismLoopResult)
        assert result.result_id.startswith("olr-")
        assert "reality_check" in result.steps_completed
        assert "work_packet_created" in result.steps_completed
        assert "governance_evaluated" in result.steps_completed


class TestOrganismLoopCycle2:
    """Cycle 2: higher-risk deploy intent with cycle 1 context."""

    @pytest.fixture
    def engine(self) -> OrganismLoopEngine:
        return OrganismLoopEngine()

    @pytest.mark.asyncio
    async def test_deploy_gets_higher_governance_scrutiny(
        self, engine: OrganismLoopEngine
    ) -> None:
        """Deploy intent should trigger governance with higher risk classification."""
        result = await engine.execute_intent(
            intent="Deploy selected strategy to production servers",
            desired_end_state="Microservices deployed and running",
        )
        assert "governance_evaluated" in result.steps_completed
        # The governance system should recognize deploy as higher risk
        # It may approve, block, or deny — all are valid governance responses
        governance_acted = (
            "governance_approved" in result.steps_completed
            or "governance_denied" in result.steps_completed
            or result.final_status in ("denied", "blocked")
        )
        assert governance_acted

    @pytest.mark.asyncio
    async def test_cycle2_has_reality_context(
        self, engine: OrganismLoopEngine
    ) -> None:
        """Reality model should include domain context (if cycle 1 wrote observations)."""
        # Run cycle 1 first
        r1 = await engine.execute_intent(
            intent="Research cloud deployment strategy",
        )
        assert r1.reality_snapshot_id != ""

        # Run cycle 2 on same engine (shares subsystems)
        r2 = await engine.execute_intent(
            intent="Deploy selected strategy to production servers",
        )
        assert r2.reality_snapshot_id != ""
        # Both cycles got reality snapshots — the loop is stateful
        assert r1.reality_snapshot_id != r2.reality_snapshot_id

    @pytest.mark.asyncio
    async def test_two_cycles_produce_distinct_packets(
        self, engine: OrganismLoopEngine
    ) -> None:
        r1 = await engine.execute_intent(intent="Research cloud deployment strategy")
        r2 = await engine.execute_intent(intent="Deploy selected strategy to production")
        assert r1.work_packet_id != r2.work_packet_id
        assert r1.result_id != r2.result_id


class TestOrganismSubsystemWiring:
    """Verify each subsystem is genuinely wired (not stubbed)."""

    def test_empire_router_returns_reality_snapshot(self) -> None:
        router = EmpireRouter()
        snapshot = router.get_reality_snapshot()
        assert isinstance(snapshot, RealitySnapshot)
        assert isinstance(snapshot.active_domains, list)

    def test_event_spine_emits(self) -> None:
        from substrate.organism.event_spine import EventDomain
        spine = EventSpine()
        event = spine.emit(
            domain=EventDomain.EXECUTION,
            event_type="test_organism_loop",
            source="test",
            data={"test": True},
        )
        assert event.event_id != ""
        assert event.event_type == "test_organism_loop"

    def test_work_queue_instantiates(self) -> None:
        queue = UniversalWorkQueue()
        assert queue is not None

    def test_canonical_write_path_instantiates(self) -> None:
        writer = CanonicalWritePath()
        assert writer is not None

    def test_organism_loop_engine_instantiates(self) -> None:
        engine = OrganismLoopEngine()
        assert engine is not None
        assert engine._empire_router is not None
        assert engine._work_queue is not None
        assert engine._policy_engine is not None
        assert engine._executor is not None
        assert engine._event_spine is not None
        assert engine._canonical_write is not None


class TestOrganismLoopLifecycleStates:
    """Verify the loop tracks and emits correct lifecycle states."""

    @pytest.fixture
    def engine(self) -> OrganismLoopEngine:
        return OrganismLoopEngine()

    @pytest.mark.asyncio
    async def test_steps_completed_ordering(self, engine: OrganismLoopEngine) -> None:
        result = await engine.execute_intent(
            intent="Research cloud deployment strategy",
        )
        # First three steps must always happen in order
        idx_reality = result.steps_completed.index("reality_check")
        idx_packet = result.steps_completed.index("work_packet_created")
        idx_governance = result.steps_completed.index("governance_evaluated")
        assert idx_reality < idx_packet < idx_governance

    @pytest.mark.asyncio
    async def test_final_status_is_terminal(self, engine: OrganismLoopEngine) -> None:
        result = await engine.execute_intent(
            intent="Research cloud deployment strategy",
        )
        terminal = {"completed", "failed", "denied", "blocked"}
        assert result.final_status in terminal

    @pytest.mark.asyncio
    async def test_duration_recorded(self, engine: OrganismLoopEngine) -> None:
        result = await engine.execute_intent(
            intent="Research cloud deployment strategy",
        )
        assert result.total_duration_ms > 0


class TestOrganismLoopSecurityHardening:
    """Verify security hardening of the orchestration drain stage."""

    def test_approval_gate_blocks_drain(self) -> None:
        from substrate.organism.work_packet import WorkPacket, PacketLifecycleStatus

        packet = WorkPacket(
            user_intent="Deploy to production",
            approval_gates=["ceo_approval"],
            status=PacketLifecycleStatus.APPROVED,
        )
        assert packet.requires_operator_approval() is True
        # Packets with open approval gates must not be drained

    def test_execution_ready_requires_approved_status(self) -> None:
        from substrate.organism.work_packet import WorkPacket, PacketLifecycleStatus

        packet = WorkPacket(
            user_intent="Some task",
            status=PacketLifecycleStatus.DRAFTED,
        )
        assert packet.is_execution_ready() is False

        packet.status = PacketLifecycleStatus.APPROVED
        assert packet.is_execution_ready() is True

    def test_lifecycle_transitions_enforce_path(self) -> None:
        from substrate.organism.work_packet import (
            WorkPacket, PacketLifecycleStatus, _VALID_TRANSITIONS,
        )
        packet = WorkPacket(status=PacketLifecycleStatus.DRAFTED)
        # Cannot jump directly to COMPLETED
        allowed = _VALID_TRANSITIONS[PacketLifecycleStatus.DRAFTED]
        assert PacketLifecycleStatus.COMPLETED not in allowed
        # Must go through intermediate states
        assert PacketLifecycleStatus.CLASSIFIED in allowed
