"""Canonical work-context contracts — Wave 1 constitutional types.

These contracts are EMBEDDED in Conversation/Plan/Task artifacts — there is no
separate store for any of them. Each is a typed, serializable dataclass with a
single semantic meaning under the Convergence Law
(.claude/rules/convergence-law.md):

  - ``PrincipalContext``   — who is acting, within which tenant, under which
                             durable membership. Identity semantics:
                             principal_id (who acts) ≠ tenant_id (sovereign
                             boundary) ≠ membership_id (durable principal↔tenant
                             relationship) ≠ seat_id (commercial entitlement —
                             NEVER authority identity).
  - ``WorkScope``          — the first-class scope of a Plan or Task. Always a
                             typed field, never hidden in source_evidence.
  - ``WorkLineageContext`` — per-Task planning lineage (goal → objective → plan
                             → packet). Named ``*Context`` because the name
                             ``WorkLineage`` is already the canonical continuity
                             aggregate in ``substrate.organism.continuity_runtime``
                             (a DIFFERENT concept: objective→outcome→projection
                             history). Recorded in the convergence ledger.
  - ``EvidenceRef``        — typed provenance reference. Raw evidence stays in
                             source systems; artifacts persist bounded refs +
                             summaries. Evidence is provenance, NEVER mutation
                             authority.
  - ``SkillRequirementRef``— the ONLY new Skill-reference shape (§23.4). Bare
                             skill-id strings are prohibited in new artifacts.
  - ``WorkRequirements``   — one requirements envelope resolved by archetype
                             resolution; populates existing WorkPacket fields
                             first, adds only what is proven missing.

All types registered in ``substrate/canonical_types.py``.
UMH substrate subsystem. Instance-agnostic. No I/O in this module.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

# Migration status literals shared by legacy-derived identity/scope values.
MIGRATION_STATUS_LEGACY_DERIVED = "legacy_derived"
MIGRATION_STATUS_NATIVE = "native"


def _from_dict(cls: type, d: dict[str, Any]) -> Any:
    return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class PrincipalKind(str, Enum):
    """What kind of actor a principal is. Wave 1 uses HUMAN; enum future-proof."""

    HUMAN = "human"
    AGENT = "agent"
    SERVICE = "service"
    WORKLOAD = "workload"
    DEVICE = "device"


class EpistemicStatus(str, Enum):
    """How an evidence claim relates to observed reality."""

    OBSERVED = "observed"
    DECLARED = "declared"
    INFERRED = "inferred"
    SIMULATED = "simulated"
    DISPUTED = "disputed"
    SUPERSEDED = "superseded"
    UNKNOWN = "unknown"


class WorkAuthorityError(ValueError):
    """A work mutation was attempted without principal+tenant+membership."""


@dataclass
class PrincipalContext:
    """Authenticated actor identity for one operation.

    Authorization identity = principal_id + tenant_id + membership_id.
    seat_id is commercial passthrough only and confers no authority.
    Membership is NEVER derived from a browser session.
    """

    principal_id: str = ""
    principal_kind: str = PrincipalKind.HUMAN.value
    tenant_id: str = ""
    membership_id: str = ""
    seat_id: str = ""
    active_role_assignment_ids: list[str] = field(default_factory=list)
    delegation_chain_ids: list[str] = field(default_factory=list)
    authenticated_by: str = ""
    authority_source: str = ""
    authority_expiry: float = 0.0
    compatibility_origin: str = ""
    migration_status: str = MIGRATION_STATUS_NATIVE

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PrincipalContext:
        return _from_dict(cls, d)

    def has_work_authority(self) -> bool:
        return bool(self.principal_id and self.tenant_id and self.membership_id)

    def require_work_authority(self) -> None:
        """Fail closed: work mutations need principal + tenant + membership.

        Communication paths never call this — they answer safely without it.
        """
        if not self.has_work_authority():
            missing = [
                name
                for name, value in (
                    ("principal_id", self.principal_id),
                    ("tenant_id", self.tenant_id),
                    ("membership_id", self.membership_id),
                )
                if not value
            ]
            raise WorkAuthorityError(
                f"work mutation requires authenticated identity; missing: {missing}"
            )


@dataclass
class WorkScope:
    """First-class scope of a Plan or Task. tenant_id is mandatory.

    A Task's scope must be contained by its parent Plan's scope
    (``is_within``). Cross-tenant artifacts are prohibited in Wave 1.
    """

    tenant_id: str = ""
    primary_company_id: str = ""
    company_ids: list[str] = field(default_factory=list)
    project_ids: list[str] = field(default_factory=list)
    product_ids: list[str] = field(default_factory=list)
    projection_ids: list[str] = field(default_factory=list)
    workspace_ids: list[str] = field(default_factory=list)
    repository_ids: list[str] = field(default_factory=list)
    environment_ids: list[str] = field(default_factory=list)
    conversation_id: str = ""
    target_kind: str = ""  # e.g. umh_substrate | projection | external
    data_classification: str = ""
    visibility_scope: str = ""
    policy_refs: list[str] = field(default_factory=list)
    jurisdiction_refs: list[str] = field(default_factory=list)
    legacy_org_id: str = ""
    migration_status: str = MIGRATION_STATUS_NATIVE

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> WorkScope:
        return _from_dict(cls, d)

    def validate(self) -> None:
        if not self.tenant_id.strip():
            raise ValueError("WorkScope.tenant_id is mandatory and must be non-empty")

    _CONTAINED_LIST_FIELDS = (
        "company_ids",
        "project_ids",
        "product_ids",
        "projection_ids",
        "workspace_ids",
        "repository_ids",
        "environment_ids",
    )

    def is_within(self, parent: WorkScope) -> bool:
        """True when this (Task) scope is contained by the parent (Plan) scope.

        Same tenant always required. For each id-list dimension, a non-empty
        parent list bounds the child; an empty parent list means the parent
        did not constrain that dimension.
        """
        if not self.tenant_id or self.tenant_id != parent.tenant_id:
            return False
        for fname in self._CONTAINED_LIST_FIELDS:
            parent_ids = set(getattr(parent, fname))
            child_ids = set(getattr(self, fname))
            if parent_ids and not child_ids.issubset(parent_ids):
                return False
        if parent.primary_company_id and self.primary_company_id:
            company_universe = set(parent.company_ids) | {parent.primary_company_id}
            if self.primary_company_id not in company_universe:
                return False
        return True

    def scope_hash(self) -> str:
        """Deterministic hash of the scope's identity-bearing dimensions.

        Used by GoalRegistry idempotent create-or-reuse
        (tenant_id + objective identity key + scope hash).
        """
        payload = {
            "tenant_id": self.tenant_id,
            "primary_company_id": self.primary_company_id,
            "company_ids": sorted(self.company_ids),
            "project_ids": sorted(self.project_ids),
            "product_ids": sorted(self.product_ids),
            "projection_ids": sorted(self.projection_ids),
            "target_kind": self.target_kind,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:16]


@dataclass
class WorkLineageContext:
    """Per-Task planning lineage — where one Task sits in the work hierarchy.

    Lineage, not duplicated context: ids only, resolved through their
    canonical owners (GoalRegistry, PlanningStore, packet store).
    """

    goal_refs: list[str] = field(default_factory=list)
    objective_id: str = ""
    parent_objective_id: str = ""
    plan_record_id: str = ""
    parent_plan_record_id: str = ""
    parent_packet_id: str = ""
    decomposition_level: int = 0
    end_state_contribution: str = ""
    originating_intent_id: str = ""
    originating_conversation_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> WorkLineageContext:
        return _from_dict(cls, d)


@dataclass
class EvidenceRef:
    """Typed provenance reference to one piece of evidence in a source system.

    Evidence is provenance — it can never be a mutation authority. Raw
    evidence bytes stay in the source system; artifacts persist this bounded
    reference plus an extraction summary.
    """

    evidence_id: str = ""
    source_system: str = ""
    source_object_type: str = ""
    source_object_id: str = ""
    canonical_entity_id: str = ""
    locator: str = ""
    epistemic_status: str = EpistemicStatus.UNKNOWN.value
    observed_at: float = 0.0
    source_modified_at: float = 0.0
    freshness_status: str = ""
    confidence: float = 0.0
    content_hash: str = ""
    tenant_id: str = ""
    visibility_scope: str = ""
    extraction_summary: str = ""
    contradiction_refs: list[str] = field(default_factory=list)
    provenance_chain: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> EvidenceRef:
        return _from_dict(cls, d)


@dataclass
class SkillRequirementRef:
    """Versioned, role-bound Skill requirement (§23.4 — the ONLY new shape).

    Every ``required_skill_refs`` in new Wave 1 artifacts is a list of these.
    Candidate/unqualified Skill versions cannot satisfy a requirement;
    promotion never silently rewrites the refs on existing work.
    """

    skill_id: str = ""
    version_constraint: str = ""
    semantic_type: str = (
        ""  # competency|procedure|workflow|playbook|tool-instruction|prompt-package
    )
    minimum_maturity: str = ""
    minimum_mastery: str = ""
    qualification_profile_ref: str = ""
    responsible_role_contract_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SkillRequirementRef:
        return _from_dict(cls, d)

    def validate(self) -> list[str]:
        """Return validation errors (empty when the ref is well-formed)."""
        errors: list[str] = []
        if not self.skill_id.strip():
            errors.append("skill_id must be non-empty")
        if not self.version_constraint.strip():
            errors.append(f"skill {self.skill_id!r}: version_constraint is required")
        if not self.responsible_role_contract_id.strip():
            errors.append(f"skill {self.skill_id!r}: responsible_role_contract_id is required")
        return errors


@dataclass
class WorkRequirements:
    """One requirements envelope for a Task, resolved by archetype resolution.

    Populates EXISTING WorkPacket fields first (required_knowledge_models,
    templates, workflows, tools, role_contracts, output_contracts,
    approval_gates, validation_plan, rollback_plan); this envelope carries
    only what those fields do not.
    """

    work_archetype_ref: str = ""
    required_capability_ids: list[str] = field(default_factory=list)
    required_skill_refs: list[dict[str, Any]] = field(default_factory=list)
    environment_requirements: dict[str, Any] = field(default_factory=dict)
    governance_requirements: dict[str, Any] = field(default_factory=dict)
    separation_of_duty: list[dict[str, Any]] = field(default_factory=list)
    independent_verification_role_refs: list[str] = field(default_factory=list)
    proof_contract: dict[str, Any] = field(default_factory=dict)
    resource_constraints: dict[str, Any] = field(default_factory=dict)
    human_attention_boundary: str = ""
    # ── writable-path authority (first-class, NEVER evidence-derived) ────────
    # The workspace-relative paths this Task is AUTHORIZED to modify. This is a
    # MUTATION AUTHORITY: verification compares the actual diff against exactly
    # this persisted contract, and a change outside it fails the attempt before
    # any Proof is minted.
    #
    # It is a typed first-class field, never read from ``source_evidence``.
    # Evidence is provenance (see ``EvidenceRef``): it may record WHERE a scope
    # came from, but editing a descriptive evidence entry must never widen what
    # a worker may write. Keeping this on the requirements envelope means the
    # authority is persisted with the Task contract and travels with it.
    #
    # ``scope_declared`` distinguishes the two states a plain empty list cannot:
    #   * declared + empty  → ZERO paths authorized (a verifier's zero-diff
    #     contract) — a real, enforceable policy;
    #   * NOT declared      → no authority resolved → execution BLOCKS.
    # Without this flag, "nothing declared" and "nothing permitted" are the same
    # value, and a Task with no contract would silently inherit the strictest or
    # the loosest reading depending on the caller.
    writable_path_scope: list[str] = field(default_factory=list)
    scope_declared: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> WorkRequirements:
        return _from_dict(cls, d)

    def declare_writable_paths(self, paths: list[str]) -> WorkRequirements:
        """Set the authoritative writable-path scope (fluent).

        An explicitly empty list is a legal declaration meaning "no path may
        change" — which is why it also sets ``scope_declared``.
        """
        self.writable_path_scope = [str(p) for p in paths]
        self.scope_declared = True
        return self

    def validate_writable_path_scope(self) -> list[str]:
        """Structural errors in the declared scope (empty list = valid).

        Rejects policies that are not scopes at all. These are refused HERE, at
        the contract, so an unsafe scope can never be persisted onto a Task and
        later discovered only at verification time.
        """
        errors: list[str] = []
        if not self.scope_declared:
            return errors
        for raw in self.writable_path_scope:
            path = str(raw or "").strip()
            if not path:
                errors.append("empty writable path is not a scope")
                continue
            if path.startswith("/"):
                errors.append(f"absolute writable path {path!r} — must be workspace-relative")
            if path.startswith("~"):
                errors.append(f"home-relative writable path {path!r} — must be workspace-relative")
            # A Windows drive path survives the normalization below (the
            # backslash swap turns 'C:\\Windows' into a benign-looking relative
            # 'C:/Windows'), so it must be refused explicitly.
            if len(path) > 1 and path[1] == ":" and path[0].isalpha():
                errors.append(f"drive-qualified writable path {path!r} — must be workspace-relative")
            # Normalize with os.path.normpath, not a bare string strip: 'app/..'
            # and 'app//..' both COLLAPSE to '.' (whole workspace) yet passed the
            # string-only check, so an unsafe authority could be persisted and was
            # only refused later at verification. The contract's promise — refused
            # HERE so it can never be persisted — must actually hold.
            normalized = os.path.normpath(path.replace("\\", "/")).strip("/")
            if normalized in (".", ""):
                errors.append(
                    "whole-workspace scope ('.') is not a scope — the sandbox mount is a "
                    "containment boundary, not a mutation authority"
                )
            if normalized == ".." or normalized.startswith("../") or "/../" in normalized:
                errors.append(f"writable path {path!r} escapes the workspace")
        return errors

    def skill_refs(self) -> list[SkillRequirementRef]:
        return [SkillRequirementRef.from_dict(r) for r in self.required_skill_refs]

    def validate_skill_refs(self) -> list[str]:
        """Bare skill ids are prohibited — every ref must be a structured,
        versioned SkillRequirementRef that passes its own validation."""
        errors: list[str] = []
        for raw in self.required_skill_refs:
            if not isinstance(raw, dict):
                errors.append(f"bare skill reference {raw!r} prohibited — use SkillRequirementRef")
                continue
            errors.extend(SkillRequirementRef.from_dict(raw).validate())
        return errors


__all__ = [
    "MIGRATION_STATUS_LEGACY_DERIVED",
    "MIGRATION_STATUS_NATIVE",
    "EpistemicStatus",
    "EvidenceRef",
    "PrincipalContext",
    "PrincipalKind",
    "SkillRequirementRef",
    "WorkAuthorityError",
    "WorkLineageContext",
    "WorkRequirements",
    "WorkScope",
]
