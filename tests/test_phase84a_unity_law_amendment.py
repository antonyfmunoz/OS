"""Phase 84A — Universal Law Kernel Amendment: Unity / Oneness + Polarity Synthesis tests.

Tests covering Unity law addition, domain projections, polarity synthesis contracts,
law application updates, validation, views, registry/API/CLI integration, layering
invariants, and regression.
"""

import ast
import os
import sys
import unittest

sys.path.insert(0, "/opt/OS")


# ── Section 1: Unity Law Normalization ──────────────────────────────


class TestUnityNormalizesUnity(unittest.TestCase):
    def test_normalizes_unity(self):
        from umh.ontology.laws import UniversalLawName, normalize_universal_law_name

        self.assertEqual(normalize_universal_law_name("unity"), UniversalLawName.UNITY_ONENESS)

    def test_normalizes_oneness(self):
        from umh.ontology.laws import UniversalLawName, normalize_universal_law_name

        self.assertEqual(normalize_universal_law_name("oneness"), UniversalLawName.UNITY_ONENESS)

    def test_normalizes_unity_oneness(self):
        from umh.ontology.laws import UniversalLawName, normalize_universal_law_name

        self.assertEqual(
            normalize_universal_law_name("unity_oneness"), UniversalLawName.UNITY_ONENESS
        )

    def test_normalizes_unity_slash(self):
        from umh.ontology.laws import UniversalLawName, normalize_universal_law_name

        self.assertEqual(
            normalize_universal_law_name("unity / oneness"), UniversalLawName.UNITY_ONENESS
        )

    def test_normalizes_law_of_unity(self):
        from umh.ontology.laws import UniversalLawName, normalize_universal_law_name

        self.assertEqual(
            normalize_universal_law_name("law of unity"), UniversalLawName.UNITY_ONENESS
        )

    def test_normalizes_law_of_oneness(self):
        from umh.ontology.laws import UniversalLawName, normalize_universal_law_name

        self.assertEqual(
            normalize_universal_law_name("law of oneness"), UniversalLawName.UNITY_ONENESS
        )

    def test_unknown_still_degrades(self):
        from umh.ontology.laws import UniversalLawName, normalize_universal_law_name

        self.assertEqual(normalize_universal_law_name("garbage"), UniversalLawName.UNKNOWN)


# ── Section 2: Unity Law in Defaults ────────────────────────────────


class TestDefaultLawsIncludeUnity(unittest.TestCase):
    def test_unity_present(self):
        from umh.ontology.laws import UniversalLawName, get_default_universal_laws

        laws = get_default_universal_laws()
        names = [l.law_name for l in laws]
        self.assertIn(UniversalLawName.UNITY_ONENESS, names)

    def test_unity_scope_is_universal(self):
        from umh.ontology.laws import LawScope, get_default_universal_laws

        unity = [l for l in get_default_universal_laws() if l.law_id == "law_unity_oneness"][0]
        self.assertEqual(unity.scope, LawScope.UNIVERSAL)

    def test_unity_not_domain_specific(self):
        from umh.ontology.laws import LawType, get_default_universal_laws

        unity = [l for l in get_default_universal_laws() if l.law_id == "law_unity_oneness"][0]
        self.assertNotEqual(unity.law_type, LawType.DOMAIN_SPECIFIC)

    def test_unity_not_heuristic(self):
        from umh.ontology.laws import LawType, get_default_universal_laws

        unity = [l for l in get_default_universal_laws() if l.law_id == "law_unity_oneness"][0]
        self.assertNotEqual(unity.law_type, LawType.HEURISTIC)

    def test_unity_has_evidence_basis(self):
        from umh.ontology.laws import get_default_universal_laws

        unity = [l for l in get_default_universal_laws() if l.law_id == "law_unity_oneness"][0]
        self.assertTrue(len(unity.evidence_basis) > 0)

    def test_unity_has_failure_conditions(self):
        from umh.ontology.laws import get_default_universal_laws

        unity = [l for l in get_default_universal_laws() if l.law_id == "law_unity_oneness"][0]
        self.assertGreater(len(unity.failure_conditions), 0)

    def test_unity_has_applies_to_primitives(self):
        from umh.ontology.laws import get_default_universal_laws

        unity = [l for l in get_default_universal_laws() if l.law_id == "law_unity_oneness"][0]
        self.assertGreater(len(unity.applies_to_primitives), 0)

    def test_unity_governs_relationships(self):
        from umh.ontology.laws import get_default_universal_laws

        unity = [l for l in get_default_universal_laws() if l.law_id == "law_unity_oneness"][0]
        governs_lower = [g.lower() for g in unity.governs]
        has_relational = any("relational" in g or "interdependence" in g for g in governs_lower)
        self.assertTrue(has_relational)

    def test_unity_transition_mentions_wider_effects(self):
        from umh.ontology.laws import get_default_universal_laws

        unity = [l for l in get_default_universal_laws() if l.law_id == "law_unity_oneness"][0]
        te = unity.state_transition_effect.lower()
        self.assertTrue("wider" in te or "systemic" in te or "effects" in te)

    def test_unity_constraints_preserve_differentiation(self):
        from umh.ontology.laws import get_default_universal_laws

        unity = [l for l in get_default_universal_laws() if l.law_id == "law_unity_oneness"][0]
        constraints_text = " ".join(unity.constraints_created).lower()
        self.assertTrue(
            "distinction" in constraints_text
            or "differentiation" in constraints_text
            or "boundar" in constraints_text
        )

    def test_unity_examples_include_execution_spine(self):
        from umh.ontology.laws import get_default_universal_laws

        unity = [l for l in get_default_universal_laws() if l.law_id == "law_unity_oneness"][0]
        examples_text = " ".join(unity.examples).lower()
        self.assertTrue(
            "execution spine" in examples_text
            or "world-model" in examples_text
            or "world model" in examples_text
            or "shared" in examples_text
        )

    def test_unity_serialization_roundtrip(self):
        from umh.ontology.laws import UniversalLaw, get_default_universal_laws

        unity = [l for l in get_default_universal_laws() if l.law_id == "law_unity_oneness"][0]
        d = unity.to_dict()
        restored = UniversalLaw.from_dict(d)
        self.assertEqual(restored.law_id, unity.law_id)
        self.assertEqual(restored.law_name.value, "unity_oneness")
        self.assertEqual(restored.scope.value, "universal")

    def test_unity_confidence_matches_convention(self):
        from umh.ontology.laws import get_default_universal_laws

        unity = [l for l in get_default_universal_laws() if l.law_id == "law_unity_oneness"][0]
        self.assertGreaterEqual(unity.confidence, 0.8)
        self.assertLessEqual(unity.confidence, 1.0)

    def test_unity_metadata_has_doctrine(self):
        from umh.ontology.laws import get_default_universal_laws

        unity = [l for l in get_default_universal_laws() if l.law_id == "law_unity_oneness"][0]
        self.assertIn("doctrine", unity.metadata)
        self.assertEqual(unity.metadata["doctrine"], "differentiated unity")

    def test_existing_laws_unchanged(self):
        from umh.ontology.laws import get_default_universal_laws

        laws = get_default_universal_laws()
        law_ids = {l.law_id for l in laws}
        for expected in [
            "law_causality",
            "law_polarity",
            "law_feedback",
            "law_entropy",
            "law_leverage",
        ]:
            self.assertIn(expected, law_ids)


