"""Phase 87B source-to-node routing — integrates ingestion sources with Phase 87A node routing.

Maps ingestion sources to node affinities and capabilities from
umh.distributed, then generates routing recommendations for where
each source should be ingested.

Advisory/planning only. No scraping. No API calls. No account connections.
No file reading. No memory promotion. No execution.
"""

from __future__ import annotations

from typing import Any

from umh.distributed.contracts import (
    CapabilityDomain,
    RuntimeNodeType,
    SourceAffinity,
)
from umh.ingestion.contracts import (
    AccessMethod,
    IngestionSource,
    PermissionScope,
    PlatformType,
    SourceClass,
    SourceIngestionRoute,
    _ingest_id,
)


_SOURCE_CLASS_NODE_AFFINITY: dict[SourceClass, SourceAffinity] = {
    SourceClass.EMAIL: SourceAffinity.VPS_PREFERRED,
    SourceClass.CALENDAR: SourceAffinity.VPS_PREFERRED,
    SourceClass.TASK_MANAGEMENT: SourceAffinity.VPS_PREFERRED,
    SourceClass.NOTE_TAKING: SourceAffinity.ANY_NODE,
    SourceClass.DOCUMENT_EDITING: SourceAffinity.VPS_PREFERRED,
    SourceClass.SPREADSHEET: SourceAffinity.VPS_PREFERRED,
    SourceClass.CLOUD_STORAGE: SourceAffinity.VPS_PREFERRED,
    SourceClass.CODE_REPOSITORY: SourceAffinity.VPS_PREFERRED,
    SourceClass.CI_CD: SourceAffinity.VPS_ONLY,
    SourceClass.CONTAINER_RUNTIME: SourceAffinity.VPS_ONLY,
    SourceClass.SOCIAL_MEDIA: SourceAffinity.LOCAL_ONLY,
    SourceClass.MESSAGING: SourceAffinity.VPS_PREFERRED,
    SourceClass.VIDEO_PLATFORM: SourceAffinity.ANY_NODE,
    SourceClass.AUDIO_PLATFORM: SourceAffinity.LOCAL_PREFERRED,
    SourceClass.CRM: SourceAffinity.VPS_PREFERRED,
    SourceClass.PAYMENT_PROCESSING: SourceAffinity.VPS_PREFERRED,
    SourceClass.ACCOUNTING: SourceAffinity.VPS_PREFERRED,
    SourceClass.ANALYTICS: SourceAffinity.VPS_PREFERRED,
    SourceClass.ADVERTISING: SourceAffinity.VPS_PREFERRED,
    SourceClass.AI_ASSISTANT: SourceAffinity.ANY_NODE,
    SourceClass.BROWSER_HISTORY: SourceAffinity.LOCAL_ONLY,
    SourceClass.VOICE_MEMO: SourceAffinity.LOCAL_ONLY,
    SourceClass.CAMERA_CAPTURE: SourceAffinity.LOCAL_ONLY,
    SourceClass.SCREEN_CAPTURE: SourceAffinity.LOCAL_ONLY,
    SourceClass.EBOOK_READER: SourceAffinity.LOCAL_PREFERRED,
    SourceClass.PODCAST_PLAYER: SourceAffinity.ANY_NODE,
    SourceClass.DESIGN_TOOL: SourceAffinity.LOCAL_PREFERRED,
    SourceClass.THREE_D_MODELING: SourceAffinity.LOCAL_PREFERRED,
}

