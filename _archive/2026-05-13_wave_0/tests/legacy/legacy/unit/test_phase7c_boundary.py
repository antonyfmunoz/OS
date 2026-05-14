"""Tests for Phase 7C: Multi-Agent Intelligence Layer — Boundary & invariant checks.

Critical safety tests verifying:
- Agents do NOT import execute() from umh.execution.engine (lightweight_execute is allowed)
- Agents do NOT import from umh.orchestrator
- Agents do NOT mutate state
- AgentOutput is serializable
- BaseAgent is abstract and cannot be instantiated directly
- Review verdict does not gate execution (advisory only)
- Agents are stateless (multiple calls return independent results)
"""

from __future__ import annotations

import inspect
import sys

sys.path.insert(0, "/opt/OS")

import os

os.environ.setdefault("UMH_API_KEY", "test-key-phase7c")

import json
import re
from unittest.mock import MagicMock, patch

import pytest

from umh.agents.base import AgentOutput, AgentRole, BaseAgent
from umh.agents.debugger import DebugAgent
from umh.agents.reviewer import ReviewerAgent


# ── A. Import boundary checks ───────────────────────────────────────


class TestImportBoundaries:
    def test_reviewer_no_execute_import(self):
        """ReviewerAgent source MUST NOT import execute() from umh.execution.engine.

        lightweight_execute is allowed (it is a read-only LLM call wrapper).
        """
        import umh.agents.reviewer

        source = inspect.getsource(umh.agents.reviewer)
        # Check for the dangerous import: "from umh.execution.engine import execute"
        # Must NOT match "from umh.execution.engine import lightweight_execute"
        dangerous = re.findall(r"from\s+umh\.execution\.engine\s+import\s+execute\b", source)
        assert len(dangerous) == 0, (
            "ReviewerAgent imports execute() — only lightweight_execute is allowed"
        )

    def test_debugger_no_execute_import(self):
        """DebugAgent source MUST NOT import execute() from umh.execution.engine."""
        import umh.agents.debugger

        source = inspect.getsource(umh.agents.debugger)
        dangerous = re.findall(r"from\s+umh\.execution\.engine\s+import\s+execute\b", source)
        assert len(dangerous) == 0, (
            "DebugAgent imports execute() — only lightweight_execute is allowed"
        )

    def test_reviewer_no_orchestrator_import(self):
        """ReviewerAgent source MUST NOT import from umh.orchestrator."""
        import umh.agents.reviewer

        source = inspect.getsource(umh.agents.reviewer)
        assert "from umh.orchestrator" not in source
        assert "import umh.orchestrator" not in source

    def test_debugger_no_orchestrator_import(self):
        """DebugAgent source MUST NOT import from umh.orchestrator."""
        import umh.agents.debugger

        source = inspect.getsource(umh.agents.debugger)
        assert "from umh.orchestrator" not in source
        assert "import umh.orchestrator" not in source

    def test_base_agent_no_execute_import(self):
        """BaseAgent source MUST NOT import from umh.execution.engine."""
        import umh.agents.base

        source = inspect.getsource(umh.agents.base)
        assert "from umh.execution.engine import" not in source


# ── B. State mutation checks ─────────────────────────────────────────


class TestStateMutation:
    def test_reviewer_no_state_mutation(self):
        """ReviewerAgent.run has no methods that write to DB, files, or global state.

        Heuristic check: run method source should not contain open(), write(),
        cursor, or destructive os/shutil/subprocess calls.
        """
        import umh.agents.reviewer

        source = inspect.getsource(umh.agents.reviewer.ReviewerAgent.run)
        dangerous_patterns = [
            "open(",
            ".write(",
            "cursor",
            "os.remove",
            "os.unlink",
            "shutil.",
            "subprocess.",
        ]
        for pattern in dangerous_patterns:
            assert pattern not in source, (
                f"ReviewerAgent.run contains '{pattern}' — potential state mutation"
            )

    def test_debugger_no_state_mutation(self):
        """DebugAgent.run has no methods that write to DB, files, or global state."""
        import umh.agents.debugger

        source = inspect.getsource(umh.agents.debugger.DebugAgent.run)
        dangerous_patterns = [
            "open(",
            ".write(",
            "cursor",
            "os.remove",
            "os.unlink",
            "shutil.",
            "subprocess.",
        ]
        for pattern in dangerous_patterns:
            assert pattern not in source, (
                f"DebugAgent.run contains '{pattern}' — potential state mutation"
            )


# ── C. Output correctness ───────────────────────────────────────────


