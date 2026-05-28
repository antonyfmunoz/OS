"""Tests for WorkcellV2 — durable inbox/outbox execution cells."""

import sys

sys.path.insert(0, "/opt/OS/.claude/worktrees/anti-divergence-gate")

import json
import tempfile
import time
import pytest
from typing import Any

from substrate.organism.runtime_graph import (
    RuntimeCapability,
    RuntimeClass,
    RuntimeResult,
)
from substrate.organism.workcell_protocol import (
    Workcell,
    WorkcellCheckpoint,
    WorkcellMessage,
    WorkcellRole,
    WorkcellStatus,
)


class FakeAdapter:
    def __init__(self, output: str = "result") -> None:
        self._output = output

    @property
    def runtime_id(self) -> str:
        return "fake"

    @property
    def runtime_class(self) -> RuntimeClass:
        return RuntimeClass.AI_CLI

    @property
    def capabilities(self) -> frozenset[RuntimeCapability]:
        return frozenset({RuntimeCapability.REASON})

    def check_available(self) -> bool:
        return True

    def execute(self, prompt: str, **kwargs: Any) -> RuntimeResult | None:
        return RuntimeResult(output=self._output, runtime_id="fake", latency_ms=10)


class FailingAdapter:
    @property
    def runtime_id(self) -> str:
        return "failing"

    @property
    def runtime_class(self) -> RuntimeClass:
        return RuntimeClass.AI_CLI

    @property
    def capabilities(self) -> frozenset[RuntimeCapability]:
        return frozenset({RuntimeCapability.REASON})

    def check_available(self) -> bool:
        return True

    def execute(self, prompt: str, **kwargs: Any) -> RuntimeResult | None:
        raise RuntimeError("adapter crashed")


class TestWorkcellMessage:
    def test_defaults(self):
        msg = WorkcellMessage(sender="test", intent="do_work")
        assert msg.id.startswith("msg-")
        assert msg.created_at > 0
        assert msg.priority == 5

    def test_filename_encoding(self):
        msg = WorkcellMessage(sender="advisor", intent="task", priority=1)
        assert msg.filename.startswith("01-")
        assert "from-advisor" in msg.filename
        assert msg.filename.endswith(".json")

    def test_roundtrip(self):
        msg = WorkcellMessage(sender="test", intent="work", payload={"key": "val"})
        d = msg.to_dict()
        restored = WorkcellMessage.from_dict(d)
        assert restored.sender == msg.sender
        assert restored.intent == msg.intent
        assert restored.payload == msg.payload

    def test_priority_ordering(self):
        high = WorkcellMessage(sender="a", intent="urgent", priority=1)
        low = WorkcellMessage(sender="b", intent="routine", priority=9)
        assert high.filename < low.filename


class TestWorkcellInboxOutbox:
    def test_send_and_receive(self):
        with tempfile.TemporaryDirectory() as td:
            cell = Workcell("test-cell", WorkcellRole.RESEARCHER, base_dir=td)
            msg = WorkcellMessage(
                sender="advisor", intent="research", payload={"task": "analyze code"}
            )
            cell.send_message(msg)

            messages = cell.receive_messages()
            assert len(messages) == 1
            assert messages[0].sender == "advisor"
            assert messages[0].payload["task"] == "analyze code"

    def test_claim_message(self):
        with tempfile.TemporaryDirectory() as td:
            cell = Workcell("test-cell", WorkcellRole.BUILDER, base_dir=td)
            msg = WorkcellMessage(sender="advisor", intent="build")
            cell.send_message(msg)

            messages = cell.receive_messages()
            assert cell.claim_message(messages[0])

            inbox_files = list(cell._inbox.glob("*.json"))
            assert len(inbox_files) == 0

            inflight_files = list(cell._inflight.glob("*.json"))
            assert len(inflight_files) == 1

    def test_complete_message(self):
        with tempfile.TemporaryDirectory() as td:
            cell = Workcell("test-cell", WorkcellRole.EXECUTOR, base_dir=td)
            msg = WorkcellMessage(sender="advisor", intent="execute")
            cell.send_message(msg)

            messages = cell.receive_messages()
            cell.claim_message(messages[0])
            cell.complete_message(messages[0], {"output": "done"})

            processed_files = list(cell._processed.glob("*.json"))
            assert len(processed_files) == 1

            outbox_files = list(cell._outbox.glob("*.json"))
            assert len(outbox_files) == 1

    def test_collect_outbox(self):
        with tempfile.TemporaryDirectory() as td:
            cell = Workcell("test-cell", WorkcellRole.EXECUTOR, base_dir=td)
            msg = WorkcellMessage(sender="advisor", intent="work")
            cell.send_message(msg)

            messages = cell.receive_messages()
            cell.claim_message(messages[0])
            cell.complete_message(messages[0], {"output": "result"})

            outbox = cell.collect_outbox()
            assert len(outbox) == 1
            assert outbox[0].payload["result"]["output"] == "result"

            assert len(list(cell._outbox.glob("*.json"))) == 0

    def test_recover_stale_inflight(self):
        with tempfile.TemporaryDirectory() as td:
            cell = Workcell("test-cell", WorkcellRole.EXECUTOR, base_dir=td)
            msg = WorkcellMessage(sender="advisor", intent="work")
            cell.send_message(msg)

            messages = cell.receive_messages()
            cell.claim_message(messages[0])

            import os

            inflight_path = cell._inflight / messages[0].filename
            old_time = time.time() - 400
            os.utime(inflight_path, (old_time, old_time))

            recovered = cell.recover_stale_inflight()
            assert recovered == 1

            inbox_files = list(cell._inbox.glob("*.json"))
            assert len(inbox_files) == 1