_SOURCE_CLASS_CAPABILITIES: dict[SourceClass, list[CapabilityDomain]] = {
    SourceClass.EMAIL: [CapabilityDomain.NETWORK],
    SourceClass.CALENDAR: [CapabilityDomain.NETWORK],
    SourceClass.TASK_MANAGEMENT: [CapabilityDomain.NETWORK],
    SourceClass.NOTE_TAKING: [CapabilityDomain.FILESYSTEM],
    SourceClass.DOCUMENT_EDITING: [CapabilityDomain.NETWORK],
    SourceClass.SPREADSHEET: [CapabilityDomain.NETWORK],
    SourceClass.CLOUD_STORAGE: [CapabilityDomain.NETWORK, CapabilityDomain.STORAGE],
    SourceClass.CODE_REPOSITORY: [CapabilityDomain.NETWORK, CapabilityDomain.SSH],
    SourceClass.CI_CD: [CapabilityDomain.NETWORK, CapabilityDomain.DOCKER],
    SourceClass.CONTAINER_RUNTIME: [CapabilityDomain.DOCKER],
    SourceClass.SOCIAL_MEDIA: [CapabilityDomain.BROWSER, CapabilityDomain.LOCAL_ACCOUNTS],
    SourceClass.MESSAGING: [CapabilityDomain.NETWORK],
    SourceClass.VIDEO_PLATFORM: [CapabilityDomain.NETWORK],
    SourceClass.AUDIO_PLATFORM: [CapabilityDomain.AUDIO, CapabilityDomain.FILESYSTEM],
    SourceClass.CRM: [CapabilityDomain.NETWORK],
    SourceClass.PAYMENT_PROCESSING: [CapabilityDomain.NETWORK],
    SourceClass.ACCOUNTING: [CapabilityDomain.NETWORK],
    SourceClass.ANALYTICS: [CapabilityDomain.NETWORK],
    SourceClass.ADVERTISING: [CapabilityDomain.NETWORK],
    SourceClass.AI_ASSISTANT: [CapabilityDomain.FILESYSTEM],
    SourceClass.BROWSER_HISTORY: [CapabilityDomain.BROWSER, CapabilityDomain.FILESYSTEM],
    SourceClass.VOICE_MEMO: [CapabilityDomain.AUDIO, CapabilityDomain.FILESYSTEM],
    SourceClass.CAMERA_CAPTURE: [CapabilityDomain.CAMERA],
    SourceClass.SCREEN_CAPTURE: [CapabilityDomain.DISPLAY, CapabilityDomain.FILESYSTEM],
    SourceClass.EBOOK_READER: [CapabilityDomain.FILESYSTEM],
    SourceClass.PODCAST_PLAYER: [CapabilityDomain.NETWORK],
    SourceClass.DESIGN_TOOL: [CapabilityDomain.FILESYSTEM, CapabilityDomain.DISPLAY],
    SourceClass.THREE_D_MODELING: [CapabilityDomain.FILESYSTEM, CapabilityDomain.COMPUTE],
}

_ACCESS_METHOD_AFFINITY_OVERRIDE: dict[AccessMethod, SourceAffinity] = {
    AccessMethod.BROWSER_SESSION: SourceAffinity.LOCAL_ONLY,
    AccessMethod.SCREEN_CAPTURE: SourceAffinity.LOCAL_ONLY,
    AccessMethod.LOCAL_FILESYSTEM: SourceAffinity.LOCAL_PREFERRED,
}


def get_source_node_affinity(source_class: SourceClass) -> SourceAffinity:
    return _SOURCE_CLASS_NODE_AFFINITY.get(source_class, SourceAffinity.UNKNOWN)


def get_source_required_capabilities(source_class: SourceClass) -> list[CapabilityDomain]:
    return _SOURCE_CLASS_CAPABILITIES.get(source_class, [])


