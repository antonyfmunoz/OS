"""
Tests for the daily runtime contracts layer:
  - presence_state
  - runtime_profile
  - daily_rituals
  - handoff_artifact
  - workstation_profile_contract

Enforces: deterministic IDs, SET/REMOVE-only mutations, frozen dataclasses,
replay safety, bounded scans, no provider/UI leakage.
"""

import sys

sys.path.insert(0, "/opt/OS")

from umh.substrate.presence_state import (
    PRESENCE_ACTIVE_STATION,
    PRESENCE_DEEP_WORK,
    PRESENCE_OFF,
    PRESENCE_OVERNIGHT_AUTONOMOUS,
    PRESENCE_REMOTE_LIGHT,
    PresenceState,
    build_presence_state,
    build_presence_state_mutations,
    compute_presence_state_id,
    load_presence_state,
    set_presence,
    summarize_presence_state,
)
from umh.substrate.runtime_profile import (
    RuntimeProfile,
    build_runtime_profile,
    build_runtime_profile_mutations,
    compute_runtime_profile_id,
    list_runtime_profiles,
    load_runtime_profile,
    profile_from_dict,
    profile_to_dict,
)
from umh.substrate.daily_rituals import (
    CANONICAL_CLOSE_STEPS,
    CANONICAL_OPEN_STEPS,
    CloseDayPlan,
    CloseDayRequest,
    OpenDayPlan,
    OpenDayRequest,
    build_close_day_plan,
    build_close_day_request,
    build_open_day_plan,
    build_open_day_request,
    compute_close_day_request_id,
    compute_open_day_request_id,
    summarize_close_day_plan,
    summarize_open_day_plan,
)
from umh.substrate.handoff_artifact import (
    ARTIFACT_KIND_CLOSE_DAY_HANDOFF,
    ARTIFACT_KIND_OPEN_DAY_BRIEF,
    HandoffArtifact,
    build_close_day_handoff_artifact,
    build_open_day_handoff_artifact,
    compute_handoff_artifact_id,
    handoff_artifact_to_mutations,
    list_recent_handoff_artifacts,
    load_handoff_artifact,
)
from umh.substrate.workstation_profile_contract import (
    TRIGGER_CLAP,
    TRIGGER_MANUAL,
    TRIGGER_REMOTE_COMMAND,
    TRIGGER_WAKE_PHRASE,
    WorkstationActivationRequest,
    WorkstationProfileBinding,
    WorkstationRuntimeAdapter,
    binding_to_mutations,
    build_workstation_activation_request,
    build_workstation_profile_binding,
    compute_workstation_activation_id,
    compute_workstation_binding_id,
    load_workstation_profile_binding,
)


# ===================================================================
# A. Presence State
# ===================================================================


