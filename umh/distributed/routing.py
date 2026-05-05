"""Phase 87A routing advisory — deterministic node selection for tasks.

Given a task description and constraints, recommends which node should
handle it. Pure function — no global state, no I/O, no side effects.

Three doctrines:
  - Distributed Runtime: UMH runs across multiple nodes
  - Node-Aware Routing: tasks declare required capabilities, route to safest valid node
  - Local Embodiment: sources needing local browser/accounts default to Local PC

No execution. No mutation. No adapter calls. No LLM calls.
No network listeners. No secrets.
"""

from __future__ import annotations

from typing import Any

from umh.distributed.capabilities import get_source_affinity, get_source_capabilities
from umh.distributed.contracts import (
    CapabilityDomain,
    NodeAvailability,
    RoutingDecision,
    RoutingPolicy,
    RoutingPriority,
    RuntimeNodeProfile,
    RuntimeNodeType,
    SourceAffinity,
    _dist_id,
)


def route_task_advisory(
    task_description: str,
    nodes: list[RuntimeNodeProfile],
    policy: RoutingPolicy | None = None,
    source_name: str | None = None,
) -> RoutingDecision:
    if not nodes:
        return RoutingDecision(
            decision_id=_dist_id("route"),
            task_description=task_description,
            reason="no nodes available",
            warnings=["no nodes registered"],
        )

    available = [
        n
        for n in nodes
        if n.availability
        in (
            NodeAvailability.ALWAYS_ON,
            NodeAvailability.ON_DEMAND,
            NodeAvailability.INTERMITTENT,
            NodeAvailability.SCHEDULED,
        )
    ]

    if not available:
        return RoutingDecision(
            decision_id=_dist_id("route"),
            task_description=task_description,
            reason="no available nodes (all future or unknown)",
            warnings=["all registered nodes have future or unknown availability"],
        )

    required_caps: set[CapabilityDomain] = set()
    affinity = SourceAffinity.ANY_NODE

    if source_name:
        required_caps = set(get_source_capabilities(source_name))
        affinity = get_source_affinity(source_name)

    if policy:
        required_caps.update(policy.required_capabilities)
        if policy.source_affinity != SourceAffinity.ANY_NODE:
            affinity = policy.source_affinity
        if policy.requires_gpu:
            required_caps.add(CapabilityDomain.GPU)
        if policy.requires_browser:
            required_caps.add(CapabilityDomain.BROWSER)
        if policy.requires_local_accounts:
            required_caps.add(CapabilityDomain.LOCAL_ACCOUNTS)
        if policy.requires_display:
            required_caps.add(CapabilityDomain.DISPLAY)

    if not required_caps:
        required_caps = _infer_capabilities_from_description(task_description)
        if not affinity or affinity == SourceAffinity.ANY_NODE:
            affinity = _infer_affinity_from_description(task_description)

    candidates = _filter_by_capabilities(available, required_caps)
    candidates = _filter_by_affinity(candidates, affinity)

    if not candidates:
        candidates = _filter_by_capabilities(available, required_caps)

    if not candidates:
        candidates = available

    if policy and policy.preferred_node_types:
        preferred = [n for n in candidates if n.node_type in policy.preferred_node_types]
        if preferred:
            candidates = preferred

    selected = _rank_candidates(candidates, affinity, policy)

    alternatives = [n.name for n in candidates if n.node_id != selected.node_id][:3]
    warnings: list[str] = []

    if selected.availability == NodeAvailability.INTERMITTENT:
        warnings.append(f"{selected.name} has intermittent availability")

    if affinity == SourceAffinity.LOCAL_ONLY and selected.node_type != RuntimeNodeType.LOCAL_PC:
        warnings.append(f"source requires local-only but routed to {selected.node_type.value}")

    if affinity == SourceAffinity.GPU_REQUIRED and not selected.gpu:
        warnings.append("source requires GPU but selected node has no GPU")

    confidence = _calculate_confidence(selected, required_caps, affinity)

    return RoutingDecision(
        decision_id=_dist_id("route"),
        task_description=task_description,
        selected_node_id=selected.node_id,
        selected_node_type=selected.node_type,
        policy_id=policy.policy_id if policy else "",
        reason=_build_reason(selected, affinity, required_caps),
        alternatives=alternatives,
        warnings=warnings,
        confidence=confidence,
        metadata={
            "source_name": source_name or "",
            "affinity": affinity.value,
            "required_capabilities": [c.value for c in required_caps],
        },
    )