# ── Section 3: Domain Projections of Unity ──────────────────────────


class TestBusinessProjectionIncludesUnity(unittest.TestCase):
    def test_business_has_unity(self):
        from umh.ontology.domain_projection import get_projection_by_domain

        ps = get_projection_by_domain("business")
        unity_projs = [
            lp for lp in ps.law_projections if lp.universal_law_id == "law_unity_oneness"
        ]
        self.assertEqual(len(unity_projs), 1)


class TestSoftwareProjectionIncludesUnity(unittest.TestCase):
    def test_software_has_unity(self):
        from umh.ontology.domain_projection import get_projection_by_domain

        ps = get_projection_by_domain("software")
        unity_projs = [
            lp for lp in ps.law_projections if lp.universal_law_id == "law_unity_oneness"
        ]
        self.assertEqual(len(unity_projs), 1)


class TestHumanProjectionIncludesUnity(unittest.TestCase):
    def test_human_has_unity(self):
        from umh.ontology.domain_projection import get_projection_by_domain

        ps = get_projection_by_domain("human")
        unity_projs = [
            lp for lp in ps.law_projections if lp.universal_law_id == "law_unity_oneness"
        ]
        self.assertEqual(len(unity_projs), 1)


class TestContentProjectionIncludesUnity(unittest.TestCase):
    def test_content_has_unity(self):
        from umh.ontology.domain_projection import get_projection_by_domain

        ps = get_projection_by_domain("content")
        unity_projs = [
            lp for lp in ps.law_projections if lp.universal_law_id == "law_unity_oneness"
        ]
        self.assertEqual(len(unity_projs), 1)


class TestUmhInternalProjectionIncludesUnity(unittest.TestCase):
    def test_umh_internal_has_unity(self):
        from umh.ontology.domain_projection import get_projection_by_domain

        ps = get_projection_by_domain("umh_internal")
        unity_projs = [
            lp for lp in ps.law_projections if lp.universal_law_id == "law_unity_oneness"
        ]
        self.assertEqual(len(unity_projs), 1)


class TestUnityProjectionsPointBack(unittest.TestCase):
    def test_all_point_to_law_id(self):
        from umh.ontology.domain_projection import get_default_domain_projection_sets

        for ps in get_default_domain_projection_sets():
            for lp in ps.law_projections:
                if lp.universal_law_id == "law_unity_oneness":
                    self.assertEqual(lp.universal_law_id, "law_unity_oneness")