class TestPresenceState:
    """Presence state model tests."""

    def test_deterministic_id(self) -> None:
        """Same inputs produce the same ID every time."""
        id1 = compute_presence_state_id(
            "sess_1", "2026-04-17T10:00:00Z", "active_station"
        )
        id2 = compute_presence_state_id(
            "sess_1", "2026-04-17T10:00:00Z", "active_station"
        )
        assert id1 == id2
        assert id1.startswith("prs_")

    def test_different_inputs_different_id(self) -> None:
        """Different inputs produce different IDs."""
        id1 = compute_presence_state_id(
            "sess_1", "2026-04-17T10:00:00Z", "active_station"
        )
        id2 = compute_presence_state_id(
            "sess_2", "2026-04-17T10:00:00Z", "active_station"
        )
        assert id1 != id2

    def test_build_and_load(self) -> None:
        """Build a presence state, persist via mutations, load back."""
        ps = build_presence_state(
            runtime_session_id="sess_1",
            presence=PRESENCE_ACTIVE_STATION,
            mode="focused",
            transport="discord",
            reason="morning login",
            set_at="2026-04-17T10:00:00Z",
        )
        assert ps.presence == PRESENCE_ACTIVE_STATION
        assert ps.mode == "focused"
        assert ps.transport == "discord"
        assert ps.reason == "morning login"

        mutations = build_presence_state_mutations(ps)
        assert len(mutations) == 1
        assert mutations[0]["op"] == "SET"

        # Apply mutations to state and load back
        state: dict = {}
        for m in mutations:
            state[m["key"]] = m["value"]

        loaded = load_presence_state(state, "sess_1")
        assert loaded is not None
        assert loaded.state_id == ps.state_id
        assert loaded.presence == PRESENCE_ACTIVE_STATION

    def test_single_record_overwrite(self) -> None:
        """Setting presence twice overwrites — no history accumulation."""
        state: dict = {}

        ps1, muts1 = set_presence(
            state,
            runtime_session_id="sess_1",
            presence=PRESENCE_REMOTE_LIGHT,
            set_at="2026-04-17T08:00:00Z",
        )
        for m in muts1:
            state[m["key"]] = m["value"]

        ps2, muts2 = set_presence(
            state,
            runtime_session_id="sess_1",
            presence=PRESENCE_DEEP_WORK,
            set_at="2026-04-17T10:00:00Z",
        )
        for m in muts2:
            state[m["key"]] = m["value"]

        # Only one key for this session
        presence_keys = [k for k in state if k.startswith("runtime_presence.")]
        assert len(presence_keys) == 1

        loaded = load_presence_state(state, "sess_1")
        assert loaded is not None
        assert loaded.presence == PRESENCE_DEEP_WORK

    def test_load_missing_returns_none(self) -> None:
        """Loading from empty state returns None."""
        assert load_presence_state({}, "nonexistent") is None

    def test_summary_deterministic(self) -> None:
        """Summary output is stable and deterministic."""
        ps = build_presence_state(
            runtime_session_id="sess_1",
            presence=PRESENCE_ACTIVE_STATION,
            mode="focused",
            transport="discord",
            reason="morning login",
            set_at="2026-04-17T10:00:00Z",
        )
        s1 = summarize_presence_state(ps)
        s2 = summarize_presence_state(ps)
        assert s1 == s2
        assert "sess_1" in s1
        assert "active_station" in s1

    def test_frozen_dataclass(self) -> None:
        """PresenceState is frozen — cannot mutate fields."""
        ps = build_presence_state(
            runtime_session_id="sess_1",
            presence=PRESENCE_OFF,
            set_at="2026-04-17T10:00:00Z",
        )
        try:
            ps.presence = "deep_work"  # type: ignore[misc]
            assert False, "Should have raised FrozenInstanceError"
        except AttributeError:
            pass

    def test_presence_constants_exist(self) -> None:
        """All expected presence constants are defined."""
        assert PRESENCE_OFF == "off"
        assert PRESENCE_REMOTE_LIGHT == "remote_light"
        assert PRESENCE_ACTIVE_STATION == "active_station"
        assert PRESENCE_DEEP_WORK == "deep_work"
        assert PRESENCE_OVERNIGHT_AUTONOMOUS == "overnight_autonomous"


# ===================================================================
# B. Runtime Profile
# ===================================================================


