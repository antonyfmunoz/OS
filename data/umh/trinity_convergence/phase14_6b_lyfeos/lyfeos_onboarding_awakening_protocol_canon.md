# LyfeOS Onboarding / Awakening Protocol Canon

**Phase:** 14.6B-LyfeOS
**Artifact:** 25 of 30
**operator_approved:** false
**allows_implementation:** false
**Date:** 2026-06-03

---

## Purpose

Canonical documentation of the LyfeOS onboarding architecture, including the 8-mission flow, archetype calibration, step tracking, completion logic, and the identified integration gap.

---

## Onboarding Overview

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

The LyfeOS onboarding is an 8-mission "Awakening Protocol" that builds a user's character sheet through guided self-assessment. Each mission populates a section of the `userProfile` table.

- **Route:** `/onboarding`
- **Component:** `OnboardingPage.tsx`
- **Tracking:** `userProfile.onboardingMission` (current mission 0-7), `userProfile.onboardingStep` (step within mission)
- **Completion:** `userProfile.onboardingCompleted` (boolean)
- **History:** `userProfile.completedOnboardingMissions` (integer array)

---

## Mission Map

### Mission 0: Access & Quickstart

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

| Aspect | Detail |
|--------|--------|
| Purpose | Basic account setup and demographic info |
| Profile fields populated | `ageRange`, `birthday`, `location`, `timezone` |
| Prerequisites | Account created, email verified |
| Outcome | User can access the app; basic context established |

---

### Mission 1: Archetype Calibration

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

| Aspect | Detail |
|--------|--------|
| Purpose | Determine user's archetype profile through a comprehensive quiz |
| Quiz length | 54 questions |
| Archetypes (6) | Warrior, Architect, Creator, Monarch, Oracle, Alchemist |
| Profile fields populated | `archetypePrimary`, `archetypeSecondary`, `archetypeShadow`, `archetypeScores` |
| Scoring | Each archetype receives a numeric score; top 3 ranked as primary/secondary/shadow |
| Outcome | User's character type is established; influences AI companion personality and recommendations |

#### Archetype Descriptions

| Archetype | Core Trait |
|-----------|-----------|
| Warrior | Discipline, action, willpower |
| Architect | Systems thinking, structure, strategy |
| Creator | Expression, innovation, craft |
| Monarch | Leadership, presence, authority |
| Oracle | Insight, wisdom, perception |
| Alchemist | Transformation, adaptation, synthesis |

---

### Mission 2: Identity

**Provenance:** SYNTHESIZED_CANON

| Aspect | Detail |
|--------|--------|
| Purpose | Map core identity patterns |
| Profile fields populated | `primaryInstincts`, `keyDrivers`, `shadowDistortions` |
| Outcome | User's fundamental drives and shadow patterns identified |

---

### Mission 3: Personality

**Provenance:** SYNTHESIZED_CANON

| Aspect | Detail |
|--------|--------|
| Purpose | Map beliefs, values, standards, habits, strengths, weaknesses |
| Profile fields populated | `coreBelief`, `limitingBelief`, `empoweringBelief`, `primaryValues`, `supportingValues`, `selfStandards`, `othersStandards`, `typicalPatterns`, `habits`, `urges`, `traitToReprogram`, `desiredTrait`, `strengths`, `weaknesses` |
| Outcome | Full personality profile for AI coaching and self-awareness |

---

### Mission 4: Vision & Goals

**Provenance:** SYNTHESIZED_CANON

| Aspect | Detail |
|--------|--------|
| Purpose | Define life vision across multiple time horizons |
| Profile fields populated | `lifeStage`, `desiredEmotion`, `vision90Day`, `vision90DayMetric`, `vision18Month`, `vision18MonthMetric`, `vision5Year`, `vision5YearChip`, `vision10Year`, `vision10YearLegacy`, `legacyMetric`, `mortalityInsights`, `lifeDomains`, `currentGoals` |
| Outcome | Vision goals created in `visionGoals` table; goal-tracking begins |

---

### Mission 5: Learning & Skills

**Provenance:** SYNTHESIZED_CANON

| Aspect | Detail |
|--------|--------|
| Purpose | Map learning style, competencies, and skill development plan |
| Profile fields populated | `learningStyle`, `integrationMethod`, `pastDeepDives`, `domainsOfCompetence`, `currentDeepDive`, `skillStackingPyramid`, `knowledgeAreas`, `skillsToAcquire`, `practiceCadence` |
| Outcome | AI companion can tailor advice to user's learning style and skill gaps |

---

### Mission 6: Projects & Creations

**Provenance:** SYNTHESIZED_CANON

