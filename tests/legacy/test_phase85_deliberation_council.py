"""Phase 85 — Deliberation Council System v1 tests.

Covers: contracts, roles, request, perspective, evidence, gaps,
disagreement, scoring, aggregation, advisory, deliberation pipeline,
ontology bridge, views, registry, API/CLI, safety/layering, regression.
"""

import ast
import sys
import unittest

sys.path.insert(0, "/opt/OS")


# ══════════════════════════════════════════════════════════════════
# 1. Contract Normalization (12 tests)
# ════════════════════════════════��═════════════════════════════════


class TestContractNormalization(unittest.TestCase):
    def test_council_status_known(self):
        from umh.council.contracts import CouncilStatus, normalize_council_status

        self.assertEqual(normalize_council_status("draft"), CouncilStatus.DRAFT)
        self.assertEqual(normalize_council_status("convened"), CouncilStatus.CONVENED)
        self.assertEqual(normalize_council_status("advisory_issued"), CouncilStatus.ADVISORY_ISSUED)

    def test_council_status_unknown(self):
        from umh.council.contracts import CouncilStatus, normalize_council_status

        self.assertEqual(normalize_council_status("bogus"), CouncilStatus.UNKNOWN)

    def test_deliberation_domain_known(self):
        from umh.council.contracts import DeliberationDomain, normalize_deliberation_domain

        self.assertEqual(normalize_deliberation_domain("business"), DeliberationDomain.BUSINESS)
        self.assertEqual(
            normalize_deliberation_domain("umh_internal"), DeliberationDomain.UMH_INTERNAL
        )

    def test_deliberation_domain_normalizes_hyphens(self):
        from umh.council.contracts import DeliberationDomain, normalize_deliberation_domain

        self.assertEqual(
            normalize_deliberation_domain("umh-internal"), DeliberationDomain.UMH_INTERNAL
        )
        self.assertEqual(
            normalize_deliberation_domain("cross domain"), DeliberationDomain.CROSS_DOMAIN
        )

    def test_deliberation_domain_unknown(self):
        from umh.council.contracts import DeliberationDomain, normalize_deliberation_domain

        self.assertEqual(normalize_deliberation_domain("xyz"), DeliberationDomain.UNKNOWN)

    def test_urgency_level_normalization(self):
        from umh.council.contracts import UrgencyLevel, normalize_urgency_level

        self.assertEqual(normalize_urgency_level("critical"), UrgencyLevel.CRITICAL)
        self.assertEqual(normalize_urgency_level("nope"), UrgencyLevel.UNKNOWN)

    def test_confidence_level_normalization(self):
        from umh.council.contracts import ConfidenceLevel, normalize_confidence_level

        self.assertEqual(normalize_confidence_level("high"), ConfidenceLevel.HIGH)
        self.assertEqual(normalize_confidence_level("very_high"), ConfidenceLevel.VERY_HIGH)
        self.assertEqual(normalize_confidence_level("very-high"), ConfidenceLevel.VERY_HIGH)

    def test_evidence_strength_normalization(self):
        from umh.council.contracts import EvidenceStrength, normalize_evidence_strength

        self.assertEqual(normalize_evidence_strength("strong"), EvidenceStrength.STRONG)
        self.assertEqual(normalize_evidence_strength("bogus"), EvidenceStrength.UNKNOWN)

    def test_assumption_status_normalization(self):
        from umh.council.contracts import AssumptionStatus, normalize_assumption_status

        self.assertEqual(normalize_assumption_status("validated"), AssumptionStatus.VALIDATED)
        self.assertEqual(normalize_assumption_status("xyz"), AssumptionStatus.UNKNOWN)

    def test_clamp_score(self):
        from umh.council.contracts import clamp_score

        self.assertEqual(clamp_score(0.5), 0.5)
        self.assertEqual(clamp_score(-1.0), 0.0)
        self.assertEqual(clamp_score(2.0), 1.0)
        self.assertEqual(clamp_score("not_a_number"), 0.0)

    def test_evidence_item_roundtrip(self):
        from umh.council.contracts import EvidenceItem, EvidenceStrength

        ei = EvidenceItem(
            evidence_id="ev_1",
            claim="test claim",
            strength=EvidenceStrength.STRONG,
            source="test",
            confidence=0.9,
        )
        d = ei.to_dict()
        restored = EvidenceItem.from_dict(d)
        self.assertEqual(restored.claim, "test claim")
        self.assertEqual(restored.strength, EvidenceStrength.STRONG)

    def test_assumption_roundtrip(self):
        from umh.council.contracts import Assumption, AssumptionStatus

        a = Assumption(
            assumption_id="asm_1",
            statement="test assumption",
            status=AssumptionStatus.VALIDATED,
            basis="evidence",
            risk_if_wrong="bad things",
        )
        d = a.to_dict()
        restored = Assumption.from_dict(d)
        self.assertEqual(restored.statement, "test assumption")
        self.assertEqual(restored.status, AssumptionStatus.VALIDATED)


# ═════════���═══════════════════════════════��════════════════════════
# 2. Enum Completeness (5 tests)
# ═════════════════════════��════════════════════════════════════════


class TestEnumCompleteness(unittest.TestCase):
    def test_council_status_count(self):
        from umh.council.contracts import CouncilStatus

        self.assertGreaterEqual(len(CouncilStatus), 8)

    def test_deliberation_domain_count(self):
        from umh.council.contracts import DeliberationDomain

        self.assertGreaterEqual(len(DeliberationDomain), 7)

    def test_urgency_level_count(self):
        from umh.council.contracts import UrgencyLevel

        self.assertGreaterEqual(len(UrgencyLevel), 5)

    def test_council_role_type_count(self):
        from umh.council.roles import CouncilRoleType

        self.assertGreaterEqual(len(CouncilRoleType), 7)

    def test_disagreement_type_count(self):
        from umh.council.disagreement import DisagreementType

        self.assertGreaterEqual(len(DisagreementType), 8)


# ══════════════���═══════════════════════════════════════════════════
# 3. Roles (10 tests)
# ═══════════════════���══════════════════════════════════��═══════════