def route_ingestion_source(source: IngestionSource) -> SourceIngestionRoute:
    affinity = _resolve_affinity(source)
    caps = get_source_required_capabilities(source.source_class)

    access_overrides = _check_access_method_overrides(source.access_methods)
    if access_overrides:
        affinity = access_overrides

    node_type = _recommend_node_type(affinity)
    warnings = _generate_routing_warnings(source, affinity, node_type)
    reason = _build_routing_reason(source, affinity, node_type, caps)

    return SourceIngestionRoute(
        route_id=_ingest_id("route"),
        source_id=source.source_id,
        source_class=source.source_class,
        platform=source.platform,
        recommended_node_type=node_type,
        source_affinity=affinity.value,
        required_capabilities=[c.value for c in caps],
        access_method=source.access_methods[0] if source.access_methods else AccessMethod.UNKNOWN,
        permission_scope=source.permission_scopes[0]
        if source.permission_scopes
        else PermissionScope.UNKNOWN,
        sensitivity=source.sensitivity,
        review_requirement=source.review_requirement,
        reason=reason,
        warnings=warnings,
    )


def route_all_sources(
    sources: list[IngestionSource],
) -> list[SourceIngestionRoute]:
    return [route_ingestion_source(s) for s in sources]


def get_local_only_sources(
    sources: list[IngestionSource],
) -> list[IngestionSource]:
    return [s for s in sources if _resolve_affinity(s) == SourceAffinity.LOCAL_ONLY]


def get_vps_sources(
    sources: list[IngestionSource],
) -> list[IngestionSource]:
    return [
        s
        for s in sources
        if _resolve_affinity(s) in (SourceAffinity.VPS_ONLY, SourceAffinity.VPS_PREFERRED)
    ]


def _resolve_affinity(source: IngestionSource) -> SourceAffinity:
    override = _check_access_method_overrides(source.access_methods)
    if override:
        return override
    return get_source_node_affinity(source.source_class)


def _check_access_method_overrides(
    methods: list[AccessMethod],
) -> SourceAffinity | None:
    for method in methods:
        if method in _ACCESS_METHOD_AFFINITY_OVERRIDE:
            return _ACCESS_METHOD_AFFINITY_OVERRIDE[method]
    return None


def _recommend_node_type(affinity: SourceAffinity) -> str:
    mapping: dict[SourceAffinity, str] = {
        SourceAffinity.LOCAL_ONLY: RuntimeNodeType.LOCAL_PC.value,
        SourceAffinity.LOCAL_PREFERRED: RuntimeNodeType.LOCAL_PC.value,
        SourceAffinity.VPS_ONLY: RuntimeNodeType.VPS.value,
        SourceAffinity.VPS_PREFERRED: RuntimeNodeType.VPS.value,
        SourceAffinity.GPU_REQUIRED: RuntimeNodeType.CLOUD_GPU.value,
        SourceAffinity.ANY_NODE: RuntimeNodeType.VPS.value,
        SourceAffinity.BROWSER_REQUIRED: RuntimeNodeType.LOCAL_PC.value,
    }
    return mapping.get(affinity, RuntimeNodeType.VPS.value)


def _generate_routing_warnings(
    source: IngestionSource,
    affinity: SourceAffinity,
    node_type: str,
) -> list[str]:
    warnings: list[str] = []

    if affinity == SourceAffinity.LOCAL_ONLY:
        warnings.append("Requires local PC with logged-in browser sessions")

    if AccessMethod.BROWSER_SESSION in source.access_methods:
        warnings.append("Browser session access — session cookies may expire")

    from umh.ingestion.contracts import SourceSensitivity

    if source.sensitivity == SourceSensitivity.FINANCIAL:
        warnings.append("Financial source — ensure encrypted transport and audit logging")

    if source.sensitivity == SourceSensitivity.CREDENTIAL:
        warnings.append("Credential source — should not be ingested, access at runtime only")

    return warnings


def _build_routing_reason(
    source: IngestionSource,
    affinity: SourceAffinity,
    node_type: str,
    caps: list[CapabilityDomain],
) -> str:
    parts = [f"Route {source.name} to {node_type}"]
    if affinity != SourceAffinity.UNKNOWN:
        parts.append(f"affinity={affinity.value}")
    if caps:
        parts.append(f"caps=[{', '.join(c.value for c in caps)}]")
    if source.access_methods:
        parts.append(f"access={source.access_methods[0].value}")
    return " | ".join(parts)
