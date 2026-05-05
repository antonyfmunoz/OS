"""Phase 80 compatibility bridges — convert existing definitions to RegistryItems.

Bridges existing capability/environment/adapter/backend/mode definitions into
the unified registry format without modifying or breaking those modules.

No execution. No mutation. No adapter calls. Read-only conversions.
"""

from __future__ import annotations

from typing import Any

from umh.registry.contracts import (
    RegistryAuthorityRequirement,
    RegistryItem,
    RegistryItemStatus,
    RegistryType,
    _registry_id,
)

_AUTHORITY_MAP: dict[str, RegistryAuthorityRequirement] = {
    "OBSERVE": RegistryAuthorityRequirement.OBSERVE,
    "ANALYZE": RegistryAuthorityRequirement.ANALYZE,
    "ACT": RegistryAuthorityRequirement.ACT,
    "EXECUTE": RegistryAuthorityRequirement.EXECUTE,
}


def capability_definitions_to_registry_items(
    capabilities: list[Any] | None = None,
) -> list[RegistryItem]:
    if capabilities is None:
        try:
            from umh.capabilities.definitions import list_capabilities

            capabilities = list_capabilities()
        except Exception:
            return []

    items: list[RegistryItem] = []
    for cap in capabilities:
        cap_id = getattr(cap, "capability_id", "")
        name = getattr(cap, "name", cap_id)
        risk = getattr(cap, "risk_level", None)
        risk_str = risk.value if hasattr(risk, "value") else str(risk) if risk else ""
        auth = getattr(cap, "authority_required", None)
        auth_name = auth.name if hasattr(auth, "name") else ""
        auth_req = _AUTHORITY_MAP.get(auth_name, RegistryAuthorityRequirement.UNKNOWN)
        allowed_envs = getattr(cap, "allowed_environments", frozenset())
        requires_approval = getattr(cap, "requires_approval", False)
        notes = getattr(cap, "notes", "")

        items.append(
            RegistryItem(
                item_id=f"cap_{cap_id}",
                registry_type=RegistryType.CAPABILITY,
                name=name,
                description=notes,
                status=RegistryItemStatus.ACTIVE,
                authority_required=auth_req,
                capabilities=[cap_id],
                environments=sorted(allowed_envs),
                tags=["mvp", f"risk:{risk_str}"],
                version="76",
                source_module="umh.capabilities.definitions",
                risk_level=risk_str,
                requires_approval=requires_approval,
                metadata={
                    "default_timeout_s": getattr(cap, "default_timeout_s", 30),
                    "expected_inputs": list(getattr(cap, "expected_inputs", ())),
                    "expected_outputs": list(getattr(cap, "expected_outputs", ())),
                },
            )
        )
    return items


def environment_definitions_to_registry_items(
    environments: list[Any] | None = None,
) -> list[RegistryItem]:
    if environments is None:
        try:
            from umh.environments.definitions import list_environments

            environments = list_environments()
        except Exception:
            return []

    items: list[RegistryItem] = []
    for env in environments:
        env_id = getattr(env, "environment_id", "")
        desc = getattr(env, "description", "")
        caps = getattr(env, "capabilities", frozenset())
        available = getattr(env, "available", True)
        network = getattr(env, "network_policy", "deny")
        safe_roots = getattr(env, "safe_roots", ())

        items.append(
            RegistryItem(
                item_id=f"env_{env_id}",
                registry_type=RegistryType.ENVIRONMENT,
                name=env_id,
                description=desc,
                status=RegistryItemStatus.ACTIVE if available else RegistryItemStatus.UNAVAILABLE,
                capabilities=sorted(caps),
                environments=[env_id],
                tags=["mvp", f"network:{network}"],
                version="76",
                source_module="umh.environments.definitions",
                metadata={
                    "network_policy": network,
                    "safe_roots": list(safe_roots),
                },
            )
        )
    return items


