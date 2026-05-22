"""tests for DEX advisor — interpret, decompose, delegate, synthesize."""

import pytest
from services.umh.organism.advisor import Advisor
from services.umh.organism.store import OrganismStore


@pytest.fixture
def store(tmp_path):
    return OrganismStore(store_dir=tmp_path / "organism")


@pytest.fixture
def advisor(store):
    return Advisor(store=store)


def test_advisor_has_agents(advisor):
    agents = advisor.list_agents()
    assert len(agents) == 3
    names = {a["agent_name"] for a in agents}
    assert names == {"Researcher", "Builder", "Auto-Research"}


def test_advisor_delegates_to_researcher(advisor):
    result = advisor.handle_signal(
        "Audit cognitive_loop.py for state mutations outside canonical paths"
    )
    assert result is not None
    assert result["delegated_to"] == "researcher"
    assert result["deliverable"] is not None


def test_advisor_delegates_to_builder(advisor):
    result = advisor.handle_signal(
        "Create a new file at /tmp/test_organism.txt with content 'hello'"
    )
    assert result is not None
    assert result["delegated_to"] == "builder"


def test_advisor_returns_status(advisor):
    status = advisor.organism_status()
    assert "agents" in status
    assert "total_deliverables" in status
    assert len(status["agents"]) == 3
