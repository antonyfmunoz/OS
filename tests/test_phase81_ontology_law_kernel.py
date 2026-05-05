"""Phase 81 tests — Reality-Derived Universal Ontology + Law Kernel v1.

Tests cover:
- Universal primitives (types, scopes, defaults, lookup, projections, instances)
- Universal laws (types, scopes, defaults, lookup, classification, projections)
- Abstraction layer (ordering, nodes, paths)
- Domain projections (types, defaults, lookup, project functions)
- Correspondence validation (status, maps, defaults, validation logic)
- Law application (status, apply_law, apply_laws, summarize)
- Ontology validation (primitive, law, projection, kernel)
- Views (primitive, law, domain projection, correspondence, kernel)
- Registry integration (new types, bridges, catalog)
- API endpoints (callable, read-only)
- CLI commands (parser accepts, dispatch entries)
- Layering invariants (no forbidden imports)
- Cross-module consistency
"""

import argparse
import ast
import importlib
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, "/opt/OS")


# ── Primitives: Types & Enums ───────────────────────────────────


class TestPrimitiveType(unittest.TestCase):
    def test_has_20_types(self):
        from umh.ontology.primitives import PrimitiveType

        self.assertEqual(len(PrimitiveType), 20)

    def test_all_values_lowercase(self):
        from umh.ontology.primitives import PrimitiveType

        for member in PrimitiveType:
            self.assertEqual(member.value, member.value.lower())

    def test_core_types_present(self):
        from umh.ontology.primitives import PrimitiveType

        expected = {
            "entity",
            "state",
            "relationship",
            "change",
            "time",
            "constraint",
            "resource",
            "action",
            "feedback",
            "goal",
            "outcome",
        }
        values = {m.value for m in PrimitiveType}
        self.assertTrue(expected.issubset(values))


class TestPrimitiveScope(unittest.TestCase):
    def test_has_5_scopes(self):
        from umh.ontology.primitives import PrimitiveScope

        self.assertEqual(len(PrimitiveScope), 5)

    def test_universal_exists(self):
        from umh.ontology.primitives import PrimitiveScope

        self.assertIn("universal", [m.value for m in PrimitiveScope])


class TestPrimitiveAbstractionLevel(unittest.TestCase):
    def test_has_levels(self):
        from umh.ontology.primitives import PrimitiveAbstractionLevel

        self.assertGreaterEqual(len(PrimitiveAbstractionLevel), 5)


# ── Primitives: UniversalPrimitive ──────────────────────────────


class TestUniversalPrimitive(unittest.TestCase):
    def test_default_primitives_count(self):
        from umh.ontology.primitives import get_primitives

        prims = get_primitives()
        self.assertEqual(len(prims), 16)

    def test_all_primitives_have_ids(self):
        from umh.ontology.primitives import get_primitives

        for p in get_primitives():
            self.assertTrue(p.primitive_id, f"Missing ID on {p.name}")
            self.assertTrue(p.primitive_id.startswith("prim_"))

    def test_all_primitives_have_definitions(self):
        from umh.ontology.primitives import get_primitives

        for p in get_primitives():
            self.assertTrue(len(p.definition) > 10, f"Short definition on {p.name}")

    def test_all_primitives_scope_universal(self):
        from umh.ontology.primitives import PrimitiveScope, get_primitives

        for p in get_primitives():
            self.assertEqual(p.scope, PrimitiveScope.UNIVERSAL, f"{p.name} not universal")

    def test_all_primitives_have_evidence_basis(self):
        from umh.ontology.primitives import get_primitives

        for p in get_primitives():
            self.assertTrue(p.evidence_basis, f"No evidence on {p.name}")

    def test_confidence_bounded_0_1(self):
        from umh.ontology.primitives import get_primitives

        for p in get_primitives():
            self.assertGreaterEqual(p.confidence, 0.0, f"{p.name}")
            self.assertLessEqual(p.confidence, 1.0, f"{p.name}")

    def test_to_dict_roundtrip(self):
        from umh.ontology.primitives import UniversalPrimitive, get_primitives

        for p in get_primitives():
            d = p.to_dict()
            p2 = UniversalPrimitive.from_dict(d)
            self.assertEqual(p.primitive_id, p2.primitive_id)
            self.assertEqual(p.name, p2.name)
            self.assertEqual(p.scope.value, p2.scope.value)

    def test_get_primitive_by_id(self):
        from umh.ontology.primitives import get_primitive_by_id

        p = get_primitive_by_id("prim_entity")
        self.assertIsNotNone(p)
        self.assertEqual(p.primitive_id, "prim_entity")

    def test_get_primitive_by_id_missing(self):
        from umh.ontology.primitives import get_primitive_by_id

        self.assertIsNone(get_primitive_by_id("prim_nonexistent"))

    def test_get_primitive_by_name(self):
        from umh.ontology.primitives import get_primitive_by_name

        p = get_primitive_by_name("entity")
        self.assertIsNotNone(p)

    def test_get_primitive_by_name_missing(self):
        from umh.ontology.primitives import get_primitive_by_name

        self.assertIsNone(get_primitive_by_name("nonexistent_xyz"))

    def test_all_ids_unique(self):
        from umh.ontology.primitives import get_primitives

        ids = [p.primitive_id for p in get_primitives()]
        self.assertEqual(len(ids), len(set(ids)))

    def test_all_names_unique(self):
        from umh.ontology.primitives import get_primitives

        names = [p.name for p in get_primitives()]
        self.assertEqual(len(names), len(set(names)))


# ── Primitives: PrimitiveProjection ─────────────────────────────


class TestPrimitiveProjection(unittest.TestCase):
    def test_projection_has_universal_ref(self):
        from umh.ontology.primitives import PrimitiveProjection

        proj = PrimitiveProjection(
            projection_id="proj_test",
            universal_primitive_id="prim_entity",
            domain="business",
            local_name="customer",
            local_definition="A business customer entity",
        )
        self.assertEqual(proj.universal_primitive_id, "prim_entity")

    def test_projection_to_dict(self):
        from umh.ontology.primitives import PrimitiveProjection

        proj = PrimitiveProjection(
            projection_id="proj_test",
            universal_primitive_id="prim_entity",
            domain="business",
            local_name="customer",
        )
        d = proj.to_dict()
        self.assertEqual(d["projection_id"], "proj_test")
        self.assertEqual(d["universal_primitive_id"], "prim_entity")


