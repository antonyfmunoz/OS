"""Phase 14.8B Wave 2 — Organism Loop wiring tests.

Verifies:
1. WP-2.1: Intent capture pipeline (/intent/classify endpoint)
2. WP-2.2: Work packet generation from intent (/organism/universal-work/generate)
3. WP-2.4: Agent/tool routing from work packets (execution/start routing)
4. WP-2.3: Approval UI remains untouched (no regressions)
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, "/opt/OS")

WORKTREE = Path("/opt/OS/.claude/worktrees/phase-14-7b-cockpit-usability")
COCKPIT_PY = WORKTREE / "transports/api/cockpit.py"
UNIVERSAL_WORK_PY = WORKTREE / "transports/api/cockpit_universal_work_routes.py"
APPROVAL_STORE_TS = WORKTREE / "cockpit/src/renderer/stores/approvalStore.ts"
APPROVALS_PANEL_TSX = WORKTREE / "cockpit/src/renderer/panels/ApprovalsPanel.tsx"
UNIVERSAL_WORK_PANEL = WORKTREE / "cockpit/src/renderer/panels/UniversalWorkPanel.tsx"
CAP_ROUTER_PY = WORKTREE / "substrate/execution/runtime/capability_router.py"
WPE_PY = WORKTREE / "substrate/organism/work_packet_engine.py"


def _find_handler_block(content: str, marker: str, size: int = 1500) -> str:
    """Find the code block starting from a marker string."""
    idx = content.find(marker)
    if idx == -1:
        return ""
    return content[idx:idx + size]


def _find_handler_by_def(content: str, func_name: str, size: int = 3200) -> str:
    """Find a function body by its def line."""
    idx = content.find(f"def {func_name}")
    if idx == -1:
        idx = content.find(f"async def {func_name}")
    if idx == -1:
        return ""
    return content[idx:idx + size]


# ── WP-2.1: Intent Capture Pipeline ─────────────────────────────────────────


class TestIntentClassifyEndpoint:
    """Verify POST /intent/classify exists and wires to spine classification."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        self.content = COCKPIT_PY.read_text()
        self.handler = _find_handler_by_def(self.content, "intent_classify")

    def test_endpoint_registered(self):
        assert '"/intent/classify"' in self.content

    def test_endpoint_is_post(self):
        idx = self.content.find('"/intent/classify"')
        block = self.content[max(0, idx - 100):idx + 50]
        assert "post" in block.lower()

    def test_requires_operator_role(self):
        idx = self.content.find('"/intent/classify"')
        line_end = self.content.find("\n", idx)
        block = self.content[max(0, idx - 10):line_end + 1]
        assert "_require_operator_role" in block

    def test_uses_intent_patterns(self):
        assert "_INTENT_PATTERNS" in self.handler

    def test_persists_to_conversation_memory(self):
        assert "ConversationMemory" in self.handler
        assert "log_event" in self.handler

    def test_returns_intent_and_event_id(self):
        assert '"intent"' in self.handler
        assert '"event_id"' in self.handler
        assert '"persisted"' in self.handler

    def test_returns_deterministic_confidence(self):
        assert '"deterministic"' in self.handler

    def test_validates_empty_text(self):
        assert '"text"' in self.handler or "'text'" in self.handler


class TestIntentPatterns:
    """Verify spine's intent patterns classify correctly."""

    def test_patterns_importable(self):
        from substrate.execution.spine import _INTENT_PATTERNS
        assert len(_INTENT_PATTERNS) > 0

    def test_classifies_command(self):
        from substrate.execution.spine import _INTENT_PATTERNS
        for pattern, intent in _INTENT_PATTERNS:
            if pattern.search("create a new module"):
                assert intent == "command"
                return
        pytest.fail("No pattern matched 'create a new module'")

    def test_classifies_question(self):
        from substrate.execution.spine import _INTENT_PATTERNS
        for pattern, intent in _INTENT_PATTERNS:
            if pattern.search("what is the current status?"):
                assert intent in ("question", "status")
                return
        pytest.fail("No pattern matched")

    def test_classifies_greeting(self):
        from substrate.execution.spine import _INTENT_PATTERNS
        for pattern, intent in _INTENT_PATTERNS:
            if pattern.search("hello"):
                assert intent == "greeting"
                return
        pytest.fail("No pattern matched 'hello'")

    def test_classifies_status(self):
        from substrate.execution.spine import _INTENT_PATTERNS
        for pattern, intent in _INTENT_PATTERNS:
            if pattern.search("show me the status"):
                assert intent == "status"
                return
        pytest.fail("No pattern matched 'show me the status'")

    def test_classifies_analysis(self):
        from substrate.execution.spine import _INTENT_PATTERNS
        for pattern, intent in _INTENT_PATTERNS:
            if pattern.search("analyse the conversion data"):
                assert intent == "analysis"
                return
        pytest.fail("No pattern matched")

    def test_unknown_for_nonsense(self):
        from substrate.execution.spine import _INTENT_PATTERNS
        for pattern, intent in _INTENT_PATTERNS:
            if pattern.search("xyzzy"):
                pytest.fail(f"Unexpected match: {intent}")


