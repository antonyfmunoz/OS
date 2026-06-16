"""Phase 25 — Workspace Observation tests.

Tests workspace observation models, engine, probe, routes, and type registration.
~70 tests across 10 test classes.
"""

from __future__ import annotations

import json
import os
import sys
import time
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))


# ── Test Observation Types ──────────────────────────────────────────────────


class TestObservationTypes:
    def test_observation_domain_values(self):
        from substrate.meta_ide.workspace_observation import ObservationDomain

        assert ObservationDomain.TERMINAL == "terminal"
        assert ObservationDomain.CONTAINER == "container"
        assert ObservationDomain.PREVIEW == "preview"
        assert ObservationDomain.REPOSITORY == "repository"
        assert ObservationDomain.ENGINEERING_SESSION == "engineering_session"

    def test_observation_domain_count(self):
        from substrate.meta_ide.workspace_observation import ObservationDomain

        assert len(ObservationDomain) == 5

    def test_process_health_values(self):
        from substrate.meta_ide.workspace_observation import ProcessHealth

        assert ProcessHealth.HEALTHY == "healthy"
        assert ProcessHealth.DEGRADED == "degraded"
        assert ProcessHealth.CRASHED == "crashed"
        assert ProcessHealth.UNKNOWN == "unknown"

    def test_process_health_count(self):
        from substrate.meta_ide.workspace_observation import ProcessHealth

        assert len(ProcessHealth) == 4

    def test_observation_domain_string_conversion(self):
        from substrate.meta_ide.workspace_observation import ObservationDomain

        assert str(ObservationDomain.TERMINAL) == "ObservationDomain.TERMINAL"
        assert ObservationDomain.TERMINAL.value == "terminal"

    def test_process_health_string_conversion(self):
        from substrate.meta_ide.workspace_observation import ProcessHealth

        assert ProcessHealth("healthy") == ProcessHealth.HEALTHY


# ── Test Terminal Observation ───────────────────────────────────────────────


class TestTerminalObservation:
    def test_construction(self):
        from substrate.meta_ide.workspace_observation import TerminalObservation

        t = TerminalObservation(terminal_id="main:bash.0", session_name="main")
        assert t.terminal_id == "main:bash.0"
        assert t.session_name == "main"

    def test_defaults(self):
        from substrate.meta_ide.workspace_observation import TerminalObservation

        t = TerminalObservation(terminal_id="t1")
        assert t.host_id == ""
        assert t.window_name == ""
        assert t.pane_index == 0
        assert t.current_command == ""
        assert t.cwd == ""
        assert t.pid == 0
        assert t.is_active is False
        assert t.last_output_at == 0.0
        assert t.observed_at > 0

    def test_to_dict(self):
        from substrate.meta_ide.workspace_observation import TerminalObservation

        t = TerminalObservation(
            terminal_id="dev:vim.1",
            session_name="dev",
            window_name="vim",
            pane_index=1,
            current_command="vim main.py",
            is_active=True,
        )
        d = t.to_dict()
        assert d["terminal_id"] == "dev:vim.1"
        assert d["session_name"] == "dev"
        assert d["current_command"] == "vim main.py"
        assert d["is_active"] is True

    def test_to_dict_has_all_fields(self):
        from substrate.meta_ide.workspace_observation import TerminalObservation

        t = TerminalObservation(terminal_id="t1")
        d = t.to_dict()
        expected_keys = {
            "terminal_id",
            "host_id",
            "session_name",
            "window_name",
            "pane_index",
            "current_command",
            "cwd",
            "pid",
            "is_active",
            "last_output_at",
            "observed_at",
        }
        assert set(d.keys()) == expected_keys

    def test_with_host_id(self):
        from substrate.meta_ide.workspace_observation import TerminalObservation

        t = TerminalObservation(terminal_id="t1", host_id="srv1500858")
        assert t.host_id == "srv1500858"
        assert t.to_dict()["host_id"] == "srv1500858"

    def test_with_cwd(self):
        from substrate.meta_ide.workspace_observation import TerminalObservation

        t = TerminalObservation(terminal_id="t1", cwd="/opt/OS")
        assert t.cwd == "/opt/OS"

    def test_with_pid(self):
        from substrate.meta_ide.workspace_observation import TerminalObservation

        t = TerminalObservation(terminal_id="t1", pid=12345)
        assert t.pid == 12345

    def test_active_state(self):
        from substrate.meta_ide.workspace_observation import TerminalObservation

        active = TerminalObservation(terminal_id="t1", is_active=True)
        idle = TerminalObservation(terminal_id="t2", is_active=False)
        assert active.is_active is True
        assert idle.is_active is False


