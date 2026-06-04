# LyfeOS Missions / Quests Architecture

**Phase:** 14.6B-LyfeOS
**Artifact:** 18 of 30
**operator_approved:** false
**allows_implementation:** false
**Date:** 2026-06-03

---

## Purpose

Canonical documentation of the full mission/quest system architecture in LyfeOS, including the data model, categorization, difficulty ranks, repeat patterns, ritual groups, vision goal linking, external sync, views, XP rewards, cost system, and all supporting tables.

---

## Quest Data Model (quests table)

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH (from shared/schema.ts lines 311-356)

The `quests` table is the core mission entity with 40+ columns:

### Core Fields

| Column | Type | Default | Description |
|--------|------|---------|-------------|
| `id` | serial | auto | Primary key |
| `userId` | integer | required | FK to users.id |
| `title` | text | required | Mission title |
| `description` | text | required | Mission description (supports markdown + inline images) |
| `category` | text | "general" | Mission category |
| `completed` | boolean | false | Completion status |
| `completedAt` | timestamp | null | When completed |
| `missionStatus` | text | "confirmed" | Status: confirmed, pending, completed, cancelled |
| `deletedAt` | timestamp | null | Soft delete timestamp |
| `createdAt` | timestamp | now | Creation timestamp |
| `updatedAt` | timestamp | now | Last update timestamp |

### Cost System

| Column | Type | Default | Description |
|--------|------|---------|-------------|
| `energyCost` | integer | 1 | Energy points consumed on completion |
| `attentionCost` | integer | 0 | Attention tokens consumed |
| `timeCost` | integer | 0 | Time tokens consumed |
| `experienceReward` | integer | 10 | XP earned on completion |

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH. Default XP reward is 10. Energy cost defaults to 1. Attention and Time costs default to 0.

### Scheduling Fields

| Column | Type | Default | Description |
|--------|------|---------|-------------|
| `startDate` | text | null | YYYY-MM-DD format |
| `startTime` | text | null | HH:MM format |
| `endDate` | text | null | YYYY-MM-DD format |
| `endTime` | text | null | HH:MM format |
| `dueDate` | text | null | Legacy field, kept for compatibility |
| `allDay` | boolean | false | All-day event flag |
| `timezone` | text | null | IANA timezone |
| `location` | text | null | Physical location |
| `url` | text | null | Associated URL |
| `attendees` | jsonb | [] | Attendee list |

### Notification Fields

| Column | Type | Default | Description |
|--------|------|---------|-------------|
| `notificationEnabled` | boolean | false | Whether notifications are active |
| `notificationTime` | text | null | Legacy: HH:MM or minutes-before format |
| `notifications` | jsonb | [] | Array of { date: "YYYY-MM-DD", time: "HH:MM" } |

### Difficulty and Ranking

| Column | Type | Default | Description |
|--------|------|---------|-------------|
| `difficulty` | text | "D" | S, A, B, C, D ranks |
| `sortOrder` | integer | 0 | Manual sort position |

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH. Five difficulty ranks inspired by Solo Leveling anime ranking system.

### Repeat / Ritual Fields

| Column | Type | Default | Description |
|--------|------|---------|-------------|
| `isRitualized` | boolean | false | Whether this is a ritual mission |
| `ritualGroup` | text | null | Ritual group name |
| `repeatFrequency` | text | null | hourly, daily, weekly, monthly, yearly |
| `repeatInterval` | integer | 1 | Every X frequency units |
| `repeatDays` | text[] | null | For weekly: ["mon","tue","wed",...] |
| `repeatEndDate` | text | null | YYYY-MM-DD, null means forever |
| `parentRitualId` | integer | null | Links generated instances to original ritual |

### Linking Fields

| Column | Type | Default | Description |
|--------|------|---------|-------------|
| `visionGoalId` | integer | null | FK to visionGoals.id |
| `linkedItems` | jsonb | [] | JSONB links to documents/folders |
| `viewId` | integer | null | Custom board view ID |
| `viewColumn` | text | null | Column assignment in custom board view |

### External Sync Fields

| Column | Type | Default | Description |
|--------|------|---------|-------------|
| `externalId` | text | null | External system ID (e.g., Google Tasks) |
| `externalSource` | text | null | Source system name |

---

## Categories

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH (from tables.py VALID_QUEST_CATEGORIES + replit.md)

| Category | Description |
|----------|-------------|
| `setup` | Onboarding/setup missions |
| `rituals` | Recurring ritual missions |
| `life pillars` | Missions aligned to life domain pillars |
| `general` | Default catch-all category |
| `custom` | User-created custom categories (via `userCategories` table) |

Users can also create custom categories via the `userCategories` table, which stores:
- `value`: machine-readable slug
- `label`: display name
- `description`: optional AI-generated or user-provided description

---

## Difficulty Ranks

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

| Rank | Implied Difficulty |
|------|--------------------|
| S | Highest — life-changing/major milestone |
| A | High — significant effort required |
| B | Medium-high — substantial task |
| C | Medium — moderate effort |
| D | Low — default, quick/simple task |

---

## Repeat Patterns

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

| Frequency | Interval Example | Days Support |
|-----------|-----------------|--------------|
| `hourly` | Every N hours | N/A |
| `daily` | Every N days | N/A |
| `weekly` | Every N weeks | `repeatDays`: ["mon","tue",...] |
| `monthly` | Every N months | N/A |
| `yearly` | Every N years | N/A |

