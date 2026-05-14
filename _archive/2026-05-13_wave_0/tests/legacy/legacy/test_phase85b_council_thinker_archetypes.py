"""Phase 85B — Council Thinker Archetypes + Adversarial Deliberation Protocol v1.

Tests for: archetypes, adversarial assessment, minority report,
red team, blue team, consensus analysis, synthesis protocol,
enhanced views, safety, and regression.
"""

import sys
import unittest

sys.path.insert(0, "/opt/OS")


class TestThinkerArchetypes(unittest.TestCase):
    """Test archetype definitions, profiles, and assignment."""

    def test_all_profiles_count(self):
        from umh.council.archetypes import get_all_thinker_profiles

        profiles = get_all_thinker_profiles()
        self.assertEqual(len(profiles), 23)

    def test_archetype_enum_has_unknown(self):
        from umh.council.archetypes import ThinkerArchetype

        self.assertIn(ThinkerArchetype.UNKNOWN, ThinkerArchetype)

    def test_archetype_enum_count(self):
        from umh.council.archetypes import ThinkerArchetype

        self.assertEqual(len(ThinkerArchetype), 24)

    def test_all_required_archetypes_present(self):
        from umh.council.archetypes import ThinkerArchetype

        required = [
            "CONTRARIAN",
            "SKEPTIC",
            "RED_TEAM",
            "BLUE_TEAM",
            "FIRST_PRINCIPLES",
            "LEVERAGE_MAXIMIZER",
            "FUTURE_BACKCASTER",
            "OPERATOR",
            "STRATEGIST",
            "TECHNICAL_ARCHITECT",
            "FINANCIAL_ANALYST",
            "LEGAL_REGULATORY",
            "SECURITY_REVIEWER",
            "CUSTOMER_ADVOCATE",
            "PRODUCT_REVIEWER",
            "SYSTEMS_THINKER",
            "ONTOLOGY_LAW_REVIEWER",
            "MEMORY_HISTORIAN",
            "QUALITY_JUDGE",
            "EVIDENCE_JUDGE",
            "BRAND_STRATEGIST",
            "GROWTH_DISTRIBUTION",
            "HUMAN_FACTOR_REVIEWER",
        ]
        for name in required:
            self.assertTrue(hasattr(ThinkerArchetype, name), f"Missing: {name}")

    def test_adversarial_profiles(self):
        from umh.council.archetypes import get_adversarial_profiles

        adv = get_adversarial_profiles()
        self.assertGreaterEqual(len(adv), 4)
        for p in adv:
            self.assertTrue(p.adversarial)

    def test_profiles_have_lens(self):
        from umh.council.archetypes import get_all_thinker_profiles

        for p in get_all_thinker_profiles():
            self.assertTrue(p.lens, f"{p.archetype.value} has no lens")

    def test_profiles_have_asks(self):
        from umh.council.archetypes import get_all_thinker_profiles

        for p in get_all_thinker_profiles():
            self.assertGreater(len(p.asks), 0, f"{p.archetype.value} has no asks")

    def test_profiles_have_blind_spots(self):
        from umh.council.archetypes import get_all_thinker_profiles

        for p in get_all_thinker_profiles():
            self.assertGreater(len(p.blind_spots), 0, f"{p.archetype.value} has no blind spots")

    def test_normalize_archetype(self):
        from umh.council.archetypes import normalize_thinker_archetype, ThinkerArchetype

        self.assertEqual(normalize_thinker_archetype("red_team"), ThinkerArchetype.RED_TEAM)
        self.assertEqual(normalize_thinker_archetype("UNKNOWN"), ThinkerArchetype.UNKNOWN)
        self.assertEqual(normalize_thinker_archetype("garbage"), ThinkerArchetype.UNKNOWN)

    def test_profile_to_dict(self):
        from umh.council.archetypes import get_all_thinker_profiles

        p = get_all_thinker_profiles()[0]
        d = p.to_dict()
        self.assertIn("archetype", d)
        self.assertIn("lens", d)
        self.assertIn("adversarial", d)

    def test_profile_weight_positive(self):
        from umh.council.archetypes import get_all_thinker_profiles

        for p in get_all_thinker_profiles():
            self.assertGreater(p.weight, 0.0)