| Aspect | Detail |
|--------|--------|
| Purpose | Map current projects and creative focus |
| Profile fields populated | `currentProjects`, `projectDefinition`, `activePhase`, `primaryCraft`, `primaryCraftWhy` |
| Outcome | Mission suggestions aligned to active projects |

---

### Mission 7: Body & Health

**Provenance:** SYNTHESIZED_CANON

| Aspect | Detail |
|--------|--------|
| Purpose | Map physical state, fitness, nutrition, and health goals |
| Profile fields populated | `physicalMetrics`, `fitnessMovement`, `nutritionRecovery`, `healthVitality`, `healthBaseline`, `injuries` |
| Outcome | Health-related missions and insights enabled |

---

## Onboarding Completion Logic

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

```
1. User starts at onboardingMission = 0, onboardingStep = 0
2. Each mission has N steps (varies by mission)
3. On step completion: onboardingStep increments
4. On mission completion:
   a. Mission number added to completedOnboardingMissions array
   b. onboardingMission increments
   c. onboardingStep resets to 0
5. After mission 7 completes:
   a. onboardingCompleted = true
   b. User redirected to Dashboard
   c. Auth check no longer redirects to /onboarding
```

### Tracking Fields

| Field | Type | Description |
|-------|------|-------------|
| `onboardingMission` | integer | Current active mission (0-7) |
| `onboardingStep` | integer | Current step within active mission |
| `onboardingCompleted` | boolean | True when all missions complete |
| `completedOnboardingMissions` | integer[] | Array of completed mission indices |
| `completedTutorials` | text[] | Array of completed tutorial slugs |
| `totalXP` | integer | XP accumulated during onboarding |

---

## Legacy setupMissionStatus

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

```json
{
  "archetype": "incomplete",
  "integrations": "incomplete",
  "future_self": "incomplete",
  "rituals": "incomplete",
  "pillars": "incomplete"
}
```

This is a legacy tracking field from an earlier onboarding design. Notable:

- **"integrations: incomplete"** shows the original intent to include an integration/synchronization onboarding mission
- This mission was never implemented because UMH did not exist when onboarding was built
- The current 8-mission flow does not include an integrations mission
- See artifact 26 (lyfeos_integrations_onboarding_gap.md) for detailed analysis

---

## Missing: Integrations / Synchronization Mission

**Provenance:** UMH_INTEGRATION_DEPENDENT_GAP

The original onboarding design intended to include an "Integrations" mission that would:
- Connect Google Calendar
- Connect other external services
- Set up synchronization preferences
- Configure data sources

This was deferred because:
1. UMH substrate did not exist when onboarding was built
2. Integration architecture was unclear
3. The 8 missions focus on self-knowledge, not tool setup

When UMH integration activates, a new onboarding mission (Mission 8+) should be added to:
- Connect the LyfeOS user to UMH identity
- Configure AI routing preferences
- Set privacy/data sharing boundaries
- Optionally connect external integrations (Google, etc.)

---

## Sections NOT Covered by Current Missions

**Provenance:** SYNTHESIZED_CANON

Several profile sections exist in the schema but do not have a clear mapping to missions 0-7:

| Section | Profile Fields | Status |
|---------|---------------|--------|
| Wealth & Work | `careerVocation`, `activeVentures`, `financialPosition`, etc. | May be populated post-onboarding or via later mission |
| Performance & Contribution | `collaborationStyle`, `roleOrientation`, etc. | May be populated post-onboarding |
| Style & Expression | `aesthetic`, `signatureExpression`, `creativeOutlets` | May be populated post-onboarding |
| History & Roots | `shadowPatterns`, `historicalContext`, `upbringing`, etc. | May be populated post-onboarding |
| Systems & Rituals | `idealDay`, `morningRituals`, `eveningRituals`, etc. | May be populated post-onboarding |
| Emotions & Coping | `emotionsToCultivate`, `copingPractices`, etc. | May be populated post-onboarding |

These sections likely represent planned but unimplemented onboarding missions (missions 8-12+), or they are populated through natural app usage and AI companion conversations rather than formal onboarding steps.

---

## Open Questions

| ID | Question | Classification |
|----|----------|----------------|
| ONBOARD-001 | Are missions 0-7 the final set, or are missions 8+ planned for the remaining profile sections? | OPEN_QUESTION_OPERATOR_DECISION_REQUIRED |
| ONBOARD-002 | Can users re-take onboarding missions to update their profile answers? | INFERRED_PROFESSIONAL_GAP |
| ONBOARD-003 | Does completing onboarding grant a special XP bonus or achievement? | INFERRED_PROFESSIONAL_GAP |
| ONBOARD-004 | Should the integrations mission be mission 8 or inserted earlier in the flow? | UMH_INTEGRATION_DEPENDENT_GAP |
