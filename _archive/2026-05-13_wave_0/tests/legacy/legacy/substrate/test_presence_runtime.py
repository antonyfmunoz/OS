"""Tests for presence_runtime — presence modes, work profiles, bootstrap."""

import sys

import pytest

sys.path.insert(0, "/opt/OS")


# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _reset_state():
    """Reset cached state between tests."""
    from umh.substrate.presence_runtime import reset_for_tests

    reset_for_tests()
    yield
    reset_for_tests()


# ─── Presence Mode Tests ────────────────────────────────────────────────────


class TestPresenceMode:
    def test_all_four_modes_exist(self):
        from umh.substrate.presence_runtime import PresenceMode

        assert PresenceMode.ACTIVE_LOCAL.value == "active_local"
        assert PresenceMode.AWAY_LOCAL.value == "away_local"
        assert PresenceMode.REMOTE_ACTIVE.value == "remote_active"
        assert PresenceMode.OVERNIGHT.value == "overnight"

    def test_modes_are_string_enum(self):
        from umh.substrate.presence_runtime import PresenceMode

        assert isinstance(PresenceMode.ACTIVE_LOCAL, str)
        assert PresenceMode.ACTIVE_LOCAL == "active_local"


class TestPresenceBehavior:
    def test_active_local_allows_interruptions(self):
        from umh.substrate.presence_runtime import (
            PRESENCE_BEHAVIORS,
            PresenceMode,
        )

        b = PRESENCE_BEHAVIORS[PresenceMode.ACTIVE_LOCAL]
        assert b.allow_interruptions is True
        assert b.prefer_local_routing is True
        assert b.tts_eligible is True
        assert b.suppress_non_critical is False
        assert b.routing_hint == "local"

    def test_away_local_suppresses(self):
        from umh.substrate.presence_runtime import (
            PRESENCE_BEHAVIORS,
            PresenceMode,
        )

        b = PRESENCE_BEHAVIORS[PresenceMode.AWAY_LOCAL]
        assert b.allow_interruptions is False
        assert b.suppress_non_critical is True
        assert b.tts_eligible is False
        assert b.routing_hint == "vps"

    def test_remote_active_no_local(self):
        from umh.substrate.presence_runtime import (
            PRESENCE_BEHAVIORS,
            PresenceMode,
        )

        b = PRESENCE_BEHAVIORS[PresenceMode.REMOTE_ACTIVE]
        assert b.prefer_local_routing is False
        assert b.allow_interruptions is True
        assert b.routing_hint == "vps"

    def test_overnight_auto_execute(self):
        from umh.substrate.presence_runtime import (
            PRESENCE_BEHAVIORS,
            PresenceMode,
        )

        b = PRESENCE_BEHAVIORS[PresenceMode.OVERNIGHT]
        assert b.auto_execute_overnight is True
        assert b.allow_interruptions is False
        assert b.suppress_non_critical is True

    def test_behavior_to_dict(self):
        from umh.substrate.presence_runtime import (
            PRESENCE_BEHAVIORS,
            PresenceMode,
        )

        d = PRESENCE_BEHAVIORS[PresenceMode.ACTIVE_LOCAL].to_dict()
        assert d["mode"] == "active_local"
        assert isinstance(d["allow_interruptions"], bool)

    def test_behavior_is_frozen(self):
        from umh.substrate.presence_runtime import (
            PRESENCE_BEHAVIORS,
            PresenceMode,
        )

        b = PRESENCE_BEHAVIORS[PresenceMode.ACTIVE_LOCAL]
        with pytest.raises(AttributeError):
            b.allow_interruptions = False  # type: ignore[misc]

    def test_every_mode_has_behavior(self):
        from umh.substrate.presence_runtime import (
            PRESENCE_BEHAVIORS,
            PresenceMode,
        )

        for mode in PresenceMode:
            assert mode in PRESENCE_BEHAVIORS


# ─── Work Profile Tests ────────────────────────────────────────────────────