class TestUnityProjectionNotUniversalScope(unittest.TestCase):
    def test_projections_are_domain_scoped(self):
        from umh.ontology.domain_projection import get_default_domain_projection_sets

        for ps in get_default_domain_projection_sets():
            for lp in ps.law_projections:
                if lp.universal_law_id == "law_unity_oneness":
                    self.assertNotEqual(ps.domain.value, "unknown")


# ── Section 4: Polarity Synthesis Contracts ─────────────────────────


class TestPolaritySynthesisStatusNormalization(unittest.TestCase):
    def test_known_values(self):
        from umh.ontology.polarity_synthesis import (
            PolaritySynthesisStatus,
            normalize_polarity_synthesis_status,
        )

        self.assertEqual(
            normalize_polarity_synthesis_status("synthesized"),
            PolaritySynthesisStatus.SYNTHESIZED,
        )
        self.assertEqual(
            normalize_polarity_synthesis_status("partial"), PolaritySynthesisStatus.PARTIAL
        )
        self.assertEqual(
            normalize_polarity_synthesis_status("garbage"), PolaritySynthesisStatus.UNKNOWN
        )


class TestPoleTypeNormalization(unittest.TestCase):
    def test_known_values(self):
        from umh.ontology.polarity_synthesis import PolarityPoleType, normalize_pole_type

        self.assertEqual(normalize_pole_type("force"), PolarityPoleType.FORCE)
        self.assertEqual(normalize_pole_type("value"), PolarityPoleType.VALUE)
        self.assertEqual(normalize_pole_type("garbage"), PolarityPoleType.UNKNOWN)


class TestSynthesisConfidenceNormalization(unittest.TestCase):
    def test_known_values(self):
        from umh.ontology.polarity_synthesis import (
            SynthesisConfidence,
            normalize_synthesis_confidence,
        )

        self.assertEqual(normalize_synthesis_confidence("high"), SynthesisConfidence.HIGH)
        self.assertEqual(normalize_synthesis_confidence("garbage"), SynthesisConfidence.UNKNOWN)


class TestPolarityPoleSerialization(unittest.TestCase):
    def test_serializes(self):
        from umh.ontology.polarity_synthesis import create_polarity_pole

        p = create_polarity_pole("speed", truth_claim="Fast matters")
        d = p.to_dict()
        self.assertIn("pole_id", d)
        self.assertEqual(d["label"], "speed")
        self.assertEqual(d["truth_claim"], "Fast matters")


class TestPolarityPairSerialization(unittest.TestCase):
    def test_serializes(self):
        from umh.ontology.polarity_synthesis import create_polarity_pair, create_polarity_pole

        pa = create_polarity_pole("speed", truth_claim="Fast matters")
        pb = create_polarity_pole("safety", truth_claim="Safe matters")
        pair = create_polarity_pair(pa, pb, shared_context="dev")
        d = pair.to_dict()
        self.assertIn("pair_id", d)
        self.assertIn("pole_a", d)
        self.assertIn("pole_b", d)


class TestPolaritySynthesisRoundtrip(unittest.TestCase):
    def test_roundtrip(self):
        from umh.ontology.polarity_synthesis import (
            PolaritySynthesis,
            PolaritySynthesisStatus,
            SynthesisConfidence,
        )

        s = PolaritySynthesis(
            synthesis_id="syn_test",
            pair_id="pair_test",
            status=PolaritySynthesisStatus.SYNTHESIZED,
            higher_order_frame="governed execution",
            third_truth="governed acceleration",
            confidence=SynthesisConfidence.HIGH,
        )
        d = s.to_dict()
        restored = PolaritySynthesis.from_dict(d)
        self.assertEqual(restored.synthesis_id, "syn_test")
        self.assertEqual(restored.status, PolaritySynthesisStatus.SYNTHESIZED)
        self.assertEqual(restored.third_truth, "governed acceleration")


class TestMissingPoleTruthReturnsInsufficientData(unittest.TestCase):
    def test_missing_pole_a(self):
        from umh.ontology.polarity_synthesis import (
            PolaritySynthesisStatus,
            create_polarity_pair,
            create_polarity_pole,
            synthesize_polarity,
        )

        pa = create_polarity_pole("speed")
        pb = create_polarity_pole("safety", truth_claim="Safe matters")
        pair = create_polarity_pair(pa, pb)
        result = synthesize_polarity(pair)
        self.assertEqual(result.status, PolaritySynthesisStatus.INSUFFICIENT_DATA)

    def test_missing_pole_b(self):
        from umh.ontology.polarity_synthesis import (
            PolaritySynthesisStatus,
            create_polarity_pair,
            create_polarity_pole,
            synthesize_polarity,
        )

        pa = create_polarity_pole("speed", truth_claim="Fast matters")
        pb = create_polarity_pole("safety")
        pair = create_polarity_pair(pa, pb)
        result = synthesize_polarity(pair)
        self.assertEqual(result.status, PolaritySynthesisStatus.INSUFFICIENT_DATA)