class TestCouncilRoles(unittest.TestCase):
    def test_default_roles_exist(self):
        from umh.council.roles import get_default_council_roles

        roles = get_default_council_roles()
        self.assertGreaterEqual(len(roles), 6)

    def test_chair_role_present(self):
        from umh.council.roles import CouncilRoleType, get_default_council_roles

        roles = get_default_council_roles()
        chair = [r for r in roles if r.role_type == CouncilRoleType.CHAIR]
        self.assertEqual(len(chair), 1)

    def test_strategist_role_present(self):
        from umh.council.roles import CouncilRoleType, get_default_council_roles

        roles = get_default_council_roles()
        strats = [r for r in roles if r.role_type == CouncilRoleType.STRATEGIST]
        self.assertEqual(len(strats), 1)

    def test_role_has_evaluation_criteria(self):
        from umh.council.roles import get_default_council_roles

        for role in get_default_council_roles():
            self.assertGreaterEqual(
                len(role.evaluation_criteria), 1, f"{role.role_id} missing criteria"
            )

    def test_role_has_blind_spots(self):
        from umh.council.roles import get_default_council_roles

        for role in get_default_council_roles():
            self.assertGreaterEqual(
                len(role.known_blind_spots), 1, f"{role.role_id} missing blind spots"
            )

    def test_role_has_perspective_lens(self):
        from umh.council.roles import get_default_council_roles

        for role in get_default_council_roles():
            self.assertTrue(role.perspective_lens, f"{role.role_id} missing lens")

    def test_role_to_dict(self):
        from umh.council.roles import get_default_council_roles

        role = get_default_council_roles()[0]
        d = role.to_dict()
        self.assertIn("role_id", d)
        self.assertIn("role_type", d)
        self.assertIn("weight", d)

    def test_role_from_dict(self):
        from umh.council.roles import CouncilRole

        data = {"role_id": "r1", "name": "Test", "role_type": "engineer", "weight": 1.5}
        role = CouncilRole.from_dict(data)
        self.assertEqual(role.name, "Test")
        self.assertEqual(role.weight, 1.5)

    def test_role_weight_clamped(self):
        from umh.council.roles import CouncilRole

        role = CouncilRole.from_dict({"weight": 999})
        self.assertLessEqual(role.weight, 5.0)

    def test_normalize_role_type(self):
        from umh.council.roles import CouncilRoleType, normalize_council_role_type

        self.assertEqual(normalize_council_role_type("risk_analyst"), CouncilRoleType.RISK_ANALYST)
        self.assertEqual(normalize_council_role_type("risk-analyst"), CouncilRoleType.RISK_ANALYST)
        self.assertEqual(normalize_council_role_type("bogus"), CouncilRoleType.UNKNOWN)


# ═══════════════════════════════════════════��══════════════════════
# 4. Deliberation Request (8 tests)
# ════════════════════════════════════════════════���═════════════════


class TestDeliberationRequest(unittest.TestCase):
    def test_create_request(self):
        from umh.council.request import create_deliberation_request

        req = create_deliberation_request("Should we ship?", context="Release decision")
        self.assertTrue(req.request_id.startswith("dreq_"))
        self.assertEqual(req.question, "Should we ship?")

    def test_request_to_dict(self):
        from umh.council.request import create_deliberation_request

        req = create_deliberation_request("Test Q")
        d = req.to_dict()
        self.assertIn("request_id", d)
        self.assertIn("question", d)
        self.assertIn("domain", d)

    def test_request_from_dict(self):
        from umh.council.request import DeliberationRequest

        data = {"question": "Q1", "domain": "software", "urgency": "high"}
        req = DeliberationRequest.from_dict(data)
        self.assertEqual(req.question, "Q1")
        self.assertEqual(req.domain.value, "software")
        self.assertEqual(req.urgency.value, "high")

    def test_validate_missing_question(self):
        from umh.council.request import create_deliberation_request, validate_deliberation_request

        req = create_deliberation_request("")
        issues = validate_deliberation_request(req)
        self.assertTrue(any("Missing question" in i for i in issues))

    def test_validate_unknown_domain(self):
        from umh.council.request import create_deliberation_request, validate_deliberation_request

        req = create_deliberation_request("Q?")
        issues = validate_deliberation_request(req)
        self.assertTrue(any("unknown" in i.lower() for i in issues))

    def test_request_with_laws_and_polarities(self):
        from umh.council.request import create_deliberation_request

        req = create_deliberation_request(
            "Test",
            relevant_laws=["law_unity_oneness"],
            relevant_polarities=["speed", "safety"],
        )
        self.assertEqual(req.relevant_laws, ["law_unity_oneness"])
        self.assertEqual(req.relevant_polarities, ["speed", "safety"])

    def test_request_constraints(self):
        from umh.council.request import create_deliberation_request

        req = create_deliberation_request("Q?", constraints=["budget < $1k"])
        self.assertEqual(req.constraints, ["budget < $1k"])

    def test_request_roundtrip(self):
        from umh.council.request import DeliberationRequest, create_deliberation_request

        req = create_deliberation_request("Roundtrip test", context="ctx")
        d = req.to_dict()
        restored = DeliberationRequest.from_dict(d)
        self.assertEqual(restored.question, "Roundtrip test")
        self.assertEqual(restored.context, "ctx")


# ══════════════���═════════════════════════════════════════════════���═
# 5. Perspective Reports (10 tests)
# ════════════════════��════════════════════════════════���════════════


class TestPerspectiveReports(unittest.TestCase):
    def _make_perspective(self, role_id="r1", position="Proceed", score=0.7):
        from umh.council.contracts import ConfidenceLevel, EvidenceItem, EvidenceStrength
        from umh.council.perspective import create_perspective_report

        return create_perspective_report(
            "req_1",
            role_id,
            position=position,
            reasoning="Good reasons",
            recommendation="Do it",
            evidence=[
                EvidenceItem(
                    evidence_id="ev_1",
                    claim="data supports",
                    strength=EvidenceStrength.MODERATE,
                    confidence=0.7,
                )
            ],
            confidence=ConfidenceLevel.MEDIUM,
            score=score,
        )

    def test_create_perspective(self):
        p = self._make_perspective()
        self.assertTrue(p.report_id.startswith("prpt_"))
        self.assertEqual(p.position, "Proceed")

    def test_perspective_to_dict(self):
        p = self._make_perspective()
        d = p.to_dict()
        self.assertIn("report_id", d)
        self.assertIn("evidence", d)
        self.assertEqual(len(d["evidence"]), 1)

    def test_perspective_from_dict(self):
        from umh.council.perspective import PerspectiveReport

        p = self._make_perspective()
        restored = PerspectiveReport.from_dict(p.to_dict())
        self.assertEqual(restored.position, "Proceed")
        self.assertEqual(len(restored.evidence), 1)

    def test_perspective_no_position_warning(self):
        from umh.council.contracts import ConfidenceLevel
        from umh.council.perspective import create_perspective_report

        p = create_perspective_report("req_1", "r1", confidence=ConfidenceLevel.LOW, score=0.3)
        self.assertTrue(any("No position" in w for w in p.warnings))

    def test_perspective_no_evidence_warning(self):
        from umh.council.contracts import ConfidenceLevel
        from umh.council.perspective import create_perspective_report

        p = create_perspective_report(
            "req_1", "r1", position="Yes", confidence=ConfidenceLevel.LOW, score=0.3
        )
        self.assertTrue(any("No evidence" in w for w in p.warnings))

    def test_validate_perspective_complete(self):
        from umh.council.perspective import validate_perspective_report

        p = self._make_perspective()
        issues = validate_perspective_report(p)
        self.assertEqual(len(issues), 0)

    def test_validate_perspective_missing_fields(self):
        from umh.council.perspective import PerspectiveReport, validate_perspective_report

        p = PerspectiveReport()
        issues = validate_perspective_report(p)
        self.assertGreaterEqual(len(issues), 3)

    def test_perspective_score_clamped(self):
        from umh.council.contracts import ConfidenceLevel
        from umh.council.perspective import create_perspective_report

        p = create_perspective_report(
            "r", "r1", position="X", score=5.0, confidence=ConfidenceLevel.LOW
        )
        self.assertLessEqual(p.score, 1.0)

    def test_perspective_dissents(self):
        from umh.council.contracts import ConfidenceLevel
        from umh.council.perspective import create_perspective_report

        p = create_perspective_report(
            "r",
            "r1",
            position="Yes",
            dissents=["But timing is bad"],
            confidence=ConfidenceLevel.MEDIUM,
            score=0.5,
        )
        self.assertEqual(p.dissents, ["But timing is bad"])

    def test_perspective_risks_and_opportunities(self):
        from umh.council.contracts import ConfidenceLevel
        from umh.council.perspective import create_perspective_report

        p = create_perspective_report(
            "r",
            "r1",
            position="Go",
            risks_identified=["Could fail"],
            opportunities_identified=["Could win"],
            confidence=ConfidenceLevel.HIGH,
            score=0.8,
        )
        self.assertEqual(p.risks_identified, ["Could fail"])
        self.assertEqual(p.opportunities_identified, ["Could win"])


