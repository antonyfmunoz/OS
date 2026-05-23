"""Node mesh signal emitter — declares signal types a remote node can emit."""

from __future__ import annotations

from substrate.governance.risk_classes import RiskClass
from substrate.types import SignalUrgency
from substrate.sockets.protocols import SignalDescriptor


class NodeSignalEmitter:
    """Proxy SignalEmitter for a remote mesh node.

    Satisfies the SignalEmitter protocol structurally. The actual signal
    push happens when the server receives signal.emit over WebSocket and
    calls SignalSocket.emit() directly.
    """

    def __init__(self, node_id: str) -> None:
        self._node_id = node_id

    @property
    def integration_id(self) -> str:
        return f"node-{self._node_id}"

    def describe_signals(self) -> list[SignalDescriptor]:
        return [
            SignalDescriptor(
                "node.system.metrics",
                "System telemetry (CPU, memory, disk, battery)",
                default_urgency=SignalUrgency.LOW,
                default_risk_class=RiskClass.READ_ONLY,
            ),
            SignalDescriptor(
                "node.workspace.window_change",
                "Active window changed",
                default_urgency=SignalUrgency.LOW,
                default_risk_class=RiskClass.READ_ONLY,
            ),
            SignalDescriptor(
                "node.filesystem.change",
                "File created, modified, or deleted",
                default_urgency=SignalUrgency.NORMAL,
                default_risk_class=RiskClass.READ_ONLY,
            ),
            SignalDescriptor(
                "node.connected",
                "Node came online",
                default_urgency=SignalUrgency.NORMAL,
                default_risk_class=RiskClass.READ_ONLY,
            ),
            SignalDescriptor(
                "node.disconnected",
                "Node went offline",
                default_urgency=SignalUrgency.HIGH,
                default_risk_class=RiskClass.READ_ONLY,
            ),
        ]