class TestArchetypeAssignment(unittest.TestCase):
    """Test domain-based archetype selection."""

    def test_assign_returns_profiles(self):
        from umh.council.archetypes import assign_archetypes_for_request
        from umh.council.contracts import DeliberationDomain

        profiles = assign_archetypes_for_request(DeliberationDomain.BUSINESS)
        self.assertGreater(len(profiles), 0)

    def test_assign_includes_adversarial(self):
        from umh.council.archetypes import assign_archetypes_for_request
        from umh.council.contracts import DeliberationDomain

        profiles = assign_archetypes_for_request(
            DeliberationDomain.BUSINESS, include_adversarial=True
        )
        adversarial = [p for p in profiles if p.adversarial]
        self.assertGreater(len(adversarial), 0)

    def test_assign_respects_no_adversarial(self):
        from umh.council.archetypes import assign_archetypes_for_request
        from umh.council.contracts import DeliberationDomain

        profiles = assign_archetypes_for_request(
            DeliberationDomain.BUSINESS, include_adversarial=False
        )
        self.assertGreater(len(profiles), 0)

    def test_assign_critical_urgency_caps(self):
        from umh.council.archetypes import assign_archetypes_for_request
        from umh.council.contracts import DeliberationDomain, UrgencyLevel

        profiles = assign_archetypes_for_request(
            DeliberationDomain.CROSS_DOMAIN,
            urgency=UrgencyLevel.CRITICAL,
        )
        self.assertLessEqual(len(profiles), 6)

    def test_assign_high_urgency_caps(self):
        from umh.council.archetypes import assign_archetypes_for_request
        from umh.council.contracts import DeliberationDomain, UrgencyLevel

        profiles = assign_archetypes_for_request(
            DeliberationDomain.CROSS_DOMAIN,
            urgency=UrgencyLevel.HIGH,
        )
        self.assertLessEqual(len(profiles), 8)

    def test_assign_software_domain(self):
        from umh.council.archetypes import assign_archetypes_for_request
        from umh.council.contracts import DeliberationDomain

        profiles = assign_archetypes_for_request(DeliberationDomain.SOFTWARE)
        self.assertGreater(len(profiles), 0)

    def test_domain_profiles_for_umh(self):
        from umh.council.archetypes import get_profiles_for_domain
        from umh.council.contracts import DeliberationDomain

        profiles = get_profiles_for_domain(DeliberationDomain.UMH_INTERNAL)
        self.assertGreater(len(profiles), 0)


class TestStubThinkerReports(unittest.TestCase):
    """Test deterministic stub perspective generation."""

    def test_generate_stub_report(self):
        from umh.council.archetypes import generate_stub_thinker_report, get_all_thinker_profiles

        profile = get_all_thinker_profiles()[0]
        report = generate_stub_thinker_report("req1", profile, "Should we proceed?")
        self.assertTrue(report.report_id)
        self.assertEqual(report.request_id, "req1")
        self.assertTrue(report.position)

    def test_stub_has_evidence(self):
        from umh.council.archetypes import generate_stub_thinker_report, get_all_thinker_profiles

        profile = get_all_thinker_profiles()[0]
        report = generate_stub_thinker_report("req1", profile, "test?")
        self.assertGreater(len(report.evidence), 0)

    def test_stub_has_assumptions(self):
        from umh.council.archetypes import generate_stub_thinker_report, get_all_thinker_profiles

        profile = get_all_thinker_profiles()[0]
        report = generate_stub_thinker_report("req1", profile, "test?")
        self.assertGreater(len(report.assumptions), 0)

    def test_stub_adversarial_metadata(self):
        from umh.council.archetypes import generate_stub_thinker_report, get_adversarial_profiles

        profile = get_adversarial_profiles()[0]
        report = generate_stub_thinker_report("req1", profile, "test?")
        self.assertTrue(report.metadata.get("adversarial"))

    def test_stub_has_risks(self):
        from umh.council.archetypes import generate_stub_thinker_report, get_all_thinker_profiles

        profile = get_all_thinker_profiles()[0]
        report = generate_stub_thinker_report("req1", profile, "test?")
        self.assertGreater(len(report.risks_identified), 0)

    def test_all_archetypes_generate_reports(self):
        from umh.council.archetypes import generate_stub_thinker_report, get_all_thinker_profiles

        for profile in get_all_thinker_profiles():
            report = generate_stub_thinker_report("req1", profile, "test?")
            self.assertTrue(report.report_id, f"{profile.archetype.value} failed")