# ═════════════���════════════════════════════════════════════════════
# 6. Evidence Assessment (7 tests)
# ════════════════════════════════════════════════��═════════════════


class TestEvidenceAssessment(unittest.TestCase):
    def _perspectives_with_evidence(self):
        from umh.council.contracts import ConfidenceLevel, EvidenceItem, EvidenceStrength
        from umh.council.perspective import create_perspective_report

        return [
            create_perspective_report(
                "req_1",
                "r1",
                position="Yes",
                evidence=[
                    EvidenceItem(
                        evidence_id="e1",
                        claim="c1",
                        strength=EvidenceStrength.STRONG,
                        confidence=0.9,
                    ),
                    EvidenceItem(
                        evidence_id="e2",
                        claim="c2",
                        strength=EvidenceStrength.MODERATE,
                        confidence=0.7,
                    ),
                ],
                confidence=ConfidenceLevel.HIGH,
                score=0.8,
            ),
            create_perspective_report(
                "req_1",
                "r2",
                position="No",
                evidence=[
                    EvidenceItem(
                        evidence_id="e3", claim="c3", strength=EvidenceStrength.WEAK, confidence=0.4
                    ),
                ],
                confidence=ConfidenceLevel.LOW,
                score=0.3,
            ),
        ]

    def test_assess_evidence_counts(self):
        from umh.council.evidence import assess_evidence

        result = assess_evidence("req_1", self._perspectives_with_evidence())
        self.assertEqual(result.total_evidence_count, 3)
        self.assertEqual(result.strong_count, 1)
        self.assertEqual(result.moderate_count, 1)

    def test_assess_evidence_average(self):
        from umh.council.evidence import assess_evidence

        result = assess_evidence("req_1", self._perspectives_with_evidence())
        self.assertGreater(result.average_strength_score, 0)

    def test_assess_no_evidence(self):
        from umh.council.contracts import ConfidenceLevel
        from umh.council.evidence import assess_evidence

        result = assess_evidence("req_1", [])
        self.assertEqual(result.total_evidence_count, 0)
        self.assertEqual(result.overall_confidence, ConfidenceLevel.LOW)

    def test_assess_confidence_level(self):
        from umh.council.evidence import assess_evidence

        result = assess_evidence("req_1", self._perspectives_with_evidence())
        self.assertIn(result.overall_confidence.value, ["low", "medium", "high"])

    def test_assess_gaps_detected(self):
        from umh.council.contracts import ConfidenceLevel
        from umh.council.evidence import assess_evidence
        from umh.council.perspective import create_perspective_report

        perspectives = [
            create_perspective_report(
                "r", "r1", position="X", confidence=ConfidenceLevel.LOW, score=0.3
            ),
        ]
        result = assess_evidence("r", perspectives)
        self.assertTrue(any("lack evidence" in g.lower() for g in result.gaps))

    def test_assess_to_dict(self):
        from umh.council.evidence import assess_evidence

        result = assess_evidence("req_1", self._perspectives_with_evidence())
        d = result.to_dict()
        self.assertIn("total_evidence_count", d)
        self.assertIn("overall_confidence", d)

    def test_assess_no_strong_warning(self):
        from umh.council.contracts import ConfidenceLevel, EvidenceItem, EvidenceStrength
        from umh.council.evidence import assess_evidence
        from umh.council.perspective import create_perspective_report

        perspectives = [
            create_perspective_report(
                "r",
                "r1",
                position="Yes",
                evidence=[
                    EvidenceItem(evidence_id="e1", claim="c", strength=EvidenceStrength.WEAK)
                ],
                confidence=ConfidenceLevel.LOW,
                score=0.3,
            )
        ]
        result = assess_evidence("r", perspectives)
        self.assertTrue(any("No strong" in w for w in result.warnings))


# ═══════════��═══════════════════════════���══════════════════════════
# 7. Gap Detection (8 tests)
# ════════════════════════���═══════════════════════════════��═════════