# ── Primitives: PrimitiveInstance ────────────────────────────────


class TestPrimitiveInstance(unittest.TestCase):
    def test_instance_creation(self):
        from umh.ontology.primitives import PrimitiveInstance

        inst = PrimitiveInstance(
            instance_id="inst_001",
            universal_primitive_id="prim_state",
            domain="software",
            context="database record",
            local_value="row in users table",
        )
        self.assertEqual(inst.domain, "software")

    def test_instance_to_dict(self):
        from umh.ontology.primitives import PrimitiveInstance

        inst = PrimitiveInstance(
            instance_id="inst_002",
            universal_primitive_id="prim_resource",
            domain="business",
        )
        d = inst.to_dict()
        self.assertIn("instance_id", d)
        self.assertIn("universal_primitive_id", d)


# ── Laws: Types & Enums ─────────────────────────────────────────


class TestLawType(unittest.TestCase):
    def test_has_13_types(self):
        from umh.ontology.laws import LawType

        self.assertEqual(len(LawType), 13)

    def test_all_values_lowercase(self):
        from umh.ontology.laws import LawType

        for member in LawType:
            self.assertEqual(member.value, member.value.lower())


class TestLawScope(unittest.TestCase):
    def test_has_6_scopes(self):
        from umh.ontology.laws import LawScope

        self.assertEqual(len(LawScope), 6)


class TestUniversalLawName(unittest.TestCase):
    def test_has_at_least_16_names(self):
        from umh.ontology.laws import UniversalLawName

        self.assertGreaterEqual(len(UniversalLawName), 16)

    def test_causality_present(self):
        from umh.ontology.laws import UniversalLawName

        self.assertIn("CAUSALITY", [m.name for m in UniversalLawName])


# ── Laws: UniversalLaw ──────────────────────────────────────────


class TestUniversalLaw(unittest.TestCase):
    def test_default_laws_count(self):
        from umh.ontology.laws import get_laws

        laws = get_laws()
        self.assertGreaterEqual(len(laws), 14)

    def test_all_laws_have_ids(self):
        from umh.ontology.laws import get_laws

        for law in get_laws():
            self.assertTrue(law.law_id, f"Missing ID on {law.name}")
            self.assertTrue(law.law_id.startswith("law_"))

    def test_all_laws_have_definitions(self):
        from umh.ontology.laws import get_laws

        for law in get_laws():
            self.assertTrue(len(law.definition) > 10, f"Short definition on {law.name}")

    def test_all_laws_scope_universal(self):
        from umh.ontology.laws import LawScope, get_laws

        for law in get_laws():
            self.assertEqual(law.scope, LawScope.UNIVERSAL, f"{law.name} not universal")

    def test_all_laws_have_evidence_basis(self):
        from umh.ontology.laws import get_laws

        for law in get_laws():
            self.assertTrue(law.evidence_basis, f"No evidence on {law.name}")

    def test_all_laws_have_failure_conditions(self):
        from umh.ontology.laws import get_laws

        for law in get_laws():
            self.assertTrue(law.failure_conditions, f"No failure conditions on {law.name}")

    def test_all_laws_have_governs(self):
        from umh.ontology.laws import get_laws

        for law in get_laws():
            self.assertTrue(len(law.governs) > 0, f"No governs on {law.name}")

    def test_all_laws_have_applies_to_primitives(self):
        from umh.ontology.laws import get_laws

        for law in get_laws():
            self.assertTrue(
                len(law.applies_to_primitives) > 0,
                f"No applies_to_primitives on {law.name}",
            )

    def test_confidence_bounded_0_1(self):
        from umh.ontology.laws import get_laws

        for law in get_laws():
            self.assertGreaterEqual(law.confidence, 0.0, f"{law.name}")
            self.assertLessEqual(law.confidence, 1.0, f"{law.name}")

    def test_to_dict_roundtrip(self):
        from umh.ontology.laws import UniversalLaw, get_laws

        for law in get_laws():
            d = law.to_dict()
            law2 = UniversalLaw.from_dict(d)
            self.assertEqual(law.law_id, law2.law_id)
            self.assertEqual(law.name, law2.name)

    def test_get_law_by_id(self):
        from umh.ontology.laws import get_law_by_id

        law = get_law_by_id("law_causality")
        self.assertIsNotNone(law)
        self.assertEqual(law.law_id, "law_causality")

    def test_get_law_by_id_missing(self):
        from umh.ontology.laws import get_law_by_id

        self.assertIsNone(get_law_by_id("law_nonexistent"))

    def test_get_law_by_name(self):
        from umh.ontology.laws import get_law_by_name

        law = get_law_by_name("causality")
        self.assertIsNotNone(law)

    def test_get_law_by_name_missing(self):
        from umh.ontology.laws import get_law_by_name

        self.assertIsNone(get_law_by_name("nonexistent_xyz"))

    def test_all_ids_unique(self):
        from umh.ontology.laws import get_laws

        ids = [law.law_id for law in get_laws()]
        self.assertEqual(len(ids), len(set(ids)))

    def test_state_transition_effect_present(self):
        from umh.ontology.laws import get_laws

        for law in get_laws():
            self.assertTrue(
                law.state_transition_effect,
                f"No state_transition_effect on {law.name}",
            )


# ── Laws: Classification ────────────────────────────────────────


class TestLawClassification(unittest.TestCase):
    def test_classify_universal(self):
        from umh.ontology.laws import LawScope, classify_law_scope

        cls = classify_law_scope("causality", law_type="systems")
        self.assertEqual(cls.scope, LawScope.UNIVERSAL)

    def test_classification_has_reason(self):
        from umh.ontology.laws import classify_law_scope

        cls = classify_law_scope("entropy", law_type="physical")
        self.assertTrue(cls.reason)


# ── Laws: DomainLawProjection ───────────────────────────────────


