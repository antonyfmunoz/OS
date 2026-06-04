# LyfeOS Profile / Character Sheet Canon

**Phase:** 14.6B-LyfeOS
**Artifact:** 24 of 30
**operator_approved:** false
**allows_implementation:** false
**Date:** 2026-06-03

---

## Purpose

Canonical documentation of the full profile/character sheet architecture from the `userProfile` table schema, including all sections, onboarding mission mapping, display settings, and legacy fields.

---

## Schema Overview

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH (schema.ts lines 75-255)

- **Table:** `userProfile`
- **Primary key:** `id` (serial)
- **Scope key:** `userId` (integer, FK to users.id, unique per user)
- **Total columns:** 100+ fields organized across 13 named sections
- **Data types:** Mix of text, jsonb (arrays/objects), boolean, integer, timestamp

---

## Section Breakdown

### Mission 0: Access & Quickstart

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

| Field | Type | Description |
|-------|------|-------------|
| `ageRange` | text | "18-24", "25-34", "35-44", "45-54", "55-64", "65+" |
| `birthday` | text | ISO date string "YYYY-MM-DD" |
| `location` | text | Optional location text |
| `timezone` | text | IANA timezone string |

Basic demographic data collected during first onboarding mission.

---

### Mission 1: Archetype Calibration

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

| Field | Type | Description |
|-------|------|-------------|
| `archetypePrimary` | text | Warrior, Architect, Creator, Monarch, Oracle, Alchemist |
| `archetypeSecondary` | text | Second strongest archetype |
| `archetypeShadow` | text | Shadow archetype |
| `archetypeScores` | jsonb | { warrior: X, architect: X, creator: X, monarch: X, oracle: X, alchemist: X } |

6 archetypes determined by a 54-question quiz. Each user gets a primary, secondary, and shadow archetype with numeric scores for all six.

---

### Section 1: Identity

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

| Field | Type | Description |
|-------|------|-------------|
| `primaryInstincts` | jsonb | Array of instincts |
| `keyDrivers` | jsonb | Array of drivers |
| `shadowDistortions` | jsonb | Array of shadow patterns |

Core identity drivers and patterns. Populated during onboarding mission 2.

---

### Section 2: Personality

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

| Field | Type | Description |
|-------|------|-------------|
| `coreBelief` | text | Core belief statement |
| `limitingBelief` | text | Primary limiting belief |
| `empoweringBelief` | text | Primary empowering belief |
| `primaryValues` | jsonb | Array of top 3 values |
| `supportingValues` | jsonb | Additional supporting values |
| `selfStandards` | text | Standards held for self |
| `othersStandards` | text | Standards expected of others |
| `typicalPatterns` | text | Behavioral patterns |
| `habits` | jsonb | Array of habits |
| `urges` | text | Urges/impulses |
| `traitToReprogram` | text | Trait to change |
| `desiredTrait` | text | Target replacement trait |
| `strengths` | jsonb | Array of strengths |
| `weaknesses` | jsonb | Array of weaknesses |

Populated during onboarding mission 3.

---

### Section 3: Vision & Goals

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

| Field | Type | Description |
|-------|------|-------------|
| `lifeStage` | text | Awakening, Building, Mastering, Leading |
| `desiredEmotion` | text | Flow, Peace, Joy, Power, Love, Purpose |
| `vision90Day` | text | 90-day vision statement |
| `vision90DayMetric` | text | How to measure 90-day success |
| `vision18Month` | text | 18-month vision |
| `vision18MonthMetric` | text | 18-month success metric |
| `vision5Year` | text | 5-year vision |
| `vision5YearChip` | text | 5-year "chip" (key identifier) |
| `vision10Year` | text | 10-year vision |
| `vision10YearLegacy` | text | 10-year legacy goal |
| `legacyMetric` | text | Legacy success metric |
| `mortalityInsights` | jsonb | { reflection: "", takeaway: "" } |
| `lifeDomains` | jsonb | Ordered array of life domain priorities |
| `currentGoals` | jsonb | Array of current goals |

Populated during onboarding mission 4. Feeds into the `visionGoals` table for tracking.

---

### Section 4: Learning & Skills

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