# ── Test Container Observation ──────────────────────────────────────────────


class TestContainerObservation:
    def test_construction(self):
        from substrate.meta_ide.workspace_observation import ContainerObservation

        c = ContainerObservation(container_id="abc123", container_name="os-discord")
        assert c.container_id == "abc123"
        assert c.container_name == "os-discord"

    def test_defaults(self):
        from substrate.meta_ide.workspace_observation import ContainerObservation

        c = ContainerObservation(container_id="c1")
        assert c.image == ""
        assert c.status == ""
        assert c.ports == []
        assert c.cpu_percent == 0.0
        assert c.memory_mb == 0.0
        assert c.restart_count == 0

    def test_health_mapping(self):
        from substrate.meta_ide.workspace_observation import (
            ContainerObservation,
            ProcessHealth,
        )

        c = ContainerObservation(container_id="c1", health=ProcessHealth.HEALTHY)
        assert c.health == ProcessHealth.HEALTHY
        d = c.to_dict()
        assert d["health"] == "healthy"

    def test_ports_list(self):
        from substrate.meta_ide.workspace_observation import ContainerObservation

        c = ContainerObservation(container_id="c1", ports=["8080:8080/tcp", "443:443/tcp"])
        assert len(c.ports) == 2
        assert c.to_dict()["ports"] == ["8080:8080/tcp", "443:443/tcp"]

    def test_restart_count(self):
        from substrate.meta_ide.workspace_observation import ContainerObservation

        c = ContainerObservation(container_id="c1", restart_count=5)
        assert c.restart_count == 5

    def test_to_dict_all_fields(self):
        from substrate.meta_ide.workspace_observation import ContainerObservation

        c = ContainerObservation(container_id="c1")
        d = c.to_dict()
        expected_keys = {
            "container_id",
            "container_name",
            "image",
            "status",
            "health",
            "ports",
            "cpu_percent",
            "memory_mb",
            "restart_count",
            "started_at",
            "observed_at",
        }
        assert set(d.keys()) == expected_keys

    def test_crashed_health(self):
        from substrate.meta_ide.workspace_observation import (
            ContainerObservation,
            ProcessHealth,
        )

        c = ContainerObservation(container_id="c1", health=ProcessHealth.CRASHED)
        assert c.to_dict()["health"] == "crashed"

    def test_degraded_health(self):
        from substrate.meta_ide.workspace_observation import (
            ContainerObservation,
            ProcessHealth,
        )

        c = ContainerObservation(container_id="c1", health=ProcessHealth.DEGRADED)
        assert c.to_dict()["health"] == "degraded"


# ── Test Preview Observation ────────────────────────────────────────────────


class TestPreviewObservation:
    def test_construction(self):
        from substrate.meta_ide.workspace_observation import PreviewObservation

        p = PreviewObservation(preview_id="preview-5173", name="vite dev server", port=5173)
        assert p.preview_id == "preview-5173"
        assert p.name == "vite dev server"
        assert p.port == 5173

    def test_url_building(self):
        from substrate.meta_ide.workspace_observation import PreviewObservation

        p = PreviewObservation(preview_id="p1", port=3000)
        d = p.to_dict()
        assert d["url"] == "http://localhost:3000"

    def test_explicit_url(self):
        from substrate.meta_ide.workspace_observation import PreviewObservation

        p = PreviewObservation(preview_id="p1", port=3000, url="http://0.0.0.0:3000")
        d = p.to_dict()
        assert d["url"] == "http://0.0.0.0:3000"

    def test_health_states(self):
        from substrate.meta_ide.workspace_observation import (
            PreviewObservation,
            ProcessHealth,
        )

        p = PreviewObservation(preview_id="p1", health=ProcessHealth.HEALTHY)
        assert p.to_dict()["health"] == "healthy"

    def test_defaults(self):
        from substrate.meta_ide.workspace_observation import PreviewObservation

        p = PreviewObservation(preview_id="p1")
        assert p.protocol == "http"
        assert p.pid == 0
        assert p.process_name == ""
        assert p.restart_count == 0

    def test_to_dict_all_fields(self):
        from substrate.meta_ide.workspace_observation import PreviewObservation

        p = PreviewObservation(preview_id="p1")
        d = p.to_dict()
        expected_keys = {
            "preview_id",
            "name",
            "port",
            "protocol",
            "url",
            "pid",
            "process_name",
            "health",
            "restart_count",
            "started_at",
            "last_checked_at",
            "observed_at",
        }
        assert set(d.keys()) == expected_keys

    def test_with_process_name(self):
        from substrate.meta_ide.workspace_observation import PreviewObservation

        p = PreviewObservation(preview_id="p1", process_name="node", pid=1234)
        assert p.process_name == "node"
        assert p.pid == 1234

    def test_restart_count_tracking(self):
        from substrate.meta_ide.workspace_observation import PreviewObservation

        p = PreviewObservation(preview_id="p1", restart_count=3)
        assert p.restart_count == 3


