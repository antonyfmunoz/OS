# LyfeOS Data Provenance Model

**Phase:** 14.6B-LyfeOS
**Artifact:** 33
**Operator Approved:** false
**Allows Implementation:** false
**Provenance:** SYNTHESIZED_CANON (derived from code analysis of schema.ts, replit.md, and xp-calculations.test.ts)

---

## Purpose

LyfeOS displays stats, scores, and metrics throughout the application. Not all of these are equal in reliability. This document classifies every data point by its provenance category — how the data originates, and what that means for trust, accuracy, and UMH integration.

This model was created because Phase 14.5 operator correction identified that stats were being described as "live verified data" when they are not. The data provenance model must exist before making strong claims about any stat.

---

## Provenance Categories

### 1. MANUAL_INPUT
**Definition:** User types or selects the value directly.
**Trust level:** High (user intent is clear), but accuracy depends on user honesty.
**Examples:** Profile text fields, daily log free-text, gratitude entries, contact details.

### 2. USER_SELF_REPORT
**Definition:** User self-assesses a numeric or categorical value.
**Trust level:** Medium. Subjective by nature. Useful for trend tracking, not for medical or financial decisions.
**Examples:** Mental state (1-10), physical state (1-10), emotional state (1-10), health baseline scores.

### 3. COMPUTED_FROM_APP_BEHAVIOR
**Definition:** Derived from user actions within the app. Calculated by application logic.
**Trust level:** High for internal consistency. Represents app engagement, not necessarily real-world outcomes.
**Examples:** XP, level, streak, efficiency score, time tokens, attention tokens, energy points (reset logic).

### 4. IMPORTED_FROM_INTEGRATIONS
**Definition:** Pulled from a connected external service via API.
**Trust level:** High for factual data (calendar events, task lists). Medium for metadata (categories assigned by external service).
**Examples:** Google Calendar events, Google Tasks imported as missions.

### 5. LIVE_VERIFIED_DEVICE_API
**Definition:** Real-time data from device sensors or verified external APIs.
**Trust level:** Very high. Objective measurement.
**Status:** NOT CURRENTLY IMPLEMENTED. Apple Health flag exists but no actual data flow.
**Future examples:** Step count, heart rate, sleep data, screen time, location.

### 6. UMH_INFERRED_SYNTHESIZED
**Definition:** Insights, recommendations, or derived metrics produced by UMH substrate AI.
**Trust level:** Medium. Depends on model quality and input data quality.
**Status:** NOT CURRENTLY IMPLEMENTED.
**Future examples:** Behavioral pattern detection, cross-domain correlations, personalized recommendations.

---

## Current Stats Provenance Map

| Stat | Display Name | Source Category | Current Source Detail | Notes |
|------|-------------|----------------|---------------------|-------|
| Energy Points | Energy | COMPUTED_FROM_APP_BEHAVIOR or MANUAL_INPUT | Defaults 100/100, reset logic, previous_day_energy_used tracking | Energy cost deducted by quest completion; not from device sensors |
| Health Points | Health | USER_SELF_REPORT | Defaults 100/100. PRD describes weighted formula: sleep 40% + activity 30% + nutrition 30% | In code: stored as simple current/max integers. Weighted formula may not be implemented. |
| Wealth Tokens | Wealth | MANUAL_INPUT | Defaults 100/100. No automated financial integration | User sets own value. No bank/finance API connected. |
| Time Tokens | Time | COMPUTED_FROM_APP_BEHAVIOR | Defaults 100/100. Derived from mission time costs | Not from actual time tracking device data |
| Attention Tokens | Attention | COMPUTED_FROM_APP_BEHAVIOR | Defaults 100/100. Derived from mission attention costs | Not from screen time or focus tracking |
| XP (experience_current) | XP | COMPUTED_FROM_APP_BEHAVIOR | Quest completion XP rewards (default 10), vision goal bonus XP | CODE_RESOLVED_CURRENT_TRUTH — verified in xp-calculations.test.ts |
| Level | Level | COMPUTED_FROM_APP_BEHAVIOR | Derived from cumulative XP via 3-tier formula | CODE_RESOLVED_CURRENT_TRUTH — verified in xp-calculations.test.ts |
| Streak | Streak | COMPUTED_FROM_APP_BEHAVIOR | Consecutive days with activity (lastActiveDate comparison) | Reset to 0 on missed day |
| Efficiency | Efficiency | COMPUTED_FROM_APP_BEHAVIOR | Rolling performance metric (0-100) | Calculation logic in application code |