class TestWorkProfile:
    def test_builder_profile(self):
        from umh.substrate.presence_runtime import (
            PROFILE_BEHAVIORS,
            WorkProfile,
        )

        b = PROFILE_BEHAVIORS[WorkProfile.BUILDER]
        assert b.default_workspace == "builder"
        assert b.default_scene == "builder_mode"
        assert "code" in b.focus_areas
        assert b.routing_bias == "local"

    def test_product_profile(self):
        from umh.substrate.presence_runtime import (
            PROFILE_BEHAVIORS,
            WorkProfile,
        )

        b = PROFILE_BEHAVIORS[WorkProfile.PRODUCT]
        assert b.default_workspace == "product"
        assert b.default_scene == "operator_mode"
        assert "outreach" in b.focus_areas
        assert b.routing_bias == "vps"

    def test_profile_behavior_to_dict(self):
        from umh.substrate.presence_runtime import (
            PROFILE_BEHAVIORS,
            WorkProfile,
        )

        d = PROFILE_BEHAVIORS[WorkProfile.BUILDER].to_dict()
        assert d["profile"] == "builder"
        assert isinstance(d["focus_areas"], list)

    def test_profile_is_frozen(self):
        from umh.substrate.presence_runtime import (
            PROFILE_BEHAVIORS,
            WorkProfile,
        )

        b = PROFILE_BEHAVIORS[WorkProfile.BUILDER]
        with pytest.raises(AttributeError):
            b.routing_bias = "remote"  # type: ignore[misc]


# ─── Composed State Tests ──────────────────────────────────────────────────


class TestOperatorRuntimeState:
    def test_defaults(self):
        from umh.substrate.presence_runtime import OperatorRuntimeState

        state = OperatorRuntimeState()
        assert state.presence.value == "remote_active"
        assert state.profile.value == "builder"

    def test_effective_routing_presence_overrides(self):
        from umh.substrate.presence_runtime import (
            OperatorRuntimeState,
            PresenceMode,
            WorkProfile,
        )

        # ACTIVE_LOCAL has routing_hint="local", which overrides profile
        state = OperatorRuntimeState(
            presence=PresenceMode.ACTIVE_LOCAL,
            profile=WorkProfile.PRODUCT,
        )
        assert state.effective_routing == "local"

    def test_effective_workspace_from_profile(self):
        from umh.substrate.presence_runtime import (
            OperatorRuntimeState,
            PresenceMode,
            WorkProfile,
        )

        state = OperatorRuntimeState(
            presence=PresenceMode.REMOTE_ACTIVE,
            profile=WorkProfile.PRODUCT,
        )
        assert state.effective_workspace == "product"
        assert state.effective_scene == "operator_mode"

    def test_to_dict_structure(self):
        from umh.substrate.presence_runtime import OperatorRuntimeState

        d = OperatorRuntimeState().to_dict()
        assert "presence" in d
        assert "profile" in d
        assert "behavior" in d
        assert "profile_behavior" in d
        assert "effective_routing" in d
        assert "effective_workspace" in d
        assert "effective_scene" in d


# ─── Control API Tests ─────────────────────────────────────────────────────


class TestControlAPI:
    def test_set_presence(self):
        from umh.substrate.presence_runtime import (
            PresenceMode,
            set_presence,
        )

        state = set_presence(PresenceMode.ACTIVE_LOCAL)
        assert state.presence == PresenceMode.ACTIVE_LOCAL

    def test_set_presence_with_profile(self):
        from umh.substrate.presence_runtime import (
            PresenceMode,
            WorkProfile,
            set_presence,
        )

        state = set_presence(PresenceMode.OVERNIGHT, profile=WorkProfile.PRODUCT)
        assert state.presence == PresenceMode.OVERNIGHT
        assert state.profile == WorkProfile.PRODUCT

    def test_set_profile_preserves_presence(self):
        from umh.substrate.presence_runtime import (
            PresenceMode,
            WorkProfile,
            set_presence,
            set_profile,
        )

        set_presence(PresenceMode.ACTIVE_LOCAL)
        state = set_profile(WorkProfile.PRODUCT)
        assert state.presence == PresenceMode.ACTIVE_LOCAL
        assert state.profile == WorkProfile.PRODUCT

    def test_get_runtime_returns_state(self):
        from umh.substrate.presence_runtime import (
            PresenceMode,
            get_runtime,
            set_presence,
        )

        set_presence(PresenceMode.OVERNIGHT)
        state = get_runtime()
        assert state.presence == PresenceMode.OVERNIGHT