# ── Test Engineering Session Observation ────────────────────────────────────


class TestEngineeringSessionObservation:
    def test_construction(self):
        from substrate.meta_ide.workspace_observation import EngineeringSessionObservation

        e = EngineeringSessionObservation(session_id="sess-abc", harness="claude_code")
        assert e.session_id == "sess-abc"
        assert e.harness == "claude_code"

    def test_defaults(self):
        from substrate.meta_ide.workspace_observation import EngineeringSessionObservation

        e = EngineeringSessionObservation(session_id="s1")
        assert e.status == ""
        assert e.duration_seconds == 0.0
        assert e.events_count == 0
        assert e.decisions_count == 0
        assert e.files_touched == 0
        assert e.coherence_issues == 0

    def test_to_dict(self):
        from substrate.meta_ide.workspace_observation import EngineeringSessionObservation

        e = EngineeringSessionObservation(
            session_id="s1",
            harness="claude_code",
            status="active",
            events_count=42,
        )
        d = e.to_dict()
        assert d["session_id"] == "s1"
        assert d["harness"] == "claude_code"
        assert d["events_count"] == 42

    def test_duration(self):
        from substrate.meta_ide.workspace_observation import EngineeringSessionObservation

        e = EngineeringSessionObservation(session_id="s1", duration_seconds=3600.5)
        assert e.duration_seconds == 3600.5

    def test_coherence_issues(self):
        from substrate.meta_ide.workspace_observation import EngineeringSessionObservation

        e = EngineeringSessionObservation(session_id="s1", coherence_issues=2)
        assert e.coherence_issues == 2


# ── Test Workspace Observation Snapshot ─────────────────────────────────────


class TestWorkspaceObservationSnapshot:
    def test_auto_snapshot_id(self):
        from substrate.meta_ide.workspace_observation import WorkspaceObservationSnapshot

        s = WorkspaceObservationSnapshot()
        assert s.snapshot_id.startswith("wobs-")
        assert len(s.snapshot_id) == 17  # "wobs-" + 12 hex chars

    def test_unique_ids(self):
        from substrate.meta_ide.workspace_observation import WorkspaceObservationSnapshot

        s1 = WorkspaceObservationSnapshot()
        s2 = WorkspaceObservationSnapshot()
        assert s1.snapshot_id != s2.snapshot_id

    def test_empty_lists_default(self):
        from substrate.meta_ide.workspace_observation import WorkspaceObservationSnapshot

        s = WorkspaceObservationSnapshot()
        assert s.terminals == []
        assert s.containers == []
        assert s.previews == []
        assert s.engineering_sessions == []
        assert s.repositories == []

    def test_to_dict_structure(self):
        from substrate.meta_ide.workspace_observation import WorkspaceObservationSnapshot

        s = WorkspaceObservationSnapshot()
        d = s.to_dict()
        assert "snapshot_id" in d
        assert "terminals" in d
        assert "containers" in d
        assert "previews" in d
        assert "summary" in d
        assert d["summary"]["terminal_count"] == 0

    def test_composition(self):
        from substrate.meta_ide.workspace_observation import (
            TerminalObservation,
            ContainerObservation,
            WorkspaceObservationSnapshot,
        )

        s = WorkspaceObservationSnapshot(
            terminals=[TerminalObservation(terminal_id="t1")],
            containers=[
                ContainerObservation(container_id="c1"),
                ContainerObservation(container_id="c2"),
            ],
        )
        d = s.to_dict()
        assert d["summary"]["terminal_count"] == 1
        assert d["summary"]["container_count"] == 2

    def test_metadata(self):
        from substrate.meta_ide.workspace_observation import WorkspaceObservationSnapshot

        s = WorkspaceObservationSnapshot(metadata={"source": "test"})
        assert s.metadata == {"source": "test"}
        assert s.to_dict()["metadata"] == {"source": "test"}


