"""Tests for Phase 6.2 — Execution Spine Enforcement + SpineGuard Ladder.

Validates:
  - SpineGuard enforcement ladder (OFF/WARN/BLOCK_HIGH_RISK/ENFORCE_ALL)
  - Production-safe enforcement scenarios
  - Mutation registry completeness and contract validation
  - Reliability/rollback contracts
  - Cockpit spine router integration
  - Execution doctrine unified view
"""

from __future__ import annotations

import sys
sys.path.insert(0, "/opt/OS/.claude/worktrees/anti-divergence-gate")

import time
from substrate.organism.action_envelope import (
    ActionEnvelope,
    ActionType,
    BlastRadius,
    EnvelopeStatus,
    ExecutionConstraints,
    ReversibilityClass,
    RollbackStrategy,
    VerificationStrategy,
)
from substrate.organism.event_spine import EventDomain, EventSpine
from substrate.organism.execution_journal import ExecutionJournal, JournalPhase
from substrate.organism.execution_modes import (
    ExecutionMode,
    ExecutionModeManager,
    TransitionReason,
)
from substrate.organism.governed_spine import GovernedExecutionSpine
from substrate.organism.leverage_metrics import LeverageMetrics
from substrate.organism.mutation_registry import (
    MutationRegistry,
    MutationSpec,
    CONTAINER_RESTART,
    DOCKER_EXEC,
    TMUX_SEND,
    SHELL_EXECUTE,
    PROCESS_KILL,
    GIT_MUTATE,
    REMOTE_NODE_EXEC,
    FILE_WRITE,
    FILE_DELETE,
    SOUL_DOC_WRITE,
    SESSION_LAUNCH,
    DEPLOYMENT,
    CREDENTIAL_WRITE,
    LOG_ROTATION,
    RUNTIME_REFRESH,
    TEST_SUITE_RUN,
    GRAPH_REBUILD,
    BRANCH_CLEANUP,
    DISK_CLEANUP,
    REPO_HEALTH_SCAN,
    DOCKER_HEALTH_SCAN,
    RUNTIME_RECONCILIATION,
)
from substrate.organism.spine_guard import GuardMode, SpineGuard


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_spine(
    mode: ExecutionMode = ExecutionMode.AUTONOMOUS,
) -> tuple[GovernedExecutionSpine, EventSpine, ExecutionModeManager, ExecutionJournal]:
    event_spine = EventSpine()
    mode_mgr = ExecutionModeManager(initial_mode=mode, event_spine=event_spine)
    registry = MutationRegistry()
    journal = ExecutionJournal()
    leverage = LeverageMetrics(event_spine=event_spine)
    spine = GovernedExecutionSpine(
        event_spine=event_spine,
        execution_mode=mode_mgr,
        mutation_registry=registry,
        journal=journal,
        leverage_metrics=leverage,
    )
    return spine, event_spine, mode_mgr, journal


def _low_risk_envelope(intent: str = "probe action") -> ActionEnvelope:
    return ActionEnvelope(
        intent=intent,
        action_type=ActionType.STATE,
        source="test",
        execute_fn=lambda: ("probed", True),
        risk_level="low",
        metadata={"mutation_name": "repo_health"},
    )


def _medium_risk_envelope(intent: str = "restart container") -> ActionEnvelope:
    return ActionEnvelope(
        intent=intent,
        action_type=ActionType.CONTAINER,
        source="test",
        execute_fn=lambda: ("restarted", True),
        risk_level="medium",
        constraints=ExecutionConstraints(require_approval=True),
        metadata={"mutation_name": "container_restart"},
    )


def _high_risk_envelope(intent: str = "docker exec") -> ActionEnvelope:
    return ActionEnvelope(
        intent=intent,
        action_type=ActionType.CONTAINER,
        source="test",
        execute_fn=lambda: ("executed", True),
        risk_level="high",
        constraints=ExecutionConstraints(require_approval=True),
        metadata={"mutation_name": "docker_exec"},
    )


def _critical_risk_envelope(intent: str = "deploy to prod") -> ActionEnvelope:
    return ActionEnvelope(
        intent=intent,
        action_type=ActionType.DEPLOYMENT,
        source="test",
        execute_fn=lambda: ("deployed", True),
        risk_level="critical",
        constraints=ExecutionConstraints(require_approval=True),
        metadata={"mutation_name": "deployment"},
    )