class TestDomainLawProjection(unittest.TestCase):
    def test_projection_to_dict_roundtrip(self):
        from umh.ontology.laws import DomainLawProjection

        proj = DomainLawProjection(
            projection_id="lp_test",
            universal_law_id="law_causality",
            domain="business",
            local_name="cause_effect",
            local_expression="Business cause and effect",
        )
        d = proj.to_dict()
        p2 = DomainLawProjection.from_dict(d)
        self.assertEqual(p2.projection_id, "lp_test")
        self.assertEqual(p2.universal_law_id, "law_causality")


# ── Abstraction Layer ────────────────────────────────────────────


class TestAbstractionLayer(unittest.TestCase):
    def test_layer_enum_exists(self):
        from umh.ontology.abstraction import AbstractionLayer

        self.assertGreaterEqual(len(AbstractionLayer), 10)

    def test_universal_is_highest(self):
        from umh.ontology.abstraction import AbstractionLayer, is_higher_layer

        self.assertTrue(is_higher_layer(AbstractionLayer.UNIVERSAL, AbstractionLayer.DOMAIN))

    def test_instance_is_lowest(self):
        from umh.ontology.abstraction import AbstractionLayer, is_lower_layer

        self.assertTrue(is_lower_layer(AbstractionLayer.INSTANCE, AbstractionLayer.UNIVERSAL))

    def test_same_layer_not_higher(self):
        from umh.ontology.abstraction import AbstractionLayer, is_higher_layer

        self.assertFalse(is_higher_layer(AbstractionLayer.DOMAIN, AbstractionLayer.DOMAIN))


class TestAbstractionNode(unittest.TestCase):
    def test_create_node(self):
        from umh.ontology.abstraction import AbstractionLayer, create_abstraction_node

        node = create_abstraction_node(name="test_node", layer="domain")
        self.assertTrue(node.node_id)
        self.assertEqual(node.layer, AbstractionLayer.DOMAIN)


class TestAbstractionPath(unittest.TestCase):
    def test_build_path(self):
        from umh.ontology.abstraction import AbstractionLayer, build_abstraction_path

        path = build_abstraction_path(
            AbstractionLayer.UNIVERSAL,
            AbstractionLayer.DOMAIN,
            nodes=["node_a", "node_b"],
        )
        self.assertEqual(len(path.nodes), 2)

    def test_path_to_dict(self):
        from umh.ontology.abstraction import AbstractionLayer, build_abstraction_path

        path = build_abstraction_path(
            AbstractionLayer.UNIVERSAL,
            AbstractionLayer.INSTANCE,
        )
        d = path.to_dict()
        self.assertIn("nodes", d)
        self.assertIn("lost_information", d)


# ── Domain Projections ───────────────────────────────────────────


class TestDomainType(unittest.TestCase):
    def test_has_14_types(self):
        from umh.ontology.domain_projection import DomainType

        self.assertEqual(len(DomainType), 14)

    def test_core_domains_present(self):
        from umh.ontology.domain_projection import DomainType

        expected = {"business", "software", "human", "content", "umh_internal"}
        values = {m.value for m in DomainType}
        self.assertTrue(expected.issubset(values))


class TestDomainProjectionSet(unittest.TestCase):
    def test_default_count(self):
        from umh.ontology.domain_projection import get_domain_projections

        projections = get_domain_projections()
        self.assertEqual(len(projections), 5)

    def test_all_domains_present(self):
        from umh.ontology.domain_projection import DomainType, get_domain_projections

        domains = {p.domain for p in get_domain_projections()}
        expected = {
            DomainType.BUSINESS,
            DomainType.SOFTWARE,
            DomainType.HUMAN,
            DomainType.CONTENT,
            DomainType.UMH_INTERNAL,
        }
        self.assertEqual(domains, expected)

    def test_projections_have_primitive_projections(self):
        from umh.ontology.domain_projection import get_domain_projections

        for ps in get_domain_projections():
            self.assertGreater(
                len(ps.primitive_projections),
                0,
                f"No primitive projections for {ps.domain}",
            )

    def test_projections_have_law_projections(self):
        from umh.ontology.domain_projection import get_domain_projections

        for ps in get_domain_projections():
            self.assertGreater(
                len(ps.law_projections),
                0,
                f"No law projections for {ps.domain}",
            )

    def test_primitive_projections_ref_valid_ids(self):
        from umh.ontology.domain_projection import get_domain_projections
        from umh.ontology.primitives import get_primitives

        valid_ids = {p.primitive_id for p in get_primitives()}
        for ps in get_domain_projections():
            for pp in ps.primitive_projections:
                self.assertIn(
                    pp.universal_primitive_id,
                    valid_ids,
                    f"Invalid ref {pp.universal_primitive_id} in {ps.domain}",
                )

    def test_law_projections_ref_valid_ids(self):
        from umh.ontology.domain_projection import get_domain_projections
        from umh.ontology.laws import get_laws

        valid_ids = {law.law_id for law in get_laws()}
        for ps in get_domain_projections():
            for lp in ps.law_projections:
                self.assertIn(
                    lp.universal_law_id,
                    valid_ids,
                    f"Invalid ref {lp.universal_law_id} in {ps.domain}",
                )

    def test_get_projection_by_domain(self):
        from umh.ontology.domain_projection import DomainType, get_projection_by_domain

        ps = get_projection_by_domain("business")
        self.assertIsNotNone(ps)
        self.assertEqual(ps.domain, DomainType.BUSINESS)

    def test_get_projection_by_domain_missing(self):
        from umh.ontology.domain_projection import get_projection_by_domain

        ps = get_projection_by_domain("music")
        self.assertIsNone(ps)

    def test_to_dict(self):
        from umh.ontology.domain_projection import get_domain_projections

        for ps in get_domain_projections():
            d = ps.to_dict()
            self.assertIn("domain", d)
            self.assertIn("primitive_projections", d)
            self.assertIn("law_projections", d)


class TestProjectFunctions(unittest.TestCase):
    def test_project_primitive(self):
        from umh.ontology.domain_projection import project_primitive

        result = project_primitive("prim_resource", "business")
        self.assertIsNotNone(result)

    def test_project_primitive_no_projection(self):
        from umh.ontology.domain_projection import project_primitive

        result = project_primitive("prim_entity", "music")
        self.assertIsNone(result)

    def test_project_law(self):
        from umh.ontology.domain_projection import project_law

        result = project_law("law_entropy", "software")
        self.assertIsNotNone(result)


# ── Correspondence ───────────────────────────────────────────────