class TestGapDetection(unittest.TestCase):
    def _make_req(self):
        from umh.council.request import create_deliberation_request

        return create_deliberation_request("Test Q", context="test")

    def _make_roles(self):
        from umh.council.roles import get_default_council_roles

        return get_default_council_roles()

    def _make_perspective(self, role_id):
        from umh.council.contracts import ConfidenceLevel, EvidenceItem, EvidenceStrength
        from umh.council.perspective import create_perspective_report

        return create_perspective_report(
            "req_1",
            role_id,
            position="Yes",
            evidence=[
                EvidenceItem(evidence_id="e1", claim="c", strength=EvidenceStrength.MODERATE)
            ],
            confidence=ConfidenceLevel.MEDIUM,
            score=0.6,
        )

    def test_full_coverage(self):
        from umh.council.gaps import detect_gaps

        req = self._make_req()
        roles = self._make_roles()
        perspectives = [self._make_perspective(r.role_id) for r in roles]
        result = detect_gaps(req, roles, perspectives)
        self.assertEqual(result.coverage_score, 1.0)
        self.assertEqual(len(result.missing_roles), 0)

    def test_partial_coverage(self):
        from umh.council.gaps import detect_gaps

        req = self._make_req()
        roles = self._make_roles()
        perspectives = [self._make_perspective(roles[0].role_id)]
        result = detect_gaps(req, roles, perspectives)
        self.assertLess(result.coverage_score, 1.0)
        self.assertGreater(len(result.missing_roles), 0)

    def test_no_perspectives(self):
        from umh.council.gaps import detect_gaps

        req = self._make_req()
        roles = self._make_roles()
        result = detect_gaps(req, roles, [])
        self.assertEqual(result.coverage_score, 0.0)
        self.assertTrue(any("No perspectives" in w for w in result.warnings))

    def test_gap_severity(self):
        from umh.council.gaps import GapSeverity, detect_gaps

        req = self._make_req()
        roles = self._make_roles()
        result = detect_gaps(req, roles, [])
        critical_gaps = [g for g in result.gaps if g.severity == GapSeverity.CRITICAL]
        self.assertGreaterEqual(len(critical_gaps), 1)

    def test_evidence_gap(self):
        from umh.council.contracts import ConfidenceLevel
        from umh.council.gaps import detect_gaps
        from umh.council.perspective import create_perspective_report

        req = self._make_req()
        roles = self._make_roles()
        no_ev = create_perspective_report(
            "r",
            roles[0].role_id,
            position="Yes",
            confidence=ConfidenceLevel.LOW,
            score=0.3,
        )
        result = detect_gaps(req, roles, [no_ev])
        evidence_gaps = [g for g in result.gaps if "no evidence" in g.description.lower()]
        self.assertGreaterEqual(len(evidence_gaps), 1)

    def test_gap_to_dict(self):
        from umh.council.gaps import detect_gaps

        req = self._make_req()
        roles = self._make_roles()
        result = detect_gaps(req, roles, [])
        d = result.to_dict()
        self.assertIn("coverage_score", d)
        self.assertIn("gaps", d)

    def test_gap_has_recommendation(self):
        from umh.council.gaps import detect_gaps

        req = self._make_req()
        roles = self._make_roles()
        result = detect_gaps(req, roles, [])
        for gap in result.gaps:
            if gap.missing_role_id:
                self.assertTrue(gap.recommendation)

    def test_gap_analysis_id(self):
        from umh.council.gaps import detect_gaps

        req = self._make_req()
        roles = self._make_roles()
        result = detect_gaps(req, roles, [])
        self.assertTrue(result.analysis_id.startswith("gapan_"))


# ═════════════════���═══════════════════════════���════════════════════
# 8. Disagreement Mapping (8 tests)
# ══════════════════════════════════════════════════════════════════


class TestDisagreementMapping(unittest.TestCase):
    def _make_perspectives(self, score_a=0.8, score_b=0.2):
        from umh.council.contracts import ConfidenceLevel, EvidenceItem, EvidenceStrength
        from umh.council.perspective import create_perspective_report

        return [
            create_perspective_report(
                "r",
                "role_a",
                position="Proceed",
                evidence=[
                    EvidenceItem(evidence_id="e1", claim="c", strength=EvidenceStrength.STRONG)
                ],
                confidence=ConfidenceLevel.HIGH,
                score=score_a,
            ),
            create_perspective_report(
                "r",
                "role_b",
                position="Wait",
                evidence=[
                    EvidenceItem(evidence_id="e2", claim="c2", strength=EvidenceStrength.MODERATE)
                ],
                confidence=ConfidenceLevel.MEDIUM,
                score=score_b,
            ),
        ]

    def test_divergent_scores_detected(self):
        from umh.council.disagreement import map_disagreements

        result = map_disagreements("r", self._make_perspectives(0.9, 0.1))
        self.assertGreaterEqual(result.total_count, 1)

    def test_similar_scores_no_disagreement(self):
        from umh.council.disagreement import map_disagreements

        result = map_disagreements("r", self._make_perspectives(0.5, 0.6))
        score_disagrs = [
            d for d in result.disagreements if d.synthesis_hint == "Score divergence detected"
        ]
        self.assertEqual(len(score_disagrs), 0)

    def test_single_perspective_no_disagreements(self):
        from umh.council.disagreement import map_disagreements

        perspectives = self._make_perspectives()[:1]
        result = map_disagreements("r", perspectives)
        self.assertTrue(any("Fewer than 2" in w for w in result.warnings))

    def test_dissents_become_disagreements(self):
        from umh.council.contracts import ConfidenceLevel, EvidenceItem, EvidenceStrength
        from umh.council.disagreement import map_disagreements
        from umh.council.perspective import create_perspective_report

        p = create_perspective_report(
            "r",
            "r1",
            position="Yes",
            dissents=["But maybe not"],
            evidence=[
                EvidenceItem(evidence_id="e1", claim="c", strength=EvidenceStrength.MODERATE)
            ],
            confidence=ConfidenceLevel.MEDIUM,
            score=0.5,
        )
        result = map_disagreements("r", [p, self._make_perspectives()[1]])
        dissent_disagrs = [
            d for d in result.disagreements if "self-identified" in (d.synthesis_hint or "")
        ]
        self.assertGreaterEqual(len(dissent_disagrs), 1)

    def test_consensus_possible(self):
        from umh.council.disagreement import map_disagreements

        result = map_disagreements("r", self._make_perspectives(0.6, 0.5))
        self.assertTrue(result.consensus_possible)

    def test_disagreement_to_dict(self):
        from umh.council.disagreement import map_disagreements

        result = map_disagreements("r", self._make_perspectives())
        d = result.to_dict()
        self.assertIn("disagreements", d)
        self.assertIn("consensus_possible", d)

    def test_disagreement_from_dict(self):
        from umh.council.disagreement import Disagreement

        data = {"role_a": "a", "role_b": "b", "severity": "significant"}
        d = Disagreement.from_dict(data)
        self.assertEqual(d.role_a, "a")
        self.assertEqual(d.severity.value, "significant")

    def test_no_perspectives(self):
        from umh.council.disagreement import map_disagreements

        result = map_disagreements("r", [])
        self.assertEqual(result.total_count, 0)


# ═════════════��══════════════════════════���═════════════════════════
# 9. Scoring (8 tests)
# ════════════════════════════════════════════════════════��═════════