class TestAdversarialAssessment(unittest.TestCase):
    """Test false consensus detection, groupthink indicators, and challenges."""

    def _make_perspectives(self, *, count=4, uniform=True, with_evidence=True, adversarial=False):
        from umh.council.contracts import ConfidenceLevel, EvidenceItem, EvidenceStrength
        from umh.council.perspective import create_perspective_report

        perspectives = []
        for i in range(count):
            ev = []
            if with_evidence:
                ev = [
                    EvidenceItem(
                        evidence_id=f"e{i}", claim=f"claim {i}", strength=EvidenceStrength.MODERATE
                    )
                ]
            score = 0.7 if uniform else 0.3 + i * 0.2
            meta = {"adversarial": adversarial and i == 0}
            perspectives.append(
                create_perspective_report(
                    "req1",
                    f"role_{i}",
                    position=f"Position {i}",
                    evidence=ev,
                    confidence=ConfidenceLevel.MEDIUM,
                    score=score,
                    metadata=meta,
                )
            )
        return perspectives

    def test_empty_perspectives(self):
        from umh.council.adversarial import run_adversarial_assessment

        result = run_adversarial_assessment("req1", [])
        self.assertEqual(len(result.warnings), 1)

    def test_detects_groupthink_no_dissents(self):
        from umh.council.adversarial import run_adversarial_assessment

        perspectives = self._make_perspectives(count=4, uniform=True)
        result = run_adversarial_assessment("req1", perspectives)
        self.assertGreater(len(result.groupthink_indicators), 0)

    def test_false_consensus_risk_high_for_uniform(self):
        from umh.council.adversarial import run_adversarial_assessment

        perspectives = self._make_perspectives(count=4, uniform=True, with_evidence=False)
        result = run_adversarial_assessment("req1", perspectives)
        self.assertGreater(result.false_consensus_risk, 0.3)

    def test_has_guardrails(self):
        from umh.council.adversarial import run_adversarial_assessment

        perspectives = self._make_perspectives(count=3)
        result = run_adversarial_assessment("req1", perspectives)
        self.assertGreater(len(result.guardrails), 0)

    def test_has_non_actions(self):
        from umh.council.adversarial import run_adversarial_assessment

        perspectives = self._make_perspectives(count=3)
        result = run_adversarial_assessment("req1", perspectives)
        self.assertGreater(len(result.non_actions), 0)

    def test_has_what_would_change(self):
        from umh.council.adversarial import run_adversarial_assessment

        perspectives = self._make_perspectives(count=3)
        result = run_adversarial_assessment("req1", perspectives)
        self.assertGreater(len(result.what_would_change_recommendation), 0)

    def test_to_dict(self):
        from umh.council.adversarial import run_adversarial_assessment

        perspectives = self._make_perspectives(count=3)
        result = run_adversarial_assessment("req1", perspectives)
        d = result.to_dict()
        self.assertIn("false_consensus_risk", d)
        self.assertIn("guardrails", d)
        self.assertIn("non_actions", d)

    def test_mode_enum(self):
        from umh.council.adversarial import AdversarialMode, normalize_adversarial_mode

        self.assertEqual(normalize_adversarial_mode("full"), AdversarialMode.FULL)
        self.assertEqual(normalize_adversarial_mode("junk"), AdversarialMode.UNKNOWN)

    def test_low_false_consensus_with_adversarial(self):
        from umh.council.adversarial import run_adversarial_assessment

        perspectives = self._make_perspectives(count=4, uniform=False, adversarial=True)
        result = run_adversarial_assessment("req1", perspectives)
        self.assertLess(result.false_consensus_risk, 0.5)

    def test_challenge_for_evidence_deficit(self):
        from umh.council.adversarial import run_adversarial_assessment

        perspectives = self._make_perspectives(count=4, uniform=True, with_evidence=False)
        result = run_adversarial_assessment("req1", perspectives)
        challenge_types = [c.challenge_type for c in result.challenges]
        self.assertIn("evidence_deficit", challenge_types)


class TestMinorityReport(unittest.TestCase):
    """Test minority position preservation."""

    def _make_scored_perspectives(self):
        from umh.council.contracts import ConfidenceLevel, EvidenceItem, EvidenceStrength
        from umh.council.perspective import create_perspective_report
        from umh.council.scoring import score_perspectives
        from umh.council.roles import get_default_council_roles

        roles = get_default_council_roles()
        perspectives = []
        for i, role in enumerate(roles[:4]):
            ev = [
                EvidenceItem(evidence_id=f"e{i}", claim=f"c{i}", strength=EvidenceStrength.MODERATE)
            ]
            perspectives.append(
                create_perspective_report(
                    "req1",
                    role.role_id,
                    position=f"Position {i}",
                    evidence=ev,
                    confidence=ConfidenceLevel.MEDIUM,
                    score=0.3 + i * 0.2,
                )
            )
        scoring = score_perspectives("req1", perspectives, roles)
        return perspectives, scoring

    def test_empty_perspectives(self):
        from umh.council.minority_report import build_minority_report
        from umh.council.scoring import ScoringResult

        result = build_minority_report("req1", [], ScoringResult())
        self.assertEqual(len(result.entries), 0)

    def test_preserves_dissenting(self):
        from umh.council.minority_report import build_minority_report
        from umh.council.contracts import ConfidenceLevel, EvidenceItem, EvidenceStrength
        from umh.council.perspective import create_perspective_report
        from umh.council.scoring import score_perspectives
        from umh.council.roles import get_default_council_roles

        roles = get_default_council_roles()
        p1 = create_perspective_report(
            "req1",
            roles[0].role_id,
            position="A",
            score=0.8,
            evidence=[EvidenceItem(evidence_id="e1", claim="c1", strength=EvidenceStrength.STRONG)],
            confidence=ConfidenceLevel.HIGH,
        )
        p2 = create_perspective_report(
            "req1",
            roles[1].role_id,
            position="B",
            score=0.3,
            evidence=[
                EvidenceItem(evidence_id="e2", claim="c2", strength=EvidenceStrength.MODERATE),
                EvidenceItem(evidence_id="e3", claim="c3", strength=EvidenceStrength.MODERATE),
            ],
            confidence=ConfidenceLevel.MEDIUM,
            dissents=["I disagree with A"],
        )
        scoring = score_perspectives("req1", [p1, p2], roles)
        report = build_minority_report("req1", [p1, p2], scoring)
        self.assertTrue(report.dissent_preserved)

    def test_preserves_adversarial(self):
        from umh.council.minority_report import build_minority_report
        from umh.council.contracts import ConfidenceLevel, EvidenceItem, EvidenceStrength
        from umh.council.perspective import create_perspective_report
        from umh.council.scoring import score_perspectives
        from umh.council.roles import get_default_council_roles

        roles = get_default_council_roles()
        p1 = create_perspective_report(
            "req1",
            "archetype:contrarian",
            position="Against",
            score=0.4,
            evidence=[EvidenceItem(evidence_id="e1", claim="c1", strength=EvidenceStrength.WEAK)],
            confidence=ConfidenceLevel.LOW,
            metadata={"adversarial": True, "archetype": "contrarian"},
        )
        p2 = create_perspective_report(
            "req1",
            roles[0].role_id,
            position="For",
            score=0.8,
            evidence=[EvidenceItem(evidence_id="e2", claim="c2", strength=EvidenceStrength.STRONG)],
            confidence=ConfidenceLevel.HIGH,
        )
        scoring = score_perspectives("req1", [p1, p2], roles)
        report = build_minority_report("req1", [p1, p2], scoring)
        self.assertTrue(report.dissent_preserved)
        roles_in_entries = {e.role_id for e in report.entries}
        self.assertIn("archetype:contrarian", roles_in_entries)

    def test_to_dict(self):
        perspectives, scoring = self._make_scored_perspectives()
        from umh.council.minority_report import build_minority_report

        report = build_minority_report("req1", perspectives, scoring)
        d = report.to_dict()
        self.assertIn("entries", d)
        self.assertIn("dissent_preserved", d)

    def test_minority_reason_type_enum(self):
        from umh.council.minority_report import MinorityReasonType, normalize_minority_reason

        self.assertEqual(
            normalize_minority_reason("explicit_dissent"), MinorityReasonType.EXPLICIT_DISSENT
        )
        self.assertEqual(normalize_minority_reason("junk"), MinorityReasonType.UNKNOWN)


