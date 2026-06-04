# LyfeOS UMH-Connected Future Canon

**Phase:** 14.6B-LyfeOS
**Operator Approved:** false
**Allows Implementation:** false

This document describes what LyfeOS looks like when fully connected to the Universal Mastery Hierarchy (UMH) substrate. It defines ownership boundaries, integration surfaces, blocking questions, architecture principles, and the data boundary model.

---

## 1. Ownership Model

### What LyfeOS Owns

| Domain | Description | Provenance |
|--------|-------------|------------|
| **User Experience** | All UI/UX, navigation, visual design, gamification presentation, haptics, sounds | CODE_RESOLVED_CURRENT_TRUTH |
| **Product Modules** | Dashboard, Missions, AI chat UI, Chronilog, Profile, Document Vault, Contacts, Kanban, Spreadsheets, Canvases, Graphs, Media | CODE_RESOLVED_CURRENT_TRUTH |
| **AI Companion Personality** | NOVA's name, persona, conversation style, knowledge base, salience engine | SOURCE_PRESERVED_TRUTH |
| **Gamification Logic** | XP calculations, stat token management, difficulty ranks, streak tracking, efficiency scoring | CODE_RESOLVED_CURRENT_TRUTH |
| **Onboarding Flow** | 8-mission structure, archetype calibration, character sheet population | CODE_RESOLVED_CURRENT_TRUTH |
| **User-Facing Data** | Daily logs, missions/quests, vision goals, contacts, documents, media, spreadsheets, canvases, graphs | CODE_RESOLVED_CURRENT_TRUTH |
| **External Integrations** | Google Calendar/Tasks, Firebase push notifications, future Apple Health/Notion/etc. | CODE_RESOLVED_CURRENT_TRUTH |
| **Local Schema** | All 35 tables in shared/schema.ts | CODE_RESOLVED_CURRENT_TRUTH |

### What UMH Owns

| Domain | Description | Provenance |
|--------|-------------|------------|
| **AI Runtime** | Model routing, fallback chains, cost management, provider selection | UMH_INTEGRATION_DEPENDENT_GAP |
| **Governance** | Risk classification for AI tool executions, approval gates for high-risk actions | UMH_INTEGRATION_DEPENDENT_GAP |
| **Audit Trail** | Immutable record of all automated actions, AI decisions, and state changes | UMH_INTEGRATION_DEPENDENT_GAP |
| **Memory Subsystem** | Cross-session memory persistence, memory compression, memory governance | UMH_INTEGRATION_DEPENDENT_GAP |
| **Cross-Life Intelligence** | Correlation of data across LyfeOS, CreatorOS, EOS projections for a holistic user model | UMH_INTEGRATION_DEPENDENT_GAP |
| **Signal Processing** | Signal ingestion pipeline (perceive -> interpret -> decompose -> bridge -> map -> persist) | CODE_RESOLVED_CURRENT_TRUTH (pipeline exists) |
| **Capability Execution** | Governed capability request/response protocol with outcome writeback | CODE_RESOLVED_CURRENT_TRUTH (handler exists) |
| **Outcome Recording** | Dual writeback (source row umh_status + umh_outcomes audit table) | CODE_RESOLVED_CURRENT_TRUTH (outcomes.py exists) |
| **Type System** | Canonical types for signals, capabilities, risk classes, outcomes | CODE_RESOLVED_CURRENT_TRUTH (substrate/types.py) |

### Shared Ownership (Negotiated Boundary)

| Domain | LyfeOS Role | UMH Role | Provenance |
|--------|-------------|----------|------------|
| **Authentication** | User-facing login UI, session management | Clerk provider configuration, SSO orchestration | UMH_INTEGRATION_DEPENDENT_GAP |
| **User Profile** | Character sheet storage and UI | Cross-projection profile enrichment, archetype intelligence | UMH_INTEGRATION_DEPENDENT_GAP |
| **AI Tool Execution** | Tool definition, UI for tool results | Execution governance, risk classification, audit | UMH_INTEGRATION_DEPENDENT_GAP |
| **Permissions** | Feature access in UI | Tenant isolation (RLS), role-based access governance | UMH_INTEGRATION_DEPENDENT_GAP |

---

## 2. Integration Surfaces

### 2a. Auth Integration

**Current:** Passport.js + Firebase (isolated)
**UMH-Connected:** Clerk authentication shared across projections

| Surface | Direction | Protocol | Notes |
|---------|-----------|----------|-------|
| Login/Register | LyfeOS -> Clerk -> UMH | HTTP/Clerk SDK | LyfeOS uses Clerk components, UMH configures tenant |
| Session Validation | LyfeOS -> Clerk | JWT/Session | Standard Clerk session middleware |
| User Provisioning | Clerk -> UMH -> LyfeOS | Webhook | New user creates records in both UMH and LyfeOS databases |
| SSO | User -> Clerk -> LyfeOS/CreatorOS/EOS | OAuth/OIDC | Single sign-on across projections |

