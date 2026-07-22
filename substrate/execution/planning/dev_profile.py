"""Development planning profile — artifact + production-readiness assessment.

Plan §10 (Wave 1). Applied per objective when the resolved archetype is
development-shaped. It produces ASSESSMENTS, never documents: every artifact
type and every production-readiness layer gets an explicit status — silence
is not an assessment. Missing REQUIRED artifacts become canonical Tasks; the
profile never generates a documentation corpus and never creates a rival
lifecycle or Task type.

UMH substrate subsystem. Instance-agnostic. Deterministic.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

from substrate.contracts.work_context import WorkScope

# ── Vocabulary ───────────────────────────────────────────────────────────────

ARTIFACT_TYPES: tuple[str, ...] = (
    "product_definition",
    "flows",
    "design_brief",
    "ux_spec",
    "architecture",
    "technical_design",
    "api_contracts",
    "data_schema_migration",
    "identity_authz_matrix",
    "threat_model",
    "infra_design",
    "engineering_plan",
    "test_strategy",
    "observability_plan",
    "deploy_rollback_plan",
    "field_qualification_plan",
    "runbook",
    "ai_system_spec",
    "analytics_plan",
)

ARTIFACT_STATUSES = ("required", "not_applicable", "inherited", "deferred")

PRODUCTION_LAYERS: tuple[str, ...] = (
    "layer_00_product_ux_architecture_acceptance",
    "layer_01_frontend",
    "layer_02_apis_backend",
    "layer_03_data",
    "layer_04_authn_authz",
    "layer_05_hosting",
    "layer_06_compute",
    "layer_07_vcs_ci_cd",
    "layer_08_security_secrets_tenancy_rls",
    "layer_09_rate_limiting",
    "layer_10_caching_cdn",
    "layer_11_load_scaling",
    "layer_12_observability",
    "layer_13_availability_backup_recovery_rollback",
)

CROSS_CUTTING: tuple[str, ...] = (
    "testing",
    "accessibility",
    "privacy",
    "compliance",
    "analytics",
    "feature_flags",
    "performance",
    "cost",
    "documentation",
    "ai_governance",
)

LAYER_STATUSES = (
    "required",
    "inherited",
    "existing_and_sufficient",
    "existing_but_deficient",
    "deferred",
    "not_applicable",
    "blocked",
    "verified",
)


@dataclass
class DevelopmentPlanningProfile:
    """The complete development assessment for one objective."""

    target_kind: str = ""  # umh_substrate | projection
    governance_profile: str = ""
    artifact_assessments: list[dict[str, Any]] = field(default_factory=list)
    layer_assessments: list[dict[str, Any]] = field(default_factory=list)
    cross_cutting_assessments: list[dict[str, Any]] = field(default_factory=list)
    software_target: dict[str, Any] = field(default_factory=dict)
    ai_native: dict[str, Any] = field(default_factory=dict)
    missing_required_artifacts: list[str] = field(default_factory=list)
    deterministic: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> DevelopmentPlanningProfile:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    def assert_complete(self) -> list[str]:
        """Every artifact type and layer must carry an explicit status."""
        errors: list[str] = []
        assessed_artifacts = {a["artifact_type"] for a in self.artifact_assessments}
        for artifact in ARTIFACT_TYPES:
            if artifact not in assessed_artifacts:
                errors.append(f"artifact not assessed: {artifact}")
        assessed_layers = {a["layer"] for a in self.layer_assessments}
        for layer in PRODUCTION_LAYERS:
            if layer not in assessed_layers:
                errors.append(f"layer not assessed: {layer}")
        assessed_cross = {a["item"] for a in self.cross_cutting_assessments}
        for item in CROSS_CUTTING:
            if item not in assessed_cross:
                errors.append(f"cross-cutting item not assessed: {item}")
        return errors


# ── Deterministic applicability signals ──────────────────────────────────────

_MULTI_TENANT_RE = re.compile(
    r"\b(multi-?tenant|tenant|saas|customer accounts?|rls)\b", re.IGNORECASE
)
_STATIC_RE = re.compile(r"\b(static|prototype|landing page|mock(up)?|demo page)\b", re.IGNORECASE)
_UI_RE = re.compile(
    r"\b(ui|frontend|panel|page|screen|cockpit|design|ux|web app|website)\b", re.IGNORECASE
)
_API_RE = re.compile(r"\b(api|endpoint|backend|service|route|webhook)\b", re.IGNORECASE)
_DATA_RE = re.compile(r"\b(schema|database|migration|table|store|jsonl|postgres)\b", re.IGNORECASE)
_AI_RE = re.compile(r"\b(agent|llm|model|prompt|ai|intelligence|assistant)\b", re.IGNORECASE)
_INFRA_HEAVY_RE = re.compile(
    r"\b(deploy|host|scal(e|ing)|infra|production|launch)\b", re.IGNORECASE
)

_SOFTWARE_TARGET_TABLE: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\b(iphone|android|mobile app|ios)\b", re.IGNORECASE), "mobile_app"),
    (re.compile(r"\b(desktop app|electron)\b", re.IGNORECASE), "desktop_app"),
    (re.compile(r"\b(cli|command[- ]line)\b", re.IGNORECASE), "cli"),
    (re.compile(r"\b(library|sdk|package)\b", re.IGNORECASE), "library"),
    (re.compile(r"\b(extension|plugin)\b", re.IGNORECASE), "extension"),
    (re.compile(r"\b(api|service|backend)\b", re.IGNORECASE), "service_api"),
    (re.compile(r"\b(website|web app|frontend|page|panel|cockpit)\b", re.IGNORECASE), "web_app"),
)


def build_development_profile(
    objective_text: str,
    scope: WorkScope,
    governance_profile: str = "",
) -> DevelopmentPlanningProfile:
    """Assess the minimum sufficient artifact set + all readiness layers.

    Deterministic keyword applicability. A static prototype gets the SAME
    layer list with explicit not_applicable statuses — no silent omission and
    no infrastructure theater. Tenancy/security/observability/recovery can
    only be not_applicable when the work demonstrably has no such surface.
    """
    text = objective_text or ""
    is_static = bool(_STATIC_RE.search(text))
    has_ui = bool(_UI_RE.search(text))
    has_api = bool(_API_RE.search(text)) and not is_static
    has_data = bool(_DATA_RE.search(text)) and not is_static
    has_ai = bool(_AI_RE.search(text))
    multi_tenant = bool(_MULTI_TENANT_RE.search(text))
    infra_heavy = bool(_INFRA_HEAVY_RE.search(text)) and not is_static

    profile = DevelopmentPlanningProfile(
        target_kind=scope.target_kind or "umh_substrate",
        governance_profile=governance_profile,
    )

    def _artifact(artifact_type: str, status: str, reason: str) -> None:
        profile.artifact_assessments.append(
            {
                "artifact_type": artifact_type,
                "status": status,
                "reason": reason,
                "existing_sources": [],
                "required_before_stage": "execution" if status == "required" else "",
                "validation_criteria": "reviewed and linked to Tasks"
                if status == "required"
                else "",
            }
        )
        if status == "required":
            profile.missing_required_artifacts.append(artifact_type)

    _artifact("product_definition", "inherited", "objective statement carries the product intent")
    _artifact(
        "flows",
        "required" if has_ui else "not_applicable",
        "UI surface present" if has_ui else "no UI surface",
    )
    _artifact(
        "design_brief",
        "required" if has_ui and not is_static else ("deferred" if has_ui else "not_applicable"),
        "UI needs design intent" if has_ui else "no UI surface",
    )
    _artifact(
        "ux_spec",
        "required" if has_ui and not is_static else "not_applicable",
        "interactive UI" if has_ui else "no UI surface",
    )
    _artifact(
        "architecture",
        "required" if not is_static else "not_applicable",
        "system change requires architecture fit" if not is_static else "static artifact",
    )
    _artifact(
        "technical_design",
        "required" if not is_static else "deferred",
        "implementation design needed" if not is_static else "static prototype",
    )
    _artifact(
        "api_contracts",
        "required" if has_api else "not_applicable",
        "API surface present" if has_api else "no API surface",
    )
    _artifact(
        "data_schema_migration",
        "required" if has_data else "not_applicable",
        "data model touched" if has_data else "no data surface",
    )
    _artifact(
        "identity_authz_matrix",
        "required" if (has_api or multi_tenant) else "not_applicable",
        "authenticated surface" if (has_api or multi_tenant) else "no auth surface",
    )
    _artifact(
        "threat_model",
        "required" if (multi_tenant or has_api) else "deferred",
        "external/tenant surface" if (multi_tenant or has_api) else "internal-only change",
    )
    _artifact(
        "infra_design",
        "required" if infra_heavy else "not_applicable",
        "deployment/scaling in scope" if infra_heavy else "no infra change",
    )
    _artifact(
        "engineering_plan",
        "required" if not is_static else "deferred",
        "multi-step build" if not is_static else "static prototype",
    )
    _artifact(
        "test_strategy",
        "required" if not is_static else "not_applicable",
        "behavior must be verified" if not is_static else "static artifact",
    )
    _artifact(
        "observability_plan",
        "required" if (has_api or infra_heavy) else "deferred",
        "runtime surface" if (has_api or infra_heavy) else "no runtime surface yet",
    )
    _artifact(
        "deploy_rollback_plan",
        "required" if infra_heavy else "deferred",
        "production deploy in scope" if infra_heavy else "no deploy in scope",
    )
    _artifact(
        "field_qualification_plan",
        "required" if infra_heavy else "deferred",
        "production claim requires field proof" if infra_heavy else "no production claim",
    )
    _artifact("runbook", "deferred", "operations doc follows first deploy")
    _artifact(
        "ai_system_spec",
        "required" if has_ai else "not_applicable",
        "AI-native components present" if has_ai else "no AI components",
    )
    _artifact(
        "analytics_plan",
        "deferred" if has_ui else "not_applicable",
        "measure after ship" if has_ui else "no user surface",
    )

    def _layer(layer: str, status: str, reason: str) -> None:
        profile.layer_assessments.append({"layer": layer, "status": status, "reason": reason})

    _layer(PRODUCTION_LAYERS[0], "required", "acceptance always assessed")
    _layer(
        PRODUCTION_LAYERS[1],
        "required" if has_ui else "not_applicable",
        "UI in scope" if has_ui else "no UI",
    )
    _layer(
        PRODUCTION_LAYERS[2],
        "required" if has_api else "not_applicable",
        "API in scope" if has_api else "no API",
    )
    _layer(
        PRODUCTION_LAYERS[3],
        "required" if has_data else "not_applicable",
        "data in scope" if has_data else "no data",
    )
    _layer(
        PRODUCTION_LAYERS[4],
        "required" if (has_api or multi_tenant) else "not_applicable",
        "auth surface" if (has_api or multi_tenant) else "no auth surface",
    )
    _layer(
        PRODUCTION_LAYERS[5],
        "required" if infra_heavy else "not_applicable",
        "hosting change" if infra_heavy else "no hosting change",
    )
    _layer(
        PRODUCTION_LAYERS[6],
        "required" if infra_heavy else "not_applicable",
        "compute change" if infra_heavy else "no compute change",
    )
    _layer(
        PRODUCTION_LAYERS[7],
        "required" if not is_static else "not_applicable",
        "CI/CD gates apply" if not is_static else "static artifact",
    )
    _layer(
        PRODUCTION_LAYERS[8],
        "required" if (multi_tenant or has_api or not is_static) else "not_applicable",
        "security/tenancy always explicit for running systems"
        if not is_static
        else "no running surface",
    )
    _layer(
        PRODUCTION_LAYERS[9],
        "required" if has_api else "not_applicable",
        "public API" if has_api else "no API",
    )
    _layer(
        PRODUCTION_LAYERS[10],
        "deferred" if has_ui else "not_applicable",
        "optimize after ship" if has_ui else "no content surface",
    )
    _layer(
        PRODUCTION_LAYERS[11],
        "deferred" if infra_heavy else "not_applicable",
        "scale after field proof" if infra_heavy else "no scaling surface",
    )
    _layer(
        PRODUCTION_LAYERS[12],
        "required" if (has_api or infra_heavy) else "not_applicable",
        "runtime observability" if (has_api or infra_heavy) else "no runtime surface",
    )
    _layer(
        PRODUCTION_LAYERS[13],
        "required" if (has_data or infra_heavy) else "not_applicable",
        "recovery/rollback for stateful/deployed work"
        if (has_data or infra_heavy)
        else "stateless static artifact",
    )

    for item in CROSS_CUTTING:
        if item == "testing":
            status, reason = (
                ("required", "verification is mandatory")
                if not is_static
                else ("not_applicable", "static artifact")
            )
        elif item == "ai_governance":
            status, reason = (
                ("required", "AI components governed")
                if has_ai
                else ("not_applicable", "no AI components")
            )
        elif item in ("privacy", "compliance"):
            status, reason = (
                ("required", "tenant data in scope")
                if multi_tenant
                else ("deferred", "no external tenant data yet")
            )
        else:
            status, reason = "deferred", "assessed, scheduled post-MVP of this objective"
        profile.cross_cutting_assessments.append({"item": item, "status": status, "reason": reason})

    target_type = ""
    for pattern, target in _SOFTWARE_TARGET_TABLE:
        if pattern.search(text):
            target_type = target
            break
    if target_type:
        profile.software_target = {
            "software_artifact_type": target_type,
            "target_platforms": ["web"] if target_type in ("web_app", "service_api") else [],
            "distribution_channels": [],
            "packaging_signing": "not_applicable"
            if target_type in ("web_app", "service_api")
            else "unassessed",
            "runtime_requirements": [],
            "toolchain_constraints": [],
            "deployment_targets": [],
            "update_rollback_mechanism": "deploy_rollback_plan" if infra_heavy else "",
        }

    if has_ai:
        profile.ai_native = {
            "model_routing": "adapters/models/model_router.py call_with_fallback",
            "prompt_instruction_architecture": "instruction-compilation seam",
            "context_compilation": "bounded ContextFrame",
            "memory_retrieval": "canonical memory subsystems",
            "agent_role_topology": "RoleContract-bound",
            "skill_assignments": "SkillRequirementRef (versioned)",
            "tools_permissions": "role tool policy",
            "workflow_design": "archetype workflow template",
            "evals": "deferred",
            "ai_observability": "deferred",
            "prompt_injection_defenses": "required",
            "cost_latency_budgets": "deferred",
            "fallback_behavior": "deterministic-first mandatory",
        }

    return profile


__all__ = [
    "ARTIFACT_STATUSES",
    "ARTIFACT_TYPES",
    "CROSS_CUTTING",
    "LAYER_STATUSES",
    "PRODUCTION_LAYERS",
    "DevelopmentPlanningProfile",
    "build_development_profile",
]