# ─── Bootstrap Tests ────────────────────────────────────────────────────────


class TestBootstrap:
    def test_builder_local_bootstrap(self):
        from umh.substrate.presence_runtime import (
            OperatorRuntimeState,
            PresenceMode,
            WorkProfile,
            resolve_bootstrap,
        )

        state = OperatorRuntimeState(
            presence=PresenceMode.ACTIVE_LOCAL,
            profile=WorkProfile.BUILDER,
        )
        reqs = resolve_bootstrap(state)
        assert reqs.user_scene == "builder_mode"
        assert "vscode" in reqs.user_apps
        assert "github" in reqs.user_apps  # local routing adds github
        assert reqs.user_tts is True
        assert reqs.system_session_target == "local"
        assert reqs.system_ensure_git_clean is True

    def test_product_remote_bootstrap(self):
        from umh.substrate.presence_runtime import (
            OperatorRuntimeState,
            PresenceMode,
            WorkProfile,
            resolve_bootstrap,
        )

        state = OperatorRuntimeState(
            presence=PresenceMode.REMOTE_ACTIVE,
            profile=WorkProfile.PRODUCT,
        )
        reqs = resolve_bootstrap(state)
        assert reqs.user_scene == "operator_mode"
        assert "discord" in reqs.user_apps
        assert "notion" in reqs.user_apps  # interruptions allowed
        assert reqs.user_tts is False
        assert reqs.system_session_target == "vps"
        assert reqs.system_ensure_crm_accessible is True

    def test_overnight_minimal_bootstrap(self):
        from umh.substrate.presence_runtime import (
            OperatorRuntimeState,
            PresenceMode,
            WorkProfile,
            resolve_bootstrap,
        )

        state = OperatorRuntimeState(
            presence=PresenceMode.OVERNIGHT,
            profile=WorkProfile.BUILDER,
        )
        reqs = resolve_bootstrap(state)
        assert reqs.user_scene == "overnight"
        assert reqs.user_apps == []
        assert reqs.user_tts is False
        assert reqs.user_wake is False

    def test_away_local_disables_voice(self):
        from umh.substrate.presence_runtime import (
            OperatorRuntimeState,
            PresenceMode,
            WorkProfile,
            resolve_bootstrap,
        )

        state = OperatorRuntimeState(
            presence=PresenceMode.AWAY_LOCAL,
            profile=WorkProfile.BUILDER,
        )
        reqs = resolve_bootstrap(state)
        assert reqs.user_tts is False
        assert reqs.user_wake is False

    def test_bootstrap_to_dict(self):
        from umh.substrate.presence_runtime import (
            BootstrapRequirements,
        )

        reqs = BootstrapRequirements(user_scene="test")
        d = reqs.to_dict()
        assert "user_facing" in d
        assert "system_required" in d
        assert d["user_facing"]["scene"] == "test"
        assert d["system_required"]["check_node_health"] is True


# ─── Lifecycle Modifier Tests ──────────────────────────────────────────────


class TestLifecycleModifiers:
    def test_modifiers_reflect_state(self):
        from umh.substrate.presence_runtime import (
            OperatorRuntimeState,
            PresenceMode,
            WorkProfile,
            get_lifecycle_modifiers,
        )

        state = OperatorRuntimeState(
            presence=PresenceMode.ACTIVE_LOCAL,
            profile=WorkProfile.BUILDER,
        )
        mods = get_lifecycle_modifiers(state)
        assert mods["presence_mode"] == "active_local"
        assert mods["work_profile"] == "builder"
        assert mods["workspace"] == "builder"
        assert mods["routing"] == "local"
        assert mods["lifecycle_modifier"] == "full_capability"
        assert "code" in mods["focus_areas"]


# ─── Continuity Integration Tests ──────────────────────────────────────────


class TestContinuityIntegration:
    def test_presence_for_continuity(self):
        from umh.substrate.presence_runtime import (
            PresenceMode,
            presence_for_continuity,
            set_presence,
        )

        set_presence(PresenceMode.ACTIVE_LOCAL)
        info = presence_for_continuity()
        assert info["presence_mode"] == "active_local"
        assert info["effective_routing"] == "local"
        assert info["tts_eligible"] is True
        assert "resolved_at" in info