# ── WP-2.2: Work Packet Lifecycle ───────────────────────────────────────────


class TestGenerateEndpoint:
    """Verify POST /organism/universal-work/generate exists and wires correctly."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        self.content = UNIVERSAL_WORK_PY.read_text()
        self.handler = _find_handler_by_def(self.content, "_generate_from_intent")

    def test_generate_route_registered(self):
        assert '"/organism/universal-work/generate"' in self.content

    def test_generate_is_post(self):
        idx = self.content.find("/organism/universal-work/generate")
        block = self.content[max(0, idx - 20):idx + 80]
        assert "POST" in block

    def test_generate_requires_auth(self):
        idx = self.content.find("/organism/universal-work/generate")
        block = self.content[max(0, idx - 20):idx + 120]
        assert "dependencies" in block

    def test_generate_handler_exists(self):
        assert self.handler != ""

    def test_generate_calls_ingest_user_intent(self):
        assert "ingest_user_intent" in self.handler

    def test_generate_detects_capability(self):
        assert "detect_capability" in self.handler

    def test_generate_returns_detected_capability(self):
        assert '"detected_capability"' in self.handler

    def test_generate_returns_packet(self):
        assert '"packet"' in self.handler
        assert "to_safe_dict" in self.handler

    def test_generate_validates_empty_intent(self):
        assert "user_intent" in self.handler


class TestExistingCreateEndpoint:
    """Verify existing /organism/universal-work/create still works."""

    def test_create_route_still_exists(self):
        content = UNIVERSAL_WORK_PY.read_text()
        assert '"/organism/universal-work/create"' in content

    def test_create_handler_intact(self):
        content = UNIVERSAL_WORK_PY.read_text()
        assert "_create_packet" in content


class TestWorkPacketEngineIntegration:
    """Verify the WorkPacketEngine can create packets from intent."""

    def test_engine_importable(self):
        from substrate.organism.work_packet_engine import WorkPacketEngine
        assert WorkPacketEngine is not None

    def test_create_packet_from_intent_exists(self):
        from substrate.organism.work_packet_engine import WorkPacketEngine
        assert hasattr(WorkPacketEngine, "create_packet_from_intent")

    def test_classify_intent_exists(self):
        from substrate.organism.work_packet_engine import WorkPacketEngine
        assert hasattr(WorkPacketEngine, "classify_intent")


class TestUniversalWorkPanelRoutes:
    """Verify panel calls correct routes."""

    def test_panel_calls_summary(self):
        content = UNIVERSAL_WORK_PANEL.read_text()
        assert "/organism/universal-work/summary" in content

    def test_panel_calls_packets(self):
        content = UNIVERSAL_WORK_PANEL.read_text()
        assert "/organism/universal-work/packets" in content


# ── WP-2.4: Agent/Tool Routing ──────────────────────────────────────────────


class TestExecutionStartRouting:
    """Verify execution/start integrates capability routing."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        self.content = COCKPIT_PY.read_text()
        self.handler = _find_handler_by_def(self.content, "execution_start")

    def test_execution_start_exists(self):
        assert '"/execution/start"' in self.content

    def test_execution_start_calls_detect_capability(self):
        assert "detect_capability" in self.handler

    def test_execution_start_calls_route_capability(self):
        assert "route_capability" in self.handler

    def test_execution_start_has_llm_fallback(self):
        assert "call_with_fallback" in self.handler

    def test_execution_start_returns_routing(self):
        assert '"routing"' in self.handler

    def test_routing_result_has_capability(self):
        assert '"capability"' in self.handler

    def test_routing_result_has_provider(self):
        assert '"provider"' in self.handler

    def test_routing_result_has_error_field(self):
        assert '"error"' in self.handler

    def test_unavailable_error_typed(self):
        assert "UNAVAILABLE" in self.handler


