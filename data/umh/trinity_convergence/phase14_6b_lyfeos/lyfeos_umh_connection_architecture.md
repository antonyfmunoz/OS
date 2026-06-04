# LyfeOS UMH Connection Architecture

**Phase:** 14.6B-LyfeOS
**Artifact:** 21 of 30
**operator_approved:** false
**allows_implementation:** false
**Date:** 2026-06-03

---

## Purpose

Defines the boundary between what LyfeOS owns and what UMH owns, the integration surfaces between them, blocking questions, guiding principles, and the current state of the existing integration layer.

---

## 1. What LyfeOS Owns

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

LyfeOS is the user-facing application. It owns:

| Domain | Details |
|--------|---------|
| **UX / UI** | All React components, pages, navigation, theming, responsive design, Solo Leveling aesthetic |
| **Dashboard** | XP display, stat tokens, streak, boosts, widget states |
| **Missions** | Quest CRUD, views (Board/List/Calendar), custom views, ritual management, scheduling |
| **AI Companion Interface** | Chat UI, streaming display, image upload, voice input, conversation list |
| **Chronilog** | Daily log UI, reflection prompts, research entries, timeline display |
| **Profile** | Character sheet display, onboarding wizard UI, archetype quiz |
| **Onboarding** | 8-mission flow, step tracking, completion gates |
| **Document Vault** | Folder/document CRUD, template management, sync UI |
| **Secondary Modules** | Kanban, Spreadsheets, Canvases, Graphs, Media, Contacts, Tracker |
| **Settings** | Preferences UI, integration connect/disconnect, display settings |
| **Logs / Stats UI** | Stat detail pages, recharts visualizations, time range selectors |
| **Integrations Surfaces** | Google Calendar/Tasks OAuth UI, sync controls, status display |
| **Gamification UI** | Level-up animations, streak celebration, haptic feedback, sound effects |
| **PWA** | Service worker, offline caching, install prompt, push notifications |

---

## 2. What UMH Owns

**Provenance:** SYNTHESIZED_CANON / UMH_INTEGRATION_DEPENDENT_GAP

UMH is the invisible substrate. It owns:

| Domain | Details |
|--------|---------|
| **Agent Runtime** | Model routing, fallback chains, model selection, response generation |
| **Orchestration Governance** | Risk classification, approval gates, execution boundaries |
| **Source Truth** | Canonical type system, single-source-of-truth for shared domain models |
| **Quality Gates** | Response quality scoring, feedback loops, learning |
| **Permissions** | Action authorization, capability descriptors, risk classes |
| **Execution Boundaries** | What actions the AI can take, rate limits, scope constraints |
| **Audit** | Execution traces, outcome recording, compliance logging |
| **Memory / Salience** | Cross-session intelligence, pattern recognition, user model evolution |
| **Projection Registration** | How LyfeOS registers as a projection with the substrate |
| **Event Bus** | Signal emission, outcome reception, correlation tracking |
| **Deterministic Spine** | Rules/regex/lookup that always work, even when AI is unavailable |

---

## 3. Integration Surfaces

**Provenance:** SYNTHESIZED_CANON / UMH_INTEGRATION_DEPENDENT_GAP

These are the interfaces where LyfeOS and UMH must connect:

### 3.1 Auth Identity Mapping
- LyfeOS user ID (serial integer) must map to UMH org/user identity
- LyfeOS uses Passport.js + Firebase; UMH uses its own identity model
- Mapping table or identity bridge required

### 3.2 User / Profile Mapping
- LyfeOS `userProfile` (100+ fields) must be accessible to UMH salience engine
- UMH needs read access to profile data for AI context injection
- Boundary: UMH reads, LyfeOS writes

### 3.3 AI Runtime Handoff
- Currently: LyfeOS calls Anthropic directly
- Future: LyfeOS sends AI requests to UMH substrate, which routes through `model_router.py`
- UMH handles model selection, fallback, governance
- LyfeOS handles streaming display, UI rendering

### 3.4 Tool / Action Registry
- LyfeOS tools (web_search, create_vision_goal, batch_create_missions, etc.) must be registered as UMH capabilities
- UMH governs which tools are available, their risk classes, and approval requirements
- Existing: `projections/lyfeos/integration/manifest.py` defines `CAPABILITY_DESCRIPTORS`

### 3.5 Memory Boundaries
- Which conversation data does UMH retain vs. LyfeOS?
- Cross-session context: UMH owns; per-conversation history: LyfeOS owns
- User profile evolution: LyfeOS owns writes, UMH can read for intelligence