class TestRedTeam(unittest.TestCase):
    """Test red team vulnerability detection."""

    def _make_perspectives(self, *, with_evidence=True, with_risks=True, count=3):
        from umh.council.contracts import (
            ConfidenceLevel,
            EvidenceItem,
            EvidenceStrength,
            Assumption,
        )
        from umh.council.perspective import create_perspective_report

        perspectives = []
        for i in range(count):
            ev = []
            if with_evidence:
                ev = [
                    EvidenceItem(
                        evidence_id=f"e{i}", claim=f"c{i}", strength=EvidenceStrength.MODERATE
                    )
                ]
            risks = [f"Risk {i}"] if with_risks else []
            asms = [Assumption(assumption_id=f"a{i}", statement=f"Assume {i}", confidence=0.3)]
            perspectives.append(
                create_perspective_report(
                    "req1",
                    f"role_{i}",
                    position=f"Position {i}",
                    evidence=ev,
                    risks_identified=risks,
                    assumptions=asms,
                    score=0.7,
                    confidence=ConfidenceLevel.MEDIUM,
                )
            )
        return perspectives

    def test_empty_perspectives(self):
        from umh.council.red_team import run_red_team_analysis

        result = run_red_team_analysis("req1", [])
        self.assertEqual(len(result.warnings), 1)

    def test_finds_evidence_gaps(self):
        from umh.council.red_team import run_red_team_analysis

        perspectives = self._make_perspectives(with_evidence=False)
        result = run_red_team_analysis("req1", perspectives)
        vectors = [f.vector.value for f in result.findings]
        self.assertIn("evidence_gap", vectors)

    def test_finds_assumption_failures(self):
        from umh.council.red_team import run_red_team_analysis

        perspectives = self._make_perspectives()
        result = run_red_team_analysis("req1", perspectives)
        vectors = [f.vector.value for f in result.findings]
        self.assertIn("assumption_failure", vectors)

    def test_risk_level_with_no_evidence(self):
        from umh.council.red_team import run_red_team_analysis

        perspectives = self._make_perspectives(with_evidence=False, with_risks=False)
        result = run_red_team_analysis("req1", perspectives)
        self.assertIn(result.overall_risk_level, ["medium", "high", "critical"])

    def test_safe_with_good_perspectives(self):
        from umh.council.red_team import run_red_team_analysis
        from umh.council.contracts import ConfidenceLevel, EvidenceItem, EvidenceStrength
        from umh.council.perspective import create_perspective_report

        perspectives = [
            create_perspective_report(
                "req1",
                "r1",
                position="Good",
                evidence=[
                    EvidenceItem(evidence_id="e1", claim="c1", strength=EvidenceStrength.STRONG)
                ],
                risks_identified=["Some risk"],
                confidence=ConfidenceLevel.HIGH,
                score=0.8,
            )
        ]
        result = run_red_team_analysis("req1", perspectives)
        self.assertTrue(result.recommendation_safe)

    def test_to_dict(self):
        from umh.council.red_team import run_red_team_analysis

        perspectives = self._make_perspectives()
        result = run_red_team_analysis("req1", perspectives)
        d = result.to_dict()
        self.assertIn("findings", d)
        self.assertIn("overall_risk_level", d)

    def test_attack_vector_enum(self):
        from umh.council.red_team import AttackVector, normalize_attack_vector

        self.assertEqual(normalize_attack_vector("evidence_gap"), AttackVector.EVIDENCE_GAP)
        self.assertEqual(normalize_attack_vector("junk"), AttackVector.UNKNOWN)


