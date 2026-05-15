# Phase 85B — Council Thinker Archetypes + Adversarial Deliberation Protocol v1

**Date**: 2026-05-03
**Status**: Complete
**Extends**: Phase 85 (Deliberation Council System v1)
**Tests**: 88 passing (Phase 85B), 1566 total regression (Phase 75B–85B)
**Hard rules**: 12

## Executive Summary

Phase 85B adds adversarial intelligence to the UMH council layer. 23 typed
thinker archetypes provide domain-specific advisory lenses. An adversarial
deliberation protocol detects false consensus, preserves minority positions,
runs red-team/blue-team analysis, assesses consensus quality, and synthesizes
all layers into an EnhancedCouncilAdvisory that never erases dissent. The
entire layer remains advisory-only: no execution, no mutation, no adapter
calls, no LLM calls. v1 uses deterministic rule-based analysis.

## Architecture

### Thinker Archetypes (23)

Each archetype is a typed advisory lens with a defined perspective, key
questions it asks, known blind spots, a weight modifier, and relevant domains.

| # | Archetype | Adversarial | Weight | Primary Domains |
|---|-----------|:-----------:|--------|-----------------|
| 1 | Contrarian | Yes | 1.0 | all |
| 2 | Skeptic | Yes | 1.0 | all |
| 3 | Red Team | Yes | 1.1 | security, infrastructure |
| 4 | Blue Team | No | 1.0 | security, infrastructure |
| 5 | First Principles | No | 1.1 | all |
| 6 | Leverage Maximizer | No | 1.0 | strategy, business |
| 7 | Future Backcaster | No | 0.9 | strategy, product |
| 8 | Operator | No | 1.1 | operations, infrastructure |
| 9 | Strategist | No | 1.0 | strategy, business |
| 10 | Technical Architect | No | 1.1 | software, infrastructure |
| 11 | Financial Analyst | No | 1.0 | business, strategy |
| 12 | Legal / Regulatory | No | 0.9 | legal, business |
| 13 | Security Reviewer | Yes | 1.1 | security, software |
| 14 | Customer Advocate | No | 1.0 | product, business |
| 15 | Product Reviewer | No | 1.0 | product, software |
| 16 | Systems Thinker | No | 1.0 | all |
| 17 | Ontology / Law Reviewer | No | 1.0 | ontology, philosophy |
| 18 | Memory Historian | No | 0.8 | all |
| 19 | Quality Judge | No | 1.0 | software, operations |
| 20 | Evidence Judge | Yes | 1.2 | all |
| 21 | Brand Strategist | No | 0.9 | brand, marketing |
| 22 | Growth / Distribution | No | 1.0 | marketing, business |
| 23 | Human Factor Reviewer | No | 0.9 | product, operations |

5 adversarial archetypes (Contrarian, Skeptic, Red Team, Security Reviewer,
Evidence Judge) are always eligible for inclusion in any deliberation.

### Archetype Assignment

`assign_archetypes_for_request(domain, urgency, include_adversarial, max_archetypes)`

- Filters archetypes by domain relevance
- Caps by urgency: CRITICAL -> 6, HIGH -> 8, default -> 12
- Always includes at least one adversarial if `include_adversarial=True`
- Deterministic selection — no randomness

### Adversarial Deliberation Protocol

Six analysis layers run after Phase 85 deliberation:

1. **Adversarial Assessment** — detects groupthink (score spread < 0.15,
   identical confidence, no dissents, no adversarial thinkers), generates
   structured challenges, calculates false consensus risk (0.0–1.0)

2. **Minority Report** — preserves dissenting positions by five criteria:
   low-score-high-evidence, adversarial perspectives, explicit dissents,
   contrarian/skeptic positions, score outliers (> 0.5 deviation from mean)

3. **Red Team Analysis** — finds vulnerabilities in the recommendation:
   evidence gaps, assumption failures, scope creep, adversary actions.
   Classifies findings as critical/high/medium/low. Determines overall
   risk level and safety flag.

4. **Blue Team Analysis** — proposes defenses for each red team finding:
   guardrails for evidence gaps, monitoring for assumption failures,
   fallbacks for other findings. Always adds circuit breakers for identified
   risks and a rollback trigger. Calculates reversibility score.

5. **Consensus Quality** — classifies agreement as GENUINE, WEAK, FALSE,
   or UNTESTED based on evidence backing, adversarial presence, dissent
   recording, confidence variation, and score spread.

6. **Synthesis Protocol** — combines all layers into EnhancedCouncilAdvisory.
   Preserves all dissent. Reports guardrails, non-actions, residual
   uncertainty, what-would-change triggers. Sets overall_safe flag.

### False Consensus Risk Formula

```
risk = 0.0
if score_spread < 0.1: risk += 0.3
elif score_spread < 0.2: risk += 0.15
risk += min(0.4, groupthink_indicators * 0.1)
if no_adversarial: risk += 0.2
if no_evidence: risk += 0.2
elif evidence < 50%: risk += 0.1
risk = min(1.0, risk)
```

### Consensus Quality Classification

```
FALSE:    >= 3 false indicators (no spread, no adversarial, opinion > evidence, no dissents, identical confidence)
GENUINE:  0 false indicators AND >= 3 genuine indicators (evidence-backed, adversarial, dissents, varied confidence, moderate spread)
UNTESTED: no adversarial thinker present
WEAK:     everything else
```

### Overall Safety Determination

