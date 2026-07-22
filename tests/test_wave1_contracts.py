"""Wave 1 constitutional contract tests — work_context + principal resolution.

Covers the contract-level cores of plan §15 tests P (tenant/principal fail
closed), AA (membership stability), Y (scope never hidden / evidence never
authority), and §23.4 (SkillRequirementRef is the only skill-reference shape).
"""

from __future__ import annotations

import pytest

from substrate.contracts.principal_resolution import (
    derive_membership_id,
    derive_tenant_id,
    resolve_principal_context,
)
from substrate.contracts.work_context import (
    MIGRATION_STATUS_LEGACY_DERIVED,
    EpistemicStatus,
    EvidenceRef,
    PrincipalContext,
    SkillRequirementRef,
    WorkAuthorityError,
    WorkLineageContext,
    WorkRequirements,
    WorkScope,
)


class TestPrincipalContext:
    def test_work_authority_fails_closed_without_membership(self):
        ctx = PrincipalContext(principal_id="p1", tenant_id="t1", membership_id="")
        assert not ctx.has_work_authority()
        with pytest.raises(WorkAuthorityError) as exc:
            ctx.require_work_authority()
        assert "membership_id" in str(exc.value)

    def test_work_authority_fails_closed_without_tenant(self):
        ctx = PrincipalContext(principal_id="p1", tenant_id="", membership_id="m1")
        with pytest.raises(WorkAuthorityError):
            ctx.require_work_authority()

    def test_complete_identity_has_authority(self):
        ctx = PrincipalContext(principal_id="p1", tenant_id="t1", membership_id="m1")
        ctx.require_work_authority()  # no raise

    def test_seat_id_is_not_authority(self):
        ctx = PrincipalContext(principal_id="p1", tenant_id="t1", seat_id="seat-9")
        assert not ctx.has_work_authority()

    def test_roundtrip(self):
        ctx = PrincipalContext(principal_id="p1", tenant_id="t1", membership_id="m1")
        assert PrincipalContext.from_dict(ctx.to_dict()) == ctx


class TestPrincipalResolution:
    def test_membership_stable_across_calls(self):
        # Test AA core: same principal + tenant → same membership, always.
        assert derive_membership_id("u1", "tenant-a") == derive_membership_id("u1", "tenant-a")

    def test_membership_distinct_per_tenant(self):
        assert derive_membership_id("u1", "tenant-a") != derive_membership_id("u1", "tenant-b")

    def test_membership_empty_when_identity_incomplete(self):
        assert derive_membership_id("", "tenant-a") == ""
        assert derive_membership_id("u1", "") == ""

    def test_tenant_derivation_prefix_stable(self):
        assert derive_tenant_id("org1") == "tenant-org1"
        assert derive_tenant_id("tenant-org1") == "tenant-org1"
        assert derive_tenant_id("") == ""

    def test_resolution_is_legacy_derived_and_deterministic(self, monkeypatch):
        monkeypatch.delenv("UMH_USER_ID", raising=False)
        monkeypatch.delenv("UMH_ORG_ID", raising=False)
        monkeypatch.delenv("EOS_ORG_ID", raising=False)
        a = resolve_principal_context(user_id="u1", org_id="org1")
        b = resolve_principal_context(user_id="u1", org_id="org1")
        assert a.migration_status == MIGRATION_STATUS_LEGACY_DERIVED
        assert a.membership_id and a.membership_id == b.membership_id
        assert a.tenant_id == "tenant-org1"
        a.require_work_authority()

    def test_unknown_identity_fails_closed_for_work(self, monkeypatch):
        monkeypatch.delenv("UMH_USER_ID", raising=False)
        monkeypatch.delenv("UMH_ORG_ID", raising=False)
        monkeypatch.delenv("EOS_ORG_ID", raising=False)
        ctx = resolve_principal_context()
        with pytest.raises(WorkAuthorityError):
            ctx.require_work_authority()


