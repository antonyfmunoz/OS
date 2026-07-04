"""WP-P0-001 — Fail-closed governed_mutation() regression tests.

Proves the mutation entry point fails CLOSED when the control plane (organism
daemon / GovernedExecutionSpine) is unavailable:

  (a) daemon-down + non-LOW-risk mutation      → rejected 503, NO state change
  (b) daemon-down + degraded_mode_allowed low   → executes AND emits degraded audit
  (c) daemon-up                                  → passthrough unchanged
  (d) audit-record emission asserted for the degraded path

All deterministic: no network, no live Neon. The daemon is simulated by
controlling what transports.api.governed._get_router() returns (a mock router
when "up", None when "down").

Run with: pytest tests/test_governed_mutation_fail_closed.py -v
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Import THIS worktree's code, not the sibling /opt/OS checkout. The worktree
# root is two levels up from tests/ (…/p0-001/tests/ -> …/p0-001).
_WORKTREE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _WORKTREE_ROOT not in sys.path:
    sys.path.insert(0, _WORKTREE_ROOT)

from substrate.organism.action_envelope import ActionType, BlastRadius  # noqa: E402
from substrate.organism.mutation_registry import (  # noqa: E402
    MutationRegistry,
    MutationSpec,
)
from substrate.organism.mutation_router import (  # noqa: E402
    DegradedDecision,
    MutationRequest,
    evaluate_degraded_mutation,
    route_mutation_degraded,
)

pytestmark = pytest.mark.smoke


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def isolated_ledger(tmp_path, monkeypatch):
    """Point the execution ledger at a throwaway JSONL file and reset the
    module-level singleton so each test observes only its own audit records."""
    monkeypatch.setenv("UMH_ROOT", str(tmp_path))
    import substrate.organism.execution_ledger as led_mod

    led_mod._ledger_instance = None  # force re-init against tmp UMH_ROOT
    new_path = tmp_path / "data" / "runtime" / "execution_ledger.jsonl"
    monkeypatch.setattr(led_mod, "_LEDGER_PATH", new_path, raising=False)

    ledger = led_mod.get_execution_ledger()
    ledger._path = new_path
    yield ledger

    led_mod._ledger_instance = None


@pytest.fixture
def registry_with_test_specs():
    """A standalone registry with two extra specs that exercise both sides of
    the fail-closed rules table."""
    reg = MutationRegistry()
    reg.register(
        MutationSpec(
            name="test_degraded_ok",
            action_type=ActionType.STATE,
            risk_level="low",
            blast_radius=BlastRadius.LOCAL_RUNTIME,
            degraded_mode_allowed=True,
            description="test-only: low-risk local, opted in",
        )
    )
    reg.register(
        MutationSpec(
            name="test_low_no_optin",
            action_type=ActionType.STATE,
            risk_level="low",
            blast_radius=BlastRadius.LOCAL_RUNTIME,
            degraded_mode_allowed=False,
            description="test-only: low-risk local, NOT opted in",
        )
    )
    reg.register(
        MutationSpec(
            name="test_high_optin",
            action_type=ActionType.STATE,
            risk_level="high",
            blast_radius=BlastRadius.LOCAL_RUNTIME,
            degraded_mode_allowed=True,
            description="test-only: high-risk but opted in (must still fail closed)",
        )
    )
    reg.register(
        MutationSpec(
            name="test_optin_nonlocal",
            action_type=ActionType.STATE,
            risk_level="low",
            blast_radius=BlastRadius.EXTERNAL,
            degraded_mode_allowed=True,
            description="test-only: low-risk opted-in but non-local blast radius",
        )
    )
    return reg


# ── (a) daemon-down + non-LOW-risk → blocked 503, no state change ─────────────


class TestFailClosedNonLowRisk:
    def test_high_risk_rejected_no_state_change(self, isolated_ledger):
        state = {"written": False}

        def execute_fn():
            state["written"] = True
            return ("SHOULD NOT RUN", True)

        # git_mutate is high-risk in the built-in registry; not degraded-allowed.
        req = MutationRequest(
            mutation_name="git_mutate",
            intent="force push to main",
            execute_fn=execute_fn,
        )
        resp = route_mutation_degraded(req)

        assert resp.success is False
        assert resp.http_status == 503
        assert resp.status == "rejected_control_plane_unavailable"
        assert state["written"] is False, "execute_fn must NOT run when fail-closed"

    def test_critical_risk_rejected(self, isolated_ledger):
        state = {"written": False}

        def execute_fn():
            state["written"] = True
            return ("SHOULD NOT RUN", True)

        req = MutationRequest(
            mutation_name="deployment",  # critical in built-in registry
            intent="deploy to prod without governance",
            execute_fn=execute_fn,
        )
        resp = route_mutation_degraded(req)

        assert resp.success is False
        assert resp.http_status == 503
        assert state["written"] is False

    def test_low_risk_without_optin_rejected(self, isolated_ledger, registry_with_test_specs):
        state = {"written": False}

        def execute_fn():
            state["written"] = True
            return ("SHOULD NOT RUN", True)

        req = MutationRequest(
            mutation_name="test_low_no_optin",
            intent="low risk but not opted in",
            execute_fn=execute_fn,
        )
        resp = route_mutation_degraded(req, registry=registry_with_test_specs)

        assert resp.success is False
        assert resp.http_status == 503
        assert state["written"] is False

    def test_settings_update_low_but_not_optin_rejected(self, isolated_ledger):
        """A real built-in low-risk API mutation still fails closed because it
        does not opt into degraded mode."""
        state = {"written": False}

        def execute_fn():
            state["written"] = True
            return ("SHOULD NOT RUN", True)

        req = MutationRequest(
            mutation_name="settings_update",
            intent="update a setting while daemon down",
            execute_fn=execute_fn,
        )
        resp = route_mutation_degraded(req)

        assert resp.success is False
        assert state["written"] is False


# ── (b) daemon-down + degraded_mode_allowed low-risk → succeeds + audit ───────


class TestDegradedAllowedExecutes:
    def test_degraded_allowed_executes_and_writes(self, isolated_ledger, registry_with_test_specs):
        state = {"written": False}

        def execute_fn():
            state["written"] = True
            return ("did the safe read", True)

        req = MutationRequest(
            mutation_name="test_degraded_ok",
            intent="safe low-risk local read",
            execute_fn=execute_fn,
        )
        resp = route_mutation_degraded(req, registry=registry_with_test_specs)

        assert resp.success is True
        assert resp.degraded is True
        assert resp.status == "completed_degraded"
        assert state["written"] is True

    def test_builtin_repo_health_degraded_allowed(self, isolated_ledger):
        """The built-in read-only repo_health scan is opted in and executes."""
        ran = {"count": 0}

        def execute_fn():
            ran["count"] += 1
            return ("health: ok", True)

        req = MutationRequest(
            mutation_name="repo_health",
            intent="degraded read-only health scan",
            execute_fn=execute_fn,
        )
        resp = route_mutation_degraded(req)

        assert resp.success is True
        assert resp.degraded is True
        assert ran["count"] == 1


# ── (d) audit-record emission asserted ────────────────────────────────────────


class TestAuditRecordEmission:
    def test_rejected_path_emits_audit(self, isolated_ledger):
        req = MutationRequest(
            mutation_name="git_mutate",
            intent="force push (rejected)",
            execute_fn=lambda: ("x", True),
        )
        route_mutation_degraded(req)

        entries = isolated_ledger.query(limit=50)
        statuses = [e.status for e in entries]
        assert "rejected_fail_closed" in statuses, statuses
        rej = [e for e in entries if e.status == "rejected_fail_closed"][0]
        assert "[DEGRADED]" in rej.description
        assert rej.executor_type == "degraded_mode"

    def test_degraded_execution_emits_completed_audit(
        self, isolated_ledger, registry_with_test_specs
    ):
        req = MutationRequest(
            mutation_name="test_degraded_ok",
            intent="safe read (audited)",
            execute_fn=lambda: ("ok", True),
        )
        route_mutation_degraded(req, registry=registry_with_test_specs)

        entries = isolated_ledger.query(limit=50)
        statuses = [e.status for e in entries]
        # Both the pre-execution "executing" marker and the terminal
        # "completed" marker must be recorded — no silent path.
        assert "degraded_executing" in statuses, statuses
        assert "degraded_completed" in statuses, statuses

    def test_degraded_execution_failure_is_audited(self, isolated_ledger, registry_with_test_specs):
        def boom():
            raise RuntimeError("execute blew up")

        req = MutationRequest(
            mutation_name="test_degraded_ok",
            intent="failing safe read",
            execute_fn=boom,
        )
        resp = route_mutation_degraded(req, registry=registry_with_test_specs)

        assert resp.success is False
        assert resp.status == "failed_degraded"
        statuses = [e.status for e in isolated_ledger.query(limit=50)]
        assert "degraded_failed" in statuses, statuses


# ── (c) daemon-up → behavior unchanged (passthrough) ──────────────────────────


class TestDaemonUpPassthrough:
    def test_router_present_routes_through_spine(self):
        """When _get_router() returns a router (daemon up), governed_mutation
        delegates to router.execute() and NEVER touches the degraded path."""
        import transports.api.governed as gov
        from substrate.organism.mutation_router import MutationResponse

        fake_router = MagicMock()
        fake_router.execute.return_value = MutationResponse(
            success=True, output="governed", status="completed", envelope_id="env-1"
        )

        with (
            patch.object(gov, "_get_router", return_value=fake_router),
            patch.object(gov, "route_mutation_degraded") as mock_degraded,
        ):
            resp = gov.governed_mutation(
                mutation_name="settings_update",
                intent="normal governed update",
                execute_fn=lambda: ("wrote", True),
            )

        assert resp.success is True
        assert resp.status == "completed"
        fake_router.execute.assert_called_once()
        mock_degraded.assert_not_called()

    def test_daemon_down_uses_degraded_gate(self):
        """When _get_router() returns None (daemon down), governed_mutation
        delegates DOWN into route_mutation_degraded — never executes directly."""
        import transports.api.governed as gov
        from substrate.organism.mutation_router import MutationResponse

        state = {"written": False}

        def execute_fn():
            state["written"] = True
            return ("wrote", True)

        with (
            patch.object(gov, "_get_router", return_value=None),
            patch.object(
                gov,
                "route_mutation_degraded",
                return_value=MutationResponse(
                    success=False, status="rejected_control_plane_unavailable"
                ),
            ) as mock_degraded,
        ):
            resp = gov.governed_mutation(
                mutation_name="git_mutate",
                intent="force push while down",
                execute_fn=execute_fn,
            )

        mock_degraded.assert_called_once()
        assert resp.success is False
        assert state["written"] is False


# ── Pure rules-table unit coverage ────────────────────────────────────────────


class TestDeterministicRulesTable:
    def test_unregistered_rejected(self):
        reg = MutationRegistry()
        d = evaluate_degraded_mutation(
            MutationRequest(
                mutation_name="does_not_exist",
                intent="x",
                execute_fn=lambda: ("", True),
            ),
            reg,
        )
        assert isinstance(d, DegradedDecision)
        assert d.allowed is False

    def test_optin_high_risk_still_rejected(self, registry_with_test_specs):
        """Opt-in alone must not bypass the risk gate: a high-risk spec with
        degraded_mode_allowed=True still fails closed on the risk check."""
        d = evaluate_degraded_mutation(
            MutationRequest(
                mutation_name="test_high_optin",
                intent="x",
                execute_fn=lambda: ("", True),
            ),
            registry_with_test_specs,
        )
        assert d.allowed is False
        assert "risk=high" in d.reason

    def test_optin_nonlocal_blast_rejected(self, registry_with_test_specs):
        """Opt-in + low risk but non-local blast radius must fail closed."""
        d = evaluate_degraded_mutation(
            MutationRequest(
                mutation_name="test_optin_nonlocal",
                intent="x",
                execute_fn=lambda: ("", True),
            ),
            registry_with_test_specs,
        )
        assert d.allowed is False
        assert "blast_radius" in d.reason

    def test_optin_missing_rejected(self):
        """A real high-risk built-in (not opted in) fails closed."""
        reg = MutationRegistry()
        d = evaluate_degraded_mutation(
            MutationRequest(mutation_name="git_mutate", intent="x", execute_fn=lambda: ("", True)),
            reg,
        )
        assert d.allowed is False
        assert "degraded_mode_allowed is False" in d.reason

    def test_low_risk_optin_allowed(self, registry_with_test_specs):
        d = evaluate_degraded_mutation(
            MutationRequest(
                mutation_name="test_degraded_ok",
                intent="x",
                execute_fn=lambda: ("", True),
            ),
            registry_with_test_specs,
        )
        assert d.allowed is True
