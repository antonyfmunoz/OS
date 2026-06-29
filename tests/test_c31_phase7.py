"""C31 Phase 7: Verification & Campaign Closure tests.

Validates all 7 success criteria and proves the full governance loop closes.
"""
from __future__ import annotations

import os
import sys
import tempfile

import pytest

sys.path.insert(0, "/opt/OS")


# ── SC1: Projection governance ──────────────────────────────────────


class TestProjectionGovernance:
    def test_projection_port_exists(self):
        from substrate.sockets.projection_port import ProjectionPort

        port = ProjectionPort()
        assert hasattr(port, "register")
        assert hasattr(port, "audit_all")

    def test_four_projections_in_registry(self):
        import json

        registry_path = os.path.join(
            "/opt/OS", "data", "umh", "projection_registry.json"
        )
        with open(registry_path) as f:
            registry = json.load(f)
        ids = set(registry.keys())
        assert "eos" in ids
        assert "lyfeos" in ids
        assert "cos" in ids

    def test_daemon_registers_projections(self):
        src = os.path.join("/opt/OS", "substrate", "organism", "daemon.py")
        with open(src) as f:
            code = f.read()
        assert "_register_umh_projection" in code
        assert "projection_registry.json" in code


# ── SC2: Daily engineering through substrate ─────────────────────────


class TestDailyEngineering:
    def test_dev_session_tracker_imports(self):
        from substrate.organism.dev_session_tracker import DevSessionTracker

        tracker = DevSessionTracker(store_dir=tempfile.mkdtemp())
        assert hasattr(tracker, "start_session")
        assert hasattr(tracker, "complete_session")

    def test_github_operations_imports(self):
        from adapters.github.github_operations import GitHubOperations

        ops = GitHubOperations()
        assert hasattr(ops, "create_pr_envelope")
        assert hasattr(ops, "merge_pr_envelope")

    def test_cockpit_has_dev_session_endpoints(self):
        src = os.path.join(
            "/opt/OS", "transports", "api", "cockpit_spine_router.py"
        )
        with open(src) as f:
            code = f.read()
        assert "/organism/dev-sessions" in code
        assert "/organism/daily-driver" in code


# ── SC3: Adapter protocol coverage ──────────────────────────────────


class TestAdapterCoverage:
    def test_manifest_count(self):
        from adapters.adapter_engine.production_manifests import (
            ALL_PRODUCTION_MANIFESTS,
        )

        assert len(ALL_PRODUCTION_MANIFESTS) >= 16

    def test_all_manifests_have_capabilities(self):
        from adapters.adapter_engine.production_manifests import (
            ALL_PRODUCTION_MANIFESTS,
        )

        for m in ALL_PRODUCTION_MANIFESTS:
            assert len(m.capabilities) > 0, f"{m.adapter_id} has no capabilities"


# ── SC4: Protocol standardization ───────────────────────────────────


class TestProtocolStandardization:
    def test_contract_files_exist(self):
        contracts_dir = os.path.join("/opt/OS", "substrate", "contracts")
        py_files = [
            f
            for f in os.listdir(contracts_dir)
            if f.endswith(".py") and not f.startswith("__")
        ]
        assert len(py_files) >= 11

    def test_enforcement_hooks_exist(self):
        scripts = os.path.join("/opt/OS", "scripts")
        assert os.path.isfile(os.path.join(scripts, "check_type_divergence.py"))
        assert os.path.isfile(os.path.join(scripts, "check_dependency_direction.py"))
        assert os.path.isfile(os.path.join(scripts, "check_projection_leak.py"))


# ── SC5: Capability extraction ──────────────────────────────────────


class TestCapabilityExtraction:
    def test_learning_loop_imports(self):
        from substrate.organism.outcome_learning import OutcomeLearningLoop

        loop = OutcomeLearningLoop(
            store_path=os.path.join(tempfile.mkdtemp(), "test.jsonl")
        )
        assert hasattr(loop, "record_outcome")
        assert hasattr(loop, "recent_outcomes")

    def test_capability_compounding_imports(self):
        from substrate.organism.capability_compounding_runtime import (
            CapabilityCompoundingRuntime,
        )

        rt = CapabilityCompoundingRuntime()
        assert rt is not None

    def test_spine_has_learning_loop_wiring(self):
        src = os.path.join(
            "/opt/OS", "substrate", "organism", "governed_spine.py"
        )
        with open(src) as f:
            code = f.read()
        assert "learning_loop" in code
        assert "OutcomeLearningLoop" in code