class TestWorkScope:
    def test_tenant_mandatory(self):
        with pytest.raises(ValueError):
            WorkScope(tenant_id="  ").validate()
        WorkScope(tenant_id="t1").validate()  # no raise

    def test_task_scope_within_plan_scope(self):
        plan = WorkScope(tenant_id="t1", project_ids=["p1", "p2"], company_ids=["c1"])
        task = WorkScope(tenant_id="t1", project_ids=["p1"], company_ids=["c1"])
        assert task.is_within(plan)

    def test_cross_tenant_rejected(self):
        plan = WorkScope(tenant_id="t1")
        assert not WorkScope(tenant_id="t2").is_within(plan)
        assert not WorkScope(tenant_id="").is_within(plan)

    def test_task_scope_exceeding_plan_rejected(self):
        plan = WorkScope(tenant_id="t1", project_ids=["p1"])
        task = WorkScope(tenant_id="t1", project_ids=["p1", "p3"])
        assert not task.is_within(plan)

    def test_unconstrained_parent_dimension_admits_child(self):
        plan = WorkScope(tenant_id="t1")  # no project constraint
        task = WorkScope(tenant_id="t1", project_ids=["p9"])
        assert task.is_within(plan)

    def test_scope_hash_deterministic_and_order_insensitive(self):
        a = WorkScope(tenant_id="t1", project_ids=["p2", "p1"])
        b = WorkScope(tenant_id="t1", project_ids=["p1", "p2"])
        c = WorkScope(tenant_id="t2", project_ids=["p1", "p2"])
        assert a.scope_hash() == b.scope_hash()
        assert a.scope_hash() != c.scope_hash()

    def test_scope_is_first_class_typed_fields(self):
        # Test Y core: scope lives in typed fields, round-trips losslessly —
        # never a blob folded into source_evidence.
        scope = WorkScope(tenant_id="t1", legacy_org_id="org1", target_kind="projection")
        restored = WorkScope.from_dict(scope.to_dict())
        assert restored == scope
        assert restored.tenant_id == "t1"


class TestEvidenceRef:
    def test_epistemic_status_values(self):
        for status in EpistemicStatus:
            ref = EvidenceRef(evidence_id="e1", epistemic_status=status.value)
            assert EvidenceRef.from_dict(ref.to_dict()).epistemic_status == status.value

    def test_default_status_unknown(self):
        assert EvidenceRef().epistemic_status == EpistemicStatus.UNKNOWN.value

    def test_from_dict_ignores_unknown_keys(self):
        ref = EvidenceRef.from_dict({"evidence_id": "e1", "not_a_field": 1})
        assert ref.evidence_id == "e1"

    def test_evidence_has_no_mutation_surface(self):
        # Test Y core: EvidenceRef is pure provenance — no write/apply/commit
        # methods exist on the type.
        forbidden = [
            n for n in dir(EvidenceRef) if n in ("apply", "commit", "write", "mutate", "save")
        ]
        assert forbidden == []


class TestWorkLineageContext:
    def test_roundtrip_and_distinct_from_continuity_worklineage(self):
        from substrate.organism.continuity_runtime import WorkLineage

        lineage = WorkLineageContext(
            objective_id="goal-abc", plan_record_id="opr-1", decomposition_level=2
        )
        assert WorkLineageContext.from_dict(lineage.to_dict()) == lineage
        # Different concepts, different types — the continuity aggregate must
        # not be the same class as the per-Task planning lineage.
        assert WorkLineageContext is not WorkLineage
        assert "lineage_id" not in WorkLineageContext.__dataclass_fields__


class TestSkillRequirementRef:
    def test_valid_ref_passes(self):
        ref = SkillRequirementRef(
            skill_id="skill-x",
            version_constraint=">=1.0",
            semantic_type="procedure",
            responsible_role_contract_id="role-dev",
        )
        assert ref.validate() == []

    def test_unversioned_ref_rejected(self):
        ref = SkillRequirementRef(skill_id="skill-x", responsible_role_contract_id="r1")
        errors = ref.validate()
        assert any("version_constraint" in e for e in errors)

    def test_role_unbound_ref_rejected(self):
        ref = SkillRequirementRef(skill_id="skill-x", version_constraint="1.0")
        errors = ref.validate()
        assert any("responsible_role_contract_id" in e for e in errors)

    def test_bare_skill_ids_prohibited_in_requirements(self):
        # §23.4: bare skill-id strings are prohibited in new artifacts.
        reqs = WorkRequirements(required_skill_refs=["bare-skill-id"])  # type: ignore[list-item]
        errors = reqs.validate_skill_refs()
        assert any("bare skill reference" in e for e in errors)

    def test_structured_refs_validate_through_requirements(self):
        reqs = WorkRequirements(
            required_skill_refs=[
                SkillRequirementRef(
                    skill_id="s1",
                    version_constraint="1.x",
                    responsible_role_contract_id="role-1",
                ).to_dict()
            ]
        )
        assert reqs.validate_skill_refs() == []
        assert [r.skill_id for r in reqs.skill_refs()] == ["s1"]


class TestCanonicalRegistration:
    def test_all_wave1_contracts_registered(self):
        from substrate.canonical_types import CANONICAL_TYPES

        for name in (
            "PrincipalContext",
            "PrincipalKind",
            "EpistemicStatus",
            "WorkScope",
            "WorkLineageContext",
            "EvidenceRef",
            "SkillRequirementRef",
            "WorkRequirements",
        ):
            assert CANONICAL_TYPES.get(name) == ["substrate.contracts.work_context"], name

    def test_worklineage_remains_owned_by_continuity_runtime(self):
        from substrate.canonical_types import CANONICAL_TYPES

        assert CANONICAL_TYPES["WorkLineage"] == ["substrate.organism.continuity_runtime"]