| Field | Type | Description |
|-------|------|-------------|
| `learningStyle` | jsonb | { visual: X, auditory: X, reading: X, kinesthetic: X } |
| `integrationMethod` | text | How user integrates new knowledge |
| `pastDeepDives` | jsonb | Array of past research topics |
| `domainsOfCompetence` | jsonb | Array of competence domains |
| `currentDeepDive` | jsonb | { question: "", purpose: "", successCriteria: "" } |
| `skillStackingPyramid` | jsonb | { vocational: "", evolutionary: [], resonant: [], staticFoundational: [], seasonalFoundational: [] } |
| `knowledgeAreas` | jsonb | Array of knowledge areas |
| `skillsToAcquire` | jsonb | Array of skills to learn |
| `practiceCadence` | jsonb | { hoursPerWeek: X, note: "" } |

Populated during onboarding mission 5.

---

### Section 5: Projects & Creations

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

| Field | Type | Description |
|-------|------|-------------|
| `currentProjects` | jsonb | Array of { name, doneWhen } |
| `projectDefinition` | text | What "a project" means to this user |
| `activePhase` | text | Current project phase |
| `primaryCraft` | text | Primary craft/skill |
| `primaryCraftWhy` | text | Why this is the primary craft |

Populated during onboarding mission 6.

---

### Section 6: Body & Health

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

| Field | Type | Description |
|-------|------|-------------|
| `physicalMetrics` | jsonb | { height, weight, bodyType, distinctiveFeatures } |
| `fitnessMovement` | jsonb | { trainingStyle, movementPractices: [] } |
| `nutritionRecovery` | jsonb | { nutritionalApproach, recoveryPractices: [], stressRecoveryStyle } |
| `healthVitality` | jsonb | { conditions: [], energyPatterns, somaticAwareness, longevityFocus: [] } |
| `healthBaseline` | jsonb | { sleep: X, exercise: X, nutrition: X, priority: "" } |
| `injuries` | text | Current injuries/conditions |

Populated during onboarding mission 7.

---

### Section 7: Wealth & Work

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

| Field | Type | Description |
|-------|------|-------------|
| `careerVocation` | text | Career/vocation description |
| `activeVentures` | jsonb | Array of active ventures |
| `financialPosition` | jsonb | { income, expenses, savings, debt } |
| `financialConstraints` | jsonb | Array of constraints |
| `moneyConfidence` | jsonb | { score: 1-10, habitShift } |
| `moneyRelationship` | text | Relationship with money |
| `weeklyCapacity` | jsonb | { hours: X, cap: "" } |
| `energyDrains` | jsonb | Array of energy drains |
| `resources` | jsonb | { skills: bool, tools: bool, network: bool, financial: bool, time: bool } |
| `physicalEnvironment` | text | Work environment description |
| `physicalEnvironmentImpact` | text | How environment impacts work |
| `digitalEnvironment` | jsonb | Array of digital tools/environments |

---

### Section 8: Performance & Contribution

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

| Field | Type | Description |
|-------|------|-------------|
| `collaborationStyle` | text | How user collaborates |
| `roleOrientation` | text | Leader/follower/independent |
| `decisionOrientation` | text | Decision-making approach |
| `stressResponse` | text | How user handles stress |
| `optimalEnvironment` | text | Best working conditions |
| `greatestContribution` | text | Where user adds most value |

---

### Section 9: Style & Expression

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

| Field | Type | Description |
|-------|------|-------------|
| `aesthetic` | text | Personal aesthetic description |
| `signatureExpression` | text | Signature form of expression |
| `creativeOutlets` | jsonb | Array of creative outlets |

---

### History & Roots

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

| Field | Type | Description |
|-------|------|-------------|
| `shadowPatterns` | jsonb | { pattern, lesson } |
| `historicalContext` | jsonb | Timeline with age markers |
| `upbringing` | text | Upbringing description |
| `culturalContext` | text | Cultural background |
| `keyExperiences` | jsonb | { experience, outcomes } |

---

### Systems & Rituals

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

| Field | Type | Description |
|-------|------|-------------|
| `idealDay` | text | Ideal day description |
| `lockedHabit` | text | Most important locked habit |
| `idealWeek` | jsonb | Weekly structure |
| `yearlyCycles` | jsonb | Array of yearly cycles/rhythms |
| `morningRituals` | jsonb | Array of morning rituals |
| `eveningRituals` | jsonb | Array of evening rituals |
| `groundingRitual` | text | Grounding/centering ritual |
| `boundaries` | jsonb | { techOffTime, workHours, recoveryTime } |

---

### Emotions & Coping

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

