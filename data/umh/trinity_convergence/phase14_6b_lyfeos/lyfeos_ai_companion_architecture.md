# LyfeOS AI Companion Architecture

**Phase:** 14.6B-LyfeOS
**Artifact:** 19 of 30
**operator_approved:** false
**allows_implementation:** false
**Date:** 2026-06-03

---

## Purpose

Canonical documentation of the LyfeOS AI companion system architecture, covering naming, model routing, streaming, conversation persistence, knowledge base, tool capabilities, vision analysis, and the relationship to the UMH substrate.

---

## AI Companion Identity

### Default Name: NOVA

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

- Field: `userStats.aiAssistantName` (text, default "NOVA", NOT NULL)
- NOVA is the **default/historical name**, not a permanent universal AI system name
- Users can rename their AI companion via the Settings page
- The `aiAssistantName` field is user-editable
- All UI references should use the user's chosen name, not hardcode "NOVA"

### Roles

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH (from replit.md)

The AI companion acts in three capacities:
1. **Advisor** — provides strategic life guidance based on user profile, goals, and knowledge base
2. **Coach** — motivates, tracks progress, holds accountable
3. **Executive Assistant** — creates missions, manages goals, searches the web, navigates the app

---

## Model Routing (Dual Model)

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

| Model | Use Case | Trigger |
|-------|----------|---------|
| Claude Haiku | Simple tasks, quick responses, basic conversation | Default for all interactions |
| Claude Sonnet | Complex reasoning, tool use, image analysis | Automatically upgraded when tools are invoked, complex interactions detected, or images present |

### Upgrade Triggers (Haiku to Sonnet)

1. Tool use is required (any tool call)
2. Complex interaction detected (multi-step reasoning)
3. Image/vision content present in conversation
4. Explicit user request for deeper analysis

**Provenance Note:** Current implementation uses Anthropic models via Replit AI Integrations. Future UMH integration would route through `adapters/models/model_router.py` with `call_with_fallback()`.

---

## Streaming

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

- Responses stream via **Server-Sent Events (SSE)**
- Client receives tokens incrementally for real-time display
- Streaming endpoint handles both Haiku and Sonnet responses
- Error handling for stream interruptions

---

## Conversation Persistence

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH (schema.ts lines 1247-1276)

### conversations table

| Column | Type | Description |
|--------|------|-------------|
| `id` | serial | Primary key |
| `userId` | integer | FK to users.id (cascade delete) |
| `title` | text | Conversation title |
| `createdAt` | timestamp | Creation time |
| `deletedAt` | timestamp | Soft delete |

### messages table

| Column | Type | Description |
|--------|------|-------------|
| `id` | serial | Primary key |
| `conversationId` | integer | FK to conversations.id (cascade delete) |
| `role` | text | "user" or "assistant" |
| `content` | text | Message content |
| `createdAt` | timestamp | Creation time |

### Legacy AI Messages (aiMessages table)

| Column | Type | Description |
|--------|------|-------------|
| `id` | serial | Primary key |
| `userId` | integer | FK to users.id |
| `sender` | text | "ai" or "user" |
| `content` | text | Message content |
| `timestamp` | timestamp | Message time |

**Note:** Both `conversations`/`messages` (newer, conversation-threaded) and `aiMessages` (older, flat list) exist in schema. The newer `conversations`/`messages` system supports multiple named conversations with soft delete.

---

## 16-Domain Knowledge Base

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

Location: `server/replit_integrations/chat/knowledge-base.ts`

| # | Domain |
|---|--------|
| 1 | Philosophy |
| 2 | Sleep |
| 3 | Exercise |
| 4 | Nutrition |
| 5 | Psychology |
| 6 | Relationships |
| 7 | Finance |
| 8 | Learning |
| 9 | Productivity |
| 10 | Crisis Management |
| 11 | Modern Challenges |
| 12 | Breathwork |
| 13 | Advanced Nutrition |
| 14 | Functional Fitness |
| 15 | Biomarkers |
| 16 | Supplementation |

### Knowledge Injection

- **Automatic topic detection**: System analyzes user message and injects relevant domain knowledge into the system prompt
- **Active retrieval**: `lookup_knowledge_base` tool allows the AI to explicitly search knowledge during conversation