class TestScoring(unittest.TestCase):
    def _make_perspectives_and_roles(self):
        from umh.council.contracts import ConfidenceLevel, EvidenceItem, EvidenceStrength
        from umh.council.perspective import create_perspective_report
        from umh.council.roles import get_default_council_roles

        roles = get_default_council_roles()
        perspectives = []
        for i, role in enumerate(roles[:3]):
            perspectives.append(
                create_perspective_report(
                    "r",
                    role.role_id,
                    position=f"P{i}",
                    evidence=[
                        EvidenceItem(
                            evidence_id=f"e{i}", claim=f"c{i}", strength=EvidenceStrength.MODERATE
                        )
                    ],
                    confidence=ConfidenceLevel.MEDIUM,
                    score=0.5 + i * 0.1,
                )
            )
        return perspectives, roles

    def test_scoring_produces_ranked(self):
        from umh.council.scoring import score_perspectives

        perspectives, roles = self._make_perspectives_and_roles()
        result = score_perspectives("r", perspectives, roles)
        self.assertEqual(len(result.scored_perspectives), 3)
        self.assertEqual(result.scored_perspectives[0].rank, 1)

    def test_scoring_top_role(self):
        from umh.council.scoring import score_perspectives

        perspectives, roles = self._make_perspectives_and_roles()
        result = score_perspectives("r", perspectives, roles)
        self.assertTrue(result.top_role_id)

    def test_scoring_weights_applied(self):
        from umh.council.scoring import score_perspectives

        perspectives, roles = self._make_perspectives_and_roles()
        result = score_perspectives("r", perspectives, roles)
        for sp in result.scored_perspectives:
            self.assertGreaterEqual(sp.role_weight, 0)

    def test_scoring_to_dict(self):
        from umh.council.scoring import score_perspectives

        perspectives, roles = self._make_perspectives_and_roles()
        result = score_perspectives("r", perspectives, roles)
        d = result.to_dict()
        self.assertIn("scored_perspectives", d)
        self.assertIn("top_role_id", d)

    def test_scoring_spread(self):
        from umh.council.scoring import score_perspectives

        perspectives, roles = self._make_perspectives_and_roles()
        result = score_perspectives("r", perspectives, roles)
        self.assertGreaterEqual(result.score_spread, 0)

    def test_scoring_no_perspectives(self):
        from umh.council.roles import get_default_council_roles
        from umh.council.scoring import score_perspectives

        result = score_perspectives("r", [], get_default_council_roles())
        self.assertTrue(any("No perspectives" in w for w in result.warnings))

    def test_scoring_confidence_factor(self):
        from umh.council.scoring import score_perspectives

        perspectives, roles = self._make_perspectives_and_roles()
        result = score_perspectives("r", perspectives, roles)
        for sp in result.scored_perspectives:
            self.assertGreater(sp.confidence_factor, 0)

    def test_scoring_weighted_score(self):
        from umh.council.scoring import score_perspectives

        perspectives, roles = self._make_perspectives_and_roles()
        result = score_perspectives("r", perspectives, roles)
        for sp in result.scored_perspectives:
            self.assertGreater(sp.weighted_score, 0)


# ════════���════════════════��═══════════════════════════════════���════
# 10. Aggregation (8 tests)
# ══════════════════════════════════════════════════════��═══════════


class TestAggregation(unittest.TestCase):
    def _run_pipeline(self, n_perspectives=3):
        from umh.council.contracts import ConfidenceLevel, EvidenceItem, EvidenceStrength
        from umh.council.disagreement import map_disagreements
        from umh.council.evidence import assess_evidence
        from umh.council.gaps import detect_gaps
        from umh.council.perspective import create_perspective_report
        from umh.council.request import create_deliberation_request
        from umh.council.roles import get_default_council_roles
        from umh.council.scoring import score_perspectives

        req = create_deliberation_request("Test Q", context="test")
        roles = get_default_council_roles()
        perspectives = []
        for role in roles[:n_perspectives]:
            perspectives.append(
                create_perspective_report(
                    req.request_id,
                    role.role_id,
                    position=f"{role.name} says yes",
                    reasoning=f"Because {role.perspective_lens}",
                    recommendation=f"Proceed with {role.name.lower()} considerations",
                    evidence=[
                        EvidenceItem(
                            evidence_id=f"e_{role.role_id}",
                            claim="data",
                            strength=EvidenceStrength.MODERATE,
                            confidence=0.7,
                        )
                    ],
                    confidence=ConfidenceLevel.MEDIUM,
                    score=0.6,
                )
            )

        ev = assess_evidence(req.request_id, perspectives)
        gaps = detect_gaps(req, roles, perspectives)
        disagr = map_disagreements(req.request_id, perspectives)
        scoring = score_perspectives(req.request_id, perspectives, roles)
        return req, perspectives, ev, gaps, disagr, scoring, roles

    def test_aggregate_produces_recommendation(self):
        from umh.council.aggregation import aggregate_perspectives

        req, perspectives, ev, gaps, disagr, scoring, _ = self._run_pipeline()
        result = aggregate_perspectives(req.request_id, perspectives, scoring, ev, gaps, disagr)
        self.assertTrue(result.primary_recommendation)

    def test_aggregate_has_rationale(self):
        from umh.council.aggregation import aggregate_perspectives

        req, perspectives, ev, gaps, disagr, scoring, _ = self._run_pipeline()
        result = aggregate_perspectives(req.request_id, perspectives, scoring, ev, gaps, disagr)
        self.assertTrue(result.supporting_rationale)

    def test_aggregate_confidence(self):
        from umh.council.aggregation import aggregate_perspectives

        req, perspectives, ev, gaps, disagr, scoring, _ = self._run_pipeline()
        result = aggregate_perspectives(req.request_id, perspectives, scoring, ev, gaps, disagr)
        self.assertIn(result.confidence.value, ["low", "medium", "high", "unknown"])

    def test_aggregate_consensus_strength(self):
        from umh.council.aggregation import aggregate_perspectives

        req, perspectives, ev, gaps, disagr, scoring, _ = self._run_pipeline()
        result = aggregate_perspectives(req.request_id, perspectives, scoring, ev, gaps, disagr)
        self.assertGreaterEqual(result.consensus_strength, 0.0)

    def test_aggregate_no_perspectives(self):
        from umh.council.aggregation import aggregate_perspectives
        from umh.council.disagreement import map_disagreements
        from umh.council.evidence import assess_evidence
        from umh.council.gaps import detect_gaps
        from umh.council.request import create_deliberation_request
        from umh.council.roles import get_default_council_roles
        from umh.council.scoring import score_perspectives

        req = create_deliberation_request("Q")
        roles = get_default_council_roles()
        ev = assess_evidence(req.request_id, [])
        gaps = detect_gaps(req, roles, [])
        disagr = map_disagreements(req.request_id, [])
        scoring = score_perspectives(req.request_id, [], roles)
        result = aggregate_perspectives(req.request_id, [], scoring, ev, gaps, disagr)
        self.assertIn("Insufficient", result.primary_recommendation)

    def test_aggregate_to_dict(self):
        from umh.council.aggregation import aggregate_perspectives

        req, perspectives, ev, gaps, disagr, scoring, _ = self._run_pipeline()
        result = aggregate_perspectives(req.request_id, perspectives, scoring, ev, gaps, disagr)
        d = result.to_dict()
        self.assertIn("primary_recommendation", d)
        self.assertIn("consensus_strength", d)

    def test_aggregate_roundtrip(self):
        from umh.council.aggregation import AggregatedRecommendation, aggregate_perspectives

        req, perspectives, ev, gaps, disagr, scoring, _ = self._run_pipeline()
        result = aggregate_perspectives(req.request_id, perspectives, scoring, ev, gaps, disagr)
        d = result.to_dict()
        restored = AggregatedRecommendation.from_dict(d)
        self.assertEqual(restored.primary_recommendation, result.primary_recommendation)

    def test_aggregate_next_actions(self):
        from umh.council.aggregation import aggregate_perspectives

        req, perspectives, ev, gaps, disagr, scoring, _ = self._run_pipeline()
        result = aggregate_perspectives(req.request_id, perspectives, scoring, ev, gaps, disagr)
        self.assertGreaterEqual(len(result.next_actions), 1)