# ── SpineGuard Enforcement Ladder Tests ───────────────────────────────────────


class TestSpineGuardEnforcementLadder:
    """Tests for the 4-level enforcement ladder: OFF → WARN → BLOCK_HIGH_RISK → ENFORCE_ALL."""

    def test_guard_mode_enum(self):
        assert GuardMode.OFF.value == "off"
        assert GuardMode.WARN.value == "warn"
        assert GuardMode.BLOCK_HIGH_RISK.value == "block_high_risk"
        assert GuardMode.ENFORCE_ALL.value == "enforce_all"

    def test_off_mode_allows_everything(self):
        guard = SpineGuard(mode=GuardMode.OFF)
        assert guard.check_direct_mutation("test", "low mutation", "low") is False
        assert guard.check_direct_mutation("test", "medium mutation", "medium") is False
        assert guard.check_direct_mutation("test", "high mutation", "high") is False
        assert guard.check_direct_mutation("test", "critical mutation", "critical") is False
        assert guard.to_dict()["total_violations"] == 0
        assert guard.to_dict()["total_blocked"] == 0
        assert guard.to_dict()["total_allowed"] == 4

    def test_warn_mode_logs_but_never_blocks(self):
        event_spine = EventSpine()
        journal = ExecutionJournal()
        guard = SpineGuard(mode=GuardMode.WARN, event_spine=event_spine, journal=journal)

        assert guard.check_direct_mutation("test", "low mutation", "low") is False
        assert guard.check_direct_mutation("test", "medium mutation", "medium") is False
        assert guard.check_direct_mutation("test", "high mutation", "high") is False
        assert guard.check_direct_mutation("test", "critical mutation", "critical") is False

        stats = guard.to_dict()
        assert stats["total_violations"] == 4
        assert stats["total_blocked"] == 0
        assert stats["total_allowed"] == 4

        events = event_spine.recent(10)
        assert len(events) == 4
        assert all(e.event_type == "spine_guard_violation" for e in events)

    def test_block_high_risk_allows_low(self):
        guard = SpineGuard(mode=GuardMode.BLOCK_HIGH_RISK)
        assert guard.check_direct_mutation("test", "low probe", "low") is False

    def test_block_high_risk_blocks_medium(self):
        guard = SpineGuard(mode=GuardMode.BLOCK_HIGH_RISK)
        assert guard.check_direct_mutation("test", "medium mutation", "medium") is True

    def test_block_high_risk_blocks_high(self):
        guard = SpineGuard(mode=GuardMode.BLOCK_HIGH_RISK)
        assert guard.check_direct_mutation("test", "high mutation", "high") is True

    def test_block_high_risk_blocks_critical(self):
        guard = SpineGuard(mode=GuardMode.BLOCK_HIGH_RISK)
        assert guard.check_direct_mutation("test", "critical mutation", "critical") is True

    def test_enforce_all_blocks_everything(self):
        guard = SpineGuard(mode=GuardMode.ENFORCE_ALL)
        assert guard.check_direct_mutation("test", "low probe", "low") is True
        assert guard.check_direct_mutation("test", "medium mutation", "medium") is True
        assert guard.check_direct_mutation("test", "high mutation", "high") is True
        assert guard.check_direct_mutation("test", "critical mutation", "critical") is True

        stats = guard.to_dict()
        assert stats["total_blocked"] == 4
        assert stats["total_allowed"] == 0

    def test_mode_transition_at_runtime(self):
        guard = SpineGuard(mode=GuardMode.WARN)
        assert guard.check_direct_mutation("test", "starts warn", "medium") is False

        guard.set_mode(GuardMode.BLOCK_HIGH_RISK)
        assert guard.mode == GuardMode.BLOCK_HIGH_RISK
        assert guard.check_direct_mutation("test", "now blocked", "medium") is True

        guard.set_mode(GuardMode.ENFORCE_ALL)
        assert guard.check_direct_mutation("test", "even low blocked", "low") is True

    def test_mode_change_emits_event(self):
        event_spine = EventSpine()
        guard = SpineGuard(mode=GuardMode.WARN, event_spine=event_spine)
        guard.set_mode(GuardMode.BLOCK_HIGH_RISK)

        events = event_spine.recent(10)
        mode_events = [e for e in events if e.event_type == "spine_guard_mode_changed"]
        assert len(mode_events) == 1
        assert mode_events[0].data["old_mode"] == "warn"
        assert mode_events[0].data["new_mode"] == "block_high_risk"

    def test_blocked_violations_filtered(self):
        guard = SpineGuard(mode=GuardMode.BLOCK_HIGH_RISK)
        guard.check_direct_mutation("src1", "low action", "low")
        guard.check_direct_mutation("src2", "medium action", "medium")
        guard.check_direct_mutation("src3", "high action", "high")

        blocked = guard.blocked_violations()
        assert len(blocked) == 2
        assert all(v["blocked"] for v in blocked)

        all_violations = guard.recent_violations()
        assert len(all_violations) == 3

    def test_journal_recording(self):
        journal = ExecutionJournal()
        guard = SpineGuard(mode=GuardMode.BLOCK_HIGH_RISK, journal=journal)
        guard.check_direct_mutation("test_src", "test mutation", "high")

        entries = journal.recent(10)
        assert len(entries) == 1
        entry = entries[0]
        assert entry.phase == JournalPhase.GOVERNANCE_CHECK
        assert "spine_guard:test_src" in entry.source
        assert entry.details["blocked"] is True
        assert entry.details["guard_mode"] == "block_high_risk"

    def test_event_type_differs_for_blocked_vs_warned(self):
        event_spine = EventSpine()
        guard = SpineGuard(mode=GuardMode.BLOCK_HIGH_RISK, event_spine=event_spine)

        guard.check_direct_mutation("src1", "low allowed", "low")
        guard.check_direct_mutation("src2", "high blocked", "high")

        events = event_spine.recent(10)
        assert events[0].event_type == "spine_guard_violation"
        assert events[1].event_type == "spine_guard_blocked"

    def test_legacy_report_direct_mutation_compat(self):
        guard = SpineGuard(mode=GuardMode.BLOCK_HIGH_RISK)
        guard.report_direct_mutation("legacy_src", "legacy call")
        stats = guard.to_dict()
        assert stats["total_violations"] == 1
        assert stats["total_blocked"] == 1

    def test_default_mode_is_block_high_risk(self):
        guard = SpineGuard()
        assert guard.mode == GuardMode.BLOCK_HIGH_RISK


