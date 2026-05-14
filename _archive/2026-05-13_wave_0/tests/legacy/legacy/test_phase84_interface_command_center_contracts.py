"""Phase 84 — Interface Layer + Command Center Contracts v1 tests.

170+ tests covering surface contracts, command envelopes, events,
state machine, voice-wave, approvals, notifications, surface registry,
interface safety, command center snapshot, registry/observability/API/CLI
integration, layering invariants, and regression.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, "/opt/OS")


# ── Section 1: Surface Contracts ──────────────────────────────────


class TestInterfaceSurfaceTypeNormalization(unittest.TestCase):
    def test_known_values(self):
        from umh.interface.surfaces import InterfaceSurfaceType, normalize_surface_type

        self.assertEqual(
            normalize_surface_type("command_center"), InterfaceSurfaceType.COMMAND_CENTER
        )
        self.assertEqual(normalize_surface_type("cli"), InterfaceSurfaceType.CLI)
        self.assertEqual(normalize_surface_type("telegram"), InterfaceSurfaceType.TELEGRAM)

    def test_unknown_degrades(self):
        from umh.interface.surfaces import InterfaceSurfaceType, normalize_surface_type

        self.assertEqual(normalize_surface_type("nonexistent"), InterfaceSurfaceType.UNKNOWN)


class TestInterfacePlatformNormalization(unittest.TestCase):
    def test_known_values(self):
        from umh.interface.surfaces import InterfacePlatform, normalize_platform

        self.assertEqual(normalize_platform("ios"), InterfacePlatform.IOS)
        self.assertEqual(normalize_platform("windows"), InterfacePlatform.WINDOWS)

    def test_unknown_degrades(self):
        from umh.interface.surfaces import InterfacePlatform, normalize_platform

        self.assertEqual(normalize_platform("webos"), InterfacePlatform.UNKNOWN)


class TestInterfaceSurfaceStatusNormalization(unittest.TestCase):
    def test_known_values(self):
        from umh.interface.surfaces import InterfaceSurfaceStatus, normalize_surface_status

        self.assertEqual(normalize_surface_status("available"), InterfaceSurfaceStatus.AVAILABLE)
        self.assertEqual(normalize_surface_status("future"), InterfaceSurfaceStatus.FUTURE)

    def test_unknown_degrades(self):
        from umh.interface.surfaces import InterfaceSurfaceStatus, normalize_surface_status

        self.assertEqual(normalize_surface_status("bogus"), InterfaceSurfaceStatus.UNKNOWN)


class TestInterfaceCapabilityNormalization(unittest.TestCase):
    def test_known_values(self):
        from umh.interface.surfaces import InterfaceCapability, normalize_interface_capability

        self.assertEqual(
            normalize_interface_capability("display_state"), InterfaceCapability.DISPLAY_STATE
        )
        self.assertEqual(
            normalize_interface_capability("execution_intent"), InterfaceCapability.EXECUTION_INTENT
        )

    def test_unknown_degrades(self):
        from umh.interface.surfaces import InterfaceCapability, normalize_interface_capability

        self.assertEqual(normalize_interface_capability("fly"), InterfaceCapability.UNKNOWN)


class TestInterfaceSurfaceSerialization(unittest.TestCase):
    def test_roundtrip(self):
        from umh.interface.surfaces import (
            InterfaceSurface,
            InterfaceSurfaceType,
            create_interface_surface,
        )

        s = create_interface_surface("Test", surface_type=InterfaceSurfaceType.CLI)
        d = s.to_dict()
        s2 = InterfaceSurface.from_dict(d)
        self.assertEqual(s.surface_id, s2.surface_id)
        self.assertEqual(s.name, s2.name)


class TestSurfaceCapabilityMatrixSerialization(unittest.TestCase):
    def test_serializes(self):
        from umh.interface.surfaces import (
            InterfaceSurfaceType,
            build_surface_capability_matrix,
            create_interface_surface,
        )

        s = create_interface_surface(
            "X", surface_type=InterfaceSurfaceType.CLI, capabilities=["display_state"]
        )
        m = build_surface_capability_matrix(s)
        d = m.to_dict()
        self.assertIn("capabilities", d)
        self.assertIn("unsupported_capabilities", d)


class TestDefaultSurfacesExist(unittest.TestCase):
    def test_defaults_not_empty(self):
        from umh.interface.surfaces import get_default_interface_surfaces

        surfaces = get_default_interface_surfaces()
        self.assertGreater(len(surfaces), 0)

    def test_includes_command_center(self):
        from umh.interface.surfaces import InterfaceSurfaceType, get_default_interface_surfaces

        surfaces = get_default_interface_surfaces()
        types = [s.surface_type for s in surfaces]
        self.assertIn(InterfaceSurfaceType.COMMAND_CENTER, types)

    def test_includes_desktop_overlay(self):
        from umh.interface.surfaces import InterfaceSurfaceType, get_default_interface_surfaces

        types = [s.surface_type for s in get_default_interface_surfaces()]
        self.assertIn(InterfaceSurfaceType.DESKTOP_OVERLAY, types)

    def test_includes_floating_operator(self):
        from umh.interface.surfaces import InterfaceSurfaceType, get_default_interface_surfaces

        types = [s.surface_type for s in get_default_interface_surfaces()]
        self.assertIn(InterfaceSurfaceType.FLOATING_OPERATOR, types)

    def test_includes_minimized_voice_wave(self):
        from umh.interface.surfaces import InterfaceSurfaceType, get_default_interface_surfaces

        types = [s.surface_type for s in get_default_interface_surfaces()]
        self.assertIn(InterfaceSurfaceType.MINIMIZED_VOICE_WAVE, types)

    def test_includes_ghost_mode(self):
        from umh.interface.surfaces import InterfaceSurfaceType, get_default_interface_surfaces

        types = [s.surface_type for s in get_default_interface_surfaces()]
        self.assertIn(InterfaceSurfaceType.GHOST_MODE, types)

    def test_includes_voice_interface(self):
        from umh.interface.surfaces import InterfaceSurfaceType, get_default_interface_surfaces

        types = [s.surface_type for s in get_default_interface_surfaces()]
        self.assertIn(InterfaceSurfaceType.VOICE_INTERFACE, types)

    def test_includes_telegram(self):
        from umh.interface.surfaces import InterfaceSurfaceType, get_default_interface_surfaces

        types = [s.surface_type for s in get_default_interface_surfaces()]
        self.assertIn(InterfaceSurfaceType.TELEGRAM, types)

    def test_includes_discord(self):
        from umh.interface.surfaces import InterfaceSurfaceType, get_default_interface_surfaces

        types = [s.surface_type for s in get_default_interface_surfaces()]
        self.assertIn(InterfaceSurfaceType.DISCORD, types)

    def test_includes_cli(self):
        from umh.interface.surfaces import InterfaceSurfaceType, get_default_interface_surfaces

        types = [s.surface_type for s in get_default_interface_surfaces()]
        self.assertIn(InterfaceSurfaceType.CLI, types)

    def test_includes_api(self):
        from umh.interface.surfaces import InterfaceSurfaceType, get_default_interface_surfaces

        types = [s.surface_type for s in get_default_interface_surfaces()]
        self.assertIn(InterfaceSurfaceType.API, types)


class TestIOSSurfaceLimitations(unittest.TestCase):
    def test_ios_no_global_overlay(self):
        from umh.interface.surfaces import InterfacePlatform, get_default_interface_surfaces

        ios_surfaces = [
            s for s in get_default_interface_surfaces() if s.platform == InterfacePlatform.IOS
        ]
        all_limitations = []
        for s in ios_surfaces:
            all_limitations.extend(s.limitations)
        combined = " ".join(all_limitations).lower()
        self.assertIn("no true global overlay", combined)

    def test_ios_no_siri_replacement(self):
        from umh.interface.surfaces import InterfacePlatform, get_default_interface_surfaces

        ios_surfaces = [
            s for s in get_default_interface_surfaces() if s.platform == InterfacePlatform.IOS
        ]
        all_limitations = []
        for s in ios_surfaces:
            all_limitations.extend(s.limitations)
        combined = " ".join(all_limitations).lower()
        self.assertIn("no siri replacement", combined)


class TestCommandCenterCapabilities(unittest.TestCase):
    def test_supports_dashboard_approvals_traces(self):
        from umh.interface.surfaces import (
            InterfaceCapability,
            InterfaceSurfaceType,
            get_default_interface_surfaces,
        )

        cc = [
            s
            for s in get_default_interface_surfaces()
            if s.surface_type == InterfaceSurfaceType.COMMAND_CENTER
        ][0]
        caps = cc.capabilities
        self.assertIn(InterfaceCapability.SHOW_DASHBOARD.value, caps)
        self.assertIn(InterfaceCapability.SHOW_APPROVALS.value, caps)
        self.assertIn(InterfaceCapability.SHOW_TRACES.value, caps)


class TestMinimizedVoiceWaveRepresentational(unittest.TestCase):
    def test_is_representational(self):
        from umh.interface.surfaces import InterfaceSurfaceType, get_default_interface_surfaces

        wave = [
            s
            for s in get_default_interface_surfaces()
            if s.surface_type == InterfaceSurfaceType.MINIMIZED_VOICE_WAVE
        ][0]
        combined = " ".join(wave.limitations).lower()
        self.assertIn("representational only", combined)


class TestUnknownSurfaceSafe(unittest.TestCase):
    def test_unknown_surface_does_not_crash(self):
        from umh.interface.surfaces import InterfaceSurfaceType, create_interface_surface

        s = create_interface_surface("Unknown", surface_type=InterfaceSurfaceType.UNKNOWN)
        d = s.to_dict()
        self.assertEqual(d["surface_type"], "unknown")


# ── Section 2: Command Envelope ───────────────────────────────────


class TestCommandTypeNormalization(unittest.TestCase):
    def test_known_values(self):
        from umh.interface.commands import InterfaceCommandType, normalize_command_type

        self.assertEqual(normalize_command_type("read_query"), InterfaceCommandType.READ_QUERY)
        self.assertEqual(
            normalize_command_type("execution_intent"), InterfaceCommandType.EXECUTION_INTENT
        )

    def test_unknown_degrades(self):
        from umh.interface.commands import InterfaceCommandType, normalize_command_type

        self.assertEqual(normalize_command_type("bogus"), InterfaceCommandType.UNKNOWN)


class TestCommandStatusNormalization(unittest.TestCase):
    def test_known(self):
        from umh.interface.commands import InterfaceCommandStatus, normalize_command_status

        self.assertEqual(normalize_command_status("validated"), InterfaceCommandStatus.VALIDATED)


class TestActionRiskNormalization(unittest.TestCase):
    def test_known(self):
        from umh.interface.commands import InterfaceActionRisk, normalize_action_risk

        self.assertEqual(normalize_action_risk("read_only"), InterfaceActionRisk.READ_ONLY)


class TestCommandEnvelopeSerialization(unittest.TestCase):
    def test_roundtrip(self):
        from umh.interface.commands import (
            InterfaceCommandEnvelope,
            InterfaceCommandType,
            create_command_envelope,
        )

        env = create_command_envelope("srf_test", InterfaceCommandType.READ_QUERY)
        d = env.to_dict()
        env2 = InterfaceCommandEnvelope.from_dict(d)
        self.assertEqual(env.command_id, env2.command_id)
        self.assertEqual(env.surface_id, env2.surface_id)


class TestReadQueryValidates(unittest.TestCase):
    def test_validates(self):
        from umh.interface.commands import (
            InterfaceCommandType,
            create_command_envelope,
            validate_interface_command,
        )

        env = create_command_envelope("srf_test", InterfaceCommandType.READ_QUERY)
        v = validate_interface_command(env)
        self.assertTrue(v.valid)


class TestExecutionIntentRequiresControlPlane(unittest.TestCase):
    def test_requires_control_plane(self):
        from umh.interface.commands import (
            InterfaceCommandType,
            create_command_envelope,
            validate_interface_command,
        )

        env = create_command_envelope("srf_test", InterfaceCommandType.EXECUTION_INTENT)
        v = validate_interface_command(env)
        self.assertTrue(v.requires_control_plane)


class TestApprovalResponseRoute(unittest.TestCase):
    def test_governance_route(self):
        from umh.interface.commands import (
            InterfaceCommandType,
            create_command_envelope,
            validate_interface_command,
        )

        env = create_command_envelope("srf_test", InterfaceCommandType.APPROVAL_RESPONSE)
        v = validate_interface_command(env)
        self.assertTrue(v.valid)
        self.assertTrue(v.requires_governance)


class TestUnknownCommandRejected(unittest.TestCase):
    def test_rejected(self):
        from umh.interface.commands import (
            InterfaceCommandType,
            create_command_envelope,
            validate_interface_command,
        )

        env = create_command_envelope("srf_test", InterfaceCommandType.UNKNOWN)
        v = validate_interface_command(env)
        self.assertFalse(v.valid)


class TestRouteReadQuery(unittest.TestCase):
    def test_routes_to_observability(self):
        from umh.interface.commands import (
            InterfaceCommandType,
            create_command_envelope,
            route_interface_command,
        )

        env = create_command_envelope("srf_test", InterfaceCommandType.READ_QUERY)
        r = route_interface_command(env)
        self.assertEqual(r.route_target, "observability")
        self.assertTrue(r.allowed)


class TestRouteExecutionIntent(unittest.TestCase):
    def test_routes_to_control_plane(self):
        from umh.interface.commands import (
            InterfaceCommandType,
            create_command_envelope,
            route_interface_command,
        )

        env = create_command_envelope("srf_test", InterfaceCommandType.EXECUTION_INTENT)
        r = route_interface_command(env)
        self.assertEqual(r.route_target, "control_plane")


class TestReadOnlyCommandMarked(unittest.TestCase):
    def test_read_only(self):
        from umh.interface.commands import InterfaceCommandType, create_command_envelope

        env = create_command_envelope("srf_test", InterfaceCommandType.READ_QUERY)
        self.assertTrue(env.read_only)


class TestValidationIncludesSurface(unittest.TestCase):
    def test_missing_surface_error(self):
        from umh.interface.commands import (
            InterfaceCommandType,
            create_command_envelope,
            validate_interface_command,
        )

        env = create_command_envelope("", InterfaceCommandType.READ_QUERY)
        v = validate_interface_command(env)
        self.assertFalse(v.valid)
        self.assertTrue(any("surface_id" in e.lower() for e in v.errors))


class TestNoCommandExecutes(unittest.TestCase):
    def test_execution_intent_does_not_execute(self):
        from umh.interface.commands import (
            InterfaceCommandType,
            create_command_envelope,
            route_interface_command,
        )

        env = create_command_envelope("srf_test", InterfaceCommandType.EXECUTION_INTENT)
        r = route_interface_command(env)
        self.assertEqual(r.route_target, "control_plane")


# ── Section 3: Events ─────────────────────────────────────────────


class TestEventTypeNormalization(unittest.TestCase):
    def test_known(self):
        from umh.interface.events import InterfaceEventType, normalize_event_type

        self.assertEqual(normalize_event_type("surface_opened"), InterfaceEventType.SURFACE_OPENED)

    def test_unknown(self):
        from umh.interface.events import InterfaceEventType, normalize_event_type

        self.assertEqual(normalize_event_type("xyz"), InterfaceEventType.UNKNOWN)


class TestEventSourceNormalization(unittest.TestCase):
    def test_known(self):
        from umh.interface.events import InterfaceEventSource, normalize_event_source

        self.assertEqual(normalize_event_source("user"), InterfaceEventSource.USER)


class TestInterfaceEventSerialization(unittest.TestCase):
    def test_roundtrip(self):
        from umh.interface.events import InterfaceEvent, InterfaceEventType, create_interface_event

        e = create_interface_event(InterfaceEventType.SURFACE_OPENED)
        d = e.to_dict()
        e2 = InterfaceEvent.from_dict(d)
        self.assertEqual(e.event_id, e2.event_id)


class TestEventBatchSerialization(unittest.TestCase):
    def test_serializes(self):
        from umh.interface.events import (
            InterfaceEventType,
            build_event_batch,
            create_interface_event,
        )

        events = [create_interface_event(InterfaceEventType.SURFACE_OPENED) for _ in range(3)]
        batch = build_event_batch(events)
        d = batch.to_dict()
        self.assertEqual(d["total"], 3)


class TestEventBatchLimitEnforced(unittest.TestCase):
    def test_truncates(self):
        from umh.interface.events import (
            InterfaceEventType,
            build_event_batch,
            create_interface_event,
        )

        events = [create_interface_event(InterfaceEventType.SURFACE_OPENED) for _ in range(150)]
        batch = build_event_batch(events, limit=100)
        self.assertEqual(batch.total, 100)
        self.assertTrue(len(batch.warnings) > 0)


class TestEventsReadOnly(unittest.TestCase):
    def test_read_only_flag(self):
        from umh.interface.events import InterfaceEventType, create_interface_event

        e = create_interface_event(InterfaceEventType.COMMAND_RECEIVED)
        self.assertTrue(e.read_only)


class TestUnknownEventSafe(unittest.TestCase):
    def test_unknown(self):
        from umh.interface.events import InterfaceEventType, create_interface_event

        e = create_interface_event(InterfaceEventType.UNKNOWN)
        self.assertEqual(e.event_type, InterfaceEventType.UNKNOWN)
        d = e.to_dict()
        self.assertIn("event_id", d)


# ── Section 4: State Machine ─────────────────────────────────────


class TestInterfaceModeNormalization(unittest.TestCase):
    def test_known(self):
        from umh.interface.state_machine import InterfaceMode, normalize_interface_mode

        self.assertEqual(normalize_interface_mode("full_screen"), InterfaceMode.FULL_SCREEN)

    def test_unknown(self):
        from umh.interface.state_machine import InterfaceMode, normalize_interface_mode

        self.assertEqual(normalize_interface_mode("xyz"), InterfaceMode.UNKNOWN)


class TestVisibilityNormalization(unittest.TestCase):
    def test_known(self):
        from umh.interface.state_machine import InterfaceVisibility, normalize_visibility

        self.assertEqual(normalize_visibility("visible"), InterfaceVisibility.VISIBLE)


class TestFocusStateNormalization(unittest.TestCase):
    def test_known(self):
        from umh.interface.state_machine import InterfaceFocusState, normalize_focus_state

        self.assertEqual(normalize_focus_state("active"), InterfaceFocusState.ACTIVE)


class TestTransitionStatusNormalization(unittest.TestCase):
    def test_known(self):
        from umh.interface.state_machine import (
            InterfaceTransitionStatus,
            normalize_transition_status,
        )

        self.assertEqual(normalize_transition_status("allowed"), InterfaceTransitionStatus.ALLOWED)


class TestInterfaceStateSerialization(unittest.TestCase):
    def test_serializes(self):
        from umh.interface.state_machine import InterfaceMode, create_interface_state

        s = create_interface_state(surface_id="srf_test", mode=InterfaceMode.FULL_SCREEN)
        d = s.to_dict()
        self.assertEqual(d["mode"], "full_screen")
        self.assertEqual(d["visibility"], "visible")


class TestInterfaceTransitionSerialization(unittest.TestCase):
    def test_serializes(self):
        from umh.interface.state_machine import (
            InterfaceMode,
            create_interface_state,
            transition_interface_state,
        )

        s = create_interface_state(mode=InterfaceMode.FULL_SCREEN)
        t = transition_interface_state(s, InterfaceMode.WINDOWED)
        d = t.to_dict()
        self.assertIn("transition_id", d)
        self.assertEqual(d["status"], "allowed")


class TestFullScreenToWindowed(unittest.TestCase):
    def test_allowed(self):
        from umh.interface.state_machine import (
            InterfaceMode,
            InterfaceTransitionStatus,
            create_interface_state,
            transition_interface_state,
        )

        s = create_interface_state(mode=InterfaceMode.FULL_SCREEN)
        t = transition_interface_state(s, InterfaceMode.WINDOWED)
        self.assertEqual(t.status, InterfaceTransitionStatus.ALLOWED)


class TestExpandedToMinimized(unittest.TestCase):
    def test_allowed(self):
        from umh.interface.state_machine import (
            InterfaceMode,
            InterfaceTransitionStatus,
            create_interface_state,
            transition_interface_state,
        )

        s = create_interface_state(mode=InterfaceMode.EXPANDED_OVERLAY)
        t = transition_interface_state(s, InterfaceMode.MINIMIZED_WAVE)
        self.assertEqual(t.status, InterfaceTransitionStatus.ALLOWED)


class TestMinimizedToExpanded(unittest.TestCase):
    def test_allowed(self):
        from umh.interface.state_machine import (
            InterfaceMode,
            InterfaceTransitionStatus,
            create_interface_state,
            transition_interface_state,
        )

        s = create_interface_state(mode=InterfaceMode.MINIMIZED_WAVE)
        t = transition_interface_state(s, InterfaceMode.EXPANDED_OVERLAY)
        self.assertEqual(t.status, InterfaceTransitionStatus.ALLOWED)


class TestExpandedToGhost(unittest.TestCase):
    def test_allowed(self):
        from umh.interface.state_machine import (
            InterfaceMode,
            InterfaceTransitionStatus,
            create_interface_state,
            transition_interface_state,
        )

        s = create_interface_state(mode=InterfaceMode.EXPANDED_OVERLAY)
        t = transition_interface_state(s, InterfaceMode.GHOST)
        self.assertEqual(t.status, InterfaceTransitionStatus.ALLOWED)


class TestGhostToExpanded(unittest.TestCase):
    def test_allowed(self):
        from umh.interface.state_machine import (
            InterfaceMode,
            InterfaceTransitionStatus,
            create_interface_state,
            transition_interface_state,
        )

        s = create_interface_state(mode=InterfaceMode.GHOST)
        t = transition_interface_state(s, InterfaceMode.EXPANDED_OVERLAY)
        self.assertEqual(t.status, InterfaceTransitionStatus.ALLOWED)


class TestUnsupportedTransition(unittest.TestCase):
    def test_unsupported(self):
        from umh.interface.state_machine import (
            InterfaceMode,
            InterfaceTransitionStatus,
            create_interface_state,
            transition_interface_state,
        )

        s = create_interface_state(mode=InterfaceMode.TERMINAL)
        t = transition_interface_state(s, InterfaceMode.FULL_SCREEN)
        self.assertEqual(t.status, InterfaceTransitionStatus.UNSUPPORTED)


class TestUnknownTransitionSafe(unittest.TestCase):
    def test_unknown_mode_unsupported(self):
        from umh.interface.state_machine import (
            InterfaceMode,
            InterfaceTransitionStatus,
            create_interface_state,
            transition_interface_state,
        )

        s = create_interface_state(mode=InterfaceMode.UNKNOWN)
        t = transition_interface_state(s, InterfaceMode.FULL_SCREEN)
        self.assertEqual(t.status, InterfaceTransitionStatus.UNSUPPORTED)


class TestDeterministicTransition(unittest.TestCase):
    def test_same_mode_is_noop(self):
        from umh.interface.state_machine import (
            InterfaceMode,
            InterfaceTransitionStatus,
            create_interface_state,
            transition_interface_state,
        )

        s = create_interface_state(mode=InterfaceMode.WINDOWED)
        t = transition_interface_state(s, InterfaceMode.WINDOWED)
        self.assertEqual(t.status, InterfaceTransitionStatus.NOOP)


# ── Section 5: Voice Wave ─────────────────────────────────────────


class TestVoiceWaveStateNormalization(unittest.TestCase):
    def test_known(self):
        from umh.interface.voice_wave import VoiceWaveState, normalize_voice_wave_state

        self.assertEqual(normalize_voice_wave_state("idle"), VoiceWaveState.IDLE)

    def test_unknown(self):
        from umh.interface.voice_wave import VoiceWaveState, normalize_voice_wave_state

        self.assertEqual(normalize_voice_wave_state("xyz"), VoiceWaveState.UNKNOWN)


class TestVoiceWaveLineStateNormalization(unittest.TestCase):
    def test_known(self):
        from umh.interface.voice_wave import VoiceWaveLineState, normalize_line_state

        self.assertEqual(normalize_line_state("pulse"), VoiceWaveLineState.PULSE)


class TestDefaultGlyphSixLines(unittest.TestCase):
    def test_six_lines(self):
        from umh.interface.voice_wave import get_default_six_line_wave

        g = get_default_six_line_wave()
        self.assertEqual(g.line_count, 6)
        self.assertEqual(len(g.line_states), 6)


class TestIdleGlyphSerializes(unittest.TestCase):
    def test_serializes(self):
        from umh.interface.voice_wave import VoiceWaveState, create_voice_wave_glyph

        g = create_voice_wave_glyph(VoiceWaveState.IDLE)
        d = g.to_dict()
        self.assertEqual(d["state"], "idle")


class TestListeningGlyphSerializes(unittest.TestCase):
    def test_serializes(self):
        from umh.interface.voice_wave import VoiceWaveState, create_voice_wave_glyph

        g = create_voice_wave_glyph(VoiceWaveState.LISTENING)
        d = g.to_dict()
        self.assertEqual(d["state"], "listening")


class TestThinkingGlyphSerializes(unittest.TestCase):
    def test_serializes(self):
        from umh.interface.voice_wave import VoiceWaveState, create_voice_wave_glyph

        d = create_voice_wave_glyph(VoiceWaveState.THINKING).to_dict()
        self.assertEqual(d["state"], "thinking")


class TestSpeakingGlyphSerializes(unittest.TestCase):
    def test_serializes(self):
        from umh.interface.voice_wave import VoiceWaveState, create_voice_wave_glyph

        d = create_voice_wave_glyph(VoiceWaveState.SPEAKING).to_dict()
        self.assertEqual(d["state"], "speaking")


class TestMutedGlyphSerializes(unittest.TestCase):
    def test_serializes(self):
        from umh.interface.voice_wave import VoiceWaveState, create_voice_wave_glyph

        d = create_voice_wave_glyph(VoiceWaveState.MUTED).to_dict()
        self.assertEqual(d["state"], "muted")


class TestAttentionRequiredGlyphSerializes(unittest.TestCase):
    def test_serializes(self):
        from umh.interface.voice_wave import VoiceWaveState, create_voice_wave_glyph

        d = create_voice_wave_glyph(VoiceWaveState.ATTENTION_REQUIRED).to_dict()
        self.assertEqual(d["state"], "attention_required")


class TestExecutingGlyphSerializes(unittest.TestCase):
    def test_serializes(self):
        from umh.interface.voice_wave import VoiceWaveState, create_voice_wave_glyph

        d = create_voice_wave_glyph(VoiceWaveState.EXECUTING).to_dict()
        self.assertEqual(d["state"], "executing")


class TestVoiceWaveTransitionSerializes(unittest.TestCase):
    def test_serializes(self):
        from umh.interface.voice_wave import (
            VoiceWaveState,
            create_voice_wave_glyph,
            transition_voice_wave,
        )

        g = create_voice_wave_glyph(VoiceWaveState.IDLE)
        t = transition_voice_wave(g, VoiceWaveState.LISTENING)
        d = t.to_dict()
        self.assertTrue(d["allowed"])


class TestAccessibleLabelRequired(unittest.TestCase):
    def test_label_set(self):
        from umh.interface.voice_wave import VoiceWaveState, create_voice_wave_glyph

        for state in VoiceWaveState:
            g = create_voice_wave_glyph(state)
            self.assertTrue(len(g.accessible_label) > 0, f"No label for {state.value}")


class TestNoAudioImplementation(unittest.TestCase):
    def test_no_audio_imports(self):
        src_path = "/opt/OS/umh/interface/voice_wave.py"
        with open(src_path) as f:
            source = f.read()
        for lib in ["pyaudio", "sounddevice", "speech_recognition", "pyttsx3", "whisper"]:
            self.assertNotIn(lib, source, f"voice_wave.py imports {lib}")


# ── Section 6: Approval Views ────────────────────────────────────


class TestApprovalActionNormalization(unittest.TestCase):
    def test_known(self):
        from umh.interface.approval_views import (
            ApprovalSurfaceAction,
            normalize_approval_surface_action,
        )

        self.assertEqual(
            normalize_approval_surface_action("approve"), ApprovalSurfaceAction.APPROVE
        )

    def test_unknown(self):
        from umh.interface.approval_views import (
            ApprovalSurfaceAction,
            normalize_approval_surface_action,
        )

        self.assertEqual(normalize_approval_surface_action("xyz"), ApprovalSurfaceAction.UNKNOWN)


class TestApprovalDisplayStatusNormalization(unittest.TestCase):
    def test_known(self):
        from umh.interface.approval_views import (
            ApprovalDisplayStatus,
            normalize_approval_display_status,
        )

        self.assertEqual(
            normalize_approval_display_status("pending"), ApprovalDisplayStatus.PENDING
        )


class TestApprovalRequestViewSerialization(unittest.TestCase):
    def test_serializes(self):
        from umh.interface.approval_views import create_approval_request_view

        v = create_approval_request_view(
            "appr_1", title="Test Approval", risk_level="high", environment="production"
        )
        d = v.to_dict()
        self.assertEqual(d["approval_id"], "appr_1")
        self.assertEqual(d["risk_level"], "high")


class TestApprovalResponseSerialization(unittest.TestCase):
    def test_serializes(self):
        from umh.interface.approval_views import ApprovalResponseEnvelope, ApprovalSurfaceAction

        r = ApprovalResponseEnvelope(
            response_id="r1",
            approval_id="a1",
            surface_id="s1",
            action=ApprovalSurfaceAction.APPROVE,
        )
        d = r.to_dict()
        self.assertEqual(d["action"], "approve")


class TestApprovalValidationSerialization(unittest.TestCase):
    def test_serializes(self):
        from umh.interface.approval_views import (
            ApprovalResponseEnvelope,
            ApprovalSurfaceAction,
            validate_approval_response,
        )

        r = ApprovalResponseEnvelope(
            response_id="r1",
            approval_id="a1",
            surface_id="s1",
            action=ApprovalSurfaceAction.APPROVE,
        )
        v = validate_approval_response(r)
        d = v.to_dict()
        self.assertTrue(d["valid"])


class TestUnknownApprovalActionInvalid(unittest.TestCase):
    def test_invalid(self):
        from umh.interface.approval_views import (
            ApprovalResponseEnvelope,
            ApprovalSurfaceAction,
            validate_approval_response,
        )

        r = ApprovalResponseEnvelope(
            response_id="r1",
            approval_id="a1",
            surface_id="s1",
            action=ApprovalSurfaceAction.UNKNOWN,
        )
        v = validate_approval_response(r)
        self.assertFalse(v.valid)


class TestHighRiskApprovalRequiresContext(unittest.TestCase):
    def test_consequences_and_environment(self):
        from umh.interface.approval_views import create_approval_request_view

        v = create_approval_request_view(
            "appr_2",
            risk_level="high",
            environment="production",
            consequences=["Data may be permanently modified"],
        )
        self.assertGreater(len(v.consequences), 0)
        self.assertNotEqual(v.environment, "")


class TestApprovalResponseNoMutation(unittest.TestCase):
    def test_envelope_only(self):
        from umh.interface.approval_views import (
            ApprovalResponseEnvelope,
            ApprovalSurfaceAction,
            validate_approval_response,
        )

        r = ApprovalResponseEnvelope(
            response_id="r1",
            approval_id="a1",
            surface_id="s1",
            action=ApprovalSurfaceAction.APPROVE,
        )
        v = validate_approval_response(r)
        self.assertTrue(
            any("no mutation" in w.lower() or "envelope only" in w.lower() for w in v.warnings)
        )


# ── Section 7: Notification Views ─────────────────────────────────


class TestNotificationTypeNormalization(unittest.TestCase):
    def test_known(self):
        from umh.interface.notification_views import NotificationType, normalize_notification_type

        self.assertEqual(normalize_notification_type("info"), NotificationType.INFO)


class TestNotificationPriorityNormalization(unittest.TestCase):
    def test_known(self):
        from umh.interface.notification_views import (
            NotificationPriority,
            normalize_notification_priority,
        )

        self.assertEqual(normalize_notification_priority("urgent"), NotificationPriority.URGENT)


class TestNotificationChannelNormalization(unittest.TestCase):
    def test_known(self):
        from umh.interface.notification_views import (
            NotificationChannel,
            normalize_notification_channel,
        )

        self.assertEqual(normalize_notification_channel("cli"), NotificationChannel.CLI)


class TestNotificationStatusNormalization(unittest.TestCase):
    def test_known(self):
        from umh.interface.notification_views import (
            NotificationStatus,
            normalize_notification_status,
        )

        self.assertEqual(normalize_notification_status("created"), NotificationStatus.CREATED)


class TestNotificationSerialization(unittest.TestCase):
    def test_serializes(self):
        from umh.interface.notification_views import NotificationType, create_notification

        n = create_notification(NotificationType.INFO, title="Test", message="Hello")
        d = n.to_dict()
        self.assertEqual(d["title"], "Test")
        self.assertEqual(d["notification_type"], "info")


class TestNotificationAckSerialization(unittest.TestCase):
    def test_serializes(self):
        from umh.interface.notification_views import NotificationAck

        a = NotificationAck(ack_id="ack_1", notification_id="n1", surface_id="s1")
        d = a.to_dict()
        self.assertEqual(d["ack_id"], "ack_1")


class TestHeartbeatNotificationDisplayOnly(unittest.TestCase):
    def test_display_only(self):
        from umh.interface.notification_views import NotificationType, create_notification

        n = create_notification(NotificationType.HEARTBEAT, title="Heartbeat")
        self.assertEqual(n.status.value, "created")


class TestApprovalRequiredNotification(unittest.TestCase):
    def test_serializes(self):
        from umh.interface.notification_views import NotificationType, create_notification

        n = create_notification(NotificationType.APPROVAL_REQUIRED, title="Needs Approval")
        d = n.to_dict()
        self.assertEqual(d["notification_type"], "approval_required")


class TestNoExternalSend(unittest.TestCase):
    def test_no_send_imports(self):
        import ast

        src_path = "/opt/OS/umh/interface/notification_views.py"
        with open(src_path) as f:
            source = f.read()
        tree = ast.parse(source)
        imported_names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_names.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported_names.add(node.module.split(".")[0])
        for lib in ["smtplib", "telegram", "discord", "requests"]:
            self.assertNotIn(lib, imported_names, f"Forbidden import: {lib}")


# ── Section 8: Surface Registry ───────────────────────────────────


class TestDefaultSurfaceRegistryInitializes(unittest.TestCase):
    def test_initializes(self):
        from umh.interface.surface_registry import build_default_surface_registry

        reg = build_default_surface_registry()
        self.assertGreater(reg.surface_count, 0)


class TestRegisterSurface(unittest.TestCase):
    def test_register_works(self):
        from umh.interface.surface_registry import InterfaceSurfaceRegistry
        from umh.interface.surfaces import InterfaceSurfaceType, create_interface_surface

        reg = InterfaceSurfaceRegistry()
        s = create_interface_surface("Test", surface_type=InterfaceSurfaceType.CLI)
        reg.register_surface(s)
        self.assertEqual(reg.surface_count, 1)


class TestGetSurface(unittest.TestCase):
    def test_retrieves(self):
        from umh.interface.surface_registry import build_default_surface_registry

        reg = build_default_surface_registry()
        surfaces = reg.list_surfaces(limit=1)
        s = reg.get_surface(surfaces[0].surface_id)
        self.assertIsNotNone(s)


class TestListByType(unittest.TestCase):
    def test_filters(self):
        from umh.interface.surface_registry import build_default_surface_registry
        from umh.interface.surfaces import InterfaceSurfaceType

        reg = build_default_surface_registry()
        cli_surfaces = reg.list_surfaces(surface_type=InterfaceSurfaceType.CLI)
        self.assertGreater(len(cli_surfaces), 0)
        self.assertTrue(all(s.surface_type == InterfaceSurfaceType.CLI for s in cli_surfaces))


class TestListByPlatform(unittest.TestCase):
    def test_filters(self):
        from umh.interface.surface_registry import build_default_surface_registry
        from umh.interface.surfaces import InterfacePlatform

        reg = build_default_surface_registry()
        ios = reg.list_surfaces(platform=InterfacePlatform.IOS)
        self.assertTrue(all(s.platform == InterfacePlatform.IOS for s in ios))


class TestQueryByCapability(unittest.TestCase):
    def test_finds(self):
        from umh.interface.surface_registry import build_default_surface_registry

        reg = build_default_surface_registry()
        results = reg.query_by_capability("display_state")
        self.assertGreater(len(results), 0)


class TestCapabilityMatrixBuilds(unittest.TestCase):
    def test_builds(self):
        from umh.interface.surface_registry import build_default_surface_registry

        reg = build_default_surface_registry()
        matrix = reg.build_capability_matrix()
        self.assertGreater(len(matrix), 0)
        for m in matrix:
            d = m.to_dict()
            self.assertIn("capabilities", d)


class TestBestSurfaceForCapability(unittest.TestCase):
    def test_deterministic(self):
        from umh.interface.surface_registry import (
            build_default_surface_registry,
            find_best_surface_for_capability,
        )

        reg = build_default_surface_registry()
        best = find_best_surface_for_capability(reg, "display_state")
        self.assertIsNotNone(best)


class TestExplainSurfaceLimitations(unittest.TestCase):
    def test_explains(self):
        from umh.interface.surface_registry import explain_surface_limitations
        from umh.interface.surfaces import InterfaceSurfaceType, create_interface_surface

        s = create_interface_surface(
            "X", surface_type=InterfaceSurfaceType.MOBILE_APP, limitations=["No overlay"]
        )
        exp = explain_surface_limitations(s)
        self.assertIn("No overlay", exp)


class TestQueryLimitEnforced(unittest.TestCase):
    def test_limited(self):
        from umh.interface.surface_registry import build_default_surface_registry

        reg = build_default_surface_registry()
        results = reg.list_surfaces(limit=2)
        self.assertLessEqual(len(results), 2)


class TestRegistryNoDestructiveMethods(unittest.TestCase):
    def test_no_delete_clear_pop(self):
        from umh.interface.surface_registry import InterfaceSurfaceRegistry

        reg = InterfaceSurfaceRegistry()
        for method_name in ["delete", "remove", "clear", "pop", "drop"]:
            self.assertFalse(
                hasattr(reg, method_name), f"Registry has destructive method: {method_name}"
            )


# ── Section 9: Interface Safety ───────────────────────────────────


class TestCommandSafetyReadOnly(unittest.TestCase):
    def test_read_only_safe(self):
        from umh.interface.commands import InterfaceCommandType, create_command_envelope
        from umh.interface.safety import validate_command_is_safe

        env = create_command_envelope("s1", InterfaceCommandType.READ_QUERY)
        result = validate_command_is_safe(env)
        self.assertTrue(result.safe)


class TestCommandSafetyUnknownExecution(unittest.TestCase):
    def test_unknown_not_safe(self):
        from umh.interface.commands import InterfaceCommandType, create_command_envelope
        from umh.interface.safety import validate_command_is_safe

        env = create_command_envelope("s1", InterfaceCommandType.UNKNOWN)
        env.read_only = False
        result = validate_command_is_safe(env)
        self.assertFalse(result.safe)


class TestSafetyScanSafeOnMissing(unittest.TestCase):
    def test_missing_dir(self):
        from umh.interface.safety import validate_interface_module_boundaries

        result = validate_interface_module_boundaries("/nonexistent/path")
        self.assertTrue(result.safe)
        self.assertGreater(len(result.warnings), 0)


class TestSafetyScanDetectsAdapterImport(unittest.TestCase):
    def test_detects(self):
        from umh.interface.safety import scan_interface_for_forbidden_imports

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("from umh.adapters.cli import CliAdapter\n")
            f.flush()
            result = scan_interface_for_forbidden_imports([f.name])
            self.assertFalse(result.safe)
        os.unlink(f.name)


class TestSafetyScanDetectsSubprocess(unittest.TestCase):
    def test_detects(self):
        from umh.interface.safety import validate_interface_module_boundaries

        with tempfile.TemporaryDirectory() as td:
            fp = os.path.join(td, "bad.py")
            with open(fp, "w") as f:
                f.write("import subprocess\nsubprocess.run(['ls'])\n")
            result = validate_interface_module_boundaries(td)
            self.assertFalse(result.safe)


class TestSafetyScanDetectsStorageMutation(unittest.TestCase):
    def test_detects(self):
        from umh.interface.safety import scan_interface_for_direct_storage_mutation

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write('with open("data.json", "w") as fp:\n    json.dump({}, fp)\n')
            f.flush()
            result = scan_interface_for_direct_storage_mutation([f.name])
            self.assertFalse(result.safe)
        os.unlink(f.name)


class TestSafetyScanReadOnly(unittest.TestCase):
    def test_no_mutation(self):
        src_path = "/opt/OS/umh/interface/safety.py"
        with open(src_path) as f:
            source = f.read()
        self.assertNotIn("shutil.rmtree(", source)


class TestSafetyResultSerialization(unittest.TestCase):
    def test_serializes(self):
        from umh.interface.safety import InterfaceSafetyResult

        r = InterfaceSafetyResult(safe=True, warnings=["test"])
        d = r.to_dict()
        self.assertTrue(d["safe"])


# ── Section 10: Command Center ────────────────────────────────────


class TestCommandCenterSectionNormalization(unittest.TestCase):
    def test_known(self):
        from umh.interface.command_center import (
            CommandCenterSection,
            normalize_command_center_section,
        )

        self.assertEqual(
            normalize_command_center_section("dashboard"), CommandCenterSection.DASHBOARD
        )


class TestCommandCenterSnapshotSerialization(unittest.TestCase):
    def test_serializes(self):
        from umh.interface.command_center import build_command_center_snapshot

        snap = build_command_center_snapshot()
        d = snap.to_dict()
        self.assertIn("generated_at", d)
        self.assertIn("warnings", d)


class TestSnapshotWorksWithNoComponents(unittest.TestCase):
    def test_degrades_gracefully(self):
        from umh.interface.command_center import build_command_center_snapshot

        snap = build_command_center_snapshot()
        self.assertGreater(len(snap.warnings), 0)


class TestSnapshotIncludesSystemStatus(unittest.TestCase):
    def test_when_provided(self):
        from umh.interface.command_center import build_command_center_snapshot

        snap = build_command_center_snapshot(system_status={"health": "ok"})
        self.assertIsNotNone(snap.system_status)


class TestSnapshotIncludesDashboard(unittest.TestCase):
    def test_when_provided(self):
        from umh.interface.command_center import build_command_center_snapshot

        snap = build_command_center_snapshot(operator_dashboard={"user_id": "u1"})
        self.assertIsNotNone(snap.operator_dashboard)


class TestSnapshotIncludesRegistrySummary(unittest.TestCase):
    def test_when_provided(self):
        from umh.interface.command_center import build_command_center_snapshot

        snap = build_command_center_snapshot(registry_summary={"total": 50})
        self.assertIsNotNone(snap.registry_summary)


class TestSnapshotIncludesOntologySummary(unittest.TestCase):
    def test_when_provided(self):
        from umh.interface.command_center import build_command_center_snapshot

        snap = build_command_center_snapshot(ontology_summary={"primitives": 13})
        self.assertIsNotNone(snap.ontology_summary)


class TestSnapshotIncludesStorageSummary(unittest.TestCase):
    def test_when_provided(self):
        from umh.interface.command_center import build_command_center_snapshot

        snap = build_command_center_snapshot(storage_summary={"backends": 2})
        self.assertIsNotNone(snap.storage_summary)


class TestSnapshotIncludesMigrationSummary(unittest.TestCase):
    def test_when_provided(self):
        from umh.interface.command_center import build_command_center_snapshot

        snap = build_command_center_snapshot(migration_summary={"deprecated": 5})
        self.assertIsNotNone(snap.migration_summary)


class TestSnapshotIncludesVoiceWave(unittest.TestCase):
    def test_when_provided(self):
        from umh.interface.command_center import build_command_center_snapshot
        from umh.interface.voice_wave import VoiceWaveState, get_default_six_line_wave

        g = get_default_six_line_wave(VoiceWaveState.IDLE)
        snap = build_command_center_snapshot(voice_wave=g.to_dict())
        self.assertIsNotNone(snap.voice_wave)


class TestSnapshotWarningsForMissing(unittest.TestCase):
    def test_warns(self):
        from umh.interface.command_center import build_command_center_snapshot

        snap = build_command_center_snapshot()
        warning_text = " ".join(snap.warnings).lower()
        self.assertIn("unavailable", warning_text)


class TestNoExecutionInCommandCenter(unittest.TestCase):
    def test_no_execution_imports(self):
        src_path = "/opt/OS/umh/interface/command_center.py"
        with open(src_path) as f:
            source = f.read()
        self.assertNotIn("execute_governed", source)
        self.assertNotIn("adapter_backend", source)


# ── Section 11: Registry Integration ─────────────────────────────


class TestInterfaceSurfaceBridge(unittest.TestCase):
    def test_returns_items(self):
        from umh.registry.bridges import interface_surfaces_to_registry_items

        items = interface_surfaces_to_registry_items()
        self.assertGreater(len(items), 0)
        for item in items:
            self.assertEqual(item.registry_type.value, "interface_surface")


class TestVoiceWaveStatesBridge(unittest.TestCase):
    def test_returns_items(self):
        from umh.registry.bridges import voice_wave_states_to_registry_items

        items = voice_wave_states_to_registry_items()
        self.assertGreater(len(items), 0)


class TestCommandCenterSectionsBridge(unittest.TestCase):
    def test_returns_items(self):
        from umh.registry.bridges import command_center_sections_to_registry_items

        items = command_center_sections_to_registry_items()
        self.assertGreater(len(items), 0)


class TestRegistryCatalogIncludesInterface(unittest.TestCase):
    def test_catalog_loads_interface(self):
        from umh.registry.catalog import build_default_registry_catalog
        from umh.registry.contracts import RegistryType

        catalog = build_default_registry_catalog()
        interface_items = catalog.by_type(RegistryType.INTERFACE_SURFACE)
        self.assertGreater(len(interface_items), 0)


class TestRegistryIntegrationMetadataOnly(unittest.TestCase):
    def test_no_execution(self):
        from umh.registry.bridges import interface_surfaces_to_registry_items

        items = interface_surfaces_to_registry_items()
        for item in items:
            self.assertIsNotNone(item.to_dict())


class TestPhase80RegistryStillWorks(unittest.TestCase):
    def test_catalog_builds(self):
        from umh.registry.catalog import build_default_registry_catalog

        catalog = build_default_registry_catalog()
        self.assertGreater(len(catalog.items), 0)


# ── Section 12: Observability ─────────────────────────────────────


class TestSystemStatusWithoutInterface(unittest.TestCase):
    def test_works(self):
        from umh.observability.system_status import build_system_status

        status = build_system_status(user_id="u1")
        d = status.to_dict()
        self.assertIn("interface_status", d)
        self.assertEqual(d["interface_status"], "unavailable")


class TestSystemStatusWithInterface(unittest.TestCase):
    def test_includes_interface(self):
        from umh.interface.surface_registry import build_default_surface_registry
        from umh.observability.system_status import build_system_status

        reg = build_default_surface_registry()
        status = build_system_status(user_id="u1", interface_registry=reg)
        d = status.to_dict()
        self.assertEqual(d["interface_status"], "ok")


class TestInterfaceUnavailableNotHealthy(unittest.TestCase):
    def test_not_healthy(self):
        from umh.observability.system_status import build_system_status

        status = build_system_status(user_id="u1")
        self.assertNotEqual(status.health.value, "healthy")


class TestDashboardWithoutInterface(unittest.TestCase):
    def test_works(self):
        from umh.observability.operator_views import build_operator_dashboard_snapshot

        snap = build_operator_dashboard_snapshot(user_id="u1")
        d = snap.to_dict()
        self.assertIn("interface_summary", d)


class TestDashboardWithInterface(unittest.TestCase):
    def test_includes_interface(self):
        from umh.interface.surface_registry import build_default_surface_registry
        from umh.observability.operator_views import build_operator_dashboard_snapshot

        reg = build_default_surface_registry()
        snap = build_operator_dashboard_snapshot(user_id="u1", interface_registry=reg)
        d = snap.to_dict()
        self.assertIn("surface_count", d.get("interface_summary", {}))


class TestCommandCenterSnapshotReadOnly(unittest.TestCase):
    def test_read_only(self):
        from umh.interface.command_center import build_command_center_snapshot

        snap = build_command_center_snapshot()
        d = snap.to_dict()
        self.assertIsInstance(d, dict)


# ── Section 13: API/Control ───────────────────────────────────────


class TestInterfaceApiEndpoints(unittest.TestCase):
    def test_endpoints_registered(self):
        from umh.control.api import app

        routes = [r.path for r in app.routes if hasattr(r, "path")]
        expected = [
            "/interface/status",
            "/interface/surfaces",
            "/interface/surfaces/{surface_id}",
            "/interface/capability-matrix",
            "/interface/command-center",
            "/interface/voice-wave",
            "/interface/notifications",
            "/interface/approvals",
            "/interface/safety",
            "/interface/commands/validate",
        ]
        for ep in expected:
            self.assertIn(ep, routes, f"Missing endpoint: {ep}")

    def test_endpoints_are_get(self):
        from umh.control.api import app

        for route in app.routes:
            if (
                hasattr(route, "path")
                and route.path.startswith("/interface/")
                and route.path != "/interface/commands/validate"
            ):
                methods = getattr(route, "methods", set())
                self.assertTrue("GET" in methods, f"{route.path} should be GET")

    def test_validate_is_post(self):
        from umh.control.api import app

        for route in app.routes:
            if hasattr(route, "path") and route.path == "/interface/commands/validate":
                methods = getattr(route, "methods", set())
                self.assertIn("POST", methods)

    def test_no_execute_endpoint(self):
        from umh.control.api import app

        routes = [r.path for r in app.routes if hasattr(r, "path")]
        for r in routes:
            if r.startswith("/interface/"):
                self.assertNotIn("execute", r.lower().replace("commands/validate", ""))


# ── Section 14: CLI ───────────────────────────────────────────────


class TestInterfaceCliCommands(unittest.TestCase):
    def test_commands_in_parser(self):
        from umh.control.cli import build_parser

        parser = build_parser()
        choices = parser._subparsers._group_actions[0].choices
        expected = [
            "interface-status",
            "interface-surfaces",
            "interface-matrix",
            "interface-command-center",
            "interface-voice-wave",
            "interface-notifications",
            "interface-approvals",
            "interface-safety",
        ]
        for cmd in expected:
            self.assertIn(cmd, choices, f"Missing CLI command: {cmd}")


class TestInterfaceCliSmoke(unittest.TestCase):
    def test_interface_status(self):
        from umh.control.cli import main

        rc = main(["interface-status", "--json"])
        self.assertEqual(rc, 0)

    def test_interface_surfaces(self):
        from umh.control.cli import main

        rc = main(["interface-surfaces", "--json"])
        self.assertEqual(rc, 0)

    def test_interface_voice_wave(self):
        from umh.control.cli import main

        rc = main(["interface-voice-wave", "--json"])
        self.assertEqual(rc, 0)

    def test_interface_safety(self):
        from umh.control.cli import main

        rc = main(["interface-safety", "--json"])
        self.assertEqual(rc, 0)

    def test_interface_command_center(self):
        from umh.control.cli import main

        rc = main(["interface-command-center", "--json"])
        self.assertEqual(rc, 0)


# ── Section 15: Layering Invariants ──────────────────────────────


_INTERFACE_FILES = [
    "/opt/OS/umh/interface/surfaces.py",
    "/opt/OS/umh/interface/commands.py",
    "/opt/OS/umh/interface/events.py",
    "/opt/OS/umh/interface/state_machine.py",
    "/opt/OS/umh/interface/voice_wave.py",
    "/opt/OS/umh/interface/approval_views.py",
    "/opt/OS/umh/interface/notification_views.py",
    "/opt/OS/umh/interface/command_center.py",
    "/opt/OS/umh/interface/surface_registry.py",
]


def _read_all_interface_source() -> str:
    parts = []
    for fp in _INTERFACE_FILES:
        if os.path.isfile(fp):
            with open(fp) as f:
                parts.append(f.read())
    return "\n".join(parts)


class TestNoSubprocessImport(unittest.TestCase):
    def test_no_subprocess(self):
        source = _read_all_interface_source()
        self.assertNotIn("import subprocess", source)


class TestNoRequestsImport(unittest.TestCase):
    def test_no_requests(self):
        source = _read_all_interface_source()
        self.assertNotIn("import requests", source)
        self.assertNotIn("import httpx", source)


class TestNoBrowserAutomation(unittest.TestCase):
    def test_no_selenium_playwright(self):
        source = _read_all_interface_source()
        self.assertNotIn("selenium", source)
        self.assertNotIn("playwright", source)


class TestNoAdapterImport(unittest.TestCase):
    def test_no_adapter_calls(self):
        source = _read_all_interface_source()
        self.assertNotIn("from umh.adapters", source)
        self.assertNotIn("import umh.adapters", source)


class TestNoExecutionEngineCall(unittest.TestCase):
    def test_no_direct_execution(self):
        source = _read_all_interface_source()
        self.assertNotIn("execute_governed(", source)


class TestNoTraceMutation(unittest.TestCase):
    def test_no_trace_writes(self):
        source = _read_all_interface_source()
        self.assertNotIn("trace_store.store(", source)
        self.assertNotIn("trace_store.save(", source)


class TestNoOutcomeMutation(unittest.TestCase):
    def test_no_outcome_writes(self):
        source = _read_all_interface_source()
        self.assertNotIn("outcome_store.store(", source)
        self.assertNotIn("outcome_store.save(", source)


class TestNoFeedbackMutation(unittest.TestCase):
    def test_no_feedback_writes(self):
        source = _read_all_interface_source()
        self.assertNotIn("feedback_store.store(", source)
        self.assertNotIn("feedback_store.save(", source)


class TestNoMemoryPromotion(unittest.TestCase):
    def test_no_promote(self):
        source = _read_all_interface_source()
        self.assertNotIn(".promote(", source)


class TestNoGovernanceMutation(unittest.TestCase):
    def test_no_governance_writes(self):
        source = _read_all_interface_source()
        for pat in [".approve(", ".deny(", ".escalate("]:
            self.assertNotIn(pat, source, f"Interface modules contain {pat}")


class TestNoBackendRoutingMutation(unittest.TestCase):
    def test_no_routing_mutation(self):
        source = _read_all_interface_source()
        self.assertNotIn("backend_registry.register(", source)


class TestNoRegistryOntologyMigrationMutation(unittest.TestCase):
    def test_no_mutation(self):
        source = _read_all_interface_source()
        self.assertNotIn("registry.remove(", source)
        self.assertNotIn("ontology.update(", source)
        self.assertNotIn("migration.delete(", source)


class TestNoNativeUIDependencies(unittest.TestCase):
    def test_no_native_ui(self):
        source = _read_all_interface_source()
        for lib in ["tkinter", "PyQt", "wxPython", "kivy", "electron", "tauri"]:
            self.assertNotIn(lib, source, f"Interface modules import {lib}")


class TestNoVoiceAPIDependencies(unittest.TestCase):
    def test_no_voice_api(self):
        source = _read_all_interface_source()
        for lib in [
            "pyaudio",
            "sounddevice",
            "speech_recognition",
            "pyttsx3",
            "whisper",
            "azure.cognitiveservices",
        ]:
            self.assertNotIn(lib, source)


# ── Section 16: Regression ────────────────────────────────────────


class TestPhase75bRegression(unittest.TestCase):
    def test_importable(self):
        import importlib

        importlib.import_module("tests.test_phase75b_mvp_lockin")


class TestPhase76Regression(unittest.TestCase):
    def test_importable(self):
        import importlib

        importlib.import_module("tests.test_phase76_adapters")


class TestPhase77Regression(unittest.TestCase):
    def test_importable(self):
        import importlib

        importlib.import_module("tests.test_phase77_workstation_state")


class TestPhase78Regression(unittest.TestCase):
    def test_importable(self):
        import importlib

        importlib.import_module("tests.test_phase78_feedback_loop")


class TestPhase79Regression(unittest.TestCase):
    def test_importable(self):
        import importlib

        importlib.import_module("tests.test_phase79_observability")


class TestPhase80Regression(unittest.TestCase):
    def test_importable(self):
        import importlib

        importlib.import_module("tests.test_phase80_registry")


class TestPhase81Regression(unittest.TestCase):
    def test_importable(self):
        import importlib

        importlib.import_module("tests.test_phase81_ontology_law_kernel")


class TestPhase82Regression(unittest.TestCase):
    def test_importable(self):
        import importlib

        importlib.import_module("tests.test_phase82_storage_memory_discipline")


class TestPhase83Regression(unittest.TestCase):
    def test_importable(self):
        import importlib

        importlib.import_module("tests.test_phase83_legacy_migration_boundary")


if __name__ == "__main__":
    unittest.main()