def adapter_pack_to_registry_items(
    adapter_backend: Any | None = None,
) -> list[RegistryItem]:
    if adapter_backend is None:
        return []

    seen_adapters: dict[str, RegistryItem] = {}

    adapters_map = getattr(adapter_backend, "_adapters", {})
    for cap, adapter in adapters_map.items():
        adapter_name = getattr(adapter, "name", type(adapter).__name__)
        if adapter_name in seen_adapters:
            item = seen_adapters[adapter_name]
            if cap not in item.capabilities:
                item.capabilities.append(cap)
            continue

        supported_caps = list(getattr(adapter, "supported_capabilities", frozenset()))
        supported_envs = list(getattr(adapter, "supported_environments", frozenset()))

        item = RegistryItem(
            item_id=f"adp_{adapter_name}",
            registry_type=RegistryType.ADAPTER,
            name=adapter_name,
            description=f"MVP adapter: {adapter_name}",
            status=RegistryItemStatus.ACTIVE,
            capabilities=sorted(supported_caps),
            environments=sorted(supported_envs),
            tags=["mvp", "adapter"],
            version="76",
            source_module="umh.adapters",
        )
        seen_adapters[adapter_name] = item

    return list(seen_adapters.values())


def backend_registry_to_registry_items(
    backend_registry: Any | None = None,
) -> list[RegistryItem]:
    if backend_registry is None:
        try:
            from umh.execution.backend_registry import get_backend_registry

            backend_registry = get_backend_registry()
        except Exception:
            return []

    items: list[RegistryItem] = []
    try:
        envs = backend_registry.list_environments()
    except Exception:
        return []

    for env_name in envs:
        backend = backend_registry.get(env_name)
        backend_name = type(backend).__name__ if backend else "unknown"
        can_handle = hasattr(backend, "can_handle")

        items.append(
            RegistryItem(
                item_id=f"bknd_{env_name}",
                registry_type=RegistryType.BACKEND,
                name=f"{backend_name}:{env_name}",
                description=f"Execution backend for environment '{env_name}'",
                status=RegistryItemStatus.ACTIVE,
                environments=[env_name],
                tags=["backend", f"impl:{backend_name}"],
                version="76",
                source_module="umh.execution.backend_registry",
                metadata={
                    "backend_class": backend_name,
                    "has_can_handle": can_handle,
                },
            )
        )
    return items


def workstation_modes_to_registry_items(
    mode_registry: Any | None = None,
) -> list[RegistryItem]:
    if mode_registry is None:
        try:
            from umh.workstation.modes import ModeRegistry

            mode_registry = ModeRegistry()
        except Exception:
            return []

    items: list[RegistryItem] = []
    try:
        modes = mode_registry.list_modes()
    except Exception:
        return []

    for mode_profile in modes:
        mode_val = getattr(mode_profile, "mode", None)
        mode_name = mode_val.value if hasattr(mode_val, "value") else str(mode_val)
        desc = getattr(mode_profile, "description", "")
        gov_level = getattr(mode_profile, "default_governance_level", "")
        auth_req = _AUTHORITY_MAP.get(gov_level.upper(), RegistryAuthorityRequirement.UNKNOWN)
        env_pref = getattr(mode_profile, "default_environment_preference", "")
        allowed_caps = sorted(getattr(mode_profile, "allowed_capabilities", frozenset()))
        restricted_caps = sorted(getattr(mode_profile, "restricted_capabilities", frozenset()))
        tags_raw = list(getattr(mode_profile, "memory_context_tags", ()))

        items.append(
            RegistryItem(
                item_id=f"mode_{mode_name}",
                registry_type=RegistryType.WORKSTATION_MODE,
                name=mode_name,
                description=desc,
                status=RegistryItemStatus.ACTIVE,
                authority_required=auth_req,
                capabilities=allowed_caps,
                environments=[env_pref] if env_pref else [],
                tags=["workstation_mode"] + tags_raw,
                version="77",
                source_module="umh.workstation.modes",
                metadata={
                    "default_governance_level": gov_level,
                    "restricted_capabilities": restricted_caps,
                    "boot_sequence_id": getattr(mode_profile, "boot_sequence_id", ""),
                },
            )
        )
    return items