# ── Production-Safe Enforcement Tests ─────────────────────────────────────────


class TestProductionEnforcement:
    """Task 6: Controlled enforcement scenarios matching production behavior."""

    def test_low_risk_through_spine_executes(self):
        """Scenario 1: LOW-risk action through spine — should execute."""
        spine, _, _, journal = _make_spine()
        env = _low_risk_envelope()
        result = spine.submit(env)

        assert result.status == EnvelopeStatus.COMPLETED
        assert result.result_success is True
        assert result.result_output == "probed"

        entries = journal.entries_for(env.envelope_id)
        phases = [e.phase for e in entries]
        assert JournalPhase.PROPOSED in phases
        assert JournalPhase.EXECUTION_COMPLETED in phases

    def test_medium_risk_without_approval_pends(self):
        """Scenario 2: MEDIUM-risk action without approval — should pend/block."""
        spine, _, _, journal = _make_spine()
        env = _medium_risk_envelope()
        result = spine.submit(env)

        assert result.status == EnvelopeStatus.PROPOSED
        pending = spine.pending_envelopes()
        assert len(pending) == 1
        assert pending[0]["envelope_id"] == env.envelope_id

    def test_medium_risk_approved_executes(self):
        """Scenario 3: Approve MEDIUM-risk action — should execute."""
        spine, event_spine, _, journal = _make_spine()
        env = _medium_risk_envelope()
        spine.submit(env)

        approved = spine.approve(env.envelope_id, approved_by="test_operator")
        assert approved is not None
        assert approved.status == EnvelopeStatus.COMPLETED
        assert approved.result_success is True
        assert approved.approved_by == "test_operator"

        events = event_spine.recent(100)
        event_types = [e.event_type for e in events]
        assert "envelope_proposed" in event_types
        assert "envelope_awaiting_approval" in event_types
        assert "envelope_executing" in event_types
        assert "envelope_completed" in event_types

    def test_high_risk_direct_blocked_by_spine_guard(self):
        """Scenario 4: Direct high-risk mutation — should be blocked by SpineGuard."""
        event_spine = EventSpine()
        journal = ExecutionJournal()
        guard = SpineGuard(
            mode=GuardMode.BLOCK_HIGH_RISK,
            event_spine=event_spine,
            journal=journal,
        )

        blocked = guard.check_direct_mutation(
            "runtime_adapter",
            "docker exec container bash -c 'rm -rf /'",
            "high",
        )

        assert blocked is True

        stats = guard.to_dict()
        assert stats["total_blocked"] == 1

        events = event_spine.recent(10)
        guard_events = [e for e in events if "spine_guard" in e.event_type]
        assert len(guard_events) == 1
        assert guard_events[0].event_type == "spine_guard_blocked"
        assert guard_events[0].priority.value == "critical"

        journal_entries = journal.recent(10)
        assert len(journal_entries) == 1
        assert journal_entries[0].details["blocked"] is True

    def test_all_four_scenarios_reflect_in_endpoints(self):
        """Scenario 5: Verify EventSpine, journal, and stats reflect all cases."""
        spine, event_spine, _, journal = _make_spine()
        guard = SpineGuard(
            mode=GuardMode.BLOCK_HIGH_RISK,
            event_spine=event_spine,
            journal=journal,
        )

        low_env = _low_risk_envelope()
        spine.submit(low_env)

        med_env = _medium_risk_envelope()
        spine.submit(med_env)
        spine.approve(med_env.envelope_id, approved_by="operator")

        guard.check_direct_mutation("bypass_attempt", "direct docker exec", "high")

        spine_stats = spine.to_dict()
        assert spine_stats["total_executed"] >= 2
        assert spine_stats["total_succeeded"] >= 2
        assert spine_stats["pending_count"] == 0

        guard_stats = guard.to_dict()
        assert guard_stats["total_blocked"] == 1

        all_events = event_spine.recent(100)
        assert len(all_events) > 0

        journal_stats = journal.statistics()
        assert journal_stats["total_entries"] > 0