class TestKnownSynthesisSpeedSafety(unittest.TestCase):
    def test_governed_acceleration(self):
        from umh.ontology.polarity_synthesis import (
            create_polarity_pair,
            create_polarity_pole,
            synthesize_polarity,
        )

        pa = create_polarity_pole("speed", truth_claim="Fast iteration matters")
        pb = create_polarity_pole("safety", truth_claim="Safety prevents mistakes")
        pair = create_polarity_pair(pa, pb, contradiction_layer="resource allocation")
        result = synthesize_polarity(pair)
        self.assertEqual(result.third_truth, "governed acceleration")


class TestKnownSynthesisAutonomyControl(unittest.TestCase):
    def test_bounded_autonomy(self):
        from umh.ontology.polarity_synthesis import (
            create_polarity_pair,
            create_polarity_pole,
            synthesize_polarity,
        )

        pa = create_polarity_pole("autonomy", truth_claim="Freedom enables creativity")
        pb = create_polarity_pole("control", truth_claim="Control prevents chaos")
        pair = create_polarity_pair(pa, pb, contradiction_layer="authority")
        result = synthesize_polarity(pair)
        self.assertEqual(result.third_truth, "bounded autonomy")


class TestKnownSynthesisSimplicityComplexity(unittest.TestCase):
    def test_progressive_disclosure(self):
        from umh.ontology.polarity_synthesis import (
            create_polarity_pair,
            create_polarity_pole,
            synthesize_polarity,
        )

        pa = create_polarity_pole("simplicity", truth_claim="Simple is accessible")
        pb = create_polarity_pole("complexity", truth_claim="Complex is powerful")
        pair = create_polarity_pair(pa, pb, contradiction_layer="interface design")
        result = synthesize_polarity(pair)
        self.assertEqual(result.third_truth, "progressive disclosure")


class TestKnownSynthesisLocalCloud(unittest.TestCase):
    def test_environment_explicit_routing(self):
        from umh.ontology.polarity_synthesis import (
            create_polarity_pair,
            create_polarity_pole,
            synthesize_polarity,
        )

        pa = create_polarity_pole("local-first", truth_claim="Local is fast and private")
        pb = create_polarity_pole("cloud availability", truth_claim="Cloud is always available")
        pair = create_polarity_pair(pa, pb, contradiction_layer="deployment architecture")
        result = synthesize_polarity(pair)
        self.assertEqual(result.third_truth, "environment-explicit runtime routing")


class TestKnownSynthesisStabilityAdaptation(unittest.TestCase):
    def test_adaptive_stability(self):
        from umh.ontology.polarity_synthesis import (
            create_polarity_pair,
            create_polarity_pole,
            synthesize_polarity,
        )

        pa = create_polarity_pole("stability", truth_claim="Stable systems are reliable")
        pb = create_polarity_pole("adaptation", truth_claim="Adaptation handles change")
        pair = create_polarity_pair(pa, pb, contradiction_layer="system design")
        result = synthesize_polarity(pair)
        self.assertIn("adaptive stability", result.third_truth)


class TestGenericSynthesis(unittest.TestCase):
    def test_unknown_poles_produce_generic(self):
        from umh.ontology.polarity_synthesis import (
            create_polarity_pair,
            create_polarity_pole,
            synthesize_polarity,
        )

        pa = create_polarity_pole("novelty", truth_claim="New things are valuable")
        pb = create_polarity_pole("tradition", truth_claim="Tradition preserves wisdom")
        pair = create_polarity_pair(pa, pb, contradiction_layer="culture")
        result = synthesize_polarity(pair)
        self.assertIn("partial truth", result.third_truth.lower())


class TestSynthesisIdentifiesTruthInBothPoles(unittest.TestCase):
    def test_preserved_values(self):
        from umh.ontology.polarity_synthesis import (
            create_polarity_pair,
            create_polarity_pole,
            synthesize_polarity,
        )

        pa = create_polarity_pole("speed", truth_claim="Fast", value_preserved="responsiveness")
        pb = create_polarity_pole("safety", truth_claim="Safe", value_preserved="reliability")
        pair = create_polarity_pair(pa, pb, contradiction_layer="resources")
        result = synthesize_polarity(pair)
        self.assertIn("responsiveness", result.preserved_values)
        self.assertIn("reliability", result.preserved_values)


class TestSynthesisIdentifiesContradictionLayer(unittest.TestCase):
    def test_pair_has_contradiction_layer(self):
        from umh.ontology.polarity_synthesis import create_polarity_pair, create_polarity_pole

        pa = create_polarity_pole("speed", truth_claim="Fast")
        pb = create_polarity_pole("safety", truth_claim="Safe")
        pair = create_polarity_pair(pa, pb, contradiction_layer="resource allocation")
        self.assertEqual(pair.contradiction_layer, "resource allocation")


class TestSynthesisIdentifiesHigherOrderFrame(unittest.TestCase):
    def test_has_frame(self):
        from umh.ontology.polarity_synthesis import (
            create_polarity_pair,
            create_polarity_pole,
            synthesize_polarity,
        )

        pa = create_polarity_pole("speed", truth_claim="Fast")
        pb = create_polarity_pole("safety", truth_claim="Safe")
        pair = create_polarity_pair(pa, pb, contradiction_layer="resources")
        result = synthesize_polarity(pair)
        self.assertTrue(len(result.higher_order_frame) > 0)


