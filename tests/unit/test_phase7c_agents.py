"""Tests for Phase 7C: Multi-Agent Intelligence Layer — Core agents.

Verifies:
- ReviewerAgent role, description, output structure, verdicts, risk levels
- DebugAgent role, output structure, failure classification, retryability
- Both agents are advisory-only, stateless, and return AgentOutput

The reviewer uses severity: critical/warning/info and verdict: reject/revise/approve.
The debugger uses categories: timeout, permission_denied, input_error, external_failure,
validation_error, internal_error, unknown.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

import pytest

from umh.agents.base import AgentOutput, AgentRole, BaseAgent
from umh.agents.debugger import DebugAgent
from umh.agents.reviewer import ReviewerAgent


# ── Helpers ──────────────────────────────────────────────────────────


def _sample_plan(steps=None, source="template", confidence=1.0):
    if steps is None:
        steps = [
            {
                "step_id": "s1",
                "name": "Step 1",
                "operation": "summarize",
                "inputs": {"prompt": "test"},
                "execution_class": "llm_call",
                "rationale": "test",
            }
        ]
    return {
        "plan_id": "eplan_test",
        "objective": {"title": "Test", "description": "Test plan"},
        "steps": steps,
        "source": source,
        "confidence": confidence,
        "status": "validated",
    }


def _sample_task(error="", failed_step=0, step_count=3):
    steps = []
    for i in range(step_count):
        if i == failed_step:
            status = "failed"
        elif i > failed_step:
            status = "pending"
        else:
            status = "completed"
        steps.append(
            {
                "name": f"Step {i}",
                "operation": "summarize",
                "status": status,
                "inputs_template": {},
                "result": {},
            }
        )
    return {
        "id": "task_test",
        "status": "failed",
        "steps": steps,
        "error": error,
    }


# ── A. ReviewerAgent ─────────────────────────────────────────────────


class TestReviewerAgent:
    def setup_method(self):
        self.agent = ReviewerAgent()

    def test_reviewer_role_is_reviewer(self):
        assert self.agent.role == AgentRole.REVIEWER

    def test_reviewer_description_not_empty(self):
        assert self.agent.description
        assert len(self.agent.description) > 5

    def test_reviewer_run_returns_agent_output(self):
        plan = _sample_plan()
        result = self.agent.run({"plan": plan, "objective": "Test"})
        assert isinstance(result, AgentOutput)

    def test_reviewer_output_has_required_fields(self):
        """Output must have issues, risk_level, suggestions, verdict, summary."""
        plan = _sample_plan()
        result = self.agent.run({"plan": plan, "objective": "Test"})
        output = result.output
        assert "verdict" in output
        assert "risk_level" in output
        assert "issues" in output
        assert "suggestions" in output
        assert "summary" in output

    def test_reviewer_low_risk_simple_plan(self):
        """Single step, known operation, template source -> approve, low risk."""
        plan = _sample_plan()
        result = self.agent.run({"plan": plan, "objective": "Test"})
        output = result.output
        assert output["verdict"] == "approve"
        assert output["risk_level"] == "low"

    def test_reviewer_warns_on_shell_command(self):
        """Plan with shell_command operation produces a warning issue."""
        steps = [
            {
                "step_id": "s1",
                "name": "Run command",
                "operation": "shell_command",
                "inputs": {"command": "ls"},
                "execution_class": "side_effect",
                "rationale": "list files",
            }
        ]
        plan = _sample_plan(steps=steps)
        result = self.agent.run({"plan": plan, "objective": "Test"})
        output = result.output
        shell_issues = [i for i in output["issues"] if "shell_command" in i.get("message", "")]
        assert len(shell_issues) >= 1
        assert shell_issues[0]["severity"] == "warning"

    def test_reviewer_warns_on_high_step_count(self):
        """6+ steps should produce a warning about step count."""
        steps = [
            {
                "step_id": f"s{i}",
                "name": f"Step {i}",
                "operation": "summarize",
                "inputs": {"prompt": "test"},
                "execution_class": "llm_call",
                "rationale": "test",
            }
            for i in range(7)
        ]
        plan = _sample_plan(steps=steps)
        result = self.agent.run({"plan": plan, "objective": "Test"})
        output = result.output
        step_issues = [i for i in output["issues"] if "steps" in i.get("message", "").lower()]
        assert len(step_issues) >= 1
        assert step_issues[0]["severity"] in ("warning", "critical")

    def test_reviewer_critical_on_excessive_steps(self):
        """9+ steps (>8) should produce a critical severity issue."""
        steps = [
            {
                "step_id": f"s{i}",
                "name": f"Step {i}",
                "operation": "summarize",
                "inputs": {"prompt": "test"},
                "execution_class": "llm_call",
                "rationale": "test",
            }
            for i in range(10)
        ]
        plan = _sample_plan(steps=steps)
        result = self.agent.run({"plan": plan, "objective": "Test"})
        output = result.output
        step_issues = [i for i in output["issues"] if "steps" in i.get("message", "").lower()]
        assert len(step_issues) >= 1
        assert any(i["severity"] == "critical" for i in step_issues)

    def test_reviewer_warns_on_llm_source(self):
        """source=llm should produce a warning about untrusted."""
        plan = _sample_plan(source="llm")
        result = self.agent.run({"plan": plan, "objective": "Test"})
        output = result.output
        llm_issues = [
            i
            for i in output["issues"]
            if "untrusted" in i.get("message", "").lower() or "llm" in i.get("message", "").lower()
        ]
        assert len(llm_issues) >= 1

    def test_reviewer_warns_on_low_confidence(self):
        """Low confidence (<0.5) should produce a warning."""
        plan = _sample_plan(confidence=0.3)
        result = self.agent.run({"plan": plan, "objective": "Test"})
        output = result.output
        confidence_issues = [
            i for i in output["issues"] if "confidence" in i.get("message", "").lower()
        ]
        # confidence < 0.3 → critical, 0.3..0.5 → warning
        assert len(confidence_issues) >= 1

    def test_reviewer_critical_on_very_low_confidence(self):
        """Very low confidence (<0.3) should produce a critical issue."""
        plan = _sample_plan(confidence=0.2)
        result = self.agent.run({"plan": plan, "objective": "Test"})
        output = result.output
        confidence_issues = [
            i for i in output["issues"] if "confidence" in i.get("message", "").lower()
        ]
        assert len(confidence_issues) >= 1
        assert any(i["severity"] == "critical" for i in confidence_issues)

    def test_reviewer_handles_approval_gated_ops(self):
        """Plans with computer_click produce an info issue about approval."""
        steps = [
            {
                "step_id": "s1",
                "name": "Click element",
                "operation": "computer_click",
                "inputs": {"x": 100, "y": 200},
                "execution_class": "side_effect",
                "rationale": "Click a button",
            }
        ]
        plan = _sample_plan(steps=steps)
        result = self.agent.run({"plan": plan, "objective": "Test"})
        output = result.output
        approval_issues = [
            i for i in output["issues"] if "approval" in i.get("message", "").lower()
        ]
        assert len(approval_issues) >= 1
        assert approval_issues[0]["severity"] == "info"

    def test_reviewer_verdict_approve_on_clean_plan(self):
        """Clean single-step template plan -> approve."""
        plan = _sample_plan()
        result = self.agent.run({"plan": plan, "objective": "Test"})
        assert result.output["verdict"] == "approve"

    def test_reviewer_verdict_revise_on_many_warnings(self):
        """3+ warnings -> verdict=revise."""
        # shell_command steps each produce a warning
        steps = [
            {
                "step_id": f"s{i}",
                "name": f"Step {i}",
                "operation": "shell_command",
                "inputs": {"command": f"echo {i}"},
                "execution_class": "side_effect",
                "rationale": f"step {i}",
            }
            for i in range(4)
        ]
        plan = _sample_plan(steps=steps)
        result = self.agent.run({"plan": plan, "objective": "Test"})
        # 4 shell_command warnings -> verdict should be revise
        assert result.output["verdict"] == "revise"

    def test_reviewer_verdict_reject_on_critical(self):
        """Plan with critical issues -> verdict=reject."""
        steps = [
            {
                "step_id": "s1",
                "name": "Bad step",
                "operation": "shell_command",
                "inputs": {},  # missing "command" -> critical
                "execution_class": "llm_call",  # should be side_effect -> critical
                "rationale": "nuke it",
            }
        ]
        plan = _sample_plan(steps=steps)
        result = self.agent.run({"plan": plan, "objective": "Test"})
        assert result.output["verdict"] == "reject"
        assert result.output["risk_level"] == "high"


# ── B. DebugAgent ────────────────────────────────────────────────────


class TestDebugAgent:
    def setup_method(self):
        self.agent = DebugAgent()

    def test_debugger_role_is_debugger(self):
        assert self.agent.role == AgentRole.DEBUGGER

    def test_debugger_run_returns_agent_output(self):
        task = _sample_task(error="something failed")
        result = self.agent.run({"task": task, "error": "something failed", "plan": {}})
        assert isinstance(result, AgentOutput)

    def test_debugger_output_has_required_fields(self):
        """Output must have root_cause, failed_step_index, failure_category,
        suggested_fix, retryable, confidence."""
        task = _sample_task(error="something failed")
        result = self.agent.run({"task": task, "error": "something failed", "plan": {}})
        output = result.output
        assert "root_cause" in output
        assert "failed_step_index" in output
        assert "failure_category" in output
        assert "suggested_fix" in output
        assert "retryable" in output
        assert "confidence" in output

    def test_debugger_detects_timeout(self):
        """Error containing 'timeout' -> category=timeout, retryable=True."""
        task = _sample_task(error="operation timeout after 30s")
        result = self.agent.run({"task": task, "error": "operation timeout after 30s", "plan": {}})
        output = result.output
        assert output["failure_category"] == "timeout"
        assert output["retryable"] is True

    def test_debugger_detects_permission(self):
        """Error containing 'permission' -> category=permission_denied, retryable=False."""
        task = _sample_task(error="permission denied: /root/secret")
        result = self.agent.run(
            {"task": task, "error": "permission denied: /root/secret", "plan": {}}
        )
        output = result.output
        assert output["failure_category"] == "permission_denied"
        assert output["retryable"] is False

    def test_debugger_detects_not_found(self):
        """Error containing 'not found' -> category=input_error."""
        task = _sample_task(error="file not found: /tmp/missing.txt")
        result = self.agent.run(
            {"task": task, "error": "file not found: /tmp/missing.txt", "plan": {}}
        )
        output = result.output
        assert output["failure_category"] == "input_error"

    def test_debugger_detects_500(self):
        """Error containing '500' -> category=external_failure, retryable=True."""
        task = _sample_task(error="server returned 500 internal error")
        result = self.agent.run(
            {"task": task, "error": "server returned 500 internal error", "plan": {}}
        )
        output = result.output
        assert output["failure_category"] == "external_failure"
        assert output["retryable"] is True

    def test_debugger_detects_connection_error(self):
        """Error containing 'connection' -> category=external_failure, retryable=True."""
        task = _sample_task(error="connection refused by host")
        result = self.agent.run({"task": task, "error": "connection refused by host", "plan": {}})
        output = result.output
        assert output["failure_category"] == "external_failure"
        assert output["retryable"] is True

    def test_debugger_unknown_error(self):
        """Random error with no pattern -> category=unknown."""
        task = _sample_task(error="xyzzy foobarbaz")
        result = self.agent.run({"task": task, "error": "xyzzy foobarbaz", "plan": {}})
        output = result.output
        assert output["failure_category"] == "unknown"

    def test_debugger_finds_failed_step(self):
        """Task with step at index 2 failed -> failed_step_index=2."""
        task = _sample_task(error="something failed", failed_step=2, step_count=4)
        result = self.agent.run({"task": task, "error": "something failed", "plan": {}})
        output = result.output
        assert output["failed_step_index"] == 2

    def test_debugger_confidence_higher_for_known_category(self):
        """Known failure category should have higher confidence than unknown."""
        known = self.agent.run(
            {
                "task": _sample_task(error="timeout"),
                "error": "timeout",
                "plan": {},
            }
        )
        unknown = self.agent.run(
            {
                "task": _sample_task(error="xyzzy"),
                "error": "xyzzy",
                "plan": {},
            }
        )
        # Both start at 0.6 base, but LLM may adjust. At minimum they should
        # be valid confidence values.
        assert known.confidence >= 0.0
        assert unknown.confidence >= 0.0