# ── Mutation Registry Contract Tests ──────────────────────────────────────────


class TestMutationRegistryContracts:
    """Task 7: Every registered mutation has required fields."""

    def test_registry_has_22_builtins(self):
        registry = MutationRegistry()
        specs = registry.all_specs()
        assert len(specs) == 22

    def test_new_phase62_mutations_registered(self):
        registry = MutationRegistry()
        new_names = [
            "docker_exec", "tmux_send", "shell_execute", "process_kill",
            "git_mutate", "remote_node_exec", "file_write", "file_delete",
            "soul_doc_write", "session_launch", "deployment", "credential_write",
        ]
        for name in new_names:
            assert registry.is_registered(name), f"{name} not registered"

    def test_every_spec_has_risk_class(self):
        registry = MutationRegistry()
        valid_risks = {"low", "medium", "high", "critical"}
        for spec in registry.all_specs():
            assert spec.risk_level in valid_risks, f"{spec.name} has invalid risk: {spec.risk_level}"

    def test_every_spec_has_reversibility(self):
        registry = MutationRegistry()
        for spec in registry.all_specs():
            assert isinstance(spec.reversibility, ReversibilityClass), f"{spec.name} missing reversibility"

    def test_every_spec_has_timeout(self):
        registry = MutationRegistry()
        for spec in registry.all_specs():
            assert spec.timeout_seconds > 0, f"{spec.name} has no timeout"

    def test_every_spec_has_blast_radius(self):
        registry = MutationRegistry()
        for spec in registry.all_specs():
            assert isinstance(spec.blast_radius, BlastRadius), f"{spec.name} missing blast radius"

    def test_every_spec_has_allowed_modes(self):
        registry = MutationRegistry()
        for spec in registry.all_specs():
            assert len(spec.allowed_modes) > 0, f"{spec.name} has no allowed modes"

    def test_every_spec_has_description(self):
        registry = MutationRegistry()
        for spec in registry.all_specs():
            assert spec.description, f"{spec.name} missing description"

    def test_high_risk_requires_approval(self):
        registry = MutationRegistry()
        for spec in registry.all_specs():
            if spec.risk_level in ("high", "critical"):
                assert spec.require_approval is True, (
                    f"{spec.name} is risk={spec.risk_level} but doesn't require approval"
                )

    def test_critical_risk_has_verification_or_justification(self):
        registry = MutationRegistry()
        for spec in registry.all_specs():
            if spec.risk_level == "critical":
                assert spec.verification_required or spec.name == "process_kill", (
                    f"{spec.name} is critical but has no verification requirement"
                )

    def test_rollback_supported_implies_reversible(self):
        registry = MutationRegistry()
        for spec in registry.all_specs():
            if spec.rollback_supported:
                assert spec.reversibility != ReversibilityClass.IRREVERSIBLE, (
                    f"{spec.name} supports rollback but is irreversible"
                )

    def test_risk_distribution(self):
        registry = MutationRegistry()
        by_risk = registry.to_dict()["by_risk"]
        assert by_risk["low"] >= 5
        assert by_risk["medium"] >= 4
        assert by_risk["high"] >= 5
        assert by_risk["critical"] >= 3

    def test_incomplete_spec_rejected_by_spine(self):
        """Unregistered mutations are rejected by the spine."""
        spine, _, _, _ = _make_spine()
        env = ActionEnvelope(
            intent="unregistered mutation",
            action_type=ActionType.STATE,
            source="test",
            execute_fn=lambda: ("ok", True),
            metadata={"mutation_name": "nonexistent_thing"},
        )
        result = spine.submit(env)
        assert result.status == EnvelopeStatus.REJECTED
        assert "unregistered" in result.rejected_reason

    def test_to_dict_includes_all_fields(self):
        registry = MutationRegistry()
        spec = registry.lookup("deployment")
        assert spec is not None
        d = spec.to_dict()
        required_keys = {
            "name", "action_type", "risk_level", "reversibility",
            "allowed_modes", "required_capabilities", "verification_required",
            "rollback_supported", "blast_radius", "timeout_seconds",
            "max_retries", "require_approval", "description",
        }
        assert required_keys.issubset(d.keys())


