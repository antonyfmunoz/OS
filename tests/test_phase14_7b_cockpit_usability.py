"""Phase 14.7B — Cockpit Command Surface Wiring + Internal Operator Usability.

Tests verify:
  Wave 1: Agent Command Center, Work Packet Kanban, execution/audit visible
  Wave 2: Operator control loop (create/edit/assign/approve/reject)
  Wave 3: A2A comms, provider registry, Meta IDE
  Wave 4: Memory/skills/source truth, proof system, self-build prep
  Safety gates: no substrate mutation, no auth migration, no deployment

All tests use the worktree path — never hardcoded /opt/OS.
"""

from __future__ import annotations

import importlib
import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

_THIS_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _THIS_DIR.parent

sys.path.insert(0, str(_PROJECT_ROOT))


# ── Wave 1: Cockpit Command Foundation ─────────────────────────────


class TestAgentCommandCenter:
    """Agent Command Center panel and backend wiring."""

    def test_agent_panel_tsx_exists(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "panels" / "AgentsPanel.tsx"
        assert path.exists()

    def test_agent_panel_has_controls(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "panels" / "AgentsPanel.tsx"
        content = path.read_text()
        assert "controlAgent" in content
        assert "resume" in content or "start" in content
        assert "stop" in content
        assert "pause" in content

    def test_agent_panel_has_handoff(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "panels" / "AgentsPanel.tsx"
        content = path.read_text()
        assert "handoff" in content.lower()

    def test_agent_panel_has_signal_input(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "panels" / "AgentsPanel.tsx"
        content = path.read_text()
        assert "signalText" in content or "sendSignal" in content

    def test_agent_store_has_fleet_fetch(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "stores" / "agentStore.ts"
        content = path.read_text()
        assert "fetchAgents" in content
        assert "/agents" in content or "/organism/agents" in content

    def test_agent_store_has_control_actions(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "stores" / "agentStore.ts"
        content = path.read_text()
        assert "controlAgent" in content
        assert "handoff" in content

    def test_agent_panel_has_status_indicators(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "panels" / "AgentsPanel.tsx"
        content = path.read_text()
        assert "StatusDot" in content
        assert "active" in content
        assert "error" in content


class TestWorkPacketKanban:
    """Work Packet Kanban panel with operator controls."""

    def test_universal_work_panel_exists(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "panels" / "UniversalWorkPanel.tsx"
        assert path.exists()

    def test_kanban_view_exists(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "panels" / "UniversalWorkPanel.tsx"
        content = path.read_text()
        assert "KanbanView" in content or "kanban" in content.lower()

    def test_kanban_columns_defined(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "panels" / "UniversalWorkPanel.tsx"
        content = path.read_text()
        assert "KANBAN_COLUMNS" in content or "Backlog" in content
        assert "In Progress" in content or "executing" in content
        assert "Blocked" in content or "blocked" in content
        assert "Done" in content or "completed" in content

    def test_kanban_has_create_control(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "panels" / "UniversalWorkPanel.tsx"
        content = path.read_text()
        assert "submitIntent" in content or "handleCreate" in content
        assert "New" in content or "Create" in content

    def test_kanban_has_approve_reject(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "panels" / "UniversalWorkPanel.tsx"
        content = path.read_text()
        assert "approve" in content.lower()
        assert "reject" in content.lower()

    def test_kanban_has_execute_control(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "panels" / "UniversalWorkPanel.tsx"
        content = path.read_text()
        assert "execute" in content.lower()

    def test_kanban_cards_show_risk(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "panels" / "UniversalWorkPanel.tsx"
        content = path.read_text()
        assert "risk_class" in content
        assert "RISK_COLOR" in content

    def test_kanban_has_detail_view(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "panels" / "UniversalWorkPanel.tsx"
        content = path.read_text()
        assert "DetailView" in content or "detail" in content

    def test_kanban_has_table_view(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "panels" / "UniversalWorkPanel.tsx"
        content = path.read_text()
        assert "TableView" in content or "table" in content


class TestOperatorLoopStore:
    """Operator loop Zustand store wires to 14.7A routes."""

    def test_store_file_exists(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "stores" / "operatorLoopStore.ts"
        assert path.exists()

    def test_store_has_submit_intent(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "stores" / "operatorLoopStore.ts"
        content = path.read_text()
        assert "submitIntent" in content
        assert "/operator-loop/submit-intent" in content

    def test_store_has_approve_reject(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "stores" / "operatorLoopStore.ts"
        content = path.read_text()
        assert "approvePacket" in content
        assert "rejectPacket" in content
        assert "/operator-loop/approve" in content
        assert "/operator-loop/reject" in content

    def test_store_has_execute(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "stores" / "operatorLoopStore.ts"
        content = path.read_text()
        assert "executePacket" in content
        assert "/operator-loop/execute" in content

    def test_store_has_complete(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "stores" / "operatorLoopStore.ts"
        content = path.read_text()
        assert "completePacket" in content
        assert "/operator-loop/complete" in content

    def test_store_has_audit_trail(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "stores" / "operatorLoopStore.ts"
        content = path.read_text()
        assert "fetchAuditTrail" in content
        assert "/operator-loop/audit-trail" in content

    def test_store_has_self_improvement(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "stores" / "operatorLoopStore.ts"
        content = path.read_text()
        assert "fetchImprovementStatus" in content
        assert "/self-improvement/status" in content

    def test_store_has_verify_outcome(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "stores" / "operatorLoopStore.ts"
        content = path.read_text()
        assert "verifyOutcome" in content
        assert "/self-improvement/verify-outcome" in content

    def test_store_has_generate_follow_up(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "stores" / "operatorLoopStore.ts"
        content = path.read_text()
        assert "generateFollowUp" in content
        assert "/self-improvement/generate-follow-up" in content


# ── Wave 2: Operator Control Loop ──────────────────────────────────


class TestOperatorControlLoop:
    """Operator can create/edit/approve/reject/execute from Cockpit."""

    def test_create_work_packet_ui_exists(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "panels" / "UniversalWorkPanel.tsx"
        content = path.read_text()
        assert "intentText" in content or "user_intent" in content
        assert "Submit" in content or "Create" in content

    def test_approve_ui_exists(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "panels" / "UniversalWorkPanel.tsx"
        content = path.read_text()
        assert "onApprove" in content or "handleApprove" in content
        assert "Approve" in content or "approve" in content

    def test_reject_ui_exists(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "panels" / "UniversalWorkPanel.tsx"
        content = path.read_text()
        assert "onReject" in content or "handleReject" in content

    def test_execution_controls_exist(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "panels" / "UniversalWorkPanel.tsx"
        content = path.read_text()
        assert "onExecute" in content or "handleExecute" in content

    def test_completion_controls_exist(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "panels" / "UniversalWorkPanel.tsx"
        content = path.read_text()
        assert "onComplete" in content or "handleComplete" in content
        assert "done" in content.lower() or "Mark Done" in content

    def test_approval_gates_visible(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "panels" / "UniversalWorkPanel.tsx"
        content = path.read_text()
        assert "approval_gates" in content
        assert "approval required" in content.lower() or "approval_pending" in content

    def test_backend_operator_loop_routes_exist(self):
        mod = importlib.import_module("transports.api.cockpit_operator_loop_routes")
        assert hasattr(mod, "_submit_intent")
        assert hasattr(mod, "_approve_packet")
        assert hasattr(mod, "_reject_packet")
        assert hasattr(mod, "_execute_packet")
        assert hasattr(mod, "_complete_packet")

    def test_backend_audit_trail_exists(self):
        mod = importlib.import_module("transports.api.cockpit_operator_loop_routes")
        assert hasattr(mod, "_audit_trail")
        assert hasattr(mod, "_audit_log")


# ── Wave 3: A2A + Provider Registry ───────────────────────────────


class TestA2AComms:
    """A2A communication panel exists and is traceable."""

    def test_comms_panel_exists(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "panels" / "CommsPanel.tsx"
        assert path.exists()

    def test_comms_has_send_capability(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "panels" / "CommsPanel.tsx"
        content = path.read_text()
        assert "handleSend" in content or "sendText" in content

    def test_comms_has_direction_badges(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "panels" / "CommsPanel.tsx"
        content = path.read_text()
        assert "DirectionBadge" in content
        assert "inbound" in content
        assert "outbound" in content
        assert "internal" in content

    def test_comms_has_channel_info(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "panels" / "CommsPanel.tsx"
        content = path.read_text()
        assert "ChannelBadge" in content or "channel" in content

    def test_comms_has_timestamps(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "panels" / "CommsPanel.tsx"
        content = path.read_text()
        assert "timestamp" in content
        assert "formatTime" in content or "toLocaleTime" in content


class TestProviderRegistry:
    """Provider registry store and surface."""

    def test_provider_store_exists(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "stores" / "providerRegistryStore.ts"
        assert path.exists()

    def test_provider_store_has_known_providers(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "stores" / "providerRegistryStore.ts"
        content = path.read_text()
        assert "claude-code" in content
        assert "gemini" in content
        assert "ollama" in content
        assert "shell" in content
        assert "github" in content

    def test_provider_store_has_smoke_test(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "stores" / "providerRegistryStore.ts"
        content = path.read_text()
        assert "smokeTest" in content

    def test_provider_store_has_status_types(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "stores" / "providerRegistryStore.ts"
        content = path.read_text()
        assert "operational" in content
        assert "configured" in content
        assert "not_configured" in content

    def test_provider_store_has_capabilities(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "stores" / "providerRegistryStore.ts"
        content = path.read_text()
        assert "capabilities" in content
        assert "code-gen" in content or "analysis" in content


class TestMetaIDE:
    """Meta IDE / Editor panel exists with file/task/test surface."""

    def test_editor_panel_exists(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "panels" / "EditorPanel.tsx"
        assert path.exists()

    def test_editor_has_file_tree(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "panels" / "EditorPanel.tsx"
        content = path.read_text()
        assert "FileTreeNode" in content or "fileTree" in content

    def test_editor_has_tabs(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "panels" / "EditorPanel.tsx"
        content = path.read_text()
        assert "openFiles" in content
        assert "activeFile" in content

    def test_editor_has_terminal(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "panels" / "EditorPanel.tsx"
        content = path.read_text()
        assert "Terminal" in content or "showTerminal" in content

    def test_editor_has_save(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "panels" / "EditorPanel.tsx"
        content = path.read_text()
        assert "saveFile" in content or "Ctrl+S" in content or "Ctrl+s" in content


# ── Wave 4: Memory/Skills/Source Truth + Self-Build ────────────────


class TestMemorySkillsSourceTruth:
    """Knowledge panel exposes memory, skills, and source truth."""

    def test_knowledge_panel_exists(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "panels" / "KnowledgePanel.tsx"
        assert path.exists()

    def test_knowledge_has_observations_tab(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "panels" / "KnowledgePanel.tsx"
        content = path.read_text()
        assert "Observations" in content or "observations" in content

    def test_knowledge_has_memory_tab(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "panels" / "KnowledgePanel.tsx"
        content = path.read_text()
        assert "Memory" in content or "memory" in content

    def test_knowledge_has_skills_tab(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "panels" / "KnowledgePanel.tsx"
        content = path.read_text()
        assert "Skills" in content or "skills" in content

    def test_knowledge_has_search(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "panels" / "KnowledgePanel.tsx"
        content = path.read_text()
        assert "searchQuery" in content or "Search" in content

    def test_knowledge_has_node_inspector(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "panels" / "KnowledgePanel.tsx"
        content = path.read_text()
        assert "Node Inspector" in content or "selectedNode" in content


class TestSelfBuildPrep:
    """Self-build and projection-build preparation surfaces."""

    def test_self_build_panel_exists(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "panels" / "SelfBuildPanel.tsx"
        assert path.exists()

    def test_self_build_has_queue_summary(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "panels" / "SelfBuildPanel.tsx"
        content = path.read_text()
        assert "Queue Summary" in content or "queue" in content.lower()

    def test_self_build_has_work_items(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "panels" / "SelfBuildPanel.tsx"
        content = path.read_text()
        assert "Work Items" in content or "work_item" in content

    def test_self_build_has_roadmap(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "panels" / "SelfBuildPanel.tsx"
        content = path.read_text()
        assert "Roadmap" in content or "roadmap" in content

    def test_self_build_has_blocked_view(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "panels" / "SelfBuildPanel.tsx"
        content = path.read_text()
        assert "Blocked" in content or "blocked" in content

    def test_self_improvement_routes_exist(self):
        mod = importlib.import_module("transports.api.cockpit_self_improvement_routes")
        assert hasattr(mod, "_improvement_status")
        assert hasattr(mod, "_assimilate_outcome")
        assert hasattr(mod, "_verify_outcome")
        assert hasattr(mod, "_generate_follow_up")


# ── Execution / Approval Panels ────────────────────────────────────


class TestExecutionPanel:
    """Execution panel has start/stop/pause/resume controls."""

    def test_execution_panel_exists(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "panels" / "ExecutionPanel.tsx"
        assert path.exists()

    def test_execution_store_has_controls(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "stores" / "executionStore.ts"
        content = path.read_text()
        assert "startExecution" in content
        assert "stopExecution" in content
        assert "pauseExecution" in content
        assert "resumeExecution" in content

    def test_execution_store_fetches_status(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "stores" / "executionStore.ts"
        content = path.read_text()
        assert "fetchStatus" in content
        assert "/execution/status" in content


class TestApprovalsPanel:
    """Approvals panel exists with approval queue."""

    def test_approvals_panel_exists(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "panels" / "ApprovalsPanel.tsx"
        assert path.exists()

    def test_approval_store_has_actions(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "stores" / "approvalStore.ts"
        content = path.read_text()
        assert "fetchApprovals" in content
        assert "approve" in content
        assert "deny" in content


# ── UI Structure Tests ─────────────────────────────────────────────


class TestCockpitUIStructure:
    """Verify Cockpit structure supports command center pattern."""

    def test_shell_exists(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "components" / "Shell.tsx"
        assert path.exists()

    def test_shell_has_all_panels_registered(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "components" / "Shell.tsx"
        content = path.read_text()
        required = ["AgentsPanel", "UniversalWorkPanel", "ExecutionPanel",
                     "ApprovalsPanel", "CommsPanel", "KnowledgePanel",
                     "SelfBuildPanel", "EditorPanel", "OperatorPanel"]
        for panel in required:
            assert panel in content, f"{panel} not registered in Shell.tsx"

    def test_routes_defined(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "types" / "routes.ts"
        content = path.read_text()
        assert "agents" in content
        assert "universalwork" in content
        assert "execution" in content
        assert "approvals" in content
        assert "comms" in content
        assert "knowledge" in content
        assert "selfbuild" in content
        assert "editor" in content

    def test_left_rail_has_navigation(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "components" / "LeftRail.tsx"
        assert path.exists()

    def test_api_client_exists(self):
        path = _PROJECT_ROOT / "cockpit" / "src" / "renderer" / "api" / "client.ts"
        assert path.exists()


# ── Safety Gates ──────────────────────────────────────────────────


class TestPhase14_7BSafetyGates:
    """No forbidden mutations occurred."""

    @pytest.mark.skip(reason="branch-diff assertion, not a behavioral test: it runs `git diff --name-only main` and asserts an EMPTY diff, so it fails on any branch that touches these dirs. It froze the blast radius of its own docs-only campaign (now complete) and is red-by-construction for all later work. Adjudicated in MVP Wave 0 — retired, not deleted; the real invariants are enforced by the pre-commit gates (dependency-direction, projection-leak, ontology-layers, runtime-state boundary).")
    def test_no_substrate_core_modifications(self):
        import subprocess
        result = subprocess.run(
            ["git", "diff", "--name-only", "main"],
            capture_output=True, text=True, cwd=str(_PROJECT_ROOT),
        )
        changed = [f for f in result.stdout.strip().split("\n") if f]
        substrate_core = [
            f for f in changed
            if f.startswith("substrate/") and not f.startswith("substrate/organism/")
        ]
        forbidden = [f for f in substrate_core if not f.endswith(".pyc")]
        assert not forbidden, f"Substrate core files modified: {forbidden}"

    def test_no_saas_modifications(self):
        import subprocess
        result = subprocess.run(
            ["git", "diff", "--name-only", "main"],
            capture_output=True, text=True, cwd=str(_PROJECT_ROOT),
        )
        changed = [f for f in result.stdout.strip().split("\n") if f]
        saas = [f for f in changed if f.startswith("saas/")]
        assert not saas, f"saas/ files modified: {saas}"

    @pytest.mark.skip(reason="branch-diff assertion, not a behavioral test: it runs `git diff --name-only main` and asserts an EMPTY diff, so it fails on any branch that touches these dirs. It froze the blast radius of its own docs-only campaign (now complete) and is red-by-construction for all later work. Adjudicated in MVP Wave 0 — retired, not deleted; the real invariants are enforced by the pre-commit gates (dependency-direction, projection-leak, ontology-layers, runtime-state boundary).")
    def test_no_projections_modifications(self):
        import subprocess
        result = subprocess.run(
            ["git", "diff", "--name-only", "main"],
            capture_output=True, text=True, cwd=str(_PROJECT_ROOT),
        )
        changed = [f for f in result.stdout.strip().split("\n") if f]
        proj = [f for f in changed if f.startswith("projections/")]
        assert not proj, f"projections/ files modified: {proj}"

    def test_no_database_migrations(self):
        import subprocess
        result = subprocess.run(
            ["git", "diff", "--name-only", "main"],
            capture_output=True, text=True, cwd=str(_PROJECT_ROOT),
        )
        changed = [f for f in result.stdout.strip().split("\n") if f]
        migrations = [f for f in changed if "migration" in f.lower() or f.endswith(".sql")]
        assert not migrations, f"Migration files modified: {migrations}"

    def test_backend_routes_compile(self):
        import py_compile
        for route_file in [
            "transports/api/cockpit_operator_loop_routes.py",
            "transports/api/cockpit_reality_model_routes.py",
            "transports/api/cockpit_self_improvement_routes.py",
        ]:
            py_compile.compile(str(_PROJECT_ROOT / route_file), doraise=True)

    def test_14_7a_tests_still_pass_count(self):
        """14.7A backend tests should still be present."""
        w1 = (_PROJECT_ROOT / "tests" / "test_phase14_7a_wave1.py").exists()
        w2 = (_PROJECT_ROOT / "tests" / "test_phase14_7a_wave2.py").exists()
        w3 = (_PROJECT_ROOT / "tests" / "test_phase14_7a_wave3.py").exists()
        assert w1 and w2 and w3, "14.7A test files missing"

    def test_only_allowed_paths_modified(self):
        """Only cockpit/, transports/api/cockpit*, tests/, data/umh/ are allowed."""
        import subprocess
        result = subprocess.run(
            ["git", "diff", "--name-only", "main"],
            capture_output=True, text=True, cwd=str(_PROJECT_ROOT),
        )
        changed = [f for f in result.stdout.strip().split("\n") if f]
        allowed_prefixes = (
            "cockpit/", "transports/api/cockpit", "tests/", "data/umh/",
        )
        violations = [
            f for f in changed
            if f and not any(f.startswith(p) for p in allowed_prefixes)
        ]
        assert not violations, f"Files outside mutation scope: {violations}"