def governance_policies_to_registry_items() -> list[RegistryItem]:
    try:
        from umh.governance.authority import get_governance_policy

        policy = get_governance_policy()
        policy_name = type(policy).__name__
        max_auth = ""
        if hasattr(policy, "_max"):
            max_auth = policy._max.name if hasattr(policy._max, "name") else str(policy._max)

        return [
            RegistryItem(
                item_id="policy_default_governance",
                registry_type=RegistryType.POLICY,
                name="default_governance",
                description=f"Active governance policy: {policy_name}",
                status=RegistryItemStatus.ACTIVE,
                authority_required=_AUTHORITY_MAP.get(
                    max_auth, RegistryAuthorityRequirement.UNKNOWN
                ),
                tags=["governance", "policy", "active"],
                version="76",
                source_module="umh.governance.authority",
                metadata={"policy_class": policy_name, "max_authority": max_auth},
            )
        ]
    except Exception:
        return []


def ontology_primitives_to_registry_items(
    primitives: list[Any] | None = None,
) -> list[RegistryItem]:
    if primitives is None:
        try:
            from umh.ontology.primitives import get_primitives

            primitives = get_primitives()
        except Exception:
            return []

    items: list[RegistryItem] = []
    for p in primitives:
        pid = getattr(p, "primitive_id", "")
        name = getattr(p, "name", pid)
        pt = getattr(p, "primitive_type", None)
        pt_str = pt.value if hasattr(pt, "value") else str(pt or "")
        scope = getattr(p, "scope", None)
        scope_str = scope.value if hasattr(scope, "value") else ""
        conf = getattr(p, "confidence", 0.0)

        items.append(
            RegistryItem(
                item_id=f"onto_{pid}",
                registry_type=RegistryType.PRIMITIVE,
                name=name,
                description=getattr(p, "definition", "")[:200],
                status=RegistryItemStatus.ACTIVE,
                tags=["ontology", "primitive", f"scope:{scope_str}", f"type:{pt_str}"],
                version="81",
                source_module="umh.ontology.primitives",
                metadata={
                    "primitive_type": pt_str,
                    "scope": scope_str,
                    "confidence": conf,
                    "evidence_basis": getattr(p, "evidence_basis", ""),
                },
            )
        )
    return items


def ontology_laws_to_registry_items(
    laws: list[Any] | None = None,
) -> list[RegistryItem]:
    if laws is None:
        try:
            from umh.ontology.laws import get_laws

            laws = get_laws()
        except Exception:
            return []

    items: list[RegistryItem] = []
    for law in laws:
        lid = getattr(law, "law_id", "")
        name = getattr(law, "name", lid)
        lt = getattr(law, "law_type", None)
        lt_str = lt.value if hasattr(lt, "value") else str(lt or "")
        scope = getattr(law, "scope", None)
        scope_str = scope.value if hasattr(scope, "value") else ""
        conf = getattr(law, "confidence", 0.0)

        items.append(
            RegistryItem(
                item_id=f"onto_{lid}",
                registry_type=RegistryType.LAW,
                name=name,
                description=getattr(law, "definition", "")[:200],
                status=RegistryItemStatus.ACTIVE,
                tags=["ontology", "law", f"scope:{scope_str}", f"type:{lt_str}"],
                version="81",
                source_module="umh.ontology.laws",
                metadata={
                    "law_type": lt_str,
                    "scope": scope_str,
                    "confidence": conf,
                    "evidence_basis": getattr(law, "evidence_basis", ""),
                    "governs": list(getattr(law, "governs", [])),
                },
            )
        )
    return items