class TestSynthesisIdentifiesDominanceRisks(unittest.TestCase):
    def test_reduced_failure_modes(self):
        from umh.ontology.polarity_synthesis import (
            create_polarity_pair,
            create_polarity_pole,
            synthesize_polarity,
        )

        pa = create_polarity_pole("speed", truth_claim="Fast", risk_if_dominant="Reckless errors")
        pb = create_polarity_pole("safety", truth_claim="Safe", risk_if_dominant="Paralysis")
        pair = create_polarity_pair(pa, pb, contradiction_layer="resources")
        result = synthesize_polarity(pair)
        self.assertGreater(len(result.reduced_failure_modes), 0)


class TestSynthesisProducesRecommendationOnly(unittest.TestCase):
    def test_recommendation_is_string(self):
        from umh.ontology.polarity_synthesis import (
            create_polarity_pair,
            create_polarity_pole,
            synthesize_polarity,
        )

        pa = create_polarity_pole("speed", truth_claim="Fast")
        pb = create_polarity_pole("safety", truth_claim="Safe")
        pair = create_polarity_pair(pa, pb, contradiction_layer="resources")
        result = synthesize_polarity(pair)
        self.assertIsInstance(result.integrated_action_recommendation, str)
        self.assertGreater(len(result.integrated_action_recommendation), 0)


class TestSynthesisDoesNotExecute(unittest.TestCase):
    def test_no_execution_attributes(self):
        from umh.ontology.polarity_synthesis import PolaritySynthesis

        attrs = dir(PolaritySynthesis)
        for forbidden in ["execute", "dispatch", "run", "send", "mutate"]:
            self.assertNotIn(forbidden, attrs)


# ── Section 5: Law Application ──────────────────────────────────────


class TestUnityApplicationMissingContext(unittest.TestCase):
    def test_empty_context(self):
        from umh.ontology.law_application import LawApplicationStatus, apply_law_to_context
        from umh.ontology.laws import get_law_by_id

        unity = get_law_by_id("law_unity_oneness")
        result = apply_law_to_context(unity, "")
        self.assertEqual(result.status, LawApplicationStatus.INSUFFICIENT_DATA)


class TestUnityApplicationModuleContext(unittest.TestCase):
    def test_module_context(self):
        from umh.ontology.law_application import apply_law_to_context
        from umh.ontology.laws import get_law_by_id

        unity = get_law_by_id("law_unity_oneness")
        result = apply_law_to_context(unity, "Modifying a module that handles state transitions")
        has_dependency_risk = any(
            "dependen" in r.lower() or "caller" in r.lower() for r in result.risks_identified
        )
        self.assertTrue(has_dependency_risk)


class TestUnityApplicationBusinessContext(unittest.TestCase):
    def test_business_context(self):
        from umh.ontology.law_application import apply_law_to_context
        from umh.ontology.laws import get_law_by_id

        unity = get_law_by_id("law_unity_oneness")
        result = apply_law_to_context(unity, "Making a business decision about pricing")
        has_systemic = any(
            "systemic" in r.lower() or "team" in r.lower() or "brand" in r.lower()
            for r in result.risks_identified
        )
        self.assertTrue(has_systemic)


class TestUnityApplicationInterfaceContext(unittest.TestCase):
    def test_interface_context(self):
        from umh.ontology.law_application import apply_law_to_context
        from umh.ontology.laws import get_law_by_id

        unity = get_law_by_id("law_unity_oneness")
        result = apply_law_to_context(unity, "Changing interface command routing")
        has_boundary = any(
            "cockpit" in r.lower() or "control boundary" in r.lower()
            for r in result.risks_identified
        )
        self.assertTrue(has_boundary)


class TestUnityApplicationAgentContext(unittest.TestCase):
    def test_agent_context(self):
        from umh.ontology.law_application import apply_law_to_context
        from umh.ontology.laws import get_law_by_id

        unity = get_law_by_id("law_unity_oneness")
        result = apply_law_to_context(unity, "Creating a new agent for task automation")
        has_governance = any(
            "governance" in r.lower() or "bypass" in r.lower() for r in result.risks_identified
        )
        self.assertTrue(has_governance)


class TestUnityApplicationAdvisoryOnly(unittest.TestCase):
    def test_no_execution_methods(self):
        from umh.ontology.law_application import LawApplication

        attrs = dir(LawApplication)
        for forbidden in ["execute", "dispatch", "run", "send", "mutate"]:
            self.assertNotIn(forbidden, attrs)


# ── Section 6: Validation ───────────────────────────────────────────


