"""Runtime Continuity Store v1.

Append-only JSONL persistence for runtime continuity data:
events, traces, outcomes, context updates, continuity snapshots,
open loops, and resume packets.

UMH substrate subsystem. Phase 96.8BN.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class RuntimeContinuityStore:
    """Persists runtime continuity data to JSONL files."""

    def __init__(self, store_dir: str | Path = "data/runtime/substrate_continuity"):
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)

        self.events_path = self.store_dir / "events.jsonl"
        self.traces_path = self.store_dir / "traces.jsonl"
        self.outcomes_path = self.store_dir / "outcomes.jsonl"
        self.context_updates_path = self.store_dir / "context_updates.jsonl"
        self.snapshots_path = self.store_dir / "continuity_snapshots.jsonl"
        self.summaries_path = self.store_dir / "session_summaries.jsonl"
        self.resume_packets_path = self.store_dir / "resume_packets.jsonl"

    def _append(self, path: Path, record: dict[str, Any]) -> None:
        with open(path, "a") as f:
            f.write(json.dumps(record, separators=(",", ":")) + "\n")

    def append_event(self, event: dict[str, Any]) -> None:
        self._append(self.events_path, event)

    def append_trace(self, trace: dict[str, Any]) -> None:
        self._append(self.traces_path, trace)

    def append_outcome(self, outcome: dict[str, Any]) -> None:
        self._append(self.outcomes_path, outcome)

    def append_context_update(self, update: dict[str, Any]) -> None:
        self._append(self.context_updates_path, update)

    def save_snapshot(self, snapshot: dict[str, Any]) -> None:
        self._append(self.snapshots_path, snapshot)

    def save_summary(self, summary: dict[str, Any]) -> None:
        self._append(self.summaries_path, summary)

    def save_resume_packet(self, packet: dict[str, Any]) -> Path:
        self._append(self.resume_packets_path, packet)
        latest_path = self.store_dir / "latest_resume_packet.json"
        with open(latest_path, "w") as f:
            json.dump(packet, f, indent=2)
        return latest_path

    def load_latest_resume_packet(self) -> dict[str, Any] | None:
        latest_path = self.store_dir / "latest_resume_packet.json"
        if not latest_path.exists():
            return None
        with open(latest_path) as f:
            return json.load(f)

    def load_latest_snapshot(self) -> dict[str, Any] | None:
        return self._load_last_line(self.snapshots_path)

    def load_recent_events(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._load_last_n(self.events_path, limit)

    def load_recent_traces(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._load_last_n(self.traces_path, limit)

    def load_recent_outcomes(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._load_last_n(self.outcomes_path, limit)

    def load_all_summaries(self) -> list[dict[str, Any]]:
        return self._load_all(self.summaries_path)

    def count_events(self) -> int:
        return self._count_lines(self.events_path)

    def count_traces(self) -> int:
        return self._count_lines(self.traces_path)

    def count_outcomes(self) -> int:
        return self._count_lines(self.outcomes_path)

    def get_stats(self) -> dict[str, Any]:
        return {
            "events": self.count_events(),
            "traces": self.count_traces(),
            "outcomes": self.count_outcomes(),
            "snapshots": self._count_lines(self.snapshots_path),
            "summaries": self._count_lines(self.summaries_path),
            "resume_packets": self._count_lines(self.resume_packets_path),
            "has_latest_resume": (self.store_dir / "latest_resume_packet.json").exists(),
        }

    def _load_all(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        records = []
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records

    def _load_last_n(self, path: Path, n: int) -> list[dict[str, Any]]:
        all_records = self._load_all(path)
        return all_records[-n:]

    def _load_last_line(self, path: Path) -> dict[str, Any] | None:
        if not path.exists():
            return None
        last = None
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    last = json.loads(line)
        return last

    def _count_lines(self, path: Path) -> int:
        if not path.exists():
            return 0
        count = 0
        with open(path) as f:
            for line in f:
                if line.strip():
                    count += 1
        return count