### 2b. Profile Integration

**Current:** user_profile table (200 fields, LyfeOS-only)
**UMH-Connected:** LyfeOS profile + UMH cross-projection profile

| Surface | Direction | Protocol | Notes |
|---------|-----------|----------|-------|
| Profile Sync | LyfeOS -> UMH | Signal (lyfeos_profile_updated) | LyfeOS emits profile change signals |
| Cross-Projection Enrichment | UMH -> LyfeOS | Capability response | UMH provides insights from other projections |
| Archetype Intelligence | LyfeOS <-> UMH | Bidirectional | LyfeOS owns assessment; UMH correlates with behavior |

### 2c. AI Runtime Integration

**Current:** Local Anthropic SDK calls in LyfeOS server
**UMH-Connected:** AI calls route through UMH model_router

| Surface | Direction | Protocol | Notes |
|---------|-----------|----------|-------|
| Chat Completion | LyfeOS -> UMH model_router | API call | UMH handles model selection, fallback, cost tracking |
| Tool Execution | LyfeOS -> UMH governance -> Tool | Governed capability request | Each tool call risk-classified before execution |
| Knowledge Injection | LyfeOS -> UMH | Context enrichment | UMH adds cross-projection context to AI prompts |
| Streaming | UMH -> LyfeOS | WebSocket/SSE | UMH streams AI responses back to LyfeOS |

### 2d. Permissions Integration

**Current:** No RLS, userId-based filtering in application code
**UMH-Connected:** Database-level RLS + UMH tenant governance

| Surface | Direction | Protocol | Notes |
|---------|-----------|----------|-------|
| Row-Level Security | UMH -> LyfeOS DB | RLS policies | UMH defines policies, Drizzle migrations apply them |
| Feature Flags | UMH -> LyfeOS | Config/API | Premium features gated by UMH tenant config |
| Role Assignment | UMH -> Clerk -> LyfeOS | Role claims | admin/premium/free roles flow through auth |

### 2e. Memory Integration

**Current:** Conversations stored in LyfeOS messages table (no cross-session intelligence)
**UMH-Connected:** UMH memory subsystem provides persistent AI memory

| Surface | Direction | Protocol | Notes |
|---------|-----------|----------|-------|
| Memory Write | LyfeOS (via NOVA) -> UMH memory | Signal | Important user statements/preferences saved |
| Memory Read | UMH memory -> LyfeOS AI prompt | Context injection | Past context loaded into NOVA's system prompt |
| Memory Governance | UMH | Policy | What to remember, what to forget, privacy rules |

### 2f. Audit Integration

**Current:** user_activity_events table (basic event tracking)
**UMH-Connected:** UMH audit trail + LyfeOS local events

| Surface | Direction | Protocol | Notes |
|---------|-----------|----------|-------|
| Event Emission | LyfeOS -> UMH | Signal | User actions emit signals to UMH pipeline |
| Outcome Recording | UMH -> LyfeOS DB | Writeback | umh_status column + umh_outcomes table |
| Audit Queries | Operator -> UMH cockpit | Dashboard | Cross-projection audit view |

### 2g. Event Bus Integration

**Current:** No event system between LyfeOS and external systems
**UMH-Connected:** UMH signal pipeline processes LyfeOS events

| Surface | Direction | Protocol | Notes |
|---------|-----------|----------|-------|
| Signal Emission | LyfeOS DB -> UMH Poller | Direct Postgres poll (30s) | Already implemented in integration layer |
| Signal Types | quest_completed, daily_log_created, stats_updated | SignalEnvelope | 3 signal types defined in manifest.py |
| Capabilities | create_quest, complete_quest, log_daily_reflection, noop | CapabilityRequest/Response | 4 capabilities defined |

---

## 3. Blocking Questions

These must be resolved by the operator before UMH connection can proceed.

### Architecture Questions [OPEN_QUESTION_OPERATOR_DECISION_REQUIRED]

| # | Question | Impact | Default Assumption |
|---|----------|--------|-------------------|
| Q1 | Should NOVA's AI calls route through UMH model_router, or should LyfeOS retain its own Anthropic SDK calls? | Architecture, cost, latency | Route through UMH (adapter-first principle) |
| Q2 | Should LyfeOS's 35-table schema stay in its own Neon database, or migrate to a shared UMH database? | Data isolation, migration complexity | Separate database (current), UMH accesses via polling |
| Q3 | Should Clerk auth replace Firebase+Passport before or after UMH connection? | Migration sequencing | After (current auth works; UMH connection is independent) |
| Q4 | Should RLS be implemented before or after UMH connection? | Security, data isolation | Before (protects user data regardless of UMH) |
| Q5 | Should the UMH integration layer remain direct Postgres polling, or switch to an API/webhook model? | Architecture, coupling | Start with polling (already built), migrate to events later |
| Q6 | How should LyfeOS handle UMH unavailability? Degrade gracefully or block AI features? | User experience, reliability | Degrade gracefully (deterministic-first principle) |

