"""Organism store — JSONL persistence for deliverables, messages, agent state."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from substrate.organism.protocols import (
    AgentMessage,
    Deliverable,
    LearningSignal,
)
from substrate.state.runtime_paths import runtime_state_dir


class OrganismStore:
    def __init__(self, store_dir: str | Path | None = None) -> None:
        self._dir = Path(store_dir) if store_dir else runtime_state_dir("organism")
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
        origin_channel: str | None = None,
    ) -> list[dict[str, Any]]:
        all_m = self._read_all(self._messages)
        if recipient:
            all_m = [m for m in all_m if m.get("recipient") == recipient]
        if sender:
            all_m = [m for m in all_m if m.get("sender") == sender]
        if origin_channel:
            all_m = [m for m in all_m if m.get("origin_channel") == origin_channel]
        return all_m[-limit:]

    def save_conversation_turn(
        self,
        content: str,
        response: str,
        origin_channel: str,
        projection_id: str | None = None,
        responder: str = "system",
        media: list[dict[str, Any]] | None = None,
        source: str | None = None,
    ) -> tuple[AgentMessage, AgentMessage]:
        """Persist both inbound user message and outbound response as a pair.

        ``media`` (optional) is a list of MediaAttachment dicts (e.g. a voice
        message's audio) stored on the inbound operator turn so it survives reload —
        /chat/history re-emits it and the cockpit renders the audio player.
        """
        from uuid import uuid4 as _uuid4

        conv_id = _uuid4()
        _inbound_payload: dict[str, Any] = {"content": content, "projection_id": projection_id}
        if media:
            _inbound_payload["media"] = media
        if source:
            # Persist the input source (e.g. "voice") so /chat/history can re-emit it —
            # the cockpit needs it to keep the voice badge + transcript chevron after reload.
            _inbound_payload["source"] = source
        inbound = AgentMessage(
            sender="operator",
            recipient=responder,
            intent="converse",
            payload=_inbound_payload,
            conversation_id=conv_id,
            origin_channel=origin_channel,
        )
        self.save_message(inbound)

        outbound = AgentMessage(
            sender=responder,
            recipient="operator",
            intent="response",
            payload={"content": response, "projection_id": projection_id},
            conversation_id=conv_id,
            parent_message_id=inbound.id,
            origin_channel=origin_channel,
        )
        self.save_message(outbound)
        return inbound, outbound

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