def build_default_routing_policies() -> list[RoutingPolicy]:
    return [
        RoutingPolicy(
            policy_id=_dist_id("policy"),
            name="Local Embodiment",
            description="Tasks requiring browser, local accounts, or display route to Local PC",
            priority=RoutingPriority.PRIVACY,
            source_affinity=SourceAffinity.LOCAL_ONLY,
            required_capabilities=[
                CapabilityDomain.BROWSER,
                CapabilityDomain.LOCAL_ACCOUNTS,
            ],
            preferred_node_types=[RuntimeNodeType.LOCAL_PC],
            requires_browser=True,
            requires_local_accounts=True,
        ),
        RoutingPolicy(
            policy_id=_dist_id("policy"),
            name="VPS Always-On Services",
            description="Long-running services, Docker containers, and cron jobs route to VPS",
            priority=RoutingPriority.RELIABILITY,
            source_affinity=SourceAffinity.VPS_PREFERRED,
            required_capabilities=[CapabilityDomain.DOCKER],
            preferred_node_types=[RuntimeNodeType.VPS],
        ),
        RoutingPolicy(
            policy_id=_dist_id("policy"),
            name="GPU Burst Compute",
            description="ML training, inference, and media rendering route to GPU nodes",
            priority=RoutingPriority.CAPABILITY,
            source_affinity=SourceAffinity.GPU_REQUIRED,
            required_capabilities=[CapabilityDomain.GPU],
            preferred_node_types=[RuntimeNodeType.CLOUD_GPU, RuntimeNodeType.LOCAL_PC],
            requires_gpu=True,
        ),
        RoutingPolicy(
            policy_id=_dist_id("policy"),
            name="API Integration",
            description="API calls with tokens/keys route to VPS (always-on, secrets available)",
            priority=RoutingPriority.RELIABILITY,
            source_affinity=SourceAffinity.VPS_PREFERRED,
            required_capabilities=[CapabilityDomain.NETWORK],
            preferred_node_types=[RuntimeNodeType.VPS],
        ),
        RoutingPolicy(
            policy_id=_dist_id("policy"),
            name="Social Media Scraping",
            description="Browser-based social media ingestion requires local logged-in sessions",
            priority=RoutingPriority.PRIVACY,
            source_affinity=SourceAffinity.LOCAL_ONLY,
            required_capabilities=[
                CapabilityDomain.BROWSER,
                CapabilityDomain.LOCAL_ACCOUNTS,
            ],
            preferred_node_types=[RuntimeNodeType.LOCAL_PC],
            requires_browser=True,
            requires_local_accounts=True,
        ),
        RoutingPolicy(
            policy_id=_dist_id("policy"),
            name="File Processing",
            description="Local file operations — filesystem read/write",
            priority=RoutingPriority.LATENCY,
            source_affinity=SourceAffinity.ANY_NODE,
            required_capabilities=[CapabilityDomain.FILESYSTEM],
            preferred_node_types=[RuntimeNodeType.VPS, RuntimeNodeType.LOCAL_PC],
        ),
    ]


def _infer_capabilities_from_description(desc: str) -> set[CapabilityDomain]:
    caps: set[CapabilityDomain] = set()
    lower = desc.lower()
    if any(kw in lower for kw in ["browser", "scrape", "web page", "login"]):
        caps.add(CapabilityDomain.BROWSER)
    if any(kw in lower for kw in ["account", "logged in", "session", "cookie"]):
        caps.add(CapabilityDomain.LOCAL_ACCOUNTS)
    if any(kw in lower for kw in ["gpu", "train", "inference", "render", "cuda"]):
        caps.add(CapabilityDomain.GPU)
    if any(kw in lower for kw in ["docker", "container", "service"]):
        caps.add(CapabilityDomain.DOCKER)
    if any(kw in lower for kw in ["ssh", "remote"]):
        caps.add(CapabilityDomain.SSH)
    if any(kw in lower for kw in ["file", "disk", "read", "write", "path"]):
        caps.add(CapabilityDomain.FILESYSTEM)
    if any(kw in lower for kw in ["api", "http", "request", "webhook"]):
        caps.add(CapabilityDomain.NETWORK)
    if any(kw in lower for kw in ["camera", "photo", "webcam"]):
        caps.add(CapabilityDomain.CAMERA)
    if any(kw in lower for kw in ["audio", "mic", "voice", "speaker"]):
        caps.add(CapabilityDomain.AUDIO)
    if any(kw in lower for kw in ["display", "screen", "gui", "visual"]):
        caps.add(CapabilityDomain.DISPLAY)
    return caps


