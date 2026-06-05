"""Phase 14.11B — Dual mode taxonomy + resolver tests.

Tests lifecycle modes, profile modes, dual composition,
resolver upgrade, and risk ceiling derivation.
"""

from __future__ import annotations

import sys
sys.path.insert(0, "/opt/OS")

import pytest

from substrate.workstation.lifecycle_modes import (
    LIFECYCLE_RISK_CEILING,
    LifecycleMode,
)
from substrate.workstation.profile_modes import ProfileMode
from substrate.workstation.mode_resolver import (
    _derive_lifecycle_mode,
    _derive_posture,
    _derive_risk_ceiling,
    resolve_composite_mode,
)


class TestLifecycleModeEnum:
    def test_all_modes_present(self) -> None:
        expected = {
            "day_cycle", "night_cycle", "overnight", "maintenance",
            "idle", "away", "remote_work", "end_of_workday", "emergency",
        }
        actual = {m.value for m in LifecycleMode}
        assert actual == expected

    def test_count(self) -> None:
        assert len(LifecycleMode) == 9

    def test_str_enum(self) -> None:
        assert LifecycleMode.DAY_CYCLE == "day_cycle"
        assert isinstance(LifecycleMode.EMERGENCY, str)

    def test_risk_ceiling_coverage(self) -> None:
        for mode in LifecycleMode:
            assert mode in LIFECYCLE_RISK_CEILING, f"{mode} missing risk ceiling"

    def test_day_cycle_high_risk(self) -> None:
        assert LIFECYCLE_RISK_CEILING[LifecycleMode.DAY_CYCLE] == "HIGH"

    def test_night_cycle_low_risk(self) -> None:
        assert LIFECYCLE_RISK_CEILING[LifecycleMode.NIGHT_CYCLE] == "LOW"

    def test_emergency_critical_risk(self) -> None:
        assert LIFECYCLE_RISK_CEILING[LifecycleMode.EMERGENCY] == "CRITICAL"


class TestProfileModeEnum:
    def test_all_modes_present(self) -> None:
        expected = {
            "developer", "research", "music", "design",
            "content", "command_center", "finance", "learning",
        }
        actual = {m.value for m in ProfileMode}
        assert actual == expected

    def test_count(self) -> None:
        assert len(ProfileMode) == 8

    def test_str_enum(self) -> None:
        assert ProfileMode.DEVELOPER == "developer"
        assert isinstance(ProfileMode.MUSIC, str)


class TestDualComposition:
    def test_lifecycle_and_profile_are_orthogonal(self) -> None:
        lifecycle_values = {m.value for m in LifecycleMode}
        profile_values = {m.value for m in ProfileMode}
        overlap = lifecycle_values & profile_values
        assert overlap == set(), f"Overlap: {overlap}"

    def test_simultaneous_modes_in_resolver(self) -> None:
        result = resolve_composite_mode(
            continuity_state="active",
            lifecycle_mode="day_cycle",
            active_profile_modes=["developer", "research"],
        )
        assert result["lifecycle_mode"] == "day_cycle"
        assert result["active_profile_modes"] == ["developer", "research"]
        assert result["continuity_state"] == "active"

    def test_night_cycle_with_developer(self) -> None:
        result = resolve_composite_mode(
            continuity_state="night_sleeping",
            lifecycle_mode="night_cycle",
            active_profile_modes=["developer"],
        )
        assert result["lifecycle_mode"] == "night_cycle"
        assert result["active_profile_modes"] == ["developer"]
        assert result["risk_ceiling"] == "LOW"


class TestResolverUpgrade:
    def test_14_11a_fields_preserved(self) -> None:
        result = resolve_composite_mode()
        assert "operator_day_mode" in result
        assert "operational_mode" in result
        assert "station_presence_mode" in result
        assert "operator_mode" in result
        assert "effective_posture" in result

    def test_14_11b_fields_added(self) -> None:
        result = resolve_composite_mode()
        assert "continuity_state" in result
        assert "lifecycle_mode" in result
        assert "active_profile_modes" in result
        assert "risk_ceiling" in result

    def test_default_continuity_is_active(self) -> None:
        result = resolve_composite_mode()
        assert result["continuity_state"] == "active"

    def test_default_profile_is_developer(self) -> None:
        result = resolve_composite_mode()
        assert result["active_profile_modes"] == ["developer"]

    def test_default_lifecycle_is_day_cycle(self) -> None:
        result = resolve_composite_mode()
        assert result["lifecycle_mode"] == "day_cycle"

    def test_explicit_override_continuity(self) -> None:
        result = resolve_composite_mode(continuity_state="away")
        assert result["continuity_state"] == "away"


class TestDeriveLifecycleMode:
    def test_night_sleeping_maps_to_night_cycle(self) -> None:
        modes = {
            "continuity_state": "night_sleeping",
            "operator_day_mode": {"mode": "overnight"},
        }
        assert _derive_lifecycle_mode(modes) == "night_cycle"

    def test_away_maps_to_away(self) -> None:
        modes = {
            "continuity_state": "away",
            "operator_day_mode": {"mode": "unknown"},
        }
        assert _derive_lifecycle_mode(modes) == "away"

    def test_remote_maps_to_remote_work(self) -> None:
        modes = {
            "continuity_state": "remote",
            "operator_day_mode": {"mode": "unknown"},
        }
        assert _derive_lifecycle_mode(modes) == "remote_work"

    def test_idle_maps_to_idle(self) -> None:
        modes = {
            "continuity_state": "idle",
            "operator_day_mode": {"mode": "unknown"},
        }
        assert _derive_lifecycle_mode(modes) == "idle"

    def test_active_defaults_to_day_cycle(self) -> None:
        modes = {
            "continuity_state": "active",
            "operator_day_mode": {"mode": "local_active"},
        }
        assert _derive_lifecycle_mode(modes) == "day_cycle"

    def test_extended_absence_maps_to_overnight(self) -> None:
        modes = {
            "continuity_state": "extended_absence",
            "operator_day_mode": {"mode": "unknown"},
        }
        assert _derive_lifecycle_mode(modes) == "overnight"


class TestRiskCeiling:
    def test_day_cycle_high(self) -> None:
        assert _derive_risk_ceiling("day_cycle") == "HIGH"

    def test_night_cycle_low(self) -> None:
        assert _derive_risk_ceiling("night_cycle") == "LOW"

    def test_emergency_critical(self) -> None:
        assert _derive_risk_ceiling("emergency") == "CRITICAL"

    def test_unknown_defaults_low(self) -> None:
        assert _derive_risk_ceiling("bogus") == "LOW"

    def test_remote_work_medium(self) -> None:
        assert _derive_risk_ceiling("remote_work") == "MEDIUM"