def domain_projections_to_registry_items(
    projections: list[Any] | None = None,
) -> list[RegistryItem]:
    if projections is None:
        try:
            from umh.ontology.domain_projection import get_domain_projections

            projections = get_domain_projections()
        except Exception:
            return []

    items: list[RegistryItem] = []
    for ps in projections:
        d = getattr(ps, "domain", None)
        domain_str = d.value if hasattr(d, "value") else str(d or "")
        pp_count = len(getattr(ps, "primitive_projections", []))
        lp_count = len(getattr(ps, "law_projections", []))

        items.append(
            RegistryItem(
                item_id=f"onto_proj_{domain_str}",
                registry_type=RegistryType.DOMAIN_PROJECTION,
                name=f"{domain_str}_projection",
                description=f"Domain projection for {domain_str}",
                status=RegistryItemStatus.ACTIVE,
                tags=["ontology", "projection", f"domain:{domain_str}"],
                version="81",
                source_module="umh.ontology.domain_projection",
                metadata={
                    "domain": domain_str,
                    "primitive_projection_count": pp_count,
                    "law_projection_count": lp_count,
                    "confidence": getattr(ps, "confidence", 0.0),
                },
            )
        )
    return items


def correspondence_maps_to_registry_items(
    maps: list[Any] | None = None,
) -> list[RegistryItem]:
    if maps is None:
        try:
            from umh.ontology.correspondence import get_correspondence_maps

            maps = get_correspondence_maps()
        except Exception:
            return []

    items: list[RegistryItem] = []
    for cm in maps:
        mid = getattr(cm, "map_id", "")
        src = getattr(cm, "source_domain", "")
        tgt = getattr(cm, "target_domain", "")
        st = getattr(cm, "status", None)
        st_str = st.value if hasattr(st, "value") else str(st or "")

        items.append(
            RegistryItem(
                item_id=f"onto_{mid}",
                registry_type=RegistryType.CORRESPONDENCE_MAP,
                name=mid,
                description=f"Correspondence: {src} -> {tgt}",
                status=RegistryItemStatus.ACTIVE,
                tags=["ontology", "correspondence", f"src:{src}", f"tgt:{tgt}"],
                version="81",
                source_module="umh.ontology.correspondence",
                metadata={
                    "source_domain": src,
                    "target_domain": tgt,
                    "correspondence_status": st_str,
                    "confidence": getattr(cm, "confidence", 0.0),
                    "analogy_breaks_count": len(getattr(cm, "analogy_breaks", [])),
                },
            )
        )
    return items


def legacy_modules_to_registry_items(
    records: list[Any] | None = None,
) -> list[RegistryItem]:
    if records is None:
        try:
            from umh.migration.deprecation_registry import build_default_deprecation_registry

            reg = build_default_deprecation_registry()
            records = reg._records
        except Exception:
            return []

    items: list[RegistryItem] = []
    for r in records:
        status_val = getattr(r, "status", None)
        status_str = status_val.value if hasattr(status_val, "value") else str(status_val or "")
        cat = getattr(r, "category", None)
        cat_str = cat.value if hasattr(cat, "value") else str(cat or "")
        risk = getattr(r, "risk_level", None)
        risk_str = risk.value if hasattr(risk, "value") else str(risk or "")
        action = getattr(r, "migration_action", None)
        action_str = action.value if hasattr(action, "value") else str(action or "")

        reg_status = (
            RegistryItemStatus.DEPRECATED
            if status_str == "deprecated"
            else RegistryItemStatus.ACTIVE
        )

        items.append(
            RegistryItem(
                item_id=f"legacy_{getattr(r, 'module_name', '').replace('.', '_')}",
                registry_type=RegistryType.LEGACY_MODULE,
                name=getattr(r, "module_name", ""),
                description=getattr(r, "reason", "") or f"Legacy module: {cat_str}",
                status=reg_status,
                tags=["legacy", f"category:{cat_str}", f"risk:{risk_str}"] + getattr(r, "tags", []),
                version="83",
                source_module="umh.migration.deprecation_registry",
                risk_level=risk_str,
                metadata={
                    "legacy_status": status_str,
                    "migration_action": action_str,
                    "clean_equivalent": getattr(r, "clean_equivalent", None),
                    "evidence_count": len(getattr(r, "evidence", [])),
                },
            )
        )
    return items