# ── Reliability and Rollback Contract Tests ───────────────────────────────────


class TestReliabilityContracts:
    """Task 7: Verification, rollback, and reliability guarantees."""

    def test_verification_pass_results_in_verified_status(self):
        spine, _, _, _ = _make_spine()
        env = ActionEnvelope(
            intent="verified action",
            action_type=ActionType.STATE,
            source="test",
            execute_fn=lambda: ("done", True),
            verification=VerificationStrategy(
                description="check output",
                verify_fn=lambda: True,
            ),
        )
        result = spine.submit(env)
        assert result.status == EnvelopeStatus.VERIFIED

    def test_verification_fail_results_in_verification_failed(self):
        spine, _, _, _ = _make_spine()
        env = ActionEnvelope(
            intent="bad verification",
            action_type=ActionType.STATE,
            source="test",
            execute_fn=lambda: ("done", True),
            verification=VerificationStrategy(
                description="always fails",
                verify_fn=lambda: False,
            ),
        )
        result = spine.submit(env)
        assert result.status == EnvelopeStatus.VERIFICATION_FAILED

    def test_verification_exception_results_in_verification_failed(self):
        def _verify_boom() -> bool:
            raise RuntimeError("verify crash")

        spine, _, _, _ = _make_spine()
        env = ActionEnvelope(
            intent="verify exception",
            action_type=ActionType.STATE,
            source="test",
            execute_fn=lambda: ("done", True),
            verification=VerificationStrategy(
                description="will crash",
                verify_fn=_verify_boom,
            ),
        )
        result = spine.submit(env)
        assert result.status == EnvelopeStatus.VERIFICATION_FAILED

    def test_rollback_on_failure(self):
        rolled_back = [False]

        def _rollback() -> bool:
            rolled_back[0] = True
            return True

        spine, _, _, journal = _make_spine()
        env = ActionEnvelope(
            intent="fail and rollback",
            action_type=ActionType.STATE,
            source="test",
            execute_fn=lambda: ("oops", False),
            rollback=RollbackStrategy(
                description="restore state",
                rollback_fn=_rollback,
            ),
        )
        result = spine.submit(env)
        assert result.status == EnvelopeStatus.ROLLED_BACK
        assert rolled_back[0] is True

        entries = journal.entries_for(env.envelope_id)
        phases = [e.phase for e in entries]
        assert JournalPhase.ROLLBACK_STARTED in phases
        assert JournalPhase.ROLLBACK_COMPLETED in phases

    def test_rollback_failure_recorded(self):
        def _bad_rollback() -> bool:
            return False

        spine, _, _, journal = _make_spine()
        env = ActionEnvelope(
            intent="rollback will fail",
            action_type=ActionType.STATE,
            source="test",
            execute_fn=lambda: ("oops", False),
            rollback=RollbackStrategy(
                description="will fail",
                rollback_fn=_bad_rollback,
            ),
        )
        result = spine.submit(env)
        assert result.status == EnvelopeStatus.FAILED

        entries = journal.entries_for(env.envelope_id)
        phases = [e.phase for e in entries]
        assert JournalPhase.ROLLBACK_STARTED in phases
        assert JournalPhase.ROLLBACK_FAILED in phases

    def test_retry_contract(self):
        call_count = [0]

        def _flaky() -> tuple[str, bool]:
            call_count[0] += 1
            return ("success" if call_count[0] >= 3 else "fail", call_count[0] >= 3)

        spine, _, _, journal = _make_spine()
        env = ActionEnvelope(
            intent="flaky action",
            action_type=ActionType.STATE,
            source="test",
            execute_fn=_flaky,
            constraints=ExecutionConstraints(max_retries=3),
        )
        result = spine.submit(env)
        assert result.status == EnvelopeStatus.COMPLETED
        assert result.retry_count == 2

        entries = journal.entries_for(env.envelope_id)
        retry_entries = [e for e in entries if e.phase == JournalPhase.RETRY]
        assert len(retry_entries) == 2

    def test_max_retries_exhausted(self):
        spine, _, _, _ = _make_spine()
        env = ActionEnvelope(
            intent="always fails",
            action_type=ActionType.STATE,
            source="test",
            execute_fn=lambda: ("nope", False),
            constraints=ExecutionConstraints(max_retries=2),
        )
        result = spine.submit(env)
        assert result.status == EnvelopeStatus.FAILED
        assert result.retry_count == 2

    def test_idempotency_prevents_re_execution(self):
        spine, _, _, _ = _make_spine()
        env1 = ActionEnvelope(
            intent="idempotent op",
            action_type=ActionType.STATE,
            source="test",
            execute_fn=lambda: ("done", True),
            constraints=ExecutionConstraints(idempotent=True),
        )
        result1 = spine.submit(env1)
        assert result1.status == EnvelopeStatus.COMPLETED

        env2 = ActionEnvelope(
            intent="idempotent op",
            action_type=ActionType.STATE,
            source="test",
            execute_fn=lambda: ("done again", True),
            constraints=ExecutionConstraints(idempotent=True),
        )
        result2 = spine.submit(env2)
        assert result2.status == EnvelopeStatus.REJECTED
        assert "idempotent" in result2.rejected_reason

    def test_success_rate_tracking(self):
        spine, _, _, _ = _make_spine()
        spine.submit(_low_risk_envelope("success1"))
        spine.submit(_low_risk_envelope("success2"))

        fail_env = ActionEnvelope(
            intent="fail",
            action_type=ActionType.STATE,
            source="test",
            execute_fn=lambda: ("fail", False),
            risk_level="low",
        )
        spine.submit(fail_env)

        stats = spine.to_dict()
        assert stats["total_succeeded"] == 2
        assert stats["total_failed"] == 1
        expected_rate = round(2 / 3, 4)
        assert stats["success_rate"] == expected_rate


