"""C34 Phase 1-2 tests: MutationRegistry extensions, MutationRouter, MutationCatalog."""

from __future__ import annotations

import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from substrate.organism.action_envelope import (
    ActionType,
    BlastRadius,
    EnvelopeStatus,
    ReversibilityClass,
)
from substrate.organism.mutation_registry import MutationRegistry, MutationSpec
from substrate.organism.mutation_router import (
    MutationRequest,
    MutationResponse,
    MutationRouter,
)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_spine(registry: MutationRegistry):
    """Build a minimal GovernedExecutionSpine for testing."""
    from substrate.organism.event_spine import EventSpine
    from substrate.organism.execution_journal import ExecutionJournal
    from substrate.organism.execution_modes import ExecutionMode, ExecutionModeManager
    from substrate.organism.governed_spine import GovernedExecutionSpine

    mode_mgr = ExecutionModeManager()
    mode_mgr._current_mode = ExecutionMode.ASSISTED
    return GovernedExecutionSpine(
        event_spine=EventSpine(),
        execution_mode=mode_mgr,
        mutation_registry=registry,
        journal=ExecutionJournal(),
    )


# ── Phase 1: MutationRegistry extensions ────────────────────────────────────


class TestRegistryExtensions:
    def test_api_layer_specs_registered(self):
        reg = MutationRegistry()
        api_specs = [
            "settings_update",
            "config_set",
            "approval_decide",
            "governance_update",
            "channel_message_send",
            "conversation_send",
            "memory_promote",
            "work_packet_create",
            "work_packet_update",
            "projection_event",
            "adapter_update",
            "sandbox_create",
            "state_mutate",
        ]
        for name in api_specs:
            spec = reg.lookup(name)
            assert spec is not None, f"missing API spec: {name}"
            assert spec.name == name

    def test_total_spec_count(self):
        reg = MutationRegistry()
        assert len(reg.all_specs()) >= 35  # 22 built-in + 13 API-layer + additional domain specs

    def test_governance_update_requires_approval(self):
        reg = MutationRegistry()
        spec = reg.lookup("governance_update")
        assert spec is not None
        assert spec.require_approval is True
        assert spec.risk_level == "high"

    def test_settings_update_low_risk(self):
        reg = MutationRegistry()
        spec = reg.lookup("settings_update")
        assert spec is not None
        assert spec.risk_level == "low"
        assert spec.require_approval is False

    def test_channel_message_send_external(self):
        reg = MutationRegistry()
        spec = reg.lookup("channel_message_send")
        assert spec is not None
        assert spec.blast_radius == BlastRadius.EXTERNAL
        assert spec.reversibility == ReversibilityClass.IRREVERSIBLE


# ── Phase 2: MutationRouter ─────────────────────────────────────────────────


