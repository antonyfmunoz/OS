# LyfeOS Chronilog Architecture

**Phase:** 14.6B-LyfeOS
**Artifact:** 28 of 30
**operator_approved:** false
**allows_implementation:** false
**Date:** 2026-06-03

---

## Purpose

Canonical documentation of the Chronilog (daily logs + timeline) architecture, including the data model, all log sections, unique constraints, and connected features.

---

## Overview

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

The Chronilog is LyfeOS's daily logging and reflection system. It serves as both a daily initialization ritual and a longitudinal record of the user's mental, physical, and emotional state.

- **Route:** `/chronilog`
- **Component:** `ChronilogPage.tsx`
- **Table:** `userDailyLogs`
- **Constraint:** One entry per user per day (unique index on `userId + date`)

---

## Data Model (userDailyLogs table)

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH (schema.ts lines 258-296)

### Core Fields

| Column | Type | Default | Description |
|--------|------|---------|-------------|
| `id` | serial | auto | Primary key |
| `userId` | integer | required | FK to users.id |
| `date` | date | required | Log date (unique per user) |
| `yesterdayXp` | integer | 0 | XP earned the previous day |
| `todayPrimaryMission` | text | null | User's primary mission for the day |
| `optionalBoostsShown` | boolean | false | Whether daily boosts have been displayed |
| `boostsData` | jsonb | {} | Daily boost content/configuration |
| `createdAt` | timestamp | now | Record creation time |

### Unique Constraint

```sql
UNIQUE INDEX user_daily_logs_user_date_idx ON (userId, date)
```

Only one log entry per user per day. This enforces that the Chronilog is a daily practice, not an arbitrary collection.

---

## Log Sections

### 1. Energy Log

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

| Column | Type | Default | Description |
|--------|------|---------|-------------|
| `wakeTime` | text | null | Time user woke up (HH:MM format) |
| `sleepTime` | text | null | Time user went to sleep (HH:MM format) |
| `mentalState` | integer | 5 | 1-10 scale, mental state rating |
| `physicalState` | integer | 5 | 1-10 scale, physical state rating |
| `emotionalState` | integer | 5 | 1-10 scale, emotional state rating |

The Energy Log captures the user's baseline state for the day. Default scores of 5 represent a neutral baseline. These feed into the AI companion's salience engine and stat calculations.

### 2. Intention Log

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

| Column | Type | Default | Description |
|--------|------|---------|-------------|
| `gratitude` | text | null | What the user is grateful for today |
| `tomorrowGoals` | text | null | Goals for tomorrow (forward-looking) |
| `annualGoals` | text | null | Annual goals reminder/reflection |
| `thoughts` | text | null | Free-form thoughts and intentions |

The Intention Log captures forward-looking commitments and gratitude practice. `annualGoals` serves as a recurring anchor to long-term vision.

### 3. Data Log

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

| Column | Type | Default | Description |
|--------|------|---------|-------------|
| `contentConsumed` | text | null | Information consumed today (articles, books, videos) |
| `research` | text | null | Research notes (legacy field) |
| `todoIdeas` | text | null | Ideas for future todos |
| `todosConverted` | boolean | false | Whether todoIdeas have been converted to quests |

The Data Log captures intellectual input. `todosConverted` tracks whether free-form todo ideas have been formalized into quests via the conversion feature.

### 4. Research Log

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

| Column | Type | Default | Description |
|--------|------|---------|-------------|
| `sourceAuthor` | text | null | Source author name |
| `sourceMaterial` | text | null | Source material reference |
| `researchNote` | text | null | Research note |
| `revisionNote` | text | null | Revision and summary note |
| `executionNote` | text | null | Execution note (action items from research) |
| `researchEntries` | jsonb | [] | Array of archived research entries for multiple entries per day |

The Research Log follows a structured research-to-execution workflow:
1. Capture the source (author + material)
2. Take initial notes (researchNote)
3. Synthesize/revise (revisionNote)
4. Extract action items (executionNote)