def migration_mappings_to_registry_items(
    mappings: list[Any] | None = None,
) -> list[RegistryItem]:
    if mappings is None:
        try:
            from umh.migration.deprecation_registry import build_default_deprecation_registry

            reg = build_default_deprecation_registry()
            mappings = reg._mappings
        except Exception:
            return []

    items: list[RegistryItem] = []
    for m in mappings:
        action = getattr(m, "migration_action", None)
        action_str = action.value if hasattr(action, "value") else str(action or "")

        items.append(
            RegistryItem(
                item_id=f"mm_{getattr(m, 'mapping_id', '')}",
                registry_type=RegistryType.MIGRATION_MAPPING,
                name=getattr(m, "legacy_module", ""),
                description=f"Migration: {getattr(m, 'legacy_module', '')} -> {getattr(m, 'clean_equivalent', '')}",
                status=RegistryItemStatus.ACTIVE,
                tags=["migration", f"action:{action_str}"],
                version="83",
                source_module="umh.migration.compatibility",
                metadata={
                    "legacy_module": getattr(m, "legacy_module", ""),
                    "clean_equivalent": getattr(m, "clean_equivalent", ""),
                    "confidence": getattr(m, "confidence", 0.0),
                    "blockers_count": len(getattr(m, "blockers", [])),
                },
            )
        )
    return items


def import_boundary_rules_to_registry_items(
    rules: list[Any] | None = None,
) -> list[RegistryItem]:
    if rules is None:
        try:
            from umh.migration.import_boundary import build_default_import_boundary_rules

            rules = build_default_import_boundary_rules()
        except Exception:
            return []

    items: list[RegistryItem] = []
    for rule in rules:
        status_val = getattr(rule, "status", None)
        status_str = status_val.value if hasattr(status_val, "value") else str(status_val or "")

        items.append(
            RegistryItem(
                item_id=f"ibr_{getattr(rule, 'rule_id', '')}",
                registry_type=RegistryType.IMPORT_BOUNDARY_RULE,
                name=getattr(rule, "rule_id", ""),
                description=getattr(rule, "reason", ""),
                status=RegistryItemStatus.ACTIVE,
                tags=["import_boundary", f"status:{status_str}"],
                version="83",
                source_module="umh.migration.import_boundary",
                metadata={
                    "source_pattern": getattr(rule, "source_pattern", ""),
                    "forbidden_import_pattern": getattr(rule, "forbidden_import_pattern", ""),
                    "allowed_exceptions": getattr(rule, "allowed_exceptions", []),
                },
            )
        )
    return items


def interface_surfaces_to_registry_items(
    surfaces: list[Any] | None = None,
) -> list[RegistryItem]:
    items: list[RegistryItem] = []
    if surfaces is None:
        try:
            from umh.interface.surfaces import get_default_interface_surfaces

            surfaces = get_default_interface_surfaces()
        except Exception:
            return items
    for s in surfaces:
        stype = getattr(s, "surface_type", None)
        stype_str = stype.value if hasattr(stype, "value") else str(stype or "unknown")
        status_val = getattr(s, "status", None)
        status_str = (
            status_val.value if hasattr(status_val, "value") else str(status_val or "unknown")
        )
        mapped = (
            RegistryItemStatus.ACTIVE
            if status_str == "available"
            else RegistryItemStatus.REGISTERED
        )
        items.append(
            RegistryItem(
                item_id=f"isrf_{getattr(s, 'surface_id', '')}",
                registry_type=RegistryType.INTERFACE_SURFACE,
                name=getattr(s, "name", ""),
                description=f"Interface surface: {stype_str}",
                status=mapped,
                capabilities=getattr(s, "capabilities", []),
                tags=[
                    "interface",
                    f"surface_type:{stype_str}",
                    f"platform:{getattr(s, 'platform', 'unknown')}",
                ],
                version="84",
                source_module="umh.interface.surfaces",
                metadata={
                    "surface_type": stype_str,
                    "limitations": getattr(s, "limitations", []),
                    "supports_voice": getattr(s, "supports_voice", False),
                    "supports_global_overlay": getattr(s, "supports_global_overlay", False),
                },
            )
        )
    return items