# ── Test Workspace Observation Engine ───────────────────────────────────────


class TestWorkspaceObservationEngine:
    def test_observe_empty(self):
        from substrate.meta_ide.workspace_observation import WorkspaceObservationEngine

        engine = WorkspaceObservationEngine(repo_paths=[])
        snap = engine.observe()
        assert snap.terminals == []
        assert snap.containers == []
        assert snap.previews == []

    def test_observe_with_terminal_data(self):
        from substrate.meta_ide.workspace_observation import WorkspaceObservationEngine

        engine = WorkspaceObservationEngine(repo_paths=[])
        snap = engine.observe(
            terminal_data=[
                {"terminal_id": "main:bash.0", "session_name": "main", "is_active": True},
            ]
        )
        assert len(snap.terminals) == 1
        assert snap.terminals[0].terminal_id == "main:bash.0"
        assert snap.terminals[0].is_active is True

    def test_observe_with_container_data(self):
        from substrate.meta_ide.workspace_observation import WorkspaceObservationEngine

        engine = WorkspaceObservationEngine(repo_paths=[])
        snap = engine.observe(
            container_data=[
                {"container_id": "abc", "container_name": "os-discord", "status": "running"},
            ]
        )
        assert len(snap.containers) == 1
        assert snap.containers[0].container_name == "os-discord"

    def test_observe_with_preview_data(self):
        from substrate.meta_ide.workspace_observation import WorkspaceObservationEngine

        engine = WorkspaceObservationEngine(repo_paths=[])
        snap = engine.observe(
            preview_data=[
                {"preview_id": "preview-5173", "name": "vite", "port": 5173},
            ]
        )
        assert len(snap.previews) == 1
        assert snap.previews[0].port == 5173

    def test_latest_returns_most_recent(self):
        from substrate.meta_ide.workspace_observation import WorkspaceObservationEngine

        engine = WorkspaceObservationEngine(repo_paths=[])
        assert engine.latest() is None
        engine.observe()
        engine.observe(terminal_data=[{"terminal_id": "t2"}])
        latest = engine.latest()
        assert latest is not None
        assert len(latest.terminals) == 1

    def test_history_returns_bounded(self):
        from substrate.meta_ide.workspace_observation import WorkspaceObservationEngine

        engine = WorkspaceObservationEngine(repo_paths=[])
        for _ in range(5):
            engine.observe()
        assert len(engine.history(limit=3)) == 3
        assert len(engine.history(limit=10)) == 5

    def test_deque_bounds(self):
        from substrate.meta_ide.workspace_observation import WorkspaceObservationEngine

        engine = WorkspaceObservationEngine(repo_paths=[])
        for _ in range(110):
            engine.observe()
        assert len(engine.history(limit=200)) == 100

    def test_event_spine_emission(self):
        from substrate.meta_ide.workspace_observation import WorkspaceObservationEngine

        spine = MagicMock()
        engine = WorkspaceObservationEngine(repo_paths=[], event_spine=spine)
        engine.observe(terminal_data=[{"terminal_id": "t1"}])
        spine.emit.assert_called_once()
        call_kwargs = spine.emit.call_args
        assert call_kwargs[1]["data"]["terminal_count"] == 1

    def test_none_spine_graceful(self):
        from substrate.meta_ide.workspace_observation import WorkspaceObservationEngine

        engine = WorkspaceObservationEngine(repo_paths=[], event_spine=None)
        snap = engine.observe()
        assert snap is not None

    def test_safe_parse_ignores_unknown_fields(self):
        from substrate.meta_ide.workspace_observation import WorkspaceObservationEngine

        engine = WorkspaceObservationEngine(repo_paths=[])
        snap = engine.observe(
            terminal_data=[
                {"terminal_id": "t1", "unknown_field": "ignored", "extra": 42},
            ]
        )
        assert len(snap.terminals) == 1
        assert snap.terminals[0].terminal_id == "t1"
        assert not hasattr(snap.terminals[0], "unknown_field")

    def test_engineering_sessions_from_jsonl(self, tmp_path):
        sessions_dir = tmp_path / "data" / "umh" / "sessions"
        sessions_dir.mkdir(parents=True)
        active_file = sessions_dir / "active_sessions.jsonl"
        active_file.write_text(
            json.dumps(
                {
                    "session_id": "s1",
                    "harness": "claude_code",
                    "status": "active",
                    "events_count": 10,
                }
            )
            + "\n"
            + json.dumps({"session_id": "s2", "harness": "codex", "status": "active"})
            + "\n"
        )

        from substrate.meta_ide.workspace_observation import WorkspaceObservationEngine

        with patch.dict(os.environ, {"UMH_ROOT": str(tmp_path)}):
            engine = WorkspaceObservationEngine(repo_paths=[])
            snap = engine.observe()
            assert len(snap.engineering_sessions) == 2
            assert snap.engineering_sessions[0].session_id == "s1"
            assert snap.engineering_sessions[0].events_count == 10

    def test_engineering_sessions_missing_file(self, tmp_path):
        from substrate.meta_ide.workspace_observation import WorkspaceObservationEngine

        with patch.dict(os.environ, {"UMH_ROOT": str(tmp_path)}):
            engine = WorkspaceObservationEngine(repo_paths=[])
            snap = engine.observe()
            assert snap.engineering_sessions == []


