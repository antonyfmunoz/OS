"""Work Archetype resolution — deterministic work-shape → policy binding.

Plan §7 (Wave 1). An archetype binds one recognizable shape of work to its
canonical defaults: responsible Role, required Skills (versioned
SkillRequirementRefs, §23.4), workflow template, tool policy, environment
class, governance policy, independent verification role, proof contract, and
expected artifacts.

Deterministic law: equivalent work + scope → the same archetype and the same
policy set. Contextual overrides are explicit, attributed, and reasoned —
never silent. No worker/model/device binding exists in canonical Task
identity (that is Wave 2 scheduling).

This module extends the EXISTING canonical registries (role_contracts seeds,
template homes) rather than creating a rival registry: archetype entries
reference role_contract ids and template names; they do not redefine them.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

from substrate.contracts.work_context import SkillRequirementRef, WorkScope

# ── Result record ────────────────────────────────────────────────────────────


@dataclass
class WorkArchetypeResolution:
    """The resolved archetype + policy set for one unit of work."""

    archetype_id: str = ""
    archetype_version: int = 1
    match_evidence: list[str] = field(default_factory=list)
    default_role_contract_id: str = ""
    required_skill_refs: list[dict[str, Any]] = field(default_factory=list)
    workflow_template: str = ""
    tool_policy: list[str] = field(default_factory=list)
    context_policy: str = ""
    environment_class: str = ""
    governance_policy: dict[str, Any] = field(default_factory=dict)
    verification_role_contract_id: str = ""
    proof_contract: dict[str, Any] = field(default_factory=dict)
    expected_artifacts: list[str] = field(default_factory=list)
    performance_expectations: dict[str, Any] = field(default_factory=dict)
    overrides: list[dict[str, str]] = field(default_factory=list)
    unresolved_requirement_gaps: list[str] = field(default_factory=list)
    deterministic: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> WorkArchetypeResolution:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ── Archetype table (data, not a new registry technology) ────────────────────
# Role ids reference SEED_ROLE_CONTRACTS in substrate.organism.role_contracts.
# Skill refs are versioned SkillRequirementRefs; semantic types per §7.


def _skill(
    skill_id: str, semantic_type: str, role: str, mastery: str = "practitioner"
) -> dict[str, Any]:
    return SkillRequirementRef(
        skill_id=skill_id,
        version_constraint=">=1",
        semantic_type=semantic_type,
        minimum_maturity="qualified",
        minimum_mastery=mastery,
        responsible_role_contract_id=role,
    ).to_dict()


_ARCHETYPES: dict[str, dict[str, Any]] = {
    "development": {
        "patterns": r"\b(build|implement|develop|refactor|migrate|fix|deploy|integrate|ship|code|api|schema|service|frontend|backend|subsystem)\b",
        "default_role": "role-impl-op",
        "verification_role": "role-verify-op",
        "workflow_template": "development-plan-execute-verify",
        "tools": ["repository", "test_runner", "typecheck"],
        "environment_class": "isolated_worktree",
        "skills": [
            _skill("software-implementation", "competency", "role-impl-op"),
            _skill("verification-discipline", "procedure", "role-verify-op"),
        ],
        "artifacts": ["technical_design", "test_strategy", "deploy_rollback_plan"],
        "proof": {"required": ["tests_green", "import_check", "review"]},
    },
    "research": {
        "patterns": r"\b(research|investigate|analy[sz]e|audit|map|survey|compare|study|assess|diagnos)\w*\b",
        "default_role": "role-research-op",
        "verification_role": "role-verify-op",
        "workflow_template": "research-sweep-synthesize",
        "tools": ["search", "read", "graph_query"],
        "environment_class": "read_only",
        "skills": [_skill("evidence-synthesis", "competency", "role-research-op")],
        "artifacts": ["findings_report"],
        "proof": {"required": ["sources_cited", "coverage_stated"]},
    },
    "content": {
        "patterns": r"\b(write|draft|post|article|newsletter|script|copy|brand|content|video|thumbnail)\b",
        "default_role": "role-impl-op",
        "verification_role": "role-verify-op",
        "workflow_template": "content-draft-review-publish",
        "tools": ["editor"],
        "environment_class": "workspace",
        "skills": [_skill("content-production", "competency", "role-impl-op")],
        "artifacts": ["content_draft"],
        "proof": {"required": ["review_pass"]},
    },
    "operations": {
        "patterns": r"\b(restart|rotate|clean|monitor|backup|provision|configure|upgrade|patch|operate|maintain)\b",
        "default_role": "role-impl-op",
        "verification_role": "role-verify-op",
        "workflow_template": "ops-change-verify",
        "tools": ["shell_gated", "docker"],
        "environment_class": "governed_runtime",
        "skills": [_skill("runtime-operations", "procedure", "role-impl-op")],
        "artifacts": ["runbook_entry"],
        "proof": {"required": ["healthy_after_change"]},
    },
    "outreach": {
        "patterns": r"\b(outreach|lead|prospect|email\s+campaign|follow[- ]up|sales|pitch|client)\b",
        "default_role": "role-impl-op",
        "verification_role": "role-verify-op",
        "workflow_template": "outreach-sequence",
        "tools": ["crm"],
        "environment_class": "workspace",
        "skills": [_skill("outreach-execution", "playbook", "role-impl-op")],
        "artifacts": ["outreach_log"],
        "proof": {"required": ["activity_recorded"]},
    },
}

_DEFAULT_ARCHETYPE = "development"

_GOVERNANCE_BY_TARGET_KIND: dict[str, dict[str, Any]] = {
    # §10 self-build vs projection-build — ONE archetype family, two
    # governance profiles selected by WorkScope.target_kind.
    "umh_substrate": {
        "profile": "self_build",
        "requires": [
            "anti_divergence_validation",
            "architecture_law_checks",
            "isolated_source_state",
            "commit_provenance",
            "independent_verification",
            "field_qualification",
            "owner_merge_authority",
            "rollback_path",
        ],
    },
    "projection": {
        "profile": "projection_build",
        "requires": [
            "contract_conformity",
            "tenant_isolation",
            "no_substrate_duplication",
            "projection_field_proof",
            "deployment_authority",
        ],
    },
}


def resolve_archetype(
    work_text: str,
    scope: WorkScope,
    overrides: list[dict[str, str]] | None = None,
) -> WorkArchetypeResolution:
    """Resolve the archetype + policy set for one unit of work.

    Deterministic: first archetype whose pattern matches, in fixed table
    order; no match → development default with the fallback recorded as
    match evidence. Overrides must carry attribution + reason; unreasoned
    overrides land in unresolved_requirement_gaps instead of applying.
    """
    text = (work_text or "").lower()
    chosen_id = _DEFAULT_ARCHETYPE
    evidence: list[str] = []
    for archetype_id, entry in _ARCHETYPES.items():
        match = re.search(entry["patterns"], text)
        if match:
            chosen_id = archetype_id
            evidence.append(f"pattern match: {match.group(0)!r} → {archetype_id}")
            break
    if not evidence:
        evidence.append(f"no pattern matched — canonical default {_DEFAULT_ARCHETYPE!r}")

    entry = _ARCHETYPES[chosen_id]
    governance = _GOVERNANCE_BY_TARGET_KIND.get(
        scope.target_kind, {"profile": "standard", "requires": ["governed_mutation_only"]}
    )
    if scope.target_kind:
        evidence.append(
            f"target_kind={scope.target_kind} → governance profile {governance['profile']}"
        )

    resolution = WorkArchetypeResolution(
        archetype_id=chosen_id,
        archetype_version=1,
        match_evidence=evidence,
        default_role_contract_id=entry["default_role"],
        required_skill_refs=[dict(s) for s in entry["skills"]],
        workflow_template=entry["workflow_template"],
        tool_policy=list(entry["tools"]),
        context_policy="bounded_context_frame",
        environment_class=entry["environment_class"],
        governance_policy=dict(governance),
        verification_role_contract_id=entry["verification_role"],
        proof_contract=dict(entry["proof"]),
        expected_artifacts=list(entry["artifacts"]),
        performance_expectations={"determinism": "same work+scope → same policy"},
    )

    for override in overrides or []:
        if override.get("field") and override.get("reason") and override.get("attributed_to"):
            resolution.overrides.append(dict(override))
        else:
            resolution.unresolved_requirement_gaps.append(
                f"override rejected (needs field+reason+attributed_to): {override!r}"
            )
    return resolution


# ── Skill-resolution law (Wave 1 planning validation, §7/§23.4) ──────────────


def validate_skill_requirements(
    skill_refs: list[dict[str, Any]],
    responsible_role: Any,
    verification_role_id: str = "",
) -> list[str]:
    """Validate role-bound Skill requirements at PLANNING time.

    Checks (Wave 1 — declared-compatibility only; worker mastery = Wave 2):
      - every ref is a structured, versioned SkillRequirementRef;
      - the responsible Role does not PROHIBIT the skill;
      - a non-empty permitted list must include the skill (empty = unrestricted);
      - minimum mastery is declared where the role declares a requirement;
      - the independent verifier role is distinct where one is required.
    Returns requirement-gap strings (empty = clean).
    """
    gaps: list[str] = []
    role_id = getattr(responsible_role, "role_id", "") if responsible_role else ""
    permitted = set(getattr(responsible_role, "permitted_skill_ids", []) or [])
    prohibited = set(getattr(responsible_role, "prohibited_skill_ids", []) or [])
    mastery_reqs = getattr(responsible_role, "skill_mastery_requirements", {}) or {}

    for raw in skill_refs:
        if not isinstance(raw, dict):
            gaps.append(f"bare skill reference prohibited: {raw!r}")
            continue
        ref = SkillRequirementRef.from_dict(raw)
        gaps.extend(ref.validate())
        if ref.skill_id in prohibited:
            gaps.append(f"skill {ref.skill_id!r} is PROHIBITED for role {role_id!r}")
        elif permitted and ref.skill_id not in permitted:
            gaps.append(f"skill {ref.skill_id!r} not permitted for role {role_id!r}")
        required_mastery = mastery_reqs.get(ref.skill_id, "")
        if required_mastery and not ref.minimum_mastery:
            gaps.append(
                f"skill {ref.skill_id!r}: role {role_id!r} requires mastery "
                f"{required_mastery!r} but the ref declares none"
            )
        if (
            ref.responsible_role_contract_id
            and role_id
            and ref.responsible_role_contract_id not in (role_id, verification_role_id)
        ):
            # A ref may be bound to the responsible role OR the independent
            # verifier role — any other binding is a requirement gap.
            gaps.append(
                f"skill {ref.skill_id!r} bound to role {ref.responsible_role_contract_id!r}, "
                f"not the responsible role {role_id!r}"
            )
        if (
            verification_role_id
            and ref.responsible_role_contract_id == verification_role_id
            and role_id == verification_role_id
        ):
            # Separation of duty: the verifier may not be the performer.
            gaps.append(
                f"verification role {verification_role_id!r} must be distinct from "
                f"the responsible role"
            )
    return gaps


__all__ = [
    "WorkArchetypeResolution",
    "resolve_archetype",
    "validate_skill_requirements",
]