def interface_commands_to_registry_items() -> list[RegistryItem]:
    items: list[RegistryItem] = []
    try:
        from umh.interface.commands import InterfaceCommandType

        for ct in InterfaceCommandType:
            if ct == InterfaceCommandType.UNKNOWN:
                continue
            items.append(
                RegistryItem(
                    item_id=f"icmd_{ct.value}",
                    registry_type=RegistryType.INTERFACE_COMMAND,
                    name=ct.value,
                    description=f"Interface command type: {ct.value}",
                    status=RegistryItemStatus.ACTIVE,
                    tags=["interface", "command_type"],
                    version="84",
                    source_module="umh.interface.commands",
                )
            )
    except Exception:
        pass
    return items


def voice_wave_states_to_registry_items() -> list[RegistryItem]:
    items: list[RegistryItem] = []
    try:
        from umh.interface.voice_wave import VoiceWaveState

        for vws in VoiceWaveState:
            if vws == VoiceWaveState.UNKNOWN:
                continue
            items.append(
                RegistryItem(
                    item_id=f"vws_{vws.value}",
                    registry_type=RegistryType.VOICE_WAVE_STATE,
                    name=vws.value,
                    description=f"Voice wave state: {vws.value}",
                    status=RegistryItemStatus.ACTIVE,
                    tags=["interface", "voice_wave"],
                    version="84",
                    source_module="umh.interface.voice_wave",
                )
            )
    except Exception:
        pass
    return items


def council_roles_to_registry_items(
    roles: list[Any] | None = None,
) -> list[RegistryItem]:
    if roles is None:
        try:
            from umh.council.roles import get_default_council_roles

            roles = get_default_council_roles()
        except Exception:
            return []

    items: list[RegistryItem] = []
    for role in roles:
        role_id = getattr(role, "role_id", "")
        name = getattr(role, "name", role_id)
        rt = getattr(role, "role_type", None)
        rt_str = rt.value if hasattr(rt, "value") else str(rt or "")
        domain = getattr(role, "domain", None)
        domain_str = domain.value if hasattr(domain, "value") else str(domain or "")

        items.append(
            RegistryItem(
                item_id=f"cr_{role_id}",
                registry_type=RegistryType.COUNCIL_ROLE,
                name=name,
                description=getattr(role, "perspective_lens", "")[:200],
                status=RegistryItemStatus.ACTIVE,
                tags=["council", "role", f"type:{rt_str}", f"domain:{domain_str}"],
                version="85",
                source_module="umh.council.roles",
                metadata={
                    "role_type": rt_str,
                    "domain": domain_str,
                    "weight": getattr(role, "weight", 1.0),
                },
            )
        )
    return items


def command_center_sections_to_registry_items() -> list[RegistryItem]:
    items: list[RegistryItem] = []
    try:
        from umh.interface.command_center import CommandCenterSection

        for sec in CommandCenterSection:
            if sec == CommandCenterSection.UNKNOWN:
                continue
            items.append(
                RegistryItem(
                    item_id=f"ccs_{sec.value}",
                    registry_type=RegistryType.COMMAND_CENTER_SECTION,
                    name=sec.value,
                    description=f"Command Center section: {sec.value}",
                    status=RegistryItemStatus.ACTIVE,
                    tags=["interface", "command_center"],
                    version="84",
                    source_module="umh.interface.command_center",
                )
            )
    except Exception:
        pass
    return items
