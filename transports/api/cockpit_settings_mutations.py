"""Settings Mutation Runtime — single entry point for all settings mutations.

UI, chat, and voice paths all call these functions. No separate shortcuts.

Pipeline per mutation:
  1. Validate (type, enum)
  2. Constrain (domain rules)
  3. Warn (risky changes)
  4. Approval gate (if authority-impacting)
  5. Persist (config file via settings_persistence)
  6. Apply (mutate runtime dicts)
  7. Audit (emit event)
  8. Return MutationResult with applied_state

UMH transport layer.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class MutationResult:
    ok: bool
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    audit_event: dict[str, Any] | None = None
    requires_approval: bool = False
    approval_reason: str = ""
    applied_state: dict[str, Any] | None = None


# ── Model Routing Mutations ────────────────────────────────────────


def toggle_provider(provider_key: str, enabled: bool) -> MutationResult:
    """Enable or disable a model provider."""
    from adapters.models.model_router import MODEL_REGISTRY
    from substrate.state.config.settings_persistence import load_settings, save_settings
    from transports.api.cockpit_audit import emit_settings_audit

    if provider_key not in MODEL_REGISTRY:
        return MutationResult(ok=False, errors=[f"Unknown provider: {provider_key}"])

    config = MODEL_REGISTRY[provider_key]
    old_value = config.available
    warnings: list[str] = []

    if not enabled:
        from adapters.models.model_router import ROLE_SLOTS, ROLE_FAILOVER
        from substrate.contracts.agent_types import ProviderRole

        for role, slot_key in ROLE_SLOTS.items():
            if slot_key == provider_key:
                failover = ROLE_FAILOVER.get(role)
                if failover and failover in MODEL_REGISTRY and MODEL_REGISTRY[failover].available:
                    warnings.append(f"Failover {failover} will take over {role.value}")
                else:
                    warnings.append(f"No failover for {role.value} — disabling may break routing")

    config.available = enabled
    config.status_reason = "healthy" if enabled else "disabled"

    overrides = load_settings("model_routing")
    if "providers" not in overrides:
        overrides["providers"] = {}
    overrides["providers"][provider_key] = {
        "available": enabled,
        "status_reason": config.status_reason,
    }
    save_settings("model_routing", overrides)

    audit = emit_settings_audit(
        action="toggle_provider",
        target=provider_key,
        old_value={"available": old_value},
        new_value={"available": enabled},
        domain="model_routing",
        constraint_warnings=warnings,
    )

    return MutationResult(
        ok=True,
        warnings=warnings,
        audit_event=audit,
        applied_state={
            "provider": provider_key,
            "available": enabled,
            "status_reason": config.status_reason,
        },
    )


def set_purpose_chain(purpose: str, roles: list[str]) -> MutationResult:
    """Set the role chain for a purpose."""
    from adapters.models.model_router import PURPOSE_ROUTING
    from substrate.contracts.agent_types import ProviderRole
    from substrate.state.config.settings_persistence import load_settings, save_settings
    from transports.api.cockpit_audit import emit_settings_audit

    if purpose not in PURPOSE_ROUTING:
        return MutationResult(ok=False, errors=[f"Unknown purpose: {purpose}"])

    if not roles:
        return MutationResult(ok=False, errors=["Purpose chain cannot be empty"])

    valid_roles = {r.value for r in ProviderRole}
    invalid = [r for r in roles if r not in valid_roles]
    if invalid:
        return MutationResult(ok=False, errors=[f"Invalid roles: {invalid}"])

    old_chain = [r.value for r in PURPOSE_ROUTING[purpose]]
    new_role_objs = [ProviderRole(r) for r in roles]
    PURPOSE_ROUTING[purpose] = new_role_objs

    overrides = load_settings("model_routing")
    if "purpose_routing" not in overrides:
        overrides["purpose_routing"] = {}
    overrides["purpose_routing"][purpose] = roles
    save_settings("model_routing", overrides)

    audit = emit_settings_audit(
        action="set_purpose_chain",
        target=purpose,
        old_value=old_chain,
        new_value=roles,
        domain="model_routing",
    )

    return MutationResult(
        ok=True,
        audit_event=audit,
        applied_state={"purpose": purpose, "chain": roles},
    )


def set_role_slot(role: str, provider_key: str) -> MutationResult:
    """Assign a provider to a role slot."""
    from adapters.models.model_router import MODEL_REGISTRY, ROLE_SLOTS
    from substrate.contracts.agent_types import ProviderRole
    from substrate.state.config.settings_persistence import load_settings, save_settings
    from transports.api.cockpit_audit import emit_settings_audit

    valid_roles = {r.value for r in ProviderRole}
    if role not in valid_roles:
        return MutationResult(ok=False, errors=[f"Invalid role: {role}"])

    if provider_key not in MODEL_REGISTRY and provider_key != "cc_sdk":
        return MutationResult(ok=False, errors=[f"Unknown provider: {provider_key}"])

    role_enum = ProviderRole(role)
    old_key = ROLE_SLOTS.get(role_enum, "")
    warnings: list[str] = []

    if role == "strategic_brain":
        warnings.append("Changing STRATEGIC_BRAIN affects CEO-level decisions — confirm intent")

    ROLE_SLOTS[role_enum] = provider_key

    overrides = load_settings("model_routing")
    if "role_slots" not in overrides:
        overrides["role_slots"] = {}
    overrides["role_slots"][role] = provider_key
    save_settings("model_routing", overrides)

    audit = emit_settings_audit(
        action="set_role_slot",
        target=role,
        old_value=old_key,
        new_value=provider_key,
        domain="model_routing",
        constraint_warnings=warnings,
    )

    return MutationResult(
        ok=True,
        warnings=warnings,
        audit_event=audit,
        requires_approval=role == "strategic_brain",
        approval_reason="STRATEGIC_BRAIN change affects CEO-level decisions"
        if role == "strategic_brain"
        else "",
        applied_state={"role": role, "provider": provider_key},
    )


# ── Governance Mutations ───────────────────────────────────────────


GOVERNANCE_CONSTRAINTS: dict[str, set[str]] = {
    "FINANCIAL": {"AUTONOMOUS"},
    "SECURITY_SENSITIVE": {"AUTONOMOUS"},
}

AUTHORITY_ORDER = ["AUTONOMOUS", "NOTIFY", "APPROVE", "ESCALATE", "DENY"]


def update_governance_policy(risk_class_name: str, authority_name: str) -> MutationResult:
    """Update a single governance policy entry."""
    from substrate.governance.authority import AuthorityLevel
    from substrate.governance.policy_engine import _DEFAULT_POLICY
    from substrate.governance.risk_classes import RiskClass
    from substrate.state.config.settings_persistence import load_settings, save_settings
    from transports.api.cockpit_audit import emit_settings_audit

    try:
        rc = RiskClass[risk_class_name]
    except KeyError:
        return MutationResult(ok=False, errors=[f"Unknown risk class: {risk_class_name}"])

    try:
        auth = AuthorityLevel[authority_name]
    except KeyError:
        return MutationResult(ok=False, errors=[f"Unknown authority level: {authority_name}"])

    blocked = GOVERNANCE_CONSTRAINTS.get(risk_class_name, set())
    if authority_name in blocked:
        return MutationResult(
            ok=False,
            errors=[f"{risk_class_name} cannot be set to {authority_name}"],
        )

    old_auth = _DEFAULT_POLICY.get(rc, AuthorityLevel.DENY)
    old_name = old_auth.name
    warnings: list[str] = []

    old_idx = AUTHORITY_ORDER.index(old_name) if old_name in AUTHORITY_ORDER else 4
    new_idx = AUTHORITY_ORDER.index(authority_name) if authority_name in AUTHORITY_ORDER else 4
    if new_idx < old_idx:
        warnings.append(f"Lowering authority for {risk_class_name}: {old_name} → {authority_name}")

    _DEFAULT_POLICY[rc] = auth

    overrides = load_settings("governance_policy")
    overrides[risk_class_name] = authority_name
    save_settings("governance_policy", overrides)

    audit = emit_settings_audit(
        action="update_governance_policy",
        target=risk_class_name,
        old_value=old_name,
        new_value=authority_name,
        domain="governance",
        constraint_warnings=warnings,
    )

    return MutationResult(
        ok=True,
        warnings=warnings,
        audit_event=audit,
        applied_state={"risk_class": risk_class_name, "authority": authority_name},
    )


# ── Device Mutations ───────────────────────────────────────────────


def update_device_role(device_id: str, role: str) -> MutationResult:
    """Update a device's role with constraint checking."""
    import json
    import os

    from substrate.organism.device_registry_writer import _read_registry, update_device
    from substrate.state.config.settings_persistence import DEVICE_ROLE_CONSTRAINTS
    from transports.api.cockpit_audit import emit_settings_audit

    _root = os.environ.get("UMH_ROOT") or "/opt/OS"
    registry_path = os.path.join(_root, "infra", "device_registry.json")
    devices = _read_registry(registry_path)
    device = next((d for d in devices if d.get("id") == device_id), None)

    if device is None:
        return MutationResult(ok=False, errors=[f"Device '{device_id}' not found"])

    if role not in ("controller", "executor", "orchestrator"):
        return MutationResult(ok=False, errors=[f"Invalid role: {role}"])

    device_type = device.get("device_type", "unknown")
    constraints = DEVICE_ROLE_CONSTRAINTS.get(device_type, DEVICE_ROLE_CONSTRAINTS["unknown"])
    allowed = constraints["allowed"]

    if role not in allowed:
        reason = constraints.get(
            "reason", f"{device_type} devices cannot be assigned role '{role}'"
        )
        return MutationResult(ok=False, errors=[reason])

    old_role = device.get("role", "controller")
    warnings: list[str] = []
    requires_approval = False
    approval_reason = ""

    if role == "executor":
        warnings.append("This grants compute execution authority")
        requires_approval = True
        approval_reason = "Executor role grants compute execution authority"
    elif role == "orchestrator":
        warnings.append(
            "This grants orchestration authority — only one orchestrator should be active"
        )
        requires_approval = True
        approval_reason = "Orchestrator role grants full orchestration authority"

    old_values = update_device(device_id, {"role": role}, registry_path=registry_path)

    audit = emit_settings_audit(
        action="update_device_role",
        target=device_id,
        old_value={"role": old_role},
        new_value={"role": role},
        domain="device",
        constraint_warnings=warnings,
    )

    return MutationResult(
        ok=True,
        warnings=warnings,
        audit_event=audit,
        requires_approval=requires_approval,
        approval_reason=approval_reason,
        applied_state={"device_id": device_id, "role": role, "role_status": "needs_review"},
    )


