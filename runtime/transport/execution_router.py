"""
Data-driven execution router for the event-native execution fabric.

Stateless decision engine that accepts a RoutingContext and returns a
RoutingDecision. Consults the NodeRegistry for node health and capabilities.
NEVER invokes execution — only decides WHERE.

Usage:
    from runtime.transport.execution_router import ExecutionRouter
    from runtime.transport.execution_contract import (
        ExecutionClass, RoutingContext,
    )

    router = ExecutionRouter()
    decision = router.route(RoutingContext(
        execution_class=ExecutionClass.PURE,
        required_capabilities=frozenset({"reasoning"}),
    ))
    print(decision.target.node_id, decision.reason_code)
"""

from __future__ import annotations

from runtime.transport.execution_contract import (
    ExecutionClass,
    ExecutionTarget,
    RoutingContext,
    RoutingDecision,
    RoutingReasonCode,
)
from runtime.transport.nodes import (
    Node,
    NodeRegistry,
    NodeRole,
    NodeStatus,
)


class ExecutionRouter:
    """Routes execution requests to the best available node.

    Stateless decision engine. Re-reads registry state on each call.
    Returns immutable RoutingDecision with full rationale.

    Policy:
    - PURE: local (VPS/orchestrator) preferred unless capability requires workstation
    - SIDE_EFFECT: workstation preferred if capability exists and node is online
    - TRANSPORT: workstation preferred if required capability exists
    - Fallback to local only when context.allow_fallback is True
    - force_node_id overrides all other logic
    """

    def __init__(self, registry: NodeRegistry | None = None) -> None:
        self._registry = registry or NodeRegistry.default()

    def route(self, context: RoutingContext) -> RoutingDecision:
        """Route an execution request to the best available node.

        Args:
            context: Immutable routing parameters describing what is needed.

        Returns:
            RoutingDecision with target node, transport, and rationale.
        """
        # 1. Explicit override
        if context.force_node_id:
            node = self._registry.get(context.force_node_id)
            if node is not None and node.status == NodeStatus.ONLINE:
                return self._decision(
                    node,
                    context,
                    RoutingReasonCode.EXPLICIT_OVERRIDE,
                    f"forced to {node.node_id}",
                )

        # 2. Find capable nodes
        capable = self._capable_nodes(context.required_capabilities)

        # 3. Filter by health — ONLINE preferred, DEGRADED acceptable for PURE only
        online = [n for n in capable if n.status == NodeStatus.ONLINE]
        if context.execution_class == ExecutionClass.PURE:
            degraded = [n for n in capable if n.status == NodeStatus.DEGRADED]
            healthy = online or degraded
        else:
            healthy = online

        if not healthy:
            if context.allow_fallback:
                return self._local_fallback(
                    context,
                    "no healthy capable node found; falling back to local",
                )
            return self._no_route(
                context,
                "no healthy capable node found and fallback disabled",
            )

        # 4. Apply execution class policy
        if context.execution_class == ExecutionClass.PURE:
            preferred = self._prefer_role(healthy, NodeRole.ORCHESTRATOR)
            reason_code = RoutingReasonCode.EXECUTION_CLASS_POLICY
            detail = "PURE prefers orchestrator (low latency local)"
        elif context.execution_class == ExecutionClass.SIDE_EFFECT:
            preferred = self._prefer_role(healthy, NodeRole.WORKSTATION)
            reason_code = RoutingReasonCode.EXECUTION_CLASS_POLICY
            detail = "SIDE_EFFECT prefers workstation (local resources)"
        else:  # TRANSPORT
            preferred = self._prefer_role(healthy, NodeRole.WORKSTATION)
            reason_code = RoutingReasonCode.EXECUTION_CLASS_POLICY
            detail = "TRANSPORT prefers workstation (transport capabilities)"

        if preferred is None:
            # Should not happen since healthy is non-empty, but guard anyway
            if context.allow_fallback:
                return self._local_fallback(context, "no preferred node; fallback")
            return self._no_route(context, "no preferred node and fallback disabled")

        # Single capable node gets a more specific reason
        if len(healthy) == 1:
            reason_code = RoutingReasonCode.ONLY_CAPABLE_NODE
            detail = f"only capable node: {preferred.node_id}"

        return self._decision(preferred, context, reason_code, detail)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _capable_nodes(self, required: frozenset[str]) -> list[Node]:
        """Find nodes that have ALL required capabilities.

        If no capabilities are required, returns all non-OFFLINE nodes.
        """
        all_nodes = self._registry.all()
        if not required:
            return [n for n in all_nodes if n.status != NodeStatus.OFFLINE]

        result: list[Node] = []
        for node in all_nodes:
            if node.status == NodeStatus.OFFLINE:
                continue
            if all(node.has_capability(cap) for cap in required):
                result.append(node)
        return result

    def _prefer_role(self, nodes: list[Node], role: NodeRole) -> Node | None:
        """Return first node with given role, else first node in list."""
        if not nodes:
            return None
        for node in nodes:
            if node.role == role:
                return node
        return nodes[0]

    def _transport_for(self, node: Node) -> str:
        """Determine transport protocol for a node.

        ORCHESTRATOR uses direct (in-process), everything else uses http.
        """
        if node.role == NodeRole.ORCHESTRATOR:
            return "direct"
        return "http"

    def _decision(
        self,
        node: Node,
        context: RoutingContext,
        reason_code: RoutingReasonCode,
        detail: str,
    ) -> RoutingDecision:
        """Build a RoutingDecision with optional fallback info."""
        fallback_node_id: str | None = None
        fallback_transport: str | None = None

        # Set fallback for non-ORCHESTRATOR nodes when allowed
        if node.role != NodeRole.ORCHESTRATOR and context.allow_fallback:
            vps = self._registry.get("vps-primary")
            if vps is not None and vps.status == NodeStatus.ONLINE:
                fallback_node_id = "vps-primary"
                fallback_transport = "direct"

        target = ExecutionTarget(
            node_id=node.node_id,
            transport=self._transport_for(node),
            fallback_node_id=fallback_node_id,
            fallback_transport=fallback_transport,
        )
        return RoutingDecision(
            target=target,
            reason_code=reason_code,
            reason_detail=detail,
            routing_context=context,
        )

    def _local_fallback(self, context: RoutingContext, detail: str) -> RoutingDecision:
        """Build a vps-primary fallback decision."""
        target = ExecutionTarget(
            node_id="vps-primary",
            transport="direct",
        )
        return RoutingDecision(
            target=target,
            reason_code=RoutingReasonCode.FALLBACK_PRIMARY_UNAVAILABLE,
            reason_detail=detail,
            routing_context=context,
        )

    def _no_route(self, context: RoutingContext, detail: str) -> RoutingDecision:
        """Build an empty-target decision when no route is possible."""
        target = ExecutionTarget(
            node_id="",
            transport="",
        )
        return RoutingDecision(
            target=target,
            reason_code=RoutingReasonCode.FALLBACK_PRIMARY_UNAVAILABLE,
            reason_detail=detail,
            routing_context=context,
        )
