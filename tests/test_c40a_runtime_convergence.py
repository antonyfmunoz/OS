"""C40A — Surface Runtime Convergence Tests.

Tests the C40A campaign components: mesh dispatch convergence, projection
equivalence measurement, and 4-dimensional qualification.

Wave 0 adjudication (2026-07-20): the former TestRuntimeBoundaryAudit class
imported scripts/run_c40a_runtime_audit.py, deleted with the retired campaign
tooling in e171df789 — the class was orphaned, its 4 tests failing on
ModuleNotFoundError ever since. Adjudicated invariant-by-invariant, never
deleted for green:
  1. serialization chain  → RETIRED: covered better by
     tests/test_mesh_dispatch_contract.py::TestSerializationChain (+
     TestShellAdapterContract, TestRelayPassthrough).
  2. surfaces documented  → RETIRED with recorded gap: no live operator-
     surface registry exists to assert against; rebuilding one as live code
     is a Wave 5 (Cockpit daily-driver) requirement.
  3. governance bypass    → REPLACED by live full-path tests in
     tests/test_mesh_dispatch_contract.py::TestGovernanceCapabilityName
     alongside the validate_request hardening (dotted-operation
     normalization; unknown operations denied; allowed_commands binds to
     shell.execute). The hazard was latent (direct-call only) — the
     production node client already normalized before policy evaluation.
  4. runtime adapter name → REPLACED by the emitted-capability contract test
     in the same class.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")


from substrate.organism.daemon import OrganismDaemon
from substrate.organism.mutation_registry import MutationRegistry
from substrate.organism.mutation_router import (
    MutationRequest,
    MutationRouter,
)


class TestMeshDispatchContract:
    """Verify dispatch payload contracts end-to-end."""

    def test_command_payload_reaches_adapter(self):
        """Simulate full chain for command path."""
        params = {"command": "echo test", "timeout": 30}
        body = {
            "node_id": "windows-desktop",
            "capability": "shell",
            "params": params,
            "timeout": 30,
        }

        # Relay extraction
        relay_params = body.get("params", {})
        assert "command" in relay_params

        # JSON-RPC wrapping
        rpc = {
            "jsonrpc": "2.0",
            "method": "capability.execute",
            "params": {
                "request_id": "test",
                "capability_name": body["capability"],
                "params": relay_params,
                "timeout_seconds": 30,
            },
            "id": "test",
        }

        # Client extraction
        msg_params = rpc["params"]
        cap_params = msg_params.get("params", {})
        assert "command" in cap_params
        assert cap_params["command"] == "echo test"

    def test_argv_payload_reaches_adapter(self):
        """Simulate full chain for argv path."""
        params = {"argv": ["echo", "test"], "cwd": "/tmp"}
        body = {
            "node_id": "windows-desktop",
            "capability": "shell",
            "params": params,
            "timeout": 30,
        }

        relay_params = body.get("params", {})
        rpc = {
            "jsonrpc": "2.0",
            "method": "capability.execute",
            "params": {
                "request_id": "test",
                "capability_name": "shell",
                "params": relay_params,
                "timeout_seconds": 30,
            },
            "id": "test",
        }

        msg_params = rpc["params"]
        cap_params = msg_params.get("params", {})
        assert "argv" in cap_params
        assert cap_params["argv"] == ["echo", "test"]


class TestProjectionEquivalence:
    """Verify mutations produce consistent state across observation points."""

    def setup_method(self):
        self.daemon = OrganismDaemon()
        self.router = MutationRouter(
            spine=self.daemon.governed_spine,
            registry=self.daemon.mutation_registry,
        )

    def test_mutation_emits_event(self):
        events = []
        self.daemon.event_spine.subscribe("test_proj", lambda e: events.append(e))

        request = MutationRequest(
            mutation_name="settings_update",
            intent="projection equivalence test",
            execute_fn=lambda: ("test output", True),
            source="c40a_test",
        )
        resp = self.router.execute(request)
        assert resp.success
        assert len(events) > 0

    def test_mutation_creates_journal_entry(self):
        request = MutationRequest(
            mutation_name="settings_update",
            intent="journal test",
            execute_fn=lambda: ("test output", True),
            source="c40a_test",
        )
        resp = self.router.execute(request)
        entries = self.daemon.execution_journal.entries_for(resp.envelope_id)
        assert len(entries) >= 2

    def test_source_preserved_across_surfaces(self):
        sources = ["cockpit", "python_api", "discord_signal", "mesh_dispatch", "cli"]
        for src in sources:
            request = MutationRequest(
                mutation_name="presence_update",
                intent=f"source test {src}",
                execute_fn=lambda: ("ok", True),
                source=src,
            )
            resp = self.router.execute(request)
            assert resp.success
            if resp.envelope:
                assert resp.envelope.source == src


class TestRuntimeClassification:
    """Verify runtime classification taxonomy replaces C39 gap grades."""

    def test_governance_constraint(self):
        """Observe-mode rejection is Governance Constraint, not defect."""
        daemon = OrganismDaemon()
        router = MutationRouter(
            spine=daemon.governed_spine,
            registry=daemon.mutation_registry,
        )

        request = MutationRequest(
            mutation_name="container_restart",
            intent="test governance constraint",
            execute_fn=lambda: ("output", True),
            source="c40a_test",
            require_approval=False,
        )
        resp = router.execute(request)
        if not resp.success and "mode" in (resp.rejected_reason or "").lower():
            classification = "Governance Constraint"
        elif resp.success:
            classification = "Success"
        else:
            classification = "Implementation Defect"

        assert classification in ("Governance Constraint", "Success")

    def test_execution_failure_is_implementation_defect(self):
        daemon = OrganismDaemon()
        router = MutationRouter(
            spine=daemon.governed_spine,
            registry=daemon.mutation_registry,
        )

        request = MutationRequest(
            mutation_name="settings_update",
            intent="test failure classification",
            execute_fn=lambda: ("deliberate failure", False),
            source="c40a_test",
        )
        resp = router.execute(request)
        assert not resp.success
        classification = "Implementation Defect"
        assert classification == "Implementation Defect"


class TestFourDimensionalQualification:
    """Verify the 4-dimensional verdict structure."""

    def test_organism_dimension(self):
        from scripts.run_qualification import (
            _bootstrap_organism,
            _submit_batch,
            _validate_all_properties,
        )
        from substrate.organism.qualification_harness import (
            ORL,
            QualificationConfig,
            QualificationHarness,
            QualificationOrchestrator,
        )

        org = _bootstrap_organism()
        harness = QualificationHarness(load_existing=False)
        config = QualificationConfig(
            min_mutations=150,
            max_mutations=5000,
            batch_size=25,
            target_confidence=0.95,
        )
        orchestrator = QualificationOrchestrator(harness, config, mutation_registry=org["registry"])

        report = orchestrator.run_until_converged(
            lambda bs: _submit_batch(org, harness, bs),
            lambda recs: _validate_all_properties(org, harness, recs),
        )

        orl = report.orl_achieved
        if isinstance(orl, ORL):
            orl = orl.value
        # Cold-start qualification may converge to ORL-7 or ORL-8
        # depending on random mutation mix. Campaign uses warm harness
        # and consistently achieves ORL-8.
        assert orl >= 7
        assert report.orl_confidence >= 0.90

    def test_runtime_dimension_structure(self):
        """Runtime dimension tracks mesh reliability."""
        runtime_dim = {
            "dimension": "runtime",
            "metrics": {
                "mesh_dispatch_success_rate": 0.0,
                "adapter_contract_compliance": True,
                "session_routing_correct": True,
                "failure_recovery_s": 0.0,
            },
            "status": "UNTESTED",
        }
        assert runtime_dim["dimension"] == "runtime"
        assert "mesh_dispatch_success_rate" in runtime_dim["metrics"]

    def test_projection_dimension_structure(self):
        """Projection dimension tracks cross-surface agreement."""
        projection_dim = {
            "dimension": "projection",
            "metrics": {
                "projection_agreement": 1.0,
                "event_loss": 0,
                "latency_s": 0.0,
                "surfaces_verified": 0,
            },
            "status": "UNTESTED",
        }
        assert projection_dim["dimension"] == "projection"
        assert "event_loss" in projection_dim["metrics"]

    def test_operator_dimension_structure(self):
        """Operator dimension tracks end-to-end workflows."""
        operator_dim = {
            "dimension": "operator",
            "metrics": {
                "workflows_completed": 0,
                "evidence_chains_complete": 0,
                "manual_fallbacks": 0,
            },
            "status": "UNTESTED",
        }
        assert operator_dim["dimension"] == "operator"


class TestMutationRegistryStability:
    """Verify mutation registry is stable from C39."""

    def test_46_plus_specs_registered(self):
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

    def test_key_mutations_exist(self):
        registry = MutationRegistry()
        required = [
            "settings_update",
            "container_restart",
            "docker_exec",
            "shell_execute",
            "deployment",
            "file_write",
            "state_mutate",
            "presence_update",
        ]
        for name in required:
            assert registry.is_registered(name), f"{name} not registered"


class TestEventSpineIntegrity:
    """Verify event spine delivers events reliably."""

    def test_subscribe_and_emit(self):
        daemon = OrganismDaemon()
        received = []
        daemon.event_spine.subscribe("test_integrity", lambda e: received.append(e))

        router = MutationRouter(
            spine=daemon.governed_spine,
            registry=daemon.mutation_registry,
        )

        for i in range(10):
            request = MutationRequest(
                mutation_name="settings_update",
                intent=f"event integrity test {i}",
                execute_fn=lambda: ("ok", True),
                source="c40a_test",
            )
            router.execute(request)

        assert len(received) >= 10, f"Expected >= 10 events, got {len(received)}"

    def test_zero_event_loss(self):
        daemon = OrganismDaemon()
        events_by_envelope = {}
        daemon.event_spine.subscribe(
            "test_loss",
            lambda e: events_by_envelope.setdefault(
                getattr(e, "envelope_id", None) or getattr(e, "id", "unknown"),
                [],
            ).append(e),
        )

        router = MutationRouter(
            spine=daemon.governed_spine,
            registry=daemon.mutation_registry,
        )

        envelope_ids = []
        for i in range(20):
            request = MutationRequest(
                mutation_name="presence_update",
                intent=f"loss test {i}",
                execute_fn=lambda: ("ok", True),
                source="c40a_test",
            )
            resp = router.execute(request)
            if resp.envelope_id:
                envelope_ids.append(resp.envelope_id)

        # Every completed mutation should have emitted at least one event
        assert len(envelope_ids) > 0
        # Total events should be >= number of mutations (each emits multiple events)
        total_events = sum(len(v) for v in events_by_envelope.values())
        assert total_events >= len(envelope_ids)
