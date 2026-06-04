# LyfeOS Integrations Onboarding Gap

**Phase:** 14.6B-LyfeOS
**Artifact:** 26 of 30
**operator_approved:** false
**allows_implementation:** false
**Date:** 2026-06-03

---

## Purpose

Dedicated analysis of the missing integration/synchronization onboarding mission in LyfeOS, establishing the gap classification, historical context, and future requirements.

---

## The Gap

**Classification:** UMH_INTEGRATION_DEPENDENT_GAP

LyfeOS has 8 onboarding missions (0-7) that build a user's character sheet through guided self-assessment. An Integrations/Synchronization mission was planned but never implemented.

---

## Evidence of Original Intent

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

### 1. setupMissionStatus Legacy Field

In `userProfile` table (schema.ts line 239-245):

```typescript
setupMissionStatus: jsonb("setup_mission_status").default({
  archetype: "incomplete",
  integrations: "incomplete",
  future_self: "incomplete",
  rituals: "incomplete",
  pillars: "incomplete"
})
```

The `"integrations: incomplete"` entry explicitly shows that an integrations mission was part of the original onboarding design.

### 2. userIntegrations Table Exists

A dedicated `userIntegrations` table exists (schema.ts lines 299-308):

```typescript
export const userIntegrations = pgTable("user_integrations", {
  id: serial("id").primaryKey(),
  userId: integer("user_id").notNull().references(() => users.id, { onDelete: "cascade" }),
  appleHealthConnected: boolean("apple_health_connected").default(false),
  googleCalendarConnected: boolean("google_calendar_connected").default(false),
  notionConnected: boolean("notion_connected").default(false),
  otherIntegrations: jsonb("other_integrations").default({}),
  ...
});
```

This table is ready to track integration connections but has no onboarding flow driving users to populate it.

### 3. Google Calendar Integration Exists

Full Google Calendar + Tasks OAuth integration exists in server routes. Users can connect via Settings, but there is no guided onboarding step for it.

---

## Why It Was Deferred

**Provenance:** SYNTHESIZED_CANON

1. **UMH did not exist** at the time onboarding was implemented. The integration architecture (which integrations? what data flows? what permissions?) was undefined.

2. **The 8 missions focus on self-knowledge**, not external tool setup. The design philosophy prioritizes building the user's internal model before connecting external systems.

3. **Integration complexity**: connecting Google, Apple Health, Notion, and future services requires OAuth flows, token management, error handling, and sync logic that was not ready during initial onboarding implementation.

4. **Scope management**: shipping a working MVP with 8 self-knowledge missions was prioritized over a speculative integrations mission that depended on undecided architecture.

---

## Current Integration Access Path

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

Without an onboarding mission, users access integrations via:

1. **Settings page** (`/settings`) — Google Calendar connect/disconnect UI
2. **Document Vault** — Google Drive sync dialog with Obsidian and Evernote import/export
3. **Missions page** — Google Tasks import (after Calendar connected)

This is a "find it yourself" model. No guided setup. No discovery flow.

---

## What the Missing Mission Should Include

**Provenance:** INFERRED_PROFESSIONAL_GAP / UMH_INTEGRATION_DEPENDENT_GAP

### Phase 1 (Pre-UMH Integration)

An integrations onboarding mission focused on existing external services:

| Step | Action | Service |
|------|--------|---------|
| 1 | Welcome / explain why integrations matter | N/A |
| 2 | Connect Google Calendar (optional) | Google OAuth |
| 3 | Import Google Tasks as missions (optional) | Google Tasks API |
| 4 | Connect Document Vault to Google Drive (optional) | Google Drive |
| 5 | Configure notification preferences | Push/FCM |
| 6 | Review connected services summary | N/A |

### Phase 2 (Post-UMH Integration)

An expanded mission that adds UMH substrate connection:

| Step | Action | Service |
|------|--------|---------|
| 7 | Map LyfeOS identity to UMH identity | UMH Identity Bridge |
| 8 | Configure AI routing preferences (model, fallback) | UMH Model Router |
| 9 | Set privacy/data sharing boundaries | UMH Governance |
| 10 | Configure cross-projection data sharing (if applicable) | UMH Projection Registry |
| 11 | Run integration health check | UMH Health Check |

---

## Legacy Status Values

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

The `setupMissionStatus` field contains five setup missions from the original design:

| Mission | Current Status | Mapping |
|---------|---------------|---------|
| `archetype` | Maps to Mission 1 | Implemented (Archetype Calibration) |
| `integrations` | NOT IMPLEMENTED | This gap |
| `future_self` | Maps to Mission 4 | Implemented (Vision & Goals) |
| `rituals` | Maps to onboarding ritual setup | Partially implemented (Systems & Rituals section in profile) |
| `pillars` | Maps to life domain selection | Implemented (Vision & Goals — lifeDomains) |

---

## Impact of the Gap

| Area | Impact |
|------|--------|
| **Discoverability** | Users may never find integration features without guided setup |
| **Data richness** | Calendar data not flowing into AI companion context for unconnected users |
| **Engagement** | Connected integrations increase daily touchpoints and retention |
| **UMH readiness** | When UMH integration activates, there is no onboarding path for it |
| **Completeness** | The onboarding "Awakening Protocol" feels incomplete without a final connection step |

---

## Recommended Resolution Timeline

| When | Action |
|------|--------|
| **Before UMH integration** | Add a lightweight Mission 8: External Integrations (Google Calendar, Google Drive, notifications) |
| **After UMH integration defined** | Expand Mission 8 or add Mission 9: UMH Connection (identity mapping, AI routing, privacy boundaries) |
| **After cross-projection launches** | Add Mission 10: Cross-Projection Setup (data sharing, unified profile) |

---

## Open Questions

| ID | Question | Classification |
|----|----------|----------------|
| INT-001 | Should the integrations mission be required or optional? | OPEN_QUESTION_OPERATOR_DECISION_REQUIRED |
| INT-002 | If optional, should incomplete integration missions affect onboardingCompleted status? | OPEN_QUESTION_OPERATOR_DECISION_REQUIRED |
| INT-003 | Should the integrations mission be numbered as Mission 8 or inserted between existing missions (e.g., Mission 4.5)? | OPEN_QUESTION_OPERATOR_DECISION_REQUIRED |
| INT-004 | Should Apple Health integration be included in the onboarding flow? (Table exists but implementation status unclear) | OPEN_QUESTION_OPERATOR_DECISION_REQUIRED |