- `repeatEndDate`: null means repeat forever
- `parentRitualId`: generated instances link back to the original ritual definition
- `repeatInterval`: default 1 (every occurrence of the frequency)

---

## Ritual Groups (ritualGroups table)

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH (schema.ts lines 1336-1352)

| Column | Type | Description |
|--------|------|-------------|
| `id` | serial | Primary key |
| `userId` | integer | FK to users.id |
| `value` | text | Machine-readable group slug |
| `label` | text | Display name |
| `description` | text | Optional description |
| `parentGroupValue` | text | Hierarchical grouping (parent group) |
| `createdAt` | timestamp | Creation time |

Ritual groups organize ritualized missions into named collections (e.g., "Morning Routine", "Evening Wind-Down"). Supports hierarchical nesting via `parentGroupValue`.

---

## Vision Goal Linking

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

- Quests link to vision goals via `visionGoalId` FK to `visionGoals.id`
- Vision goals have time horizons: `legacy`, `10year`, `5year`, `18month`, `90day`
- Progress toward a vision goal = ratio of completed linked quests to total linked quests
- Vision goals track `bonusXp` awarded on goal completion
- `disconnectedMissionIds`: tracks missions that were previously linked but manually disconnected

### Vision Goals Table (visionGoals)

| Column | Type | Description |
|--------|------|-------------|
| `id` | serial | Primary key |
| `userId` | integer | FK to users.id |
| `category` | text | legacy, 10year, 5year, 18month, 90day |
| `title` | text | Goal title |
| `description` | text | Goal description |
| `rewardText` | text | Reward description |
| `bonusXp` | integer | XP bonus on completion (default 0) |
| `completed` | boolean | Completion status |
| `completedAt` | timestamp | Completion time |
| `disconnectedMissionIds` | integer[] | Previously linked mission IDs |
| `displayOrder` | integer | Display sort order |
| `createdAt` | timestamp | Creation time |

---

## External Sync (Google Tasks)

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

- Google Tasks imported as missions via `externalId` and `externalSource` fields on `quests`
- Smart deduplication during import: matches by `externalId` first, then fuzzy-matches by title+date+time
- Bidirectional: local quests can be pushed to Google Tasks
- OAuth flow managed via `integrations` table token storage

---

## Mission Views (missionViews table)

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH (schema.ts lines 1406-1433)

| Column | Type | Description |
|--------|------|-------------|
| `id` | serial | Primary key |
| `userId` | integer | FK to users.id |
| `name` | text | View name |
| `viewType` | text | Board, List, or Calendar |
| `filters` | jsonb | Category/difficulty/status/date filters |
| `columns` | jsonb | Custom column headers for board views |
| `sortBy` | text | Sort field |
| `sortDirection` | text | asc or desc |
| `createdAt` | timestamp | Creation time |
| `updatedAt` | timestamp | Last update |

### Default Views (3)

1. **Board**: Vertical kanban with Today/Future/Completed/Inbox/Terminated sections
2. **List**: Schedule-style chronological flat list grouped by day
3. **Calendar**: Google Calendar-style with Year/Month/Week/Day zoom levels, colored category chips, current time indicator, day-detail panel

### Custom Views (Notion-style)

- Users can create additional Board/List/Calendar views with custom names
- Custom category/difficulty filters per view
- Custom column headers for board views
- Stored in `mission_views` table

---

## Mission Pages (missionPages table)

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH (schema.ts lines 386-399)

| Column | Type | Description |
|--------|------|-------------|
| `id` | serial | Primary key |
| `userId` | integer | FK to users.id |
| `title` | text | Page title |
| `slug` | text | URL slug (unique) |
| `content` | text | Page content (markdown) |
| `completed` | boolean | Completion status |
| `xpValue` | integer | XP awarded (default 5) |
| `tags` | text[] | Tag array |
| `eventId` | integer | FK to calendarEvents.id |
| `date` | text | YYYY-MM-DD for day filtering |
| `createdAt` | timestamp | Creation time |
| `updatedAt` | timestamp | Last update |

Mission pages are supplementary content pages associated with missions. They have their own XP value and can be linked to calendar events.

---

## Search, Sort, Filter

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

- **Search**: Text search across mission titles and descriptions
- **Sort**: By date (createdAt), title (alphabetical), energy cost, difficulty rank
- **Filter**: By category, difficulty (S/A/B/C/D), status (confirmed/pending/completed/cancelled), date range
- Filters apply across all view types (Board, List, Calendar)

---

## Soft Delete

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

- `deletedAt` column: null means active, timestamp means soft-deleted
- Soft-deleted quests are excluded from normal views but preserved in database
- Terminated section in Board view shows soft-deleted items

---

## Open Questions

| ID | Question | Classification |
|----|----------|----------------|
| MISSION-001 | What is the maximum number of custom views a user can create? | INFERRED_PROFESSIONAL_GAP |
| MISSION-002 | Should ritual instances auto-generate ahead of time or on-demand? | OPEN_QUESTION_OPERATOR_DECISION_REQUIRED |
| MISSION-003 | Are `autoUnlockConditions` currently evaluated by any runtime logic? | IMPLEMENTATION_DEBT |