### Data Questions [OPEN_QUESTION_OPERATOR_DECISION_REQUIRED]

| # | Question | Impact | Default Assumption |
|---|----------|--------|-------------------|
| Q7 | What LyfeOS data should flow to UMH, and what stays local? | Privacy, data volume | Quest completions, stats changes, daily log summaries flow. Raw profile data stays local. |
| Q8 | Should UMH have write access to LyfeOS database, or read-only with capability requests? | Trust boundary, safety | Read + governed write (current: create_quest, complete_quest, log_daily_reflection) |
| Q9 | How is sensitive personal data (health, wealth, psychology) handled in the UMH pipeline? | Privacy, compliance | Sensitive fields redacted in signals. Only aggregate/summary data flows to UMH. |
| Q10 | Should NOVA conversation history flow to UMH memory, or stay LyfeOS-local? | Memory, privacy | Selected memories flow. Full conversation stays local. |

### Operational Questions [OPEN_QUESTION_OPERATOR_DECISION_REQUIRED]

| # | Question | Impact | Default Assumption |
|---|----------|--------|-------------------|
| Q11 | What is the deployment timeline for UMH connection? | Planning | After LyfeOS production hardening (RLS, backups, error tracking) |
| Q12 | Should UMH connection be feature-flaggable (toggle on/off per user)? | Rollout safety | Yes (gradual rollout) |

---

## 4. Architecture Principles

### 4a. Adapter-First, Not Rewrite-First [SYNTHESIZED_CANON]

LyfeOS should NOT be rewritten to depend on UMH. Instead:
1. LyfeOS continues to work standalone (current state)
2. UMH integration is added as an adapter layer
3. Adapter can be enabled/disabled via feature flag
4. If UMH is unavailable, LyfeOS falls back to local behavior

### 4b. User Never Needs to Know UMH Exists [SYNTHESIZED_CANON]

From the user's perspective, they are using LyfeOS with their AI companion (NOVA or whatever they renamed it). UMH is invisible infrastructure — like a database engine or CDN. Specifically:

- No UMH branding, terminology, or concepts ever surface in LyfeOS UI
- Governance gates appear as "confirmation prompts" or "safety checks," not as UMH concepts
- Quality improvements appear as the AI getting smarter over time
- Audit trails are invisible unless the user explicitly requests activity logs
- Failover is transparent — features either work or show "temporarily unavailable"
- Cross-projection intelligence appears as the AI knowing relevant context, not as "data from another system"
- Error messages never reference UMH, substrate, signals, capabilities, or governance

This is the same principle as how users don't know their bank uses Kubernetes or their streaming service uses a CDN. The infrastructure is invisible.

### 4c. Deterministic-First [SYNTHESIZED_CANON]

Every UMH-connected feature must work without UMH:
- AI chat: falls back to local Anthropic SDK if UMH model_router is unavailable
- Governance: falls back to local risk classification rules
- Memory: falls back to conversation-local context
- Audit: falls back to local user_activity_events

### 4d. Boundary Preservation [SYNTHESIZED_CANON]

LyfeOS owns its UX. UMH never dictates:
- What the navigation looks like
- How missions are displayed
- What NOVA says to the user
- How gamification feels

UMH provides infrastructure. LyfeOS provides experience.

### 4e. Progressive Integration [SYNTHESIZED_CANON]

Integration should proceed in phases:
1. **Phase A:** Signal emission only (UMH observes LyfeOS, no writes)
2. **Phase B:** Governed capabilities (UMH can create quests, log reflections via capability protocol)
3. **Phase C:** AI runtime routing (NOVA uses UMH model_router)
4. **Phase D:** Full memory integration (cross-session NOVA memory via UMH)
5. **Phase E:** Cross-projection intelligence (LyfeOS data enriches EOS/CreatorOS and vice versa)

---

## 5. Data Boundary Model

### 5a. What Flows to UMH

| Data Type | Flows? | Format | Sensitivity |
|-----------|--------|--------|-------------|
| Quest completions | Yes | SignalEnvelope (quest title, category, difficulty, XP) | LOW |
| Stat changes | Yes | SignalEnvelope (level, XP, streak, energy) | LOW |
| Daily log summaries | Yes | SignalEnvelope (state scores, gratitude summary) | MEDIUM |
| Vision goal completions | Yes | SignalEnvelope (goal title, category, bonus XP) | LOW |
| AI memory extracts | Selective | Memory fragments (user-approved) | MEDIUM |