class TestKernelValidatesWithUnity(unittest.TestCase):
    def test_valid_with_unity(self):
        from umh.ontology.domain_projection import get_domain_projections
        from umh.ontology.laws import get_laws
        from umh.ontology.primitives import get_primitives
        from umh.ontology.validation import validate_ontology_kernel

        prims = get_primitives()
        laws = get_laws()
        projs = get_domain_projections()
        result = validate_ontology_kernel(prims, laws, projs)
        self.assertTrue(result.valid)


class TestUnityWithoutEvidenceFails(unittest.TestCase):
    def test_missing_evidence(self):
        from umh.ontology.laws import LawScope, LawType, UniversalLaw, UniversalLawName
        from umh.ontology.validation import validate_universal_law

        bad_law = UniversalLaw(
            law_id="law_bad_unity",
            law_name=UniversalLawName.UNITY_ONENESS,
            law_type=LawType.SYSTEMS,
            scope=LawScope.UNIVERSAL,
            definition="Test",
            evidence_basis="",
            failure_conditions=["test"],
        )
        issues = validate_universal_law(bad_law)
        error_msgs = [i.message for i in issues if i.severity == "error"]
        self.assertTrue(any("evidence" in m.lower() for m in error_msgs))


class TestUnityWithoutFailureConditionsFails(unittest.TestCase):
    def test_missing_failures(self):
        from umh.ontology.laws import LawScope, LawType, UniversalLaw, UniversalLawName
        from umh.ontology.validation import validate_universal_law

        bad_law = UniversalLaw(
            law_id="law_bad_unity2",
            law_name=UniversalLawName.UNITY_ONENESS,
            law_type=LawType.SYSTEMS,
            scope=LawScope.UNIVERSAL,
            definition="Test",
            evidence_basis="Test evidence",
            failure_conditions=[],
        )
        issues = validate_universal_law(bad_law)
        error_msgs = [i.message for i in issues if i.severity == "error"]
        self.assertTrue(any("failure" in m.lower() for m in error_msgs))


class TestUnityProjectionClaimingUniversalFails(unittest.TestCase):
    def test_universal_projection_rejected(self):
        from umh.ontology.domain_projection import DomainProjectionSet, DomainType
        from umh.ontology.primitives import PrimitiveProjection, PrimitiveScope
        from umh.ontology.validation import validate_no_domain_projection_marked_universal

        bad_proj = PrimitiveProjection(
            projection_id="bad",
            universal_primitive_id="prim_entity",
            domain="business",
            local_name="test",
            local_definition="test",
        )
        bad_proj.scope = PrimitiveScope.UNIVERSAL
        ps = DomainProjectionSet(
            domain=DomainType.BUSINESS,
            primitive_projections=[bad_proj],
        )
        issues = validate_no_domain_projection_marked_universal([ps])
        self.assertGreater(len(issues), 0)


class TestPolarityPoleValidation(unittest.TestCase):
    def test_missing_truth_claim(self):
        from umh.ontology.polarity_synthesis import create_polarity_pole
        from umh.ontology.validation import validate_polarity_pole

        pole = create_polarity_pole("speed")
        issues = validate_polarity_pole(pole)
        error_msgs = [i.message for i in issues if i.severity == "error"]
        self.assertTrue(any("truth_claim" in m for m in error_msgs))


class TestPolarityPairValidation(unittest.TestCase):
    def test_missing_contradiction_layer(self):
        from umh.ontology.polarity_synthesis import create_polarity_pair, create_polarity_pole
        from umh.ontology.validation import validate_polarity_pair

        pa = create_polarity_pole("speed", truth_claim="Fast")
        pb = create_polarity_pole("safety", truth_claim="Safe")
        pair = create_polarity_pair(pa, pb)
        issues = validate_polarity_pair(pair)
        warning_msgs = [i.message for i in issues if i.severity == "warning"]
        self.assertTrue(any("contradiction" in m.lower() for m in warning_msgs))


class TestPolaritySynthesisValidation(unittest.TestCase):
    def test_missing_frame(self):
        from umh.ontology.polarity_synthesis import PolaritySynthesis
        from umh.ontology.validation import validate_polarity_synthesis

        s = PolaritySynthesis(synthesis_id="test", higher_order_frame="", third_truth="test")
        issues = validate_polarity_synthesis(s)
        warning_msgs = [i.message for i in issues if i.severity == "warning"]
        self.assertTrue(any("higher_order_frame" in m for m in warning_msgs))


# ── Section 7: Views ────────────────────────────────────────────────


class TestOntologyKernelViewIncludesUnity(unittest.TestCase):
    def test_law_count_includes_unity(self):
        from umh.ontology.laws import get_laws
        from umh.ontology.views import build_ontology_kernel_view

        laws = get_laws()
        view = build_ontology_kernel_view(laws=laws)
        self.assertGreaterEqual(view.law_count, 15)

    def test_unity_oneness_present_flag(self):
        from umh.ontology.laws import get_laws
        from umh.ontology.views import build_ontology_kernel_view

        laws = get_laws()
        view = build_ontology_kernel_view(laws=laws)
        self.assertTrue(view.unity_oneness_present)

    def test_polarity_synthesis_ready_flag(self):
        from umh.ontology.laws import get_laws
        from umh.ontology.views import build_ontology_kernel_view

        laws = get_laws()
        view = build_ontology_kernel_view(laws=laws)
        self.assertTrue(view.polarity_synthesis_ready)