class TestCorrespondenceStatus(unittest.TestCase):
    def test_has_5_statuses(self):
        from umh.ontology.correspondence import CorrespondenceStatus

        self.assertEqual(len(CorrespondenceStatus), 5)


class TestCorrespondenceMap(unittest.TestCase):
    def test_default_maps_count(self):
        from umh.ontology.correspondence import get_default_correspondence_maps

        maps = get_default_correspondence_maps()
        self.assertEqual(len(maps), 6)

    def test_all_maps_have_source_target(self):
        from umh.ontology.correspondence import get_default_correspondence_maps

        for cm in get_default_correspondence_maps():
            self.assertTrue(cm.source_domain, f"No source on {cm.map_id}")
            self.assertTrue(cm.target_domain, f"No target on {cm.map_id}")

    def test_all_maps_have_shared_primitives(self):
        from umh.ontology.correspondence import get_default_correspondence_maps

        for cm in get_default_correspondence_maps():
            self.assertGreater(
                len(cm.shared_primitives),
                0,
                f"No shared primitives on {cm.map_id}",
            )

    def test_all_maps_have_analogy_breaks(self):
        from umh.ontology.correspondence import get_default_correspondence_maps

        for cm in get_default_correspondence_maps():
            self.assertGreater(
                len(cm.analogy_breaks),
                0,
                f"No analogy breaks declared on {cm.map_id}",
            )

    def test_all_maps_have_evidence(self):
        from umh.ontology.correspondence import get_default_correspondence_maps

        for cm in get_default_correspondence_maps():
            self.assertTrue(cm.evidence, f"No evidence on {cm.map_id}")

    def test_to_dict(self):
        from umh.ontology.correspondence import get_default_correspondence_maps

        for cm in get_default_correspondence_maps():
            d = cm.to_dict()
            self.assertIn("map_id", d)
            self.assertIn("analogy_breaks", d)
            self.assertIn("status", d)


class TestCorrespondenceValidation(unittest.TestCase):
    def test_validate_returns_check(self):
        from umh.ontology.correspondence import (
            get_default_correspondence_maps,
            validate_correspondence_map,
        )

        for cm in get_default_correspondence_maps():
            check = validate_correspondence_map(cm)
            self.assertIn(
                check.status.value,
                {"validated", "partial", "weak", "invalid", "unknown"},
            )

    def test_validated_map_has_positive_checks(self):
        from umh.ontology.correspondence import (
            CorrespondenceStatus,
            get_default_correspondence_maps,
            validate_correspondence_map,
        )

        for cm in get_default_correspondence_maps():
            check = validate_correspondence_map(cm)
            if check.status == CorrespondenceStatus.VALIDATED:
                self.assertTrue(check.primitives_match)
                self.assertTrue(check.evidence_sufficient)

    def test_get_correspondence_maps_function(self):
        from umh.ontology.correspondence import get_correspondence_maps

        maps = get_correspondence_maps()
        self.assertEqual(len(maps), 6)


# ── Law Application ──────────────────────────────────────────────


class TestLawApplicationStatus(unittest.TestCase):
    def test_has_5_statuses(self):
        from umh.ontology.law_application import LawApplicationStatus

        self.assertEqual(len(LawApplicationStatus), 5)


class TestApplyLaw(unittest.TestCase):
    def test_apply_law_to_context(self):
        from umh.ontology.law_application import apply_law_to_context
        from umh.ontology.laws import get_law_by_id

        law = get_law_by_id("law_causality")
        result = apply_law_to_context(
            law,
            "Customer action causes state change",
            primitives=["change", "action"],
            domain="business",
        )
        self.assertTrue(result.application_id)
        self.assertEqual(result.law_id, "law_causality")

    def test_apply_law_empty_context(self):
        from umh.ontology.law_application import LawApplicationStatus, apply_law_to_context
        from umh.ontology.laws import get_law_by_id

        law = get_law_by_id("law_causality")
        result = apply_law_to_context(law, "")
        self.assertEqual(result.status, LawApplicationStatus.INSUFFICIENT_DATA)
        self.assertLessEqual(result.confidence, 0.2)

    def test_apply_law_with_matching_primitives(self):
        from umh.ontology.law_application import LawApplicationStatus, apply_law_to_context
        from umh.ontology.laws import get_law_by_id

        law = get_law_by_id("law_feedback")
        result = apply_law_to_context(
            law,
            "Feedback loop drives outcome improvement",
            primitives=["feedback", "signal", "action"],
            domain="software",
        )
        self.assertIn(
            result.status,
            [LawApplicationStatus.APPLICABLE, LawApplicationStatus.PARTIALLY_APPLICABLE],
        )

    def test_apply_law_confidence_bounded(self):
        from umh.ontology.law_application import apply_law_to_context
        from umh.ontology.laws import get_laws

        for law in get_laws():
            result = apply_law_to_context(law, "some context", primitives=["entity"])
            self.assertGreaterEqual(result.confidence, 0.0)
            self.assertLessEqual(result.confidence, 1.0)


class TestApplyLaws(unittest.TestCase):
    def test_apply_laws_to_context(self):
        from umh.ontology.law_application import apply_laws_to_context
        from umh.ontology.laws import get_laws

        results = apply_laws_to_context(
            get_laws(),
            "state change with constraint",
            primitives=["state", "change", "constraint"],
            domain="umh_internal",
        )
        self.assertGreaterEqual(len(results), 14)


class TestSummarizeLawApplication(unittest.TestCase):
    def test_summarize(self):
        from umh.ontology.law_application import (
            apply_law_to_context,
            summarize_law_application,
        )
        from umh.ontology.laws import get_law_by_id

        law = get_law_by_id("law_entropy")
        result = apply_law_to_context(
            law,
            "Deprecated stale code accumulates",
            primitives=["state", "change"],
            domain="software",
        )
        summary = summarize_law_application(result)
        self.assertIsInstance(summary, dict)
        self.assertIn("law_id", summary)


# ── Validation ───────────────────────────────────────────────────


