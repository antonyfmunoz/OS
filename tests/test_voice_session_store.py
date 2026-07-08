"""P4S31 Voice Convergence — the ONE canonical voice record store.

Proves the folded record store (formerly bridge/voice_session.py) persists and
reloads, migrates legacy-shaped rows, caps retention, and that the convergence
additions — the TOTAL bidirectional STATUS_MAP and the exchange<->turn mappers —
are correct and never raise.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from substrate.execution.voice.store import (
    RECORD_TO_RUNTIME_STATUS,
    STATUS_MAP,
    VoiceSessionRecord,
    VoiceSessionRecordStatus,
    VoiceSessionStore,
    VoiceTurn,
    VoiceTurnSource,
    exchange_to_turns,
    record_status_to_runtime,
    runtime_status_to_record,
    turn_to_exchange,
)


def _fresh_store() -> VoiceSessionStore:
    s = VoiceSessionStore(autoload=False)
    s.clear()
    return s


def test_record_persists_and_reloads() -> None:
    store = _fresh_store()
    rec = VoiceSessionRecord(session_id="vs_test1", node_id="n1", role_slug="ea")
    rec.append_turn(
        VoiceTurn(
            turn_id="vt1",
            source=VoiceTurnSource.USER,
            text="hello",
            occurred_at="2026-07-07T00:00:00+00:00",
        )
    )
    store.put(rec)
    got = store.get("vs_test1")
    assert got is not None
    assert got.turn_count == 1
    # round-trips through dict form
    rebuilt = VoiceSessionRecord.from_dict(got.as_dict())
    assert rebuilt.session_id == "vs_test1"
    assert rebuilt.status == VoiceSessionRecordStatus.ACTIVE  # append promoted it
    assert rebuilt.turns[0].source == VoiceTurnSource.USER


def test_legacy_key_migrates() -> None:
    # A row shaped exactly like the OLD bridge VoiceSession.as_dict() (pending
    # then ended) must load and re-persist as the canonical record unchanged.
    legacy = {
        "session_id": "vs_legacy",
        "node_id": "beast",
        "role_slug": "ea_orchestrator",
        "status": "ended",
        "started_at": "2026-07-01T00:00:00+00:00",
        "ended_at": "2026-07-01T00:05:00+00:00",
        "last_activity_at": "2026-07-01T00:05:00+00:00",
        "turns": [
            {
                "turn_id": "vt_old",
                "source": "user",
                "text": "legacy utterance",
                "occurred_at": "2026-07-01T00:01:00+00:00",
            }
        ],
        "role_history": [],
        "error_reason": None,
        "metadata": {"origin": "bridge"},
    }
    rec = VoiceSessionRecord.from_dict(legacy)
    assert rec.session_id == "vs_legacy"
    assert rec.status == VoiceSessionRecordStatus.ENDED
    assert rec.status.is_terminal
    assert rec.turns[0].text == "legacy utterance"
    # re-persist path is lossless for the fields we carry
    again = VoiceSessionRecord.from_dict(rec.as_dict())
    assert again.status == VoiceSessionRecordStatus.ENDED
    assert again.metadata["origin"] == "bridge"


def test_exchange_to_turns_cardinality() -> None:
    # responded -> 2 turns (USER then AGENT); AGENT carries the action_id.
    turns = exchange_to_turns(
        "what's the weather", "sunny", True, role_slug="ea", action_id="act_1"
    )
    assert len(turns) == 2
    assert turns[0].source == VoiceTurnSource.USER
    assert turns[1].source == VoiceTurnSource.AGENT
    assert turns[1].action_id == "act_1"
    # non-responded -> 1 USER turn only
    one = exchange_to_turns("just a note", "", False)
    assert len(one) == 1
    assert one[0].source == VoiceTurnSource.USER
    # silence -> no turns
    assert exchange_to_turns("", "", False) == []
    # roundtrip back to an exchange-shaped dict
    rt = turn_to_exchange(turns)
    assert rt["utterance"] == "what's the weather"
    assert rt["response_text"] == "sunny"
    assert rt["responded"] is True
    assert rt["action_id"] == "act_1"


def test_status_map_total_roundtrip() -> None:
    # Every runtime operational status maps to a record enum OBJECT.
    for phase in ("idle", "listening", "processing", "speaking", "error"):
        mapped = runtime_status_to_record(phase)
        assert isinstance(mapped, VoiceSessionRecordStatus)
        assert mapped in STATUS_MAP.values()
    # unknown never raises
    assert isinstance(runtime_status_to_record("nonsense"), VoiceSessionRecordStatus)
    # reverse is total over every record status
    for rs in VoiceSessionRecordStatus:
        back = record_status_to_runtime(rs)
        assert isinstance(back, str)
        assert rs in RECORD_TO_RUNTIME_STATUS


def test_retention_caps_at_max() -> None:
    store = _fresh_store()
    # push more than the cap; oldest-by-started_at drop.
    for i in range(120):
        store.put(
            VoiceSessionRecord(
                session_id=f"vs_{i:04d}",
                node_id="n",
                role_slug="ea",
                started_at=f"2026-07-07T00:{i // 60:02d}:{i % 60:02d}+00:00",
            )
        )
    assert len(store) <= 100
