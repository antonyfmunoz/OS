# LyfeOS Systems & Secondary Modules Architecture

**Phase:** 14.6B-LyfeOS
**Artifact:** 29 of 30
**operator_approved:** false
**allows_implementation:** false
**Date:** 2026-06-03

---

## Purpose

Documents that "Systems" is NOT a primary navigation tab (operator correction) and catalogs all secondary modules/routes that provide systems-like functionality.

---

## Critical Correction: Systems is NOT a Primary Tab

**Provenance:** SOURCE_PRESERVED_TRUTH (operator correction)

Early documentation and the Phase 14.5 convergence plan listed "Systems" as a primary navigation tab alongside Dashboard, Missions, AI, Chronilog, and Profile. The operator has corrected this: **Systems does not exist as a primary navigation tab.**

Systems-like functionality is distributed across secondary modules accessible via their own routes. These modules provide tool and organizational capabilities that support the primary workflow (missions, logs, goals) without occupying primary navigation space.

---

## Secondary Modules Inventory

### Document Vault (`/document-vault`)

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

| Aspect | Detail |
|--------|--------|
| Component | `DocumentVaultPage.tsx` |
| API Routes | `server/routes/documents.ts` |
| Schema Tables | `folders`, `documents`, `templates` |
| Description | Google Drive-style data organizer with nested folder system |

**Features:**
- List and Grid/Gallery view modes
- Markdown document creation and editing
- Media upload (images, videos, PDFs)
- Nested folder hierarchy with `parentId` self-referencing FK
- Template library with category and tag organization
- Bidirectional sync:
  - Google Drive/Docs (OAuth-based)
  - Obsidian import/export (.md/.zip)
  - Evernote import/export (.enex)
- Source tracking: `source`, `externalId`, `externalUrl`, `lastSyncedAt` fields with visual source badges
- Quick-filter chips (All, Documents, Images, Videos, PDFs)
- Soft delete (`deletedAt` on both folders and documents)
- Favorite marking on documents and folders

---

### Kanban Boards (`/kanban`)

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

| Aspect | Detail |
|--------|--------|
| Component | `KanbanPage.tsx` |
| API Routes | `server/routes/kanban.ts` |
| Schema Tables | `kanbanBoards`, `kanbanColumns`, `kanbanTasks` |
| Description | Standalone project boards with customizable columns and task cards |

**Features:**
- Multiple boards per user
- Customizable columns with title, status identifier, and order
- Task cards with priority (low/medium/high), tags, dates
- Drag-and-drop between columns (via `react-dnd`)
- Default board flag (`isDefault`)
- Cascade delete: deleting a board removes all columns and tasks

**Note:** This is separate from the Missions Board view. The Missions page has its own kanban-style Board view with Today/Future/Completed/Inbox/Terminated sections. The Kanban module is a general-purpose project management tool.

---

### Spreadsheets (`/spreadsheets`)

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

| Aspect | Detail |
|--------|--------|
| Component | `SpreadsheetsPage.tsx` |
| API Routes | `server/routes/spreadsheets.ts` |
| Schema Tables | `spreadsheets` |
| Description | User spreadsheets with flexible JSON content storage |

**Features:**
- Title and description
- Content stored as JSONB (flexible structure for spreadsheet data)
- Category classification
- Favorite marking

---

### Canvases (`/canvases`)

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

| Aspect | Detail |
|--------|--------|
| Component | `CanvasesPage.tsx` |
| API Routes | `server/routes/canvases.ts` |
| Schema Tables | `canvases` |
| Description | Whiteboard/canvas drawing tool with JSONB element storage |

**Features:**
- Title and description
- Content stored as JSONB (shapes, connections, text elements)
- Category classification
- Favorite marking

---

### Graphs (`/graphs`)

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

| Aspect | Detail |
|--------|--------|
| Component | `GraphsPage.tsx` |
| API Routes | `server/routes/graphs.ts` |
| Schema Tables | `graphs` |
| Description | Node-link diagrams and visualizations with JSONB storage |

**Features:**
- Title and description
- Content stored as JSONB (nodes, edges, styling metadata)
- Category classification
- Favorite marking

---

### Contacts (`/contacts`)

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

| Aspect | Detail |
|--------|--------|
| Component | `ContactsPage.tsx` |
| API Routes | `server/routes/contacts.ts` |
| Schema Tables | `contacts` |
| Description | Personal CRM/rolodex with 30+ fields per contact |

