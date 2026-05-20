"""Notion signal emitter — implements SignalEmitter Protocol."""

from __future__ import annotations

from services.umh.sockets.protocols import SignalDescriptor

from .manifest import INTEGRATION_ID, SIGNAL_DESCRIPTORS


class NotionSignalEmitter:
    """Declares what signal types the Notion integration can emit.

    Phase 1: declaration only — no polling or active emission.
    """

    @property
    def integration_id(self) -> str:
        return INTEGRATION_ID

    def describe_signals(self) -> list[SignalDescriptor]:
        return list(SIGNAL_DESCRIPTORS)