class TestRuntimeProfile:
    """Runtime profile contract tests."""

    def test_deterministic_profile_id(self) -> None:
        """Same name always yields the same profile ID."""
        id1 = compute_runtime_profile_id("development")
        id2 = compute_runtime_profile_id("development")
        assert id1 == id2
        assert id1.startswith("prof_")

    def test_different_names_different_id(self) -> None:
        """Different names produce different IDs."""
        id1 = compute_runtime_profile_id("development")
        id2 = compute_runtime_profile_id("streaming")
        assert id1 != id2

    def test_round_trip_serialization(self) -> None:
        """Profile survives to_dict -> from_dict round trip."""
        profile = build_runtime_profile(
            name="development",
            default_mode="focused",
            default_presence="active_station",
            startup_actions=("open_ide", "load_context", "start_timer"),
            activation_rules=("weekday_morning",),
            delivery_policy="batch",
            continuity_policy="resume_last",
            transport_preferences=("discord", "terminal"),
            execution_policy="sequential",
        )
        d = profile.to_dict()
        restored = RuntimeProfile.from_dict(d)
        assert restored.profile_id == profile.profile_id
        assert restored.name == "development"
        assert restored.startup_actions == ("open_ide", "load_context", "start_timer")
        assert restored.transport_preferences == ("discord", "terminal")

    def test_list_and_load(self) -> None:
        """Profiles can be listed and loaded from state."""
        p1 = build_runtime_profile(
            name="dev",
            default_mode="focused",
            default_presence="active_station",
        )
        p2 = build_runtime_profile(
            name="stream",
            default_mode="broadcast",
            default_presence="active_station",
        )

        state: dict = {}
        for m in build_runtime_profile_mutations(p1):
            state[m["key"]] = m["value"]
        for m in build_runtime_profile_mutations(p2):
            state[m["key"]] = m["value"]

        profiles = list_runtime_profiles(state)
        assert len(profiles) == 2
        assert p1.profile_id in profiles
        assert p2.profile_id in profiles

        loaded = load_runtime_profile(state, p1.profile_id)
        assert loaded is not None
        assert loaded.name == "dev"

    def test_load_missing_returns_none(self) -> None:
        """Loading nonexistent profile returns None."""
        assert load_runtime_profile({}, "nonexistent") is None

    def test_no_hardcoded_personas(self) -> None:
        """Profiles are generic — no DeveloperProfile/StreamerProfile classes."""
        # This is a structural test: RuntimeProfile is the only class
        import umh.substrate.runtime_profile as mod

        classes = [
            name
            for name in dir(mod)
            if isinstance(getattr(mod, name), type)
            and name != "RuntimeProfile"
            and "Profile" in name
        ]
        assert classes == [], f"Found hardcoded profile classes: {classes}"

    def test_startup_actions_preserved(self) -> None:
        """Generic startup_actions are preserved through serialization."""
        profile = build_runtime_profile(
            name="custom",
            default_mode="casual",
            default_presence="remote_light",
            startup_actions=("load_context", "check_mail", "run_audit"),
        )
        mutations = build_runtime_profile_mutations(profile)
        state: dict = {}
        for m in mutations:
            state[m["key"]] = m["value"]
        loaded = load_runtime_profile(state, profile.profile_id)
        assert loaded is not None
        assert loaded.startup_actions == ("load_context", "check_mail", "run_audit")

    def test_mutations_are_set_only(self) -> None:
        """Profile mutations use SET ops only."""
        profile = build_runtime_profile(
            name="test",
            default_mode="m",
            default_presence="p",
        )
        for m in build_runtime_profile_mutations(profile):
            assert m["op"] == "SET"

    def test_frozen_dataclass(self) -> None:
        """RuntimeProfile is frozen."""
        profile = build_runtime_profile(
            name="x",
            default_mode="m",
            default_presence="p",
        )
        try:
            profile.name = "y"  # type: ignore[misc]
            assert False, "Should have raised FrozenInstanceError"
        except AttributeError:
            pass

    def test_profile_to_dict_from_dict_aliases(self) -> None:
        """profile_to_dict and profile_from_dict are importable."""
        assert profile_to_dict is not None
        assert profile_from_dict is not None


# ===================================================================
# C. Daily Rituals
# ===================================================================


