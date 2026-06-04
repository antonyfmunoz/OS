# LyfeOS Dashboard Architecture

**Phase:** 14.6B-LyfeOS
**Artifact:** 17 of 30
**operator_approved:** false
**allows_implementation:** false
**Date:** 2026-06-03

---

## Purpose

Canonical documentation of the LyfeOS Dashboard (`/`) architecture, including all UI elements, data sources, widget persistence, and provenance for each component.

---

## Dashboard Layout Overview

The Dashboard is the home screen and primary entry point for authenticated users. It presents a gamified overview of the user's current state across XP, stats, missions, streaks, and AI assistant access.

**Route:** `/`
**Component:** `DashboardPage.tsx`
**Provenance:** CODE_RESOLVED_CURRENT_TRUTH (from replit.md + schema evidence)

---

## Dashboard Elements

### 1. XP Progress Bar + Level Display

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

- Source: `userStats.experienceCurrent`, `userStats.experienceMax`, `userStats.level`
- Visual: Progress bar showing current XP vs. XP needed for next level
- Level number prominently displayed
- XP system uses 3-tier exponential curve:
  - Levels 1-10: base XP thresholds with standard multiplier
  - Levels 11-50: increased XP requirements per level
  - Levels 51-100: highest tier with steep XP scaling
- Level 1 threshold: 1000 XP (from schema default `experienceMax: 1000`)

### 2. Quick Stat Cards (5 Tokens)

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

| Stat | Current Field | Max Field | Default |
|------|--------------|-----------|---------|
| Energy Points | `energyPointsCurrent` | `energyPointsMax` | 100/100 |
| Health Points | `healthPointsCurrent` | `healthPointsMax` | 100/100 |
| Wealth Tokens | `wealthTokensCurrent` | `wealthTokensMax` | 100/100 |
| Time Tokens | `timeTokensCurrent` | `timeTokensMax` | 100/100 |
| Attention Tokens | `attentionTokensCurrent` | `attentionTokensMax` | 100/100 |

- Each stat displayed as a card/token with current/max ratio
- Tappable/clickable — navigates to `/stat/:statType` detail page
- Visual indicators for low/critical stat levels
- Stats have specific reset and calculation logic per stat type

### 3. Today's Primary Mission

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

- Source: `userDailyLogs.todayPrimaryMission`
- Displays the user's self-declared primary mission for the day
- Set during daily log initialization
- Quick-complete action available from dashboard

### 4. Streak Counter

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

- Source: `userStats.streakDays`, `userStats.lastActiveDate`
- Displays consecutive days of activity
- Streak breaks when `lastActiveDate` is not yesterday
- Visual emphasis (fire icon, glow effect consistent with Solo Leveling aesthetic)
- Haptic feedback on streak milestone achievement

### 5. Recent Completions

**Provenance:** SYNTHESIZED_CANON (from replit.md "recent completions" reference + quests schema)

- Source: `quests` table filtered by `completed = true`, ordered by `completedAt DESC`
- Shows N most recently completed missions
- Each entry shows title, XP earned (`experienceReward`), and completion timestamp
- Quick navigation to mission detail

### 6. Vision Goal Progress

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

- Source: `visionGoals` table + linked `quests` via `visionGoalId` FK
- Displays progress toward active vision goals across time horizons:
  - 90-day goals
  - 18-month goals
  - 5-year goals
  - 10-year goals
  - Legacy goals
- Progress calculated as ratio of completed linked missions to total linked missions
- Bonus XP (`bonusXp`) shown per goal

### 7. AI Companion Quick-Access Panel

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

- Quick chat entry point without navigating to full `/ai` page
- Displays AI companion name from `userStats.aiAssistantName` (default: "NOVA")
- May show last message or greeting
- Tappable to navigate to full AI conversation page

### 8. Daily Boosts Display

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

- Source: `userDailyLogs.boostsData` (JSONB), `userDailyLogs.optionalBoostsShown`
- Displays daily boost suggestions/motivational content
- Boosts data persisted per day in the daily log
- Boolean flag tracks whether optional boosts have been shown to user today

### 9. Efficiency Score

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

- Source: `userStats.efficiencyScore`
- Tracks daily performance metric
- Uses `previousDayEnergyUsed` for calculation
- Displayed as a score/percentage on the dashboard

---

## Widget State Persistence

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

- Source: `widgetStates` table
- Schema: `id`, `userId` (unique per user), `states` (JSONB)
- Persists which dashboard widgets are visible/collapsed/configured
- Allows user to customize dashboard layout
- One row per user with all widget states in single JSONB blob

---

## Data Sources Summary

| Dashboard Element | Primary Table(s) | Key Fields |
|-------------------|-------------------|------------|
| XP + Level | `userStats` | `experienceCurrent`, `experienceMax`, `level` |
| Stat Cards | `userStats` | All `*Current`/`*Max` pairs |
| Primary Mission | `userDailyLogs` | `todayPrimaryMission` |
| Streak | `userStats` | `streakDays`, `lastActiveDate` |
| Completions | `quests` | `completed`, `completedAt`, `experienceReward` |
| Vision Progress | `visionGoals` + `quests` | `visionGoalId` FK link |
| AI Quick Access | `userStats` | `aiAssistantName` |
| Daily Boosts | `userDailyLogs` | `boostsData`, `optionalBoostsShown` |
| Efficiency | `userStats` | `efficiencyScore`, `previousDayEnergyUsed` |
| Widget States | `widgetStates` | `states` (JSONB) |

---

## Yesterday XP

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

- Source: `userDailyLogs.yesterdayXp`
- Displayed on dashboard (and Chronilog) showing previous day's XP earnings
- Calculated and stored during daily log creation

---

## Open Questions

| ID | Question | Classification |
|----|----------|----------------|
| DASH-001 | Is the dashboard layout fixed or does the user have drag-and-drop widget reordering? | OPEN_QUESTION_OPERATOR_DECISION_REQUIRED |
| DASH-002 | How many recent completions are shown (3? 5? 10?)? | INFERRED_PROFESSIONAL_GAP |
| DASH-003 | Should the AI quick-access panel support inline chat or only serve as a navigation shortcut? | OPEN_QUESTION_OPERATOR_DECISION_REQUIRED |