### 3.6 Sensitive Data Boundaries
- Financial data (from profile wealth section) — sensitivity classification needed
- Health data (from profile body section) — sensitivity classification needed
- Personal identity data — sensitivity classification needed
- UMH must respect data sensitivity tiers for what enters AI context

### 3.7 Audit Logs
- Every AI action must produce an audit trail
- Existing: `projections/lyfeos/integration/outcomes.py` writes to `umh_outcomes` table
- Existing: `projections/lyfeos/integration/tables.py` defines `update_umh_status` for source row tracking

### 3.8 Rollback
- If an AI action fails or is governance-denied, rollback mechanism needed
- Quest creation can be soft-deleted; vision goal creation can be reverted
- UMH must track which actions are reversible

### 3.9 Event Bus
- Existing: `projections/lyfeos/integration/signals.py` emits `SignalEnvelope` for quests, daily logs, stats
- Existing: Polled tables: `quests`, `user_daily_logs`, `vision_goals`
- Direction: LyfeOS DB changes emit signals to UMH; UMH outcomes write back

### 3.10 Cross-System Truth
- User's level, XP, streaks must be consistent between LyfeOS display and UMH intelligence
- No stale cache: UMH reads from LyfeOS DB as source of truth for user state

### 3.11 Backup / Recovery
- LyfeOS DB is the source of truth for all user data
- UMH stores derived intelligence (traces, outcomes, patterns) — not primary data
- Recovery: LyfeOS DB restore + UMH recomputation from signals

### 3.12 Privacy and Rate Limits
- UMH must respect user's AI assistant enabled/disabled toggle (`userStats.aiAssistantEnabled`)
- Rate limits on AI interactions — UMH enforces, LyfeOS displays
- Data retention policies — user can request data deletion

### 3.13 Failover
- When UMH is unavailable, LyfeOS must continue to function
- Deterministic-first principle: all non-AI features work without substrate
- AI features gracefully degrade to "unavailable" message

---

## 4. Blocking Questions

**Provenance:** OPEN_QUESTION_OPERATOR_DECISION_REQUIRED

| ID | Question | Impact |
|----|----------|--------|
| UMH-001 | Does LyfeOS keep its direct Anthropic API connection as a fallback, or does ALL AI routing go through UMH? | Architecture — determines if LyfeOS can function without UMH for AI |
| UMH-002 | How does the LyfeOS user ID (integer) map to UMH org/user identity? New table? Translation layer? | Identity — blocks all integration work |
| UMH-003 | Should the 16-domain knowledge base live in LyfeOS or migrate to UMH? | Intelligence — determines where domain expertise resides |
| UMH-004 | What data sensitivity classification applies to financial and health profile data? | Privacy — determines what UMH can access |
| UMH-005 | Should conversation history be stored in LyfeOS DB, UMH DB, or both? | Data architecture — affects storage and retrieval patterns |
| UMH-006 | When a user disables AI (`aiAssistantEnabled = false`), does UMH stop all signal processing for that user? | Governance — consent boundary |
| UMH-007 | Should LyfeOS vision goals be surfaced to other projections (CreatorOS, EntrepreneurOS) via UMH? | Cross-projection — determines data isolation model |
| UMH-008 | What is the latency budget for AI responses when routing through UMH vs. direct Anthropic? | Performance — user experience constraint |
| UMH-009 | Should the AI companion name choice be projection-specific or shared across projections? | Identity — user experience across products |
| UMH-010 | How does onboarding data (archetype, personality, vision) feed into UMH's user model? | Intelligence — determines depth of cross-projection personalization |
| UMH-011 | Should dismissed knowledge preferences sync across projections? | Personalization — determines preference isolation model |
| UMH-012 | When UMH is down, should LyfeOS display a degraded AI experience or completely hide AI features? | Resilience — user experience during outages |

---

## 5. Guiding Principles

**Provenance:** SYNTHESIZED_CANON

1. **Adapter-first, not rewrite-first**: Integration with UMH should use adapter patterns at the boundary, not rewrite LyfeOS internals
2. **LyfeOS stays user-facing**: All UI, UX, and user interaction belongs to LyfeOS. UMH never renders UI.
3. **UMH stays substrate**: All intelligence routing, governance, audit, and orchestration belongs to UMH. LyfeOS never implements governance logic.
4. **User never needs to know UMH exists**: From the user's perspective, they are using LyfeOS with their AI companion. UMH is invisible infrastructure.
5. **LyfeOS DB is source of truth for user data**: Profile, missions, logs, stats, conversations — all owned by LyfeOS. UMH reads, does not write primary user data.
6. **Deterministic spine preserved**: All non-AI features of LyfeOS work without UMH. Gamification, stat tracking, mission management, daily logging — all deterministic.
7. **Graceful degradation**: When UMH is unavailable, AI features show "unavailable" rather than breaking the app.
8. **Signal-based integration**: LyfeOS emits signals (database changes) to UMH; UMH sends outcomes back. No tight coupling.

