"""Integration tests for Campaign 17 — Workstation MVP Loop.

Proves the operator experience loop works end-to-end:
1. Right Rail clarification: interpret → resolved context
2. Delegation: interpret → delegation readiness assessed
3. Top HUD approval: approvals surface via UnifiedApprovalRuntime
4. Meta IDE binding: intent resolves project/repo/files/goals
5. Full loop: interpret → context → governance → execution → lifecycle
6. No direct execution from Right Rail (invariant)
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from typing import Any
from unittest.mock import MagicMock

from substrate.workstation.orchestrator_presence_runtime import (
    OrchestratorPresenceRuntime,
    PresenceMode,
)
from substrate.workstation.meta_ide_context_runtime import (
    MetaIdeContextRuntime,
    MetaIdeContextSnapshot,
)
from substrate.workstation.workstation_presence_runtime import (
    WorkstationPresenceRuntime,
)


# ── Shared fakes ─────────────────────────────────────────────────────


class _FakeOrchestratorAwareness:
    def __init__(self, ctx: dict[str, Any] | None = None) -> None:
        self._ctx = ctx or {
            "active_project": "CreatorOS",
            "active_repo": "creator-os",
            "active_directory": "/opt/creator-os",
            "active_panel": "editor",
            "active_projection": "creatoros",
            "active_files": ["src/auth.ts", "src/clerk.ts"],
            "documents": [{"id": "doc-auth", "title": "Auth Architecture"}],
            "decisions": [{"id": "dec-clerk", "title": "Use Clerk for auth"}],
        }

    def context(self) -> MagicMock:
        m = MagicMock()
        m.to_dict.return_value = self._ctx
        return m


class _FakeOrganismState:
    def __init__(self, mode: str = "idle", degraded: bool = False) -> None:
        self._mode = mode
        self._degraded = degraded

    def mode(self) -> MagicMock:
        m = MagicMock()
        m.value = self._mode
        return m

    def is_degraded(self) -> bool:
        return self._degraded


class _FakeGovernedExecution:
    def __init__(self, state: str = "idle") -> None:
        self._state = state

    def state(self) -> MagicMock:
        m = MagicMock()
        m.value = self._state
        return m


class _FakeContextResolution:
    def __init__(self) -> None:
        pass

    def resolve(self, text: str) -> MagicMock:
        m = MagicMock()
        m.to_dict.return_value = {
            "project_name": "CreatorOS",
            "repository_name": "creator-os",
            "projection": "creatoros",
            "files": [{"path": "src/auth.ts"}, {"path": "src/clerk.ts"}],
            "goals": [{"id": "g-auth", "title": "Implement auth"}],
            "decisions": [{"id": "dec-clerk"}],
            "constraints": [{"id": "c-1", "description": "Must use Clerk"}],
            "query": text,
        }
        return m


class _FakeWorkspaceAwareness:
    def __init__(self) -> None:
        pass

    def snapshot(self) -> dict[str, Any]:
        return {"repo": "creator-os", "branch": "main", "directory": "/opt/creator-os"}


class _FakeDeviceAwareness:
    def __init__(self, device: str = "srv1500858") -> None:
        self._device = device

    def detect_active_device(self) -> str:
        return self._device


class _FakeApprovals:
    def __init__(self, pending_count: int = 0, decisions: list[dict] | None = None) -> None:
        self._pending = [{"approval_id": f"a-{i}", "description": f"Approval {i}"} for i in range(pending_count)]
        self._decisions = decisions or []

    def pending(self) -> list[dict]:
        return self._pending

    def recent_decisions(self, limit: int = 1) -> list[dict]:
        return self._decisions[:limit]


class _FakeDelegation:
    def __init__(self, delegatable: int = 0) -> None:
        self._delegatable = delegatable

    def snapshot(self) -> MagicMock:
        m = MagicMock()
        m.to_dict.return_value = {
            "total_assessed": 10,
            "delegatable_count": self._delegatable,
            "delegations": [{"id": f"d-{i}"} for i in range(self._delegatable)],
        }
        return m


class _FakeMetaIdeLoop:
    def __init__(self, requests: list[dict] | None = None) -> None:
        self._requests = requests or []

    def active_requests(self) -> list[dict]:
        return self._requests


class _FakeContinuityEngine:
    def state(self) -> MagicMock:
        m = MagicMock()
        m.value = "active"
        return m

    def checkpoints(self) -> list[dict]:
        return [{"id": "cp-1"}]


class _FakeDevicePresence:
    def active_sessions(self) -> list[dict]:
        return [{"session_id": "s-1", "device_id": "srv1500858"}]


# ── Test 1: Right Rail Clarification ─────────────────────────────────


class TestRightRailClarification:
    def test_operator_intent_produces_resolved_context(self) -> None:
        """Operator gives work intent → system explains understanding → no execution."""
        opr = OrchestratorPresenceRuntime(
            orchestrator_awareness=_FakeOrchestratorAwareness(),
            organism_state=_FakeOrganismState(),
            governed_execution=_FakeGovernedExecution(),
            context_resolution=_FakeContextResolution(),
            workspace_awareness=_FakeWorkspaceAwareness(),
            device_awareness=_FakeDeviceAwareness(),
            unified_approvals=_FakeApprovals(),
            delegation_readiness=_FakeDelegation(),
        )
        result = opr.interpret("Use Clerk for CreatorOS auth")
        assert result["project_name"] == "CreatorOS"
        assert result["repository_name"] == "creator-os"
        assert len(result["files"]) == 2
        assert len(result["goals"]) == 1
        assert opr.mode() == PresenceMode.CLARIFYING


# ── Test 2: Delegation Proposal ──────────────────────────────────────


class TestDelegationProposal:
    def test_delegation_readiness_assessed_after_interpret(self) -> None:
        """Operator confirms → delegation proposal created → approval required."""
        opr = OrchestratorPresenceRuntime(
            orchestrator_awareness=_FakeOrchestratorAwareness(),
            organism_state=_FakeOrganismState(),
            governed_execution=_FakeGovernedExecution(),
            context_resolution=_FakeContextResolution(),
            workspace_awareness=_FakeWorkspaceAwareness(),
            device_awareness=_FakeDeviceAwareness(),
            unified_approvals=_FakeApprovals(),
            delegation_readiness=_FakeDelegation(delegatable=3),
        )
        opr.interpret("Use Clerk for CreatorOS auth")
        delegations = opr.active_delegations()
        assert len(delegations) == 3


# ── Test 3: Top HUD Approval ─────────────────────────────────────────


class TestTopHUDApproval:
    def test_approvals_surface_through_presence(self) -> None:
        """Pending approvals appear via UnifiedApprovalRuntime — not in Right Rail."""
        opr = OrchestratorPresenceRuntime(
            orchestrator_awareness=_FakeOrchestratorAwareness(),
            organism_state=_FakeOrganismState(),
            governed_execution=_FakeGovernedExecution(),
            context_resolution=_FakeContextResolution(),
            workspace_awareness=_FakeWorkspaceAwareness(),
            device_awareness=_FakeDeviceAwareness(),
            unified_approvals=_FakeApprovals(pending_count=2),
            delegation_readiness=_FakeDelegation(),
        )
        approvals = opr.pending_approvals()
        assert len(approvals) == 2
        assert opr.mode() == PresenceMode.WAITING_APPROVAL


# ── Test 4: Meta IDE Context Binding ─────────────────────────────────


class TestMetaIDEContextBinding:
    def test_intent_resolves_full_context(self) -> None:
        """Intent references project → context resolves repo/device/files/docs/goals."""
        mic = MetaIdeContextRuntime(
            context_resolution=_FakeContextResolution(),
            workspace_awareness=_FakeWorkspaceAwareness(),
            device_awareness=_FakeDeviceAwareness(),
            meta_ide_loop=_FakeMetaIdeLoop(),
            orchestrator_awareness=_FakeOrchestratorAwareness(),
        )
        result = mic.resolve_intent("Use Clerk for CreatorOS auth")
        assert result["project_name"] == "CreatorOS"
        assert result["repository_name"] == "creator-os"
        assert len(result["files"]) == 2
        assert len(result["goals"]) == 1
        assert len(result["constraints"]) == 1


# ── Test 5: Full MVP Loop ────────────────────────────────────────────


class TestFullMVPLoop:
    def test_full_operator_loop(self) -> None:
        """
        Right Rail intent → Delegation → Governance → Approval →
        Execution state → Lifecycle visibility.
        """
        opr = OrchestratorPresenceRuntime(
            orchestrator_awareness=_FakeOrchestratorAwareness(),
            organism_state=_FakeOrganismState(),
            governed_execution=_FakeGovernedExecution(state="governed"),
            context_resolution=_FakeContextResolution(),
            workspace_awareness=_FakeWorkspaceAwareness(),
            device_awareness=_FakeDeviceAwareness(),
            unified_approvals=_FakeApprovals(pending_count=1),
            delegation_readiness=_FakeDelegation(delegatable=2),
        )

        # Step 1: Interpret intent
        resolved = opr.interpret("Use Clerk for CreatorOS auth")
        assert "CreatorOS" in resolved["project_name"]

        # Step 2: Check delegations exist
        delegations = opr.active_delegations()
        assert len(delegations) == 2

        # Step 3: Verify governance state
        snap = opr.snapshot()
        assert snap.execution_state == "governed"
        assert snap.pending_approval_count == 1

        # Step 4: Workstation presence tracks context
        wpr = WorkstationPresenceRuntime(
            device_awareness=_FakeDeviceAwareness(),
            workspace_awareness=_FakeWorkspaceAwareness(),
            continuity_engine=_FakeContinuityEngine(),
            unified_approvals=_FakeApprovals(
                decisions=[{"approval_id": "a-0", "action": "approved"}]
            ),
            device_presence=_FakeDevicePresence(),
        )
        wpr.update_panel("commandcenter")
        wpr.update_context({"project": "CreatorOS", "repo": "creator-os"})
        ws_snap = wpr.snapshot()
        assert ws_snap.active_project == "CreatorOS"
        assert ws_snap.active_panel == "commandcenter"

        # Step 5: Meta IDE resolves the same context
        mic = MetaIdeContextRuntime(
            context_resolution=_FakeContextResolution(),
            workspace_awareness=_FakeWorkspaceAwareness(),
            device_awareness=_FakeDeviceAwareness(),
            meta_ide_loop=_FakeMetaIdeLoop([
                {"request_id": "r-1", "status": "pending"}
            ]),
            orchestrator_awareness=_FakeOrchestratorAwareness(),
        )
        ide_ctx = mic.context()
        assert ide_ctx.projection == "creatoros"
        assert len(ide_ctx.active_requests) == 1


# ── Test 6: No Direct Execution (Invariant) ─────────────────────────


class TestNoDirectExecution:
    """Right Rail = communication only. No execute/approve/reject methods."""

    def test_presence_runtime_has_no_execute_method(self) -> None:
        opr = OrchestratorPresenceRuntime(
            orchestrator_awareness=_FakeOrchestratorAwareness(),
            organism_state=_FakeOrganismState(),
            governed_execution=_FakeGovernedExecution(),
            context_resolution=_FakeContextResolution(),
            workspace_awareness=_FakeWorkspaceAwareness(),
            device_awareness=_FakeDeviceAwareness(),
            unified_approvals=_FakeApprovals(),
            delegation_readiness=_FakeDelegation(),
        )
        assert not hasattr(opr, "execute")
        assert not hasattr(opr, "approve")
        assert not hasattr(opr, "reject")
        assert not hasattr(opr, "run")
        assert not hasattr(opr, "dispatch")

    def test_meta_ide_context_has_no_mutation_methods(self) -> None:
        mic = MetaIdeContextRuntime(
            context_resolution=_FakeContextResolution(),
            workspace_awareness=_FakeWorkspaceAwareness(),
            device_awareness=_FakeDeviceAwareness(),
            meta_ide_loop=_FakeMetaIdeLoop(),
            orchestrator_awareness=_FakeOrchestratorAwareness(),
        )
        assert not hasattr(mic, "execute")
        assert not hasattr(mic, "approve")
        assert not hasattr(mic, "reject")
        assert not hasattr(mic, "submit")
        assert not hasattr(mic, "dispatch")

    def test_interpret_returns_data_not_action(self) -> None:
        """interpret() returns resolved context dict — never triggers execution."""
        opr = OrchestratorPresenceRuntime(
            orchestrator_awareness=_FakeOrchestratorAwareness(),
            organism_state=_FakeOrganismState(),
            governed_execution=_FakeGovernedExecution(),
            context_resolution=_FakeContextResolution(),
            workspace_awareness=_FakeWorkspaceAwareness(),
            device_awareness=_FakeDeviceAwareness(),
            unified_approvals=_FakeApprovals(),
            delegation_readiness=_FakeDelegation(),
        )
        result = opr.interpret("deploy the app")
        assert isinstance(result, dict)
        assert "execute" not in result
        assert "action" not in result