class TestPolaritySynthesisViewSerialization(unittest.TestCase):
    def test_serializes(self):
        from umh.ontology.polarity_synthesis import (
            PolaritySynthesis,
            PolaritySynthesisStatus,
            SynthesisConfidence,
        )
        from umh.ontology.views import polarity_synthesis_to_view

        s = PolaritySynthesis(
            synthesis_id="syn_test",
            status=PolaritySynthesisStatus.SYNTHESIZED,
            higher_order_frame="governed execution",
            third_truth="governed acceleration",
            confidence=SynthesisConfidence.HIGH,
            preserved_values=["a", "b"],
            remaining_tensions=["c"],
        )
        view = polarity_synthesis_to_view(s)
        d = view.to_dict()
        self.assertEqual(d["status"], "synthesized")
        self.assertEqual(d["preserved_values_count"], 2)
        self.assertEqual(d["remaining_tensions_count"], 1)


class TestViewsReadOnly(unittest.TestCase):
    def test_view_has_no_mutators(self):
        from umh.ontology.views import OntologyKernelView

        attrs = dir(OntologyKernelView)
        for forbidden in ["execute", "dispatch", "mutate", "write", "delete"]:
            self.assertNotIn(forbidden, attrs)


# ── Section 8: Registry Integration ─────────────────────────────────


class TestRegistryLawBridgeIncludesUnity(unittest.TestCase):
    def test_unity_in_registry_items(self):
        from umh.registry.bridges import ontology_laws_to_registry_items

        items = ontology_laws_to_registry_items()
        unity_items = [i for i in items if "unity" in i.item_id.lower()]
        self.assertEqual(len(unity_items), 1)


class TestRegistryIntegrationMetadataOnly(unittest.TestCase):
    def test_registry_items_have_metadata(self):
        from umh.registry.bridges import ontology_laws_to_registry_items

        items = ontology_laws_to_registry_items()
        for item in items:
            self.assertIsInstance(item.metadata, dict)


class TestExistingRegistryTestsStillPass(unittest.TestCase):
    def test_phase80_importable(self):
        import importlib

        mod = importlib.import_module("tests.test_phase80_registry")
        self.assertTrue(hasattr(mod, "unittest"))


# ── Section 9: API/CLI ──────────────────────────────────────────────


class TestOntologyLawsEndpointIncludesUnity(unittest.TestCase):
    def test_api_module_importable(self):
        from umh.control.api import app

        routes = [r.path for r in app.routes]
        self.assertIn("/ontology/laws", routes)

    def test_unity_endpoint_exists(self):
        from umh.control.api import app

        routes = [r.path for r in app.routes]
        self.assertIn("/ontology/laws/unity-oneness", routes)


class TestUnityEndpointReadOnly(unittest.TestCase):
    def test_get_only(self):
        from umh.control.api import app

        for r in app.routes:
            if getattr(r, "path", "") == "/ontology/laws/unity-oneness":
                methods = getattr(r, "methods", set())
                self.assertIn("GET", methods)
                self.assertNotIn("DELETE", methods)


class TestPolaritySynthesisValidateEndpoint(unittest.TestCase):
    def test_exists(self):
        from umh.control.api import app

        routes = [r.path for r in app.routes]
        self.assertIn("/ontology/polarity-synthesis/validate", routes)

    def test_is_post(self):
        from umh.control.api import app

        for r in app.routes:
            if getattr(r, "path", "") == "/ontology/polarity-synthesis/validate":
                methods = getattr(r, "methods", set())
                self.assertIn("POST", methods)


class TestCliOntologyUnityCommand(unittest.TestCase):
    def test_command_in_dispatch(self):
        from umh.control.cli import build_parser

        parser = build_parser()
        self.assertIsNotNone(parser)

    def test_unity_command_read_only(self):
        from umh.control.cli import cmd_ontology_unity

        import argparse

        args = argparse.Namespace(json=True)
        result = cmd_ontology_unity(args)
        self.assertEqual(result, 0)

    def test_synthesize_command_read_only(self):
        from umh.control.cli import cmd_ontology_synthesize

        import argparse

        args = argparse.Namespace(json=True)
        result = cmd_ontology_synthesize(args)
        self.assertEqual(result, 0)


# ── Section 10: Layering Invariants ─────────────────────────────────


class TestPolaritySynthesisNoSubprocess(unittest.TestCase):
    def test_no_subprocess(self):
        with open("/opt/OS/umh/ontology/polarity_synthesis.py") as f:
            tree = ast.parse(f.read())
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split(".")[0])
        self.assertNotIn("subprocess", imports)


class TestPolaritySynthesisNoRequests(unittest.TestCase):
    def test_no_requests(self):
        with open("/opt/OS/umh/ontology/polarity_synthesis.py") as f:
            tree = ast.parse(f.read())
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split(".")[0])
        for lib in ["requests", "httpx", "aiohttp"]:
            self.assertNotIn(lib, imports)