# ── Test Workspace Probe ────────────────────────────────────────────────────


class TestWorkspaceProbe:
    def test_import(self):
        from nodes.environments.workspace_probe import WorkspaceProbe

        probe = WorkspaceProbe()
        assert probe is not None

    def test_probe_terminals_tmux_unavailable(self):
        from nodes.environments.workspace_probe import WorkspaceProbe

        probe = WorkspaceProbe()
        with patch("nodes.environments.workspace_probe.gated_subprocess_run", return_value=None):
            result = probe.probe_terminals()
            assert result == []

    def test_probe_terminals_parses_output(self):
        from nodes.environments.workspace_probe import WorkspaceProbe

        mock_sessions = MagicMock()
        mock_sessions.returncode = 0
        mock_sessions.stdout = "main\ndev\n"

        mock_panes = MagicMock()
        mock_panes.returncode = 0
        mock_panes.stdout = "bash|0|1234|python|/opt/OS|1\n"

        probe = WorkspaceProbe()
        with patch(
            "nodes.environments.workspace_probe.gated_subprocess_run",
            side_effect=[mock_sessions, mock_panes, mock_panes],
        ):
            result = probe.probe_terminals()
            assert len(result) == 2
            assert result[0]["session_name"] == "main"
            assert result[0]["current_command"] == "python"
            assert result[0]["is_active"] is True

    def test_probe_containers_docker_unavailable(self):
        from nodes.environments.workspace_probe import WorkspaceProbe

        probe = WorkspaceProbe()
        with patch("nodes.environments.workspace_probe.gated_subprocess_run", return_value=None):
            result = probe.probe_containers()
            assert result == []

    def test_probe_containers_parses_output(self):
        from nodes.environments.workspace_probe import WorkspaceProbe

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"id":"abc123","name":"os-discord","image":"python:3.11","status":"Up 2 hours","ports":"8080:8080/tcp"}\n'

        probe = WorkspaceProbe()
        with patch(
            "nodes.environments.workspace_probe.gated_subprocess_run", return_value=mock_result
        ):
            result = probe.probe_containers()
            assert len(result) == 1
            assert result[0]["container_name"] == "os-discord"
            assert result[0]["health"] == "healthy"
            assert result[0]["ports"] == ["8080:8080/tcp"]

    def test_probe_previews_ss_unavailable(self):
        from nodes.environments.workspace_probe import WorkspaceProbe

        probe = WorkspaceProbe()
        with patch("nodes.environments.workspace_probe.gated_subprocess_run", return_value=None):
            result = probe.probe_previews()
            assert result == []

    def test_probe_previews_parses_output(self):
        from nodes.environments.workspace_probe import WorkspaceProbe

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = (
            "State   Recv-Q  Send-Q  Local Address:Port  Peer Address:Port  Process\n"
            'LISTEN  0       128     0.0.0.0:5173        0.0.0.0:*          users:(("node",pid=9876,fd=23))\n'
            'LISTEN  0       128     0.0.0.0:22          0.0.0.0:*          users:(("sshd",pid=100,fd=3))\n'
        )

        probe = WorkspaceProbe()
        with patch(
            "nodes.environments.workspace_probe.gated_subprocess_run", return_value=mock_result
        ):
            with patch.object(probe, "_pid_to_name", return_value="node"):
                result = probe.probe_previews()
                assert len(result) == 1
                assert result[0]["port"] == 5173
                assert result[0]["url"] == "http://localhost:5173"

    def test_probe_all_composition(self):
        from nodes.environments.workspace_probe import WorkspaceProbe

        probe = WorkspaceProbe()
        with patch.object(probe, "probe_terminals", return_value=[{"terminal_id": "t1"}]):
            with patch.object(probe, "probe_containers", return_value=[{"container_id": "c1"}]):
                with patch.object(probe, "probe_previews", return_value=[]):
                    result = probe.probe_all()
                    assert "terminals" in result
                    assert "containers" in result
                    assert "previews" in result
                    assert len(result["terminals"]) == 1
                    assert len(result["containers"]) == 1

    def test_cpu_gate_none_handling(self):
        from nodes.environments.workspace_probe import WorkspaceProbe

        probe = WorkspaceProbe()
        with patch("nodes.environments.workspace_probe.gated_subprocess_run", return_value=None):
            assert probe.probe_terminals() == []
            assert probe.probe_containers() == []
            assert probe.probe_previews() == []

    def test_pid_to_name_nonexistent(self):
        from nodes.environments.workspace_probe import WorkspaceProbe

        result = WorkspaceProbe._pid_to_name(999999999)
        assert result == ""


