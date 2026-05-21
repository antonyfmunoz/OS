"""Phase 79 system status — MVP harness health and readiness.

No network checks. No adapter execution. No filesystem probing.
UNKNOWN when checks missing. Never HEALTHY by default.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from umh.core.clock import iso_now as _iso_now


class SystemHealth(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    PARTIAL = "partial"
    UNKNOWN = "unknown"
    ERROR = "error"


@dataclass
class ComponentStatus:
    name: str
    available: bool = False
    status: str = "unknown"
    detail: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "available": self.available,
            "status": self.status,
            "detail": self.detail,
            "metadata": self.metadata,
        }


@dataclass
class SystemStatus:
    health: SystemHealth = SystemHealth.UNKNOWN
    generated_at: str = ""
    user_id: str = ""
    control_plane_status: str = "unknown"
    trace_store_status: str = "unknown"
    feedback_store_status: str = "unknown"
    workstation_status: str = "unknown"
    adapter_pack_status: str = "unknown"
    governance_status: str = "unknown"
    backend_registry_status: str = "unknown"
    ontology_kernel_status: str = "unknown"
    storage_gateway_status: str = "unknown"
    memory_discipline_status: str = "unknown"
    migration_status: str = "unknown"
    interface_status: str = "unknown"
    council_status: str = "unknown"
    recent_error_count: int = 0
    warnings: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "health": self.health.value,
            "generated_at": self.generated_at,
            "user_id": self.user_id,
            "control_plane_status": self.control_plane_status,
            "trace_store_status": self.trace_store_status,
            "feedback_store_status": self.feedback_store_status,
            "workstation_status": self.workstation_status,
            "adapter_pack_status": self.adapter_pack_status,
            "governance_status": self.governance_status,
            "backend_registry_status": self.backend_registry_status,
            "ontology_kernel_status": self.ontology_kernel_status,
            "storage_gateway_status": self.storage_gateway_status,
            "memory_discipline_status": self.memory_discipline_status,
            "migration_status": self.migration_status,
            "interface_status": self.interface_status,
            "council_status": self.council_status,
            "recent_error_count": self.recent_error_count,
            "warnings": self.warnings,
            "blockers": self.blockers,
            "metadata": self.metadata,
        }


def check_trace_store(trace_store: Any | None) -> ComponentStatus:
    """Check trace store availability."""
    if trace_store is None:
        return ComponentStatus(name="trace_store", available=False, status="unavailable")
    try:
        trace_store.list_traces(limit=1)
        return ComponentStatus(name="trace_store", available=True, status="ok")
    except Exception as e:
        return ComponentStatus(
            name="trace_store", available=False, status="error", detail=str(e)[:120]
        )


def check_feedback_store(feedback_store: Any | None) -> ComponentStatus:
    """Check feedback store availability."""
    if feedback_store is None:
        return ComponentStatus(name="feedback_store", available=False, status="unavailable")
    try:
        feedback_store.list_outcomes(limit=1)
        return ComponentStatus(name="feedback_store", available=True, status="ok")
    except Exception as e:
        return ComponentStatus(
            name="feedback_store", available=False, status="error", detail=str(e)[:120]
        )


def check_workstation_state(
    profile: Any | None = None,
    session: Any | None = None,
) -> ComponentStatus:
    """Check workstation state availability."""
    if profile is None and session is None:
        return ComponentStatus(name="workstation", available=False, status="unavailable")
    detail_parts: list[str] = []
    if profile is not None:
        detail_parts.append(f"profile: {getattr(profile, 'user_id', 'loaded')}")
    if session is not None:
        detail_parts.append(f"session: {getattr(session, 'session_id', 'loaded')}")
    return ComponentStatus(
        name="workstation",
        available=True,
        status="ok",
        detail=", ".join(detail_parts),
    )


def check_adapter_pack_status(
    adapter_registry: Any | None = None,
) -> ComponentStatus:
    """Check adapter pack status without executing adapters."""
    if adapter_registry is None:
        return ComponentStatus(name="adapter_pack", available=False, status="unavailable")
    try:
        adapters = (
            adapter_registry.list_adapters() if hasattr(adapter_registry, "list_adapters") else []
        )
        return ComponentStatus(
            name="adapter_pack",
            available=True,
            status="ok",
            detail=f"{len(adapters)} adapters registered",
        )
    except Exception:
        return ComponentStatus(name="adapter_pack", available=True, status="degraded")


def check_governance_status() -> ComponentStatus:
    """Check governance module availability."""
    try:
        from umh.governance.authority import check_governance

        return ComponentStatus(name="governance", available=True, status="ok")
    except Exception:
        return ComponentStatus(name="governance", available=False, status="unavailable")


def check_backend_registry(
    backend_registry: Any | None = None,
) -> ComponentStatus:
    """Check backend registry status."""
    if backend_registry is None:
        return ComponentStatus(name="backend_registry", available=False, status="unavailable")
    try:
        envs = backend_registry.list_environments()
        return ComponentStatus(
            name="backend_registry",
            available=True,
            status="ok",
            detail=f"{len(envs)} environments",
        )
    except Exception:
        return ComponentStatus(name="backend_registry", available=True, status="degraded")


def check_ontology_kernel() -> ComponentStatus:
    """Check ontology kernel availability and validation status."""
    try:
        from umh.ontology.primitives import get_primitives
        from umh.ontology.laws import get_laws
        from umh.ontology.validation import validate_ontology_kernel

        primitives = get_primitives()
        laws = get_laws()
        result = validate_ontology_kernel(primitives, laws)
        detail = f"{len(primitives)} primitives, {len(laws)} laws, valid={result.valid}"
        status = "ok" if result.valid else "degraded"
        return ComponentStatus(
            name="ontology_kernel",
            available=True,
            status=status,
            detail=detail,
            metadata={
                "primitive_count": len(primitives),
                "law_count": len(laws),
                "validation_valid": result.valid,
                "issue_count": len(result.issues),
            },
        )
    except Exception as e:
        return ComponentStatus(
            name="ontology_kernel", available=False, status="error", detail=str(e)[:120]
        )


def check_storage_gateway(gateway: Any | None = None) -> ComponentStatus:
    if gateway is None:
        return ComponentStatus(name="storage_gateway", available=False, status="unavailable")
    try:
        info = gateway.to_dict() if hasattr(gateway, "to_dict") else {}
        recs = info.get("default_record_count", 0)
        backends = info.get("backend_count", 1)
        return ComponentStatus(
            name="storage_gateway",
            available=True,
            status="ok",
            detail=f"{recs} records, {backends} backends",
            metadata={"record_count": recs, "backend_count": backends},
        )
    except Exception as e:
        return ComponentStatus(
            name="storage_gateway", available=False, status="error", detail=str(e)[:120]
        )


def check_memory_discipline() -> ComponentStatus:
    try:
        from umh.memory.discipline import build_default_memory_write_policy

        policy = build_default_memory_write_policy()
        detail = f"auto_promotion={policy.allow_auto_promotion}, min_conf={policy.min_confidence}"
        return ComponentStatus(
            name="memory_discipline",
            available=True,
            status="ok",
            detail=detail,
            metadata=policy.to_dict(),
        )
    except Exception as e:
        return ComponentStatus(
            name="memory_discipline", available=False, status="error", detail=str(e)[:120]
        )


def check_migration_status(migration_registry: Any | None = None) -> ComponentStatus:
    if migration_registry is None:
        return ComponentStatus(name="migration", available=False, status="unavailable")
    try:
        rec_count = getattr(migration_registry, "record_count", 0)
        map_count = getattr(migration_registry, "mapping_count", 0)
        return ComponentStatus(
            name="migration",
            available=True,
            status="ok",
            detail=f"{rec_count} records, {map_count} mappings",
            metadata={"record_count": rec_count, "mapping_count": map_count},
        )
    except Exception as e:
        return ComponentStatus(
            name="migration", available=False, status="error", detail=str(e)[:120]
        )


def check_interface_status(interface_registry: Any | None = None) -> ComponentStatus:
    if interface_registry is None:
        return ComponentStatus(name="interface", available=False, status="unavailable")
    try:
        count = getattr(interface_registry, "surface_count", 0)
        return ComponentStatus(
            name="interface",
            available=True,
            status="ok",
            detail=f"{count} surfaces registered",
            metadata={"surface_count": count},
        )
    except Exception as e:
        return ComponentStatus(
            name="interface", available=False, status="error", detail=str(e)[:120]
        )


def check_council_status() -> ComponentStatus:
    try:
        from umh.council.roles import get_default_council_roles
        from umh.council.views import build_council_health_view

        health = build_council_health_view()
        detail = f"{health.role_count} roles, available={health.council_available}"
        return ComponentStatus(
            name="council",
            available=health.council_available,
            status="ok" if health.council_available else "degraded",
            detail=detail,
            metadata={
                "role_count": health.role_count,
                "ontology_bridge_ready": health.ontology_bridge_ready,
            },
        )
    except Exception as e:
        return ComponentStatus(name="council", available=False, status="error", detail=str(e)[:120])


def build_system_status(
    *,
    user_id: str = "",
    trace_store: Any | None = None,
    feedback_store: Any | None = None,
    workstation_profile: Any | None = None,
    workstation_session: Any | None = None,
    adapter_registry: Any | None = None,
    backend_registry: Any | None = None,
    storage_gateway: Any | None = None,
    migration_registry: Any | None = None,
    interface_registry: Any | None = None,
) -> SystemStatus:
    """Build comprehensive system status. Never reports HEALTHY when checks are missing."""
    warnings: list[str] = []
    blockers: list[str] = []
    components: list[ComponentStatus] = []

    ts = check_trace_store(trace_store)
    components.append(ts)

    fs = check_feedback_store(feedback_store)
    components.append(fs)

    ws = check_workstation_state(workstation_profile, workstation_session)
    components.append(ws)

    ap = check_adapter_pack_status(adapter_registry)
    components.append(ap)

    gov = check_governance_status()
    components.append(gov)

    br = check_backend_registry(backend_registry)
    components.append(br)

    onto = check_ontology_kernel()
    components.append(onto)

    sg = check_storage_gateway(storage_gateway)
    components.append(sg)

    md = check_memory_discipline()
    components.append(md)

    mig = check_migration_status(migration_registry)
    components.append(mig)

    ifc = check_interface_status(interface_registry)
    components.append(ifc)

    council = check_council_status()
    components.append(council)

    available_count = sum(1 for c in components if c.available)
    total = len(components)
    error_count = sum(1 for c in components if c.status == "error")

    for c in components:
        if not c.available:
            warnings.append(f"{c.name} unavailable")
        if c.status == "error":
            blockers.append(f"{c.name}: {c.detail}")

    if error_count > 0:
        health = SystemHealth.ERROR
    elif available_count == total:
        health = SystemHealth.HEALTHY
    elif available_count == 0:
        health = SystemHealth.UNKNOWN
    elif available_count >= total // 2:
        health = SystemHealth.DEGRADED
    else:
        health = SystemHealth.PARTIAL

    recent_error_count = 0
    if trace_store is not None:
        try:
            recent = trace_store.list_traces(limit=25)
            recent_error_count = sum(
                1
                for t in recent
                if (getattr(t, "status", "") == "failed" or getattr(t, "error", None))
            )
        except Exception:
            pass

    return SystemStatus(
        health=health,
        generated_at=_iso_now(),
        user_id=user_id,
        control_plane_status="ok",
        trace_store_status=ts.status,
        feedback_store_status=fs.status,
        workstation_status=ws.status,
        adapter_pack_status=ap.status,
        governance_status=gov.status,
        backend_registry_status=br.status,
        ontology_kernel_status=onto.status,
        storage_gateway_status=sg.status,
        memory_discipline_status=md.status,
        migration_status=mig.status,
        interface_status=ifc.status,
        council_status=council.status,
        recent_error_count=recent_error_count,
        warnings=warnings,
        blockers=blockers,
    )
