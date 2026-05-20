"""Tests for Notion watermark persistence — JSONL append-log."""

from __future__ import annotations

import threading
from pathlib import Path

import pytest

from services.umh.integrations.notion.watermarks import WatermarkStore


class TestWatermarkStore:
    @pytest.fixture()
    def store(self, tmp_path: Path) -> WatermarkStore:
        return WatermarkStore(path=tmp_path / "watermarks.jsonl")

    def test_load_empty_file_missing(self, store: WatermarkStore) -> None:
        assert store.load_watermarks() == {}

    def test_get_watermark_missing_returns_default(self, store: WatermarkStore) -> None:
        wm = store.get_watermark("db-1")
        assert wm == "2000-01-01T00:00:00.000Z"

    def test_record_and_load(self, store: WatermarkStore) -> None:
        store.record_watermark("db-1", "2026-05-20T10:00:00.000Z")
        marks = store.load_watermarks()
        assert marks["db-1"] == "2026-05-20T10:00:00.000Z"

    def test_latest_entry_wins(self, store: WatermarkStore) -> None:
        store.record_watermark("db-1", "2026-05-20T10:00:00.000Z")
        store.record_watermark("db-1", "2026-05-20T11:00:00.000Z")
        store.record_watermark("db-1", "2026-05-20T12:00:00.000Z")
        marks = store.load_watermarks()
        assert marks["db-1"] == "2026-05-20T12:00:00.000Z"

    def test_multiple_databases(self, store: WatermarkStore) -> None:
        store.record_watermark("db-1", "2026-05-20T10:00:00.000Z")
        store.record_watermark("db-2", "2026-05-20T11:00:00.000Z")
        marks = store.load_watermarks()
        assert marks["db-1"] == "2026-05-20T10:00:00.000Z"
        assert marks["db-2"] == "2026-05-20T11:00:00.000Z"

    def test_get_watermark_after_record(self, store: WatermarkStore) -> None:
        store.record_watermark("db-1", "2026-05-20T10:00:00.000Z")
        assert store.get_watermark("db-1") == "2026-05-20T10:00:00.000Z"

    def test_file_created_with_parents(self, tmp_path: Path) -> None:
        deep_path = tmp_path / "a" / "b" / "c" / "watermarks.jsonl"
        store = WatermarkStore(path=deep_path)
        store.record_watermark("db-1", "2026-05-20T10:00:00.000Z")
        assert deep_path.exists()
        assert store.get_watermark("db-1") == "2026-05-20T10:00:00.000Z"

    def test_malformed_lines_skipped(self, store: WatermarkStore) -> None:
        store.path.parent.mkdir(parents=True, exist_ok=True)
        with open(store.path, "w") as f:
            f.write("not json\n")
            f.write('{"database_id": "db-1", "watermark": "2026-05-20T10:00:00.000Z"}\n')
            f.write("{}\n")
        marks = store.load_watermarks()
        assert marks == {"db-1": "2026-05-20T10:00:00.000Z"}

    def test_concurrent_writes(self, store: WatermarkStore) -> None:
        errors: list[Exception] = []

        def writer(db_id: str, count: int) -> None:
            try:
                for i in range(count):
                    store.record_watermark(db_id, f"2026-05-20T{i:02d}:00:00.000Z")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(f"db-{t}", 10)) for t in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        marks = store.load_watermarks()
        assert len(marks) == 4
