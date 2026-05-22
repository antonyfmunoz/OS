"""tests for organism ViewFrame event broadcasting."""

import pytest
from substrate.organism.advisor import Advisor
from substrate.organism.store import OrganismStore
from services.umh.sockets.envelopes import ViewFrame


class FakeViewSocket:
    def __init__(self):
        self.frames: list[ViewFrame] = []

    def broadcast(self, frame: ViewFrame) -> None:
        self.frames.append(frame)


@pytest.fixture
def store(tmp_path):
    return OrganismStore(store_dir=tmp_path / "organism")


@pytest.fixture
def view_socket():
    return FakeViewSocket()


@pytest.fixture
def advisor(store, view_socket):
    return Advisor(store=store, view_socket=view_socket)


def test_signal_emits_events(advisor, view_socket):
    advisor.handle_signal("Audit services/umh/organism/ for missing files")
    event_types = [f.event_type for f in view_socket.frames]
    assert "organism.signal_received" in event_types
    assert "organism.task_delegated" in event_types
    assert "organism.deliverable_produced" in event_types


def test_signal_received_has_routing(advisor, view_socket):
    advisor.handle_signal("Check for unused imports")
    received = [f for f in view_socket.frames if f.event_type == "organism.signal_received"]
    assert len(received) == 1
    assert received[0].data["routed_to"] == "researcher"
    assert received[0].integration_id == "organism"


def test_deliverable_event_has_critique(advisor, view_socket):
    advisor.handle_signal("Search for TODO comments")
    delivered = [f for f in view_socket.frames if f.event_type == "organism.deliverable_produced"]
    assert len(delivered) == 1
    assert "critique_score" in delivered[0].data
    assert delivered[0].data["critique_score"] is not None


def test_no_events_without_view_socket(store):
    advisor = Advisor(store=store, view_socket=None)
    result = advisor.handle_signal("List files")
    assert result["deliverable"] is not None