---

## 6. Existing UMH Integration Layer

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

The integration layer already exists at `projections/lyfeos/integration/`:

### 6.1 signals.py — LyfeOSSignalEmitter

- Builds `SignalEnvelope` objects from polled LyfeOS database rows
- Three signal types:
  - `lyfeos_quest_completed` — quest completion events
  - `lyfeos_daily_log_created` — daily log creation events
  - `lyfeos_stats_updated` — stat changes (level up, XP, streak)
- Each signal includes full payload with table name, row ID, user ID, and relevant fields

### 6.2 handlers.py — LyfeOSCapabilityHandler

- Implements capability requests:
  - `noop` — acknowledge a polled signal
  - `create_quest` — insert a quest into LyfeOS DB
  - `complete_quest` — mark a quest as completed
  - `log_daily_reflection` — insert a daily log entry
- Direct psycopg2 connection to LyfeOS database
- Health check endpoint

### 6.3 outcomes.py — LyfeOSOutcomeReceiver

- Receives pipeline outcomes from UMH and writes back to LyfeOS
- Dual writeback: source row `umh_status` update + `umh_outcomes` audit table insert
- Severity ladder: source row only advances to higher severity (success < timeout < governance_denied < error)
- Status mapping: success, failure/error, governance_denied, timeout

### 6.4 correlation.py — LyfeOSCorrelationMap

- Thread-safe in-memory mapping from correlation_id to writeback target
- Tracks which LyfeOS table/row a UMH outcome should write back to

### 6.5 tables.py — Database Query Helpers

- Typed row dataclasses: `QuestRow`, `UserStatsRow`, `DailyLogRow`, `VisionGoalRow`
- Read helpers: `fetch_quests_since`, `fetch_stats_for_user`, `fetch_daily_logs_since`, `fetch_vision_goals_since`
- Write helpers: `insert_quest`, `update_quest`, `insert_daily_log`
- Outcome helpers: `update_umh_status`, `insert_umh_outcome`
- Valid sets: `VALID_QUEST_DIFFICULTIES`, `VALID_QUEST_CATEGORIES`, `VALID_VISION_CATEGORIES`, `VALID_MISSION_STATUSES`

### 6.6 manifest.py — Integration Manifest

- Integration ID: `"lyfeos"`
- Signal descriptors (3 signal types with urgency and risk classification)
- Capability descriptors (4 capabilities with input/output schemas)
- Polled tables: `["quests", "user_daily_logs", "vision_goals"]`
- Default poll interval: 30 seconds
- Config loader: reads `LYFEOS_DATABASE_URL`, `LYFEOS_USER_IDS`, `LYFEOS_POLL_INTERVAL` from environment

---

## Integration Layer Status

| Component | Status | Notes |
|-----------|--------|-------|
| Signal emission (signals.py) | Implemented, not wired to live polling | Builds envelopes but needs a polling loop to drive |
| Capability handling (handlers.py) | Implemented, testable | Direct DB access, health check works |
| Outcome writeback (outcomes.py) | Implemented, not receiving live outcomes | Dual writeback logic complete |
| Correlation mapping (correlation.py) | Implemented | Thread-safe, in-memory |
| DB query helpers (tables.py) | Implemented | Full CRUD for integration use cases |
| Manifest (manifest.py) | Implemented | Defines integration contract |
| **Live polling loop** | **NOT IMPLEMENTED** | No scheduler/poller drives signal emission |
| **UMH registration** | **NOT IMPLEMENTED** | Integration not registered with UMH substrate runtime |
| **AI routing through UMH** | **NOT IMPLEMENTED** | LyfeOS still calls Anthropic directly |

**Classification:** The integration layer is architecturally complete but operationally dormant. All building blocks exist; none are wired to production runtime.

---

## Open Questions

| ID | Question | Classification |
|----|----------|----------------|
| CONN-001 | Should the polling loop run inside the LyfeOS process or as a separate UMH worker? | OPEN_QUESTION_OPERATOR_DECISION_REQUIRED |
| CONN-002 | Should integration registration be automatic on LyfeOS startup or manual operator action? | OPEN_QUESTION_OPERATOR_DECISION_REQUIRED |
| CONN-003 | What is the migration path from direct Anthropic calls to UMH-routed AI? | UMH_INTEGRATION_DEPENDENT_GAP |