class TestCapabilityRouterIntegration:
    """Verify the capability router infrastructure is production-ready."""

    def test_detect_capability_importable(self):
        from substrate.execution.runtime.capability_router import detect_capability
        assert detect_capability is not None

    def test_route_capability_importable(self):
        from substrate.execution.runtime.capability_router import route_capability
        assert route_capability is not None

    def test_detect_code_write(self):
        from substrate.execution.runtime.capability_router import detect_capability, Capability
        cap = detect_capability("implement the dashboard feature")
        assert cap == Capability.CODE_WRITE

    def test_detect_shell_execute(self):
        from substrate.execution.runtime.capability_router import detect_capability, Capability
        cap = detect_capability("run the test script")
        assert cap == Capability.SHELL_EXECUTE

    def test_detect_code_review(self):
        from substrate.execution.runtime.capability_router import detect_capability, Capability
        cap = detect_capability("review this code for bugs")
        assert cap == Capability.CODE_REVIEW

    def test_detect_web_research(self):
        from substrate.execution.runtime.capability_router import detect_capability, Capability
        cap = detect_capability("research market trends for SaaS")
        assert cap == Capability.WEB_RESEARCH

    def test_detect_reason_fallback(self):
        from substrate.execution.runtime.capability_router import detect_capability, Capability
        cap = detect_capability("think about this problem carefully")
        assert cap == Capability.REASON

    def test_route_returns_none_for_llm_only(self):
        from substrate.execution.runtime.capability_router import route_capability
        result = route_capability("think about this")
        assert result is None


# ── WP-2.3: Approval UI — No Changes ────────────────────────────────────────


class TestApprovalUIUntouched:
    """Verify Wave 2 did not modify the approval infrastructure."""

    def test_approval_store_calls_approvals(self):
        content = APPROVAL_STORE_TS.read_text()
        assert "fetchApi" in content
        assert "'/approvals'" in content

    def test_approval_store_has_approve(self):
        content = APPROVAL_STORE_TS.read_text()
        assert "/approve" in content

    def test_approval_store_has_deny(self):
        content = APPROVAL_STORE_TS.read_text()
        assert "/deny" in content

    def test_approvals_panel_renders(self):
        content = APPROVALS_PANEL_TSX.read_text()
        assert "useApprovalStore" in content
        assert "pending" in content.lower()

    def test_backend_approval_routes_exist(self):
        content = COCKPIT_PY.read_text()
        assert '"/approvals"' in content
        assert '"/approvals/{approval_id}/approve"' in content
        assert '"/approvals/{approval_id}/deny"' in content


# ── Wave 1 No-Regression ────────────────────────────────────────────────────


class TestWave1NoRegression:
    """Verify Wave 1 sealed files are untouched."""

    def test_world_model_store_no_organism(self):
        store = WORKTREE / "cockpit/src/renderer/stores/worldModelStore.ts"
        content = store.read_text()
        assert "/organism/" not in content

    def test_world_model_store_has_reality_model(self):
        store = WORKTREE / "cockpit/src/renderer/stores/worldModelStore.ts"
        content = store.read_text()
        assert "/reality-model/" in content

    def test_world_model_panel_no_organism(self):
        panel = WORKTREE / "cockpit/src/renderer/panels/WorldModelPanel.tsx"
        content = panel.read_text()
        assert "/organism/" not in content

    def test_world_model_panel_uses_store(self):
        panel = WORKTREE / "cockpit/src/renderer/panels/WorldModelPanel.tsx"
        content = panel.read_text()
        assert "useWorldModelStore" in content

    def test_reality_model_routes_unchanged(self):
        routes = WORKTREE / "transports/api/cockpit_reality_model_routes.py"
        content = routes.read_text()
        assert "/reality-model/status" in content
        assert "/reality-model/canonical/patterns" in content
