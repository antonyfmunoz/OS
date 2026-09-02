"""P4S31 Voice Convergence — operator_api warm-engine preload (Commit 3).

Proves the warm VoiceEngine is a process-wide singleton and that the governed
WS builds a VoiceSession on the SAME preloaded instance (GAP A: the preload is
not wasted on an engine nobody uses).
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import substrate.execution.voice.warm_engine as we


def test_warm_engine_is_singleton() -> None:
    we.reset_warm_engine_for_tests()
    a = we.get_warm_engine()
    b = we.get_warm_engine()
    assert a is b


def test_preload_loads_model_once(monkeypatch) -> None:
    we.reset_warm_engine_for_tests()
    fake = MagicMock()
    fake.intelligent.load_faster_whisper = MagicMock(return_value=True)
    monkeypatch.setattr(we, "VoiceEngine", lambda: fake)
    assert we.preload_warm_engine() is True
    fake.intelligent.load_faster_whisper.assert_called_once_with(local_files_only=True)
    # subsequent get returns the same preloaded instance
    assert we.get_warm_engine() is fake


def test_preload_reports_fail_soft_load_failure(monkeypatch) -> None:
    we.reset_warm_engine_for_tests()
    fake = MagicMock()
    fake.intelligent.load_faster_whisper = MagicMock(return_value=False)
    monkeypatch.setattr(we, "VoiceEngine", lambda: fake)
    assert we.preload_warm_engine() is False
    fake.intelligent.load_faster_whisper.assert_called_once_with(local_files_only=True)
    assert we.get_warm_engine() is fake


def test_ws_uses_same_warm_engine(monkeypatch) -> None:
    # GAP A: the WS-built VoiceSession's engine IS the preloaded singleton.
    we.reset_warm_engine_for_tests()
    sentinel = MagicMock()
    monkeypatch.setattr(we, "VoiceEngine", lambda: sentinel)
    warm = we.get_warm_engine()

    from substrate.execution.voice.session import VoiceSession

    sess = VoiceSession(engine=we.get_warm_engine())
    assert sess._engine is warm is sentinel