| Field | Type | Description |
|-------|------|-------------|
| `emotionsToCultivate` | jsonb | Array of target emotions |
| `copingPractices` | text | Coping practices |
| `copingEssential` | text | Essential coping mechanism |
| `traitsToCultivate` | jsonb | Array of traits to develop |
| `beliefSystem` | jsonb | { empowering: [], limiting: [], core, strongest } |
| `dominantInstinct` | jsonb | { type, description, influence } |
| `decisionMakingStyles` | jsonb | Array of decision styles |
| `decisionMakingPrimary` | text | Primary decision style |
| `lifeRoles` | jsonb | Array of life roles |
| `definingRole` | text | Most defining role |
| `relationshipDrains` | text | What drains relationships |
| `conflictStyle` | text | Conflict handling style |
| `moneyMemory` | jsonb | { memory, impact } |
| `financialSecurity` | jsonb | { reflection, eliminate } |
| `financialHabits` | jsonb | { current: [], toReprogram: [] } |

---

## Character Affirmation

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

| Field | Type | Description |
|-------|------|-------------|
| `characterAffirmation` | text | AI-generated third-person narrative summarizing the user's character |

Generated by the AI companion using all profile data. A personalized narrative that reflects the user's archetype, values, strengths, goals, and journey.

---

## Display Settings (in userProfile)

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `blueLightFilter` | boolean | false | Blue light filter toggle |
| `hapticFeedback` | boolean | true | Mobile vibration feedback |
| `soundEffects` | boolean | true | Synthesized sound effects |

---

## Onboarding Tracking

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `onboardingMission` | integer | 0 | Current mission (0-7) |
| `onboardingStep` | integer | 0 | Current step within mission |
| `onboardingCompleted` | boolean | false | Whether all missions are done |
| `completedOnboardingMissions` | integer[] | [] | Array of completed mission numbers |
| `completedTutorials` | text[] | [] | Array of completed tutorial slugs |
| `totalXP` | integer | 0 | Total XP earned during onboarding |

---

## Legacy Fields

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `startStage` | text | null | Legacy: Awakening, Building, Mastering, Leading |
| `targetArchetype` | text | null | Legacy: target archetype |
| `flowStyle` | jsonb | {} | Legacy: flow state preferences |
| `coreMotivation` | text | null | Legacy: core motivation |
| `setupMissionStatus` | jsonb | { archetype: "incomplete", integrations: "incomplete", future_self: "incomplete", rituals: "incomplete", pillars: "incomplete" } | Legacy setup mission tracking |
| `primaryThemeColor` | text | "#00e0ff" | Legacy: theme color |
| `futureSelfSummary` | text | null | Legacy: future self narrative |
| `aiPersonalityProfile` | jsonb | {} | Legacy: AI personality config |

**Note:** `setupMissionStatus` contains `"integrations: incomplete"` which shows the original intent to include an integrations onboarding mission. This was deferred because UMH did not exist at time of implementation (see artifact 26: lyfeos_integrations_onboarding_gap.md).

---

## Mission-to-Section Mapping

| Onboarding Mission | Profile Section(s) Populated |
|--------------------|-----------------------------|
| Mission 0 | Access & Quickstart (ageRange, birthday, location, timezone) |
| Mission 1 | Archetype Calibration (archetypePrimary/Secondary/Shadow, archetypeScores) |
| Mission 2 | Identity (primaryInstincts, keyDrivers, shadowDistortions) |
| Mission 3 | Personality (beliefs, values, standards, patterns, strengths, weaknesses) |
| Mission 4 | Vision & Goals (visions, metrics, life stage, life domains, current goals) |
| Mission 5 | Learning & Skills (learning style, deep dives, skill pyramid) |
| Mission 6 | Projects & Creations (current projects, primary craft) |
| Mission 7 | Body & Health (physical metrics, fitness, nutrition, health baseline) |

**Provenance:** SYNTHESIZED_CANON. Missions 0-7 map to schema sections but exact field-per-step mapping requires code inspection of onboarding components.

---

## Open Questions

| ID | Question | Classification |
|----|----------|----------------|
| PROF-001 | Are Wealth & Work, Performance, Style & Expression, History & Roots, Systems & Rituals, and Emotions & Coping filled during onboarding or only later? | OPEN_QUESTION_OPERATOR_DECISION_REQUIRED |
| PROF-002 | Should the characterAffirmation regenerate periodically as the profile evolves? | INFERRED_PROFESSIONAL_GAP |
| PROF-003 | When UMH integration activates, which profile fields are shared with the substrate vs. kept local? | UMH_INTEGRATION_DEPENDENT_GAP |
