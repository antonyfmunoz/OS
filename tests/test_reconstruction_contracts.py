"""Tests for reconstruction record contracts."""

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(os.environ.get("UMH_ROOT", Path(__file__).resolve().parents[1])).resolve()
sys.path.insert(0, str(REPO_ROOT))

from substrate.understanding.reconstruction import contracts as C


class TestImportProvenance:
    def test_module_imported_from_active_root(self):
        """The module under test comes from THIS tree, never a stale /opt/OS."""
        mod_file = Path(C.__file__).resolve()
        assert str(mod_file).startswith(str(REPO_ROOT)), (
            f"contracts imported from {mod_file}, expected under {REPO_ROOT}"
        )


class TestContracts:
    def test_stable_acquisition_id_deterministic_and_namespaced(self):
        a = C.SourceRecord(
            subject_path="x.py",
            source_kind="repository_file",
            modality="code",
            activity_id="a1",
            run_id="r",
            source_content_hash="h",
        )
        b = C.SourceRecord(
            subject_path="x.py",
            source_kind="repository_file",
            modality="code",
            activity_id="a1",
            run_id="r",
            source_content_hash="h",
        )
        assert a.id == b.id and a.id.startswith("source:")

    def test_source_identity_vs_acquisition_identity(self):
        """source_identity_id is stable ACROSS runs; the acquisition record id
        is run/activity scoped (V4.1 correction 19)."""
        a = C.SourceRecord(
            subject_path="x.py",
            source_kind="repository_file",
            modality="code",
            activity_id="a1",
            run_id="r1",
            source_content_hash="h",
        )
        b = C.SourceRecord(
            subject_path="x.py",
            source_kind="repository_file",
            modality="code",
            activity_id="a2",
            run_id="r2",
            source_content_hash="h",
        )
        assert a.source_identity_id == b.source_identity_id
        assert a.id != b.id
        assert a.source_identity_id.startswith("srcident:")

    def test_source_todict_roundtrips(self):
        s = C.SourceRecord(
            subject_path="x",
            source_kind="repository_file",
            modality="code",
            activity_id="a",
            run_id="r",
            source_content_hash="h",
        )
        d = s.to_dict()
        assert d["id"] == s.id and d["source_identity_id"] == s.source_identity_id
        assert json.dumps(d, sort_keys=True)

    def test_hash_kinds_are_distinct_fields(self):
        s = C.SourceRecord(
            subject_path="agg",
            source_kind="derived_artifact",
            modality="derived",
            activity_id="a",
            run_id="r",
            source_content_hash="",
            extraction_hash="e1",
            derivation_key="d1",
            derivation_activity_id="a",
        )
        d = s.to_dict()
        assert d["source_content_hash"] == ""
        assert d["extraction_hash"] == "e1"
        assert d["derivation_key"] == "d1"

    def test_facet_groups_partition(self):
        allf = set(C.FACET_STRENGTH)
        assert C.DECLARATION_FACETS | C.IMPLEMENTATION_FACETS | C.RUNTIME_FACETS == allf
        assert not (C.DECLARATION_FACETS & C.RUNTIME_FACETS)

    def test_observation_facet_predicates(self):
        s = "source:x"
        kw = dict(source_id=s, run_id="r", observation_kind="maturity")
        assert C.ObservationRecord("s", "p", 1, maturity_facet="declared", **kw).is_declaration
        assert C.ObservationRecord("s", "p", 1, maturity_facet="importable", **kw).is_implementation
        assert C.ObservationRecord("s", "p", 1, maturity_facet="running", **kw).is_runtime

    def test_observation_kind_without_maturity_facet(self):
        """A probe failure is observation_kind='probe_status' with NO maturity
        facet — never coerced to 'declared' (V4.1 correction 13)."""
        o = C.ObservationRecord(
            "probe:x",
            "probe_unavailable",
            {"error": "gate"},
            observation_kind="probe_status",
            source_id="source:x",
            run_id="r",
        )
        assert o.maturity_facet is None
        assert not o.is_declaration and not o.is_runtime and not o.is_implementation
        assert o.to_dict()["maturity_facet"] is None

    def test_declaration_never_runtime(self):
        o = C.ObservationRecord(
            "s",
            "p",
            True,
            observation_kind="maturity",
            maturity_facet="specified",
            source_id="source:x",
            run_id="r",
        )
        assert o.is_declaration and not o.is_runtime and not o.is_implementation

    def test_valid_time_qualifier(self):
        vt = C.ValidTime(start="2026-01-01", qualifier="open")
        assert vt.to_dict()["qualifier"] == "open"

    def test_observation_value_order_independent(self):
        kw = dict(
            observation_kind="maturity",
            maturity_facet="declared",
            source_id="src",
            run_id="r",
        )
        o1 = C.ObservationRecord("s", "p", {"b": 1, "a": 2}, **kw)
        o2 = C.ObservationRecord("s", "p", {"a": 2, "b": 1}, **kw)
        assert o1.id == o2.id

    def test_claim_lineage_stable_across_status(self):
        e1 = C.ClaimLedgerEntry("prop", "cap", "mod", "proposed", "r")
        e2 = C.ClaimLedgerEntry("prop", "cap", "mod", "supported", "r2")
        assert e1.lineage_id() == e2.lineage_id() and e1.id != e2.id

    def test_canonical_owner_claim_shape(self):
        """Canonical ownership is an explicit claim type with object_ref —
        never mined from free text (V4.1 correction 16)."""
        c = C.ClaimLedgerEntry(
            "canonical_runtime.py is declared the canonical operation runtime",
            "canonical_owner",
            "operation_runtime",
            "proposed",
            "r",
            object_ref="substrate/organism/canonical_runtime.py",
        )
        d = c.to_dict()
        assert d["claim_type"] == "canonical_owner"
        assert d["object_ref"] == "substrate/organism/canonical_runtime.py"
        # object_ref participates in lineage identity
        c2 = C.ClaimLedgerEntry(
            c.proposition,
            c.claim_type,
            c.scope,
            "proposed",
            "r",
            object_ref="somewhere/else.py",
        )
        assert c.lineage_id() != c2.lineage_id()

    def test_causal_record_typed_basis_with_validity_dims(self):
        c = C.CausalSupportRecord(
            "a1",
            "reported",
            "r",
            evidence_ids=("e1",),
            limitations=("small n",),
            internal_validity=None,
        )
        d = c.to_dict()
        assert c.id.startswith("causal:") and d["limitations"] == ["small n"]
        # validity dimensions are separate, None = not assessed (never guessed)
        assert d["internal_validity"] is None
        assert d["external_validity"] is None
        assert "not a rank" in (C.CausalSupportRecord.__doc__ or "").lower() or (
            "typed evidence class" in (C.CausalSupportRecord.__doc__ or "").lower()
        )

    def test_identity_pair_order_independent(self):
        r1 = C.IdentityResolution(("a", "b"), "link", "r")
        r2 = C.IdentityResolution(("b", "a"), "link", "r")
        assert r1.lineage_id() == r2.lineage_id()

    def test_identity_candidate_basis_recorded(self):
        r = C.IdentityResolution(
            ("a", "b"), "unresolved", "r", candidate_basis="mined:duplicate_basename"
        )
        assert r.to_dict()["candidate_basis"] == "mined:duplicate_basename"
