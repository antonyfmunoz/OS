"""End-to-end test — the vertical slice acceptance criterion.

Signal in -> advisor interprets -> researcher agent receives -> worker executes
-> critique loop runs -> deliverable persisted -> trace queryable.
"""

import pytest
from substrate.organism.advisor import Advisor
from substrate.organism.store import OrganismStore


@pytest.fixture
def store(tmp_path):
    return OrganismStore(store_dir=tmp_path / "organism")


@pytest.fixture
def advisor(store):
    return Advisor(store=store)


def test_full_vertical_slice(advisor, store):
    """Antony sends a signal. DEX delegates. Agent executes. Deliverable appears."""
    result = advisor.handle_signal(
        "Audit the services/umh/organism/ directory for any missing __init__.py files"
    )

    assert result["delegated_to"] in ("researcher", "builder")
    assert result["deliverable"] is not None
    deliverable = result["deliverable"]

    assert "self_critique" in deliverable
    assert deliverable["self_critique"]["score"] >= 1

    assert result["trace_id"] is not None

    stored = store.list_deliverables()
    assert len(stored) >= 1

    signals = store.list_learning_signals()
    assert len(signals) >= 1

    messages = store.list_messages(recipient="researcher")
    assert len(messages) >= 1


def test_multiple_signals_accumulate(advisor, store):
    """Multiple signals produce accumulating deliverables."""
    advisor.handle_signal("Check for unused imports in app.py")
    advisor.handle_signal("Search for TODO comments in the codebase")

    deliverables = store.list_deliverables()
    assert len(deliverables) >= 2


def test_organism_status_reflects_work(advisor, store):
    """After work, organism status shows completed tasks."""
    advisor.handle_signal("List all Python files in services/umh/")

    status = advisor.organism_status()
    assert status["total_deliverables"] >= 1
    assert status["total_learning_signals"] >= 1
    assert any(a["tasks_completed"] > 0 for a in status["agents"])
