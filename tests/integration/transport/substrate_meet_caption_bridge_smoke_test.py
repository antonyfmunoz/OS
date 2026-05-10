"""Smoke tests for eos_ai.substrate.meet_caption_bridge.

Writer tests are owned by Subagent A. Reader tests are appended below
by Subagent B. Run directly:

    python3 tests/substrate/substrate_meet_caption_bridge_smoke_test.py
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
from pathlib import Path

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from eos_ai.substrate.meet_caption_bridge import (  # noqa: E402
    BRIDGE_ROOT,
    SOURCE_TAG,
    CaptionWriter,
    append_caption,
    bridge_path_for,
    compute_event_id,
    now_iso_utc,
    sanitize_meeting_code,
)


# === WRITER TESTS (Subagent A) ===


def _tmp_root() -> Path:
    return Path(tempfile.mkdtemp(prefix="meetbridge_"))


def test_sanitize_meeting_code() -> None:
    assert sanitize_meeting_code("abc-xyz_123") == "abc-xyz_123"
    assert sanitize_meeting_code("abc xyz!@#") == "abc_xyz"
    assert sanitize_meeting_code("") == "unknown"
    assert sanitize_meeting_code("!!!") == "unknown"
    assert sanitize_meeting_code("a" * 200) == "a" * 64
    # non-string
    assert sanitize_meeting_code(None) == "unknown"  # type: ignore[arg-type]


def test_bridge_path_for_creates_dir() -> None:
    root = _tmp_root()
    # remove then let it recreate
    os.rmdir(root)
    path = bridge_path_for("abc-test", root=root)
    assert root.exists()
    assert path.parent == root
    assert path.name == "abc-test.jsonl"
    mode = oct(root.stat().st_mode & 0o777)
    assert mode == "0o700", f"expected 0o700, got {mode}"


def test_compute_event_id_deterministic() -> None:
    a = compute_event_id("2026-01-01T00:00:00.000000Z", "hello", "x", "m1")
    b = compute_event_id("2026-01-01T00:00:00.000000Z", "hello", "x", "m1")
    c = compute_event_id("2026-01-01T00:00:00.000000Z", "hello", "y", "m1")
    assert a == b
    assert a != c
    assert len(a) == 16
    assert all(ch in "0123456789abcdef" for ch in a)


def test_append_writes_one_line_jsonl() -> None:
    root = _tmp_root()
    w = CaptionWriter("abc-test", root=root)
    result = w.append("hello world", speaker="tester")
    assert result["status"] == "ok", result
    assert result["event_id"]
    lines = w.path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    rec = json.loads(lines[0])
    for key in ("ts", "text", "speaker", "meeting_code", "source", "event_id"):
        assert key in rec, f"missing {key}"
    assert rec["text"] == "hello world"
    assert rec["speaker"] == "tester"
    assert rec["meeting_code"] == "abc-test"
    assert rec["source"] == SOURCE_TAG
    assert rec["ts"].endswith("Z")


def test_append_atomic_many_threads() -> None:
    root = _tmp_root()
    w = CaptionWriter("atomic", root=root)
    N_THREADS = 20
    PER_THREAD = 25
    total = N_THREADS * PER_THREAD

    def worker(tid: int) -> None:
        for i in range(PER_THREAD):
            r = w.append(f"t{tid}-i{i}", speaker=f"s{tid}")
            assert r["status"] == "ok"

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(N_THREADS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    raw = w.path.read_bytes()
    # No partial line: must end with newline
    assert raw.endswith(b"\n")
    lines = raw.decode("utf-8").splitlines()
    assert len(lines) == total, f"expected {total}, got {len(lines)}"
    # Each line parses independently
    for line in lines:
        rec = json.loads(line)
        assert rec["source"] == SOURCE_TAG
        assert rec["meeting_code"] == "atomic"


def test_append_empty_text_returns_empty_status() -> None:
    root = _tmp_root()
    w = CaptionWriter("empty", root=root)
    for bad in ("", "   ", "\n\t"):
        r = w.append(bad)
        assert r["status"] == "empty_text", r
    assert not w.path.exists()


def test_append_merges_extra_under_canonical() -> None:
    root = _tmp_root()
    w = CaptionWriter("legit", root=root)
    r = w.append(
        "hi",
        speaker="me",
        extra={"meeting_code": "HIJACK", "source": "EVIL", "custom": "x"},
    )
    assert r["status"] == "ok"
    rec = json.loads(w.path.read_text(encoding="utf-8").splitlines()[0])
    assert rec["meeting_code"] == "legit"  # canonical wins
    assert rec["source"] == SOURCE_TAG  # canonical wins
    assert rec["custom"] == "x"  # extra preserved


def test_append_many() -> None:
    root = _tmp_root()
    w = CaptionWriter("many", root=root)
    items = [
        {"text": "one", "speaker": "a"},
        {"text": "two"},
        {"text": ""},  # invalid
        "not a dict",  # invalid
        {"text": "three", "speaker": "b", "extra_field": 1},
    ]
    agg = w.append_many(items)  # type: ignore[arg-type]
    assert agg["written"] == 3, agg
    assert len(agg["errors"]) == 2, agg
    lines = w.path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3


def test_module_level_append_caption() -> None:
    root = _tmp_root()
    r = append_caption("mod-lvl", "hi there", speaker="x", root=root)
    assert r["status"] == "ok"
    path = bridge_path_for("mod-lvl", root=root)
    assert path.exists()
    assert "hi there" in path.read_text(encoding="utf-8")


def test_now_iso_utc_format() -> None:
    ts = now_iso_utc()
    assert ts.endswith("Z")
    assert "T" in ts


def test_bridge_root_constant() -> None:
    assert str(BRIDGE_ROOT).endswith("meet_captions")


_WRITER_TESTS = [
    test_sanitize_meeting_code,
    test_bridge_path_for_creates_dir,
    test_compute_event_id_deterministic,
    test_append_writes_one_line_jsonl,
    test_append_atomic_many_threads,
    test_append_empty_text_returns_empty_status,
    test_append_merges_extra_under_canonical,
    test_append_many,
    test_module_level_append_caption,
    test_now_iso_utc_format,
    test_bridge_root_constant,
]


def run_all() -> int:
    failures = 0
    for fn in _WRITER_TESTS:
        name = fn.__name__
        try:
            fn()
            print(f"PASS {name}")
        except Exception as e:  # noqa: BLE001
            failures += 1
            print(f"FAIL {name}: {e!r}")
    if failures:
        print(f"\n{failures} failure(s)")
        return 1
    print("\nall writer tests passed")
    return 0


# === READER TESTS (Subagent B) — appended below ===


from eos_ai.substrate.meet_caption_bridge import (  # noqa: E402
    CaptionReader,
    make_bridge_hook,
)


def test_reader_empty_file_returns_empty_no_raise() -> None:
    root = _tmp_root()
    r = CaptionReader("no-file", root=root)
    assert r.read_new() == []
    assert r.offset == 0
    s = r.stats()
    assert s["file_exists"] is False
    assert s["total_valid"] == 0


def test_reader_reads_new_lines_after_append() -> None:
    root = _tmp_root()
    w = CaptionWriter("live", root=root)
    r = CaptionReader("live", root=root)
    assert r.read_new() == []
    w.append("first", speaker="a")
    w.append("second", speaker="b")
    out = r.read_new(max_lines=10)
    assert len(out) == 2
    assert out[0]["text"] == "first"
    assert out[1]["text"] == "second"
    # second call returns nothing new
    assert r.read_new() == []
    # new append picked up
    w.append("third", speaker="c")
    out2 = r.read_new()
    assert len(out2) == 1
    assert out2[0]["text"] == "third"


def test_reader_offset_advances_and_stops_at_partial_line() -> None:
    root = _tmp_root()
    path = bridge_path_for("partial", root=root)
    eid = compute_event_id("2026-01-01T00:00:00.000000Z", "valid", "s", "partial")
    valid_line = json.dumps(
        {
            "ts": "2026-01-01T00:00:00.000000Z",
            "text": "valid",
            "speaker": "s",
            "meeting_code": "partial",
            "source": "google_meet",
            "event_id": eid,
        }
    )
    path.write_bytes((valid_line + "\n" + '{"parti').encode("utf-8"))
    r = CaptionReader("partial", root=root)
    out = r.read_new()
    assert len(out) == 1
    assert out[0]["text"] == "valid"
    # Offset should be at start of partial line.
    assert r.offset == len(valid_line) + 1
    # Second read returns nothing (partial stays pending).
    assert r.read_new() == []
    # Completing the partial yields it.
    with open(path, "ab") as f:
        eid2 = compute_event_id(
            "2026-01-01T00:00:01.000000Z", "second", None, "partial"
        )
        tail = json.dumps(
            {
                "ts": "2026-01-01T00:00:01.000000Z",
                "text": "second",
                "speaker": None,
                "meeting_code": "partial",
                "source": "google_meet",
                "event_id": eid2,
            }
        )
        # rewrite to replace the bad partial with a fresh complete line
    # Simpler: truncate and rewrite file with valid+complete second line
    path.write_bytes(
        (
            valid_line
            + "\n"
            + json.dumps(
                {
                    "ts": "2026-01-01T00:00:01.000000Z",
                    "text": "second",
                    "speaker": None,
                    "meeting_code": "partial",
                    "source": "google_meet",
                    "event_id": eid2,
                }
            )
            + "\n"
        ).encode("utf-8")
    )
    out2 = r.read_new()
    assert len(out2) == 1
    assert out2[0]["text"] == "second"


def test_reader_skips_corrupt_json_line() -> None:
    root = _tmp_root()
    path = bridge_path_for("corrupt", root=root)
    eid = compute_event_id("2026-01-01T00:00:00.000000Z", "ok", "s", "corrupt")
    good = json.dumps(
        {
            "ts": "2026-01-01T00:00:00.000000Z",
            "text": "ok",
            "speaker": "s",
            "meeting_code": "corrupt",
            "source": "google_meet",
            "event_id": eid,
        }
    )
    path.write_bytes(("{bad json}\n" + good + "\n").encode("utf-8"))
    r = CaptionReader("corrupt", root=root)
    out = r.read_new()
    assert len(out) == 1
    assert out[0]["text"] == "ok"
    s = r.stats()
    assert s["total_skipped_corrupt"] == 1


def test_reader_dedupes_by_event_id() -> None:
    root = _tmp_root()
    w = CaptionWriter("dedupe", root=root)
    w.append(
        "hello",
        speaker="x",
        ts="2026-01-01T00:00:00.000000Z",
        event_id="FIXED123",
    )
    w.append(
        "hello",
        speaker="x",
        ts="2026-01-01T00:00:00.000000Z",
        event_id="FIXED123",
    )
    r = CaptionReader("dedupe", root=root)
    out = r.read_new(max_lines=10)
    assert len(out) == 1
    s = r.stats()
    assert s["total_skipped_duplicate"] == 1


def test_reader_bounded_by_max_lines() -> None:
    root = _tmp_root()
    w = CaptionWriter("bounded", root=root)
    for i in range(20):
        w.append(f"m{i}", speaker="s", event_id=f"E{i:04d}")
    r = CaptionReader("bounded", root=root)
    first = r.read_new(max_lines=5)
    assert len(first) == 5
    assert first[0]["text"] == "m0"
    assert first[-1]["text"] == "m4"
    second = r.read_new(max_lines=5)
    assert len(second) == 5
    assert second[0]["text"] == "m5"
    assert second[-1]["text"] == "m9"


def test_reader_persists_offset_when_enabled() -> None:
    root = _tmp_root()
    w = CaptionWriter("persist", root=root)
    for i in range(5):
        w.append(f"m{i}", event_id=f"P{i}")
    r1 = CaptionReader("persist", root=root, persist_offset=True)
    out1 = r1.read_new(max_lines=3)
    assert len(out1) == 3
    off1 = r1.offset
    assert off1 > 0
    # New reader instance resumes at persisted offset
    r2 = CaptionReader("persist", root=root, persist_offset=True)
    assert r2.offset == off1
    out2 = r2.read_new(max_lines=10)
    assert len(out2) == 2
    assert out2[0]["text"] == "m3"


def test_make_bridge_hook_yields_source_shape() -> None:
    root = _tmp_root()
    w = CaptionWriter("hookshape", root=root)
    for i in range(3):
        w.append(f"u{i}", speaker=f"sp{i}", event_id=f"H{i}")
    hook = make_bridge_hook("hookshape", root=root, batch_size=5)
    seen = []
    for _ in range(3):
        v = hook()
        assert v is not None
        assert set(v.keys()) == {"text", "user_id", "participant_name", "metadata"}
        seen.append(v)
    assert seen[0]["text"] == "u0"
    assert seen[0]["participant_name"] == "sp0"
    assert seen[0]["user_id"] == "sp0"
    assert hook() is None


def test_make_bridge_hook_metadata_preserves_canonical_fields() -> None:
    root = _tmp_root()
    w = CaptionWriter("metacheck", root=root)
    w.append("only", speaker="me", event_id="M1")
    hook = make_bridge_hook("metacheck", root=root, batch_size=5)
    v = hook()
    assert v is not None
    meta = v["metadata"]
    for key in ("ts", "meeting_code", "source", "event_id"):
        assert key in meta, f"missing metadata key {key}"
    assert meta["source"] == "google_meet"
    assert meta["meeting_code"] == "metacheck"
    assert meta["event_id"] == "M1"


def test_drain_all_hard_cap() -> None:
    root = _tmp_root()
    w = CaptionWriter("drain", root=root)
    for i in range(300):
        w.append(f"d{i}", event_id=f"D{i:04d}")
    r = CaptionReader("drain", root=root)
    out = r.drain_all(hard_cap=100)
    assert len(out) == 100
    assert out[0]["text"] == "d0"
    assert out[-1]["text"] == "d99"


_READER_TESTS = [
    test_reader_empty_file_returns_empty_no_raise,
    test_reader_reads_new_lines_after_append,
    test_reader_offset_advances_and_stops_at_partial_line,
    test_reader_skips_corrupt_json_line,
    test_reader_dedupes_by_event_id,
    test_reader_bounded_by_max_lines,
    test_reader_persists_offset_when_enabled,
    test_make_bridge_hook_yields_source_shape,
    test_make_bridge_hook_metadata_preserves_canonical_fields,
    test_drain_all_hard_cap,
]

_WRITER_TESTS.extend(_READER_TESTS)


if __name__ == "__main__":
    sys.exit(run_all())
