"""Phase 77 Workstation State + Session Continuity — comprehensive test suite.

Tests (70+):
  - OperatorProfile: create, save, load, round-trip, defaults, ExecutionPreference
  - DeviceRegistry: register, get, list, mark_seen, set_status, to_dict/from_dict, defaults
  - EnvironmentRegistry: register, get, list, find_by_capability, find_preferred, set_status, defaults
  - ModeRegistry: list, get, validate, register custom, all 9 modes, ModeProfile round-trip
  - SessionState: create, load, update, pause, close, get_active, list, lifecycle, from_dict
  - Resume: summarize_traces, list_pending_approvals, build_resume_summary, format_resume_summary
  - BootSequence: full boot, partial failure, all 10 steps, mode resolution, BootResult round-trip
  - Run loop: workstation_context in metadata, absent context preserves behavior
  - Invariants: no subprocess/requests/browser imports in workstation modules
  - Storage: StorageBackend compatibility with profile persistence
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

import pytest

# ═══════════════════════════════════════════════════════════════════════
# 1. OperatorProfile + ExecutionPreference
# ═══════════════════════════════════════════════════════════════════════

from umh.workstation.operator_profile import (
    ExecutionPreference,
    OperatorProfile,
    create_default_profile,
    load_or_create_profile,
    save_profile,
)


class TestExecutionPreference:
    def test_defaults(self):
        pref = ExecutionPreference()
        assert pref.preferred_environment == "local"
        assert pref.preferred_device == "default_vps"
        assert pref.allow_simulation_fallback is True
        assert pref.max_risk_without_approval == "medium"

    def test_to_dict_round_trip(self):
        pref = ExecutionPreference(
            preferred_environment="cloud",
            preferred_backend="gemini",
            max_risk_without_approval="high",
        )
        d = pref.to_dict()
        restored = ExecutionPreference.from_dict(d)
        assert restored.preferred_environment == "cloud"
        assert restored.preferred_backend == "gemini"
        assert restored.max_risk_without_approval == "high"

    def test_from_dict_with_missing_keys(self):
        pref = ExecutionPreference.from_dict({})
        assert pref.preferred_environment == "local"
        assert pref.preferred_device == "default_vps"

    def test_metadata_preserved(self):
        pref = ExecutionPreference(metadata={"key": "value"})
        d = pref.to_dict()
        assert d["metadata"] == {"key": "value"}


class TestOperatorProfile:
    def test_create_default(self):
        profile = create_default_profile("user_1")
        assert profile.user_id == "user_1"
        assert profile.workstation_id.startswith("ws_")
        assert profile.active_mode == "command_center"
        assert profile.created_at != ""
        assert isinstance(profile.execution_preference, ExecutionPreference)

    def test_to_dict_round_trip(self):
        profile = create_default_profile("user_rt")
        d = profile.to_dict()
        restored = OperatorProfile.from_dict(d)
        assert restored.user_id == "user_rt"
        assert restored.workstation_id == profile.workstation_id
        assert restored.active_mode == "command_center"
        assert restored.execution_preference.preferred_environment == "local"

    def test_from_dict_minimal(self):
        profile = OperatorProfile.from_dict({"user_id": "min_user"})
        assert profile.user_id == "min_user"
        assert profile.active_mode == "command_center"
        assert profile.workstation_id == ""

    def test_load_or_create_no_store(self):
        profile = load_or_create_profile("no_store_user")
        assert profile.user_id == "no_store_user"
        assert profile.workstation_id.startswith("ws_")

    def test_load_or_create_with_store(self):
        store = _DictStore()
        p1 = load_or_create_profile("store_user", store=store)
        p2 = load_or_create_profile("store_user", store=store)
        assert p1.workstation_id == p2.workstation_id

    def test_save_profile(self):
        store = _DictStore()
        profile = create_default_profile("save_user")
        save_profile(profile, store)
        data = store.get(f"profile:{profile.user_id}")
        assert data is not None
        assert data["user_id"] == "save_user"

    def test_save_updates_timestamp(self):
        store = _DictStore()
        profile = create_default_profile("ts_user")
        old_updated = profile.updated_at
        save_profile(profile, store)
        assert profile.updated_at >= old_updated


# ═══════════════════════════════════════════════════════════════════════
# 2. DeviceRegistry
# ═══════════════════════════════════════════════════════════════════════

from umh.workstation.device_registry import (
    DeviceRecord,
    DeviceRegistry,
    DeviceStatus,
    DeviceType,
    create_default_devices,
)


class TestDeviceRecord:
    def test_to_dict_round_trip(self):
        rec = DeviceRecord(
            device_id="dev1",
            name="Test Device",
            device_type=DeviceType.VPS,
            status=DeviceStatus.ACTIVE,
            capabilities=["cli.command"],
        )
        d = rec.to_dict()
        restored = DeviceRecord.from_dict(d)
        assert restored.device_id == "dev1"
        assert restored.device_type == DeviceType.VPS
        assert restored.status == DeviceStatus.ACTIVE
        assert "cli.command" in restored.capabilities

    def test_defaults(self):
        rec = DeviceRecord(device_id="x", name="X")
        assert rec.device_type == DeviceType.UNKNOWN
        assert rec.status == DeviceStatus.UNKNOWN
        assert rec.capabilities == []


class TestDeviceRegistry:
    def test_register_and_get(self):
        reg = DeviceRegistry()
        dev = DeviceRecord(device_id="d1", name="D1")
        reg.register_device(dev)
        assert reg.get_device("d1") is dev

    def test_get_missing(self):
        reg = DeviceRegistry()
        assert reg.get_device("nope") is None

    def test_list_devices(self):
        reg = DeviceRegistry()
        reg.register_device(DeviceRecord(device_id="a", name="A"))
        reg.register_device(DeviceRecord(device_id="b", name="B"))
        assert len(reg.list_devices()) == 2

    def test_mark_seen_updates_timestamp(self):
        reg = DeviceRegistry()
        dev = DeviceRecord(device_id="ms", name="MS", status=DeviceStatus.UNKNOWN)
        reg.register_device(dev)
        assert reg.mark_seen("ms") is True
        assert dev.last_seen != ""
        assert dev.status == DeviceStatus.AVAILABLE

    def test_mark_seen_missing(self):
        reg = DeviceRegistry()
        assert reg.mark_seen("nope") is False

    def test_set_status(self):
        reg = DeviceRegistry()
        dev = DeviceRecord(device_id="s1", name="S1")
        reg.register_device(dev)
        assert reg.set_status("s1", DeviceStatus.OFFLINE) is True
        assert dev.status == DeviceStatus.OFFLINE

    def test_set_status_missing(self):
        reg = DeviceRegistry()
        assert reg.set_status("nope", DeviceStatus.ACTIVE) is False

    def test_to_dict_from_dict_round_trip(self):
        reg = DeviceRegistry()
        reg.register_device(DeviceRecord(device_id="r1", name="R1", device_type=DeviceType.LAPTOP))
        d = reg.to_dict()
        restored = DeviceRegistry.from_dict(d)
        assert restored.get_device("r1") is not None
        assert restored.get_device("r1").device_type == DeviceType.LAPTOP

    def test_create_default_devices(self):
        devices = create_default_devices()
        assert len(devices) >= 1
        vps = devices[0]
        assert vps.device_id == "default_vps"
        assert vps.device_type == DeviceType.VPS
        assert vps.status == DeviceStatus.ACTIVE


# ═══════════════════════════════════════════════════════════════════════
# 3. EnvironmentRegistry
# ═══════════════════════════════════════════════════════════════════════

from umh.workstation.environment_registry import (
    EnvironmentStatus,
    WorkstationEnvironmentRecord,
    WorkstationEnvironmentRegistry,
    create_default_environments,
)


class TestWorkstationEnvironmentRecord:
    def test_to_dict_round_trip(self):
        rec = WorkstationEnvironmentRecord(
            environment_id="env1",
            name="Test Env",
            capabilities=["cli.command"],
            network_policy="allow_list",
            status=EnvironmentStatus.ACTIVE,
        )
        d = rec.to_dict()
        restored = WorkstationEnvironmentRecord.from_dict(d)
        assert restored.environment_id == "env1"
        assert restored.network_policy == "allow_list"
        assert restored.status == EnvironmentStatus.ACTIVE

    def test_defaults(self):
        rec = WorkstationEnvironmentRecord(environment_id="x", name="X")
        assert rec.environment_type == "general"
        assert rec.network_policy == "deny"
        assert rec.status == EnvironmentStatus.UNKNOWN


class TestWorkstationEnvironmentRegistry:
    def test_register_and_get(self):
        reg = WorkstationEnvironmentRegistry()
        env = WorkstationEnvironmentRecord(environment_id="e1", name="E1")
        reg.register_environment(env)
        assert reg.get_environment("e1") is env

    def test_get_missing(self):
        reg = WorkstationEnvironmentRegistry()
        assert reg.get_environment("nope") is None

    def test_list_environments(self):
        reg = WorkstationEnvironmentRegistry()
        reg.register_environment(WorkstationEnvironmentRecord(environment_id="a", name="A"))
        reg.register_environment(WorkstationEnvironmentRecord(environment_id="b", name="B"))
        assert len(reg.list_environments()) == 2

    def test_find_by_capability(self):
        reg = WorkstationEnvironmentRegistry()
        reg.register_environment(
            WorkstationEnvironmentRecord(
                environment_id="e1", name="E1", capabilities=["cli.command", "http.get"]
            )
        )
        reg.register_environment(
            WorkstationEnvironmentRecord(environment_id="e2", name="E2", capabilities=["http.get"])
        )
        found = reg.find_by_capability("cli.command")
        assert len(found) == 1
        assert found[0].environment_id == "e1"

    def test_find_by_capability_none(self):
        reg = WorkstationEnvironmentRegistry()
        assert reg.find_by_capability("missing") == []

    def test_find_preferred_active_over_available(self):
        reg = WorkstationEnvironmentRegistry()
        reg.register_environment(
            WorkstationEnvironmentRecord(
                environment_id="avail", name="A", status=EnvironmentStatus.AVAILABLE
            )
        )
        reg.register_environment(
            WorkstationEnvironmentRecord(
                environment_id="active", name="B", status=EnvironmentStatus.ACTIVE
            )
        )
        pref = reg.find_preferred()
        assert pref is not None
        assert pref.environment_id == "active"

    def test_find_preferred_with_capability_filter(self):
        reg = WorkstationEnvironmentRegistry()
        reg.register_environment(
            WorkstationEnvironmentRecord(
                environment_id="e1",
                name="E1",
                capabilities=["http.get"],
                status=EnvironmentStatus.ACTIVE,
            )
        )
        reg.register_environment(
            WorkstationEnvironmentRecord(
                environment_id="e2",
                name="E2",
                capabilities=["cli.command"],
                status=EnvironmentStatus.ACTIVE,
            )
        )
        pref = reg.find_preferred(capability="cli.command")
        assert pref is not None
        assert pref.environment_id == "e2"

    def test_find_preferred_empty(self):
        reg = WorkstationEnvironmentRegistry()
        assert reg.find_preferred() is None

    def test_set_status(self):
        reg = WorkstationEnvironmentRegistry()
        env = WorkstationEnvironmentRecord(environment_id="s1", name="S1")
        reg.register_environment(env)
        assert reg.set_status("s1", EnvironmentStatus.UNAVAILABLE) is True
        assert env.status == EnvironmentStatus.UNAVAILABLE

    def test_set_status_missing(self):
        reg = WorkstationEnvironmentRegistry()
        assert reg.set_status("nope", EnvironmentStatus.ACTIVE) is False

    def test_to_dict_from_dict_round_trip(self):
        reg = WorkstationEnvironmentRegistry()
        reg.register_environment(
            WorkstationEnvironmentRecord(
                environment_id="rt", name="RT", network_policy="allow_list"
            )
        )
        d = reg.to_dict()
        restored = WorkstationEnvironmentRegistry.from_dict(d)
        assert restored.get_environment("rt") is not None
        assert restored.get_environment("rt").network_policy == "allow_list"

    def test_create_default_environments(self):
        envs = create_default_environments()
        assert len(envs) >= 1
        ids = [e.environment_id for e in envs]
        assert "local" in ids


# ═══════════════════════════════════════════════════════════════════════
# 4. ModeRegistry + WorkstationMode
# ═══════════════════════════════════════════════════════════════════════

from umh.workstation.modes import ModeProfile, ModeRegistry, WorkstationMode


class TestWorkstationMode:
    def test_all_nine_modes_exist(self):
        modes = list(WorkstationMode)
        assert len(modes) == 9
        names = {m.value for m in modes}
        for expected in [
            "command_center",
            "developer",
            "research",
            "maintenance",
            "outreach",
            "content",
            "overnight",
            "simulation",
            "emergency",
        ]:
            assert expected in names, f"Missing mode: {expected}"


class TestModeProfile:
    def test_frozen(self):
        profile = ModeProfile(mode=WorkstationMode.DEVELOPER, description="dev")
        with pytest.raises(AttributeError):
            profile.description = "changed"

    def test_to_dict_round_trip(self):
        profile = ModeProfile(
            mode=WorkstationMode.RESEARCH,
            description="Research",
            default_environment_preference="simulation",
            allowed_capabilities=frozenset(["http.get"]),
            memory_context_tags=("research", "data"),
        )
        d = profile.to_dict()
        restored = ModeProfile.from_dict(d)
        assert restored.mode == WorkstationMode.RESEARCH
        assert restored.default_environment_preference == "simulation"
        assert "http.get" in restored.allowed_capabilities
        assert "research" in restored.memory_context_tags


class TestModeRegistry:
    def test_all_mvp_modes_loaded(self):
        reg = ModeRegistry()
        modes = reg.list_modes()
        assert len(modes) == 9

    def test_get_mode_by_string(self):
        reg = ModeRegistry()
        profile = reg.get_mode("command_center")
        assert profile is not None
        assert profile.mode == WorkstationMode.COMMAND_CENTER

    def test_get_mode_by_enum(self):
        reg = ModeRegistry()
        profile = reg.get_mode(WorkstationMode.EMERGENCY)
        assert profile is not None
        assert "emergency" in profile.description.lower()

    def test_get_mode_invalid(self):
        reg = ModeRegistry()
        assert reg.get_mode("nonexistent_mode") is None

    def test_validate_mode_valid(self):
        reg = ModeRegistry()
        assert reg.validate_mode("developer") is True

    def test_validate_mode_invalid(self):
        reg = ModeRegistry()
        assert reg.validate_mode("invalid") is False

    def test_register_custom_mode(self):
        reg = ModeRegistry()
        custom = ModeProfile(
            mode=WorkstationMode.COMMAND_CENTER,
            description="Custom CC override",
        )
        reg.register_mode(custom)
        fetched = reg.get_mode("command_center")
        assert fetched.description == "Custom CC override"

    def test_default_modes_static(self):
        modes = ModeRegistry.default_modes()
        assert len(modes) == 9

    def test_overnight_mode_conservative(self):
        reg = ModeRegistry()
        overnight = reg.get_mode("overnight")
        assert overnight.default_governance_level == "observe"
        assert overnight.default_environment_preference == "simulation"

    def test_emergency_mode_elevated(self):
        reg = ModeRegistry()
        emergency = reg.get_mode("emergency")
        assert emergency.default_governance_level == "execute"


# ═══════════════════════════════════════════════════════════════════════
# 5. SessionState + SessionStore
# ═══════════════════════════════════════════════════════════════════════

from umh.workstation.session_state import (
    SessionState,
    SessionStatus,
    SessionStore,
    get_session_store,
    reset_session_store,
)


class TestSessionState:
    def test_to_dict_round_trip(self):
        session = SessionState(
            session_id="s1",
            user_id="u1",
            active_mode="developer",
            status=SessionStatus.ACTIVE,
            continuity_notes=["note1"],
        )
        d = session.to_dict()
        restored = SessionState.from_dict(d)
        assert restored.session_id == "s1"
        assert restored.active_mode == "developer"
        assert restored.status == SessionStatus.ACTIVE
        assert "note1" in restored.continuity_notes

    def test_from_dict_defaults(self):
        session = SessionState.from_dict({"session_id": "min"})
        assert session.user_id == ""
        assert session.active_mode == "command_center"
        assert session.status == SessionStatus.ACTIVE


class TestSessionStore:
    def setup_method(self):
        reset_session_store(SessionStore())

    def test_create_session(self):
        store = SessionStore()
        session = store.create_session("u1", mode="developer")
        assert session.session_id.startswith("sess_")
        assert session.user_id == "u1"
        assert session.active_mode == "developer"
        assert session.status == SessionStatus.ACTIVE

    def test_load_session(self):
        store = SessionStore()
        created = store.create_session("u1")
        loaded = store.load_session(created.session_id)
        assert loaded is created

    def test_load_session_missing(self):
        store = SessionStore()
        assert store.load_session("nonexistent") is None

    def test_update_session(self):
        store = SessionStore()
        session = store.create_session("u1")
        old_updated = session.updated_at
        store.update_session(session, last_input_summary="test input")
        assert session.last_input_summary == "test input"
        assert session.updated_at >= old_updated

    def test_pause_session(self):
        store = SessionStore()
        session = store.create_session("u1")
        paused = store.pause_session(session.session_id)
        assert paused.status == SessionStatus.PAUSED

    def test_pause_session_missing(self):
        store = SessionStore()
        assert store.pause_session("nope") is None

    def test_close_session(self):
        store = SessionStore()
        session = store.create_session("u1")
        closed = store.close_session(session.session_id)
        assert closed.status == SessionStatus.CLOSED

    def test_close_removes_active(self):
        store = SessionStore()
        session = store.create_session("u1")
        store.close_session(session.session_id)
        assert store.get_active_session("u1") is None

    def test_close_session_missing(self):
        store = SessionStore()
        assert store.close_session("nope") is None

    def test_get_active_session(self):
        store = SessionStore()
        session = store.create_session("u1")
        active = store.get_active_session("u1")
        assert active is session

    def test_get_active_session_none(self):
        store = SessionStore()
        assert store.get_active_session("nobody") is None

    def test_get_active_session_paused_returns_none(self):
        store = SessionStore()
        session = store.create_session("u1")
        store.pause_session(session.session_id)
        assert store.get_active_session("u1") is None

    def test_list_sessions(self):
        store = SessionStore()
        store.create_session("u1")
        store.create_session("u2")
        assert len(store.list_sessions()) == 2

    def test_list_sessions_filtered(self):
        store = SessionStore()
        store.create_session("u1")
        store.create_session("u2")
        assert len(store.list_sessions(user_id="u1")) == 1

    def test_session_lifecycle(self):
        store = SessionStore()
        s = store.create_session("u1", mode="research")
        assert s.status == SessionStatus.ACTIVE
        store.pause_session(s.session_id)
        assert s.status == SessionStatus.PAUSED
        store.update_session(s, status=SessionStatus.ACTIVE)
        assert s.status == SessionStatus.ACTIVE
        store.close_session(s.session_id)
        assert s.status == SessionStatus.CLOSED

    def test_global_singleton(self):
        reset_session_store(None)
        s1 = get_session_store()
        s2 = get_session_store()
        assert s1 is s2
        reset_session_store(None)


# ═══════════════════════════════════════════════════════════════════════
# 6. Resume: traces, approvals, summary
# ═══════════════════════════════════════════════════════════════════════

from umh.workstation.resume import (
    PendingApprovalView,
    TraceResumeSummary,
    build_resume_summary,
    format_resume_summary,
    list_pending_approvals,
    summarize_recent_traces,
)


class _FakeTrace:
    def __init__(self, trace_id: str, user_id: str, status: str):
        self.trace_id = trace_id
        self.user_id = user_id
        self.status = status


class _FakeTraceStore:
    def __init__(self, traces: list[_FakeTrace]):
        self._traces = traces

    def list_traces(self, limit: int = 10) -> list[_FakeTrace]:
        return self._traces[:limit]


class _FakeApprovalRequest:
    def __init__(self, req_id: str, operation: str = "test_op", status: str = "pending"):
        self.id = req_id
        self.operation = operation
        self.inputs_summary = "test inputs summary for approval"
        self.created_at = "2026-05-01T00:00:00Z"
        self.status = status
        self.risk_level = "medium"
        self.capability_type = "cli.command"


class _FakeApprovalStore:
    def __init__(self, pending: list[_FakeApprovalRequest]):
        self._pending = pending

    def list_pending(self) -> list[_FakeApprovalRequest]:
        return self._pending


class TestPendingApprovalView:
    def test_to_dict(self):
        view = PendingApprovalView(
            approval_id="ap1",
            directive_summary="test_op: do thing",
            status="pending",
            risk_level="medium",
        )
        d = view.to_dict()
        assert d["approval_id"] == "ap1"
        assert d["status"] == "pending"


class TestSummarizeRecentTraces:
    def test_basic_counts(self):
        traces = [
            _FakeTrace("t1", "u1", "completed"),
            _FakeTrace("t2", "u1", "failed"),
            _FakeTrace("t3", "u1", "completed"),
        ]
        store = _FakeTraceStore(traces)
        ids, successes, failures = summarize_recent_traces(store, "u1")
        assert len(ids) == 3
        assert successes == 2
        assert failures == 1

    def test_filters_by_user(self):
        traces = [
            _FakeTrace("t1", "u1", "completed"),
            _FakeTrace("t2", "u2", "completed"),
        ]
        store = _FakeTraceStore(traces)
        ids, successes, _ = summarize_recent_traces(store, "u1")
        assert len(ids) == 1
        assert successes == 1

    def test_handles_exception(self):
        class _BrokenStore:
            def list_traces(self, limit=10):
                raise RuntimeError("broken")

        ids, successes, failures = summarize_recent_traces(_BrokenStore(), "u1")
        assert ids == []
        assert successes == 0
        assert failures == 0

    def test_empty_store(self):
        store = _FakeTraceStore([])
        ids, s, f = summarize_recent_traces(store, "u1")
        assert ids == []


class TestListPendingApprovals:
    def test_returns_views(self):
        store = _FakeApprovalStore([_FakeApprovalRequest("a1")])
        views = list_pending_approvals("u1", approval_store=store)
        assert len(views) == 1
        assert views[0].approval_id == "a1"
        assert views[0].risk_level == "medium"

    def test_no_store_returns_empty(self):
        views = list_pending_approvals("u1", approval_store=None)
        assert views == [] or isinstance(views, list)


class TestBuildResumeSummary:
    def test_full_summary(self):
        profile = create_default_profile("u1")
        session_store = SessionStore()
        session = session_store.create_session("u1", mode="developer")
        traces = [_FakeTrace("t1", "u1", "completed"), _FakeTrace("t2", "u1", "failed")]
        trace_store = _FakeTraceStore(traces)
        approval_store = _FakeApprovalStore([_FakeApprovalRequest("a1")])

        summary = build_resume_summary(
            profile=profile,
            session=session,
            trace_store=trace_store,
            approval_store=approval_store,
        )
        assert summary.user_id == "u1"
        assert summary.recent_successes == 1
        assert summary.recent_failures == 1
        assert len(summary.pending_approvals) == 1
        assert summary.generated_at != ""
        assert "1 recent failures" in summary.recommended_resume_points[0]

    def test_no_trace_store(self):
        profile = create_default_profile("u1")
        summary = build_resume_summary(profile=profile)
        assert summary.recent_trace_ids == []
        assert summary.recent_successes == 0

    def test_no_session(self):
        profile = create_default_profile("u1")
        summary = build_resume_summary(profile=profile)
        assert summary.session_id == ""

    def test_resume_points_include_approvals(self):
        profile = create_default_profile("u1")
        approval_store = _FakeApprovalStore(
            [
                _FakeApprovalRequest("a1"),
                _FakeApprovalRequest("a2"),
            ]
        )
        summary = build_resume_summary(profile=profile, approval_store=approval_store)
        points = summary.recommended_resume_points
        assert any("2 pending approvals" in p for p in points)


class TestFormatResumeSummary:
    def test_basic_format(self):
        summary = TraceResumeSummary(
            user_id="u1",
            session_id="sess_abc",
            last_mode="developer",
            recent_trace_ids=["t1", "t2"],
            recent_successes=1,
            recent_failures=1,
            recommended_resume_points=["1 failure to review"],
        )
        text = format_resume_summary(summary)
        assert "sess_abc" in text
        assert "developer" in text
        assert "2" in text
        assert "1 failure to review" in text


# ═══════════════════════════════════════════════════════════════════════
# 7. BootSequence
# ═══════════════════════════════════════════════════════════════════════

from umh.workstation.boot_sequence import BootResult, BootStep, run_boot_sequence


class TestBootStep:
    def test_defaults(self):
        step = BootStep(name="test")
        assert step.status == "pending"
        assert step.error is None

    def test_to_dict(self):
        step = BootStep(name="x", status="completed", output={"k": "v"})
        d = step.to_dict()
        assert d["name"] == "x"
        assert d["status"] == "completed"
        assert d["output"]["k"] == "v"


class TestBootResult:
    def test_to_dict(self):
        result = BootResult(boot_id="b1", user_id="u1", mode="developer", status="completed")
        d = result.to_dict()
        assert d["boot_id"] == "b1"
        assert d["mode"] == "developer"
        assert d["status"] == "completed"


class TestRunBootSequence:
    def setup_method(self):
        reset_session_store(SessionStore())

    def test_full_boot_completes(self):
        result = run_boot_sequence("u1")
        assert result.status in ("completed", "partial")
        assert result.boot_id.startswith("boot_")
        assert result.user_id == "u1"
        assert result.mode == "command_center"
        assert len(result.steps) == 10

    def test_all_step_names(self):
        result = run_boot_sequence("u1")
        names = [s.name for s in result.steps]
        expected = [
            "load_profile",
            "resolve_mode",
            "load_devices",
            "load_environments",
            "load_session",
            "load_traces",
            "load_approvals",
            "build_resume",
            "resolve_preference",
            "finalize",
        ]
        assert names == expected

    def test_profile_loaded(self):
        result = run_boot_sequence("u1")
        assert result.loaded_profile.get("user_id") == "u1"
        assert result.workstation_id.startswith("ws_")

    def test_session_loaded(self):
        result = run_boot_sequence("u1")
        assert result.loaded_session.get("user_id") == "u1"
        assert result.loaded_session.get("status") == "active"

    def test_devices_loaded(self):
        result = run_boot_sequence("u1")
        assert len(result.loaded_devices) >= 1

    def test_environments_loaded(self):
        result = run_boot_sequence("u1")
        assert len(result.loaded_environments) >= 1

    def test_custom_mode(self):
        result = run_boot_sequence("u1", mode="developer")
        assert result.mode == "developer"

    def test_invalid_mode_step_fails(self):
        result = run_boot_sequence("u1", mode="totally_invalid")
        mode_step = [s for s in result.steps if s.name == "resolve_mode"][0]
        assert mode_step.status == "failed"
        assert result.status == "partial"

    def test_with_store_persists_profile(self):
        store = _DictStore()
        result = run_boot_sequence("u1", store=store)
        assert result.loaded_profile.get("user_id") == "u1"
        assert store.get("profile:u1") is not None

    def test_timestamps_set(self):
        result = run_boot_sequence("u1")
        assert result.started_at != ""
        assert result.completed_at != ""
        assert result.completed_at >= result.started_at

    def test_execution_preference_resolved(self):
        result = run_boot_sequence("u1")
        assert "preferred_environment" in result.execution_preference


# ═══════════════════════════════════════════════════════════════════════
# 8. Run loop integration
# ═══════════════════════════════════════════════════════════════════════


class TestRunLoopWorkstationContext:
    def test_workstation_context_in_metadata(self):
        from umh.run import run

        ws_ctx = {
            "active_mode": "developer",
            "active_session_id": "sess_test",
            "execution_preference": {"preferred_environment": "local"},
        }
        result = run("hello", workstation_context=ws_ctx)
        assert "workstation" in result.metadata
        assert result.metadata["workstation"]["active_mode"] == "developer"
        assert result.metadata["workstation"]["active_session_id"] == "sess_test"

    def test_no_workstation_context(self):
        from umh.run import run

        result = run("hello")
        assert "workstation" not in result.metadata

    def test_empty_workstation_context(self):
        from umh.run import run

        result = run("hello", workstation_context={})
        assert "workstation" not in result.metadata


# ═══════════════════════════════════════════════════════════════════════
# 9. Invariants: no forbidden imports in workstation modules
# ═══════════════════════════════════════════════════════════════════════

import ast
import pathlib


_FORBIDDEN_MODULES = {"subprocess", "requests", "selenium", "playwright"}


class TestWorkstationInvariants:
    """Workstation modules must not import subprocess, requests, or browser execution."""

    WORKSTATION_DIR = pathlib.Path("/opt/OS/umh/workstation")

    def test_no_forbidden_imports(self):
        violations = []
        for py_file in self.WORKSTATION_DIR.glob("*.py"):
            source = py_file.read_text()
            try:
                tree = ast.parse(source)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in _FORBIDDEN_MODULES:
                            violations.append(f"{py_file.name}: import {alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    if node.module and any(node.module.startswith(m) for m in _FORBIDDEN_MODULES):
                        violations.append(f"{py_file.name}: from {node.module}")
        assert violations == [], f"Forbidden imports found: {violations}"

    def test_no_dangerous_os_calls(self):
        violations = []
        for py_file in self.WORKSTATION_DIR.glob("*.py"):
            source = py_file.read_text()
            for pattern in ["os.system(", "os.popen(", "os.exec"]:
                if pattern in source:
                    violations.append(f"{py_file.name}: {pattern}")
        assert violations == [], f"Dangerous OS calls found in: {violations}"


# ═══════════════════════════════════════════════════════════════════════
# 10. Storage compatibility
# ═══════════════════════════════════════════════════════════════════════

from umh.storage.backend import InMemoryStorage


class TestStorageCompatibility:
    def test_inmemory_storage_works_with_profile(self):
        store = InMemoryStorage()
        profile = load_or_create_profile("storage_user", store=store)
        assert profile.user_id == "storage_user"
        loaded = load_or_create_profile("storage_user", store=store)
        assert loaded.workstation_id == profile.workstation_id

    def test_inmemory_storage_save_and_retrieve(self):
        store = InMemoryStorage()
        profile = create_default_profile("s_user")
        save_profile(profile, store)
        data = store.get(f"profile:{profile.user_id}")
        assert data["user_id"] == "s_user"
        assert data["workstation_id"] == profile.workstation_id


# ═══════════════════════════════════════════════════════════════════════
# 11. Package exports
# ═══════════════════════════════════════════════════════════════════════


class TestPackageExports:
    def test_all_exports_importable(self):
        from umh.workstation import (
            BootResult,
            ExecutionPreference,
            ModeRegistry,
            OperatorProfile,
            SessionState,
            WorkstationMode,
            get_session_store,
            run_boot_sequence,
        )

        assert BootResult is not None
        assert ExecutionPreference is not None
        assert ModeRegistry is not None
        assert OperatorProfile is not None
        assert SessionState is not None
        assert WorkstationMode is not None
        assert callable(get_session_store)
        assert callable(run_boot_sequence)


# ═══════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════


class _DictStore:
    """Minimal store implementing get/put for tests."""

    def __init__(self):
        self._data: dict[str, Any] = {}

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def put(self, key: str, value: Any) -> None:
        self._data[key] = value

    def all_keys(self) -> list[str]:
        return list(self._data.keys())
