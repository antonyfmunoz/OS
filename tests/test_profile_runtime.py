"""Tests for Phase 11 — Profile Runtime.

Covers:
  - Enum completeness
  - Data model serialization roundtrips
  - Profile Registry (data-driven, seed, CRUD)
  - System Mode Registry (data-driven, seed, exclusivity groups)
  - Profile Mode State Machine (activate, deactivate, override, transitions)
  - System Mode State Machine (concurrent modes, exclusivity enforcement)
  - Conflict Detector (exclusive pairs, unsafe combos, risk escalation)
  - Profile Activation Planner (plan generation, system mode influence)
  - Profile Timeline (emit, retrieve)
  - Profile Context Assembler (unified context, system mode effects)
  - Profile Runtime (full orchestration, integration, snapshots)
  - Singleton (identity, reset)
  - Acceptance tests (spec requirements)
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import time
import sys
import unittest

sys.path.insert(0, "/opt/OS")

from substrate.organism.profile_runtime import (
    ActivationSource,
    ConflictDetector,
    ConflictSeverity,
    Profile,
    ProfileActivationPlan,
    ProfileActivationPlanner,
    ProfileConflict,
    ProfileContext,
    ProfileContextAssembler,
    ProfileEventType,
    ProfileModeEnum,
    ProfileModeState,
    ProfileModeStateMachine,
    ProfileModeTransition,
    ProfilePreference,
    ProfileRecommendation,
    ProfileRegistry,
    ProfileRuntime,
    ProfileRuntimeSnapshot,
    ProfileTimeline,
    SystemMode,
    SystemModeEnum,
    SystemModeRegistry,
    SystemModeStateMachine,
    get_profile_runtime,
    reset_profile_runtime,
)


# ── Enum Tests ────────────────────────────────────────────────────


class TestProfileModeEnum(unittest.TestCase):
    def test_has_spec_required_modes(self):
        required = {"engineer", "founder", "artist", "content", "research", "admin"}
        values = {m.value for m in ProfileModeEnum}
        self.assertTrue(required.issubset(values))

    def test_all_values_are_strings(self):
        for m in ProfileModeEnum:
            self.assertIsInstance(m.value, str)

    def test_count(self):
        self.assertGreaterEqual(len(ProfileModeEnum), 6)


class TestSystemModeEnum(unittest.TestCase):
    def test_has_spec_required_modes(self):
        required = {"day", "night", "afk", "maintenance", "security", "focus", "emergency"}
        values = {m.value for m in SystemModeEnum}
        self.assertTrue(required.issubset(values))

    def test_all_values_are_strings(self):
        for m in SystemModeEnum:
            self.assertIsInstance(m.value, str)


class TestActivationSource(unittest.TestCase):
    def test_has_spec_required_sources(self):
        required = {"manual", "command", "cockpit", "inferred", "schedule", "restored"}
        values = {s.value for s in ActivationSource}
        self.assertEqual(required, values)


class TestProfileEventType(unittest.TestCase):
    def test_has_required_events(self):
        required = {
            "profile_activated",
            "profile_deactivated",
            "system_mode_activated",
            "system_mode_deactivated",
            "conflict_detected",
            "manual_override",
        }
        values = {e.value for e in ProfileEventType}
        self.assertTrue(required.issubset(values))


class TestConflictSeverity(unittest.TestCase):
    def test_levels(self):
        self.assertEqual(
            {s.value for s in ConflictSeverity},
            {"warning", "error", "critical"},
        )


# ── Data Model Tests ─────────────────────────────────────────────


class TestProfile(unittest.TestCase):
    def test_roundtrip(self):
        p = Profile(
            name="engineer",
            description="test",
            default_workspace_template="engineering",
            preferred_domains=["eng"],
            domain_weights={"eng": 1.0},
        )
        d = p.to_dict()
        p2 = Profile.from_dict(d)
        self.assertEqual(p2.name, "engineer")
        self.assertEqual(p2.domain_weights, {"eng": 1.0})

    def test_auto_id(self):
        p = Profile(name="test")
        self.assertTrue(p.profile_id.startswith("prof-"))


class TestSystemModeModel(unittest.TestCase):
    def test_roundtrip(self):
        m = SystemMode(
            name="day",
            exclusivity_group="time_of_day",
            priority=50,
            effects={"risk_ceiling": "HIGH"},
        )
        d = m.to_dict()
        m2 = SystemMode.from_dict(d)
        self.assertEqual(m2.name, "day")
        self.assertEqual(m2.exclusivity_group, "time_of_day")

    def test_auto_id(self):
        m = SystemMode(name="test")
        self.assertTrue(m.mode_id.startswith("smode-"))


class TestProfileModeState(unittest.TestCase):
    def test_roundtrip(self):
        s = ProfileModeState(
            active_profile_mode="engineer",
            previous_profile_mode="founder",
            activation_source="manual",
            confidence=1.0,
            manual_override=True,
        )
        d = s.to_dict()
        s2 = ProfileModeState.from_dict(d)
        self.assertEqual(s2.active_profile_mode, "engineer")
        self.assertTrue(s2.manual_override)


class TestProfileModeTransition(unittest.TestCase):
    def test_roundtrip(self):
        t = ProfileModeTransition(
            from_mode="founder",
            to_mode="engineer",
            source="command",
        )
        d = t.to_dict()
        t2 = ProfileModeTransition.from_dict(d)
        self.assertEqual(t2.from_mode, "founder")
        self.assertEqual(t2.to_mode, "engineer")

    def test_auto_id(self):
        t = ProfileModeTransition()
        self.assertTrue(t.transition_id.startswith("ptrans-"))


class TestProfilePreference(unittest.TestCase):
    def test_roundtrip(self):
        p = ProfilePreference(
            profile_mode="engineer",
            workspace_template_override="custom",
            panel_overrides=["editor"],
        )
        d = p.to_dict()
        p2 = ProfilePreference.from_dict(d)
        self.assertEqual(p2.profile_mode, "engineer")


class TestProfileContext(unittest.TestCase):
    def test_roundtrip(self):
        c = ProfileContext(
            active_profile="engineer",
            active_system_modes=["day", "focus"],
            domain_weights={"eng": 1.0},
        )
        d = c.to_dict()
        c2 = ProfileContext.from_dict(d)
        self.assertEqual(c2.active_profile, "engineer")
        self.assertEqual(c2.active_system_modes, ["day", "focus"])

    def test_auto_timestamp(self):
        c = ProfileContext()
        self.assertGreater(c.assembled_at, 0)


class TestProfileActivationPlan(unittest.TestCase):
    def test_roundtrip(self):
        p = ProfileActivationPlan(
            target_profile="artist",
            workspace_template_suggestion="music",
            cockpit_panel_preference=["advisor"],
            status="planned",
        )
        d = p.to_dict()
        p2 = ProfileActivationPlan.from_dict(d)
        self.assertEqual(p2.target_profile, "artist")
        self.assertEqual(p2.status, "planned")

    def test_auto_id(self):
        p = ProfileActivationPlan()
        self.assertTrue(p.plan_id.startswith("pplan-"))


class TestProfileRuntimeSnapshot(unittest.TestCase):
    def test_roundtrip(self):
        s = ProfileRuntimeSnapshot(
            profile_state={"active": "engineer"},
            active_system_modes=["day"],
        )
        d = s.to_dict()
        s2 = ProfileRuntimeSnapshot.from_dict(d)
        self.assertEqual(s2.active_system_modes, ["day"])

    def test_auto_id(self):
        s = ProfileRuntimeSnapshot()
        self.assertTrue(s.snapshot_id.startswith("prsnap-"))


class TestProfileConflict(unittest.TestCase):
    def test_roundtrip(self):
        c = ProfileConflict(
            conflict_type="exclusive_violation",
            severity="error",
            description="day and night both active",
            involved_modes=["day", "night"],
        )
        d = c.to_dict()
        c2 = ProfileConflict.from_dict(d)
        self.assertEqual(c2.conflict_type, "exclusive_violation")
        self.assertEqual(c2.involved_modes, ["day", "night"])

    def test_auto_id(self):
        c = ProfileConflict()
        self.assertTrue(c.conflict_id.startswith("pconf-"))


class TestProfileRecommendation(unittest.TestCase):
    def test_roundtrip(self):
        r = ProfileRecommendation(
            recommendation_type="profile_switch",
            title="Switch to engineer",
            source="gap_engine",
            priority=80,
        )
        d = r.to_dict()
        r2 = ProfileRecommendation.from_dict(d)
        self.assertEqual(r2.priority, 80)

    def test_auto_id(self):
        r = ProfileRecommendation()
        self.assertTrue(r.recommendation_id.startswith("prec-"))


# ── Profile Registry Tests ───────────────────────────────────────


class TestProfileRegistry(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_seeds_defaults(self):
        reg = ProfileRegistry(self.tmpdir)
        profiles = reg.all_profiles()
        names = {p.name for p in profiles}
        self.assertIn("engineer", names)
        self.assertIn("founder", names)
        self.assertIn("artist", names)
        self.assertIn("content", names)
        self.assertIn("research", names)
        self.assertIn("admin", names)

    def test_get_by_name(self):
        reg = ProfileRegistry(self.tmpdir)
        p = reg.get("engineer")
        self.assertIsNotNone(p)
        self.assertEqual(p.name, "engineer")

    def test_get_missing(self):
        reg = ProfileRegistry(self.tmpdir)
        self.assertIsNone(reg.get("nonexistent"))

    def test_add_profile(self):
        reg = ProfileRegistry(self.tmpdir)
        new = Profile(name="custom", description="test profile")
        reg.add(new)
        p = reg.get("custom")
        self.assertIsNotNone(p)
        self.assertEqual(p.description, "test profile")

    def test_remove_profile(self):
        reg = ProfileRegistry(self.tmpdir)
        self.assertTrue(reg.remove("engineer"))
        self.assertIsNone(reg.get("engineer"))
        self.assertFalse(reg.remove("nonexistent"))

    def test_persistence(self):
        reg = ProfileRegistry(self.tmpdir)
        reg.add(Profile(name="custom", description="persisted"))
        reg2 = ProfileRegistry(self.tmpdir)
        self.assertIsNotNone(reg2.get("custom"))

    def test_profiles_are_data_driven(self):
        reg = ProfileRegistry(self.tmpdir)
        path = os.path.join(self.tmpdir, "profiles.json")
        self.assertTrue(os.path.exists(path))
        with open(path) as f:
            data = json.load(f)
        self.assertIn("profiles", data)
        self.assertGreaterEqual(len(data["profiles"]), 6)


# ── System Mode Registry Tests ───────────────────────────────────


class TestSystemModeRegistry(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_seeds_defaults(self):
        reg = SystemModeRegistry(self.tmpdir)
        modes = reg.all_modes()
        names = {m.name for m in modes}
        required = {"day", "night", "afk", "maintenance", "security", "focus", "emergency"}
        self.assertTrue(required.issubset(names))

    def test_get_by_name(self):
        reg = SystemModeRegistry(self.tmpdir)
        m = reg.get("day")
        self.assertIsNotNone(m)
        self.assertEqual(m.name, "day")

    def test_exclusivity_group(self):
        reg = SystemModeRegistry(self.tmpdir)
        self.assertEqual(reg.get_exclusivity_group("day"), "time_of_day")
        self.assertEqual(reg.get_exclusivity_group("night"), "time_of_day")
        self.assertEqual(reg.get_exclusivity_group("focus"), "")

    def test_persistence(self):
        reg = SystemModeRegistry(self.tmpdir)
        path = os.path.join(self.tmpdir, "system_modes.json")
        self.assertTrue(os.path.exists(path))

    def test_data_driven(self):
        reg = SystemModeRegistry(self.tmpdir)
        path = os.path.join(self.tmpdir, "system_modes.json")
        with open(path) as f:
            data = json.load(f)
        self.assertIn("system_modes", data)
        self.assertGreaterEqual(len(data["system_modes"]), 7)


# ── Profile Mode State Machine Tests ─────────────────────────────


class TestProfileModeStateMachine(unittest.TestCase):
    def test_activate_profile(self):
        sm = ProfileModeStateMachine()
        transition = sm.activate("engineer", "manual")
        self.assertEqual(transition.to_mode, "engineer")
        self.assertEqual(sm.state.active_profile_mode, "engineer")

    def test_activate_changes_previous(self):
        sm = ProfileModeStateMachine()
        sm.activate("engineer")
        sm.activate("founder")
        self.assertEqual(sm.state.active_profile_mode, "founder")
        self.assertEqual(sm.state.previous_profile_mode, "engineer")

    def test_deactivate(self):
        sm = ProfileModeStateMachine()
        sm.activate("engineer")
        transition = sm.deactivate()
        self.assertIsNotNone(transition)
        self.assertEqual(transition.from_mode, "engineer")
        self.assertEqual(sm.state.active_profile_mode, "")

    def test_deactivate_empty(self):
        sm = ProfileModeStateMachine()
        self.assertIsNone(sm.deactivate())

    def test_manual_override_blocks_non_manual(self):
        sm = ProfileModeStateMachine()
        sm.activate("engineer", source="manual", manual_override=True)
        with self.assertRaises(ValueError):
            sm.activate("founder", source="inferred")

    def test_manual_override_allows_manual(self):
        sm = ProfileModeStateMachine()
        sm.activate("engineer", source="manual", manual_override=True)
        t = sm.activate("founder", source="manual")
        self.assertEqual(t.to_mode, "founder")

    def test_transitions_tracked(self):
        sm = ProfileModeStateMachine()
        sm.activate("engineer")
        sm.activate("founder")
        self.assertEqual(len(sm.transitions), 2)

    def test_confidence(self):
        sm = ProfileModeStateMachine()
        sm.activate("research", source="inferred", confidence=0.7)
        self.assertAlmostEqual(sm.state.confidence, 0.7)

    def test_to_dict(self):
        sm = ProfileModeStateMachine()
        sm.activate("engineer")
        d = sm.to_dict()
        self.assertIn("state", d)
        self.assertIn("transition_count", d)
        self.assertEqual(d["transition_count"], 1)


# ── System Mode State Machine Tests ──────────────────────────────


class TestSystemModeStateMachine(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.registry = SystemModeRegistry(self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_activate(self):
        sm = SystemModeStateMachine(self.registry)
        ok, deactivated = sm.activate("day")
        self.assertTrue(ok)
        self.assertEqual(deactivated, [])
        self.assertIn("day", sm.active_modes)

    def test_activate_unknown(self):
        sm = SystemModeStateMachine(self.registry)
        ok, _ = sm.activate("nonexistent")
        self.assertFalse(ok)

    def test_exclusivity(self):
        sm = SystemModeStateMachine(self.registry)
        sm.activate("day")
        ok, deactivated = sm.activate("night")
        self.assertTrue(ok)
        self.assertIn("day", deactivated)
        self.assertNotIn("day", sm.active_modes)
        self.assertIn("night", sm.active_modes)

    def test_concurrent_modes(self):
        sm = SystemModeStateMachine(self.registry)
        sm.activate("day")
        sm.activate("focus")
        sm.activate("security")
        self.assertEqual(len(sm.active_modes), 3)
        self.assertIn("day", sm.active_modes)
        self.assertIn("focus", sm.active_modes)
        self.assertIn("security", sm.active_modes)

    def test_deactivate(self):
        sm = SystemModeStateMachine(self.registry)
        sm.activate("day")
        self.assertTrue(sm.deactivate("day"))
        self.assertNotIn("day", sm.active_modes)

    def test_deactivate_inactive(self):
        sm = SystemModeStateMachine(self.registry)
        self.assertFalse(sm.deactivate("day"))

    def test_is_active(self):
        sm = SystemModeStateMachine(self.registry)
        sm.activate("focus")
        self.assertTrue(sm.is_active("focus"))
        self.assertFalse(sm.is_active("day"))


# ── Conflict Detector Tests ──────────────────────────────────────


class TestConflictDetector(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.registry = SystemModeRegistry(self.tmpdir)
        self.detector = ConflictDetector(self.registry)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_day_night_exclusive(self):
        conflicts = self.detector.detect("engineer", ["day", "night"])
        self.assertTrue(any(c.conflict_type == "exclusive_violation" for c in conflicts))

    def test_no_conflict_normal(self):
        conflicts = self.detector.detect("engineer", ["day", "focus"])
        exclusives = [c for c in conflicts if c.conflict_type == "exclusive_violation"]
        self.assertEqual(len(exclusives), 0)

    def test_emergency_focus_unsafe(self):
        conflicts = self.detector.detect("engineer", ["emergency", "focus"])
        unsafe = [c for c in conflicts if c.conflict_type == "unsafe_combination"]
        self.assertEqual(len(unsafe), 1)

    def test_security_admin_risk(self):
        conflicts = self.detector.detect("admin", ["security"])
        risk = [c for c in conflicts if c.conflict_type == "risk_escalation"]
        self.assertEqual(len(risk), 1)

    def test_empty_modes_no_conflict(self):
        conflicts = self.detector.detect("engineer", [])
        self.assertEqual(len(conflicts), 0)


# ── Profile Activation Planner Tests ─────────────────────────────


class TestProfileActivationPlanner(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.registry = ProfileRegistry(self.tmpdir)
        self.planner = ProfileActivationPlanner(self.registry)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_plan_engineer(self):
        plan = self.planner.plan("engineer")
        self.assertEqual(plan.target_profile, "engineer")
        self.assertEqual(plan.workspace_template_suggestion, "engineering")
        self.assertEqual(plan.status, "planned")
        self.assertIn("engineering", plan.recommended_active_domains)

    def test_plan_unknown_profile(self):
        plan = self.planner.plan("nonexistent")
        self.assertEqual(plan.status, "error")

    def test_focus_mode_overrides_interruption(self):
        plan = self.planner.plan("founder", ["focus"])
        self.assertEqual(plan.interruption_behavior, "none")

    def test_night_mode_overrides_interruption(self):
        plan = self.planner.plan("founder", ["night"])
        self.assertEqual(plan.interruption_behavior, "critical_only")

    def test_plan_has_all_fields(self):
        plan = self.planner.plan("artist")
        d = plan.to_dict()
        required = {
            "plan_id",
            "target_profile",
            "workspace_template_suggestion",
            "session_preference",
            "cockpit_panel_preference",
            "recommended_active_domains",
            "interruption_behavior",
            "status",
            "created_at",
        }
        self.assertTrue(required.issubset(set(d.keys())))


# ── Profile Timeline Tests ───────────────────────────────────────


class TestProfileTimeline(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_emit_and_retrieve(self):
        tl = ProfileTimeline(self.tmpdir)
        tl.emit("profile_activated", "Test event", {"profile": "engineer"})
        events = tl.get_recent()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event_type"], "profile_activated")

    def test_limit(self):
        tl = ProfileTimeline(self.tmpdir)
        for i in range(10):
            tl.emit("test", f"Event {i}")
        events = tl.get_recent(5)
        self.assertEqual(len(events), 5)

    def test_empty_timeline(self):
        tl = ProfileTimeline(self.tmpdir)
        events = tl.get_recent()
        self.assertEqual(len(events), 0)


# ── Profile Context Assembler Tests ──────────────────────────────


class TestProfileContextAssembler(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.registry = ProfileRegistry(self.tmpdir)
        self.assembler = ProfileContextAssembler(self.registry)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_assemble_engineer(self):
        ctx = self.assembler.assemble("engineer", ["day"])
        self.assertEqual(ctx.active_profile, "engineer")
        self.assertEqual(ctx.active_system_modes, ["day"])
        self.assertEqual(ctx.workspace_template, "engineering")
        self.assertIn("engineering", ctx.preferred_domains)

    def test_focus_mode_effect(self):
        ctx = self.assembler.assemble("founder", ["focus"])
        self.assertEqual(ctx.interruption_preference, "none")
        self.assertEqual(ctx.effective_notification_policy, "critical_only")

    def test_night_mode_effect(self):
        ctx = self.assembler.assemble("engineer", ["night"])
        self.assertEqual(ctx.effective_notification_policy, "critical_only")

    def test_emergency_mode_effect(self):
        ctx = self.assembler.assemble("admin", ["emergency"])
        self.assertEqual(ctx.effective_notification_policy, "all")
        self.assertEqual(ctx.risk_tolerance, "critical")

    def test_unknown_profile_graceful(self):
        ctx = self.assembler.assemble("nonexistent", [])
        self.assertEqual(ctx.active_profile, "nonexistent")
        self.assertEqual(ctx.domain_weights, {})

    def test_has_timestamp(self):
        ctx = self.assembler.assemble("engineer", [])
        self.assertGreater(ctx.assembled_at, 0)


# ── Profile Runtime Tests ────────────────────────────────────────


class TestProfileRuntime(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.rt = ProfileRuntime(self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_activate_profile(self):
        result = self.rt.activate_profile("engineer")
        self.assertTrue(result["success"])
        self.assertEqual(self.rt.get_active_profile(), "engineer")
        self.assertIn("activation_plan", result)

    def test_activate_unknown_profile(self):
        result = self.rt.activate_profile("nonexistent")
        self.assertFalse(result["success"])

    def test_deactivate_profile(self):
        self.rt.activate_profile("engineer")
        result = self.rt.deactivate_profile()
        self.assertTrue(result["success"])
        self.assertEqual(self.rt.get_active_profile(), "")

    def test_deactivate_empty(self):
        result = self.rt.deactivate_profile()
        self.assertFalse(result["success"])

    def test_activate_system_mode(self):
        result = self.rt.activate_system_mode("day")
        self.assertTrue(result["success"])
        self.assertIn("day", self.rt.get_active_system_modes())

    def test_activate_unknown_system_mode(self):
        result = self.rt.activate_system_mode("nonexistent")
        self.assertFalse(result["success"])

    def test_deactivate_system_mode(self):
        self.rt.activate_system_mode("day")
        result = self.rt.deactivate_system_mode("day")
        self.assertTrue(result["success"])
        self.assertNotIn("day", self.rt.get_active_system_modes())

    def test_deactivate_inactive_system_mode(self):
        result = self.rt.deactivate_system_mode("day")
        self.assertFalse(result["success"])

    def test_day_night_exclusivity(self):
        self.rt.activate_system_mode("day")
        result = self.rt.activate_system_mode("night")
        self.assertTrue(result["success"])
        self.assertIn("day", result["deactivated_exclusive"])
        self.assertNotIn("day", self.rt.get_active_system_modes())
        self.assertIn("night", self.rt.get_active_system_modes())

    def test_concurrent_system_modes(self):
        self.rt.activate_system_mode("day")
        self.rt.activate_system_mode("focus")
        self.rt.activate_system_mode("security")
        modes = self.rt.get_active_system_modes()
        self.assertEqual(len(modes), 3)

    def test_profile_activation_produces_plan(self):
        result = self.rt.activate_profile("engineer")
        plan = result["activation_plan"]
        self.assertEqual(plan["target_profile"], "engineer")
        self.assertEqual(plan["status"], "planned")

    def test_get_profiles(self):
        profiles = self.rt.get_profiles()
        names = {p["name"] for p in profiles}
        self.assertIn("engineer", names)
        self.assertIn("founder", names)

    def test_get_system_modes(self):
        modes = self.rt.get_system_modes()
        names = {m["name"] for m in modes}
        self.assertIn("day", names)
        self.assertIn("night", names)

    def test_get_activation_plan(self):
        self.rt.activate_profile("artist")
        plan = self.rt.get_activation_plan()
        self.assertEqual(plan["target_profile"], "artist")

    def test_get_activation_plan_empty(self):
        plan = self.rt.get_activation_plan()
        self.assertEqual(plan, {})

    def test_detect_conflicts(self):
        self.rt.activate_system_mode("emergency")
        self.rt.activate_system_mode("focus")
        conflicts = self.rt.detect_conflicts()
        self.assertGreater(len(conflicts), 0)

    def test_timeline(self):
        self.rt.activate_profile("engineer")
        self.rt.activate_system_mode("day")
        events = self.rt.get_timeline()
        self.assertGreater(len(events), 0)

    def test_get_context(self):
        self.rt.activate_profile("engineer")
        self.rt.activate_system_mode("day")
        ctx = self.rt.get_context()
        self.assertEqual(ctx.active_profile, "engineer")
        self.assertIn("day", ctx.active_system_modes)

    def test_get_domain_weights(self):
        self.rt.activate_profile("engineer")
        weights = self.rt.get_domain_weights()
        self.assertIn("engineering", weights)
        self.assertEqual(weights["engineering"], 1.0)

    def test_get_state(self):
        self.rt.activate_profile("engineer")
        self.rt.activate_system_mode("focus")
        state = self.rt.get_state()
        self.assertIn("profile_state", state)
        self.assertIn("system_modes", state)
        self.assertIn("context", state)
        self.assertIn("conflicts", state)

    def test_capture_snapshot(self):
        self.rt.activate_profile("founder")
        self.rt.activate_system_mode("day")
        snap = self.rt.capture_snapshot()
        self.assertTrue(snap.snapshot_id.startswith("prsnap-"))
        self.assertEqual(snap.profile_state["active_profile_mode"], "founder")
        self.assertIn("day", snap.active_system_modes)

    def test_manual_override_blocks_inferred(self):
        self.rt.activate_profile("engineer", source="manual", manual_override=True)
        result = self.rt.activate_profile("founder", source="inferred")
        self.assertFalse(result["success"])
        self.assertEqual(self.rt.get_active_profile(), "engineer")

    def test_state_persistence(self):
        self.rt.activate_profile("engineer")
        self.rt.activate_system_mode("day")
        rt2 = ProfileRuntime(self.tmpdir)
        self.assertEqual(rt2.get_active_profile(), "engineer")
        self.assertIn("day", rt2.get_active_system_modes())

    def test_profile_switch_with_system_modes(self):
        self.rt.activate_system_mode("night")
        self.rt.activate_system_mode("focus")
        result = self.rt.activate_profile("artist")
        plan = result["activation_plan"]
        self.assertEqual(plan["interruption_behavior"], "none")


# ── Singleton Tests ──────────────────────────────────────────────


class TestSingleton(unittest.TestCase):
    def test_identity(self):
        reset_profile_runtime()
        r1 = get_profile_runtime()
        r2 = get_profile_runtime()
        self.assertIs(r1, r2)

    def test_reset(self):
        reset_profile_runtime()
        r1 = get_profile_runtime()
        reset_profile_runtime()
        r2 = get_profile_runtime()
        self.assertIsNot(r1, r2)


# ── Acceptance Tests ─────────────────────────────────────────────


class TestAcceptance(unittest.TestCase):
    """Spec acceptance tests — each verifies a Phase 11 requirement."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.rt = ProfileRuntime(self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_profile_and_system_modes_are_separate(self):
        """Profiles and system modes are orthogonal — activating one doesn't affect the other."""
        self.rt.activate_profile("engineer")
        self.rt.activate_system_mode("night")
        self.assertEqual(self.rt.get_active_profile(), "engineer")
        self.assertIn("night", self.rt.get_active_system_modes())
        self.rt.activate_system_mode("focus")
        self.assertEqual(self.rt.get_active_profile(), "engineer")
        self.assertEqual(len(self.rt.get_active_system_modes()), 2)

    def test_day_night_exclusivity(self):
        """DAY and NIGHT are mutually exclusive."""
        self.rt.activate_system_mode("day")
        result = self.rt.activate_system_mode("night")
        self.assertIn("day", result["deactivated_exclusive"])
        modes = self.rt.get_active_system_modes()
        self.assertIn("night", modes)
        self.assertNotIn("day", modes)

    def test_manual_override_wins(self):
        """Manual override always wins over non-manual activation."""
        self.rt.activate_profile("engineer", source="manual", manual_override=True)
        result = self.rt.activate_profile("founder", source="schedule")
        self.assertFalse(result["success"])
        self.assertEqual(self.rt.get_active_profile(), "engineer")
        result2 = self.rt.activate_profile("founder", source="manual")
        self.assertTrue(result2["success"])

    def test_profile_activation_produces_plan(self):
        """Profile activation generates a workspace/context plan."""
        result = self.rt.activate_profile("research")
        plan = result["activation_plan"]
        self.assertEqual(plan["status"], "planned")
        self.assertEqual(plan["workspace_template_suggestion"], "research")
        self.assertIn("research", plan["recommended_active_domains"])

    def test_no_execution_occurs(self):
        """Profile Runtime never executes — all plans have status=planned."""
        result = self.rt.activate_profile("engineer")
        self.assertEqual(result["activation_plan"]["status"], "planned")
        state = self.rt.get_state()
        if state.get("latest_plan"):
            self.assertEqual(state["latest_plan"]["status"], "planned")

    def test_conflicts_detected(self):
        """Conflict detection catches invalid combinations."""
        self.rt.activate_system_mode("emergency")
        self.rt.activate_system_mode("focus")
        conflicts = self.rt.detect_conflicts()
        conflict_types = [c.conflict_type for c in conflicts]
        self.assertIn("unsafe_combination", conflict_types)

    def test_full_lifecycle(self):
        """Full lifecycle: activate profile → system modes → switch → deactivate."""
        self.rt.activate_profile("engineer")
        self.rt.activate_system_mode("day")
        self.rt.activate_system_mode("focus")

        self.assertEqual(self.rt.get_active_profile(), "engineer")
        self.assertEqual(len(self.rt.get_active_system_modes()), 2)

        self.rt.activate_profile("founder")
        self.assertEqual(self.rt.get_active_profile(), "founder")
        self.assertEqual(len(self.rt.get_active_system_modes()), 2)

        result = self.rt.activate_system_mode("night")
        self.assertIn("day", result["deactivated_exclusive"])
        self.assertIn("night", self.rt.get_active_system_modes())

        self.rt.deactivate_system_mode("focus")
        self.rt.deactivate_profile()
        self.assertEqual(self.rt.get_active_profile(), "")

    def test_multi_profile_consistency(self):
        """All 6 spec profiles activate correctly."""
        for profile in ["engineer", "founder", "artist", "content", "research", "admin"]:
            result = self.rt.activate_profile(profile)
            self.assertTrue(result["success"], f"Failed to activate {profile}")
            self.assertEqual(self.rt.get_active_profile(), profile)

    def test_all_system_modes_activate(self):
        """All 7 spec system modes activate correctly."""
        for mode in ["day", "night", "afk", "maintenance", "security", "focus", "emergency"]:
            self.rt.activate_system_mode(mode)
        modes = set(self.rt.get_active_system_modes())
        self.assertIn("night", modes)
        self.assertNotIn("day", modes)
        self.assertIn("afk", modes)
        self.assertIn("maintenance", modes)
        self.assertIn("security", modes)
        self.assertIn("focus", modes)
        self.assertIn("emergency", modes)

    def test_domain_weights_influence(self):
        """Profile mode provides domain weights for tick/gap/projection."""
        self.rt.activate_profile("engineer")
        weights = self.rt.get_domain_weights()
        self.assertGreater(weights.get("engineering", 0), weights.get("music", 0))

        self.rt.activate_profile("artist")
        weights = self.rt.get_domain_weights()
        self.assertGreater(weights.get("music", 0), weights.get("engineering", 0))

    def test_snapshot_cycle(self):
        """Snapshot captures and restores full state."""
        self.rt.activate_profile("founder")
        self.rt.activate_system_mode("day")
        snap = self.rt.capture_snapshot()
        d = snap.to_dict()
        snap2 = ProfileRuntimeSnapshot.from_dict(d)
        self.assertEqual(snap2.profile_state["active_profile_mode"], "founder")
        self.assertIn("day", snap2.active_system_modes)


if __name__ == "__main__":
    unittest.main()