class TestDailyRituals:
    """Daily ritual request/plan contract tests."""

    def test_deterministic_open_request_id(self) -> None:
        """Same inputs -> same open-day request ID."""
        id1 = compute_open_day_request_id("sess_1", "2026-04-17T06:00:00Z")
        id2 = compute_open_day_request_id("sess_1", "2026-04-17T06:00:00Z")
        assert id1 == id2
        assert id1.startswith("odr_")

    def test_deterministic_close_request_id(self) -> None:
        """Same inputs -> same close-day request ID."""
        id1 = compute_close_day_request_id("sess_1", "2026-04-17T22:00:00Z")
        id2 = compute_close_day_request_id("sess_1", "2026-04-17T22:00:00Z")
        assert id1 == id2
        assert id1.startswith("cdr_")

    def test_open_day_plan_creation(self) -> None:
        """Open-day plan is created with canonical steps."""
        profile = build_runtime_profile(
            name="dev",
            default_mode="focused",
            default_presence="active_station",
        )
        req = build_open_day_request(
            runtime_session_id="sess_1",
            entry_transport="discord",
            requested_at="2026-04-17T06:00:00Z",
        )
        plan = build_open_day_plan({}, req, profile)
        assert plan.steps == CANONICAL_OPEN_STEPS
        assert plan.mode == "focused"
        assert plan.presence == "active_station"
        assert plan.profile_id == profile.profile_id
        assert plan.plan_id.startswith("dp_")

    def test_open_day_plan_request_overrides(self) -> None:
        """Request-level overrides take precedence over profile defaults."""
        profile = build_runtime_profile(
            name="dev",
            default_mode="focused",
            default_presence="active_station",
        )
        req = build_open_day_request(
            runtime_session_id="sess_1",
            entry_transport="terminal",
            requested_mode="deep_work_mode",
            requested_presence="deep_work",
            requested_at="2026-04-17T06:00:00Z",
        )
        plan = build_open_day_plan({}, req, profile)
        assert plan.mode == "deep_work_mode"
        assert plan.presence == "deep_work"

    def test_close_day_plan_creation(self) -> None:
        """Close-day plan is created with canonical steps."""
        req = build_close_day_request(
            runtime_session_id="sess_1",
            requested_mode_after_close="overnight_autonomous",
            requested_at="2026-04-17T22:00:00Z",
        )
        plan = build_close_day_plan({}, req)
        assert plan.steps == CANONICAL_CLOSE_STEPS
        assert plan.mode_after_close == "overnight_autonomous"
        assert plan.overnight_enabled is True

    def test_close_day_overnight_disabled(self) -> None:
        """Close-day without overnight mode disables overnight."""
        req = build_close_day_request(
            runtime_session_id="sess_1",
            requested_mode_after_close="idle",
            requested_at="2026-04-17T22:00:00Z",
        )
        plan = build_close_day_plan({}, req)
        assert plan.overnight_enabled is False

    def test_summaries_stable(self) -> None:
        """Summaries are deterministic across repeated calls."""
        req = build_open_day_request(
            runtime_session_id="sess_1",
            entry_transport="discord",
            requested_at="2026-04-17T06:00:00Z",
        )
        plan = build_open_day_plan({}, req, None)
        s1 = summarize_open_day_plan(plan)
        s2 = summarize_open_day_plan(plan)
        assert s1 == s2
        assert "open day:" in s1

        creq = build_close_day_request(
            runtime_session_id="sess_1",
            requested_mode_after_close="idle",
            requested_at="2026-04-17T22:00:00Z",
        )
        cplan = build_close_day_plan({}, creq)
        cs1 = summarize_close_day_plan(cplan)
        cs2 = summarize_close_day_plan(cplan)
        assert cs1 == cs2
        assert "close day:" in cs1

    def test_symbolic_steps_ordered(self) -> None:
        """Open and close steps have correct count and ordering."""
        assert len(CANONICAL_OPEN_STEPS) == 8
        assert CANONICAL_OPEN_STEPS[0] == "identify_session_start"
        assert CANONICAL_OPEN_STEPS[-1] == "expose_recommended_next_action"

        assert len(CANONICAL_CLOSE_STEPS) == 8
        assert CANONICAL_CLOSE_STEPS[0] == "identify_session_close"
        assert CANONICAL_CLOSE_STEPS[-1] == "finalize_overnight_state"

    def test_no_side_effects(self) -> None:
        """Plan builders do not modify the state dict."""
        state: dict = {"some_key": "some_value"}
        state_copy = dict(state)
        req = build_open_day_request(
            runtime_session_id="sess_1",
            entry_transport="discord",
            requested_at="2026-04-17T06:00:00Z",
        )
        build_open_day_plan(state, req, None)
        assert state == state_copy

    def test_frozen_dataclasses(self) -> None:
        """All ritual dataclasses are frozen."""
        req = build_open_day_request(
            runtime_session_id="s",
            entry_transport="t",
            requested_at="2026-04-17T06:00:00Z",
        )
        try:
            req.entry_transport = "x"  # type: ignore[misc]
            assert False
        except AttributeError:
            pass


