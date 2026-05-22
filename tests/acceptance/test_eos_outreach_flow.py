"""Acceptance tests for EOS projection layer."""

import asyncio
import subprocess
import sys

sys.path.insert(0, "/opt/OS")

from substrate import Substrate
from substrate.types import ComponentType, SignalEnvelope, SignalSource


class TestEOSOutreach:
    def test_eos_agents_registered(self):
        s = Substrate()
        from projections.eos import register_eos_agents

        asyncio.run(register_eos_agents(s))
        agents = asyncio.run(s.registry.lookup(component_type=ComponentType.AGENT))
        eos_agents = [a for a in agents if "eos" in a.name.lower()]
        assert len(eos_agents) >= 1

    def test_outreach_signal_executes(self):
        s = Substrate()
        from projections.eos import register_eos_agents

        asyncio.run(register_eos_agents(s))
        signal = SignalEnvelope(
            source=SignalSource.USER,
            content="draft outreach for lead John Smith at Acme Corp",
            user_id="test-user",
            organization_id="munoz-holdings",
        )
        result = asyncio.run(s.execute(signal))
        assert result.trace_id is not None

    def test_projection_isolation(self):
        """Verify projections only use public API — no internal imports."""
        result = subprocess.run(
            ["grep", "-rn", "from substrate.", "projections/", "--include=*.py"],
            capture_output=True,
            text=True,
        )
        violations = [
            line
            for line in result.stdout.strip().split("\n")
            if line
            and "from substrate import" not in line
            and "from substrate.types import" not in line
        ]
        assert len(violations) == 0, (
            f"Projection isolation violated:\n" + "\n".join(violations)
        )