# ── Daemon Integration Tests ──────────────────────────────────────────────────


class TestDaemonIntegration:
    """Verify daemon wires Phase 6.2 components correctly."""

    def test_daemon_spine_guard_mode_is_block_high_risk(self):
        from substrate.organism.daemon import OrganismDaemon
        daemon = OrganismDaemon(store_dir="/tmp/test_phase62_daemon")
        assert daemon.spine_guard.mode == GuardMode.BLOCK_HIGH_RISK

    def test_daemon_spine_guard_has_journal(self):
        from substrate.organism.daemon import OrganismDaemon
        daemon = OrganismDaemon(store_dir="/tmp/test_phase62_daemon_journal")
        assert daemon.spine_guard._journal is not None

    def test_daemon_mutation_registry_has_22_specs(self):
        from substrate.organism.daemon import OrganismDaemon
        daemon = OrganismDaemon(store_dir="/tmp/test_phase62_daemon_reg")
        specs = daemon.mutation_registry.all_specs()
        assert len(specs) == 22

    def test_daemon_spine_guard_mode_change(self):
        from substrate.organism.daemon import OrganismDaemon
        daemon = OrganismDaemon(store_dir="/tmp/test_phase62_daemon_mode")
        daemon.spine_guard.set_mode(GuardMode.ENFORCE_ALL)
        assert daemon.spine_guard.mode == GuardMode.ENFORCE_ALL

    def test_daemon_execution_mode_manager_exposed(self):
        from substrate.organism.daemon import OrganismDaemon
        daemon = OrganismDaemon(store_dir="/tmp/test_phase62_daemon_emm")
        assert daemon.execution_mode_manager is not None


