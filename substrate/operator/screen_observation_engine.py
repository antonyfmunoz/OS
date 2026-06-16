"""UMH Screen Observation Engine — node-role-aware screen context aggregation.

Phase 33. Manages three providers (Inferred, Observed, Reported) and
implements preference ordering: fresh OBSERVED > fresh REPORTED > INFERRED.
A stale OBSERVED does NOT beat a fresh INFERRED.

Composes:
  - WorkspaceObservationEngine (terminals, sessions, repos)
  - WorkspaceTopologyEngine (workspace→repo mapping)
  - ContinuityEngine (device context)
  - UMHNodeRegistry (node roles)

UMH substrate subsystem. Instance-agnostic.
"""
from __future__ import annotations

import logging
import socket
import time
from collections import deque
from typing import Any

from substrate.operator.screen_awareness import (
    ActiveWindow,
    BrowserContext,
    FileContext,
    FocusedApplication,
    RepositoryContext,
    ScreenContextStatus,
    ScreenSnapshot,
    ScreenSourceType,
)
from substrate.operator.screen_context_providers import (
    InferredScreenContextProvider,
    ObservedScreenContextProvider,
    ReportedScreenContextProvider,
    ScreenContextProvider,
)

logger = logging.getLogger(__name__)

_SOURCE_PRIORITY = {
    ScreenSourceType.OBSERVED: 0,
    ScreenSourceType.REPORTED: 1,
    ScreenSourceType.INFERRED: 2,
}

_STATUS_PRIORITY = {
    ScreenContextStatus.ACTIVE: 0,
    ScreenContextStatus.STALE: 1,
    ScreenContextStatus.UNKNOWN: 2,
}

_ROLE_TO_EXPECTED_SOURCE = {
    "workstation": ScreenSourceType.OBSERVED,
    "builder": ScreenSourceType.OBSERVED,
    "orchestrator": ScreenSourceType.INFERRED,
    "control_plane": ScreenSourceType.INFERRED,
    "controller": ScreenSourceType.REPORTED,
    "observer": ScreenSourceType.INFERRED,
    "fallback": ScreenSourceType.INFERRED,
}


