"""Tests for Campaign 20.2 — Ambient Wake Runtime."""

import sys
import time
import unittest

sys.path.insert(0, "/opt/OS/.claude/worktrees/c20-voice-operations")

from substrate.workstation.ambient_wake_runtime import (
    COMMAND_TIMEOUT_SECONDS,
    COOLDOWN_SECONDS,
    AmbientState,
    AmbientWakeRuntime,
    AmbientWakeSnapshot,
    WakeTransition,
)


class TestAmbientStateEnum(unittest.TestCase):
    def test_all_states_exist(self):
        expected = {"dormant", "passive_listening", "wake_detected", "command_active", "cooldown"}
        actual = {s.value for s in AmbientState}
        self.assertEqual(actual, expected)

    def test_string_enum(self):
        self.assertEqual(str(AmbientState.DORMANT), "AmbientState.DORMANT")
        self.assertIsInstance(AmbientState.DORMANT, str)


class TestWakeTransition(unittest.TestCase):
    def test_defaults(self):
        t = WakeTransition()
        self.assertEqual(t.from_state, "")
        self.assertEqual(t.to_state, "")
        self.assertEqual(t.trigger, "")

    def test_to_dict(self):
        t = WakeTransition(
            from_state="dormant",
            to_state="passive_listening",
            trigger="activate",
            device_id="dev1",
            timestamp=1000.0,
            session_id="s1",
        )
        d = t.to_dict()
        self.assertEqual(d["from_state"], "dormant")
        self.assertEqual(d["to_state"], "passive_listening")
        self.assertEqual(d["trigger"], "activate")
        self.assertEqual(d["device_id"], "dev1")
        self.assertEqual(d["session_id"], "s1")


class TestAmbientWakeSnapshot(unittest.TestCase):
    def test_defaults(self):
        s = AmbientWakeSnapshot()
        self.assertEqual(s.state, "dormant")
        self.assertEqual(s.transitions_today, 0)
        self.assertEqual(s.active_command_session, "")

    def test_to_dict(self):
        s = AmbientWakeSnapshot(
            state="passive_listening",
            transitions_today=3,
            listening_devices=["d1", "d2"],
        )
        d = s.to_dict()
        self.assertEqual(d["state"], "passive_listening")
        self.assertEqual(d["transitions_today"], 3)
        self.assertEqual(len(d["listening_devices"]), 2)