# ===================================================================
# D. Handoff Artifacts
# ===================================================================


class TestHandoffArtifact:
    """Handoff artifact contract tests."""

    def test_deterministic_artifact_id(self) -> None:
        """Same inputs -> same artifact ID."""
        id1 = compute_handoff_artifact_id(
            "sess_1", "open_day_brief", "2026-04-17T06:00:00Z"
        )
        id2 = compute_handoff_artifact_id(
            "sess_1", "open_day_brief", "2026-04-17T06:00:00Z"
        )
        assert id1 == id2
        assert id1.startswith("hda_")

    def test_open_day_brief_build(self) -> None:
        """Open-day briefing artifact is built from state."""
        state: dict = {
            "execution_result:exec_1": {
                "status": "completed",
                "completed_at": "2026-04-17T05:00:00Z",
            },
            "execution_result:exec_2": {
                "status": "failed",
                "completed_at": "2026-04-17T05:30:00Z",
            },
            "active_intent.int_1": {"status": "active"},
        }
        artifact = build_open_day_handoff_artifact(
            state,
            "sess_1",
            "2026-04-17T06:00:00Z",
        )
        assert artifact.artifact_kind == ARTIFACT_KIND_OPEN_DAY_BRIEF
        assert len(artifact.completed_items) == 1
        assert len(artifact.failed_items) == 1
        assert len(artifact.open_items) == 1
        assert (
            "review" in artifact.next_recommended_action
            or "resolve" in artifact.next_recommended_action
        )

    def test_close_day_handoff_build(self) -> None:
        """Close-day handoff artifact is built from state."""
        state: dict = {
            "execution_result:exec_1": {
                "status": "completed",
                "completed_at": "2026-04-17T18:00:00Z",
            },
            "active_intent.int_1": {"status": "pending"},
        }
        artifact = build_close_day_handoff_artifact(
            state,
            "sess_1",
            "2026-04-17T22:00:00Z",
        )
        assert artifact.artifact_kind == ARTIFACT_KIND_CLOSE_DAY_HANDOFF
        assert len(artifact.completed_items) == 1
        assert len(artifact.open_items) == 1

    def test_bounded_recent_listing(self) -> None:
        """Recent listing is bounded by limit parameter."""
        state: dict = {}
        for i in range(25):
            ts = f"2026-04-17T{i:02d}:00:00Z"
            artifact = build_open_day_handoff_artifact(state, "sess_1", ts)
            for m in handoff_artifact_to_mutations(artifact):
                state[m["key"]] = m["value"]

        # Default limit = 20
        recent = list_recent_handoff_artifacts(state, "sess_1")
        assert len(recent) <= 20

        # Custom limit
        recent5 = list_recent_handoff_artifacts(state, "sess_1", limit=5)
        assert len(recent5) <= 5

    def test_mutation_builders_deterministic(self) -> None:
        """Same artifact produces same mutations."""
        artifact = build_open_day_handoff_artifact(
            {},
            "sess_1",
            "2026-04-17T06:00:00Z",
        )
        m1 = handoff_artifact_to_mutations(artifact)
        m2 = handoff_artifact_to_mutations(artifact)
        assert m1 == m2

    def test_load_round_trip(self) -> None:
        """Artifact survives persist -> load round trip."""
        artifact = build_open_day_handoff_artifact(
            {},
            "sess_1",
            "2026-04-17T06:00:00Z",
        )
        state: dict = {}
        for m in handoff_artifact_to_mutations(artifact):
            state[m["key"]] = m["value"]

        loaded = load_handoff_artifact(state, artifact.artifact_id)
        assert loaded is not None
        assert loaded.artifact_id == artifact.artifact_id
        assert loaded.artifact_kind == ARTIFACT_KIND_OPEN_DAY_BRIEF
        assert loaded.runtime_session_id == "sess_1"

    def test_load_missing_returns_none(self) -> None:
        """Loading nonexistent artifact returns None."""
        assert load_handoff_artifact({}, "nonexistent") is None

    def test_mutations_set_only(self) -> None:
        """All handoff artifact mutations use SET op."""
        artifact = build_close_day_handoff_artifact(
            {},
            "sess_1",
            "2026-04-17T22:00:00Z",
        )
        for m in handoff_artifact_to_mutations(artifact):
            assert m["op"] == "SET"

    def test_frozen_dataclass(self) -> None:
        """HandoffArtifact is frozen."""
        artifact = build_open_day_handoff_artifact(
            {},
            "sess_1",
            "2026-04-17T06:00:00Z",
        )
        try:
            artifact.title = "changed"  # type: ignore[misc]
            assert False
        except AttributeError:
            pass