class TestValidatePrimitive(unittest.TestCase):
    def test_valid_primitives_pass(self):
        from umh.ontology.primitives import get_primitives
        from umh.ontology.validation import validate_universal_primitive

        for p in get_primitives():
            issues = validate_universal_primitive(p)
            errors = [i for i in issues if i.severity == "error"]
            self.assertEqual(len(errors), 0, f"Errors on {p.name}: {errors}")

    def test_missing_definition_detected(self):
        from umh.ontology.primitives import (
            PrimitiveAbstractionLevel,
            PrimitiveScope,
            PrimitiveType,
            UniversalPrimitive,
        )
        from umh.ontology.validation import validate_universal_primitive

        bad = UniversalPrimitive(
            primitive_id="prim_bad",
            name="bad",
            primitive_type=PrimitiveType.ENTITY,
            definition="",
            abstraction_level=PrimitiveAbstractionLevel.UNIVERSAL,
            scope=PrimitiveScope.UNIVERSAL,
            evidence_basis="some evidence",
        )
        issues = validate_universal_primitive(bad)
        self.assertGreater(len(issues), 0)


class TestValidateLaw(unittest.TestCase):
    def test_valid_laws_pass(self):
        from umh.ontology.laws import get_laws
        from umh.ontology.validation import validate_universal_law

        for law in get_laws():
            issues = validate_universal_law(law)
            errors = [i for i in issues if i.severity == "error"]
            self.assertEqual(len(errors), 0, f"Errors on {law.name}: {errors}")

    def test_missing_failure_conditions_detected(self):
        from umh.ontology.laws import LawScope, LawType, UniversalLaw, UniversalLawName
        from umh.ontology.validation import validate_universal_law

        bad = UniversalLaw(
            law_id="law_bad",
            name="bad_law",
            law_name=UniversalLawName.CAUSALITY,
            law_type=LawType.SYSTEMS,
            scope=LawScope.UNIVERSAL,
            definition="A test law with no failure conditions",
            governs=["something"],
            applies_to_primitives=["entity"],
            state_transition_effect="some effect",
            evidence_basis="some evidence",
            failure_conditions="",
        )
        issues = validate_universal_law(bad)
        self.assertGreater(len(issues), 0)


class TestValidateProjection(unittest.TestCase):
    def test_valid_projections_pass(self):
        from umh.ontology.domain_projection import get_domain_projections
        from umh.ontology.primitives import get_primitives
        from umh.ontology.laws import get_laws
        from umh.ontology.validation import validate_primitive_projection, validate_law_projection

        prims = get_primitives()
        laws_list = get_laws()

        for ps in get_domain_projections():
            for pp in ps.primitive_projections:
                issues = validate_primitive_projection(pp, prims)
                errors = [i for i in issues if i.severity == "error"]
                self.assertEqual(len(errors), 0, f"Errors on {pp.projection_id}")
            for lp in ps.law_projections:
                issues = validate_law_projection(lp, laws_list)
                errors = [i for i in issues if i.severity == "error"]
                self.assertEqual(len(errors), 0, f"Errors on {lp.projection_id}")


class TestValidateOntologyKernel(unittest.TestCase):
    def test_kernel_valid(self):
        from umh.ontology.primitives import get_primitives
        from umh.ontology.laws import get_laws
        from umh.ontology.domain_projection import get_domain_projections
        from umh.ontology.validation import validate_ontology_kernel

        result = validate_ontology_kernel(get_primitives(), get_laws(), get_domain_projections())
        self.assertTrue(result.valid)
        self.assertEqual(len(result.issues), 0)
        self.assertEqual(result.checked_primitives, 16)
        self.assertGreaterEqual(result.checked_laws, 14)

    def test_kernel_result_to_dict(self):
        from umh.ontology.primitives import get_primitives
        from umh.ontology.laws import get_laws
        from umh.ontology.validation import validate_ontology_kernel

        result = validate_ontology_kernel(get_primitives(), get_laws())
        d = result.to_dict()
        self.assertIn("valid", d)
        self.assertIn("checked_primitives", d)

    def test_no_domain_projection_marked_universal(self):
        from umh.ontology.domain_projection import get_domain_projections
        from umh.ontology.validation import validate_no_domain_projection_marked_universal

        issues = validate_no_domain_projection_marked_universal(get_domain_projections())
        self.assertEqual(len(issues), 0)


# ── Views ────────────────────────────────────────────────────────


class TestPrimitiveView(unittest.TestCase):
    def test_primitive_to_view(self):
        from umh.ontology.primitives import get_primitives
        from umh.ontology.views import primitive_to_view

        for p in get_primitives():
            view = primitive_to_view(p)
            self.assertEqual(view.primitive_id, p.primitive_id)
            self.assertTrue(view.name)

    def test_view_to_dict(self):
        from umh.ontology.primitives import get_primitives
        from umh.ontology.views import primitive_to_view

        p = get_primitives()[0]
        view = primitive_to_view(p)
        d = view.to_dict()
        self.assertIn("primitive_id", d)
        self.assertIn("scope", d)


class TestLawView(unittest.TestCase):
    def test_law_to_view(self):
        from umh.ontology.laws import get_laws
        from umh.ontology.views import law_to_view

        for law in get_laws():
            view = law_to_view(law)
            self.assertEqual(view.law_id, law.law_id)

    def test_view_to_dict(self):
        from umh.ontology.laws import get_laws
        from umh.ontology.views import law_to_view

        law = get_laws()[0]
        view = law_to_view(law)
        d = view.to_dict()
        self.assertIn("law_id", d)
        self.assertIn("scope", d)


class TestDomainProjectionView(unittest.TestCase):
    def test_domain_projection_to_view(self):
        from umh.ontology.domain_projection import get_domain_projections
        from umh.ontology.views import domain_projection_to_view

        for ps in get_domain_projections():
            view = domain_projection_to_view(ps)
            self.assertTrue(view.domain)

    def test_view_to_dict(self):
        from umh.ontology.domain_projection import get_domain_projections
        from umh.ontology.views import domain_projection_to_view

        ps = get_domain_projections()[0]
        d = domain_projection_to_view(ps).to_dict()
        self.assertIn("domain", d)
        self.assertIn("primitive_projection_count", d)


