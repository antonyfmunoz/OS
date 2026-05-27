"""
Tests for Law 5.5 Tier 2 — merge_event_payload() method.

These are structural tests (import, signature, type checks) rather than
integration tests, since the method writes to Neon and the test suite
runs without a live DB connection.
"""

import inspect
import json
import os
import sys

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))
from dotenv import load_dotenv

load_dotenv(os.path.join("/opt/OS", "runtime", ".env"))
load_dotenv(os.path.join("/opt/OS", "services", ".env"))


def test_merge_event_payload_exists():
    from substrate.state.memory.memory import AgentMemory
    assert hasattr(AgentMemory, "merge_event_payload")


def test_merge_event_payload_signature():
    from substrate.state.memory.memory import AgentMemory
    sig = inspect.signature(AgentMemory.merge_event_payload)
    params = list(sig.parameters.keys())
    assert params == ["self", "org_id", "event_id", "updates"]


def test_merge_event_payload_annotations():
    from substrate.state.memory.memory import AgentMemory
    hints = AgentMemory.merge_event_payload.__annotations__
    assert hints.get("org_id") is str
    assert hints.get("event_id") is str
    assert hints.get("updates") is dict
    assert hints.get("return") is bool