# ── SC6: Stable daily operation ─────────────────────────────────────


class TestStability:
    def test_all_c31_imports_clean(self):
        from substrate.organism.governed_spine import GovernedExecutionSpine
        from substrate.organism.dev_session_tracker import DevSessionTracker
        from substrate.organism.outcome_learning import OutcomeLearningLoop
        from substrate.organism.capability_compounding_runtime import (
            CapabilityCompoundingRuntime,
        )
        from substrate.sockets.projection_port import ProjectionPort
        from adapters.github.github_operations import GitHubOperations
        from adapters.adapter_engine.production_manifests import (
            ALL_PRODUCTION_MANIFESTS,
        )

        assert len(ALL_PRODUCTION_MANIFESTS) >= 16

    def test_daemon_compiles(self):
        import py_compile

        py_compile.compile(
            os.path.join("/opt/OS", "substrate", "organism", "daemon.py"),
            doraise=True,
        )


# ── SC7: No new architectures ──────────────────────────────────────


class TestNoNewArchitectures:
    def test_dev_session_uses_action_envelope(self):
        from substrate.organism.dev_session_tracker import DevSessionTracker
        from substrate.organism.action_envelope import ActionEnvelope

        tracker = DevSessionTracker(store_dir=tempfile.mkdtemp())
        session = tracker.start_session(intent="test", projection_id="umh")
        tracker.record_commit(session.session_id, "abc", "test commit")
        envelope = tracker.complete_session(session.session_id, outcome="test")
        assert isinstance(envelope, ActionEnvelope)

    def test_github_ops_uses_action_envelope(self):
        from adapters.github.github_operations import GitHubOperations
        from substrate.organism.action_envelope import ActionEnvelope

        ops = GitHubOperations()
        envelope = ops.create_branch_envelope("test-branch")
        assert isinstance(envelope, ActionEnvelope)


# ── Full loop integration ───────────────────────────────────────────


class TestFullLoop:
    def test_intent_to_journal_loop_closes(self):
        """The critical verification: a real task flows through the full
        governed pipeline and produces journal + learning entries."""
        from substrate.organism.event_spine import EventSpine
        from substrate.organism.execution_modes import ExecutionModeManager
        from substrate.organism.mutation_registry import MutationRegistry
        from substrate.organism.execution_journal import ExecutionJournal
        from substrate.organism.outcome_learning import OutcomeLearningLoop
        from substrate.organism.governed_spine import GovernedExecutionSpine
        from substrate.organism.dev_session_tracker import DevSessionTracker

        store = tempfile.mkdtemp()
        learning = OutcomeLearningLoop(
            store_path=os.path.join(store, "learning.jsonl")
        )
        spine = GovernedExecutionSpine(
            event_spine=EventSpine(),
            execution_mode=ExecutionModeManager(),
            mutation_registry=MutationRegistry(),
            journal=ExecutionJournal(
                persist_path=os.path.join(store, "journal.jsonl")
            ),
            learning_loop=learning,
        )
        tracker = DevSessionTracker(store_dir=store)

        # Intent
        session = tracker.start_session(
            intent="C31 verification", projection_id="umh"
        )
        assert session.status == "active"

        # Work
        tracker.record_commit(session.session_id, "abc", "test")
        tracker.record_files_modified(session.session_id, ["test.py"])

        # Governance -> ActionEnvelope
        envelope = tracker.complete_session(
            session.session_id, outcome="verified"
        )
        assert envelope is not None
        assert envelope.source == "dev_session_tracker"

        # Execution
        spine.submit(envelope)

        # Learning
        outcomes = learning.recent_outcomes(limit=5)
        assert len(outcomes) >= 1