# ── Test Cockpit Routes ─────────────────────────────────────────────────────


class TestCockpitRoutes:
    def test_import_routes(self):
        from transports.api.cockpit_workspace_observation_routes import (
            configure,
            workspace_observation_router,
        )

        assert configure is not None
        assert workspace_observation_router is not None

    def test_configure_sets_flag(self):
        from transports.api import cockpit_workspace_observation_routes as mod

        mock_dep = MagicMock()
        mod.configure(mock_dep)
        assert mod._configured is True

    def test_router_has_routes(self):
        from transports.api import cockpit_workspace_observation_routes as mod

        mock_dep = MagicMock()
        mod.configure(mock_dep)
        routes = [r.path for r in mod.workspace_observation_router.routes]
        assert "/meta-ide/workspace-observation" in routes
        assert "/meta-ide/workspace-observation/terminals" in routes
        assert "/meta-ide/workspace-observation/containers" in routes
        assert "/meta-ide/workspace-observation/previews" in routes

    def test_route_count(self):
        from transports.api import cockpit_workspace_observation_routes as mod

        mock_dep = MagicMock()
        mod.configure(mock_dep)
        routes = [r for r in mod.workspace_observation_router.routes if hasattr(r, "path")]
        assert len(routes) == 6


# ── Test Type Registration ──────────────────────────────────────────────────


class TestTypeRegistration:
    def test_canonical_types_registered(self):
        from substrate.canonical_types import CANONICAL_TYPES

        phase25_types = [
            "ObservationDomain",
            "ProcessHealth",
            "TerminalObservation",
            "ContainerObservation",
            "PreviewObservation",
            "EngineeringSessionObservation",
            "WorkspaceObservationSnapshot",
        ]
        for t in phase25_types:
            assert t in CANONICAL_TYPES, f"{t} not in CANONICAL_TYPES"
            assert "substrate.meta_ide.workspace_observation" in CANONICAL_TYPES[t]

    def test_mutation_source_has_meta_ide_runtime(self):
        from substrate.reality_model.reality_mutation import MutationSource

        assert hasattr(MutationSource, "META_IDE_RUNTIME")
        assert MutationSource.META_IDE_RUNTIME == "meta_ide_runtime"

    def test_init_exports(self):
        from substrate.meta_ide import (
            ObservationDomain,
            ProcessHealth,
            TerminalObservation,
            ContainerObservation,
            PreviewObservation,
            EngineeringSessionObservation,
            WorkspaceObservationEngine,
            WorkspaceObservationSnapshot,
        )

        assert ObservationDomain is not None
        assert ProcessHealth is not None
        assert TerminalObservation is not None
        assert ContainerObservation is not None
        assert PreviewObservation is not None
        assert EngineeringSessionObservation is not None
        assert WorkspaceObservationEngine is not None
        assert WorkspaceObservationSnapshot is not None