class TestBlueTeam(unittest.TestCase):
    """Test blue team defensive analysis."""

    def test_empty_perspectives(self):
        from umh.council.blue_team import run_blue_team_analysis

        result = run_blue_team_analysis("req1", [])
        self.assertEqual(len(result.warnings), 1)

    def test_produces_defenses_from_red_team(self):
        from umh.council.blue_team import run_blue_team_analysis
        from umh.council.red_team import run_red_team_analysis
        from umh.council.contracts import (
            ConfidenceLevel,
            EvidenceItem,
            EvidenceStrength,
            Assumption,
        )
        from umh.council.perspective import create_perspective_report

        perspectives = [
            create_perspective_report(
                "req1",
                "r1",
                position="P",
                assumptions=[Assumption(assumption_id="a1", statement="x", confidence=0.2)],
                confidence=ConfidenceLevel.MEDIUM,
                score=0.5,
            )
        ]
        rt = run_red_team_analysis("req1", perspectives)
        result = run_blue_team_analysis("req1", perspectives, red_team=rt)
        self.assertGreater(len(result.defenses), 0)

    def test_always_has_rollback(self):
        from umh.council.blue_team import run_blue_team_analysis
        from umh.council.contracts import ConfidenceLevel
        from umh.council.perspective import create_perspective_report

        perspectives = [
            create_perspective_report(
                "req1", "r1", position="P", confidence=ConfidenceLevel.MEDIUM, score=0.5
            )
        ]
        result = run_blue_team_analysis("req1", perspectives)
        types = [d.defense_type.value for d in result.defenses]
        self.assertIn("rollback", types)

    def test_to_dict(self):
        from umh.council.blue_team import run_blue_team_analysis
        from umh.council.contracts import ConfidenceLevel
        from umh.council.perspective import create_perspective_report

        perspectives = [
            create_perspective_report(
                "req1", "r1", position="P", confidence=ConfidenceLevel.MEDIUM, score=0.5
            )
        ]
        result = run_blue_team_analysis("req1", perspectives)
        d = result.to_dict()
        self.assertIn("defenses", d)
        self.assertIn("reversibility_score", d)

    def test_defense_type_enum(self):
        from umh.council.blue_team import DefenseType, normalize_defense_type

        self.assertEqual(normalize_defense_type("guardrail"), DefenseType.GUARDRAIL)
        self.assertEqual(normalize_defense_type("junk"), DefenseType.UNKNOWN)


class TestConsensusAnalysis(unittest.TestCase):
    """Test consensus quality assessment."""

    def _make_perspectives(self, *, count=4, uniform=True, with_evidence=True, adversarial=False):
        from umh.council.contracts import ConfidenceLevel, EvidenceItem, EvidenceStrength
        from umh.council.perspective import create_perspective_report

        perspectives = []
        for i in range(count):
            ev = []
            if with_evidence:
                ev = [
                    EvidenceItem(
                        evidence_id=f"e{i}", claim=f"c{i}", strength=EvidenceStrength.MODERATE
                    )
                ]
            score = 0.7 if uniform else 0.3 + i * 0.15
            meta = {"adversarial": adversarial and i == 0}
            conf = ConfidenceLevel.MEDIUM if not uniform else ConfidenceLevel.HIGH
            perspectives.append(
                create_perspective_report(
                    "req1",
                    f"role_{i}",
                    position=f"P{i}",
                    evidence=ev,
                    score=score,
                    confidence=conf,
                    metadata=meta,
                )
            )
        return perspectives

    def test_fewer_than_2(self):
        from umh.council.consensus import analyze_consensus, ConsensusQuality
        from umh.council.scoring import ScoringResult

        result = analyze_consensus("req1", [], ScoringResult())
        self.assertEqual(result.quality, ConsensusQuality.UNTESTED)

    def test_false_consensus_detected(self):
        from umh.council.consensus import analyze_consensus, ConsensusQuality
        from umh.council.scoring import score_perspectives
        from umh.council.roles import get_default_council_roles

        perspectives = self._make_perspectives(count=4, uniform=True, with_evidence=False)
        roles = get_default_council_roles()
        scoring = score_perspectives("req1", perspectives, roles)
        result = analyze_consensus("req1", perspectives, scoring)
        self.assertIn(result.quality, [ConsensusQuality.FALSE, ConsensusQuality.UNTESTED])

    def test_genuine_consensus(self):
        from umh.council.consensus import analyze_consensus, ConsensusQuality
        from umh.council.scoring import score_perspectives
        from umh.council.roles import get_default_council_roles
        from umh.council.contracts import ConfidenceLevel, EvidenceItem, EvidenceStrength
        from umh.council.perspective import create_perspective_report

        roles = get_default_council_roles()
        perspectives = []
        for i, role in enumerate(roles[:4]):
            ev = [
                EvidenceItem(evidence_id=f"e{i}", claim=f"c{i}", strength=EvidenceStrength.STRONG)
            ]
            conf = [
                ConfidenceLevel.HIGH,
                ConfidenceLevel.MEDIUM,
                ConfidenceLevel.HIGH,
                ConfidenceLevel.LOW,
            ][i]
            perspectives.append(
                create_perspective_report(
                    "req1",
                    role.role_id,
                    position=f"P{i}",
                    evidence=ev,
                    score=0.6 + i * 0.05,
                    confidence=conf,
                    dissents=["minor point"] if i == 2 else [],
                    metadata={"adversarial": i == 0},
                )
            )
        scoring = score_perspectives("req1", perspectives, roles)
        result = analyze_consensus("req1", perspectives, scoring)
        self.assertGreater(len(result.genuine_consensus_indicators), 0)

    def test_to_dict(self):
        from umh.council.consensus import analyze_consensus
        from umh.council.scoring import score_perspectives
        from umh.council.roles import get_default_council_roles

        perspectives = self._make_perspectives(count=3, uniform=False)
        roles = get_default_council_roles()
        scoring = score_perspectives("req1", perspectives, roles)
        result = analyze_consensus("req1", perspectives, scoring)
        d = result.to_dict()
        self.assertIn("quality", d)
        self.assertIn("consensus_score", d)

    def test_consensus_quality_enum(self):
        from umh.council.consensus import ConsensusQuality, normalize_consensus_quality

        self.assertEqual(normalize_consensus_quality("genuine"), ConsensusQuality.GENUINE)
        self.assertEqual(normalize_consensus_quality("junk"), ConsensusQuality.UNKNOWN)