`researchEntries` is a JSONB array allowing multiple research entries per day. Each entry in the array follows the same source-note-revision-execution structure.

### 5. Reflection Log

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

| Column | Type | Default | Description |
|--------|------|---------|-------------|
| `wentWell` | text | null | What went well today |
| `couldBeBetter` | text | null | What could have been better |
| `learned` | text | null | What the user learned today |

The Reflection Log is an end-of-day practice. The three prompts can be customized via `userProfile.customReflectionPrompts`:

```json
{
  "wentWell": "What went well today?",
  "couldBeBetter": "What could have been better?",
  "learned": "What did I learn?"
}
```

---

## Connected Features

### Yesterday XP Display

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

- `yesterdayXp` stores the previous day's XP total
- Displayed prominently in the Chronilog and on the Dashboard
- Calculated and written during daily log creation

### Daily Boosts

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

- `boostsData` (JSONB) stores daily boost content
- `optionalBoostsShown` tracks whether boosts were displayed to the user
- Boosts are motivational/actionable suggestions tailored to the user's state

### Todos to Quests Conversion

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

- Users can enter free-form `todoIdeas` in the Data Log
- A conversion feature transforms these into formal quests in the `quests` table
- `todosConverted` boolean tracks whether conversion has been performed
- Prevents duplicate conversion

### Document Vault Link

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

- The Chronilog page links to the Document Vault (`/document-vault`)
- Research notes can be saved as documents for long-term reference
- The Data Vault widget is accessible from the Chronilog page

### Custom Reflection Prompts

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

- Stored in `userProfile.customReflectionPrompts` (JSONB)
- Users can customize the three reflection questions
- Defaults: "What went well today?", "What could have been better?", "What did I learn?"
- AI companion can suggest new prompts based on user patterns

---

## AI Companion Integration

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

The AI companion has read access to daily logs for its salience engine:
- Mental/physical/emotional state informs coaching context
- Gratitude entries inform positive reinforcement patterns
- Research notes inform knowledge recommendations
- Reflection entries inform growth trajectory analysis

The UMH integration layer already emits `lyfeos_daily_log_created` signals when new logs are created (see `projections/lyfeos/integration/signals.py`).

---

## Data Flow Diagram

```
User opens Chronilog
  |
  +-- Create/load daily log for today (unique per date)
  |
  +-- Energy Log section
  |     +-- Rate mental (1-10), physical (1-10), emotional (1-10)
  |     +-- Record wake/sleep times
  |
  +-- Intention Log section
  |     +-- Write gratitude
  |     +-- Set goals for tomorrow
  |     +-- Review annual goals
  |     +-- Free-form thoughts
  |
  +-- Data Log section
  |     +-- Log content consumed
  |     +-- Record todo ideas
  |     +-- [Convert todos to quests]
  |
  +-- Research Log section
  |     +-- Record source + notes
  |     +-- Revise + summarize
  |     +-- Extract execution items
  |     +-- [Archive to researchEntries array]
  |
  +-- Reflection Log section (end of day)
  |     +-- What went well
  |     +-- What could be better
  |     +-- What I learned
  |
  +-- Save → triggers signal emission to UMH (when connected)
```

---

## Open Questions

| ID | Question | Classification |
|----|----------|----------------|
| CHRON-001 | Can users edit past daily logs, or are they locked after the day ends? | OPEN_QUESTION_OPERATOR_DECISION_REQUIRED |
| CHRON-002 | Should the Research Log support linking to Document Vault documents? | INFERRED_PROFESSIONAL_GAP |
| CHRON-003 | How far back can users view their Chronilog history? All-time? 90 days? | INFERRED_PROFESSIONAL_GAP |
| CHRON-004 | Should the Chronilog timeline view show a visual calendar or a scrollable list? | OPEN_QUESTION_OPERATOR_DECISION_REQUIRED |