```
overall_safe = red_team.recommendation_safe
           AND consensus.quality != FALSE
           AND adversarial.false_consensus_risk < 0.7
```

## New Files (7)

| File | Purpose |
|------|---------|
| `umh/council/archetypes.py` | 23 thinker profiles, assignment logic, stub report generation |
| `umh/council/adversarial.py` | False consensus detection, groupthink analysis, structured challenges |
| `umh/council/minority_report.py` | Minority position preservation by 5 criteria |
| `umh/council/red_team.py` | Attack vector analysis, vulnerability finding, safety assessment |
| `umh/council/blue_team.py` | Defense recommendations, reversibility scoring, guardrail counting |
| `umh/council/consensus.py` | Consensus quality classification (GENUINE/WEAK/FALSE/UNTESTED) |
| `umh/council/synthesis_protocol.py` | Enhanced advisory synthesis, dissent preservation |

## Modified Files (1)

| File | Change |
|------|--------|
| `umh/council/views.py` | Added EnhancedAdvisoryView, enhanced_advisory_to_view(), archetype count in health view |

## Test Coverage (13 classes, 88 tests)

| Class | Tests | Coverage |
|-------|-------|----------|
| TestThinkerArchetypes | 11 | Profile count, enum completeness, adversarial profiles, lens/asks/blind_spots, normalization, serialization, weight positivity |
| TestArchetypeAssignment | 7 | Domain assignment, adversarial inclusion/exclusion, urgency capping (CRITICAL<=6, HIGH<=8), domain-specific profiles |
| TestStubThinkerReports | 6 | Generation, evidence/assumptions/risks, adversarial metadata, all 23 archetypes generate |
| TestAdversarialAssessment | 10 | Empty perspectives, groupthink detection, false consensus risk, guardrails/non-actions, mode enum, low risk with adversarial, evidence deficit |
| TestMinorityReport | 5 | Empty perspectives, dissent preservation, adversarial preservation, serialization, reason type enum |
| TestRedTeam | 7 | Empty perspectives, evidence gaps, assumption failures, risk level, safe with good perspectives, serialization, attack vector enum |
| TestBlueTeam | 5 | Empty perspectives, red team defense mapping, rollback always present, serialization, defense type enum |
| TestConsensusAnalysis | 5 | Few perspectives, false consensus detection, genuine consensus, serialization, quality enum |
| TestSynthesisProtocol | 7 | Enhanced production, guardrails/non-actions, dissent preservation, base advisory, serialization, unsafe when red team critical |
| TestEnhancedViews | 4 | Enhanced advisory view, view serialization, health view archetype count, health view serialization |
| TestSafetyLayeringPhase85B | 9 | All 7 new modules pass safety, module count >= 21, AST checks on each module |
| TestPhase85Regression | 11 | All Phase 85 module imports verified |
| TestFullPipelineRegression | 1 | End-to-end: assign -> stubs -> deliberate -> adversarial -> minority -> red -> blue -> consensus -> synthesize -> verify |

## Key Design Decisions

1. **Adversarial-by-default** — every non-trivial deliberation includes at least
   one adversarial thinker. The system structurally prevents comfortable consensus
   by requiring opposition.

2. **Dissent never erased** — minority positions are preserved, not overridden.
   The MinorityReport captures low-score-high-evidence perspectives, adversarial
   views, explicit dissents, contrarian positions, and score outliers.

3. **Red/blue team pattern** — red team finds vulnerabilities, blue team proposes
   defenses. This mirrors real security practice and gives actionable guardrails.

4. **False consensus as first-class concern** — the system actively detects when
   agreement is artificial (identical scores, no adversarial, no evidence) and
   classifies consensus quality. FALSE consensus triggers warnings and non-actions.

5. **Synthesis preserves everything** — EnhancedCouncilAdvisory wraps (not
   replaces) the Phase 85 CouncilAdvisory. All adversarial data, minority
   positions, red/blue analysis, and consensus quality are preserved in the output.

6. **Urgency-aware archetype capping** — CRITICAL urgency limits to 6 archetypes,
   HIGH to 8, default to 12. This prevents analysis paralysis on time-sensitive
   decisions while maintaining thoroughness on strategic ones.

7. **Deterministic v1** — all analysis is rule-based. Stub thinker reports use
   archetype profiles to generate domain-appropriate perspectives without LLM calls.
   This makes the entire adversarial layer fully testable and reproducible.

8. **Advisory-only doctrine maintained** — Phase 85B adds zero execution capability.
   All 7 new modules pass the same AST-based forbidden import check as Phase 85.

## Hard Rules (12)

1. All 7 new modules must pass AST-based forbidden import checking
2. Adversarial archetypes must always be eligible for inclusion
3. At least one adversarial thinker required when include_adversarial=True
4. Minority positions must never be erased or overridden
5. False consensus risk must be calculated for every adversarial assessment
6. Red team must set recommendation_safe=False when critical findings exist
7. Blue team must always include a rollback defense
8. Consensus quality FALSE must trigger warnings in synthesis
9. EnhancedCouncilAdvisory must wrap (not replace) Phase 85 CouncilAdvisory
10. No LLM calls in any Phase 85B module
11. No execution, mutation, or adapter calls in any Phase 85B module
12. Phase 85 behavior must be fully preserved — zero regression

## Regression Results

```
Phase 75B–85B full regression: 1566 passed, 0 failed
Phase 85B specific: 88 passed, 0 failed
Safety validation: 21 modules checked, 0 violations
```
