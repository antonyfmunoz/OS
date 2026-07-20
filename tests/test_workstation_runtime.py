"""Tests for Phase 10 — Workstation Runtime.

Covers all canonical types, mode classification, template registry,
context assembly, snapshot store, recommendation engine, preparation
sequencer, restoration plans, and the full WorkstationRuntime orchestrator.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, "/opt/OS")

from substrate.organism.workstation_runtime import (
    ApplicationState,
    ModeClassifier,
    PreparationSequencer,
    PreparationStep,
    PreparationStepType,
    RecommendationEngine,
    RecommendationType,
    RestorationPlan,
    SnapshotStore,
    SnapshotTrigger,
    WorkspaceContextAssembler,
    WorkspacePreparationPlan,
    WorkspaceSequence,
    WorkspaceSnapshot,
    WorkspaceState,
    WorkspaceStatus,
    WorkspaceTemplate,
    WorkspaceTemplateRegistry,
    Workstation,
    WorkstationMode,
    WorkstationProfile,
    WorkstationRecommendation,
    WorkstationRuntime,
    get_workstation_runtime,
    reset_workstation_runtime,
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Enum tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestWorkstationMode(unittest.TestCase):
    def test_all_modes(self) -> None:
        modes = list(WorkstationMode)
        self.assertEqual(len(modes), 6)
        self.assertIn(WorkstationMode.ENGINEERING, modes)
        self.assertIn(WorkstationMode.CONTENT, modes)
        self.assertIn(WorkstationMode.MUSIC, modes)
        self.assertIn(WorkstationMode.BUSINESS, modes)
        self.assertIn(WorkstationMode.RESEARCH, modes)
        self.assertIn(WorkstationMode.ADMIN, modes)

    def test_values(self) -> None:
        self.assertEqual(WorkstationMode.ENGINEERING.value, "engineering")
        self.assertEqual(WorkstationMode.MUSIC.value, "music")


class TestWorkspaceStatus(unittest.TestCase):
    def test_terminal(self) -> None:
        self.assertTrue(WorkspaceStatus.ARCHIVED.is_terminal)
        self.assertFalse(WorkspaceStatus.PLANNED.is_terminal)
        self.assertFalse(WorkspaceStatus.ACTIVE.is_terminal)
        self.assertFalse(WorkspaceStatus.READY.is_terminal)
        self.assertFalse(WorkspaceStatus.SUSPENDED.is_terminal)


class TestPreparationStepType(unittest.TestCase):
    def test_all_types(self) -> None:
        types = list(PreparationStepType)
        self.assertEqual(len(types), 6)


class TestSnapshotTrigger(unittest.TestCase):
    def test_all_triggers(self) -> None:
        triggers = list(SnapshotTrigger)
        self.assertEqual(len(triggers), 5)


class TestRecommendationType(unittest.TestCase):
    def test_all_types(self) -> None:
        types = list(RecommendationType)
        self.assertEqual(len(types), 7)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Data model tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestWorkspaceTemplate(unittest.TestCase):
    def test_roundtrip(self) -> None:
        tpl = WorkspaceTemplate(
            template_id="tpl-test",
            mode="engineering",
            label="Test",
            required_applications=["vscode"],
            required_repositories=["OS"],
            recommended_cockpit_panels=["work"],
            recommended_browser_tabs=["github"],
            required_context_sources=["continuity"],
            description="Test template",
        )
        d = tpl.to_dict()
        restored = WorkspaceTemplate.from_dict(d)
        self.assertEqual(restored.template_id, "tpl-test")
        self.assertEqual(restored.mode, "engineering")
        self.assertEqual(restored.required_applications, ["vscode"])

    def test_defaults(self) -> None:
        tpl = WorkspaceTemplate()
        self.assertEqual(tpl.template_id, "")
        self.assertEqual(tpl.required_applications, [])


class TestPreparationStep(unittest.TestCase):
    def test_roundtrip(self) -> None:
        step = PreparationStep(
            step_type="application",
            target="vscode",
            reason="Required",
            priority=100,
        )
        d = step.to_dict()
        restored = PreparationStep.from_dict(d)
        self.assertEqual(restored.step_type, "application")
        self.assertEqual(restored.target, "vscode")
        self.assertEqual(restored.priority, 100)


class TestWorkspacePreparationPlan(unittest.TestCase):
    def test_auto_id(self) -> None:
        plan = WorkspacePreparationPlan(intent="test")
        self.assertTrue(plan.plan_id.startswith("wsp-"))
        self.assertGreater(plan.created_at, 0)

    def test_roundtrip(self) -> None:
        plan = WorkspacePreparationPlan(
            mode="engineering",
            intent="build operator",
            steps=[PreparationStep(step_type="application", target="vscode")],
        )
        d = plan.to_dict()
        restored = WorkspacePreparationPlan.from_dict(d)
        self.assertEqual(restored.mode, "engineering")
        self.assertEqual(len(restored.steps), 1)
        self.assertEqual(restored.steps[0].target, "vscode")


class TestApplicationState(unittest.TestCase):
    def test_roundtrip(self) -> None:
        app = ApplicationState(name="vscode", running=True, window_title="OS")
        d = app.to_dict()
        restored = ApplicationState.from_dict(d)
        self.assertEqual(restored.name, "vscode")
        self.assertTrue(restored.running)


class TestWorkspaceState(unittest.TestCase):
    def test_roundtrip(self) -> None:
        state = WorkspaceState(
            mode="engineering",
            applications=[ApplicationState(name="vscode", running=True)],
            active_panels=["work"],
        )
        d = state.to_dict()
        restored = WorkspaceState.from_dict(d)
        self.assertEqual(restored.mode, "engineering")
        self.assertEqual(len(restored.applications), 1)
        self.assertEqual(restored.applications[0].name, "vscode")


class TestWorkspaceSnapshot(unittest.TestCase):
    def test_auto_id(self) -> None:
        snap = WorkspaceSnapshot()
        self.assertTrue(snap.snapshot_id.startswith("snap-"))
        self.assertGreater(snap.created_at, 0)

    def test_roundtrip(self) -> None:
        snap = WorkspaceSnapshot(
            trigger="manual",
            open_objectives=["build operator"],
            active_profile="engineering",
            operator_notes="test note",
        )
        d = snap.to_dict()
        restored = WorkspaceSnapshot.from_dict(d)
        self.assertEqual(restored.trigger, "manual")
        self.assertEqual(restored.open_objectives, ["build operator"])
        self.assertEqual(restored.operator_notes, "test note")


class TestRestorationPlan(unittest.TestCase):
    def test_auto_id(self) -> None:
        plan = RestorationPlan()
        self.assertTrue(plan.restoration_id.startswith("rst-"))

    def test_roundtrip(self) -> None:
        plan = RestorationPlan(
            target_mode="engineering",
            objectives_to_restore=["build"],
            operator_notes="resuming",
        )
        d = plan.to_dict()
        restored = RestorationPlan.from_dict(d)
        self.assertEqual(restored.target_mode, "engineering")
        self.assertEqual(restored.operator_notes, "resuming")


class TestWorkspaceSequence(unittest.TestCase):
    def test_auto_id(self) -> None:
        seq = WorkspaceSequence(mode="engineering")
        self.assertTrue(seq.sequence_id.startswith("seq-"))

    def test_to_dict(self) -> None:
        seq = WorkspaceSequence(
            mode="engineering",
            steps=[PreparationStep(step_type="application", target="vscode")],
            estimated_items=1,
        )
        d = seq.to_dict()
        self.assertEqual(d["mode"], "engineering")
        self.assertEqual(d["estimated_items"], 1)


class TestWorkstationProfile(unittest.TestCase):
    def test_roundtrip(self) -> None:
        profile = WorkstationProfile(
            profile_mode="engineering",
            preferred_template="tpl-engineering",
            preferred_panels=["work", "execution"],
        )
        d = profile.to_dict()
        restored = WorkstationProfile.from_dict(d)
        self.assertEqual(restored.profile_mode, "engineering")
        self.assertEqual(restored.preferred_panels, ["work", "execution"])


class TestWorkstation(unittest.TestCase):
    def test_auto_id(self) -> None:
        ws = Workstation(operator_id="op-1")
        self.assertTrue(ws.workstation_id.startswith("ws-"))

    def test_roundtrip_with_profiles(self) -> None:
        ws = Workstation(
            operator_id="op-1",
            current_mode="engineering",
            profiles=[WorkstationProfile(profile_mode="engineering")],
        )
        d = ws.to_dict()
        restored = Workstation.from_dict(d)
        self.assertEqual(restored.operator_id, "op-1")
        self.assertEqual(len(restored.profiles), 1)
        self.assertEqual(restored.profiles[0].profile_mode, "engineering")


class TestWorkstationRecommendation(unittest.TestCase):
    def test_auto_id(self) -> None:
        rec = WorkstationRecommendation(title="Test")
        self.assertTrue(rec.recommendation_id.startswith("rec-"))

    def test_to_dict(self) -> None:
        rec = WorkstationRecommendation(
            recommendation_type="resume_work",
            title="Resume coding",
            source_system="continuity",
            priority=80,
        )
        d = rec.to_dict()
        self.assertEqual(d["recommendation_type"], "resume_work")
        self.assertEqual(d["priority"], 80)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Mode Classifier
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestModeClassifier(unittest.TestCase):
    def setUp(self) -> None:
        self.classifier = ModeClassifier()

    def test_engineering_intent(self) -> None:
        mode, conf = self.classifier.classify("Work on the operator runtime code")
        self.assertEqual(mode, WorkstationMode.ENGINEERING)
        self.assertGreater(conf, 0.3)

    def test_content_intent(self) -> None:
        mode, conf = self.classifier.classify("Write a blog post about marketing")
        self.assertEqual(mode, WorkstationMode.CONTENT)
        self.assertGreater(conf, 0.3)

    def test_music_intent(self) -> None:
        mode, conf = self.classifier.classify("Produce a new beat in the studio")
        self.assertEqual(mode, WorkstationMode.MUSIC)
        self.assertGreater(conf, 0.3)

    def test_business_intent(self) -> None:
        mode, conf = self.classifier.classify("Review revenue forecast and client pipeline")
        self.assertEqual(mode, WorkstationMode.BUSINESS)
        self.assertGreater(conf, 0.3)

    def test_research_intent(self) -> None:
        mode, conf = self.classifier.classify("Investigate and analyze the benchmark data")
        self.assertEqual(mode, WorkstationMode.RESEARCH)
        self.assertGreater(conf, 0.3)

    def test_admin_intent(self) -> None:
        mode, conf = self.classifier.classify("Configure the backup schedule and monitor logs")
        self.assertEqual(mode, WorkstationMode.ADMIN)
        self.assertGreater(conf, 0.3)

    def test_empty_input(self) -> None:
        mode, conf = self.classifier.classify("")
        self.assertEqual(mode, WorkstationMode.ENGINEERING)
        self.assertEqual(conf, 0.3)

    def test_ambiguous_defaults_to_engineering(self) -> None:
        mode, conf = self.classifier.classify("hello world")
        self.assertEqual(mode, WorkstationMode.ENGINEERING)
        self.assertEqual(conf, 0.3)

    def test_mixed_signals(self) -> None:
        mode, _ = self.classifier.classify(
            "deploy the code and fix the build pipeline"
        )
        self.assertEqual(mode, WorkstationMode.ENGINEERING)

    def test_case_insensitive(self) -> None:
        mode, _ = self.classifier.classify("WRITE CONTENT FOR YOUTUBE")
        self.assertEqual(mode, WorkstationMode.CONTENT)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Template Registry
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestWorkspaceTemplateRegistry(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp()
        self.registry = WorkspaceTemplateRegistry(templates_dir=self.tmpdir)

    def test_seeds_defaults(self) -> None:
        templates = self.registry.all_templates()
        self.assertEqual(len(templates), 6)
        modes = {t.mode for t in templates}
        self.assertEqual(
            modes,
            {"engineering", "content", "music", "business", "research", "admin"},
        )

    def test_get_by_mode(self) -> None:
        tpl = self.registry.get_by_mode("engineering")
        self.assertIsNotNone(tpl)
        self.assertEqual(tpl.mode, "engineering")
        self.assertIn("vscode", tpl.required_applications)

    def test_get_by_id(self) -> None:
        tpl = self.registry.get("tpl-engineering")
        self.assertIsNotNone(tpl)
        self.assertEqual(tpl.template_id, "tpl-engineering")

    def test_add_custom_template(self) -> None:
        custom = WorkspaceTemplate(
            template_id="tpl-custom",
            mode="custom",
            label="Custom",
            required_applications=["vim"],
        )
        self.registry.add(custom)
        self.assertEqual(len(self.registry.all_templates()), 7)
        retrieved = self.registry.get("tpl-custom")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.required_applications, ["vim"])

    def test_remove(self) -> None:
        self.assertTrue(self.registry.remove("tpl-music"))
        self.assertEqual(len(self.registry.all_templates()), 5)
        self.assertFalse(self.registry.remove("nonexistent"))

    def test_persistence(self) -> None:
        self.registry.add(WorkspaceTemplate(
            template_id="tpl-persist", mode="persist", label="Persist"
        ))
        registry2 = WorkspaceTemplateRegistry(templates_dir=self.tmpdir)
        self.assertIsNotNone(registry2.get("tpl-persist"))

    def test_missing_template_returns_none(self) -> None:
        self.assertIsNone(self.registry.get("nonexistent"))
        self.assertIsNone(self.registry.get_by_mode("nonexistent"))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Context Assembler
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestWorkspaceContextAssembler(unittest.TestCase):
    def test_assemble_returns_all_sections(self) -> None:
        assembler = WorkspaceContextAssembler()
        ctx = assembler.assemble()
        self.assertIn("continuity", ctx)
        self.assertIn("presence", ctx)
        self.assertIn("strategy", ctx)
        self.assertIn("tick_loop", ctx)
        self.assertIn("projections", ctx)
        self.assertIn("reality_model", ctx)
        self.assertIn("work_packets", ctx)
        self.assertIn("assembled_at", ctx)
        self.assertGreater(ctx["assembled_at"], 0)

    def test_graceful_degradation(self) -> None:
        assembler = WorkspaceContextAssembler()
        ctx = assembler.assemble()
        self.assertIsInstance(ctx, dict)
        self.assertEqual(len(ctx), 8)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Snapshot Store
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestSnapshotStore(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp()
        self.store = SnapshotStore(data_dir=self.tmpdir)

    def test_save_and_retrieve(self) -> None:
        snap = WorkspaceSnapshot(
            trigger="manual",
            active_profile="engineering",
            operator_notes="test",
        )
        self.store.save(snap)
        recent = self.store.get_recent()
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0]["snapshot_id"], snap.snapshot_id)

    def test_get_by_id(self) -> None:
        snap = WorkspaceSnapshot(trigger="manual")
        self.store.save(snap)
        found = self.store.get_by_id(snap.snapshot_id)
        self.assertIsNotNone(found)
        self.assertEqual(found["snapshot_id"], snap.snapshot_id)

    def test_get_latest(self) -> None:
        snap1 = WorkspaceSnapshot(trigger="manual")
        snap1.created_at = time.time() - 100
        snap2 = WorkspaceSnapshot(trigger="scheduled")
        snap2.created_at = time.time()
        self.store.save(snap1)
        self.store.save(snap2)
        latest = self.store.get_latest()
        self.assertIsNotNone(latest)
        self.assertEqual(latest["snapshot_id"], snap2.snapshot_id)

    def test_empty_store(self) -> None:
        self.assertEqual(self.store.get_recent(), [])
        self.assertIsNone(self.store.get_latest())
        self.assertIsNone(self.store.get_by_id("nonexistent"))

    def test_limit(self) -> None:
        for i in range(5):
            snap = WorkspaceSnapshot(trigger="manual")
            snap.created_at = time.time() + i
            self.store.save(snap)
        recent = self.store.get_recent(limit=3)
        self.assertEqual(len(recent), 3)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Recommendation Engine
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestRecommendationEngine(unittest.TestCase):
    def test_generate_returns_list(self) -> None:
        engine = RecommendationEngine()
        recs = engine.generate()
        self.assertIsInstance(recs, list)

    def test_recommendations_sorted_by_priority(self) -> None:
        engine = RecommendationEngine()
        recs = engine.generate()
        if len(recs) >= 2:
            for i in range(len(recs) - 1):
                self.assertGreaterEqual(recs[i].priority, recs[i + 1].priority)

    def test_blocked_work_packet_recommendation(self) -> None:
        tmpdir = tempfile.mkdtemp()
        wp_dir = os.path.join(tmpdir, "data", "runtime", "umh", "universal_work")
        os.makedirs(wp_dir)
        wp_path = os.path.join(wp_dir, "work_packets.jsonl")
        with open(wp_path, "w") as f:
            f.write(json.dumps({
                "packet_id": "wp-test-1",
                "title": "Blocked packet",
                "status": "blocked",
            }) + "\n")

        engine = RecommendationEngine()
        old_root = os.environ.get("UMH_ROOT", "")
        os.environ["UMH_ROOT"] = tmpdir
        try:
            recs = engine.generate()
            blocked_recs = [
                r for r in recs
                if r.recommendation_type == RecommendationType.REVIEW_BLOCKED.value
            ]
            self.assertGreaterEqual(len(blocked_recs), 1)
        finally:
            if old_root:
                os.environ["UMH_ROOT"] = old_root
            else:
                os.environ.pop("UMH_ROOT", None)

    def test_pending_approval_recommendation(self) -> None:
        tmpdir = tempfile.mkdtemp()
        wp_dir = os.path.join(tmpdir, "data", "runtime", "umh", "universal_work")
        os.makedirs(wp_dir)
        wp_path = os.path.join(wp_dir, "work_packets.jsonl")
        with open(wp_path, "w") as f:
            f.write(json.dumps({
                "packet_id": "wp-test-2",
                "title": "Needs approval",
                "status": "pending_approval",
            }) + "\n")

        engine = RecommendationEngine()
        old_root = os.environ.get("UMH_ROOT", "")
        os.environ["UMH_ROOT"] = tmpdir
        try:
            recs = engine.generate()
            approval_recs = [
                r for r in recs
                if r.recommendation_type == RecommendationType.APPROVE_PROPOSAL.value
            ]
            self.assertGreaterEqual(len(approval_recs), 1)
        finally:
            if old_root:
                os.environ["UMH_ROOT"] = old_root
            else:
                os.environ.pop("UMH_ROOT", None)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Preparation Sequencer
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestPreparationSequencer(unittest.TestCase):
    def setUp(self) -> None:
        self.sequencer = PreparationSequencer()

    def test_sequence_from_template(self) -> None:
        tpl = WorkspaceTemplate(
            template_id="tpl-test",
            mode="engineering",
            label="Engineering",
            required_applications=["vscode", "terminal"],
            required_repositories=["OS"],
            recommended_cockpit_panels=["work"],
            recommended_browser_tabs=["github"],
            required_context_sources=["continuity"],
        )
        seq = self.sequencer.sequence(tpl)
        self.assertEqual(seq.mode, "engineering")
        self.assertEqual(seq.estimated_items, 6)
        self.assertEqual(len(seq.steps), 6)

        types = [s.step_type for s in seq.steps]
        self.assertIn("application", types)
        self.assertIn("repository", types)
        self.assertIn("cockpit_panel", types)
        self.assertIn("browser_tab", types)
        self.assertIn("context_source", types)

    def test_sequence_with_work_packets(self) -> None:
        tpl = WorkspaceTemplate(
            template_id="tpl-test",
            mode="engineering",
            label="Engineering",
            required_applications=["vscode"],
        )
        packets = [
            {"packet_id": "wp-1", "title": "Fix bug"},
            {"packet_id": "wp-2", "title": "Deploy"},
        ]
        seq = self.sequencer.sequence(tpl, work_packets=packets)
        self.assertEqual(seq.estimated_items, 3)
        wp_steps = [
            s for s in seq.steps
            if s.step_type == PreparationStepType.WORK_PACKET.value
        ]
        self.assertEqual(len(wp_steps), 2)

    def test_priority_ordering(self) -> None:
        tpl = WorkspaceTemplate(
            template_id="tpl-test",
            mode="engineering",
            label="Engineering",
            required_applications=["vscode", "terminal"],
            required_repositories=["OS"],
        )
        seq = self.sequencer.sequence(tpl)
        priorities = [s.priority for s in seq.steps]
        self.assertEqual(priorities, sorted(priorities, reverse=True))

    def test_empty_template(self) -> None:
        tpl = WorkspaceTemplate(template_id="tpl-empty", mode="empty", label="Empty")
        seq = self.sequencer.sequence(tpl)
        self.assertEqual(seq.estimated_items, 0)
        self.assertEqual(len(seq.steps), 0)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Workstation Runtime (orchestrator)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestWorkstationRuntime(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp()
        self._old_root = os.environ.get("UMH_ROOT", "")
        os.environ["UMH_ROOT"] = self.tmpdir
        os.makedirs(os.path.join(self.tmpdir, "data", "umh", "workstation", "snapshots"), exist_ok=True)
        os.makedirs(os.path.join(self.tmpdir, "data", "umh", "workstation", "templates"), exist_ok=True)
        reset_workstation_runtime()

    def tearDown(self) -> None:
        if self._old_root:
            os.environ["UMH_ROOT"] = self._old_root
        else:
            os.environ.pop("UMH_ROOT", None)
        reset_workstation_runtime()

    def test_prepare_workspace_engineering(self) -> None:
        rt = WorkstationRuntime()
        plan = rt.prepare_workspace("Work on the operator runtime code")
        self.assertEqual(plan.mode, "engineering")
        self.assertTrue(plan.plan_id.startswith("wsp-"))
        self.assertEqual(plan.status, WorkspaceStatus.PLANNED.value)
        self.assertGreater(len(plan.steps), 0)
        self.assertIn("mode", plan.context_summary)

    def test_prepare_workspace_content(self) -> None:
        rt = WorkstationRuntime()
        plan = rt.prepare_workspace("Write blog posts for social media marketing")
        self.assertEqual(plan.mode, "content")

    def test_prepare_workspace_with_profile(self) -> None:
        rt = WorkstationRuntime()
        plan = rt.prepare_workspace(
            "Deploy the service",
            profile_mode="devops",
            operator_id="op-1",
        )
        self.assertEqual(plan.profile_mode, "devops")
        self.assertEqual(plan.operator_id, "op-1")

    def test_get_templates(self) -> None:
        rt = WorkstationRuntime()
        templates = rt.get_templates()
        self.assertEqual(len(templates), 6)
        modes = {t["mode"] for t in templates}
        self.assertEqual(
            modes,
            {"engineering", "content", "music", "business", "research", "admin"},
        )

    def test_take_and_list_snapshots(self) -> None:
        rt = WorkstationRuntime()
        snap = rt.take_snapshot(operator_notes="test snap")
        self.assertTrue(snap.snapshot_id.startswith("snap-"))
        self.assertEqual(snap.operator_notes, "test snap")

        snaps = rt.get_snapshots()
        self.assertEqual(len(snaps), 1)
        self.assertEqual(snaps[0]["snapshot_id"], snap.snapshot_id)

    def test_restore_workspace_without_snapshot(self) -> None:
        rt = WorkstationRuntime()
        plan = rt.restore_workspace()
        self.assertTrue(plan.restoration_id.startswith("rst-"))
        self.assertEqual(plan.target_mode, "engineering")

    def test_restore_workspace_from_snapshot(self) -> None:
        rt = WorkstationRuntime()
        snap = rt.take_snapshot(operator_notes="before switch")
        plan = rt.restore_workspace(snapshot_id=snap.snapshot_id)
        self.assertEqual(plan.source_snapshot_id, snap.snapshot_id)
        self.assertEqual(plan.operator_notes, "before switch")

    def test_get_recommendations(self) -> None:
        rt = WorkstationRuntime()
        recs = rt.get_recommendations()
        self.assertIsInstance(recs, list)

    def test_get_state(self) -> None:
        rt = WorkstationRuntime()
        state = rt.get_state()
        self.assertIn("templates_available", state)
        self.assertEqual(state["templates_available"], 6)

    def test_state_updates_after_prepare(self) -> None:
        rt = WorkstationRuntime()
        rt.prepare_workspace("Write content for youtube channel")
        state = rt.get_state()
        self.assertEqual(state["mode"], "content")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Singleton
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestSingleton(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp()
        self._old_root = os.environ.get("UMH_ROOT", "")
        os.environ["UMH_ROOT"] = self.tmpdir
        os.makedirs(os.path.join(self.tmpdir, "data", "umh", "workstation", "snapshots"), exist_ok=True)
        os.makedirs(os.path.join(self.tmpdir, "data", "umh", "workstation", "templates"), exist_ok=True)
        reset_workstation_runtime()

    def tearDown(self) -> None:
        if self._old_root:
            os.environ["UMH_ROOT"] = self._old_root
        else:
            os.environ.pop("UMH_ROOT", None)
        reset_workstation_runtime()

    def test_singleton_identity(self) -> None:
        a = get_workstation_runtime()
        b = get_workstation_runtime()
        self.assertIs(a, b)

    def test_reset_creates_new(self) -> None:
        a = get_workstation_runtime()
        reset_workstation_runtime()
        b = get_workstation_runtime()
        self.assertIsNot(a, b)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Acceptance Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestAcceptance(unittest.TestCase):
    """End-to-end acceptance tests matching the spec scenarios."""

    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp()
        self._old_root = os.environ.get("UMH_ROOT", "")
        os.environ["UMH_ROOT"] = self.tmpdir
        os.makedirs(os.path.join(self.tmpdir, "data", "umh", "workstation", "snapshots"), exist_ok=True)
        os.makedirs(os.path.join(self.tmpdir, "data", "umh", "workstation", "templates"), exist_ok=True)
        reset_workstation_runtime()

    def tearDown(self) -> None:
        if self._old_root:
            os.environ["UMH_ROOT"] = self._old_root
        else:
            os.environ.pop("UMH_ROOT", None)
        reset_workstation_runtime()

    def test_acceptance_work_on_operator(self) -> None:
        """Spec scenario: 'Work on Operator' → engineering template, full plan."""
        rt = WorkstationRuntime()
        plan = rt.prepare_workspace("Work on Operator")

        self.assertEqual(plan.mode, "engineering")
        self.assertEqual(plan.template_id, "tpl-engineering")
        self.assertGreater(len(plan.steps), 0)
        self.assertIsInstance(plan.continuity_context, dict)
        self.assertIsInstance(plan.projection_context, dict)
        self.assertEqual(plan.status, "planned")
        self.assertIsInstance(plan.active_work_packets, list)
        self.assertIsInstance(plan.recommendations, list)

        app_steps = [
            s for s in plan.steps
            if s.step_type == PreparationStepType.APPLICATION.value
        ]
        self.assertGreater(len(app_steps), 0)
        targets = [s.target for s in app_steps]
        self.assertIn("vscode", targets)

    def test_acceptance_no_execution(self) -> None:
        """Verify that prepare_workspace never executes — only plans."""
        rt = WorkstationRuntime()
        plan = rt.prepare_workspace("Deploy all services")
        self.assertEqual(plan.status, "planned")
        self.assertNotEqual(plan.status, "active")
        self.assertNotEqual(plan.status, "completed")

    def test_acceptance_snapshot_restore_cycle(self) -> None:
        """Snapshot → restore cycle preserves context."""
        rt = WorkstationRuntime()
        rt.prepare_workspace("Write content for the newsletter")
        snap = rt.take_snapshot(operator_notes="mid-session save")
        plan = rt.restore_workspace(snapshot_id=snap.snapshot_id)
        self.assertEqual(plan.source_snapshot_id, snap.snapshot_id)
        self.assertEqual(plan.operator_notes, "mid-session save")

    def test_acceptance_template_data_driven(self) -> None:
        """Templates are data-driven, not hardcoded."""
        rt = WorkstationRuntime()
        templates = rt.get_templates()
        for tpl in templates:
            self.assertIn("template_id", tpl)
            self.assertIn("mode", tpl)
            self.assertIn("required_applications", tpl)
            self.assertIsInstance(tpl["required_applications"], list)

    def test_acceptance_recommendations_deterministic(self) -> None:
        """Recommendations come from subsystems, no LLM calls."""
        rt = WorkstationRuntime()
        recs = rt.get_recommendations()
        self.assertIsInstance(recs, list)
        for rec in recs:
            self.assertIn("source_system", rec)
            self.assertIn(rec["source_system"], {
                "strategic_gap_engine", "projection_engine",
                "tick_loop", "work_packets",
            })

    def test_acceptance_governance_maintained(self) -> None:
        """Plan status stays 'planned' — governance prevents auto-execution."""
        rt = WorkstationRuntime()
        plan = rt.prepare_workspace("Build everything")
        self.assertEqual(plan.status, "planned")
        state = rt.get_state()
        self.assertIn("mode", state)

    def test_acceptance_full_lifecycle(self) -> None:
        """Full lifecycle: prepare → snapshot → switch mode → restore."""
        rt = WorkstationRuntime()

        plan1 = rt.prepare_workspace("Work on the codebase and deploy services")
        self.assertEqual(plan1.mode, "engineering")

        snap = rt.take_snapshot(operator_notes="switching to content")

        plan2 = rt.prepare_workspace("Write blog posts for audience")
        self.assertEqual(plan2.mode, "content")

        restored = rt.restore_workspace(snapshot_id=snap.snapshot_id)
        self.assertEqual(restored.source_snapshot_id, snap.snapshot_id)
        self.assertEqual(restored.operator_notes, "switching to content")

    def test_acceptance_multi_mode_consistency(self) -> None:
        """Different intents produce different modes but same structure."""
        rt = WorkstationRuntime()

        intents = [
            ("Code the API endpoint", "engineering"),
            ("Write the newsletter", "content"),
            ("Mix the new track", "music"),
            ("Review client contracts", "business"),
            ("Analyze the benchmark results", "research"),
            ("Configure the backup schedule", "admin"),
        ]

        for intent, expected_mode in intents:
            plan = rt.prepare_workspace(intent)
            self.assertEqual(plan.mode, expected_mode, f"Failed for: {intent}")
            self.assertGreater(len(plan.steps), 0, f"No steps for: {intent}")
            self.assertTrue(plan.plan_id.startswith("wsp-"))
            self.assertEqual(plan.status, "planned")

    def test_acceptance_context_assembly_complete(self) -> None:
        """Context assembly pulls from all subsystems."""
        rt = WorkstationRuntime()
        plan = rt.prepare_workspace("Work on Operator")
        ctx = plan.context_summary
        self.assertIn("classification_confidence", ctx)
        self.assertIn("mode", ctx)
        self.assertIn("template", ctx)


if __name__ == "__main__":
    unittest.main()