class ScreenObservationEngine:
    """Aggregation façade for node-role-aware screen awareness."""

    def __init__(
        self,
        workspace_engine: Any = None,
        topology_engine: Any = None,
        continuity_engine: Any = None,
        node_registry: Any = None,
    ) -> None:
        self._workspace_engine = workspace_engine
        self._topology_engine = topology_engine
        self._continuity_engine = continuity_engine
        self._node_registry = node_registry

        node_id, device_id = self._detect_current_node()

        self._inferred_provider = InferredScreenContextProvider(
            workspace_engine=workspace_engine,
            topology_engine=topology_engine,
            continuity_engine=continuity_engine,
            node_id=node_id,
            device_id=device_id,
        )
        self._observed_provider = ObservedScreenContextProvider()
        self._reported_provider = ReportedScreenContextProvider()

        self._history: deque[ScreenSnapshot] = deque(maxlen=100)

    @property
    def workspace_engine(self) -> Any:
        if self._workspace_engine is None:
            try:
                from substrate.meta_ide.workspace_observation import WorkspaceObservationEngine
                self._workspace_engine = WorkspaceObservationEngine()
            except Exception:
                logger.debug("WorkspaceObservationEngine unavailable")
        return self._workspace_engine

    @property
    def topology_engine(self) -> Any:
        if self._topology_engine is None:
            try:
                from substrate.meta_ide.workspace_topology_engine import WorkspaceTopologyEngine
                self._topology_engine = WorkspaceTopologyEngine()
            except Exception:
                logger.debug("WorkspaceTopologyEngine unavailable")
        return self._topology_engine

    @property
    def continuity_engine(self) -> Any:
        if self._continuity_engine is None:
            try:
                from substrate.operator.continuity_engine import ContinuityEngine
                self._continuity_engine = ContinuityEngine()
            except Exception:
                logger.debug("ContinuityEngine unavailable")
        return self._continuity_engine

    @property
    def node_registry(self) -> Any:
        if self._node_registry is None:
            try:
                from substrate.organism.umh_node_registry import UMHNodeRegistry
                self._node_registry = UMHNodeRegistry()
            except Exception:
                logger.debug("UMHNodeRegistry unavailable")
        return self._node_registry

    def current_snapshot(self) -> ScreenSnapshot:
        """Return best-available screen context via preference ordering."""
        candidates: list[ScreenSnapshot] = []

        for provider in [self._observed_provider, self._reported_provider, self._inferred_provider]:
            if provider.is_available():
                try:
                    snap = provider.current_snapshot()
                    if snap.status != ScreenContextStatus.UNKNOWN:
                        candidates.append(snap)
                except Exception:
                    logger.debug("Provider %s failed", provider.provider_id)

        if not candidates:
            try:
                snap = self._inferred_provider.current_snapshot()
                candidates.append(snap)
            except Exception:
                pass

        if not candidates:
            return ScreenSnapshot(
                source_type=ScreenSourceType.INFERRED,
                status=ScreenContextStatus.UNKNOWN,
                source_confidence=0.0,
            )

        best = self._pick_best(candidates)
        self._history.appendleft(best)
        return best

    def active_application(self) -> FocusedApplication | None:
        snap = self.current_snapshot()
        return snap.active_application

    def active_window(self) -> ActiveWindow | None:
        snap = self.current_snapshot()
        return snap.active_window

    def active_repository(self) -> RepositoryContext | None:
        snap = self.current_snapshot()
        return snap.repository_context

    def active_file(self) -> FileContext | None:
        snap = self.current_snapshot()
        return snap.file_context

    def active_browser(self) -> BrowserContext | None:
        snap = self.current_snapshot()
        return snap.browser_context

    def report_observed(self, snapshot: ScreenSnapshot) -> None:
        """Accept OBSERVED context from Beast/workstation node."""
        self._observed_provider.report_observed(snapshot)

    def report_context(self, snapshot: ScreenSnapshot) -> None:
        """Accept REPORTED context from controller device."""
        self._reported_provider.report_context(snapshot)

    def history(self, limit: int = 20) -> list[ScreenSnapshot]:
        return list(self._history)[:limit]

    def expected_provider_for_node(self, node_id: str) -> str:
        """Return expected source type for a node based on its role."""
        registry = self.node_registry
        if registry is None:
            return ScreenSourceType.INFERRED.value

        node = registry.get_node(node_id)
        if node is None:
            return ScreenSourceType.INFERRED.value

        roles = getattr(node, "roles", [])
        for role in roles:
            expected = _ROLE_TO_EXPECTED_SOURCE.get(role)
            if expected and expected != ScreenSourceType.INFERRED:
                return expected.value

        return ScreenSourceType.INFERRED.value

    def provider_status(self) -> dict[str, Any]:
        """Status of all three providers."""
        return {
            "inferred": {
                "available": self._inferred_provider.is_available(),
                "source_type": self._inferred_provider.source_type.value,
                "node_id": self._inferred_provider.node_id,
                "device_id": self._inferred_provider.device_id,
                "confidence": InferredScreenContextProvider.CONFIDENCE,
            },
            "observed": {
                "available": self._observed_provider.is_available(),
                "source_type": self._observed_provider.source_type.value,
                "node_id": self._observed_provider.node_id,
                "device_id": self._observed_provider.device_id,
                "confidence": ObservedScreenContextProvider.CONFIDENCE,
                "last_update": self._observed_provider._observed_at,
            },
            "reported": {
                "available": self._reported_provider.is_available(),
                "source_type": self._reported_provider.source_type.value,
                "node_id": self._reported_provider.node_id,
                "device_id": self._reported_provider.device_id,
                "confidence": ReportedScreenContextProvider.CONFIDENCE,
                "last_update": self._reported_provider._reported_at,
            },
        }

    def _pick_best(self, candidates: list[ScreenSnapshot]) -> ScreenSnapshot:
        """Pick best candidate: fresh OBSERVED > fresh REPORTED > INFERRED.

        Stale OBSERVED does NOT beat fresh INFERRED.
        Sort key: (status_priority, source_priority) — ACTIVE beats STALE
        regardless of source type.
        """
        if not candidates:
            return ScreenSnapshot()

        if len(candidates) == 1:
            return candidates[0]

        def sort_key(snap: ScreenSnapshot) -> tuple[int, int]:
            status_pri = _STATUS_PRIORITY.get(snap.status, 2)
            source_pri = _SOURCE_PRIORITY.get(snap.source_type, 2)
            return (status_pri, source_pri)

        candidates.sort(key=sort_key)
        return candidates[0]

    def _detect_current_node(self) -> tuple[str, str]:
        """Detect current node_id and device_id from registry or hostname."""
        registry = self.node_registry
        if registry is not None:
            primary = registry.primary_node()
            if primary:
                return primary.node_id, primary.device_id

        hostname = socket.gethostname()
        return f"umh-{hostname}", hostname