# ===================================================================
# E. Workstation Profile Contract
# ===================================================================


class TestWorkstationProfileContract:
    """Workstation profile contract tests."""

    def test_deterministic_binding_id(self) -> None:
        """Same inputs -> same binding ID."""
        id1 = compute_workstation_binding_id("sess_1", "prof_abc", "discord")
        id2 = compute_workstation_binding_id("sess_1", "prof_abc", "discord")
        assert id1 == id2
        assert id1.startswith("wpb_")

    def test_deterministic_activation_id(self) -> None:
        """Same inputs -> same activation ID."""
        id1 = compute_workstation_activation_id(
            "sess_1", "bind_1", "2026-04-17T06:00:00Z"
        )
        id2 = compute_workstation_activation_id(
            "sess_1", "bind_1", "2026-04-17T06:00:00Z"
        )
        assert id1 == id2
        assert id1.startswith("wpa_")

    def test_protocol_importability(self) -> None:
        """WorkstationRuntimeAdapter protocol is importable and usable."""
        assert WorkstationRuntimeAdapter is not None

        # Verify it's a Protocol by checking it has the expected methods
        assert hasattr(WorkstationRuntimeAdapter, "activate_profile")
        assert hasattr(WorkstationRuntimeAdapter, "suspend_profile")
        assert hasattr(WorkstationRuntimeAdapter, "restore_profile")

    def test_activation_request_shape(self) -> None:
        """Activation request has all expected fields."""
        req = build_workstation_activation_request(
            runtime_session_id="sess_1",
            binding_id="bind_1",
            trigger_type=TRIGGER_MANUAL,
            entry_transport="discord",
            requested_at="2026-04-17T06:00:00Z",
        )
        assert req.trigger_type == TRIGGER_MANUAL
        assert req.entry_transport == "discord"
        assert req.binding_id == "bind_1"
        assert req.runtime_session_id == "sess_1"

        d = req.to_dict()
        restored = WorkstationActivationRequest.from_dict(d)
        assert restored.activation_id == req.activation_id
        assert restored.trigger_type == TRIGGER_MANUAL

    def test_trigger_types_preserved(self) -> None:
        """All trigger type constants are correct."""
        assert TRIGGER_MANUAL == "manual"
        assert TRIGGER_WAKE_PHRASE == "wake_phrase"
        assert TRIGGER_CLAP == "clap"
        assert TRIGGER_REMOTE_COMMAND == "remote_command"

    def test_binding_build_and_load(self) -> None:
        """Binding can be built, persisted, and loaded."""
        binding = build_workstation_profile_binding(
            runtime_session_id="sess_1",
            profile_id="prof_abc",
            transport="discord",
            startup_actions=("open_ide", "load_context"),
            continuity_policy="resume_last",
            execution_policy="sequential",
        )
        assert binding.binding_id.startswith("wpb_")
        assert binding.startup_actions == ("open_ide", "load_context")

        state: dict = {}
        for m in binding_to_mutations(binding):
            state[m["key"]] = m["value"]

        loaded = load_workstation_profile_binding(state, binding.binding_id)
        assert loaded is not None
        assert loaded.profile_id == "prof_abc"
        assert loaded.startup_actions == ("open_ide", "load_context")

    def test_no_external_logic_leakage(self) -> None:
        """Workstation module does not import Discord/Notion/Voicebox."""
        import umh.substrate.workstation_profile_contract as mod

        source = open(mod.__file__).read()
        for forbidden in [
            "discord",
            "notion",
            "voicebox",
            "obs",
            "vscode",
            "subprocess",
        ]:
            # Allow 'discord' only in comments/docstrings about transport names
            lines = source.split("\n")
            for line in lines:
                stripped = line.strip()
                if (
                    stripped.startswith("#")
                    or stripped.startswith('"""')
                    or stripped.startswith("'")
                ):
                    continue
                if f"import {forbidden}" in stripped.lower():
                    assert False, f"Found forbidden import: {forbidden}"

    def test_mutations_set_only(self) -> None:
        """Binding mutations use SET ops only."""
        binding = build_workstation_profile_binding(
            runtime_session_id="s",
            profile_id="p",
            transport="t",
        )
        for m in binding_to_mutations(binding):
            assert m["op"] == "SET"

    def test_frozen_dataclass(self) -> None:
        """WorkstationProfileBinding and WorkstationActivationRequest are frozen."""
        binding = build_workstation_profile_binding(
            runtime_session_id="s",
            profile_id="p",
            transport="t",
        )
        try:
            binding.transport = "x"  # type: ignore[misc]
            assert False
        except AttributeError:
            pass

        req = build_workstation_activation_request(
            runtime_session_id="s",
            binding_id="b",
            trigger_type="manual",
            entry_transport="t",
            requested_at="2026-04-17T06:00:00Z",
        )
        try:
            req.trigger_type = "clap"  # type: ignore[misc]
            assert False
        except AttributeError:
            pass