class TestSynthesisProtocol(unittest.TestCase):
    """Test enhanced advisory synthesis."""

    def _run_full_pipeline(self):
        from umh.council.archetypes import (
            assign_archetypes_for_request,
            generate_stub_thinker_report,
        )
        from umh.council.contracts import DeliberationDomain, UrgencyLevel
        from umh.council.request import create_deliberation_request
        from umh.council.roles import get_default_council_roles
        from umh.council.deliberation import deliberate
        from umh.council.adversarial import run_adversarial_assessment
        from umh.council.minority_report import build_minority_report
        from umh.council.red_team import run_red_team_analysis
        from umh.council.blue_team import run_blue_team_analysis
        from umh.council.consensus import analyze_consensus
        from umh.council.scoring import score_perspectives

        request = create_deliberation_request(
            "Should we launch Initiate Arena this month?",
            domain=DeliberationDomain.BUSINESS,
            urgency=UrgencyLevel.HIGH,
        )
        profiles = assign_archetypes_for_request(DeliberationDomain.BUSINESS, UrgencyLevel.HIGH)
        perspectives = [
            generate_stub_thinker_report(request.request_id, p, request.question) for p in profiles
        ]
        roles = get_default_council_roles()
        advisory = deliberate(request, perspectives, roles=roles, include_ontology=False)
        scoring = score_perspectives(request.request_id, perspectives, roles)
        adv_assess = run_adversarial_assessment(request.request_id, perspectives)
        minority = build_minority_report(request.request_id, perspectives, scoring)
        rt = run_red_team_analysis(request.request_id, perspectives)
        bt = run_blue_team_analysis(request.request_id, perspectives, red_team=rt)
        cons = analyze_consensus(request.request_id, perspectives, scoring)
        return advisory, adv_assess, minority, rt, bt, cons

    def test_synthesize_produces_enhanced(self):
        from umh.council.synthesis_protocol import synthesize_enhanced_advisory

        advisory, adv, minority, rt, bt, cons = self._run_full_pipeline()
        enhanced = synthesize_enhanced_advisory(advisory, adv, minority, rt, bt, cons)
        self.assertTrue(enhanced.enhanced_id)

    def test_enhanced_has_guardrails(self):
        from umh.council.synthesis_protocol import synthesize_enhanced_advisory

        advisory, adv, minority, rt, bt, cons = self._run_full_pipeline()
        enhanced = synthesize_enhanced_advisory(advisory, adv, minority, rt, bt, cons)
        self.assertGreater(len(enhanced.guardrails), 0)

    def test_enhanced_has_non_actions(self):
        from umh.council.synthesis_protocol import synthesize_enhanced_advisory

        advisory, adv, minority, rt, bt, cons = self._run_full_pipeline()
        enhanced = synthesize_enhanced_advisory(advisory, adv, minority, rt, bt, cons)
        self.assertGreater(len(enhanced.non_actions), 0)

    def test_enhanced_preserves_dissent(self):
        from umh.council.synthesis_protocol import synthesize_enhanced_advisory

        advisory, adv, minority, rt, bt, cons = self._run_full_pipeline()
        enhanced = synthesize_enhanced_advisory(advisory, adv, minority, rt, bt, cons)
        self.assertIsInstance(enhanced.dissent_preserved, bool)

    def test_enhanced_has_base_advisory(self):
        from umh.council.synthesis_protocol import synthesize_enhanced_advisory

        advisory, adv, minority, rt, bt, cons = self._run_full_pipeline()
        enhanced = synthesize_enhanced_advisory(advisory, adv, minority, rt, bt, cons)
        self.assertIsNotNone(enhanced.base_advisory)

    def test_enhanced_to_dict(self):
        from umh.council.synthesis_protocol import synthesize_enhanced_advisory

        advisory, adv, minority, rt, bt, cons = self._run_full_pipeline()
        enhanced = synthesize_enhanced_advisory(advisory, adv, minority, rt, bt, cons)
        d = enhanced.to_dict()
        self.assertIn("guardrails", d)
        self.assertIn("non_actions", d)
        self.assertIn("residual_uncertainty", d)
        self.assertIn("what_would_change", d)
        self.assertIn("false_consensus_risk", d)
        self.assertIn("overall_safe", d)

    def test_enhanced_unsafe_when_red_team_critical(self):
        from umh.council.synthesis_protocol import synthesize_enhanced_advisory
        from umh.council.red_team import RedTeamReport

        advisory, adv, minority, rt, bt, cons = self._run_full_pipeline()
        rt_bad = RedTeamReport(
            report_id="bad",
            request_id="req1",
            critical_findings=2,
            high_findings=3,
            overall_risk_level="critical",
            recommendation_safe=False,
        )
        enhanced = synthesize_enhanced_advisory(advisory, adv, minority, rt_bad, bt, cons)
        self.assertFalse(enhanced.overall_safe)


