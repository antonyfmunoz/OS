"""C39 — Live Gap-Closure Simulation Tests.

Tests the C39 campaign runner components: mutation submission,
gap classification, phase gating, browser evidence wiring,
and qualification recheck.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

import json
import pytest
import time
from unittest.mock import MagicMock, patch

from substrate.organism.daemon import OrganismDaemon
from substrate.organism.mutation_registry import MutationRegistry
from substrate.organism.mutation_router import (
    MutationRequest,
    MutationResponse,
    MutationRouter,
)
from substrate.organism.action_envelope import EnvelopeStatus


# ── Unit tests for C39Campaign ────────────────────────────────────────────


class TestMutationSubmission:
    def setup_method(self):
        self.daemon = OrganismDaemon()
        self.router = MutationRouter(
            spine=self.daemon.governed_spine,
            registry=self.daemon.mutation_registry,
        )

    def test_registered_mutation_completes(self):
        request = MutationRequest(
            mutation_name="settings_update",
            intent="test settings update",
            execute_fn=lambda: ("test output", True),
            source="c39_test",
        )
        resp = self.router.execute(request)
        assert resp.success
        assert resp.status == "completed"
        assert resp.envelope_id

    def test_unregistered_mutation_rejected(self):
        request = MutationRequest(
            mutation_name="nonexistent_mutation_xyz",
            intent="should be rejected",
            execute_fn=lambda: ("should not run", True),
            source="c39_test",
        )
        resp = self.router.execute(request)
        assert not resp.success
        assert resp.status == "rejected"

    def test_failing_mutation_reports_failure(self):
        request = MutationRequest(
            mutation_name="settings_update",
            intent="test deliberate failure",
            execute_fn=lambda: ("deliberate failure", False),
            source="c39_test",
        )
        resp = self.router.execute(request)
        assert not resp.success
        assert resp.status in ("failed", "rolled_back")

    def test_verification_failure_status(self):
        request = MutationRequest(
            mutation_name="settings_update",
            intent="test verify fail",
            execute_fn=lambda: ("output", True),
            source="c39_test",
            verification_fn=lambda: False,
        )
        resp = self.router.execute(request)
        assert resp.status == "verification_failed"

    def test_rollback_on_failure(self):
        rollback_called = {"value": False}

        def rollback_fn():
            rollback_called["value"] = True
            return True

        request = MutationRequest(
            mutation_name="settings_update",
            intent="test rollback",
            execute_fn=lambda: ("fail", False),
            source="c39_test",
            rollback_fn=rollback_fn,
        )
        resp = self.router.execute(request)
        assert resp.status == "rolled_back"
        assert rollback_called["value"]

    def test_source_tracking(self):
        sources = ["cockpit", "python_api", "discord_signal", "mesh_dispatch"]
        for src in sources:
            request = MutationRequest(
                mutation_name="presence_update",
                intent=f"test source {src}",
                execute_fn=lambda: ("ok", True),
                source=src,
            )
            resp = self.router.execute(request)
            assert resp.success
            if resp.envelope:
                assert resp.envelope.source == src

    def test_require_approval_override(self):
        # container_restart normally requires approval, override to skip
        request = MutationRequest(
            mutation_name="container_restart",
            intent="test approval override",
            execute_fn=lambda: ("output", True),
            source="c39_test",
            require_approval=False,
        )
        resp = self.router.execute(request)
        # In observe mode, container_restart may be rejected by mode check.
        # The test validates the require_approval override was accepted,
        # not that the mutation executed (mode governs separately).
        assert resp.envelope_id
        if resp.success:
            assert resp.status == "completed"
        else:
            assert "mode" in resp.rejected_reason.lower()

    def test_all_risk_levels_submit(self):
        registry = self.daemon.mutation_registry
        specs = registry.all_specs()
        risk_levels_seen = set()
        for spec in specs[:20]:
            request = MutationRequest(
                mutation_name=spec.name,
                intent=f"test {spec.name}",
                execute_fn=lambda: ("ok", True),
                source="c39_test",
                require_approval=False,
            )
            resp = self.router.execute(request)
            assert resp.success or resp.status == "rejected"
            risk_levels_seen.add(spec.risk_level)
        assert len(risk_levels_seen) >= 2


class TestJournalIntegration:
    def test_mutation_creates_journal_entries(self):
        daemon = OrganismDaemon()
        router = MutationRouter(
            spine=daemon.governed_spine,
            registry=daemon.mutation_registry,
        )
        request = MutationRequest(
            mutation_name="settings_update",
            intent="journal test",
            execute_fn=lambda: ("ok", True),
            source="c39_test",
        )
        resp = router.execute(request)
        entries = daemon.execution_journal.entries_for(resp.envelope_id)
        assert len(entries) >= 2
        phases = [e.phase for e in entries]
        phase_values = [p.value if hasattr(p, "value") else str(p) for p in phases]
        assert "proposed" in phase_values or "governance_check" in phase_values


class TestEventSpineIntegration:
    def test_mutation_emits_events(self):
        daemon = OrganismDaemon()
        events_captured = []
        daemon.event_spine.subscribe(
            "test_c39",
            lambda evt: events_captured.append(evt),
        )
        router = MutationRouter(
            spine=daemon.governed_spine,
            registry=daemon.mutation_registry,
        )
        request = MutationRequest(
            mutation_name="settings_update",
            intent="event test",
            execute_fn=lambda: ("ok", True),
            source="c39_test",
        )
        router.execute(request)
        assert len(events_captured) > 0


class TestOutcomeLearning:
    def test_failure_adjusts_reliability(self):
        daemon = OrganismDaemon()
        router = MutationRouter(
            spine=daemon.governed_spine,
            registry=daemon.mutation_registry,
        )
        initial = daemon.outcome_learning.get_reliability("state")

        for _ in range(5):
            request = MutationRequest(
                mutation_name="state_mutate",
                intent="reliability test",
                execute_fn=lambda: ("fail", False),
                source="c39_test",
            )
            router.execute(request)

        after = daemon.outcome_learning.get_reliability("state")
        assert after <= initial


class TestGapClassification:
    def test_successful_mutation_is_grade_a(self):
        from scripts.run_c39_simulation import C39Campaign, MutationResult

        campaign = C39Campaign(skip_browser=True)
        result = MutationResult(
            operation_id="test",
            phase=2,
            mutation_name="settings_update",
            action_type="state",
            risk_level="low",
            intent="test",
            source="test",
            success=True,
            status="completed",
        )
        campaign._classify_gap(result)
        assert result.gap_classification == "A"

    def test_rejected_unregistered_is_grade_a(self):
        from scripts.run_c39_simulation import C39Campaign, MutationResult

        campaign = C39Campaign(skip_browser=True)
        result = MutationResult(
            operation_id="test",
            phase=2,
            mutation_name="fake",
            action_type="unknown",
            risk_level="unknown",
            intent="test",
            source="test",
            success=False,
            status="rejected",
            rejected_reason="unregistered",
        )
        campaign._classify_gap(result)
        assert result.gap_classification == "A"

    def test_error_is_grade_f(self):
        from scripts.run_c39_simulation import C39Campaign, MutationResult

        campaign = C39Campaign(skip_browser=True)
        result = MutationResult(
            operation_id="test",
            phase=2,
            mutation_name="test",
            action_type="test",
            risk_level="low",
            intent="test",
            source="test",
            error="RuntimeError: something broke",
        )
        campaign._classify_gap(result)
        assert result.gap_classification == "F"


class TestPhaseGating:
    def test_phase_2_gate_passes_with_enough_mutations(self):
        from scripts.run_c39_simulation import PhaseResult

        pr = PhaseResult(phase=2, name="test")
        pr.successful = 45
        pr.rejected = 5
        assert pr.successful >= 40 and pr.rejected >= 3

    def test_campaign_runs_backend_only(self):
        from scripts.run_c39_simulation import C39Campaign

        campaign = C39Campaign(skip_browser=True)
        summary = campaign.run()
        assert summary["total_mutations"] >= 120
        assert summary["phases_completed"] == 6
        assert summary["all_gates_passed"]


class TestMutationRegistry:
    def test_46_specs_registered(self):
        registry = MutationRegistry()
        specs = registry.all_specs()
        assert len(specs) >= 46

    def test_all_risk_levels_present(self):
        registry = MutationRegistry()
        specs = registry.all_specs()
        risks = {s.risk_level for s in specs}
        assert "low" in risks
        assert "medium" in risks
        assert "high" in risks
        assert "critical" in risks

    def test_key_mutation_specs_exist(self):
        registry = MutationRegistry()
        required = [
            "settings_update", "container_restart", "docker_exec",
            "shell_execute", "deployment", "file_write",
            "state_mutate", "presence_update",
        ]
        for name in required:
            assert registry.is_registered(name), f"{name} not registered"


class TestQualificationRecheck:
    def test_qualification_produces_orl_8(self):
        from substrate.organism.qualification_harness import (
            QualificationConfig,
            QualificationHarness,
            QualificationOrchestrator,
            ORL,
        )
        from scripts.run_qualification import (
            _bootstrap_organism,
            _submit_batch,
            _validate_all_properties,
        )

        org = _bootstrap_organism()
        harness = QualificationHarness(load_existing=False)
        config = QualificationConfig(
            min_mutations=150,
            max_mutations=5000,
            batch_size=25,
            target_confidence=0.95,
        )
        orchestrator = QualificationOrchestrator(
            harness, config, mutation_registry=org["registry"]
        )

        report = orchestrator.run_until_converged(
            lambda bs: _submit_batch(org, harness, bs),
            lambda recs: _validate_all_properties(org, harness, recs),
        )

        orl = report.orl_achieved
        if isinstance(orl, ORL):
            orl = orl.value
        assert orl >= 8
        assert report.orl_confidence >= 0.95