class TestCorrespondenceView(unittest.TestCase):
    def test_correspondence_to_view(self):
        from umh.ontology.correspondence import get_correspondence_maps
        from umh.ontology.views import correspondence_to_view

        for cm in get_correspondence_maps():
            view = correspondence_to_view(cm)
            self.assertTrue(view.map_id)

    def test_view_to_dict(self):
        from umh.ontology.correspondence import get_correspondence_maps
        from umh.ontology.views import correspondence_to_view

        cm = get_correspondence_maps()[0]
        d = correspondence_to_view(cm).to_dict()
        self.assertIn("map_id", d)
        self.assertIn("status", d)
        self.assertIn("analogy_breaks_count", d)


class TestOntologyKernelView(unittest.TestCase):
    def test_build_kernel_view(self):
        from umh.ontology.correspondence import get_correspondence_maps
        from umh.ontology.domain_projection import get_domain_projections
        from umh.ontology.laws import get_laws
        from umh.ontology.primitives import get_primitives
        from umh.ontology.validation import validate_ontology_kernel
        from umh.ontology.views import build_ontology_kernel_view

        prims = get_primitives()
        laws = get_laws()
        projs = get_domain_projections()
        corrs = get_correspondence_maps()
        val = validate_ontology_kernel(prims, laws, projs)
        view = build_ontology_kernel_view(prims, laws, projs, corrs, val)
        self.assertEqual(view.primitive_count, 16)
        self.assertGreaterEqual(view.law_count, 14)
        self.assertEqual(view.domain_projection_count, 5)
        self.assertEqual(view.correspondence_count, 6)
        self.assertEqual(view.validation_status, "valid")

    def test_kernel_view_to_dict(self):
        from umh.ontology.views import build_ontology_kernel_view

        d = build_ontology_kernel_view().to_dict()
        self.assertIn("primitive_count", d)
        self.assertIn("law_count", d)
        self.assertIn("validation_status", d)
        self.assertIn("generated_at", d)


# ── Registry Integration ─────────────────────────────────────────


class TestRegistryTypes(unittest.TestCase):
    def test_new_types_exist(self):
        from umh.registry.contracts import RegistryType

        for name in ["PRIMITIVE", "LAW", "DOMAIN_PROJECTION", "CORRESPONDENCE_MAP", "ONTOLOGY"]:
            self.assertTrue(hasattr(RegistryType, name), f"Missing {name}")

    def test_enum_count_includes_phase81(self):
        from umh.registry.contracts import RegistryType

        self.assertGreaterEqual(len(RegistryType), 21)


class TestRegistryBridges(unittest.TestCase):
    def test_ontology_primitives_bridge(self):
        from umh.registry.bridges import ontology_primitives_to_registry_items

        items = ontology_primitives_to_registry_items()
        self.assertEqual(len(items), 16)
        for item in items:
            self.assertTrue(item.item_id.startswith("onto_prim_"))
            self.assertEqual(item.registry_type.value, "primitive")

    def test_ontology_laws_bridge(self):
        from umh.registry.bridges import ontology_laws_to_registry_items

        items = ontology_laws_to_registry_items()
        self.assertGreaterEqual(len(items), 14)
        for item in items:
            self.assertTrue(item.item_id.startswith("onto_law_"))
            self.assertEqual(item.registry_type.value, "law")

    def test_domain_projections_bridge(self):
        from umh.registry.bridges import domain_projections_to_registry_items

        items = domain_projections_to_registry_items()
        self.assertEqual(len(items), 5)
        for item in items:
            self.assertEqual(item.registry_type.value, "domain_projection")

    def test_correspondence_maps_bridge(self):
        from umh.registry.bridges import correspondence_maps_to_registry_items

        items = correspondence_maps_to_registry_items()
        self.assertEqual(len(items), 6)
        for item in items:
            self.assertEqual(item.registry_type.value, "correspondence_map")

    def test_bridge_items_version_81(self):
        from umh.registry.bridges import (
            correspondence_maps_to_registry_items,
            domain_projections_to_registry_items,
            ontology_laws_to_registry_items,
            ontology_primitives_to_registry_items,
        )

        for items_fn in [
            ontology_primitives_to_registry_items,
            ontology_laws_to_registry_items,
            domain_projections_to_registry_items,
            correspondence_maps_to_registry_items,
        ]:
            for item in items_fn():
                self.assertEqual(item.version, "81")


class TestRegistryCatalog(unittest.TestCase):
    def test_catalog_includes_ontology(self):
        from umh.registry.catalog import build_default_registry_catalog

        catalog = build_default_registry_catalog()
        counts = catalog.count_by_type()
        self.assertIn("primitive", counts)
        self.assertIn("law", counts)
        self.assertEqual(counts["primitive"], 16)
        self.assertGreaterEqual(counts["law"], 14)

    def test_catalog_by_type_primitive(self):
        from umh.registry.catalog import build_default_registry_catalog
        from umh.registry.contracts import RegistryType

        catalog = build_default_registry_catalog()
        prims = catalog.by_type(RegistryType.PRIMITIVE)
        self.assertEqual(len(prims), 16)

    def test_catalog_total_includes_ontology(self):
        from umh.registry.catalog import build_default_registry_catalog

        catalog = build_default_registry_catalog()
        self.assertGreaterEqual(len(catalog.items), 41)


# ── API Endpoints ────────────────────────────────────────────────


class TestAPIEndpoints(unittest.TestCase):
    def test_api_module_imports(self):
        import umh.control.api

    def test_ontology_routes_registered(self):
        from umh.control.api import app

        routes = [r.path for r in app.routes]
        expected = [
            "/ontology",
            "/ontology/primitives",
            "/ontology/laws",
            "/ontology/domain-projections",
            "/ontology/correspondence",
            "/ontology/validate",
        ]
        for route in expected:
            self.assertIn(route, routes, f"Missing route: {route}")

    def test_ontology_primitives_by_id_route(self):
        from umh.control.api import app

        routes = [r.path for r in app.routes]
        self.assertIn("/ontology/primitives/{primitive_id}", routes)

    def test_ontology_laws_by_id_route(self):
        from umh.control.api import app

        routes = [r.path for r in app.routes]
        self.assertIn("/ontology/laws/{law_id}", routes)


# ── CLI Commands ─────────────────────────────────────────────────


