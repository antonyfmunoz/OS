"""P3 Phase 4 — Slack Workflow tests.

Verifies:
1. SlackWorkflow produces governed steps
2. Message validation catches edge cases
3. Notification formatting uses templates
4. Outbox-based delivery writes JSONL
5. Full lifecycle through WorkflowRunner

Run with: pytest tests/test_p3_phase4_slack.py -v
"""

import json
import os
import sys
import tempfile

import pytest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)

pytestmark = pytest.mark.smoke


class TestSlackWorkflowStructure:

    def test_importable(self):
        from projections.eos.workflows.slack import SlackWorkflow
        assert SlackWorkflow is not None

    def test_send_message_returns_3_steps(self):
        from projections.eos.workflows.slack import SlackWorkflow
        wf = SlackWorkflow()
        steps = wf.send_message_steps("general", "hello")
        assert len(steps) == 3
        names = [s.name for s in steps]
        assert names == ["validate_message", "send_message", "confirm_delivery"]

    def test_notify_returns_2_steps(self):
        from projections.eos.workflows.slack import SlackWorkflow
        wf = SlackWorkflow()
        steps = wf.notify_steps("alerts", "error", {"source": "spine", "message": "fail"})
        assert len(steps) == 2
        names = [s.name for s in steps]
        assert names == ["format_notification", "send_notification"]

    def test_all_steps_have_mutation_names(self):
        from projections.eos.workflows.slack import SlackWorkflow
        wf = SlackWorkflow()
        all_steps = (
            wf.send_message_steps("ch", "msg")
            + wf.notify_steps("ch", "alert", {"message": "test"})
        )
        for step in all_steps:
            assert step.mutation_name, f"{step.name} missing mutation_name"
            assert step.intent

    def test_confirm_delivery_is_skip_on_failure(self):
        from projections.eos.workflows.slack import SlackWorkflow
        wf = SlackWorkflow()
        steps = wf.send_message_steps("general", "hello")
        assert steps[2].skip_on_failure is True


class TestSlackValidation:

    def test_valid_message(self):
        from projections.eos.workflows.slack import SlackWorkflow
        wf = SlackWorkflow()
        output, success = wf._validate_message("general", "hello world")
        assert success
        assert "11 chars" in output
        assert wf._validated_channel == "general"
        assert wf._validated_message == "hello world"

    def test_empty_channel_fails(self):
        from projections.eos.workflows.slack import SlackWorkflow
        wf = SlackWorkflow()
        output, success = wf._validate_message("", "hello")
        assert not success
        assert "channel" in output

    def test_empty_message_fails(self):
        from projections.eos.workflows.slack import SlackWorkflow
        wf = SlackWorkflow()
        output, success = wf._validate_message("general", "")
        assert not success
        assert "message" in output

    def test_message_too_long_fails(self):
        from projections.eos.workflows.slack import SlackWorkflow
        wf = SlackWorkflow()
        output, success = wf._validate_message("general", "x" * 4001)
        assert not success
        assert "4000" in output

    def test_channel_hash_stripped(self):
        from projections.eos.workflows.slack import SlackWorkflow
        wf = SlackWorkflow()
        wf._validate_message("#general", "test")
        assert wf._validated_channel == "general"


class TestSlackNotificationFormatting:

    def test_workflow_complete_template(self):
        from projections.eos.workflows.slack import SlackWorkflow
        wf = SlackWorkflow()
        output, success = wf._format_notification(
            "alerts", "workflow_complete",
            {"name": "research", "status": "SUCCESS"}
        )
        assert success
        assert "research" in wf._validated_message
        assert "SUCCESS" in wf._validated_message

    def test_error_template(self):
        from projections.eos.workflows.slack import SlackWorkflow
        wf = SlackWorkflow()
        output, success = wf._format_notification(
            "alerts", "error",
            {"source": "spine", "message": "timeout"}
        )
        assert success
        assert "spine" in wf._validated_message
        assert "timeout" in wf._validated_message

    def test_unknown_event_type_uses_json(self):
        from projections.eos.workflows.slack import SlackWorkflow
        wf = SlackWorkflow()
        output, success = wf._format_notification(
            "alerts", "custom_event",
            {"key": "value"}
        )
        assert success
        assert "custom_event" in wf._validated_message
        assert "value" in wf._validated_message

    def test_missing_template_keys_falls_back(self):
        from projections.eos.workflows.slack import SlackWorkflow
        wf = SlackWorkflow()
        output, success = wf._format_notification(
            "alerts", "workflow_complete",
            {"wrong_key": "value"}
        )
        assert success
        assert "workflow_complete" in wf._validated_message


