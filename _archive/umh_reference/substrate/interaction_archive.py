"""
Interaction Archive — append-only verbatim conversation store.

The single source of literal conversational truth for EOS.  Every logical
inbound and outbound message is archived here BEFORE transport chunking.

Separate from the event spine by design:
  - Event spine = structured machine events (what happened)
  - Interaction archive = verbatim human/AI text (what was said)
  - They cross-reference via correlation_id

Design rules:
  - Append-only.  Records are NEVER modified or deleted.
  - Verbatim.  raw_text is the exact logical message, not a summary.
  - Pre-chunk.  Outbound archives store the full reply, not Discord slices.
  - Interface-tagged.  Every record carries its source interface for
    cross-device continuity queries.
  - Bounded retrieval.  Query helpers cap results by default.
  - Thread-safe.  Single file lock, moderate throughput.
  - Best-effort.  Archiving failures never block the message path.
  - No DB dependency.  JSONL flat file, same pattern as event_store.

File: logs/interaction_archive.jsonl
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Optional

# ─── Config ──────────────────────────────────────────────────────────────────

_REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
_DEFAULT_ARCHIVE_PATH = os.path.join(_REPO_ROOT, "logs", "interaction_archive.jsonl")
_LOG_PREFIX = "[substrate.interaction_archive]"

# Maximum raw_text length to archive (safety bound)
_MAX_TEXT_LENGTH = 50_000


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def _new_archive_id() -> str:
    return uuid.uuid4().hex


# ─── Enums ───────────────────────────────────────────────────────────────────


class Direction(str, Enum):
    """Whether the message is coming in or going out."""

    INBOUND = "inbound"
    OUTBOUND = "outbound"


class Interface(str, Enum):
    """Source interface / transport for cross-device continuity.

    Each value identifies WHERE the interaction originated or was delivered.
    """

    DISCORD = "discord"
    LOCAL_CLI = "local_cli"
    VPS_CLI = "vps_cli"
    WORKSTATION = "workstation"
    PHONE = "phone"
    WEBHOOK = "webhook"
    VOICE = "voice"
    INTERNAL = "internal"  # system-generated


# ─── Data Model ──────────────────────────────────────────────────────────────


@dataclass
class ArchivedInteraction:
    """One verbatim logical message in the interaction archive.

    Attributes:
        archive_id: Globally unique identifier for this record.
        parent_archive_id: Optional link to a prior message this replies to.
        correlation_id: Workflow-level ID (shared with event spine).
        direction: Inbound (user→system) or outbound (system→user).
        interface: Source interface (discord, vps_cli, phone, etc).
        source_session: Session name (dex_main, dex_builder, etc).
        role: Operating context (ea_product, builder, etc).
        node_id: Node that handled this interaction (if relevant).
        logical_message_id: reply_id or group_id for cross-reference.
        raw_text: The verbatim message text.
        created_at: ISO timestamp of archival.
        metadata: Bounded additional context.
    """

    archive_id: str = field(default_factory=_new_archive_id)
    parent_archive_id: Optional[str] = None
    correlation_id: str = ""
    direction: str = Direction.INBOUND.value
    interface: str = Interface.DISCORD.value
    source_session: str = ""
    role: str = ""
    node_id: str = ""
    logical_message_id: str = ""
    raw_text: str = ""
    created_at: str = field(default_factory=_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def serialize(self) -> dict[str, Any]:
        """JSON-safe dict for JSONL storage."""
        return asdict(self)

    @classmethod
    def deserialize(cls, data: dict[str, Any]) -> "ArchivedInteraction":
        """Reconstruct from a serialized dict."""
        return cls(
            archive_id=data.get("archive_id", _new_archive_id()),
            parent_archive_id=data.get("parent_archive_id"),
            correlation_id=data.get("correlation_id", ""),
            direction=data.get("direction", Direction.INBOUND.value),
            interface=data.get("interface", Interface.DISCORD.value),
            source_session=data.get("source_session", ""),
            role=data.get("role", ""),
            node_id=data.get("node_id", ""),
            logical_message_id=data.get("logical_message_id", ""),
            raw_text=data.get("raw_text", ""),
            created_at=data.get("created_at", _now_iso()),
            metadata=data.get("metadata", {}),
        )


# ─── Archive Store ───────────────────────────────────────────────────────────


class InteractionArchive:
    """Append-only JSONL store for verbatim interactions.

    Thread-safe.  Records are never modified after creation.
    Query helpers provide bounded retrieval by various dimensions.
    """

    def __init__(self, path: str = _DEFAULT_ARCHIVE_PATH) -> None:
        self._path = path
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(self._path), exist_ok=True)

    @property
    def path(self) -> str:
        return self._path

    # ─── Write ────────────────────────────────────────────────────────────

    def archive(self, interaction: ArchivedInteraction) -> str:
        """Append a verbatim interaction to the archive.

        Returns the archive_id. Best-effort: failures are logged, never raised.
        Truncates raw_text to _MAX_TEXT_LENGTH as a safety bound.
        """
        if len(interaction.raw_text) > _MAX_TEXT_LENGTH:
            interaction.raw_text = interaction.raw_text[:_MAX_TEXT_LENGTH]
            interaction.metadata["truncated"] = True

        with self._lock:
            try:
                with open(self._path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(interaction.serialize()) + "\n")
            except Exception as exc:
                _log(f"archive failed: {exc}")

        return interaction.archive_id

    # ─── Read helpers ─────────────────────────────────────────────────────

    def _read_all(self) -> list[dict[str, Any]]:
        """Read all records from disk. Must hold self._lock."""
        items: list[dict[str, Any]] = []
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            items.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass
        except FileNotFoundError:
            pass
        return items

    def recent(
        self,
        limit: int = 50,
        *,
        direction: Optional[str] = None,
        interface: Optional[str] = None,
    ) -> list[ArchivedInteraction]:
        """Retrieve the most recent N archived interactions.

        Optional filters narrow by direction and/or interface.
        Returns newest-last ordering.
        """
        with self._lock:
            items = self._read_all()

        # Apply filters
        if direction:
            items = [i for i in items if i.get("direction") == direction]
        if interface:
            items = [i for i in items if i.get("interface") == interface]

        # Take last N
        results: list[ArchivedInteraction] = []
        for item in items[-limit:]:
            try:
                results.append(ArchivedInteraction.deserialize(item))
            except Exception:
                pass
        return results

    def by_correlation_id(
        self, correlation_id: str, *, limit: int = 100
    ) -> list[ArchivedInteraction]:
        """Retrieve all interactions sharing a correlation ID.

        Returns them in chronological order (oldest first).
        """
        with self._lock:
            items = self._read_all()

        results: list[ArchivedInteraction] = []
        for item in items:
            if item.get("correlation_id") == correlation_id:
                try:
                    results.append(ArchivedInteraction.deserialize(item))
                except Exception:
                    pass
                if len(results) >= limit:
                    break
        return results

    def by_session_or_role(
        self,
        *,
        session: Optional[str] = None,
        role: Optional[str] = None,
        limit: int = 50,
    ) -> list[ArchivedInteraction]:
        """Retrieve interactions by session name and/or role.

        At least one filter must be provided. Returns newest-last.
        """
        if not session and not role:
            return []

        with self._lock:
            items = self._read_all()

        filtered: list[dict[str, Any]] = []
        for item in items:
            match = True
            if session and item.get("source_session") != session:
                match = False
            if role and item.get("role") != role:
                match = False
            if match:
                filtered.append(item)

        results: list[ArchivedInteraction] = []
        for item in filtered[-limit:]:
            try:
                results.append(ArchivedInteraction.deserialize(item))
            except Exception:
                pass
        return results

    def by_interface(
        self, interface: str, *, limit: int = 50
    ) -> list[ArchivedInteraction]:
        """Retrieve interactions from a specific interface.

        Returns newest-last. Used for cross-device continuity queries.
        """
        with self._lock:
            items = self._read_all()

        filtered = [i for i in items if i.get("interface") == interface]

        results: list[ArchivedInteraction] = []
        for item in filtered[-limit:]:
            try:
                results.append(ArchivedInteraction.deserialize(item))
            except Exception:
                pass
        return results

    def by_time_window(
        self,
        start_iso: str,
        end_iso: Optional[str] = None,
        *,
        limit: int = 200,
    ) -> list[ArchivedInteraction]:
        """Retrieve interactions within an ISO time window.

        If end_iso is None, retrieves from start_iso to now.
        Returns chronological order.
        """
        end = end_iso or _now_iso()

        with self._lock:
            items = self._read_all()

        results: list[ArchivedInteraction] = []
        for item in items:
            created = item.get("created_at", "")
            if created >= start_iso and created <= end:
                try:
                    results.append(ArchivedInteraction.deserialize(item))
                except Exception:
                    pass
                if len(results) >= limit:
                    break
        return results

    def count(self) -> int:
        """Return total number of archived interactions."""
        with self._lock:
            items = self._read_all()
        return len(items)

    def summary(self) -> dict[str, Any]:
        """Return a lightweight summary for continuity consumers.

        Does NOT include raw text — only counts and metadata.
        """
        with self._lock:
            items = self._read_all()

        if not items:
            return {
                "total": 0,
                "inbound": 0,
                "outbound": 0,
                "interfaces": [],
                "earliest": None,
                "latest": None,
            }

        inbound = sum(1 for i in items if i.get("direction") == "inbound")
        outbound = sum(1 for i in items if i.get("direction") == "outbound")
        interfaces = sorted({i.get("interface", "") for i in items})

        return {
            "total": len(items),
            "inbound": inbound,
            "outbound": outbound,
            "interfaces": interfaces,
            "earliest": items[0].get("created_at"),
            "latest": items[-1].get("created_at"),
        }


# ─── Factory helpers ─────────────────────────────────────────────────────────


def archive_inbound(
    raw_text: str,
    *,
    interface: str = Interface.DISCORD.value,
    source_session: str = "",
    role: str = "",
    node_id: str = "",
    correlation_id: str = "",
    logical_message_id: str = "",
    parent_archive_id: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> str:
    """Archive a verbatim inbound (user→system) message.

    Convenience wrapper. Returns the archive_id.
    """
    interaction = ArchivedInteraction(
        correlation_id=correlation_id,
        direction=Direction.INBOUND.value,
        interface=interface,
        source_session=source_session,
        role=role,
        node_id=node_id,
        logical_message_id=logical_message_id,
        raw_text=raw_text,
        parent_archive_id=parent_archive_id,
        metadata=metadata or {},
    )
    return get_interaction_archive().archive(interaction)


def archive_outbound(
    raw_text: str,
    *,
    interface: str = Interface.DISCORD.value,
    source_session: str = "",
    role: str = "",
    node_id: str = "",
    correlation_id: str = "",
    logical_message_id: str = "",
    parent_archive_id: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> str:
    """Archive a verbatim outbound (system→user) reply.

    Must be called BEFORE transport chunking. Returns the archive_id.
    """
    interaction = ArchivedInteraction(
        correlation_id=correlation_id,
        direction=Direction.OUTBOUND.value,
        interface=interface,
        source_session=source_session,
        role=role,
        node_id=node_id,
        logical_message_id=logical_message_id,
        raw_text=raw_text,
        parent_archive_id=parent_archive_id,
        metadata=metadata or {},
    )
    return get_interaction_archive().archive(interaction)


# ─── /clear checkpoint ───────────────────────────────────────────────────────


def create_clear_checkpoint(
    *,
    session_name: str = "",
    role: str = "",
    node_id: str = "",
    interface: str = Interface.DISCORD.value,
    correlation_id: str = "",
    reason: str = "manual_clear",
    context_summary: str = "",
) -> dict[str, Any]:
    """Create a /clear checkpoint record and persist it to the archive.

    This captures enough state to resume continuity after a context reset.
    The checkpoint is stored as a special INBOUND interaction with
    direction=inbound and metadata.is_clear_checkpoint=True.

    Also emits a CLEAR_CHECKPOINT event to the event spine.

    Returns the checkpoint dict with archive_id and spine_event_id.
    """
    archive = get_interaction_archive()

    # Get recent interaction refs (last 10 archive_ids for cross-reference)
    recent = archive.recent(10)
    recent_refs = [r.archive_id for r in recent]
    latest_correlation = recent[-1].correlation_id if recent else ""

    checkpoint_metadata = {
        "is_clear_checkpoint": True,
        "reason": reason,
        "context_summary": context_summary,
        "recent_archive_refs": recent_refs,
        "latest_correlation_id": correlation_id or latest_correlation,
        "interaction_count_at_clear": archive.count(),
    }

    # Archive the checkpoint itself
    checkpoint = ArchivedInteraction(
        correlation_id=correlation_id or latest_correlation or _new_archive_id(),
        direction=Direction.INBOUND.value,
        interface=interface,
        source_session=session_name,
        role=role,
        node_id=node_id,
        logical_message_id="",
        raw_text=f"/clear — {reason}",
        metadata=checkpoint_metadata,
    )
    archive_id = archive.archive(checkpoint)

    # Emit to event spine (best-effort)
    spine_event_id = ""
    try:
        from umh.substrate.event_spine import EventType, create_event
        from umh.substrate.event_store import get_event_store

        # Use INBOUND_FINALIZED as the closest existing type
        # The payload distinguishes it as a clear checkpoint
        event = create_event(
            EventType.INBOUND_FINALIZED,
            source=interface,
            source_session=session_name,
            target="clear_checkpoint",
            role=role,
            payload={
                "type": "clear_checkpoint",
                "archive_id": archive_id,
                "reason": reason,
                "recent_refs": recent_refs,
                "interaction_count": checkpoint_metadata["interaction_count_at_clear"],
            },
            correlation_id=checkpoint.correlation_id,
        )
        get_event_store().append(event)
        spine_event_id = event.event_id
    except Exception as exc:
        _log(f"clear checkpoint spine event failed: {exc}")

    return {
        "archive_id": archive_id,
        "spine_event_id": spine_event_id,
        "correlation_id": checkpoint.correlation_id,
        "session_name": session_name,
        "role": role,
        "node_id": node_id,
        "interface": interface,
        "reason": reason,
        "recent_archive_refs": recent_refs,
        "interaction_count_at_clear": checkpoint_metadata["interaction_count_at_clear"],
        "created_at": checkpoint.created_at,
    }


# ─── Module-level singleton ─────────────────────────────────────────────────

_archive: Optional[InteractionArchive] = None
_archive_lock = threading.Lock()


def get_interaction_archive() -> InteractionArchive:
    """Get the module-level interaction archive singleton."""
    global _archive
    if _archive is None:
        with _archive_lock:
            if _archive is None:
                _archive = InteractionArchive()
    return _archive


# ─── Exports ─────────────────────────────────────────────────────────────────

__all__ = [
    "Direction",
    "Interface",
    "ArchivedInteraction",
    "InteractionArchive",
    "get_interaction_archive",
    "archive_inbound",
    "archive_outbound",
    "create_clear_checkpoint",
]
