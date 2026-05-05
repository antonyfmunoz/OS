"""Surface registry — tracks I/O endpoints attached to sessions.

A surface is a user-facing interface (Discord channel, voice loop,
workstation GUI) bound to a session_id. Multiple surfaces can attach
to one session simultaneously.

Design rules:
- In-memory only — no persistence yet
- Thread-safe via threading.Lock
- No substrate imports — this is runtime-layer
- No IO — pure state management
- Surfaces are observers, not owners — session is the center
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, replace
from typing import Any


@dataclass(frozen=True)
class SurfaceRecord:
    """Immutable snapshot of an attached surface."""

    surface_id: str
    session_id: str
    surface_type: str
    transport: str
    config: dict[str, Any]
    attached_ts: float
    last_activity_ts: float

    def with_updates(self, **kwargs: Any) -> SurfaceRecord:
        return replace(self, **kwargs)


_VALID_SURFACE_TYPES = frozenset({"discord", "voice", "workstation"})
_VALID_TRANSPORTS = frozenset({"webhook", "local_audio", "gui"})


class SurfaceRegistry:
    """In-memory registry of surfaces attached to sessions.

    Thread-safe. Singleton access via get_surface_registry().
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._surfaces: dict[str, SurfaceRecord] = {}
        self._session_index: dict[str, list[str]] = {}

    def attach_surface(
        self,
        session_id: str,
        surface_type: str,
        transport: str,
        config: dict[str, Any] | None = None,
        surface_id: str | None = None,
    ) -> SurfaceRecord:
        """Attach a surface to a session.

        Idempotent: if a surface with the same session_id + surface_type
        already exists, returns the existing record with updated activity.
        """
        with self._lock:
            existing_ids = self._session_index.get(session_id, [])
            for sid in existing_ids:
                rec = self._surfaces.get(sid)
                if rec and rec.surface_type == surface_type:
                    updated = rec.with_updates(
                        last_activity_ts=time.time(),
                        config=config if config is not None else rec.config,
                    )
                    self._surfaces[sid] = updated
                    return updated

            now = time.time()
            sf_id = surface_id or f"srf_{uuid.uuid4().hex[:12]}"
            record = SurfaceRecord(
                surface_id=sf_id,
                session_id=session_id,
                surface_type=surface_type,
                transport=transport,
                config=config or {},
                attached_ts=now,
                last_activity_ts=now,
            )
            self._surfaces[sf_id] = record
            self._session_index.setdefault(session_id, []).append(sf_id)
            return record

    def detach_surface(self, surface_id: str) -> SurfaceRecord | None:
        """Detach a surface. Returns the detached record or None."""
        with self._lock:
            rec = self._surfaces.pop(surface_id, None)
            if rec:
                ids = self._session_index.get(rec.session_id, [])
                if surface_id in ids:
                    ids.remove(surface_id)
                    if not ids:
                        self._session_index.pop(rec.session_id, None)
            return rec

    def get_surfaces(self, session_id: str) -> list[SurfaceRecord]:
        """Get all surfaces attached to a session."""
        with self._lock:
            ids = self._session_index.get(session_id, [])
            return [self._surfaces[sid] for sid in ids if sid in self._surfaces]

    def get_primary_surface(self, session_id: str) -> SurfaceRecord | None:
        """Get the primary (first-attached) surface for a session."""
        surfaces = self.get_surfaces(session_id)
        return surfaces[0] if surfaces else None

    def get_surface(self, surface_id: str) -> SurfaceRecord | None:
        with self._lock:
            return self._surfaces.get(surface_id)

    def update_activity(self, surface_id: str) -> SurfaceRecord | None:
        with self._lock:
            rec = self._surfaces.get(surface_id)
            if not rec:
                return None
            updated = rec.with_updates(last_activity_ts=time.time())
            self._surfaces[surface_id] = updated
            return updated

    def detach_all(self, session_id: str) -> list[SurfaceRecord]:
        """Detach all surfaces from a session. Returns detached records."""
        with self._lock:
            ids = self._session_index.pop(session_id, [])
            detached = []
            for sid in ids:
                rec = self._surfaces.pop(sid, None)
                if rec:
                    detached.append(rec)
            return detached

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "surface_count": len(self._surfaces),
                "session_count": len(self._session_index),
                "by_session": {
                    ses_id: [
                        {
                            "surface_id": self._surfaces[sid].surface_id,
                            "surface_type": self._surfaces[sid].surface_type,
                            "transport": self._surfaces[sid].transport,
                        }
                        for sid in sids
                        if sid in self._surfaces
                    ]
                    for ses_id, sids in self._session_index.items()
                },
            }


_SINGLETON: SurfaceRegistry | None = None
_SINGLETON_LOCK = threading.Lock()


def get_surface_registry() -> SurfaceRegistry:
    """Return the process-wide surface registry singleton."""
    global _SINGLETON
    if _SINGLETON is None:
        with _SINGLETON_LOCK:
            if _SINGLETON is None:
                _SINGLETON = SurfaceRegistry()
    return _SINGLETON
