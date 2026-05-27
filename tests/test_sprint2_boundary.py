"""Sprint 2 boundary repair tests — verify substrate→adapters type extraction.

Validates:
1. Canonical types live in substrate.contracts.agent_types
2. Adapters re-export the same objects (identity check, not equality)
3. No TaskType/AgentResult/RoutingResult imports from adapters remain in substrate
4. Backward compatibility for external consumers importing from adapters
"""

import os
import subprocess

os.environ.setdefault("EOS_ORG_ID", "test-org-id")
os.environ.setdefault("EOS_USER_ID", "test-user-id")


class TestCanonicalTypes:
    """Verify types are defined in substrate.contracts.agent_types."""

    def test_task_type_import(self):
        from substrate.contracts.agent_types import TaskType

        assert TaskType.SCORE.value == "score"
        assert TaskType.CONVERSATION.value == "conversation"
        assert TaskType.STRATEGIC.value == "strategic"
        assert len(TaskType) == 20

    def test_agent_result_import(self):
        from substrate.contracts.agent_types import AgentResult

        r = AgentResult(
            output="test",
            model_used="test-model",
            tokens_used={"input": 10, "output": 20, "total": 30},
            skill_used=None,
        )
        assert r.output == "test"
        assert r.cost_usd == 0.0

    def test_routing_result_import(self):
        from substrate.contracts.agent_types import RoutingResult

        r = RoutingResult(output="hello", provider="anthropic", model="sonnet", task_type="analyze")
        assert r.tokens_used == 0

    def test_model_provider_import(self):
        from substrate.contracts.agent_types import ModelProvider

        assert ModelProvider.ANTHROPIC.value == "anthropic"
        assert ModelProvider.CC_SDK.value == "cc_sdk"

    def test_cost_functions(self):
        from substrate.contracts.agent_types import COST_PER_MILLION_TOKENS, calculate_cost

        assert "claude-haiku-4-5-20251001" in COST_PER_MILLION_TOKENS
        cost = calculate_cost("claude-haiku-4-5-20251001", {"input": 1000, "output": 500})
        assert cost > 0


class TestBackwardCompatibility:
    """Adapters re-export the canonical types (same object identity)."""

    def test_agent_runtime_reexports_task_type(self):
        from substrate.contracts.agent_types import TaskType as canonical
        from adapters.models.agent_runtime import TaskType as reexported

        assert canonical is reexported

    def test_agent_runtime_reexports_agent_result(self):
        from substrate.contracts.agent_types import AgentResult as canonical
        from adapters.models.agent_runtime import AgentResult as reexported

        assert canonical is reexported

    def test_model_router_reexports_task_type(self):
        from substrate.contracts.agent_types import TaskType as canonical
        from adapters.models.model_router import TaskType as reexported

        assert canonical is reexported

    def test_model_router_reexports_routing_result(self):
        from substrate.contracts.agent_types import RoutingResult as canonical
        from adapters.models.model_router import RoutingResult as reexported

        assert canonical is reexported

    def test_model_router_reexports_model_provider(self):
        from substrate.contracts.agent_types import ModelProvider as canonical
        from adapters.models.model_router import ModelProvider as reexported

        assert canonical is reexported


class TestNoTypeImportsFromAdapters:
    """Verify substrate no longer imports TaskType/AgentResult from adapters."""

    def test_no_tasktype_from_adapters_in_substrate(self):
        result = subprocess.run(
            ["grep", "-rn", "from adapters.*import.*TaskType", "substrate/"],
            capture_output=True,
            text=True,
        )
        violations = [
            line
            for line in result.stdout.strip().split("\n")
            if line and "__pycache__" not in line
        ]
        assert violations == [], f"TaskType still imported from adapters in substrate:\n" + "\n".join(violations)

    def test_no_agentresult_from_adapters_in_substrate(self):
        result = subprocess.run(
            ["grep", "-rn", r"from adapters.*import.*AgentResult", "substrate/"],
            capture_output=True,
            text=True,
        )
        violations = [
            line
            for line in result.stdout.strip().split("\n")
            if line and "__pycache__" not in line
        ]
        assert violations == [], f"AgentResult still imported from adapters in substrate:\n" + "\n".join(violations)