class TestEnhancedViews(unittest.TestCase):
    """Test enhanced advisory view conversion."""

    def test_enhanced_advisory_to_view(self):
        from umh.council.views import enhanced_advisory_to_view, EnhancedAdvisoryView
        from umh.council.synthesis_protocol import EnhancedCouncilAdvisory

        enhanced = EnhancedCouncilAdvisory(enhanced_id="test")
        view = enhanced_advisory_to_view(enhanced)
        self.assertIsInstance(view, EnhancedAdvisoryView)
        self.assertEqual(view.enhanced_id, "test")

    def test_enhanced_view_to_dict(self):
        from umh.council.views import enhanced_advisory_to_view
        from umh.council.synthesis_protocol import EnhancedCouncilAdvisory

        enhanced = EnhancedCouncilAdvisory(enhanced_id="test", overall_safe=True)
        view = enhanced_advisory_to_view(enhanced)
        d = view.to_dict()
        self.assertIn("overall_safe", d)
        self.assertIn("false_consensus_risk", d)

    def test_health_view_has_archetype_count(self):
        from umh.council.views import build_council_health_view

        health = build_council_health_view()
        self.assertGreaterEqual(health.archetype_count, 23)

    def test_health_view_to_dict_has_archetype(self):
        from umh.council.views import build_council_health_view

        d = build_council_health_view().to_dict()
        self.assertIn("archetype_count", d)


