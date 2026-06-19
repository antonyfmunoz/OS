"""Tests for Campaign 20.3 — Voice Output Runtime."""

import sys
import unittest

sys.path.insert(0, "/opt/OS/.claude/worktrees/c20-voice-operations")

from substrate.workstation.voice_output_runtime import (
    OutputRoutingDecision,
    VoiceOutputRuntime,
    VoiceOutputSnapshot,
    VoiceOutputTarget,
)


class TestVoiceOutputTargetEnum(unittest.TestCase):
    def test_all_targets_exist(self):
        expected = {
            "spoken_reply", "right_rail_text", "conference_log",
            "discord_voice", "silent_log", "notification",
        }
        actual = {t.value for t in VoiceOutputTarget}
        self.assertEqual(actual, expected)

    def test_string_enum(self):
        self.assertIsInstance(VoiceOutputTarget.SPOKEN_REPLY, str)


class TestOutputRoutingDecision(unittest.TestCase):
    def test_defaults(self):
        d = OutputRoutingDecision()
        self.assertEqual(d.targets, [])
        self.assertEqual(d.rationale, "")

    def test_to_dict(self):
        d = OutputRoutingDecision(
            targets=["spoken_reply", "right_rail_text"],
            rationale="test",
            session_id="s1",
            source_type="right_rail",
        )
        out = d.to_dict()
        self.assertEqual(len(out["targets"]), 2)
        self.assertEqual(out["source_type"], "right_rail")


class TestVoiceOutputSnapshot(unittest.TestCase):
    def test_defaults(self):
        s = VoiceOutputSnapshot()
        self.assertEqual(s.health, "idle")
        self.assertEqual(s.total_routed, 0)

    def test_to_dict(self):
        s = VoiceOutputSnapshot(health="active", total_routed=5)
        d = s.to_dict()
        self.assertEqual(d["health"], "active")
        self.assertEqual(d["total_routed"], 5)


class TestVoiceOutputRuntime(unittest.TestCase):
    def setUp(self):
        self.rt = VoiceOutputRuntime(
            voice_session_manager=None,
            voice_route_resolver=None,
            voice_ingress_runtime=None,
        )

    def test_right_rail_targets(self):
        targets = self.rt.output_targets_for_source("right_rail")
        self.assertIn("spoken_reply", targets)
        self.assertIn("right_rail_text", targets)

    def test_conference_targets(self):
        targets = self.rt.output_targets_for_source("conference")
        self.assertIn("conference_log", targets)
        self.assertNotIn("spoken_reply", targets)

    def test_discord_targets(self):
        targets = self.rt.output_targets_for_source("discord")
        self.assertIn("discord_voice", targets)
        self.assertIn("silent_log", targets)

    def test_system_audio_targets(self):
        targets = self.rt.output_targets_for_source("system_audio")
        self.assertIn("silent_log", targets)
        self.assertEqual(len(targets), 1)

    def test_ambient_targets(self):
        targets = self.rt.output_targets_for_source("ambient")
        self.assertIn("spoken_reply", targets)
        self.assertIn("right_rail_text", targets)
        self.assertIn("silent_log", targets)

    def test_unknown_source_defaults_silent_log(self):
        targets = self.rt.output_targets_for_source("unknown_thing")
        self.assertIn("silent_log", targets)

    def test_session_type_operator_chat(self):
        targets = self.rt.output_targets_for_session_type("operator_chat")
        self.assertIn("spoken_reply", targets)
        self.assertIn("right_rail_text", targets)

    def test_session_type_conference_transcription(self):
        targets = self.rt.output_targets_for_session_type("conference_transcription")
        self.assertIn("conference_log", targets)

    def test_session_type_broadcast_capture(self):
        targets = self.rt.output_targets_for_session_type("broadcast_capture")
        self.assertIn("silent_log", targets)
        self.assertIn("notification", targets)

    def test_session_type_ambient_listening(self):
        targets = self.rt.output_targets_for_session_type("ambient_listening")
        self.assertIn("spoken_reply", targets)
        self.assertIn("silent_log", targets)

    def test_session_type_system_monitor(self):
        targets = self.rt.output_targets_for_session_type("system_monitor")
        self.assertEqual(targets, ["silent_log"])

    def test_route_output_without_session(self):
        decision = self.rt.route_output(
            session_id="nonexistent",
            response_text="hello",
            source_type="right_rail",
        )
        self.assertIsInstance(decision, OutputRoutingDecision)
        self.assertIn("spoken_reply", decision.targets)
        self.assertEqual(decision.source_type, "right_rail")

    def test_route_output_records_decision(self):
        self.rt.route_output("s1", "test", source_type="conference")
        self.rt.route_output("s2", "test2", source_type="ambient")
        self.assertEqual(self.rt._total_routed, 2)
        self.assertGreater(len(self.rt._recent_decisions), 0)

    def test_route_output_rationale_includes_source(self):
        decision = self.rt.route_output("s1", "hi", source_type="discord")
        self.assertIn("discord", decision.rationale)

    def test_snapshot_idle_when_no_routing(self):
        snap = self.rt.snapshot()
        self.assertEqual(snap.health, "idle")
        self.assertEqual(snap.total_routed, 0)

    def test_snapshot_active_after_routing(self):
        self.rt.route_output("s1", "test", source_type="right_rail")
        snap = self.rt.snapshot()
        self.assertEqual(snap.health, "active")
        self.assertEqual(snap.total_routed, 1)

    def test_snapshot_to_dict(self):
        self.rt.route_output("s1", "x", source_type="ambient")
        snap = self.rt.snapshot()
        d = snap.to_dict()
        self.assertIn("outputs_by_target", d)
        self.assertIn("recent_decisions", d)
        self.assertGreater(d["generated_at"], 0)

    def test_outputs_by_target_counts(self):
        self.rt.route_output("s1", "x", source_type="right_rail")
        self.rt.route_output("s2", "y", source_type="right_rail")
        self.assertGreaterEqual(self.rt._outputs_by_target.get("spoken_reply", 0), 2)

    def test_recent_decisions_bounded(self):
        for i in range(60):
            self.rt.route_output(f"s{i}", f"t{i}", source_type="right_rail")
        self.assertLessEqual(len(self.rt._recent_decisions), self.rt._max_recent)

    def test_graceful_degradation_no_deps(self):
        rt = VoiceOutputRuntime(
            voice_session_manager=None,
            voice_route_resolver=None,
            voice_ingress_runtime=None,
        )
        decision = rt.route_output("s1", "hello", source_type="right_rail")
        self.assertIsInstance(decision, OutputRoutingDecision)
        snap = rt.snapshot()
        self.assertIsInstance(snap.to_dict(), dict)


if __name__ == "__main__":
    unittest.main()