# ── Cockpit Spine Router Tests ────────────────────────────────────────────────


class TestCockpitSpineRouter:
    """Verify the spine router module structure."""

    def test_spine_router_importable(self):
        from transports.api.cockpit_spine_router import spine_router
        assert spine_router is not None

    def test_spine_router_has_routes_after_configure(self):
        from transports.api import cockpit_spine_router

        async def _mock_operator(request):
            pass

        cockpit_spine_router.configure(
            get_organism_fn=lambda: None,
            check_rate_limit_fn=lambda a, c: None,
            require_operator_dep=_mock_operator,
        )
        route_paths = [r.path for r in cockpit_spine_router.spine_router.routes]
        expected = [
            "/organism/spine",
            "/organism/spine/pending",
            "/organism/spine/active",
            "/organism/spine/completed",
            "/organism/spine/lifecycle/{envelope_id}",
            "/organism/spine/approve/{envelope_id}",
            "/organism/spine/reject/{envelope_id}",
            "/organism/spine/retry/{envelope_id}",
            "/organism/journal",
            "/organism/journal/recent",
            "/organism/journal/lifecycle/{envelope_id}",
            "/organism/journal/statistics",
            "/organism/mutations",
            "/organism/mutations/{mutation_name}",
            "/organism/spine-guard",
            "/organism/spine-guard/blocked",
            "/organism/spine-guard/mode",
            "/organism/execution-doctrine",
            "/organism/reliability",
        ]
        for path in expected:
            assert path in route_paths, f"missing route: {path}"

    def test_privileged_routes_have_auth_dependency(self):
        """Verify that approve/reject/retry/mode routes carry auth dependencies."""
        from transports.api import cockpit_spine_router

        async def _mock_operator(request):
            pass

        cockpit_spine_router.configure(
            get_organism_fn=lambda: None,
            check_rate_limit_fn=lambda a, c: None,
            require_operator_dep=_mock_operator,
        )
        privileged_paths = {
            "/organism/spine/approve/{envelope_id}",
            "/organism/spine/reject/{envelope_id}",
            "/organism/spine/retry/{envelope_id}",
            "/organism/spine-guard/mode",
        }
        for route in cockpit_spine_router.spine_router.routes:
            if hasattr(route, "path") and route.path in privileged_paths:
                assert route.dependencies, f"route {route.path} missing auth dependency"

    def test_configure_function_exists(self):
        from transports.api.cockpit_spine_router import configure
        assert callable(configure)


# ── Risk Classification Consistency Tests ─────────────────────────────────────


class TestRiskClassification:
    """Verify risk classifications follow governance rules."""

    def test_observe_mode_actions_are_low_risk(self):
        registry = MutationRegistry()
        observe_specs = [
            s for s in registry.all_specs()
            if ExecutionMode.OBSERVE in s.allowed_modes
        ]
        for spec in observe_specs:
            assert spec.risk_level == "low", (
                f"{spec.name} allowed in OBSERVE but risk={spec.risk_level}"
            )

    def test_critical_actions_not_in_autonomous(self):
        registry = MutationRegistry()
        for spec in registry.all_specs():
            if spec.risk_level == "critical":
                assert ExecutionMode.AUTONOMOUS not in spec.allowed_modes, (
                    f"{spec.name} is critical but allowed in AUTONOMOUS"
                )

    def test_external_blast_requires_high_or_above(self):
        registry = MutationRegistry()
        for spec in registry.all_specs():
            if spec.blast_radius == BlastRadius.EXTERNAL:
                assert spec.risk_level in ("high", "critical"), (
                    f"{spec.name} has EXTERNAL blast but risk={spec.risk_level}"
                )

    def test_cluster_wide_blast_requires_high_or_above(self):
        registry = MutationRegistry()
        for spec in registry.all_specs():
            if spec.blast_radius == BlastRadius.CLUSTER_WIDE:
                assert spec.risk_level in ("high", "critical"), (
                    f"{spec.name} has CLUSTER_WIDE blast but risk={spec.risk_level}"
                )