class TestOutputCorrectness:
    def test_reviewer_output_is_dict(self):
        """Reviewer output.output is a dict."""
        reviewer = ReviewerAgent()
        result = reviewer.run(
            {
                "plan": {
                    "steps": [
                        {
                            "step_id": "s1",
                            "name": "Test",
                            "operation": "summarize",
                            "inputs": {"prompt": "test"},
                            "execution_class": "llm_call",
                            "rationale": "test",
                        }
                    ],
                    "source": "template",
                },
                "objective": "Test",
            }
        )
        assert isinstance(result.output, dict)

    def test_debugger_output_is_dict(self):
        """Debugger output.output is a dict."""
        debugger = DebugAgent()
        result = debugger.run(
            {
                "task": {"steps": [], "error": "test error"},
                "error": "test error",
                "plan": {},
            }
        )
        assert isinstance(result.output, dict)

    def test_agent_output_serializable(self):
        """AgentOutput.to_dict() returns a JSON-serializable dict."""
        reviewer = ReviewerAgent()
        result = reviewer.run(
            {
                "plan": {
                    "steps": [
                        {
                            "step_id": "s1",
                            "name": "Test",
                            "operation": "summarize",
                            "inputs": {"prompt": "test"},
                            "execution_class": "llm_call",
                            "rationale": "test",
                        }
                    ],
                    "source": "template",
                },
                "objective": "Test",
            }
        )
        d = result.to_dict()
        # Must not raise
        serialized = json.dumps(d)
        assert isinstance(serialized, str)
        # Round-trip
        deserialized = json.loads(serialized)
        assert deserialized["agent_role"] == "reviewer"

    def test_agent_output_to_dict_has_all_fields(self):
        """to_dict() includes agent_role, agent_id, output, confidence, model_used, timestamp."""
        reviewer = ReviewerAgent()
        result = reviewer.run({"plan": {"steps": []}, "objective": "Test"})
        d = result.to_dict()
        assert "agent_role" in d
        assert "agent_id" in d
        assert "output" in d
        assert "confidence" in d
        assert "model_used" in d
        assert "timestamp" in d


# ── D. Abstract base ────────────────────────────────────────────────


class TestBaseAgent:
    def test_base_agent_is_abstract(self):
        """Cannot instantiate BaseAgent directly."""
        with pytest.raises(TypeError):
            BaseAgent()


# ── E. Advisory-only execution ──────────────────────────────────────


class TestAdvisoryOnly:
    def test_plan_review_does_not_gate_execution(self):
        """Plan with reject verdict can still execute — review is advisory only."""
        from umh.planning.models import PlanObjective, PlanStatus
        from umh.planning.planner import create_plan, execute_plan, reset_plans

        reset_plans()

        obj = PlanObjective(title="inspect_system_status")
        plan = create_plan(obj)
        assert plan.status == PlanStatus.VALIDATED

        # Manually set review verdict to reject
        plan.review = {
            "output": {
                "verdict": "reject",
                "risk_level": "high",
                "issues": [],
                "suggestions": [],
            },
            "agent_role": "reviewer",
        }

        # execute_plan should NOT check review verdict —
        # it only checks plan.status and quality
        from umh.orchestrator.task import TaskStatus

        mock_task = MagicMock()
        mock_task.id = "task_advisory_test"
        mock_task.status = TaskStatus.COMPLETED
        mock_task.paused_approval_id = None
        mock_task.to_dict.return_value = {
            "id": "task_advisory_test",
            "status": "completed",
            "steps": [],
        }

        with patch("umh.orchestrator.task.execute_task", return_value=mock_task):
            result = execute_plan(plan)

        # Execution proceeded despite reject verdict
        assert result is not None
        assert result.id == "task_advisory_test"

        reset_plans()


# ── F. Statelessness ────────────────────────────────────────────────


class TestStatelessness:
    def test_reviewer_is_stateless(self):
        """Calling run() twice with different inputs returns different results."""
        reviewer = ReviewerAgent()

        plan_clean = {
            "steps": [
                {
                    "step_id": "s1",
                    "name": "Safe step",
                    "operation": "summarize",
                    "inputs": {"prompt": "test"},
                    "execution_class": "llm_call",
                    "rationale": "test",
                }
            ],
            "source": "template",
            "confidence": 1.0,
        }
        # This plan has a critical issue (shell_command with wrong exec class
        # and missing required input)
        plan_dangerous = {
            "steps": [
                {
                    "step_id": "s1",
                    "name": "Bad step",
                    "operation": "shell_command",
                    "inputs": {},  # missing "command" -> critical
                    "execution_class": "llm_call",  # wrong class -> critical
                    "rationale": "nuke",
                }
            ],
            "source": "template",
            "confidence": 1.0,
        }

        result1 = reviewer.run({"plan": plan_clean, "objective": "Test safe"})
        result2 = reviewer.run({"plan": plan_dangerous, "objective": "Test dangerous"})

        # Results must differ based on input, proving no state leaks
        assert result1.output["verdict"] != result2.output["verdict"]
        assert result1.output["verdict"] == "approve"
        assert result2.output["verdict"] == "reject"

        # Call again with clean plan to confirm no contamination
        result3 = reviewer.run({"plan": plan_clean, "objective": "Test safe again"})
        assert result3.output["verdict"] == result1.output["verdict"]
        assert result3.output["risk_level"] == result1.output["risk_level"]

    def test_debugger_is_stateless(self):
        """Calling run() twice with different inputs returns different results."""
        debugger = DebugAgent()

        result1 = debugger.run(
            {
                "task": {"steps": [], "error": "timeout"},
                "error": "timeout",
                "plan": {},
            }
        )
        result2 = debugger.run(
            {
                "task": {"steps": [], "error": "permission denied"},
                "error": "permission denied",
                "plan": {},
            }
        )

        assert result1.output["failure_category"] != result2.output["failure_category"]

        # Call again with first input
        result3 = debugger.run(
            {
                "task": {"steps": [], "error": "timeout"},
                "error": "timeout",
                "plan": {},
            }
        )
        assert result3.output["failure_category"] == result1.output["failure_category"]
