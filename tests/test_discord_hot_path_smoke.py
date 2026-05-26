"""Smoke test: Discord → Gateway → CognitiveLoop → ModelRouter → Governance.

Verifies the entire production hot path can initialize without crashing.
Does NOT send Discord messages or call LLMs — just proves the import
chain and constructor chain are intact.
"""
import os
import sys

import pytest

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))
from dotenv import load_dotenv

load_dotenv(os.path.join(os.environ.get("UMH_ROOT", "/opt/OS"), "services", ".env"))


class TestDiscordBotImports:
    def test_discord_bot_importable(self):
        import services.discord_bot  # noqa: F401

    def test_message_handlers_importable(self):
        import services.discord_message_handlers  # noqa: F401

    def test_bot_commands_importable(self):
        import services.discord_bot_commands  # noqa: F401


class TestGateway:
    def test_gateway_importable(self):
        from substrate.control_plane.runtime.gateway import EntrepreneurOSGateway
        assert EntrepreneurOSGateway is not None

    def test_gateway_is_singleton(self):
        from substrate.control_plane.runtime.gateway import EntrepreneurOSGateway
        g1 = EntrepreneurOSGateway()
        g2 = EntrepreneurOSGateway()
        assert g1 is g2


class TestCognitiveLoop:
    def test_cognitive_loop_importable(self):
        from substrate.control_plane.runtime.cognitive_loop import CognitiveLoop
        assert CognitiveLoop is not None


class TestModelRouter:
    def test_model_router_importable(self):
        from adapters.models.model_router import call_with_fallback
        assert callable(call_with_fallback)

    def test_cc_sdk_importable(self):
        from adapters.models.cc_sdk import query_cc_sync
        assert callable(query_cc_sync)

    def test_agent_runtime_importable(self):
        from adapters.models.agent_runtime import AgentRuntime
        assert AgentRuntime is not None


class TestGovernance:
    def test_authority_engine_importable(self):
        from substrate.governance.policy.authority_engine import AuthorityEngine
        assert AuthorityEngine is not None

    def test_concrete_governance_engine_importable(self):
        from substrate.control_plane.governance import ConcreteGovernanceEngine
        assert ConcreteGovernanceEngine is not None

    def test_execution_authority_engine_importable(self):
        from substrate.governance.policy.execution_authority_engine_v1 import (
            CapabilityAuthority,
            EnvironmentAuthority,
        )
        assert CapabilityAuthority is not None
        assert EnvironmentAuthority is not None


class TestMemory:
    def test_agent_memory_importable(self):
        from substrate.state.memory.memory import AgentMemory
        assert AgentMemory is not None

    def test_embedding_engine_importable(self):
        from substrate.understanding.embedding.embedding_engine import EmbeddingEngine
        assert EmbeddingEngine is not None


class TestSubstrate:
    def test_substrate_class_importable(self):
        from substrate import Substrate
        assert Substrate is not None

    def test_execution_spine_importable(self):
        from substrate.execution.spine import ConcreteExecutionSpine
        assert ConcreteExecutionSpine is not None

    def test_types_importable(self):
        from substrate.types import SignalEnvelope, ExecutionResult
        assert SignalEnvelope is not None
        assert ExecutionResult is not None


class TestAgentTeams:
    def test_agent_teams_importable(self):
        from substrate.control_plane.agents.agent_teams import run_team_task
        assert callable(run_team_task)


class TestTransports:
    def test_discord_utils_importable(self):
        from transports.discord.discord_utils import post_to_webhook, chunk_message
        assert callable(post_to_webhook)
        assert callable(chunk_message)

    def test_signal_factory_importable(self):
        from transports.discord.signal_factory import message_to_signal
        assert callable(message_to_signal)
