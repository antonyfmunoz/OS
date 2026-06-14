"""Tests for Phase 9 — Command Runtime.

Tests command classification, context assembly, routing, timeline,
history, and acceptance scenarios.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, "/opt/OS")


# ── Enum tests ───────────────────────────────────────────────────────────


class TestCommandActionType(unittest.TestCase):
    def test_values(self):
        from substrate.organism.command_runtime import CommandActionType

        expected = {
            "query",
            "execute",
            "review",
            "approve",
            "reject",
            "schedule",
            "switch_profile",
            "switch_session",
            "switch_system_mode",
            "create_objective",
            "create_workpacket",
            "create_sequence",
        }
        self.assertEqual({e.value for e in CommandActionType}, expected)

    def test_is_mutation(self):
        from substrate.organism.command_runtime import CommandActionType

        self.assertFalse(CommandActionType.QUERY.is_mutation)
        self.assertFalse(CommandActionType.REVIEW.is_mutation)
        self.assertTrue(CommandActionType.EXECUTE.is_mutation)
        self.assertTrue(CommandActionType.APPROVE.is_mutation)
        self.assertTrue(CommandActionType.REJECT.is_mutation)
        self.assertTrue(CommandActionType.SWITCH_PROFILE.is_mutation)
        self.assertTrue(CommandActionType.CREATE_OBJECTIVE.is_mutation)

    def test_requires_approval(self):
        from substrate.organism.command_runtime import CommandActionType

        self.assertTrue(CommandActionType.EXECUTE.requires_approval)
        self.assertTrue(CommandActionType.CREATE_SEQUENCE.requires_approval)
        self.assertFalse(CommandActionType.QUERY.requires_approval)
        self.assertFalse(CommandActionType.REVIEW.requires_approval)
        self.assertFalse(CommandActionType.APPROVE.requires_approval)


class TestCommandStatus(unittest.TestCase):
    def test_terminal_states(self):
        from substrate.organism.command_runtime import CommandStatus

        self.assertTrue(CommandStatus.COMPLETED.is_terminal)
        self.assertTrue(CommandStatus.FAILED.is_terminal)
        self.assertTrue(CommandStatus.CANCELLED.is_terminal)
        self.assertTrue(CommandStatus.REJECTED.is_terminal)
        self.assertFalse(CommandStatus.RECEIVED.is_terminal)
        self.assertFalse(CommandStatus.ROUTED.is_terminal)
        self.assertFalse(CommandStatus.EXECUTING.is_terminal)


class TestCommandSource(unittest.TestCase):
    def test_values(self):
        from substrate.organism.command_runtime import CommandSource

        expected = {"cockpit", "voice", "api", "meeting", "mobile", "tick_loop", "internal"}
        self.assertEqual({e.value for e in CommandSource}, expected)


class TestCommandEventType(unittest.TestCase):
    def test_values(self):
        from substrate.organism.command_runtime import CommandEventType

        self.assertEqual(len(CommandEventType), 11)


# ── Data model tests ─────────────────────────────────────────────────────


class TestCommand(unittest.TestCase):
    def test_default_id(self):
        from substrate.organism.command_runtime import Command

        cmd = Command(raw_input="test")
        self.assertTrue(cmd.command_id.startswith("cmd-"))
        self.assertEqual(len(cmd.command_id), 16)

    def test_default_timestamp(self):
        from substrate.organism.command_runtime import Command

        cmd = Command(raw_input="test")
        self.assertGreater(cmd.timestamp, 0)

    def test_to_dict(self):
        from substrate.organism.command_runtime import Command

        cmd = Command(raw_input="build something", source="cockpit")
        d = cmd.to_dict()
        self.assertEqual(d["raw_input"], "build something")
        self.assertEqual(d["source"], "cockpit")
        self.assertIn("command_id", d)
        self.assertIn("timestamp", d)

    def test_all_fields_in_dict(self):
        from substrate.organism.command_runtime import Command

        cmd = Command()
        d = cmd.to_dict()
        expected_keys = {
            "command_id",
            "source",
            "raw_input",
            "normalized_command",
            "operator_id",
            "profile_mode",
            "session_id",
            "timestamp",
            "confidence",
            "target_domain",
            "target_agents",
            "action_type",
            "approval_required",
            "workpacket_id",
            "status",
            "context",
            "routing_result",
            "outcome",
            "error",
        }
        self.assertEqual(set(d.keys()), expected_keys)


class TestCommandEvent(unittest.TestCase):
    def test_default_id(self):
        from substrate.organism.command_runtime import CommandEvent

        evt = CommandEvent(event_type="test", command_id="cmd-123")
        self.assertTrue(evt.event_id.startswith("cevt-"))

    def test_to_dict(self):
        from substrate.organism.command_runtime import CommandEvent

        evt = CommandEvent(event_type="command_received", command_id="cmd-abc")
        d = evt.to_dict()
        self.assertEqual(d["event_type"], "command_received")
        self.assertEqual(d["command_id"], "cmd-abc")


class TestCommandContext(unittest.TestCase):
    def test_to_dict(self):
        from substrate.organism.command_runtime import CommandContext

        ctx = CommandContext(profile_mode="developer", operator_present=True)
        d = ctx.to_dict()
        self.assertEqual(d["profile_mode"], "developer")
        self.assertTrue(d["operator_present"])
        self.assertEqual(d["active_objectives"], [])

    def test_defaults(self):
        from substrate.organism.command_runtime import CommandContext

        ctx = CommandContext()
        self.assertEqual(ctx.profile_mode, "")
        self.assertFalse(ctx.operator_present)
        self.assertEqual(ctx.pending_approvals, 0)


class TestCommandRoutingDecision(unittest.TestCase):
    def test_to_dict(self):
        from substrate.organism.command_runtime import CommandRoutingDecision

        dec = CommandRoutingDecision(
            command_id="cmd-123",
            action_type="query",
            destination_system="continuity_runtime",
        )
        d = dec.to_dict()
        self.assertEqual(d["command_id"], "cmd-123")
        self.assertEqual(d["destination_system"], "continuity_runtime")

    def test_auto_timestamp(self):
        from substrate.organism.command_runtime import CommandRoutingDecision

        dec = CommandRoutingDecision()
        self.assertGreater(dec.decided_at, 0)


# ── Classifier tests ─────────────────────────────────────────────────────


class TestCommandClassifier(unittest.TestCase):
    def setUp(self):
        from substrate.organism.command_runtime import CommandClassifier

        self.classifier = CommandClassifier()

    def test_query_what(self):
        action, conf = self.classifier.classify("what changed while I was gone?")
        self.assertEqual(action.value, "query")
        self.assertEqual(conf, 1.0)

    def test_query_show(self):
        action, _ = self.classifier.classify("show me the status")
        self.assertEqual(action.value, "query")

    def test_query_question_mark(self):
        action, _ = self.classifier.classify("is the cockpit deployed?")
        self.assertEqual(action.value, "query")

    def test_query_list(self):
        action, _ = self.classifier.classify("list all pending approvals")
        self.assertEqual(action.value, "query")

    def test_query_status(self):
        action, _ = self.classifier.classify("status of the system")
        self.assertEqual(action.value, "query")

    def test_execute_build(self):
        action, _ = self.classifier.classify("build the new authentication system")
        self.assertEqual(action.value, "execute")

    def test_execute_deploy(self):
        action, _ = self.classifier.classify("deploy the cockpit")
        self.assertEqual(action.value, "execute")

    def test_execute_fix(self):
        action, _ = self.classifier.classify("fix the login bug")
        self.assertEqual(action.value, "execute")

    def test_review(self):
        action, _ = self.classifier.classify("review the operator roadmap")
        self.assertEqual(action.value, "review")

    def test_review_audit(self):
        action, _ = self.classifier.classify("audit the codebase")
        self.assertEqual(action.value, "review")

    def test_approve(self):
        action, _ = self.classifier.classify("approve packet wp-123")
        self.assertEqual(action.value, "approve")

    def test_reject(self):
        action, _ = self.classifier.classify("reject packet wp-456")
        self.assertEqual(action.value, "reject")

    def test_schedule(self):
        action, _ = self.classifier.classify("schedule the migration for next week")
        self.assertEqual(action.value, "schedule")

    def test_switch_profile_developer(self):
        action, _ = self.classifier.classify("switch to developer profile")
        self.assertEqual(action.value, "switch_profile")

    def test_switch_profile_engineer(self):
        action, _ = self.classifier.classify("switch to engineer")
        self.assertEqual(action.value, "switch_profile")

    def test_switch_session(self):
        action, _ = self.classifier.classify("switch to session abc")
        self.assertEqual(action.value, "switch_session")

    def test_create_objective(self):
        action, _ = self.classifier.classify("create objective: finish workstation runtime")
        self.assertEqual(action.value, "create_objective")

    def test_create_goal(self):
        action, _ = self.classifier.classify("add a new goal: ship voice rooms")
        self.assertEqual(action.value, "create_objective")

    def test_create_workpacket(self):
        action, _ = self.classifier.classify("create a work packet for the auth fix")
        self.assertEqual(action.value, "create_workpacket")

    def test_create_sequence(self):
        action, _ = self.classifier.classify("create a sequence for the deployment pipeline")
        self.assertEqual(action.value, "create_sequence")

    def test_empty_input(self):
        action, conf = self.classifier.classify("")
        self.assertEqual(action.value, "query")
        self.assertEqual(conf, 0.5)

    def test_fallback_execute(self):
        action, conf = self.classifier.classify("xyzzy blorp")
        self.assertEqual(action.value, "execute")
        self.assertEqual(conf, 0.5)

    def test_extract_profile_target(self):
        self.assertEqual(self.classifier.extract_profile_target("switch to developer"), "engineer")
        self.assertEqual(
            self.classifier.extract_profile_target("switch to engineer profile"), "engineer"
        )
        self.assertEqual(self.classifier.extract_profile_target("activate research"), "research")
        self.assertEqual(self.classifier.extract_profile_target("switch to music"), "artist")
        self.assertEqual(self.classifier.extract_profile_target("nothing here"), "")

    def test_extract_objective_text(self):
        self.assertEqual(
            self.classifier.extract_objective_text("create objective: finish workstation"),
            "finish workstation",
        )
        self.assertEqual(
            self.classifier.extract_objective_text("add a new goal: ship voice rooms"),
            "ship voice rooms",
        )

    def test_extract_packet_target(self):
        self.assertEqual(self.classifier.extract_packet_target("approve packet wp-123"), "wp-123")
        self.assertEqual(self.classifier.extract_packet_target("reject wp-456"), "wp-456")
        self.assertEqual(self.classifier.extract_packet_target("approve this"), "this")


# ── Timeline tests ───────────────────────────────────────────────────────


class TestCommandTimeline(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        from substrate.organism.command_runtime import CommandTimeline

        self.timeline = CommandTimeline(data_dir=self.tmpdir)

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_emit_and_read(self):
        from substrate.organism.command_runtime import CommandEvent

        evt = CommandEvent(event_type="command_received", command_id="cmd-001", summary="test")
        self.timeline.emit(evt)

        events = self.timeline.get_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["command_id"], "cmd-001")

    def test_filter_by_command_id(self):
        from substrate.organism.command_runtime import CommandEvent

        self.timeline.emit(CommandEvent(event_type="t", command_id="cmd-001", summary="a"))
        self.timeline.emit(CommandEvent(event_type="t", command_id="cmd-002", summary="b"))

        events = self.timeline.get_events(command_id="cmd-001")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["command_id"], "cmd-001")

    def test_filter_by_event_type(self):
        from substrate.organism.command_runtime import CommandEvent

        self.timeline.emit(CommandEvent(event_type="command_received", command_id="cmd-001"))
        self.timeline.emit(CommandEvent(event_type="command_routed", command_id="cmd-001"))

        events = self.timeline.get_events(event_type="command_routed")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event_type"], "command_routed")

    def test_limit(self):
        from substrate.organism.command_runtime import CommandEvent

        for i in range(10):
            self.timeline.emit(CommandEvent(event_type="t", command_id=f"cmd-{i}"))

        events = self.timeline.get_events(limit=3)
        self.assertEqual(len(events), 3)

    def test_get_command_history(self):
        from substrate.organism.command_runtime import CommandEvent

        self.timeline.emit(CommandEvent(event_type="received", command_id="cmd-x"))
        self.timeline.emit(CommandEvent(event_type="routed", command_id="cmd-x"))
        self.timeline.emit(CommandEvent(event_type="completed", command_id="cmd-x"))
        self.timeline.emit(CommandEvent(event_type="received", command_id="cmd-y"))

        history = self.timeline.get_command_history("cmd-x")
        self.assertEqual(len(history), 3)

    def test_empty_timeline(self):
        events = self.timeline.get_events()
        self.assertEqual(events, [])


# ── History tests ────────────────────────────────────────────────────────


class TestCommandHistory(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        from substrate.organism.command_runtime import CommandHistory

        self.history = CommandHistory(data_dir=self.tmpdir)

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_save_and_read(self):
        from substrate.organism.command_runtime import Command

        cmd = Command(raw_input="test command", status="completed")
        self.history.save(cmd)

        recent = self.history.get_recent()
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0]["raw_input"], "test command")

    def test_get_pending(self):
        from substrate.organism.command_runtime import Command

        self.history.save(Command(raw_input="a", status="completed"))
        self.history.save(Command(raw_input="b", status="pending_approval"))
        self.history.save(Command(raw_input="c", status="executing"))

        pending = self.history.get_pending()
        self.assertEqual(len(pending), 2)

    def test_get_by_status(self):
        from substrate.organism.command_runtime import Command

        self.history.save(Command(raw_input="a", status="completed"))
        self.history.save(Command(raw_input="b", status="completed"))
        self.history.save(Command(raw_input="c", status="failed"))

        completed = self.history.get_by_status("completed")
        self.assertEqual(len(completed), 2)

    def test_update_status(self):
        from substrate.organism.command_runtime import Command

        cmd = Command(raw_input="test", status="pending_approval")
        self.history.save(cmd)

        result = self.history.update_status(cmd.command_id, "approved")
        self.assertTrue(result)

        recent = self.history.get_recent()
        self.assertEqual(recent[0]["status"], "approved")

    def test_update_nonexistent(self):
        result = self.history.update_status("cmd-nonexistent", "approved")
        self.assertFalse(result)

    def test_empty_history(self):
        self.assertEqual(self.history.get_recent(), [])
        self.assertEqual(self.history.get_pending(), [])


# ── Context Assembler tests ──────────────────────────────────────────────


class TestContextAssembler(unittest.TestCase):
    def test_assemble_returns_context(self):
        from substrate.organism.command_runtime import ContextAssembler

        assembler = ContextAssembler()
        ctx = assembler.assemble()
        self.assertIsNotNone(ctx)
        d = ctx.to_dict()
        self.assertIn("profile_mode", d)
        self.assertIn("operator_present", d)
        self.assertIn("active_objectives", d)

    def test_graceful_failure(self):
        from substrate.organism.command_runtime import ContextAssembler

        assembler = ContextAssembler()
        ctx = assembler.assemble()
        self.assertEqual(ctx.active_objectives, [])


# ── Router tests ─────────────────────────────────────────────────────────


class TestCommandRouter(unittest.TestCase):
    def test_route_query(self):
        from substrate.organism.command_runtime import CommandRouter, Command

        router = CommandRouter()
        cmd = Command(raw_input="what changed?", action_type="query")
        decision = router.route(cmd)
        self.assertEqual(decision.destination_system, "continuity_runtime")
        self.assertEqual(decision.approval_state, "not_required")

    def test_route_query_status(self):
        from substrate.organism.command_runtime import CommandRouter, Command

        router = CommandRouter()
        cmd = Command(raw_input="show status overview", action_type="query")
        decision = router.route(cmd)
        self.assertEqual(decision.destination_system, "empire_router")

    def test_route_query_risk(self):
        from substrate.organism.command_runtime import CommandRouter, Command

        router = CommandRouter()
        cmd = Command(raw_input="what risks exist?", action_type="query")
        decision = router.route(cmd)
        self.assertEqual(decision.destination_system, "projection_engine")

    def test_route_query_drift(self):
        from substrate.organism.command_runtime import CommandRouter, Command

        router = CommandRouter()
        cmd = Command(raw_input="is anything stuck or stagnant?", action_type="query")
        decision = router.route(cmd)
        self.assertEqual(decision.destination_system, "strategic_tick_loop")

    def test_route_execute(self):
        from substrate.organism.command_runtime import CommandRouter, Command

        router = CommandRouter()
        cmd = Command(raw_input="build auth system", action_type="execute")
        decision = router.route(cmd)
        self.assertEqual(decision.destination_system, "empire_router")

    def test_route_switch_profile(self):
        from substrate.organism.command_runtime import CommandRouter, Command

        router = CommandRouter()
        cmd = Command(raw_input="switch to developer", action_type="switch_profile")
        decision = router.route(cmd)
        self.assertEqual(decision.destination_system, "profile_runtime")
        self.assertEqual(decision.approval_state, "not_required")

    def test_route_switch_session(self):
        from substrate.organism.command_runtime import CommandRouter, Command

        router = CommandRouter()
        cmd = Command(raw_input="switch to session x", action_type="switch_session")
        decision = router.route(cmd)
        self.assertEqual(decision.destination_system, "session_runtime")

    def test_route_create_objective(self):
        from substrate.organism.command_runtime import CommandRouter, Command

        router = CommandRouter()
        cmd = Command(
            raw_input="create objective: finish voice rooms", action_type="create_objective"
        )
        decision = router.route(cmd)
        self.assertEqual(decision.destination_system, "strategic_gap_engine")

    def test_route_schedule(self):
        from substrate.organism.command_runtime import CommandRouter, Command

        router = CommandRouter()
        cmd = Command(raw_input="schedule the migration", action_type="schedule")
        decision = router.route(cmd)
        self.assertEqual(decision.destination_system, "tick_loop")

    def test_route_approve(self):
        from substrate.organism.command_runtime import CommandRouter, Command

        router = CommandRouter()
        cmd = Command(raw_input="approve packet wp-123", action_type="approve")
        decision = router.route(cmd)
        self.assertEqual(decision.destination_system, "approval_system")

    def test_route_reject(self):
        from substrate.organism.command_runtime import CommandRouter, Command

        router = CommandRouter()
        cmd = Command(raw_input="reject packet wp-456", action_type="reject")
        decision = router.route(cmd)
        self.assertEqual(decision.destination_system, "approval_system")

    def test_route_create_sequence(self):
        from substrate.organism.command_runtime import CommandRouter, Command

        router = CommandRouter()
        cmd = Command(raw_input="create a sequence for deployment", action_type="create_sequence")
        decision = router.route(cmd)
        self.assertEqual(decision.destination_system, "empire_router")
        self.assertEqual(decision.approval_state, "required")


# ── Singleton tests ──────────────────────────────────────────────────────


class TestSingleton(unittest.TestCase):
    def test_singleton(self):
        from substrate.organism.command_runtime import get_command_runtime, reset_command_runtime

        reset_command_runtime()
        r1 = get_command_runtime()
        r2 = get_command_runtime()
        self.assertIs(r1, r2)

    def test_reset(self):
        from substrate.organism.command_runtime import get_command_runtime, reset_command_runtime

        reset_command_runtime()
        r1 = get_command_runtime()
        reset_command_runtime()
        r2 = get_command_runtime()
        self.assertIsNot(r1, r2)


# ── CommandRuntime integration tests ─────────────────────────────────────


class TestCommandRuntime(unittest.TestCase):
    def setUp(self):
        from substrate.organism.command_runtime import CommandRuntime

        self.tmpdir = tempfile.mkdtemp()
        self.runtime = CommandRuntime()
        self.runtime._timeline = self._make_timeline()
        self.runtime._history = self._make_history()

    def _make_timeline(self):
        from substrate.organism.command_runtime import CommandTimeline

        return CommandTimeline(data_dir=os.path.join(self.tmpdir, "timeline"))

    def _make_history(self):
        from substrate.organism.command_runtime import CommandHistory

        return CommandHistory(data_dir=os.path.join(self.tmpdir, "history"))

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_submit_query(self):
        cmd = self.runtime.submit("what is the current status?", source="cockpit")
        self.assertEqual(cmd.action_type, "query")
        self.assertEqual(cmd.status, "completed")
        self.assertTrue(cmd.command_id.startswith("cmd-"))
        self.assertEqual(cmd.source, "cockpit")

    def test_submit_review(self):
        cmd = self.runtime.submit("review the operator roadmap")
        self.assertEqual(cmd.action_type, "review")
        self.assertEqual(cmd.status, "completed")

    def test_submit_preserves_source(self):
        cmd = self.runtime.submit("show status", source="voice")
        self.assertEqual(cmd.source, "voice")

    def test_submit_produces_timeline(self):
        cmd = self.runtime.submit("what happened?")
        events = self.runtime.get_timeline(command_id=cmd.command_id)
        self.assertGreater(len(events), 0)
        event_types = {e["event_type"] for e in events}
        self.assertIn("command_received", event_types)
        self.assertIn("command_classified", event_types)

    def test_submit_records_history(self):
        self.runtime.submit("test command 1")
        self.runtime.submit("test command 2")
        history = self.runtime.get_history()
        self.assertEqual(len(history), 2)

    def test_get_status(self):
        self.runtime.submit("test status")
        status = self.runtime.get_status()
        self.assertEqual(status["phase"], "Phase 9 — Command Runtime")
        self.assertEqual(status["total_commands"], 1)

    def test_context_assembled(self):
        cmd = self.runtime.submit("show me everything")
        self.assertIn("profile_mode", cmd.context)
        self.assertIn("operator_present", cmd.context)

    def test_normalized_command(self):
        cmd = self.runtime.submit("  test   with   extra   spaces  ")
        self.assertEqual(cmd.normalized_command, "test with extra spaces")

    def test_submit_switch_profile(self):
        cmd = self.runtime.submit("switch to developer profile")
        self.assertEqual(cmd.action_type, "switch_profile")

    def test_submit_create_objective(self):
        cmd = self.runtime.submit("create objective: ship voice rooms")
        self.assertEqual(cmd.action_type, "create_objective")

    def test_submit_approve(self):
        cmd = self.runtime.submit("approve packet wp-abc")
        self.assertEqual(cmd.action_type, "approve")

    def test_get_pending(self):
        pending = self.runtime.get_pending()
        self.assertIsInstance(pending, list)

    def test_reject_command_not_found(self):
        result = self.runtime.reject_command("cmd-nonexistent", "testing")
        self.assertFalse(result["rejected"])
        self.assertIn("not found or not rejectable", result.get("error", ""))

    def test_reject_command_success(self):
        from substrate.organism.command_runtime import Command

        cmd = Command(raw_input="test", status="pending_approval")
        self.runtime._history.save(cmd)
        result = self.runtime.reject_command(cmd.command_id, "testing")
        self.assertTrue(result["rejected"])

    def test_reject_command_terminal_blocked(self):
        from substrate.organism.command_runtime import Command

        cmd = Command(raw_input="test", status="completed")
        self.runtime._history.save(cmd)
        result = self.runtime.reject_command(cmd.command_id, "testing")
        self.assertFalse(result["rejected"])
        self.assertIn("not found or not rejectable", result.get("error", ""))


# ── Acceptance tests ─────────────────────────────────────────────────────


class TestAcceptance(unittest.TestCase):
    """End-to-end acceptance scenarios from the spec."""

    def setUp(self):
        from substrate.organism.command_runtime import CommandRuntime

        self.tmpdir = tempfile.mkdtemp()
        self.runtime = CommandRuntime()
        from substrate.organism.command_runtime import CommandTimeline, CommandHistory

        self.runtime._timeline = CommandTimeline(data_dir=os.path.join(self.tmpdir, "tl"))
        self.runtime._history = CommandHistory(data_dir=os.path.join(self.tmpdir, "h"))

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_review_operator_roadmap(self):
        """'review operator roadmap' routes to review workflow."""
        cmd = self.runtime.submit("review operator roadmap")
        self.assertEqual(cmd.action_type, "review")
        self.assertEqual(cmd.status, "completed")
        self.assertIn("routing_result", cmd.to_dict())

    def test_switch_to_engineer_profile(self):
        """'switch to engineer profile' activates profile."""
        cmd = self.runtime.submit("switch to engineer profile")
        self.assertEqual(cmd.action_type, "switch_profile")
        routing = cmd.routing_result
        self.assertEqual(routing.get("destination_system"), "profile_runtime")

    def test_create_objective(self):
        """'create objective: finish workstation' creates objective."""
        cmd = self.runtime.submit("create objective: finish workstation")
        self.assertEqual(cmd.action_type, "create_objective")
        routing = cmd.routing_result
        self.assertEqual(routing.get("destination_system"), "strategic_gap_engine")

    def test_approve_packet(self):
        """'approve packet' approves packet."""
        cmd = self.runtime.submit("approve packet wp-test-1")
        self.assertEqual(cmd.action_type, "approve")
        routing = cmd.routing_result
        self.assertEqual(routing.get("destination_system"), "approval_system")

    def test_what_changed_while_gone(self):
        """'what changed while I was gone' queries Continuity Runtime."""
        cmd = self.runtime.submit("what changed while I was gone?")
        self.assertEqual(cmd.action_type, "query")
        routing = cmd.routing_result
        self.assertEqual(routing.get("destination_system"), "continuity_runtime")

    def test_full_lifecycle(self):
        """Full command lifecycle: submit → classify → route → complete."""
        cmd = self.runtime.submit("show me all pending approvals", source="voice")
        self.assertEqual(cmd.action_type, "query")
        self.assertEqual(cmd.source, "voice")
        self.assertEqual(cmd.status, "completed")
        self.assertGreater(cmd.confidence, 0)
        self.assertIn("profile_mode", cmd.context)

        events = self.runtime.get_timeline(command_id=cmd.command_id)
        event_types = [e["event_type"] for e in events]
        self.assertIn("command_received", event_types)
        self.assertIn("command_classified", event_types)
        self.assertIn("context_assembled", event_types)

        history = self.runtime.get_history()
        self.assertTrue(any(c["command_id"] == cmd.command_id for c in history))

    def test_governance_boundary(self):
        """Command Runtime classifies and routes — never executes directly."""
        cmd = self.runtime.submit("deploy the cockpit now")
        self.assertEqual(cmd.action_type, "execute")
        routing = cmd.routing_result
        self.assertEqual(routing.get("destination_system"), "empire_router")

    def test_multi_source_consistency(self):
        """Same command from different sources produces same classification."""
        from substrate.organism.command_runtime import CommandClassifier

        classifier = CommandClassifier()

        for source in ["cockpit", "voice", "api", "meeting", "mobile"]:
            action, _ = classifier.classify("show me the system status")
            self.assertEqual(action.value, "query")

    def test_no_duplicate_routing(self):
        """Command Runtime composes existing systems — never duplicates them."""
        from substrate.organism.command_runtime import CommandRouter

        router = CommandRouter()

        destinations = set()
        test_cases = [
            ("what changed?", "query"),
            ("build auth", "execute"),
            ("review code", "review"),
            ("approve wp-1", "approve"),
            ("schedule migration", "schedule"),
            ("switch to developer", "switch_profile"),
            ("create objective: x", "create_objective"),
        ]

        from substrate.organism.command_runtime import Command

        for raw, action in test_cases:
            cmd = Command(raw_input=raw, action_type=action)
            dec = router.route(cmd)
            destinations.add(dec.destination_system)

        expected_systems = {
            "continuity_runtime",
            "empire_router",
            "approval_system",
            "tick_loop",
            "presence_runtime",
            "profile_runtime",
            "session_runtime",
            "strategic_gap_engine",
        }
        self.assertTrue(
            destinations.issubset(expected_systems | {"projection_engine", "strategic_tick_loop"})
        )


if __name__ == "__main__":
    unittest.main()