def update_device_fields(device_id: str, fields: dict[str, Any]) -> MutationResult:
    """Update arbitrary fields on a device."""
    import os

    from substrate.organism.device_registry_writer import _read_registry, update_device
    from transports.api.cockpit_audit import emit_settings_audit

    _root = os.environ.get("UMH_ROOT") or "/opt/OS"
    registry_path = os.path.join(_root, "infra", "device_registry.json")
    devices = _read_registry(registry_path)
    device = next((d for d in devices if d.get("id") == device_id), None)

    if device is None:
        return MutationResult(ok=False, errors=[f"Device '{device_id}' not found"])

    if "role" in fields:
        return update_device_role(device_id, fields["role"])

    old_values = update_device(device_id, fields, registry_path=registry_path)

    audit = emit_settings_audit(
        action="update_device_fields",
        target=device_id,
        old_value=old_values,
        new_value=fields,
        domain="device",
    )

    return MutationResult(
        ok=True, audit_event=audit, applied_state={"device_id": device_id, **fields}
    )


# ── Startup: Apply Persisted Overrides ─────────────────────────────


def apply_persisted_overrides() -> None:
    """Load persisted settings and apply to runtime. Called at startup."""
    _apply_model_routing_overrides()
    _apply_governance_overrides()
    logger.info("Persisted settings overrides applied")


