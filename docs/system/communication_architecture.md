# UMH Communication Architecture

UMH has two distinct communication systems. They share UI patterns but serve fundamentally different purposes. Never conflate them.

## Chat (operator ↔ AI)

The primary interface for communicating with the AI assistant and the system.

- **Priority**: voice first, cockpit chat second
- **Route**: `/chat/converse` → `organism.converse` → SignalEnvelope → SubstrateGateway
- **Participants**: operator talks to AI. AI responds.
- **Channel selector**: cockpit is default. Discord, Telegram, etc. are additional channels the user can choose for talking to the AI — same conversation, different surface.
- **Persistence**: OrganismStore with `origin_channel` tracking
- **Real-time**: WebSocket `chat_message` events push cross-channel messages to cockpit

## Messages (operator ↔ external people)

A multi-channel unified inbox for human-to-human communication.

- **Purpose**: aggregate conversations from mobile text, Instagram DMs, Discord DMs from other humans, email threads, etc.
- **Route**: `/messages` (separate from chat)
- **Participants**: operator communicates with leads, clients, partners — real humans
- **Think**: CRM-style aggregated messaging, not AI conversation

## Key Distinction

| | Chat | Messages |
|---|---|---|
| Other party | AI assistant | External humans |
| Purpose | Command the system | Communicate with people |
| Channels | Cockpit, Discord, voice | SMS, Instagram, email, etc. |
| Route | `/chat/converse` | `/messages` |
| Backed by | SubstrateGateway | Channel adapters |

When building features, ask: "Is the operator talking to the AI or to a human?"
- AI → chat system
- Human → messages system