class TestSlackOutboxDelivery:

    def test_send_writes_to_outbox(self):
        from projections.eos.workflows import slack as slack_mod
        from projections.eos.workflows.slack import SlackWorkflow

        with tempfile.TemporaryDirectory() as tmpdir:
            orig_dir = slack_mod._OUTBOX_DIR
            orig_file = slack_mod._OUTBOX_FILE
            slack_mod._OUTBOX_DIR = tmpdir
            slack_mod._OUTBOX_FILE = os.path.join(tmpdir, "outbox.jsonl")
            try:
                wf = SlackWorkflow()
                wf._validate_message("general", "test message")
                output, success = wf._send_message()
                assert success
                assert "Queued" in output

                with open(slack_mod._OUTBOX_FILE) as f:
                    entry = json.loads(f.readline())
                assert entry["channel"] == "general"
                assert entry["message"] == "test message"
                assert entry["status"] == "queued"
            finally:
                slack_mod._OUTBOX_DIR = orig_dir
                slack_mod._OUTBOX_FILE = orig_file

    def test_send_without_validation_fails(self):
        from projections.eos.workflows.slack import SlackWorkflow
        wf = SlackWorkflow()
        output, success = wf._send_message()
        assert not success
        assert "no validated message" in output

    def test_confirm_delivery(self):
        from projections.eos.workflows import slack as slack_mod
        from projections.eos.workflows.slack import SlackWorkflow

        with tempfile.TemporaryDirectory() as tmpdir:
            orig_dir = slack_mod._OUTBOX_DIR
            orig_file = slack_mod._OUTBOX_FILE
            slack_mod._OUTBOX_DIR = tmpdir
            slack_mod._OUTBOX_FILE = os.path.join(tmpdir, "outbox.jsonl")
            try:
                wf = SlackWorkflow()
                wf._validate_message("general", "test")
                wf._send_message()
                output, success = wf._confirm_delivery()
                assert success
                assert wf._delivery_id in output
            finally:
                slack_mod._OUTBOX_DIR = orig_dir
                slack_mod._OUTBOX_FILE = orig_file


class TestSlackThroughRunner:

    def test_send_message_through_runner(self):
        from projections.eos.workflows import slack as slack_mod
        from projections.eos.workflows.runner import WorkflowRunner
        from projections.eos.workflows.slack import SlackWorkflow

        with tempfile.TemporaryDirectory() as tmpdir:
            orig_dir = slack_mod._OUTBOX_DIR
            orig_file = slack_mod._OUTBOX_FILE
            slack_mod._OUTBOX_DIR = tmpdir
            slack_mod._OUTBOX_FILE = os.path.join(tmpdir, "outbox.jsonl")
            try:
                wf = SlackWorkflow()
                runner = WorkflowRunner()
                result = runner.run(
                    "slack_send", wf.send_message_steps("general", "hello"),
                    source="test",
                )
                assert result.success
                assert result.steps_completed == 3
            finally:
                slack_mod._OUTBOX_DIR = orig_dir
                slack_mod._OUTBOX_FILE = orig_file

    def test_notify_through_runner(self):
        from projections.eos.workflows import slack as slack_mod
        from projections.eos.workflows.runner import WorkflowRunner
        from projections.eos.workflows.slack import SlackWorkflow

        with tempfile.TemporaryDirectory() as tmpdir:
            orig_dir = slack_mod._OUTBOX_DIR
            orig_file = slack_mod._OUTBOX_FILE
            slack_mod._OUTBOX_DIR = tmpdir
            slack_mod._OUTBOX_FILE = os.path.join(tmpdir, "outbox.jsonl")
            try:
                wf = SlackWorkflow()
                runner = WorkflowRunner()
                result = runner.run(
                    "slack_notify",
                    wf.notify_steps("alerts", "error", {"source": "test", "message": "boom"}),
                    source="test",
                )
                assert result.success
                assert result.steps_completed == 2
            finally:
                slack_mod._OUTBOX_DIR = orig_dir
                slack_mod._OUTBOX_FILE = orig_file

    def test_invalid_message_halts_runner(self):
        from projections.eos.workflows.runner import WorkflowRunner
        from projections.eos.workflows.slack import SlackWorkflow

        wf = SlackWorkflow()
        runner = WorkflowRunner()
        result = runner.run(
            "slack_send", wf.send_message_steps("", "hello"),
            source="test",
        )
        assert not result.success
        assert result.steps_completed == 0