class TestSafetyLayeringPhase85B(unittest.TestCase):
    """Verify all new Phase 85B modules pass safety checks."""

    def test_safety_all_modules_pass(self):
        from umh.council.safety import validate_council_module_boundaries

        result = validate_council_module_boundaries()
        self.assertTrue(result.safe, f"Violations: {result.violations}")

    def test_safety_module_count(self):
        from umh.council.safety import validate_council_module_boundaries

        result = validate_council_module_boundaries()
        self.assertGreaterEqual(result.modules_checked, 21)

    def test_no_subprocess_archetypes(self):
        import ast, pathlib

        src = pathlib.Path("/opt/OS/umh/council/archetypes.py").read_text()
        tree = ast.parse(src)
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    imports.add(a.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
        self.assertNotIn("subprocess", imports)
        self.assertNotIn("requests", imports)

    def test_no_subprocess_adversarial(self):
        import ast, pathlib

        src = pathlib.Path("/opt/OS/umh/council/adversarial.py").read_text()
        tree = ast.parse(src)
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    imports.add(a.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
        self.assertNotIn("subprocess", imports)
        self.assertNotIn("requests", imports)

    def test_no_subprocess_red_team(self):
        import ast, pathlib

        src = pathlib.Path("/opt/OS/umh/council/red_team.py").read_text()
        tree = ast.parse(src)
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    imports.add(a.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
        self.assertNotIn("subprocess", imports)
        self.assertNotIn("requests", imports)

    def test_no_subprocess_blue_team(self):
        import ast, pathlib

        src = pathlib.Path("/opt/OS/umh/council/blue_team.py").read_text()
        tree = ast.parse(src)
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    imports.add(a.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
        self.assertNotIn("subprocess", imports)
        self.assertNotIn("requests", imports)

    def test_no_subprocess_consensus(self):
        import ast, pathlib

        src = pathlib.Path("/opt/OS/umh/council/consensus.py").read_text()
        tree = ast.parse(src)
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    imports.add(a.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
        self.assertNotIn("subprocess", imports)
        self.assertNotIn("requests", imports)

    def test_no_subprocess_synthesis(self):
        import ast, pathlib

        src = pathlib.Path("/opt/OS/umh/council/synthesis_protocol.py").read_text()
        tree = ast.parse(src)
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    imports.add(a.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
        self.assertNotIn("subprocess", imports)
        self.assertNotIn("requests", imports)

    def test_no_subprocess_minority(self):
        import ast, pathlib

        src = pathlib.Path("/opt/OS/umh/council/minority_report.py").read_text()
        tree = ast.parse(src)
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    imports.add(a.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
        self.assertNotIn("subprocess", imports)
        self.assertNotIn("requests", imports)


class TestPhase85Regression(unittest.TestCase):
    """Verify Phase 85 modules still import and function correctly."""

    def test_phase85_deliberation(self):
        from umh.council.deliberation import deliberate

        self.assertTrue(callable(deliberate))

    def test_phase85_roles(self):
        from umh.council.roles import get_default_council_roles

        roles = get_default_council_roles()
        self.assertEqual(len(roles), 6)

    def test_phase85_advisory(self):
        from umh.council.advisory import CouncilAdvisory, build_council_advisory

        self.assertTrue(CouncilAdvisory)

    def test_phase85_scoring(self):
        from umh.council.scoring import score_perspectives

        self.assertTrue(callable(score_perspectives))

    def test_phase85_evidence(self):
        from umh.council.evidence import assess_evidence

        self.assertTrue(callable(assess_evidence))

    def test_phase85_gaps(self):
        from umh.council.gaps import detect_gaps

        self.assertTrue(callable(detect_gaps))

    def test_phase85_disagreement(self):
        from umh.council.disagreement import map_disagreements

        self.assertTrue(callable(map_disagreements))

    def test_phase85_views(self):
        from umh.council.views import advisory_to_view, build_council_health_view

        self.assertTrue(callable(advisory_to_view))
        self.assertTrue(callable(build_council_health_view))

    def test_phase85_safety(self):
        from umh.council.safety import validate_council_module_boundaries

        result = validate_council_module_boundaries()
        self.assertTrue(result.safe)

    def test_phase85_request(self):
        from umh.council.request import create_deliberation_request

        req = create_deliberation_request("test?")
        self.assertTrue(req.request_id)

    def test_phase85_perspective(self):
        from umh.council.perspective import create_perspective_report

        rep = create_perspective_report("r1", "role1", position="test")
        self.assertTrue(rep.report_id)


class TestFullPipelineRegression(unittest.TestCase):
    """Verify the full Phase 85 → 85B pipeline end-to-end."""

    def test_full_enhanced_pipeline(self):
        from umh.council.archetypes import (
            assign_archetypes_for_request,
            generate_stub_thinker_report,
        )
        from umh.council.contracts import DeliberationDomain, UrgencyLevel
        from umh.council.request import create_deliberation_request
        from umh.council.roles import get_default_council_roles
        from umh.council.deliberation import deliberate
        from umh.council.adversarial import run_adversarial_assessment
        from umh.council.minority_report import build_minority_report
        from umh.council.red_team import run_red_team_analysis
        from umh.council.blue_team import run_blue_team_analysis
        from umh.council.consensus import analyze_consensus
        from umh.council.scoring import score_perspectives
        from umh.council.synthesis_protocol import synthesize_enhanced_advisory

        request = create_deliberation_request(
            "Should we prioritize content production over sales calls?",
            domain=DeliberationDomain.BUSINESS,
            urgency=UrgencyLevel.MEDIUM,
        )
        profiles = assign_archetypes_for_request(DeliberationDomain.BUSINESS)
        perspectives = [
            generate_stub_thinker_report(request.request_id, p, request.question) for p in profiles
        ]
        roles = get_default_council_roles()
        advisory = deliberate(request, perspectives, roles=roles, include_ontology=False)
        scoring = score_perspectives(request.request_id, perspectives, roles)
        adv_assess = run_adversarial_assessment(request.request_id, perspectives)
        minority = build_minority_report(request.request_id, perspectives, scoring)
        rt = run_red_team_analysis(request.request_id, perspectives)
        bt = run_blue_team_analysis(request.request_id, perspectives, red_team=rt)
        cons = analyze_consensus(request.request_id, perspectives, scoring)
        enhanced = synthesize_enhanced_advisory(advisory, adv_assess, minority, rt, bt, cons)

        self.assertTrue(enhanced.enhanced_id)
        self.assertIsNotNone(enhanced.base_advisory)
        self.assertIsNotNone(enhanced.adversarial)
        self.assertIsNotNone(enhanced.minority)
        self.assertIsNotNone(enhanced.red_team)
        self.assertIsNotNone(enhanced.blue_team)
        self.assertIsNotNone(enhanced.consensus)
        self.assertGreater(len(enhanced.guardrails), 0)
        self.assertGreater(len(enhanced.non_actions), 0)

        d = enhanced.to_dict()
        self.assertIn("base_advisory", d)
        self.assertIn("adversarial", d)
        self.assertIn("minority", d)
        self.assertIn("red_team", d)
        self.assertIn("blue_team", d)
        self.assertIn("consensus", d)


if __name__ == "__main__":
    unittest.main()