class TestMutationRouter:
    def test_successful_mutation(self):
        reg = MutationRegistry()
        spine = _make_spine(reg)
        router = MutationRouter(spine=spine, registry=reg)

        response = router.execute(MutationRequest(
            mutation_name="state_mutate",
            intent="test mutation",
            execute_fn=lambda: ("done", True),
        ))
        assert response.success is True
        assert response.status in ("completed", "verified")
        assert response.envelope_id != ""

    def test_unregistered_mutation_rejected(self):
        reg = MutationRegistry()
        spine = _make_spine(reg)
        router = MutationRouter(spine=spine, registry=reg)

        response = router.execute(MutationRequest(
            mutation_name="nonexistent_mutation",
            intent="should fail",
            execute_fn=lambda: ("nope", True),
        ))
        assert response.success is False
        assert "unregistered" in response.output

    def test_failed_execution(self):
        reg = MutationRegistry()
        spine = _make_spine(reg)
        router = MutationRouter(spine=spine, registry=reg)

        response = router.execute(MutationRequest(
            mutation_name="state_mutate",
            intent="will fail",
            execute_fn=lambda: ("error occurred", False),
        ))
        assert response.success is False
        assert response.status == "failed"

    def test_execute_fn_exception(self):
        reg = MutationRegistry()
        spine = _make_spine(reg)
        router = MutationRouter(spine=spine, registry=reg)

        def _boom():
            raise ValueError("kaboom")

        response = router.execute(MutationRequest(
            mutation_name="state_mutate",
            intent="will explode",
            execute_fn=_boom,
        ))
        assert response.success is False

    def test_metadata_includes_mutation_name(self):
        reg = MutationRegistry()
        spine = _make_spine(reg)
        router = MutationRouter(spine=spine, registry=reg)

        response = router.execute(MutationRequest(
            mutation_name="settings_update",
            intent="toggle dark mode",
            execute_fn=lambda: ("toggled", True),
            metadata={"key": "dark_mode"},
        ))
        assert response.success is True
        assert response.envelope is not None
        assert response.envelope.metadata["mutation_name"] == "settings_update"
        assert response.envelope.metadata["key"] == "dark_mode"

    def test_risk_override(self):
        reg = MutationRegistry()
        spine = _make_spine(reg)
        router = MutationRouter(spine=spine, registry=reg)

        response = router.execute(MutationRequest(
            mutation_name="state_mutate",
            intent="elevated risk test",
            execute_fn=lambda: ("ok", True),
            risk_level="high",
        ))
        assert response.success is True
        assert response.envelope is not None
        assert response.envelope.risk_level == "high"

    def test_verification_fn_wired(self):
        reg = MutationRegistry()
        spine = _make_spine(reg)
        router = MutationRouter(spine=spine, registry=reg)

        verified = []

        def _verify():
            verified.append(True)
            return True

        response = router.execute(MutationRequest(
            mutation_name="state_mutate",
            intent="verify test",
            execute_fn=lambda: ("ok", True),
            verification_fn=_verify,
        ))
        assert response.success is True
        assert len(verified) == 1

    def test_to_http_dict(self):
        resp = MutationResponse(
            success=True,
            output="done",
            envelope_id="abc123",
            status="completed",
        )
        d = resp.to_http_dict()
        assert d["success"] is True
        assert d["envelope_id"] == "abc123"
        assert d["status"] == "completed"
        assert "awaiting_approval" not in d

    def test_to_http_dict_awaiting(self):
        resp = MutationResponse(
            success=True,
            envelope_id="abc123",
            status="proposed",
            awaiting_approval=True,
        )
        d = resp.to_http_dict()
        assert d["awaiting_approval"] is True

    def test_source_propagated(self):
        reg = MutationRegistry()
        spine = _make_spine(reg)
        router = MutationRouter(spine=spine, registry=reg)

        response = router.execute(MutationRequest(
            mutation_name="state_mutate",
            intent="from discord",
            execute_fn=lambda: ("ok", True),
            source="discord",
        ))
        assert response.envelope is not None
        assert response.envelope.source == "discord"


# ── Phase 2: MutationCatalog ────────────────────────────────────────────────


