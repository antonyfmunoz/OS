# Phase 14.13G — Operator Acceptance Test Report

**Date**: 2026-06-07
**Method**: Live cockpit (universalmetaharness.tech) + API (localhost:8091)
**Commit**: e0929d91 (deployed to Fly.io + os-operator Docker)
**Test scope**: Full planning loop — ask, follow-up, decompose, council, CC bridge, capture, history

---

## Executive Summary

**API layer: 8/8 tests pass.** Every intent routes correctly, deterministic fallbacks fire, CC bridge reports truthfully, history persists.

**Frontend layer: BROKEN.** DEX responses do not render in the cockpit chat. The API returns valid JSON (confirmed via browser network inspector), the frontend receives it, but the chatStore fails to append the DEX response bubble. Both test messages returned 200 with full response bodies — zero rendered in the UI.

**The ChatGPT → Claude Code → Termius loop is NOT absorbed into UMH yet.** The API backend can handle the full loop, but the operator cannot see DEX responses in the cockpit. They would need to use curl or another tool to interact with DEX, defeating the purpose.

---

## Step-by-Step Results

### Step 1-2: Open cockpit + navigate to DEX chat
- Login: PASS — Clerk auth at universalmetaharness.tech works
- Chat tab: PASS — visible in right rail, "DEX ASSISTANT" header, "Viewing: commandcenter" context
- View context: PASS — shows active route and page context
- **Friction**: 119 console errors on page load (403 on workstation/* endpoints, WebSocket handshake failure)

### Step 3: Ask DEX "What is the next highest-leverage move for UMH?"
- **API**: PASS — 200 OK, intent=unknown (conversational), 51.9s latency
- **Model routing**: cc_sdk → Gemini 429 → Groq 200 (llama-3.3-70b, 49s)
- **Response quality**: FAIL — Groq hallucinated fake data ("packet 7a, 37% increase", fabricated steps). Not grounded in actual system state.
- **Frontend rendering**: FAIL — response received in network tab but not rendered in chat
- **Latency**: 51.9s — unacceptable for interactive use. Most time in model fallback chain.

### Step 4: Follow-up question
- **API**: PASS — 200 OK, intent=unknown, 1.5s latency
- **Response**: "All providers down — circuit breaker open, retrying in 28s" — truthful about provider state
- **Frontend rendering**: FAIL — not rendered

### Step 5: Turn plan into work packets
- **API**: PASS — 200 OK, intent=decompose_intent, 4.3s latency
- **Response**: "Created 3 work packets" — deterministic fallback fired
- **Frontend rendering**: FAIL — not rendered

### Step 6: Council review
- **API**: PASS — 200 OK, intent=council_review, 0.9s latency
- **Response**: Consensus=revise, deterministic fallback with truthful caveat: "Council review ran without LLM. Recommendations are conservative."
- **Frontend rendering**: FAIL — not rendered

### Step 7: Claude Code session
- **Result**: 1 session found (ai_main, attached=False)
- **Limitation**: Session exists in tmux but is not attached (no active Claude Code process)

### Step 8: Send prompt to Claude Code
- **API**: PASS — 200 OK, intent=cc_send, 1.6s latency
- **Response**: "Claude Code send failed: No active Claude Code session accepted the message. Check that a session is running and attached."
- **Suggested actions**: [Check sessions, Retry] — both present
- **Truthful**: Yes — reports exact blocker, no fake success

### Step 9: Capture Claude output
- **API**: PASS — 200 OK, intent=cc_capture, 1.2s latency
- **Response**: "No output captured from session ``" — truthful, no fake output

### Step 10: Full loop persistence
- **API**: PASS — 20 history entries returned
- **Conversation continuity**: All messages stored with conversation_id

---

## Friction Log

| Issue | Severity | Category | Detail |
|-------|----------|----------|--------|
| DEX responses don't render | CRITICAL | Frontend | API returns valid JSON, browser receives it, chatStore doesn't append response bubble |
| 51.9s first response | HIGH | Latency | Model fallback chain: cc_sdk fail → Gemini 429 → Groq 49s |
| Groq hallucination | HIGH | Quality | llama-3.3-70b fabricated "packet 7a, 37% increase" — not grounded in system state |
| 119 console errors | MEDIUM | Frontend | 403 on workstation/* endpoints, WebSocket Sec-Protocol mismatch |
| Circuit breaker fires | MEDIUM | Reliability | Second conversational query hit all-providers-down within 28s window |
| CC session not attached | MEDIUM | Infrastructure | tmux session exists but Claude Code not running in it |
| "No output captured from session ``" | LOW | Polish | Empty session name in capture response — should say which session was checked |
| Deterministic fallback quality | LOW | Quality | Council review and decompose work but outputs are templated, not insightful |

---

## Missing Controls

1. **No loading indicator visible** — user sends message, input briefly disables, then re-enables with no feedback about processing time or model routing
2. **No retry button** — when a response fails to render, the user has no way to retry
3. **No model tier indicator** — user cannot tell if Opus, Gemini, Groq, or deterministic fallback answered
4. **No latency display** — 51.9s feels like a timeout without feedback
5. **No circuit breaker UI** — "all providers down" is text in a response, not a system status indicator

---

## Verdict: Is the ChatGPT → CC → Termius loop absorbed?

| Workflow step | ChatGPT today | DEX equivalent | Status |
|--------------|---------------|----------------|--------|
| Ask strategic question | ChatGPT chat | /dex/converse | API works, frontend broken |
| Get grounded answer | ChatGPT + context | /dex/converse + view_context | API works, Groq hallucinates |
| Follow-up conversation | ChatGPT thread | /dex/converse + conversation_id | API works, frontend broken |
| Create tasks | Manual | /dex/converse decompose_intent | Works (deterministic) |
| Review plan | ChatGPT | /dex/converse council_review | Works (deterministic fallback) |
| Send to Claude Code | Copy-paste to Termius | /dex/converse cc_send | Truthful blocker (no active session) |
| Capture Claude output | Read Termius | /dex/converse cc_capture | Truthful (no output) |
| History | ChatGPT thread | /dex/history | Works |

**Answer: NO.** The API backend can handle every step of the loop, but:
1. The cockpit frontend doesn't render DEX responses — the operator cannot see answers
2. Model quality degrades to hallucination (Groq) or templates (deterministic) without Opus/Gemini
3. CC bridge is truthful but non-functional (no attached session to receive messages)

**What would make it YES:**
1. Fix the frontend rendering bug (chatStore not appending DEX response bubbles)
2. Restore Gemini quota or Anthropic credits for conversational quality
3. Start an actual Claude Code session that DEX can delegate to