### 5b. What Stays Local

| Data Type | Stays Local? | Reason |
|-----------|-------------|--------|
| Full user profile (~200 fields) | Yes | Highly personal (health, wealth, psychology, beliefs) |
| Full daily log content | Yes | Personal reflections, thoughts, gratitude text |
| Full conversation history | Yes | Private AI coaching conversations |
| Contacts | Yes | Third-party personal information |
| Documents | Yes | Personal files and notes |
| Financial data | Yes | Income, expenses, savings, debt |
| Health data | Yes | Physical metrics, conditions, injuries |
| Media files | Yes | Personal photos and videos |
| Auth credentials | Yes | Passwords, tokens (managed by auth provider) |

### 5c. Redaction Rules

When data flows to UMH:
- Names of third parties redacted from daily logs
- Financial specifics (amounts, account numbers) stripped
- Health conditions anonymized to category level
- Contact information never included in signals
- Only mission titles and categories flow (not descriptions with personal details)

---

## 6. Privacy and Sensitive Data Handling

### Principles

1. **User consent:** No data flows to UMH without user awareness (even if programmatic)
2. **Minimum necessary:** Only the minimum data needed for UMH intelligence flows out
3. **Local by default:** Data stays in LyfeOS database unless there is a specific integration reason to share
4. **Redaction before emission:** Sensitive fields stripped before signals are built
5. **Audit everything:** Every data flow to/from UMH is recorded in umh_outcomes

### Sensitive Data Categories

| Category | Examples | Treatment |
|----------|----------|-----------|
| **Identity** | Name, email, phone, birthday | NEVER flows to UMH pipeline |
| **Psychology** | Beliefs, shadow patterns, coping practices | NEVER flows to UMH pipeline |
| **Health** | Physical metrics, conditions, injuries | Category-level only (e.g., "health improved") |
| **Finance** | Income, expenses, debt, savings | Category-level only (e.g., "wealth token changed") |
| **Relationships** | Contact details, trust levels, conflict styles | NEVER flows to UMH pipeline |
| **Behavioral** | Mission completions, streaks, XP | Flows (aggregate, non-sensitive) |
| **Preferences** | Settings, theme, notification preferences | Flows for UX personalization |

---

## 7. Failover Mode

### When UMH is Unavailable

| Feature | Behavior | Fallback |
|---------|----------|----------|
| AI Chat (NOVA) | Works normally | Local Anthropic SDK (current implementation) |
| Mission Management | Works normally | No change (fully local) |
| Daily Logging | Works normally | No change (fully local) |
| Gamification | Works normally | No change (fully local) |
| All UI | Works normally | No change (fully local) |
| Cross-projection intelligence | Unavailable | Gracefully hidden (no error, just absent) |
| Audit trail | Local only | user_activity_events continues |
| Memory | Conversation-local only | No cross-session memory enrichment |
| Governance | Local rules only | Default to lowest risk classification |

**Key Principle:** LyfeOS must ALWAYS function as a complete product without UMH. UMH is a cognitive enhancement, not a dependency.

---

## 8. Existing UMH Integration Layer

### Current Code [CODE_RESOLVED_CURRENT_TRUTH]

Located at `/opt/OS/projections/lyfeos/integration/` (1184 lines, 7 files):

| File | Lines | Purpose |
|------|-------|---------|
| `__init__.py` | 1 | Package init |
| `manifest.py` | 142 | 3 signals, 4 capabilities, 3 polled tables, config loader |
| `tables.py` | 503 | Typed row dataclasses, SQL read/write helpers, outcome writeback |
| `signals.py` | 166 | SignalEmitter: builds envelopes from polled rows |
| `handlers.py` | 151 | CapabilityHandler: noop, create_quest, complete_quest, log_daily_reflection |
| `correlation.py` | 41 | Thread-safe correlation map (UUID -> writeback target) |
| `outcomes.py` | 180 | OutcomeReceiver: dual writeback (source row + audit table) |

### Integration Method

Direct Postgres polling via `LYFEOS_DATABASE_URL`. UMH connects to LyfeOS Neon database. 30-second poll interval. Polls: quests, user_daily_logs, vision_goals tables.

### What This Already Enables (Phase A)

1. UMH can observe quest completions in real time (30s latency)
2. UMH can observe daily log creation
3. UMH can observe stat changes
4. UMH can create quests in LyfeOS (governed capability)
5. UMH can mark quests complete (governed capability)
6. UMH can log daily reflections (governed capability)
7. Full outcome writeback with severity ladder and audit trail

### What This Does NOT Enable Yet

1. No AI runtime routing (NOVA still uses local SDK)
2. No memory integration
3. No auth integration
4. No real-time events (polling, not webhooks)
5. No profile data flow
6. No cross-projection intelligence
7. LyfeOS has no awareness of UMH