# ══════════════════════════════════════════════════════════════════
# 11. Advisory (8 tests)
# ═══════════════════════════════���═══════════════════���══════════════


class TestAdvisory(unittest.TestCase):
    def _build_advisory(self):
        from umh.council.contracts import ConfidenceLevel, EvidenceItem, EvidenceStrength
        from umh.council.advisory import build_council_advisory
        from umh.council.aggregation import aggregate_perspectives
        from umh.council.disagreement import map_disagreements
        from umh.council.evidence import assess_evidence
        from umh.council.gaps import detect_gaps
        from umh.council.perspective import create_perspective_report
        from umh.council.request import create_deliberation_request
        from umh.council.roles import get_default_council_roles
        from umh.council.scoring import score_perspectives

        req = create_deliberation_request("Advisory test Q", context="test")
        roles = get_default_council_roles()
        perspectives = []
        for role in roles:
            perspectives.append(
                create_perspective_report(
                    req.request_id,
                    role.role_id,
                    position=f"{role.name} agrees",
                    reasoning=f"Eval from {role.perspective_lens}",
                    recommendation=f"Proceed per {role.name}",
                    evidence=[
                        EvidenceItem(
                            evidence_id=f"e_{role.role_id}",
                            claim="OK",
                            strength=EvidenceStrength.MODERATE,
                            confidence=0.7,
                        )
                    ],
                    confidence=ConfidenceLevel.MEDIUM,
                    score=0.6,
                )
            )

        ev = assess_evidence(req.request_id, perspectives)
        gaps = detect_gaps(req, roles, perspectives)
        disagr = map_disagreements(req.request_id, perspectives)
        scoring = score_perspectives(req.request_id, perspectives, roles)
        rec = aggregate_perspectives(req.request_id, perspectives, scoring, ev, gaps, disagr)
        return build_council_advisory(
            req.request_id, rec, scoring, ev, gaps, disagr, len(perspectives)
        )

    def test_advisory_has_id(self):
        adv = self._build_advisory()
        self.assertTrue(adv.advisory_id.startswith("adv_"))

    def test_advisory_has_recommendation(self):
        adv = self._build_advisory()
        self.assertIsNotNone(adv.recommendation)

    def test_advisory_status(self):
        from umh.council.contracts import CouncilStatus

        adv = self._build_advisory()
        self.assertIn(adv.status, (CouncilStatus.ADVISORY_ISSUED, CouncilStatus.SYNTHESIZED))

    def test_advisory_is_actionable(self):
        adv = self._build_advisory()
        self.assertIsInstance(adv.is_actionable, bool)

    def test_advisory_scoring_summary(self):
        adv = self._build_advisory()
        self.assertIn("top_role", adv.scoring_summary)

    def test_advisory_evidence_summary(self):
        adv = self._build_advisory()
        self.assertIn("total_evidence", adv.evidence_summary)

    def test_advisory_to_dict(self):
        adv = self._build_advisory()
        d = adv.to_dict()
        self.assertIn("advisory_id", d)
        self.assertIn("is_actionable", d)

    def test_advisory_roundtrip(self):
        from umh.council.advisory import CouncilAdvisory

        adv = self._build_advisory()
        d = adv.to_dict()
        restored = CouncilAdvisory.from_dict(d)
        self.assertEqual(restored.request_id, adv.request_id)


# ════════��══════════════════════════════���══════════════════════════
# 12. Full Deliberation Pipeline (8 tests)
# ══════════════════���═══════════════════════════════════════════════


class TestDeliberationPipeline(unittest.TestCase):
    def _run_full(self, question="Should we launch?", n=6):
        from umh.council.contracts import ConfidenceLevel, EvidenceItem, EvidenceStrength
        from umh.council.deliberation import deliberate
        from umh.council.perspective import create_perspective_report
        from umh.council.request import create_deliberation_request
        from umh.council.roles import get_default_council_roles

        req = create_deliberation_request(question, context="pipeline test")
        roles = get_default_council_roles()
        perspectives = []
        for role in roles[:n]:
            perspectives.append(
                create_perspective_report(
                    req.request_id,
                    role.role_id,
                    position=f"{role.name}: go",
                    reasoning=f"Logic from {role.perspective_lens}",
                    recommendation=f"Consider {role.name}",
                    evidence=[
                        EvidenceItem(
                            evidence_id=f"e_{role.role_id}",
                            claim="data",
                            strength=EvidenceStrength.MODERATE,
                            confidence=0.7,
                        )
                    ],
                    confidence=ConfidenceLevel.MEDIUM,
                    score=0.6,
                )
            )
        return deliberate(req, perspectives, roles=roles)

    def test_deliberation_returns_advisory(self):
        from umh.council.advisory import CouncilAdvisory

        adv = self._run_full()
        self.assertIsInstance(adv, CouncilAdvisory)

    def test_deliberation_has_recommendation(self):
        adv = self._run_full()
        self.assertIsNotNone(adv.recommendation)
        self.assertTrue(adv.recommendation.primary_recommendation)

    def test_deliberation_perspective_count(self):
        adv = self._run_full()
        self.assertEqual(adv.perspective_count, 6)

    def test_deliberation_missing_question_rejected(self):
        from umh.council.contracts import CouncilStatus
        from umh.council.deliberation import deliberate
        from umh.council.request import create_deliberation_request

        req = create_deliberation_request("")
        adv = deliberate(req, [])
        self.assertEqual(adv.status, CouncilStatus.REJECTED)

    def test_deliberation_with_laws(self):
        from umh.council.contracts import ConfidenceLevel, EvidenceItem, EvidenceStrength
        from umh.council.deliberation import deliberate
        from umh.council.perspective import create_perspective_report
        from umh.council.request import create_deliberation_request
        from umh.council.roles import get_default_council_roles

        req = create_deliberation_request(
            "Test with laws",
            relevant_laws=["law_unity_oneness"],
        )
        roles = get_default_council_roles()[:2]
        perspectives = [
            create_perspective_report(
                req.request_id,
                roles[0].role_id,
                position="Yes",
                evidence=[
                    EvidenceItem(evidence_id="e1", claim="c", strength=EvidenceStrength.MODERATE)
                ],
                confidence=ConfidenceLevel.MEDIUM,
                score=0.6,
            )
        ]
        adv = deliberate(req, perspectives, roles=roles)
        self.assertIn("ontology_context", adv.metadata)

    def test_deliberation_with_polarities(self):
        from umh.council.contracts import ConfidenceLevel, EvidenceItem, EvidenceStrength
        from umh.council.deliberation import deliberate
        from umh.council.perspective import create_perspective_report
        from umh.council.request import create_deliberation_request
        from umh.council.roles import get_default_council_roles

        req = create_deliberation_request(
            "Speed vs safety",
            relevant_polarities=["speed", "safety"],
        )
        roles = get_default_council_roles()[:2]
        perspectives = [
            create_perspective_report(
                req.request_id,
                roles[0].role_id,
                position="Balance",
                evidence=[
                    EvidenceItem(evidence_id="e1", claim="c", strength=EvidenceStrength.MODERATE)
                ],
                confidence=ConfidenceLevel.MEDIUM,
                score=0.6,
            )
        ]
        adv = deliberate(req, perspectives, roles=roles)
        ctx = adv.metadata.get("ontology_context", {})
        self.assertGreaterEqual(len(ctx.get("polarity_syntheses", [])), 1)

    def test_deliberation_no_ontology(self):
        from umh.council.contracts import ConfidenceLevel, EvidenceItem, EvidenceStrength
        from umh.council.deliberation import deliberate
        from umh.council.perspective import create_perspective_report
        from umh.council.request import create_deliberation_request
        from umh.council.roles import get_default_council_roles

        req = create_deliberation_request("Simple Q")
        roles = get_default_council_roles()[:2]
        perspectives = [
            create_perspective_report(
                req.request_id,
                roles[0].role_id,
                position="Yes",
                evidence=[
                    EvidenceItem(evidence_id="e1", claim="c", strength=EvidenceStrength.MODERATE)
                ],
                confidence=ConfidenceLevel.MEDIUM,
                score=0.6,
            )
        ]
        adv = deliberate(req, perspectives, roles=roles, include_ontology=False)
        self.assertNotIn("ontology_context", adv.metadata)

    def test_deliberation_advisory_serializable(self):
        import json

        adv = self._run_full()
        d = adv.to_dict()
        serialized = json.dumps(d)
        self.assertIn("advisory_id", serialized)