# ===================================================================
# F. Cross-Module Invariants
# ===================================================================


class TestInvariants:
    """Cross-module invariant enforcement."""

    def test_only_set_remove_mutations(self) -> None:
        """All mutation builders produce only SET or REMOVE ops."""
        # Presence
        ps = build_presence_state(
            runtime_session_id="s",
            presence="off",
            set_at="2026-04-17T00:00:00Z",
        )
        for m in build_presence_state_mutations(ps):
            assert m["op"] in ("SET", "REMOVE")

        # Profile
        profile = build_runtime_profile(
            name="x", default_mode="m", default_presence="p"
        )
        for m in build_runtime_profile_mutations(profile):
            assert m["op"] in ("SET", "REMOVE")

        # Handoff
        artifact = build_open_day_handoff_artifact({}, "s", "2026-04-17T00:00:00Z")
        for m in handoff_artifact_to_mutations(artifact):
            assert m["op"] in ("SET", "REMOVE")

        # Workstation binding
        binding = build_workstation_profile_binding(
            runtime_session_id="s",
            profile_id="p",
            transport="t",
        )
        for m in binding_to_mutations(binding):
            assert m["op"] in ("SET", "REMOVE")

    def test_no_list_mutation_ops(self) -> None:
        """No mutation uses APPEND, PUSH, or list-style ops."""
        all_mutations: list[dict] = []

        ps = build_presence_state(
            runtime_session_id="s",
            presence="off",
            set_at="2026-04-17T00:00:00Z",
        )
        all_mutations.extend(build_presence_state_mutations(ps))

        profile = build_runtime_profile(
            name="x", default_mode="m", default_presence="p"
        )
        all_mutations.extend(build_runtime_profile_mutations(profile))

        artifact = build_open_day_handoff_artifact({}, "s", "2026-04-17T00:00:00Z")
        all_mutations.extend(handoff_artifact_to_mutations(artifact))

        binding = build_workstation_profile_binding(
            runtime_session_id="s",
            profile_id="p",
            transport="t",
        )
        all_mutations.extend(binding_to_mutations(binding))

        forbidden_ops = {"APPEND", "PUSH", "INSERT", "ADD", "MERGE"}
        for m in all_mutations:
            assert m["op"] not in forbidden_ops, f"Found forbidden op: {m['op']}"

    def test_no_provider_imports(self) -> None:
        """New modules do not import Discord/Notion/Voicebox."""
        import umh.substrate.presence_state as ps_mod
        import umh.substrate.runtime_profile as rp_mod
        import umh.substrate.daily_rituals as dr_mod
        import umh.substrate.handoff_artifact as ha_mod
        import umh.substrate.workstation_profile_contract as wpc_mod

        for mod in [ps_mod, rp_mod, dr_mod, ha_mod, wpc_mod]:
            source = open(mod.__file__).read()
            for forbidden in ["discord_bot", "notion", "voicebox"]:
                assert f"import {forbidden}" not in source.lower(), (
                    f"{mod.__name__} imports {forbidden}"
                )

    def test_deterministic_replay(self) -> None:
        """Same inputs always produce identical mutations."""
        # Presence
        ps1 = build_presence_state(
            runtime_session_id="s",
            presence="off",
            set_at="2026-04-17T00:00:00Z",
        )
        ps2 = build_presence_state(
            runtime_session_id="s",
            presence="off",
            set_at="2026-04-17T00:00:00Z",
        )
        assert build_presence_state_mutations(ps1) == build_presence_state_mutations(
            ps2
        )

        # Profile
        p1 = build_runtime_profile(name="x", default_mode="m", default_presence="p")
        p2 = build_runtime_profile(name="x", default_mode="m", default_presence="p")
        # Profile IDs are deterministic on name, but created_at may differ
        # so we compare structure sans timestamps
        assert p1.profile_id == p2.profile_id

        # Handoff
        a1 = build_open_day_handoff_artifact({}, "s", "2026-04-17T00:00:00Z")
        a2 = build_open_day_handoff_artifact({}, "s", "2026-04-17T00:00:00Z")
        assert handoff_artifact_to_mutations(a1) == handoff_artifact_to_mutations(a2)

    def test_init_imports(self) -> None:
        """All new public APIs are importable from umh.substrate."""
        from umh.runtime_engine.substrate import (
            PRESENCE_OFF,
            PRESENCE_REMOTE_LIGHT,
            PRESENCE_ACTIVE_STATION,
            PRESENCE_DEEP_WORK,
            PRESENCE_OVERNIGHT_AUTONOMOUS,
            PresenceState,
            compute_presence_state_id,
            build_presence_state,
            build_presence_state_mutations,
            load_presence_state,
            set_human_presence,
            summarize_presence_state,
        )
        from umh.runtime_engine.substrate import (
            RuntimeProfile,
            compute_runtime_profile_id,
            build_runtime_profile,
            build_runtime_profile_mutations,
            load_runtime_profile,
            list_runtime_profiles,
        )
        from umh.runtime_engine.substrate import (
            OpenDayRequest,
            CloseDayRequest,
            OpenDayPlan,
            CloseDayPlan,
            CANONICAL_OPEN_STEPS,
            CANONICAL_CLOSE_STEPS,
            build_open_day_request,
            build_close_day_request,
            build_open_day_plan,
            build_close_day_plan,
            summarize_open_day_plan,
            summarize_close_day_plan,
        )
        from umh.runtime_engine.substrate import (
            HandoffArtifact,
            compute_handoff_artifact_id,
            build_open_day_handoff_artifact,
            build_close_day_handoff_artifact,
            handoff_artifact_to_mutations,
            load_handoff_artifact,
            list_recent_handoff_artifacts,
        )
        from umh.runtime_engine.substrate import (
            WorkstationProfileBinding,
            WorkstationActivationRequest,
            WorkstationRuntimeAdapter,
            compute_workstation_binding_id,
            compute_workstation_activation_id,
            build_workstation_profile_binding,
            build_workstation_activation_request,
            binding_to_mutations,
            load_workstation_profile_binding,
        )

        # If we got here, all imports worked
        assert True


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
