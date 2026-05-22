"""Organism store — JSONL persistence for deliverables, messages, agent state."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from services.umh.organism.protocols import (
    AgentMessage,
    Deliverable,
    LearningSignal,
)


class OrganismStore:
    def __init__(self, store_dir: str | Path = "data/umh/organism") -> None:
        self._dir = Path(store_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._deliverables = self._dir / "deliverables.jsonl"
        self._messages = self._dir / "messages.jsonl"
        self._learning = self._dir / "learning_signals.jsonl"
        self._agents_dir = self._dir / "agents"
        self._agents_dir.mkdir(exist_ok=True)

    def _append(self, path: Path, record: dict[str, Any]) -> None:
        with open(path, "a") as f:
            f.write(json.dumps(record, default=str, separators=(",", ":")) + "\n")

    def _read_all(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        entries: list[dict[str, Any]] = []
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
        return entries

    def save_deliverable(self, d: Deliverable) -> None:
        self._append(self._deliverables, d.model_dump(mode="json"))

    def list_deliverables(
        self,
        agent_id: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        all_d = self._read_all(self._deliverables)
        if agent_id:
            all_d = [d for d in all_d if d.get("agent_id") == agent_id]
        return all_d[-limit:]

    def save_message(self, msg: AgentMessage) -> None:
        self._append(self._messages, msg.model_dump(mode="json"))

    def list_messages(
        self,
        recipient: str | None = None,
        sender: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        all_m = self._read_all(self._messages)
        if recipient:
            all_m = [m for m in all_m if m.get("recipient") == recipient]
        if sender:
            all_m = [m for m in all_m if m.get("sender") == sender]
        return all_m[-limit:]

    def save_agent_state(self, agent_id: str, state: dict[str, Any]) -> None:
        state["_updated_at"] = datetime.now(timezone.utc).isoformat()
        path = self._agents_dir / f"{agent_id}.json"
        path.write_text(json.dumps(state, default=str, indent=2))

    def load_agent_state(self, agent_id: str) -> dict[str, Any] | None:
        path = self._agents_dir / f"{agent_id}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def save_learning_signal(self, sig: LearningSignal) -> None:
        self._append(self._learning, sig.model_dump(mode="json"))

    def list_learning_signals(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._read_all(self._learning)[-limit:]