def _infer_affinity_from_description(desc: str) -> SourceAffinity:
    lower = desc.lower()
    if any(kw in lower for kw in ["instagram", "tiktok", "twitter", "linkedin", "saved video"]):
        return SourceAffinity.LOCAL_ONLY
    if any(kw in lower for kw in ["docker", "service", "cron", "daemon", "always-on"]):
        return SourceAffinity.VPS_PREFERRED
    if any(kw in lower for kw in ["gpu", "train", "render"]):
        return SourceAffinity.GPU_REQUIRED
    if any(kw in lower for kw in ["browser", "logged in", "account"]):
        return SourceAffinity.LOCAL_ONLY
    return SourceAffinity.ANY_NODE


def _filter_by_capabilities(
    nodes: list[RuntimeNodeProfile],
    required: set[CapabilityDomain],
) -> list[RuntimeNodeProfile]:
    if not required:
        return nodes
    return [n for n in nodes if required.issubset(set(n.capabilities))]


def _filter_by_affinity(
    nodes: list[RuntimeNodeProfile],
    affinity: SourceAffinity,
) -> list[RuntimeNodeProfile]:
    if affinity == SourceAffinity.LOCAL_ONLY:
        return [n for n in nodes if n.node_type == RuntimeNodeType.LOCAL_PC]
    if affinity == SourceAffinity.VPS_ONLY:
        return [n for n in nodes if n.node_type == RuntimeNodeType.VPS]
    if affinity == SourceAffinity.LOCAL_PREFERRED:
        local = [n for n in nodes if n.node_type == RuntimeNodeType.LOCAL_PC]
        return local if local else nodes
    if affinity == SourceAffinity.VPS_PREFERRED:
        vps = [n for n in nodes if n.node_type == RuntimeNodeType.VPS]
        return vps if vps else nodes
    if affinity == SourceAffinity.GPU_REQUIRED:
        return [n for n in nodes if n.gpu]
    if affinity == SourceAffinity.BROWSER_REQUIRED:
        return [n for n in nodes if CapabilityDomain.BROWSER in n.capabilities]
    return nodes


def _rank_candidates(
    candidates: list[RuntimeNodeProfile],
    affinity: SourceAffinity,
    policy: RoutingPolicy | None,
) -> RuntimeNodeProfile:
    if not candidates:
        raise ValueError("no candidates to rank")

    def _score(n: RuntimeNodeProfile) -> tuple[int, float]:
        priority = 0
        if n.availability == NodeAvailability.ALWAYS_ON:
            priority -= 10
        elif n.availability == NodeAvailability.ON_DEMAND:
            priority -= 5
        elif n.availability == NodeAvailability.SCHEDULED:
            priority -= 2

        if affinity == SourceAffinity.LOCAL_ONLY and n.node_type == RuntimeNodeType.LOCAL_PC:
            priority -= 20
        elif affinity == SourceAffinity.VPS_PREFERRED and n.node_type == RuntimeNodeType.VPS:
            priority -= 15
        elif affinity == SourceAffinity.GPU_REQUIRED and n.gpu:
            priority -= 15

        if policy and n.node_type in (policy.preferred_node_types or []):
            priority -= 10

        resource_score = n.cpu_cores * 0.3 + n.memory_gb * 0.3 + n.storage_gb * 0.001
        return (priority, -resource_score)

    ranked = sorted(candidates, key=_score)
    return ranked[0]


def _calculate_confidence(
    node: RuntimeNodeProfile,
    required_caps: set[CapabilityDomain],
    affinity: SourceAffinity,
) -> float:
    score = 0.5

    node_caps = set(node.capabilities)
    if required_caps and required_caps.issubset(node_caps):
        score += 0.3
    elif required_caps:
        overlap = len(required_caps & node_caps) / len(required_caps)
        score += 0.3 * overlap

    if affinity == SourceAffinity.LOCAL_ONLY and node.node_type == RuntimeNodeType.LOCAL_PC:
        score += 0.15
    elif affinity == SourceAffinity.VPS_ONLY and node.node_type == RuntimeNodeType.VPS:
        score += 0.15
    elif affinity == SourceAffinity.ANY_NODE:
        score += 0.1

    if node.availability == NodeAvailability.ALWAYS_ON:
        score += 0.05
    elif node.availability == NodeAvailability.INTERMITTENT:
        score -= 0.05

    return max(0.0, min(1.0, score))


def _build_reason(
    node: RuntimeNodeProfile,
    affinity: SourceAffinity,
    required_caps: set[CapabilityDomain],
) -> str:
    parts = [f"Selected {node.name} ({node.node_type.value})"]
    if affinity != SourceAffinity.ANY_NODE and affinity != SourceAffinity.UNKNOWN:
        parts.append(f"affinity={affinity.value}")
    if required_caps:
        parts.append(
            f"caps=[{', '.join(c.value for c in sorted(required_caps, key=lambda x: x.value))}]"
        )
    parts.append(f"avail={node.availability.value}")
    return " | ".join(parts)