class TestCLIParser(unittest.TestCase):
    def test_ontology_commands_in_parser(self):
        from umh.control.cli import build_parser

        parser = build_parser()
        cmds = [
            "ontology-status",
            "ontology-primitives",
            "ontology-laws",
            "ontology-projections",
            "ontology-correspondence",
            "ontology-validate",
        ]
        for cmd in cmds:
            args = parser.parse_args([cmd])
            self.assertEqual(args.command, cmd)

    def test_ontology_commands_accept_json(self):
        from umh.control.cli import build_parser

        parser = build_parser()
        cmds = [
            "ontology-status",
            "ontology-primitives",
            "ontology-laws",
            "ontology-projections",
            "ontology-correspondence",
            "ontology-validate",
        ]
        for cmd in cmds:
            args = parser.parse_args([cmd, "--json"])
            self.assertTrue(args.json)


class TestCLIDispatch(unittest.TestCase):
    def test_dispatch_entries_exist(self):
        from umh.control.cli import main

        import umh.control.cli as cli_mod

        expected_handlers = [
            "cmd_ontology_status",
            "cmd_ontology_primitives",
            "cmd_ontology_laws",
            "cmd_ontology_projections",
            "cmd_ontology_correspondence",
            "cmd_ontology_validate",
        ]
        for name in expected_handlers:
            self.assertTrue(hasattr(cli_mod, name), f"Missing handler: {name}")

    def test_cli_ontology_status_runs(self):
        from umh.control.cli import main

        ret = main(["ontology-status", "--json"])
        self.assertEqual(ret, 0)

    def test_cli_ontology_validate_runs(self):
        from umh.control.cli import main

        ret = main(["ontology-validate", "--json"])
        self.assertEqual(ret, 0)

    def test_cli_ontology_primitives_runs(self):
        from umh.control.cli import main

        ret = main(["ontology-primitives", "--json"])
        self.assertEqual(ret, 0)

    def test_cli_ontology_laws_runs(self):
        from umh.control.cli import main

        ret = main(["ontology-laws", "--json"])
        self.assertEqual(ret, 0)

    def test_cli_ontology_projections_runs(self):
        from umh.control.cli import main

        ret = main(["ontology-projections", "--json"])
        self.assertEqual(ret, 0)

    def test_cli_ontology_correspondence_runs(self):
        from umh.control.cli import main

        ret = main(["ontology-correspondence", "--json"])
        self.assertEqual(ret, 0)


# ── Layering Invariants ─────────────────────────────────────────


class TestLayeringInvariants(unittest.TestCase):
    """Phase 81 modules must not import forbidden layers."""

    def _get_imports(self, filepath: Path) -> set[str]:
        src = filepath.read_text()
        tree = ast.parse(src)
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module)
        return imports

    def test_no_execution_imports(self):
        ontology_dir = Path("/opt/OS/umh/ontology")
        forbidden = {"umh.execution", "umh.adapters", "umh.control"}
        for py_file in ontology_dir.glob("*.py"):
            if py_file.name == "__init__.py":
                continue
            imports = self._get_imports(py_file)
            for imp in imports:
                for f in forbidden:
                    self.assertFalse(
                        imp.startswith(f),
                        f"{py_file.name} imports {imp} (forbidden: {f})",
                    )

    def test_no_llm_imports(self):
        ontology_dir = Path("/opt/OS/umh/ontology")
        forbidden = {"anthropic", "google.genai", "openai", "ollama"}
        for py_file in ontology_dir.glob("*.py"):
            imports = self._get_imports(py_file)
            for imp in imports:
                self.assertNotIn(
                    imp,
                    forbidden,
                    f"{py_file.name} imports LLM SDK {imp}",
                )

    def test_no_network_imports(self):
        ontology_dir = Path("/opt/OS/umh/ontology")
        forbidden = {"requests", "httpx", "aiohttp", "urllib3"}
        for py_file in ontology_dir.glob("*.py"):
            imports = self._get_imports(py_file)
            for imp in imports:
                self.assertNotIn(
                    imp,
                    forbidden,
                    f"{py_file.name} imports network lib {imp}",
                )


# ── Cross-Module Consistency ─────────────────────────────────────


class TestCrossModuleConsistency(unittest.TestCase):
    def test_all_primitive_ids_in_laws_exist(self):
        from umh.ontology.laws import get_laws
        from umh.ontology.primitives import get_primitives

        prim_names = {p.name for p in get_primitives()}
        prim_types = {p.primitive_type.value for p in get_primitives()}
        known = prim_names | prim_types

        for law in get_laws():
            for prim_ref in law.applies_to_primitives:
                self.assertIn(
                    prim_ref,
                    known,
                    f"Law {law.name} references unknown primitive '{prim_ref}'",
                )

    def test_all_governs_in_laws_non_empty(self):
        from umh.ontology.laws import get_laws

        for law in get_laws():
            for g in law.governs:
                self.assertTrue(g.strip(), f"Empty governs entry in {law.name}")

    def test_projection_confidence_bounded(self):
        from umh.ontology.domain_projection import get_domain_projections

        for ps in get_domain_projections():
            for pp in ps.primitive_projections:
                self.assertGreaterEqual(pp.confidence, 0.0)
                self.assertLessEqual(pp.confidence, 1.0)
            for lp in ps.law_projections:
                self.assertGreaterEqual(lp.confidence, 0.0)
                self.assertLessEqual(lp.confidence, 1.0)

    def test_correspondence_confidence_bounded(self):
        from umh.ontology.correspondence import get_correspondence_maps

        for cm in get_correspondence_maps():
            self.assertGreaterEqual(cm.confidence, 0.0)
            self.assertLessEqual(cm.confidence, 1.0)


# ── Observability Integration ────────────────────────────────────


class TestObservabilityIntegration(unittest.TestCase):
    def test_system_status_has_ontology_field(self):
        from umh.observability.system_status import SystemStatus

        ss = SystemStatus()
        self.assertEqual(ss.ontology_kernel_status, "unknown")

    def test_system_status_to_dict_has_ontology(self):
        from umh.observability.system_status import SystemStatus

        d = SystemStatus().to_dict()
        self.assertIn("ontology_kernel_status", d)

    def test_check_ontology_kernel(self):
        from umh.observability.system_status import check_ontology_kernel

        cs = check_ontology_kernel()
        self.assertTrue(cs.available)
        self.assertEqual(cs.status, "ok")
        self.assertIn("primitive_count", cs.metadata)

    def test_dashboard_snapshot_has_ontology_summary(self):
        from umh.interface.views import OperatorDashboardSnapshot

        snap = OperatorDashboardSnapshot(user_id="test")
        self.assertEqual(snap.ontology_summary, {})

    def test_dashboard_to_dict_has_ontology(self):
        from umh.interface.views import OperatorDashboardSnapshot

        d = OperatorDashboardSnapshot(user_id="test").to_dict()
        self.assertIn("ontology_summary", d)