class TestAmbientWakeRuntime(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = AmbientWakeRuntime(
            wake_producer_runtime=None,
            voice_session_manager=None,
            presence_runtime=None,
        )

    def setUp(self):
        self.rt = AmbientWakeRuntime(
            wake_producer_runtime=None,
            voice_session_manager=None,
            presence_runtime=None,
        )

    def test_initial_state_is_dormant(self):
        self.assertEqual(self.rt.current_state(), AmbientState.DORMANT)

    def test_activate_transitions_to_passive_listening(self):
        t = self.rt.activate()
        self.assertEqual(t.to_state, "passive_listening")
        self.assertEqual(self.rt.current_state(), AmbientState.PASSIVE_LISTENING)

    def test_deactivate_returns_to_dormant(self):
        self.rt.activate()
        t = self.rt.deactivate()
        self.assertEqual(t.to_state, "dormant")
        self.assertEqual(self.rt.current_state(), AmbientState.DORMANT)

    def test_deactivate_from_command_active(self):
        self.rt.activate()
        self.rt.on_wake_detected("dev1", "hey")
        self.assertEqual(self.rt.current_state(), AmbientState.COMMAND_ACTIVE)
        t = self.rt.deactivate()
        self.assertEqual(self.rt.current_state(), AmbientState.DORMANT)

    def test_wake_detected_from_passive_listening(self):
        self.rt.activate()
        t = self.rt.on_wake_detected("dev1", "jarvis")
        self.assertEqual(self.rt.current_state(), AmbientState.COMMAND_ACTIVE)
        self.assertEqual(t.to_state, "command_active")

    def test_wake_detected_ignored_when_dormant(self):
        t = self.rt.on_wake_detected("dev1", "hey")
        self.assertEqual(self.rt.current_state(), AmbientState.DORMANT)
        self.assertIn("ignored", t.trigger)

    def test_wake_detected_ignored_when_command_active(self):
        self.rt.activate()
        self.rt.on_wake_detected("dev1", "jarvis")
        self.assertEqual(self.rt.current_state(), AmbientState.COMMAND_ACTIVE)
        t = self.rt.on_wake_detected("dev1", "jarvis again")
        self.assertEqual(self.rt.current_state(), AmbientState.COMMAND_ACTIVE)
        self.assertIn("ignored", t.trigger)

    def test_on_command_complete_enters_cooldown(self):
        self.rt.activate()
        self.rt.on_wake_detected("dev1", "jarvis")
        t = self.rt.on_command_complete("s1")
        self.assertEqual(t.to_state, "cooldown")
        self.assertEqual(self.rt.current_state(), AmbientState.COOLDOWN)

    def test_on_command_complete_ignored_when_not_active(self):
        self.rt.activate()
        t = self.rt.on_command_complete("s1")
        self.assertIn("ignored", t.trigger)

    def test_wake_from_cooldown(self):
        self.rt.activate()
        self.rt.on_wake_detected("dev1", "jarvis")
        self.rt.on_command_complete("s1")
        self.assertEqual(self.rt.current_state(), AmbientState.COOLDOWN)
        t = self.rt.on_wake_detected("dev1", "jarvis again")
        self.assertEqual(self.rt.current_state(), AmbientState.COMMAND_ACTIVE)

    def test_command_timeout_transitions_to_cooldown(self):
        self.rt.activate()
        self.rt.on_wake_detected("dev1", "jarvis")
        self.rt._last_state_change = time.time() - COMMAND_TIMEOUT_SECONDS - 1
        state = self.rt.current_state()
        self.assertIn(state, (AmbientState.COOLDOWN, AmbientState.PASSIVE_LISTENING))

    def test_cooldown_timeout_transitions_to_passive(self):
        self.rt.activate()
        self.rt.on_wake_detected("dev1", "jarvis")
        self.rt.on_command_complete("s1")
        self.rt._last_state_change = time.time() - COOLDOWN_SECONDS - 1
        state = self.rt.current_state()
        self.assertEqual(state, AmbientState.PASSIVE_LISTENING)

    def test_on_timeout_does_not_crash(self):
        t = self.rt.on_timeout()
        self.assertIsInstance(t, WakeTransition)

    def test_listening_devices_empty_when_dormant(self):
        devs = self.rt.listening_devices()
        self.assertEqual(devs, [])

    def test_listening_devices_when_passive(self):
        self.rt.activate()
        self.rt.add_listening_device("dev1")
        devs = self.rt.listening_devices()
        self.assertIn("dev1", devs)

    def test_add_remove_listening_device(self):
        self.rt.add_listening_device("d1")
        self.rt.add_listening_device("d2")
        self.rt.remove_listening_device("d1")
        self.assertNotIn("d1", self.rt._listening_devices)
        self.assertIn("d2", self.rt._listening_devices)

    def test_snapshot(self):
        self.rt.activate()
        snap = self.rt.snapshot()
        self.assertIsInstance(snap, AmbientWakeSnapshot)
        self.assertEqual(snap.state, "passive_listening")
        d = snap.to_dict()
        self.assertIn("state", d)
        self.assertIn("generated_at", d)

    def test_transitions_today_increments(self):
        self.rt.activate()
        self.rt.on_wake_detected("d1", "jarvis")
        self.assertGreaterEqual(self.rt._transitions_today, 1)

    def test_last_wake_set(self):
        self.rt.activate()
        self.rt.on_wake_detected("d1", "hey")
        self.assertGreater(self.rt._last_wake, 0)

    def test_graceful_degradation_no_deps(self):
        rt = AmbientWakeRuntime(
            wake_producer_runtime=None,
            voice_session_manager=None,
            presence_runtime=None,
        )
        rt.activate()
        t = rt.on_wake_detected("d1", "test")
        self.assertEqual(rt.current_state(), AmbientState.COMMAND_ACTIVE)
        snap = rt.snapshot()
        self.assertIsInstance(snap.to_dict(), dict)

    def test_multiple_wake_cycles(self):
        self.rt.activate()
        for i in range(3):
            self.rt.on_wake_detected("d1", f"wake_{i}")
            self.rt.on_command_complete(f"s{i}")
            self.rt._last_state_change = time.time() - COOLDOWN_SECONDS - 1
            _ = self.rt.current_state()
        self.assertEqual(self.rt.current_state(), AmbientState.PASSIVE_LISTENING)

    def test_transition_history_bounded(self):
        self.rt.activate()
        for i in range(120):
            self.rt.on_wake_detected("d1", f"w{i}")
            self.rt.on_command_complete(f"s{i}")
            self.rt._state = AmbientState.PASSIVE_LISTENING
            self.rt._last_state_change = time.time()
        self.assertLessEqual(len(self.rt._transitions), self.rt._max_transitions)


if __name__ == "__main__":
    unittest.main()