# ═══════════════════════════════════════════════════��══════════════
# 13. Ontology Bridge (6 tests)
# ═════════════════════════════════════════════════════���════════════


class TestOntologyBridge(unittest.TestCase):
    def test_resolve_empty(self):
        from umh.council.ontology_bridge import resolve_ontology_context

        ctx = resolve_ontology_context("r")
        self.assertTrue(ctx.context_id.startswith("octx_"))
        self.assertEqual(len(ctx.matched_laws), 0)

    def test_resolve_with_valid_law(self):
        from umh.council.ontology_bridge import resolve_ontology_context

        ctx = resolve_ontology_context("r", relevant_laws=["law_unity_oneness"])
        self.assertGreaterEqual(len(ctx.matched_laws), 1)
        self.assertTrue(ctx.unity_relevant)

    def test_resolve_with_invalid_law(self):
        from umh.council.ontology_bridge import resolve_ontology_context

        ctx = resolve_ontology_context("r", relevant_laws=["law_nonexistent"])
        self.assertTrue(any("not found" in w for w in ctx.warnings))

    def test_resolve_with_polarities(self):
        from umh.council.ontology_bridge import resolve_ontology_context

        ctx = resolve_ontology_context("r", relevant_polarities=["speed", "safety"])
        self.assertGreaterEqual(len(ctx.polarity_syntheses), 1)

    def test_resolve_to_dict(self):
        from umh.council.ontology_bridge import resolve_ontology_context

        ctx = resolve_ontology_context("r", relevant_laws=["law_unity_oneness"])
        d = ctx.to_dict()
        self.assertIn("matched_laws", d)
        self.assertIn("unity_relevant", d)

    def test_resolve_odd_polarities(self):
        from umh.council.ontology_bridge import resolve_ontology_context

        ctx = resolve_ontology_context("r", relevant_polarities=["speed"])
        self.assertEqual(len(ctx.polarity_syntheses), 0)


# ════════════════════════════════════��═════════════════════════════
# 14. Views (7 tests)
# ══════════════════════════════════════════════════════���═══════════


class TestViews(unittest.TestCase):
    def test_council_health_view(self):
        from umh.council.views import build_council_health_view

        view = build_council_health_view()
        self.assertTrue(view.council_available)
        self.assertGreaterEqual(view.role_count, 6)

    def test_council_health_ontology_bridge(self):
        from umh.council.views import build_council_health_view

        view = build_council_health_view()
        self.assertTrue(view.ontology_bridge_ready)

    def test_council_health_polarity(self):
        from umh.council.views import build_council_health_view

        view = build_council_health_view()
        self.assertTrue(view.polarity_integration_ready)

    def test_council_health_to_dict(self):
        from umh.council.views import build_council_health_view

        d = build_council_health_view().to_dict()
        self.assertIn("council_available", d)
        self.assertIn("generated_at", d)

    def test_advisory_to_view(self):
        from umh.council.contracts import ConfidenceLevel, EvidenceItem, EvidenceStrength
        from umh.council.deliberation import deliberate
        from umh.council.perspective import create_perspective_report
        from umh.council.request import create_deliberation_request
        from umh.council.roles import get_default_council_roles
        from umh.council.views import advisory_to_view

        req = create_deliberation_request("View test")
        roles = get_default_council_roles()[:2]
        perspectives = [
            create_perspective_report(
                req.request_id,
                roles[0].role_id,
                position="Yes",
                evidence=[
                    EvidenceItem(evidence_id="e1", claim="c", strength=EvidenceStrength.MODERATE)
                ],
                confidence=ConfidenceLevel.MEDIUM,
                score=0.6,
            )
        ]
        adv = deliberate(req, perspectives, roles=roles)
        view = advisory_to_view(adv)
        self.assertTrue(view.advisory_id)

    def test_advisory_view_to_dict(self):
        from umh.council.views import CouncilAdvisoryView

        view = CouncilAdvisoryView(advisory_id="a1", status="advisory_issued", is_actionable=True)
        d = view.to_dict()
        self.assertEqual(d["advisory_id"], "a1")
        self.assertTrue(d["is_actionable"])

    def test_health_view_default_roles_flag(self):
        from umh.council.views import build_council_health_view

        view = build_council_health_view()
        self.assertTrue(view.default_roles_present)


# ════════════════��══════════════════════════════���══════════════════
# 15. Registry Integration (5 tests)
# ═════════════════════════��═════════════════════════════��══════════


class TestRegistryIntegration(unittest.TestCase):
    def test_registry_type_council_role(self):
        from umh.registry.contracts import RegistryType

        self.assertEqual(RegistryType.COUNCIL_ROLE.value, "council_role")

    def test_registry_type_council_advisory(self):
        from umh.registry.contracts import RegistryType

        self.assertEqual(RegistryType.COUNCIL_ADVISORY.value, "council_advisory")

    def test_council_roles_bridge(self):
        from umh.registry.bridges import council_roles_to_registry_items

        items = council_roles_to_registry_items()
        self.assertGreaterEqual(len(items), 6)
        self.assertEqual(items[0].registry_type.value, "council_role")

    def test_council_roles_in_catalog(self):
        from umh.registry.catalog import build_default_registry_catalog
        from umh.registry.contracts import RegistryType

        catalog = build_default_registry_catalog()
        council_items = [i for i in catalog.items if i.registry_type == RegistryType.COUNCIL_ROLE]
        self.assertGreaterEqual(len(council_items), 6)

    def test_registry_type_count(self):
        from umh.registry.contracts import RegistryType

        self.assertGreaterEqual(len(RegistryType), 33)