---

## Profile Data Provenance

| Section | Source Category | Sensitivity |
|---------|----------------|-------------|
| Mission 0: Access & Quickstart | MANUAL_INPUT | LOW — age range, birthday, location, timezone |
| Mission 1: Archetype Calibration | COMPUTED_FROM_APP_BEHAVIOR | MEDIUM — derived from 54-question quiz |
| Identity (instincts, drivers, shadow) | USER_SELF_REPORT | HIGH — shadow distortions, primary instincts |
| Personality (beliefs, values, habits) | USER_SELF_REPORT | HIGH — limiting beliefs, coping patterns |
| Vision & Goals | MANUAL_INPUT | MEDIUM — personal aspirations |
| Learning & Skills | MANUAL_INPUT | LOW — professional development |
| Projects & Creations | MANUAL_INPUT | LOW — current work |
| Body & Health | USER_SELF_REPORT | HIGH — physical metrics, injuries, conditions |
| Wealth & Work | USER_SELF_REPORT | HIGH — financial position, income, expenses, debt |
| Performance & Contribution | USER_SELF_REPORT | LOW — collaboration style |
| Style & Expression | MANUAL_INPUT | LOW — aesthetic preferences |
| History & Roots | USER_SELF_REPORT | HIGH — upbringing, trauma patterns, key experiences |
| Systems & Rituals | MANUAL_INPUT | LOW — daily routines |
| Emotions & Coping | USER_SELF_REPORT | HIGH — coping practices, relationship drains, conflict style |

---

## Integration Data Provenance

| Integration | Source Category | Status |
|-------------|----------------|--------|
| Google Calendar | IMPORTED_FROM_INTEGRATIONS | Active — bidirectional sync |
| Google Tasks | IMPORTED_FROM_INTEGRATIONS | Active — read-only import |
| Apple Health | LIVE_VERIFIED_DEVICE_API | Flag only — NOT connected |
| Notion | IMPORTED_FROM_INTEGRATIONS | Flag only — NOT connected |

---

## Key Distinctions

1. **Stats are NOT live-verified device data.** All 5 stat tokens (Energy, Health, Wealth, Time, Attention) are either user self-report or computed from app behavior. None come from device sensors, wearables, or financial APIs.

2. **XP and Level ARE deterministic app computations.** The 3-tier formula is code-proven and tested. These are reliable internal metrics.

3. **Health is USER_SELF_REPORT, not device-measured.** The PRD describes a weighted formula (sleep 40% + activity 30% + nutrition 30%), but the actual database stores simple current/max integers. Whether the formula is implemented in application logic requires server code inspection.

4. **Wealth is purely MANUAL_INPUT.** No Stripe, no Plaid, no financial API. Users set their own wealth tokens.

5. **Future UMH integration changes provenance.** When UMH substrate connects, some metrics could upgrade to UMH_INFERRED_SYNTHESIZED (cross-domain pattern detection) or LIVE_VERIFIED_DEVICE_API (via Apple Health integration).

---

## Operator Decision Required

- **DEC-146B-PROV-001:** Approve this provenance model as canonical classification for all LyfeOS data points.
- **DEC-146B-PROV-002:** Decide whether provenance labels should be surfaced to users in the UI (transparency principle).
- **DEC-146B-PROV-003:** Prioritize which categories should upgrade to LIVE_VERIFIED_DEVICE_API first (Apple Health is the most natural candidate).