class TestMutationCatalog:
    def test_load_from_file(self):
        from substrate.organism.mutation_catalog import MutationCatalog

        catalog_data = {
            "endpoints": [
                {
                    "file": "transports/api/test.py",
                    "method": "POST",
                    "path": "/test",
                    "mutation_name": "state_mutate",
                    "risk": "low",
                    "blast_radius": "LOCAL_RUNTIME",
                    "reversibility": "FULLY_REVERSIBLE",
                    "require_approval": False,
                    "current_path": "direct_write",
                    "governed": False,
                    "owner": "cockpit_api",
                },
                {
                    "file": "transports/api/spine.py",
                    "method": "POST",
                    "path": "/approve",
                    "mutation_name": "approval_decide",
                    "risk": "medium",
                    "blast_radius": "LOCAL_RUNTIME",
                    "reversibility": "IRREVERSIBLE",
                    "require_approval": False,
                    "current_path": "governed",
                    "governed": True,
                    "owner": "cockpit_api",
                },
            ]
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(catalog_data, f)
            f.flush()
            catalog = MutationCatalog(catalog_path=f.name)

        try:
            assert len(catalog.all_entries()) == 2
            assert len(catalog.governed_entries()) == 1
            assert len(catalog.ungoverned_entries()) == 1
            assert catalog.coverage_pct() == 50.0

            entry = catalog.lookup("POST", "/test")
            assert entry is not None
            assert entry.mutation_name == "state_mutate"

            summary = catalog.summary()
            assert summary["total"] == 2
            assert summary["governed"] == 1
        finally:
            os.unlink(f.name)

    def test_missing_catalog_file(self):
        from substrate.organism.mutation_catalog import MutationCatalog

        catalog = MutationCatalog(catalog_path="/nonexistent/path.json")
        assert len(catalog.all_entries()) == 0
        assert catalog.coverage_pct() == 0.0


# ── Census verification ─────────────────────────────────────────────────────


class TestCensusIntegrity:
    def test_census_file_exists(self):
        repo = os.environ.get("UMH_ROOT", "/opt/OS")
        # Check both possible locations
        paths = [
            os.path.join(repo, "data", "umh", "c34", "mutation_registry.json"),
            os.path.join(
                repo, ".claude", "worktrees", "c33-campaign",
                "data", "umh", "c34", "mutation_registry.json",
            ),
        ]
        found = any(os.path.isfile(p) for p in paths)
        if not found:
            pytest.skip("census not yet generated")

    def test_census_has_summary(self):
        repo = os.environ.get("UMH_ROOT", "/opt/OS")
        paths = [
            os.path.join(repo, "data", "umh", "c34", "mutation_registry.json"),
            os.path.join(
                repo, ".claude", "worktrees", "c33-campaign",
                "data", "umh", "c34", "mutation_registry.json",
            ),
        ]
        for p in paths:
            if os.path.isfile(p):
                with open(p) as f:
                    data = json.load(f)
                assert "summary" in data
                assert "endpoints" in data
                assert data["summary"]["total_mutation_endpoints"] > 0
                return
        pytest.skip("census not yet generated")


# ── Phase 3: Compounding Pipeline Wiring ───────────────────────────────────


class TestCompoundingWiring:
    """Verify the 3 compounding signals are wired end-to-end in the spine."""

    def _make_spine_with_compounding(self):
        """Build a spine with compounding engine and template extractor."""
        from substrate.organism.event_spine import EventSpine
        from substrate.organism.execution_journal import ExecutionJournal
        from substrate.organism.execution_modes import ExecutionMode, ExecutionModeManager
        from substrate.organism.governed_spine import GovernedExecutionSpine
        from substrate.organism.outcome_learning import OutcomeLearningLoop

        reg = MutationRegistry()
        mode_mgr = ExecutionModeManager()
        mode_mgr._current_mode = ExecutionMode.ASSISTED

        class FakeCompoundingEngine:
            def __init__(self):
                self.scan_calls = []

            def scan_after_cycle(self, outcomes, capabilities_data=None, operationalizations=None):
                self.scan_calls.append(outcomes)
                return []

        class FakeTemplateExtractor:
            def __init__(self):
                self.extract_calls = []
                self.match_calls = []

            def extract_from_cycle(self, cycle_id, files_changed, task_description):
                self.extract_calls.append({
                    "cycle_id": cycle_id,
                    "files_changed": files_changed,
                    "task_description": task_description,
                })
                return None

            def match_template(self, files_changed, task_description=""):
                self.match_calls.append({
                    "files_changed": files_changed,
                    "task_description": task_description,
                })
                return None

        comp = FakeCompoundingEngine()
        tmpl = FakeTemplateExtractor()
        spine = GovernedExecutionSpine(
            event_spine=EventSpine(),
            execution_mode=mode_mgr,
            mutation_registry=reg,
            journal=ExecutionJournal(),
            learning_loop=OutcomeLearningLoop(),
            compounding_engine=comp,
            template_extractor=tmpl,
        )
        return spine, reg, comp, tmpl

    def test_scan_after_cycle_called_on_success(self):
        spine, reg, comp, tmpl = self._make_spine_with_compounding()
        router = MutationRouter(spine=spine, registry=reg)

        response = router.execute(MutationRequest(
            mutation_name="state_mutate",
            intent="test compounding",
            execute_fn=lambda: ("done", True),
        ))
        assert response.success is True
        assert len(comp.scan_calls) == 1
        assert comp.scan_calls[0][0]["action_type"] == "state"

    def test_scan_not_called_on_failure(self):
        spine, reg, comp, tmpl = self._make_spine_with_compounding()
        router = MutationRouter(spine=spine, registry=reg)

        response = router.execute(MutationRequest(
            mutation_name="state_mutate",
            intent="will fail",
            execute_fn=lambda: ("error", False),
        ))
        assert response.success is False
        assert len(comp.scan_calls) == 0

    def test_extract_from_cycle_called_on_success(self):
        spine, reg, comp, tmpl = self._make_spine_with_compounding()
        router = MutationRouter(spine=spine, registry=reg)

        response = router.execute(MutationRequest(
            mutation_name="state_mutate",
            intent="test extraction",
            execute_fn=lambda: ("done", True),
            metadata={"files_changed": ["substrate/foo.py"]},
        ))
        assert response.success is True
        assert len(tmpl.extract_calls) == 1
        assert tmpl.extract_calls[0]["files_changed"] == ["substrate/foo.py"]

    def test_match_template_called_pre_execution(self):
        spine, reg, comp, tmpl = self._make_spine_with_compounding()
        router = MutationRouter(spine=spine, registry=reg)

        response = router.execute(MutationRequest(
            mutation_name="state_mutate",
            intent="test matching",
            execute_fn=lambda: ("done", True),
            metadata={"files_changed": ["transports/api/foo.py"]},
        ))
        assert response.success is True
        assert len(tmpl.match_calls) >= 1

    def test_signal_feed_consumed_in_fast_path(self):
        """Verify signal feed from learning loop is consumed by governance."""
        from substrate.organism.event_spine import EventSpine
        from substrate.organism.execution_journal import ExecutionJournal
        from substrate.organism.execution_modes import ExecutionMode, ExecutionModeManager
        from substrate.organism.governed_spine import GovernedExecutionSpine
        from substrate.organism.outcome_learning import OutcomeLearningLoop

        reg = MutationRegistry()
        mode_mgr = ExecutionModeManager()
        mode_mgr._current_mode = ExecutionMode.ASSISTED
        learning = OutcomeLearningLoop()

        spine = GovernedExecutionSpine(
            event_spine=EventSpine(),
            execution_mode=mode_mgr,
            mutation_registry=reg,
            journal=ExecutionJournal(),
            learning_loop=learning,
        )

        from substrate.organism.action_envelope import ActionEnvelope, ActionType
        envelope = ActionEnvelope(
            intent="test signal feed",
            action_type=ActionType.STATE,
            source="test",
            execute_fn=lambda: ("ok", True),
        )
        result = spine._check_fast_path(envelope)
        assert result.reason != ""

    def test_compounding_metadata_propagated(self):
        """When compounding finds candidates, metadata is set on envelope."""
        from substrate.organism.event_spine import EventSpine
        from substrate.organism.execution_journal import ExecutionJournal
        from substrate.organism.execution_modes import ExecutionMode, ExecutionModeManager
        from substrate.organism.governed_spine import GovernedExecutionSpine
        from substrate.organism.outcome_learning import OutcomeLearningLoop

        class MockCompEngine:
            def scan_after_cycle(self, outcomes, **kw):
                from dataclasses import dataclass

                @dataclass
                class FakeCandidate:
                    candidate_id: str = "c1"
                    source_description: str = "test"
                    confidence: float = 0.9

                return [FakeCandidate()]

        reg = MutationRegistry()
        mode_mgr = ExecutionModeManager()
        mode_mgr._current_mode = ExecutionMode.ASSISTED

        spine = GovernedExecutionSpine(
            event_spine=EventSpine(),
            execution_mode=mode_mgr,
            mutation_registry=reg,
            journal=ExecutionJournal(),
            learning_loop=OutcomeLearningLoop(),
            compounding_engine=MockCompEngine(),
        )
        router = MutationRouter(spine=spine, registry=reg)

        response = router.execute(MutationRequest(
            mutation_name="state_mutate",
            intent="test candidates",
            execute_fn=lambda: ("done", True),
        ))
        assert response.success is True
        assert response.envelope is not None
        assert response.envelope.metadata.get("compounding_candidates") == 1


# ── Phase 7: Validation — Mutation Equivalence ─────────────────────────────


class TestMutationEquivalenceValidation:
    """Verify C34 achieved 0% spine bypass rate and structural coverage."""

    def test_enforcement_gate_clean(self):
        """The enforcement hook reports 0 violations across all route files."""
        import subprocess

        repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        result = subprocess.run(
            [sys.executable, "scripts/check_ungoverned_mutations.py", "--all"],
            capture_output=True,
            text=True,
            cwd=repo,
        )
        assert result.returncode == 0, f"Gate failed: {result.stdout}"
        assert "clean" in result.stdout.lower()

    def test_structural_audit_zero_bypasses(self):
        """Benchmark H structural audit shows 0 spine bypasses."""
        import subprocess

        repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        result = subprocess.run(
            [
                sys.executable, "-c",
                "import os, sys, json; "
                f"os.environ['UMH_ROOT'] = '{repo}'; "
                "sys.path.insert(0, os.environ['UMH_ROOT']); "
                "from substrate.organism.benchmarks.mutation_equivalence import MutationEquivalenceScorer; "
                "s = MutationEquivalenceScorer(store_path='/nonexistent/path.jsonl'); "
                "a = s.structural_audit(); "
                "print(json.dumps(a))",
            ],
            capture_output=True,
            text=True,
            cwd=repo,
        )
        assert result.returncode == 0, result.stderr
        audit = json.loads(result.stdout.strip())
        assert audit["potential_bypasses"] == 0, (
            f"Expected 0 bypasses, got {audit['potential_bypasses']}: "
            f"{audit.get('bypasses', [])}"
        )

    def test_all_mutation_files_spine_connected(self):
        """Every mutation route file has a spine/governed import."""
        import subprocess

        repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        result = subprocess.run(
            [
                sys.executable, "-c",
                "import os, sys, json; "
                f"os.environ['UMH_ROOT'] = '{repo}'; "
                "sys.path.insert(0, os.environ['UMH_ROOT']); "
                "from substrate.organism.benchmarks.mutation_equivalence import MutationEquivalenceScorer; "
                "s = MutationEquivalenceScorer(store_path='/nonexistent/path.jsonl'); "
                "a = s.structural_audit(); "
                "print(json.dumps(a))",
            ],
            capture_output=True,
            text=True,
            cwd=repo,
        )
        assert result.returncode == 0, result.stderr
        audit = json.loads(result.stdout.strip())
        assert audit["mutation_route_files"] > 0
        assert audit["spine_connected"] == audit["mutation_route_files"], (
            f"{audit['spine_connected']}/{audit['mutation_route_files']} "
            f"mutation files connected to spine"
        )

    def test_governed_mutation_import_coverage(self):
        """At least 70 Python route files have governed_mutation import."""
        import subprocess

        repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        result = subprocess.run(
            ["grep", "-rl", "governed_mutation", "transports/api/", "--include=*.py"],
            capture_output=True,
            text=True,
            cwd=repo,
        )
        files = [f for f in result.stdout.strip().split("\n") if f]
        assert len(files) >= 70, f"Expected >= 70, got {len(files)}"

    def test_event_spine_websocket_bridge_wired(self):
        """Phase 6: app.py subscribes EventSpine to WebSocket broadcast."""
        repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        app_path = os.path.join(repo, "transports", "api", "app.py")
        with open(app_path) as f:
            content = f.read()
        assert "cockpit_ws_bridge" in content
        assert "event_spine_to_ws" in content or "_event_spine_to_ws" in content