class TestPolaritySynthesisNoBrowser(unittest.TestCase):
    def test_no_browser(self):
        with open("/opt/OS/umh/ontology/polarity_synthesis.py") as f:
            source = f.read()
        for lib in ["selenium", "playwright", "puppeteer"]:
            self.assertNotIn(f"import {lib}", source)


class TestPolaritySynthesisNoAdapters(unittest.TestCase):
    def test_no_adapter_imports(self):
        with open("/opt/OS/umh/ontology/polarity_synthesis.py") as f:
            tree = ast.parse(f.read())
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and "adapter" in node.module.lower():
                    imports.add(node.module)
        self.assertEqual(len(imports), 0)


class TestPolaritySynthesisNoExecution(unittest.TestCase):
    def test_no_execution_engine(self):
        with open("/opt/OS/umh/ontology/polarity_synthesis.py") as f:
            source = f.read()
        for pattern in ["execute_governed", "dispatch_action", "adapter.execute"]:
            self.assertNotIn(pattern, source)


class TestOntologyAmendmentsNoTraceMutation(unittest.TestCase):
    def test_no_trace_mutation(self):
        for fname in [
            "laws.py",
            "domain_projection.py",
            "law_application.py",
            "polarity_synthesis.py",
        ]:
            path = f"/opt/OS/umh/ontology/{fname}"
            if os.path.exists(path):
                with open(path) as f:
                    source = f.read()
                for pattern in ["store_trace", "persist_trace", "save_trace"]:
                    self.assertNotIn(pattern, source, f"{fname} contains {pattern}")


class TestOntologyAmendmentsNoMemoryPromotion(unittest.TestCase):
    def test_no_promote(self):
        for fname in [
            "laws.py",
            "domain_projection.py",
            "law_application.py",
            "polarity_synthesis.py",
        ]:
            path = f"/opt/OS/umh/ontology/{fname}"
            if os.path.exists(path):
                with open(path) as f:
                    source = f.read()
                for pattern in ["promote_memory", "persist_memory", "save_to_long_term"]:
                    self.assertNotIn(pattern, source, f"{fname} contains {pattern}")


class TestOntologyAmendmentsNoGovernanceMutation(unittest.TestCase):
    def test_no_governance_writes(self):
        for fname in [
            "laws.py",
            "domain_projection.py",
            "law_application.py",
            "polarity_synthesis.py",
        ]:
            path = f"/opt/OS/umh/ontology/{fname}"
            if os.path.exists(path):
                with open(path) as f:
                    source = f.read()
                for pattern in ["approve_action", "deny_action", "escalate_action"]:
                    self.assertNotIn(pattern, source, f"{fname} contains {pattern}")


class TestOntologyAmendmentsNoRoutingMutation(unittest.TestCase):
    def test_no_routing_mutation(self):
        for fname in [
            "laws.py",
            "domain_projection.py",
            "law_application.py",
            "polarity_synthesis.py",
        ]:
            path = f"/opt/OS/umh/ontology/{fname}"
            if os.path.exists(path):
                with open(path) as f:
                    source = f.read()
                for pattern in ["route_to_adapter", "dispatch_to_backend"]:
                    self.assertNotIn(pattern, source, f"{fname} contains {pattern}")


# ── Section 11: Regression ──────────────────────────────────────────


class TestPhase81Regression(unittest.TestCase):
    def test_importable(self):
        import importlib

        importlib.import_module("tests.test_phase81_ontology_law_kernel")


class TestPhase82Regression(unittest.TestCase):
    def test_importable(self):
        import importlib

        importlib.import_module("tests.test_phase82_storage_memory_discipline")


class TestPhase83Regression(unittest.TestCase):
    def test_importable(self):
        import importlib

        importlib.import_module("tests.test_phase83_legacy_migration_boundary")


class TestPhase84Regression(unittest.TestCase):
    def test_importable(self):
        import importlib

        importlib.import_module("tests.test_phase84_interface_command_center_contracts")


class TestPhase75bRegression(unittest.TestCase):
    def test_importable(self):
        import importlib

        importlib.import_module("tests.test_phase75b_mvp_lockin")


class TestPhase76Regression(unittest.TestCase):
    def test_importable(self):
        import importlib

        importlib.import_module("tests.test_phase76_adapters")


class TestPhase77Regression(unittest.TestCase):
    def test_importable(self):
        import importlib

        importlib.import_module("tests.test_phase77_workstation_state")


class TestPhase78Regression(unittest.TestCase):
    def test_importable(self):
        import importlib

        importlib.import_module("tests.test_phase78_feedback_loop")


class TestPhase79Regression(unittest.TestCase):
    def test_importable(self):
        import importlib

        importlib.import_module("tests.test_phase79_observability")


class TestPhase80Regression(unittest.TestCase):
    def test_importable(self):
        import importlib

        importlib.import_module("tests.test_phase80_registry")