# ═══════════���═══════════════════════════��══════════════════════════
# 16. Observability Integration (4 tests)
# ═════════════════���════════════════════════════════════════════════


class TestObservabilityIntegration(unittest.TestCase):
    def test_system_status_has_council(self):
        from umh.observability.system_status import SystemStatus

        ss = SystemStatus()
        self.assertEqual(ss.council_status, "unknown")

    def test_system_status_to_dict_has_council(self):
        from umh.observability.system_status import SystemStatus

        d = SystemStatus().to_dict()
        self.assertIn("council_status", d)

    def test_build_system_status_includes_council(self):
        from umh.observability.system_status import build_system_status

        status = build_system_status()
        self.assertIn(status.council_status, ["ok", "degraded", "error", "unknown", "unavailable"])

    def test_check_council_status(self):
        from umh.observability.system_status import check_council_status

        cs = check_council_status()
        self.assertEqual(cs.name, "council")
        self.assertTrue(cs.available)


# ═════════════��═════════════════════════════��══════════════════════
# 17. API/CLI Endpoint Existence (8 tests)
# ══════════════════════���═══════════════════════════════════════════


class TestAPICLIEndpoints(unittest.TestCase):
    def test_api_council_status_exists(self):
        source = open("/opt/OS/umh/control/api.py").read()
        self.assertIn("/council/status", source)

    def test_api_council_roles_exists(self):
        source = open("/opt/OS/umh/control/api.py").read()
        self.assertIn("/council/roles", source)

    def test_api_council_deliberate_exists(self):
        source = open("/opt/OS/umh/control/api.py").read()
        self.assertIn("/council/deliberate", source)

    def test_api_council_safety_exists(self):
        source = open("/opt/OS/umh/control/api.py").read()
        self.assertIn("/council/safety", source)

    def test_cli_council_status_exists(self):
        source = open("/opt/OS/umh/control/cli.py").read()
        self.assertIn("council-status", source)

    def test_cli_council_roles_exists(self):
        source = open("/opt/OS/umh/control/cli.py").read()
        self.assertIn("council-roles", source)

    def test_cli_council_deliberate_exists(self):
        source = open("/opt/OS/umh/control/cli.py").read()
        self.assertIn("council-deliberate", source)

    def test_cli_council_safety_exists(self):
        source = open("/opt/OS/umh/control/cli.py").read()
        self.assertIn("council-safety", source)


# ═══════════════════���════════════════════════��════════════════════���
# 18. Safety / Layering (12 tests)
# ═════════════════��════════════════════════════════════════════════


class TestSafetyLayering(unittest.TestCase):
    def test_safety_all_modules_pass(self):
        from umh.council.safety import validate_council_module_boundaries

        result = validate_council_module_boundaries()
        self.assertTrue(result.safe, f"Violations: {result.violations}")

    def test_safety_module_count(self):
        from umh.council.safety import validate_council_module_boundaries

        result = validate_council_module_boundaries()
        self.assertGreaterEqual(result.modules_checked, 12)

    def _check_no_forbidden_imports(self, module_path):
        with open(module_path) as f:
            source = f.read()
        tree = ast.parse(source)
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported.add(node.module.split(".")[0])
        forbidden = {"subprocess", "requests", "httpx", "aiohttp", "selenium", "playwright"}
        for lib in forbidden:
            self.assertNotIn(lib, imported, f"Forbidden import {lib} in {module_path}")

    def test_no_subprocess_contracts(self):
        self._check_no_forbidden_imports("/opt/OS/umh/council/contracts.py")

    def test_no_subprocess_roles(self):
        self._check_no_forbidden_imports("/opt/OS/umh/council/roles.py")

    def test_no_subprocess_request(self):
        self._check_no_forbidden_imports("/opt/OS/umh/council/request.py")

    def test_no_subprocess_perspective(self):
        self._check_no_forbidden_imports("/opt/OS/umh/council/perspective.py")

    def test_no_subprocess_evidence(self):
        self._check_no_forbidden_imports("/opt/OS/umh/council/evidence.py")

    def test_no_subprocess_gaps(self):
        self._check_no_forbidden_imports("/opt/OS/umh/council/gaps.py")

    def test_no_subprocess_disagreement(self):
        self._check_no_forbidden_imports("/opt/OS/umh/council/disagreement.py")

    def test_no_subprocess_aggregation(self):
        self._check_no_forbidden_imports("/opt/OS/umh/council/aggregation.py")

    def test_no_subprocess_deliberation(self):
        self._check_no_forbidden_imports("/opt/OS/umh/council/deliberation.py")


# ════════════════════════════════════════���═════════════════════════
# 19. Regression (12 tests)
# ═════��═══════════════════════════════════════════��════════════════


class TestRegression(unittest.TestCase):
    def test_phase75b_importable(self):
        from umh.capabilities.definitions import list_capabilities

        self.assertTrue(callable(list_capabilities))

    def test_phase76_importable(self):
        from umh.execution.contract import ExecutionRequest

        self.assertTrue(ExecutionRequest)

    def test_phase77_importable(self):
        from umh.governance.authority import check_governance

        self.assertTrue(callable(check_governance))

    def test_phase78_importable(self):
        from umh.feedback.outcome import OutcomeRecord

        self.assertTrue(OutcomeRecord)

    def test_phase79_importable(self):
        from umh.observability.system_status import build_system_status

        self.assertTrue(callable(build_system_status))

    def test_phase80_importable(self):
        from umh.registry.contracts import RegistryItem

        self.assertTrue(RegistryItem)

    def test_phase81_importable(self):
        from umh.ontology.laws import get_laws

        self.assertTrue(callable(get_laws))

    def test_phase82_importable(self):
        from umh.storage.gateway import StorageGateway

        self.assertTrue(StorageGateway)

    def test_phase83_importable(self):
        from umh.migration.deprecation_registry import build_default_deprecation_registry

        self.assertTrue(callable(build_default_deprecation_registry))

    def test_phase84_importable(self):
        from umh.interface.surfaces import get_default_interface_surfaces

        self.assertTrue(callable(get_default_interface_surfaces))

    def test_phase84a_importable(self):
        from umh.ontology.polarity_synthesis import synthesize_polarity

        self.assertTrue(callable(synthesize_polarity))

    def test_phase85_importable(self):
        from umh.council.deliberation import deliberate

        self.assertTrue(callable(deliberate))


if __name__ == "__main__":
    unittest.main()
