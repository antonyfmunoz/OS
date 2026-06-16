"""Operator Context Engine — aggregation façade for operator home.

Composes all existing UMH subsystem outputs into a single operator
view. This is NOT a new subsystem — it creates no new authority,
no new state, no new execution paths. It consumes existing sources
of truth and produces OperatorSnapshot.

Aggregation façades are allowed to compose peer substrate systems.
Cross-substrate composition (operator/ importing meta_ide/, organism/)
is the correct architectural move here because the entire purpose of
this engine is to aggregate existing authoritative systems.

Phase 31. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from substrate.operator.operator_context import (
    OperatorAttentionItem,
    OperatorAttentionType,
    OperatorHealthSummary,
    OperatorSeverity,
    OperatorSnapshot,
    OperatorStatusCard,
    OperatorTimelineEvent,
)

logger = logging.getLogger(__name__)

_SEVERITY_ORDER = {
    OperatorSeverity.CRITICAL: 0,
    OperatorSeverity.WARNING: 1,
    OperatorSeverity.INFO: 2,
}


class OperatorContextEngine:
    """Aggregation façade composing 6+ subsystems into one operator view."""

    def __init__(
        self,
        event_spine: Any = None,
        service_failure_engine: Any = None,
        state_coherence_engine: Any = None,
        node_registry: Any = None,
        approval_store: Any = None,
        workspace_engine: Any = None,
    ) -> None:
        self._event_spine = event_spine
        self._service_failure_engine = service_failure_engine
        self._state_coherence_engine = state_coherence_engine
        self._node_registry = node_registry
        self._approval_store = approval_store
        self._workspace_engine = workspace_engine

    # ── Lazy properties ──────────────────────────────────────────

    @property
    def event_spine(self) -> Any:
        if self._event_spine is None:
            try:
                from substrate.organism.event_spine import EventSpine

                self._event_spine = EventSpine()
            except Exception:
                logger.debug("EventSpine unavailable")
        return self._event_spine

    @property
    def service_failure_engine(self) -> Any:
        if self._service_failure_engine is None:
            try:
                from substrate.organism.service_failure_engine import (
                    ServiceFailureEngine,
                )

                self._service_failure_engine = ServiceFailureEngine()
            except Exception:
                logger.debug("ServiceFailureEngine unavailable")
        return self._service_failure_engine

    @property
    def state_coherence_engine(self) -> Any:
        if self._state_coherence_engine is None:
            try:
                from substrate.organism.state_coherence_engine import (
                    StateCoherenceEngine,
                )

                self._state_coherence_engine = StateCoherenceEngine()
            except Exception:
                logger.debug("StateCoherenceEngine unavailable")
        return self._state_coherence_engine

    @property
    def node_registry(self) -> Any:
        if self._node_registry is None:
            try:
                from substrate.organism.umh_node_registry import UMHNodeRegistry

                self._node_registry = UMHNodeRegistry()
            except Exception:
                logger.debug("UMHNodeRegistry unavailable")
        return self._node_registry

    @property
    def approval_store(self) -> Any:
        if self._approval_store is None:
            try:
                from substrate.organism.executors.approval_intercept import (
                    ApprovalInterceptStore,
                )

                self._approval_store = ApprovalInterceptStore()
            except Exception:
                logger.debug("ApprovalInterceptStore unavailable")
        return self._approval_store

    @property
    def workspace_engine(self) -> Any:
        if self._workspace_engine is None:
            try:
                from substrate.meta_ide.workspace_observation import (
                    WorkspaceObservationEngine,
                )

                self._workspace_engine = WorkspaceObservationEngine()
            except Exception:
                logger.debug("WorkspaceObservationEngine unavailable")
        return self._workspace_engine

    # ── Public API ───────────────────────────────────────────────

    def snapshot(self) -> OperatorSnapshot:
        """Full aggregated operator context."""
        now = time.time()
        health = self.health_summary()
        attention = self.attention_items()
        tl = self.timeline()
        approvals = self.pending_approvals()
        alerts = self.service_alerts()
        nodes = self.node_status()
        workspaces = self.active_workspaces()

        return OperatorSnapshot(
            health_summary=health,
            attention_items=attention,
            active_workspaces=workspaces,
            pending_approvals=approvals.get("count", 0),
            service_alerts=alerts,
            node_status=nodes,
            timeline=tl,
            generated_at=now,
        )

    def health_summary(self) -> OperatorHealthSummary:
        """Produce status cards across all subsystems."""
        cards: list[OperatorStatusCard] = []

        service_data = self._get_service_health()
        cards.append(OperatorStatusCard(
            label="Services",
            value=service_data.get("total_services", 0),
            status=self._service_status(service_data),
            detail=f"Critical: {service_data.get('critical_count', 0)}",
        ))

        state_data = self._get_state_health()
        cards.append(OperatorStatusCard(
            label="State Domains",
            value=state_data.get("total_domains", 0),
            status="healthy" if state_data.get("healthy") else "degraded",
            detail=f"Coherent: {state_data.get('coherent', 0)}",
        ))

        node_data = self._get_node_status()
        cards.append(OperatorStatusCard(
            label="Nodes",
            value=len(node_data),
            status="healthy" if node_data else "unknown",
            detail=f"{len(node_data)} registered",
        ))

        ws_data = self._get_workspace_snapshot()
        cards.append(OperatorStatusCard(
            label="Workspaces",
            value=len(ws_data),
            status="healthy" if ws_data is not None else "unknown",
            detail=f"{len(ws_data)} observed" if ws_data else "No data",
        ))

        overall = self._compute_overall(cards)

        return OperatorHealthSummary(
            overall_status=overall,
            cards=cards,
        )

    def attention_items(self) -> list[OperatorAttentionItem]:
        """Priority-sorted list of things needing operator attention."""
        items: list[OperatorAttentionItem] = []

        items.extend(self._check_state_coherence())
        items.extend(self._check_service_health())
        items.extend(self._check_pending_approvals())
        items.extend(self._check_node_status())
        items.extend(self._check_critical_events())

        items.sort(key=lambda i: _SEVERITY_ORDER.get(i.severity, 99))
        return items

    def timeline(self, limit: int = 50) -> list[OperatorTimelineEvent]:
        """Recent events formatted for operator consumption."""
        return self._get_timeline(limit)

    def pending_approvals(self) -> dict[str, Any]:
        """Pending governance approvals."""
        return self._get_pending_approvals()

    def service_alerts(self) -> list[dict[str, Any]]:
        """Services with high blast radius or critical status."""
        alerts: list[dict[str, Any]] = []
        engine = self.service_failure_engine
        if engine is None:
            return alerts

        try:
            path = engine.critical_path()
            for entry in path:
                if entry.get("blast_radius", 0) > 0:
                    alerts.append({
                        "service": entry["service_role"],
                        "blast_radius": entry["blast_radius"],
                        "criticality": entry.get("criticality", "unknown"),
                    })
        except Exception:
            logger.debug("Failed to get service alerts", exc_info=True)

        return alerts

    def node_status(self) -> list[dict[str, Any]]:
        """Current node information."""
        return self._get_node_status()

    def active_workspaces(self) -> list[dict[str, Any]]:
        """Current workspace observation data."""
        data = self._get_workspace_snapshot()
        return data if data is not None else []

    # ── Provider methods (composition boundary) ──────────────────

    def _get_service_health(self) -> dict[str, Any]:
        engine = self.service_failure_engine
        if engine is None:
            return {}
        try:
            return engine.organism_health()
        except Exception:
            logger.debug("Failed to get service health", exc_info=True)
            return {}

    def _get_state_health(self) -> dict[str, Any]:
        engine = self.state_coherence_engine
        if engine is None:
            return {}
        try:
            return engine.organism_health()
        except Exception:
            logger.debug("Failed to get state health", exc_info=True)
            return {}

    def _get_node_status(self) -> list[dict[str, Any]]:
        registry = self.node_registry
        if registry is None:
            return []
        try:
            nodes = registry.list_nodes()
            return [n.to_dict() for n in nodes]
        except Exception:
            logger.debug("Failed to get node status", exc_info=True)
            return []

    def _get_workspace_snapshot(self) -> list[dict[str, Any]] | None:
        engine = self.workspace_engine
        if engine is None:
            return None
        try:
            snap = engine.latest()
            if snap is None:
                return []
            return [snap.to_dict()]
        except Exception:
            logger.debug("Failed to get workspace snapshot", exc_info=True)
            return None

    def _get_pending_approvals(self) -> dict[str, Any]:
        store = self.approval_store
        if store is None:
            return {"count": 0, "items": []}
        try:
            pending = store.list_pending()
            return {
                "count": len(pending),
                "items": [p.to_dict() for p in pending],
            }
        except Exception:
            logger.debug("Failed to get pending approvals", exc_info=True)
            return {"count": 0, "items": []}

    def _get_timeline(self, limit: int = 50) -> list[OperatorTimelineEvent]:
        spine = self.event_spine
        if spine is None:
            return []
        try:
            events = spine.recent(limit=limit)
            return [
                OperatorTimelineEvent(
                    event_id=e.event_id,
                    domain=e.domain.value if hasattr(e.domain, "value") else str(e.domain),
                    event_type=e.event_type,
                    source=e.source,
                    summary=f"{e.event_type} from {e.source}",
                    timestamp=e.timestamp,
                    priority=e.priority.value if hasattr(e.priority, "value") else str(e.priority),
                )
                for e in events
            ]
        except Exception:
            logger.debug("Failed to get timeline", exc_info=True)
            return []

    # ── Attention checkers (deterministic rules) ─────────────────

    def _check_state_coherence(self) -> list[OperatorAttentionItem]:
        items: list[OperatorAttentionItem] = []
        engine = self.state_coherence_engine
        if engine is None:
            return items

        try:
            report = engine.coherence_report()
            for domain in report.get("domains", []):
                status = domain.get("status", "unknown")
                if status in ("drifted", "stale"):
                    items.append(OperatorAttentionItem(
                        attention_type=OperatorAttentionType.STATE,
                        severity=OperatorSeverity.CRITICAL,
                        title=f"State domain '{domain.get('domain', '?')}' is {status}",
                        detail=f"Owner: {domain.get('service_owner', 'unknown')}",
                        source="state_coherence_engine",
                    ))
        except Exception:
            logger.debug("State coherence check failed", exc_info=True)

        return items

    def _check_service_health(self) -> list[OperatorAttentionItem]:
        items: list[OperatorAttentionItem] = []
        engine = self.service_failure_engine
        if engine is None:
            return items

        try:
            path = engine.critical_path()
            for entry in path:
                br = entry.get("blast_radius", 0)
                if br > 3:
                    items.append(OperatorAttentionItem(
                        attention_type=OperatorAttentionType.SERVICE,
                        severity=OperatorSeverity.WARNING,
                        title=f"Service '{entry['service_role']}' has blast_radius={br}",
                        detail=f"Criticality: {entry.get('criticality', 'unknown')}",
                        source="service_failure_engine",
                    ))
        except Exception:
            logger.debug("Service health check failed", exc_info=True)

        return items

    def _check_pending_approvals(self) -> list[OperatorAttentionItem]:
        items: list[OperatorAttentionItem] = []
        data = self._get_pending_approvals()
        count = data.get("count", 0)

        if count > 0:
            items.append(OperatorAttentionItem(
                attention_type=OperatorAttentionType.GOVERNANCE,
                severity=OperatorSeverity.WARNING,
                title=f"{count} pending approval(s)",
                detail="Governance decisions awaiting operator input",
                source="approval_intercept_store",
            ))

        return items

    def _check_node_status(self) -> list[OperatorAttentionItem]:
        items: list[OperatorAttentionItem] = []
        engine = self.state_coherence_engine
        if engine is None:
            return items

        try:
            version_engine = engine._get_version_engine()
            if version_engine is not None:
                report = version_engine.coherence_report()
                if not report.get("coherent", True):
                    drift_items = report.get("drift_items", [])
                    items.append(OperatorAttentionItem(
                        attention_type=OperatorAttentionType.RUNTIME,
                        severity=OperatorSeverity.WARNING,
                        title="Node version drift detected",
                        detail=f"{len(drift_items)} drift item(s)",
                        source="version_coherence_engine",
                    ))
        except Exception:
            logger.debug("Node status check failed", exc_info=True)

        return items

    def _check_critical_events(self) -> list[OperatorAttentionItem]:
        items: list[OperatorAttentionItem] = []
        spine = self.event_spine
        if spine is None:
            return items

        try:
            recent = spine.recent(limit=20)
            for event in recent:
                priority = event.priority.value if hasattr(event.priority, "value") else str(event.priority)
                if priority == "critical":
                    items.append(OperatorAttentionItem(
                        attention_type=OperatorAttentionType.RUNTIME,
                        severity=OperatorSeverity.CRITICAL,
                        title=f"Critical event: {event.event_type}",
                        detail=f"Source: {event.source}",
                        source="event_spine",
                    ))
        except Exception:
            logger.debug("Critical events check failed", exc_info=True)

        return items

    # ── Helpers ──────────────────────────────────────────────────

    def _service_status(self, data: dict[str, Any]) -> str:
        if not data:
            return "unknown"
        risk = data.get("highest_risk_service", "")
        max_br = data.get("max_blast_radius", 0)
        if max_br > 5:
            return "critical"
        if max_br > 3:
            return "degraded"
        if risk:
            return "healthy"
        return "unknown"

    def _compute_overall(self, cards: list[OperatorStatusCard]) -> str:
        statuses = {c.status for c in cards}
        if "critical" in statuses:
            return "critical"
        if "degraded" in statuses:
            return "degraded"
        if statuses == {"healthy"}:
            return "healthy"
        if "healthy" in statuses:
            return "healthy"
        return "unknown"
