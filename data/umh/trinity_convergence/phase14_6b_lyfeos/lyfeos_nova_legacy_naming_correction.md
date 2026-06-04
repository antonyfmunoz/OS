# LyfeOS NOVA Legacy Naming Correction

**Phase:** 14.6B-LyfeOS
**Artifact:** 20 of 30
**operator_approved:** false
**allows_implementation:** false
**Date:** 2026-06-03

---

## Purpose

CRITICAL correction document establishing that NOVA is a historical/default AI companion name, not the permanent universal AI system name for LyfeOS or UMH.

---

## The Correction

### NOVA is NOT the universal AI system name

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH / SOURCE_PRESERVED_TRUTH

NOVA is the **default AI companion name** that ships with LyfeOS. It is:

1. A default value in the database: `aiAssistantName: text("ai_assistant_name").default("NOVA").notNull()` (userStats table)
2. User-renamable via the Settings page
3. A historical implementation choice, not a permanent system identity
4. Specific to LyfeOS as a product, not to UMH as a platform

### What NOVA is

- The **default name** for the LyfeOS AI companion when a user first creates an account
- An example/template name that demonstrates the AI companion personalization feature
- A name that may remain as the default suggestion for new users
- A reference to the concept of a new star (nova) — appropriate for a "new beginning" life OS

### What NOVA is NOT

- NOT the permanent universal AI system name
- NOT equivalent to "DEX" (the UMH/OS repo AI name)
- NOT a name that should be hardcoded in substrate/platform code
- NOT a branding decision that constrains future product direction

---

## Correct Terminology

### Product Language (USE THIS)

| Term | When to Use |
|------|-------------|
| "AI companion" | Generic reference to the LyfeOS AI feature |
| "AI assistant" | Alternative generic reference |
| "user-named AI" | When emphasizing the personalization feature |
| "LyfeOS AI interface" | When discussing the technical surface |
| "your AI companion" | User-facing copy addressing the user |

### System Language (USE THIS)

| Term | When to Use |
|------|-------------|
| `aiAssistantName` | Database field reference |
| `userStats.aiAssistantName` | Full schema reference |
| "default: NOVA" | When documenting the default value |
| "AI companion (default name: NOVA)" | When both specificity and context are needed |

### Deprecated Language (AVOID)

| Term | Why to Avoid |
|------|--------------|
| "NOVA system" | Implies NOVA is a system, not a user-facing name |
| "NOVA AI" as a proper noun | Treats a user-configurable name as a fixed brand |
| "the NOVA" | Article usage implies a unique named entity |
| "NOVA integration" | The integration is with the AI companion system, not with a name |

---

## Code References to NOVA

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH / HISTORICAL_IMPLEMENTATION_DEFAULT

Current code references to "NOVA" fall into these categories:

### 1. Schema Default (Correct)
```typescript
aiAssistantName: text("ai_assistant_name").default("NOVA").notNull()
```
This is correct — it provides a default name. No change needed.

### 2. replit.md Documentation References
The replit.md file references "NOVA" extensively as a proper noun. These reflect the current implementation but should be understood as describing the default AI companion, not a fixed identity.

**Classification:** HISTORICAL_IMPLEMENTATION_DEFAULT — accurate for current code, not prescriptive for future direction.

### 3. Knowledge Base References
The knowledge base in `server/replit_integrations/chat/knowledge-base.ts` may reference "NOVA" in system prompts.

**Recommendation:** System prompt should use `${userStats.aiAssistantName}` to dynamically insert the user's chosen name rather than hardcoding "NOVA".

### 4. UI Component References
Any component that displays the AI name should read from `userStats.aiAssistantName`, not hardcode "NOVA".

**Classification:** IMPLEMENTATION_DEBT if hardcoded; CODE_RESOLVED_CURRENT_TRUTH if dynamic.

---

## UMH Substrate Relationship

### UMH is the underlying intelligence substrate

**Provenance:** SYNTHESIZED_CANON

- UMH (Universal Mastery Hierarchy) is the orchestration and intelligence substrate
- The AI companion in LyfeOS is a **projection-specific user interface** to AI capabilities
- UMH provides: model routing, governance, execution pipeline, audit, memory
- LyfeOS provides: user-facing chat UI, personalization (including AI name), domain knowledge
- The user never needs to know UMH exists — they interact with their named AI companion

### Name Architecture

```
UMH Substrate (universal, invisible to user)
  |
  +-- LyfeOS Projection
  |     |
  |     +-- AI Companion (user-named, default "NOVA")
  |
  +-- CreatorOS Projection
  |     |
  |     +-- AI Companion (user-named, different default)
  |
  +-- EntrepreneurOS Projection
        |
        +-- AI Companion (user-named, different default)
```

Each projection can have its own default AI companion name. The name is a user-facing personalization feature, not a system identity.

---

## Future Considerations

**Provenance:** OPEN_QUESTION_OPERATOR_DECISION_REQUIRED

| ID | Question |
|----|----------|
| NOVA-001 | Should NOVA remain the default name for LyfeOS, or should a new default be chosen? |
| NOVA-002 | Should each projection (LyfeOS, CreatorOS, EntrepreneurOS) have a distinct default AI name? |
| NOVA-003 | Should the AI companion name be established during onboarding (user chooses on first setup)? |
| NOVA-004 | If the user never changes the name, should the system still treat "NOVA" as the display name? |