class TestWorkcellExecution:
    def test_process_next(self):
        with tempfile.TemporaryDirectory() as td:
            adapter = FakeAdapter(output="execution result")
            cell = Workcell("exec-cell", WorkcellRole.EXECUTOR, adapter=adapter, base_dir=td)

            msg = WorkcellMessage(sender="coord", intent="execute", payload={"task": "run tests"})
            cell.send_message(msg)

            result = cell.process_next()
            assert result is not None
            assert result["status"] == "completed"
            assert result["output"] == "execution result"
            assert cell.status == WorkcellStatus.IDLE

    def test_process_next_empty_inbox(self):
        with tempfile.TemporaryDirectory() as td:
            adapter = FakeAdapter()
            cell = Workcell("empty-cell", WorkcellRole.EXECUTOR, adapter=adapter, base_dir=td)
            result = cell.process_next()
            assert result is None

    def test_process_next_no_adapter(self):
        with tempfile.TemporaryDirectory() as td:
            cell = Workcell("no-adapter", WorkcellRole.EXECUTOR, base_dir=td)
            msg = WorkcellMessage(sender="test", intent="work")
            cell.send_message(msg)
            result = cell.process_next()
            assert result is not None
            assert "error" in result

    def test_process_next_adapter_crash(self):
        with tempfile.TemporaryDirectory() as td:
            adapter = FailingAdapter()
            cell = Workcell("crash-cell", WorkcellRole.EXECUTOR, adapter=adapter, base_dir=td)

            msg = WorkcellMessage(sender="coord", intent="execute", payload={"task": "crash"})
            cell.send_message(msg)

            result = cell.process_next()
            assert result is not None
            assert result["status"] == "failed"
            assert cell.status == WorkcellStatus.FAILED


class TestWorkcellCheckpoint:
    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as td:
            cell = Workcell("cp-cell", WorkcellRole.BUILDER, base_dir=td)

            checkpoint = WorkcellCheckpoint(
                workcell_id="cp-cell",
                work_unit_id="wu-1",
                progress=0.5,
                partial_result="halfway done",
                context={"files_modified": ["a.py"]},
            )
            cell.save_checkpoint(checkpoint)

            loaded = cell.load_checkpoint()
            assert loaded is not None
            assert loaded.progress == 0.5
            assert loaded.partial_result == "halfway done"
            assert cell.status == WorkcellStatus.CHECKPOINTED

    def test_clear_checkpoint(self):
        with tempfile.TemporaryDirectory() as td:
            cell = Workcell("cp-cell", WorkcellRole.BUILDER, base_dir=td)
            checkpoint = WorkcellCheckpoint(workcell_id="cp-cell", work_unit_id="wu-1")
            cell.save_checkpoint(checkpoint)
            cell.clear_checkpoint()
            assert cell.load_checkpoint() is None


class TestWorkcellHeartbeat:
    def test_write_and_read(self):
        with tempfile.TemporaryDirectory() as td:
            cell = Workcell("hb-cell", WorkcellRole.RESEARCHER, base_dir=td)
            cell.write_heartbeat()

            hb = cell.read_heartbeat()
            assert hb is not None
            assert hb["workcell_id"] == "hb-cell"
            assert hb["role"] == "researcher"
            assert hb["status"] == "idle"

    def test_is_alive(self):
        with tempfile.TemporaryDirectory() as td:
            cell = Workcell("alive-cell", WorkcellRole.EXECUTOR, base_dir=td)
            cell.write_heartbeat()
            assert cell.is_alive()

    def test_is_dead_without_heartbeat(self):
        with tempfile.TemporaryDirectory() as td:
            cell = Workcell("dead-cell", WorkcellRole.EXECUTOR, base_dir=td)
            assert not cell.is_alive()


class TestWorkcellStatus:
    def test_to_dict(self):
        with tempfile.TemporaryDirectory() as td:
            adapter = FakeAdapter()
            cell = Workcell("status-cell", WorkcellRole.COORDINATOR, adapter=adapter, base_dir=td)
            d = cell.to_dict()
            assert d["workcell_id"] == "status-cell"
            assert d["role"] == "coordinator"
            assert d["adapter"] == "fake"
            assert d["status"] == "idle"

    def test_shutdown(self):
        with tempfile.TemporaryDirectory() as td:
            cell = Workcell("shut-cell", WorkcellRole.EXECUTOR, base_dir=td)
            cell.shutdown()
            assert cell.status == WorkcellStatus.SHUTDOWN