# ── No Sensitive Data in Views ───────────────────────────────────


class TestNoSensitiveDataInViews(unittest.TestCase):
    def test_views_no_secrets(self):
        src = Path("/opt/OS/umh/ontology/views.py").read_text().lower()
        self.assertNotIn("api_key", src)
        self.assertNotIn("password", src)
        self.assertNotIn("token", src)


# ── Module Importability ─────────────────────────────────────────


class TestModuleImports(unittest.TestCase):
    def test_all_ontology_modules_import(self):
        modules = [
            "umh.ontology",
            "umh.ontology.primitives",
            "umh.ontology.laws",
            "umh.ontology.abstraction",
            "umh.ontology.domain_projection",
            "umh.ontology.correspondence",
            "umh.ontology.law_application",
            "umh.ontology.validation",
            "umh.ontology.views",
        ]
        for mod in modules:
            m = importlib.import_module(mod)
            self.assertIsNotNone(m)


# ── Additional Coverage ──────────────────────────────────────────


class TestClampConfidence(unittest.TestCase):
    def test_clamp_in_range(self):
        from umh.ontology.laws import clamp_confidence

        self.assertEqual(clamp_confidence(0.5), 0.5)

    def test_clamp_below_zero(self):
        from umh.ontology.laws import clamp_confidence

        self.assertEqual(clamp_confidence(-0.5), 0.0)

    def test_clamp_above_one(self):
        from umh.ontology.laws import clamp_confidence

        self.assertEqual(clamp_confidence(1.5), 1.0)

    def test_clamp_boundary(self):
        from umh.ontology.laws import clamp_confidence

        self.assertEqual(clamp_confidence(0.0), 0.0)
        self.assertEqual(clamp_confidence(1.0), 1.0)


class TestNormalizeFunctions(unittest.TestCase):
    def test_normalize_primitive_type(self):
        from umh.ontology.primitives import PrimitiveType, normalize_primitive_type

        self.assertEqual(normalize_primitive_type("entity"), PrimitiveType.ENTITY)
        self.assertEqual(normalize_primitive_type("nonsense"), PrimitiveType.UNKNOWN)

    def test_normalize_domain_type(self):
        from umh.ontology.domain_projection import DomainType, normalize_domain_type

        self.assertEqual(normalize_domain_type("business"), DomainType.BUSINESS)
        self.assertEqual(normalize_domain_type("nonsense"), DomainType.UNKNOWN)

    def test_normalize_law_type(self):
        from umh.ontology.laws import LawType, normalize_law_type

        self.assertEqual(normalize_law_type("physical"), LawType.PHYSICAL)
        self.assertEqual(normalize_law_type("nope"), LawType.UNKNOWN)

    def test_normalize_abstraction_layer(self):
        from umh.ontology.abstraction import AbstractionLayer, normalize_abstraction_layer

        self.assertEqual(normalize_abstraction_layer("universal"), AbstractionLayer.UNIVERSAL)
        self.assertEqual(normalize_abstraction_layer("nope"), AbstractionLayer.UNKNOWN)


class TestLawApplicationEdgeCases(unittest.TestCase):
    def test_apply_all_14_laws_returns_14(self):
        from umh.ontology.law_application import apply_laws_to_context
        from umh.ontology.laws import get_laws

        results = apply_laws_to_context(get_laws(), "test context")
        self.assertGreaterEqual(len(results), 14)
        for r in results:
            self.assertTrue(r.application_id)

    def test_summarize_returns_dict_keys(self):
        from umh.ontology.law_application import apply_law_to_context, summarize_law_application
        from umh.ontology.laws import get_law_by_id

        law = get_law_by_id("law_causality")
        result = apply_law_to_context(law, "test")
        summary = summarize_law_application(result)
        for key in ["law_id", "status", "confidence", "matched_primitives"]:
            self.assertIn(key, summary)


class TestRegistryBridgeDetails(unittest.TestCase):
    def test_primitive_bridge_tags_include_ontology(self):
        from umh.registry.bridges import ontology_primitives_to_registry_items

        for item in ontology_primitives_to_registry_items():
            self.assertIn("ontology", item.tags)

    def test_law_bridge_tags_include_ontology(self):
        from umh.registry.bridges import ontology_laws_to_registry_items

        for item in ontology_laws_to_registry_items():
            self.assertIn("ontology", item.tags)

    def test_projection_bridge_tags_include_ontology(self):
        from umh.registry.bridges import domain_projections_to_registry_items

        for item in domain_projections_to_registry_items():
            self.assertIn("ontology", item.tags)

    def test_correspondence_bridge_tags_include_ontology(self):
        from umh.registry.bridges import correspondence_maps_to_registry_items

        for item in correspondence_maps_to_registry_items():
            self.assertIn("ontology", item.tags)


class TestAbstractionLayerOrdering(unittest.TestCase):
    def test_ordering_consistency(self):
        from umh.ontology.abstraction import AbstractionLayer, is_higher_layer, is_lower_layer

        layers = [
            AbstractionLayer.UNIVERSAL,
            AbstractionLayer.META_SYSTEM,
            AbstractionLayer.DOMAIN,
            AbstractionLayer.SYSTEM,
            AbstractionLayer.INSTANCE,
        ]
        for i in range(len(layers) - 1):
            self.assertTrue(is_higher_layer(layers[i], layers[i + 1]))
            self.assertTrue(is_lower_layer(layers[i + 1], layers[i]))

    def test_unknown_layer_ordering(self):
        from umh.ontology.abstraction import AbstractionLayer, is_lower_layer

        self.assertTrue(is_lower_layer(AbstractionLayer.UNKNOWN, AbstractionLayer.UNIVERSAL))


if __name__ == "__main__":
    unittest.main()