**Features:**
- Core: name, alias, email, phone, secondary phone
- Professional: company, job title, department, industry
- Category and relationship type
- Social: LinkedIn, Twitter, Instagram, website
- Personal: birthday, address, city, country, timezone
- Relationship metadata: trust level (integer), contact frequency, how met, favorite
- Strengths and notes (free text)
- Last contacted tracking
- Cascade delete on user removal

---

### Media (`/media`)

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

| Aspect | Detail |
|--------|--------|
| Component | `MediaPage.tsx` |
| API Routes | `server/routes/media.ts` |
| Schema Tables | `mediaAlbums`, `mediaItems` |
| Description | Photo and video management with album organization |

**Features:**
- Albums with title, description, and cover image
- Smart albums with JSONB rules for automatic population (`isSmartAlbum`, `smartAlbumRules`)
- Media items support multiple storage modes:
  - URL-based (`fileUrl` — S3 or similar)
  - Base64 (`fileData` — inline storage)
  - File path (`filePath` — server-local)
- Metadata: MIME type, file size, date taken, location (lat/long/placeName), camera metadata
- Thumbnail support (`thumbnailUrl`)
- Tags, favorites, title, description per item
- Cascade delete on user removal

---

### Tracker (`/tracker`)

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

| Aspect | Detail |
|--------|--------|
| Component | `TrackerPage.tsx` |
| API Routes | `server/routes/trackers.ts` |
| Schema Tables | `progressTrackers`, `visionGoals` |
| Description | Goal progress tracking and milestone analytics |

**Features:**
- Progress trackers with current value, target value, and unit (e.g., "kg", "steps", "hours")
- Start/end date range
- Color customization per tracker
- Favorite marking
- Vision goal progress integration
- Milestone analytics: completion rates across time horizons

---

### Progress Trackers (within Tracker page)

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

| Column | Type | Description |
|--------|------|-------------|
| `id` | serial | Primary key |
| `userId` | integer | FK to users.id |
| `title` | text | Tracker title |
| `description` | text | Tracker description |
| `category` | text | Category (default "general") |
| `currentValue` | integer | Current progress value |
| `targetValue` | integer | Target goal value |
| `unit` | text | Unit of measurement |
| `startDate` | timestamp | Tracking start |
| `endDate` | timestamp | Tracking end (optional) |
| `color` | text | Display color (default "#00e0ff") |
| `favorite` | boolean | Favorite flag |

---

### Smart Reminders

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

| Aspect | Detail |
|--------|--------|
| Schema Table | `smartReminders` |
| Description | Configurable notification scheduling system |

| Column | Type | Description |
|--------|------|-------------|
| `id` | serial | Primary key |
| `userId` | integer | FK to users.id |
| `reminderType` | text | Type of reminder |
| `enabled` | boolean | Active toggle |
| `source` | text | Origin (default "default") |
| `preferredHour` | integer | Hour of day (0-23, default 9) |
| `preferredDays` | text[] | Days of week (default all 7) |
| `cooldownHours` | integer | Minimum hours between sends (default 20) |
| `lastSentAt` | timestamp | Last send time |

**Unique constraint:** One reminder per type per user (`userId + reminderType`).

Smart reminders are the notification scheduling backbone. They determine when to prompt users for daily logs, mission reviews, streak maintenance, etc.

---

## Common Schema Patterns Across Secondary Modules

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

All secondary modules share these patterns:

| Pattern | Tables Using It |
|---------|----------------|
| `userId` FK with cascade delete | contacts, kanbanBoards, spreadsheets, canvases, graphs, mediaAlbums, mediaItems, templates, progressTrackers |
| `favorite` boolean | contacts, spreadsheets, canvases, graphs, folders, documents, templates, progressTrackers |
| `category` text | contacts, spreadsheets, canvases, graphs, templates, progressTrackers |
| `createdAt` + `updatedAt` timestamps | All secondary module tables |
| JSONB content storage | spreadsheets.content, canvases.content, graphs.content, mediaAlbums.smartAlbumRules, mediaItems.location/metadata |

---

## Open Questions

| ID | Question | Classification |
|----|----------|----------------|
| SYS-001 | Should secondary modules be accessible from sidebar, or only via direct navigation? | OPEN_QUESTION_OPERATOR_DECISION_REQUIRED |
| SYS-002 | Is there a planned "app launcher" or "module grid" view that surfaces all secondary modules? | OPEN_QUESTION_OPERATOR_DECISION_REQUIRED |
| SYS-003 | Should smart reminders have a dedicated UI or be managed only through Settings? | INFERRED_PROFESSIONAL_GAP |
| SYS-004 | Should canvases and graphs be combined into a single "Diagrams" module? | OPEN_QUESTION_OPERATOR_DECISION_REQUIRED |