def _apply_model_routing_overrides() -> None:
    from adapters.models.model_router import MODEL_REGISTRY, PURPOSE_ROUTING, ROLE_SLOTS
    from substrate.contracts.agent_types import ProviderRole
    from substrate.state.config.settings_persistence import load_settings

    overrides = load_settings("model_routing")
    if not overrides:
        return

    providers = overrides.get("providers", {})
    for key, vals in providers.items():
        if key in MODEL_REGISTRY:
            if "available" in vals:
                MODEL_REGISTRY[key].available = vals["available"]
            if "status_reason" in vals:
                MODEL_REGISTRY[key].status_reason = vals["status_reason"]

    purpose_overrides = overrides.get("purpose_routing", {})
    for purpose, roles in purpose_overrides.items():
        if purpose in PURPOSE_ROUTING:
            try:
                PURPOSE_ROUTING[purpose] = [ProviderRole(r) for r in roles]
            except ValueError:
                logger.warning("Invalid role in persisted purpose_routing[%s]", purpose)

    role_slot_overrides = overrides.get("role_slots", {})
    for role_str, provider_key in role_slot_overrides.items():
        try:
            role_enum = ProviderRole(role_str)
            ROLE_SLOTS[role_enum] = provider_key
        except ValueError:
            logger.warning("Invalid role in persisted role_slots: %s", role_str)


def _apply_governance_overrides() -> None:
    from substrate.governance.authority import AuthorityLevel
    from substrate.governance.policy_engine import _DEFAULT_POLICY
    from substrate.governance.risk_classes import RiskClass
    from substrate.state.config.settings_persistence import load_settings

    overrides = load_settings("governance_policy")
    if not overrides:
        return

    for rc_name, auth_name in overrides.items():
        try:
            rc = RiskClass[rc_name]
            auth = AuthorityLevel[auth_name]
            _DEFAULT_POLICY[rc] = auth
        except KeyError:
            logger.warning("Invalid governance override: %s=%s", rc_name, auth_name)