# ── Integration Tests ───────────────────────────────────────────────────────


class TestIntegration:
    def test_probe_to_engine_pipeline(self):
        from substrate.meta_ide.workspace_observation import WorkspaceObservationEngine

        engine = WorkspaceObservationEngine(repo_paths=[])
        snap = engine.observe(
            terminal_data=[{"terminal_id": "main:bash.0", "session_name": "main"}],
            container_data=[{"container_id": "abc", "container_name": "os-discord"}],
            preview_data=[{"preview_id": "preview-5173", "port": 5173}],
        )
        d = snap.to_dict()
        assert d["summary"]["terminal_count"] == 1
        assert d["summary"]["container_count"] == 1
        assert d["summary"]["preview_count"] == 1

    def test_empty_probe_data(self):
        from substrate.meta_ide.workspace_observation import WorkspaceObservationEngine

        engine = WorkspaceObservationEngine(repo_paths=[])
        snap = engine.observe(terminal_data=[], container_data=[], preview_data=[])
        assert snap.terminals == []
        assert snap.containers == []
        assert snap.previews == []

    def test_partial_probe_data(self):
        from substrate.meta_ide.workspace_observation import WorkspaceObservationEngine

        engine = WorkspaceObservationEngine(repo_paths=[])
        snap = engine.observe(terminal_data=[{"terminal_id": "t1"}])
        assert len(snap.terminals) == 1
        assert snap.containers == []
        assert snap.previews == []

    def test_snapshot_to_dict_roundtrip(self):
        from substrate.meta_ide.workspace_observation import (
            TerminalObservation,
            ContainerObservation,
            PreviewObservation,
            WorkspaceObservationSnapshot,
        )

        snap = WorkspaceObservationSnapshot(
            terminals=[TerminalObservation(terminal_id="t1", session_name="main")],
            containers=[ContainerObservation(container_id="c1", container_name="os-discord")],
            previews=[PreviewObservation(preview_id="p1", port=5173)],
        )
        d = snap.to_dict()
        assert isinstance(d, dict)
        assert len(d["terminals"]) == 1
        assert d["terminals"][0]["terminal_id"] == "t1"
        assert d["containers"][0]["container_name"] == "os-discord"
        assert d["previews"][0]["port"] == 5173

    def test_observation_domain_used_in_summary(self):
        from substrate.meta_ide.workspace_observation import (
            ObservationDomain,
            WorkspaceObservationSnapshot,
            TerminalObservation,
        )

        assert ObservationDomain.TERMINAL == "terminal"
        snap = WorkspaceObservationSnapshot(
            terminals=[TerminalObservation(terminal_id="t1")],
        )
        assert snap.to_dict()["summary"]["terminal_count"] == 1

    def test_multiple_observations_build_history(self):
        from substrate.meta_ide.workspace_observation import WorkspaceObservationEngine

        engine = WorkspaceObservationEngine(repo_paths=[])
        engine.observe(terminal_data=[{"terminal_id": "t1"}])
        engine.observe(container_data=[{"container_id": "c1"}])
        engine.observe(preview_data=[{"preview_id": "p1", "port": 3000}])

        history = engine.history()
        assert len(history) == 3
        assert len(history[0].terminals) == 1
        assert len(history[1].containers) == 1
        assert len(history[2].previews) == 1

    def test_event_spine_data_shape(self):
        from substrate.meta_ide.workspace_observation import WorkspaceObservationEngine

        spine = MagicMock()
        engine = WorkspaceObservationEngine(repo_paths=[], event_spine=spine)
        engine.observe(
            terminal_data=[{"terminal_id": "t1"}, {"terminal_id": "t2"}],
            container_data=[{"container_id": "c1"}],
        )
        data = spine.emit.call_args[1]["data"]
        assert data["terminal_count"] == 2
        assert data["container_count"] == 1
        assert data["preview_count"] == 0

    def test_process_health_in_container_observation(self):
        from substrate.meta_ide.workspace_observation import (
            ContainerObservation,
            ProcessHealth,
        )

        for health in ProcessHealth:
            c = ContainerObservation(container_id="c1", health=health)
            assert c.to_dict()["health"] == health.value