### Dismissed Knowledge (dismissedKnowledge table)

| Column | Type | Description |
|--------|------|-------------|
| `id` | serial | Primary key |
| `userId` | integer | FK to users.id |
| `author` | text | Author of dismissed source |
| `sourceMaterial` | text | Source material reference |
| `createdAt` | timestamp | Dismissal time |

Users can dismiss knowledge sources they disagree with or find unhelpful. Dismissed sources are excluded from future injections.

---

## Salience Engine

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

The AI companion has full data ingestion capabilities:
- User profile (all onboarding data)
- User stats (levels, XP, streaks, stat tokens)
- Active missions (incomplete quests)
- Daily logs (recent entries)
- Vision milestones (goals across time horizons)
- Calendar events
- Conversation history

This data is assembled into the system prompt context so the AI has awareness of the user's complete state.

---

## Tool Capabilities

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH (from replit.md)

| Tool | Description | Model Required |
|------|-------------|----------------|
| `web_search` | Search the web for information | Sonnet |
| `read_webpage` | Scrape/read URL content | Sonnet |
| `create_vision_goal` | Create vision goals from chat | Sonnet |
| `batch_create_missions` | Create multiple missions at once | Sonnet |
| `uncomplete_mission` | Undo mission completion | Sonnet |
| `lookup_knowledge_base` | Search 16-domain knowledge base | Haiku or Sonnet |

**Note:** Tools trigger automatic model upgrade to Sonnet. Deep tool chaining is supported (tools can call other tools in sequence).

---

## Vision / Image Analysis

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

- Users can attach images directly in chat (upload button or paste)
- AI companion auto-extracts inline images from mission descriptions, goal descriptions, and daily logs when user's message references visual content
- Trigger keywords: "image", "photo", "mission", "goal", "log", etc.
- Images sent as base64 vision content blocks to Anthropic
- Maximum 5 most recent images per request
- Image presence triggers Haiku-to-Sonnet upgrade

### Inline Image System

- Rich text toolbar (`client/src/components/ui/rich-text-toolbar.tsx`) enables image upload across all text fields
- Images stored as base64 in `mediaItems` table with userId ownership enforcement
- Served via `/api/inline-upload/:id` with authentication
- MarkdownEditor supports image button for inline image insertion

---

## Voice Control

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

- Web Speech API integration for voice input
- Users can speak to the AI companion
- Voice-to-text transcription feeds into the standard chat pipeline
- AI responses are text-based (no TTS in current implementation — INFERRED_PROFESSIONAL_GAP: TTS would enhance the experience)

---

## Relationship to UMH Substrate

### Current State

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

- NOVA/AI companion is a **standalone implementation** within LyfeOS
- Uses Anthropic API directly via Replit AI Integrations
- NOT currently connected to UMH substrate
- No routing through `adapters/models/model_router.py`
- No governance, audit, or execution pipeline integration

### Future State

**Provenance:** UMH_INTEGRATION_DEPENDENT_GAP

- AI companion will connect to UMH through an adapter layer
- UMH substrate provides: agent runtime, orchestration governance, quality gates, execution boundaries, audit trails
- LyfeOS retains: UX surface, conversation UI, knowledge base display, tool result rendering
- The AI companion becomes a **projection-specific interface** to the UMH intelligence substrate
- Integration layer exists at `projections/lyfeos/integration/` (signals, handlers, outcomes, correlation, tables)

---

## Open Questions

| ID | Question | Classification |
|----|----------|----------------|
| AI-001 | When UMH integration happens, does the knowledge base move to UMH or stay in LyfeOS? | UMH_INTEGRATION_DEPENDENT_GAP |
| AI-002 | Should conversation history be accessible to UMH for cross-projection intelligence? | OPEN_QUESTION_OPERATOR_DECISION_REQUIRED |
| AI-003 | What approval model governs AI tool actions (create goals, batch missions)? | INFERRED_PROFESSIONAL_GAP |
| AI-004 | Should dismissed knowledge preferences sync across projections via UMH? | UMH_INTEGRATION_DEPENDENT_GAP |
